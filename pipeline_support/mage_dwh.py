"""Mage bridge: same SQL configuration, dbt execution, reconciliation, step audit."""
from datetime import datetime
import json
import os
from pathlib import Path

from .dbt_runner import build_dbt
from .dwh_checks import inspect_dwh, staging_signature
from .sql_full_load import acquire_staging_lock, batch_window, require_pending_batch

AUDITED = '[DWH_STEP_AUDITED] '


def mage_context():
    import pyodbc
    from mage_ai.io.config import ConfigFileLoader
    from mage_ai.settings.repo import get_repo_path
    repo = Path(os.environ.get('USER_CODE_PATH', get_repo_path())).resolve()
    root = repo if (repo / 'pipeline_support').is_dir() else repo.parent
    config = ConfigFileLoader(str(repo / 'io_config.yaml'), 'default')
    settings = {key: config['MSSQL_' + key] for key in
                ('HOST', 'PORT', 'USER', 'PASSWORD', 'DATABASE', 'DRIVER')}
    def escaped(value):
        return '{' + str(value).replace('}', '}}') + '}'
    options = dict(DRIVER=settings['DRIVER'], SERVER=f"{settings['HOST']},{settings['PORT']}",
                   DATABASE=settings['DATABASE'], UID=settings['USER'], PWD=settings['PASSWORD'],
                   Encrypt='yes', TrustServerCertificate='yes')
    connection_string = ';'.join(key + '=' + escaped(value) for key, value in options.items())
    def connect():
        return pyodbc.connect(connection_string, autocommit=False, timeout=15)
    env = {'MSSQL_' + key: str(settings[key]) for key in
           ('HOST', 'PORT', 'USER', 'PASSWORD', 'DRIVER')}
    env.update(DWH_DATABASE=str(settings['DATABASE']), STAGING_DATABASE=str(settings['DATABASE']),
               DBT_SCHEMA='dbt_staging', STAGING_SCHEMA='dbo', DBT_TARGET='dev')
    return root, connect, env


def lock_warehouse(connection):
    # Same order for both blocks. Staging writers cannot change the source while
    # dbt/checks run, and a second dbt build cannot alter the same DWH meanwhile.
    acquire_staging_lock(connection)
    result = connection.execute("DECLARE @r INT; EXEC @r=sys.sp_getapplock "
        "@Resource='steam_dwh_transform',@LockMode='Exclusive',@LockOwner='Session',"
        "@LockTimeout=0; SELECT @r;").fetchone()[0]
    connection.commit()
    if result < 0:
        raise RuntimeError('Another DWH transform/check is running')


def audit(connection, step, status, rows, error=None, *, completed_batch=None):
    connection.rollback()
    connection.execute('INSERT INTO dbo.etl_audit_log '
        '(pipeline_name,run_date,status,records_processed,error_message) VALUES (?,?,?,?,?)',
        step, datetime.now(), status, rows, error)
    if completed_batch:
        connection.execute('''
            UPDATE dbo.etl_steam_incremental_batch SET completed_at=SYSUTCDATETIME()
            WHERE batch_id=? AND completed_at IS NULL
        ''', completed_batch)
    connection.commit()


def failure(connection, step, exc, progress):
    try:
        audit(connection, step, 'FAILED', 0, str(exc)[:4000])
        return AUDITED
    except Exception:
        progress('Could not record the DWH step failure in etl_audit_log')
        return ''


def run_transform(staging_result, *, project_root, connect, environment,
                  executable=None, timeout_seconds=3600, progress=print):
    if not isinstance(staging_result, dict) or staging_result.get('status') != 'SUCCESS' or not (
            staging_result.get('_full_load_result') or staging_result.get('_staging_result')):
        raise ValueError('Run the staging and audit blocks successfully before dbt')
    connection = connect()
    window = None
    try:
        lock_warehouse(connection)
        batch_id = staging_result.get('batch_id')
        require_pending_batch(connection, batch_id)
        if batch_id:
            window = batch_window(connection, batch_id)
            staging_result = {**staging_result, **window}
            progress(f"DBT WINDOW: LSET={window['lset']}, CET={window['cet']}, batch={batch_id}")
        before = staging_signature(connection)
        if int(before[0]) == 0:
            raise RuntimeError('Staging is empty; dbt was not started')
        if staging_result.get('_full_load_result') and int(before[0]) != staging_result['records_processed']:
            raise RuntimeError('Staging count changed after Full Load; rerun from extract')
        if staging_result.get('outcome') == 'NO_VALID_RECORDS':
            progress('DBT SKIPPED: no valid incremental records.')
            return dict(_dbt_transform_result=True, status='SUCCESS', staging=staging_result,
                        staging_signature=before, dbt=dict(status='SKIPPED', reason='NO_VALID_RECORDS'))
        dbt_env = dict(environment, STEAM_CHANGE_BATCH=batch_id or '',
                       STEAM_CHANGE_LSET=str(window['lset']) if window else '',
                       STEAM_CHANGE_CET=str(window['cet']) if window else '')
        dbt = build_dbt(project_root, dbt_env,
                        executable=executable,
                        timeout_seconds=timeout_seconds, progress=progress)
        if before != staging_signature(connection):
            raise RuntimeError('Staging changed during dbt build; rerun the pipeline')
        audit(connection, 'steam_dbt_transform', 'SUCCESS', int(before[0]))
        return dict(_dbt_transform_result=True, status='SUCCESS', staging=staging_result,
                    staging_signature=before, dbt=dbt)
    except Exception as exc:
        prefix = failure(connection, 'steam_dbt_transform', exc, progress)
        if window:
            progress(f"DBT FAILED: LSET={window['lset']}, CET={window['cet']}; batch remains pending.")
        raise RuntimeError(prefix + f'dbt transform failed: {exc}') from exc
    finally:
        connection.close()


def check_results(transform_result, *, connect, progress=print):
    if not isinstance(transform_result, dict) or not transform_result.get('_dbt_transform_result') or transform_result.get('status') != 'SUCCESS':
        raise ValueError('Run dbt successfully before checking the DWH')
    connection = connect()
    try:
        lock_warehouse(connection)
        if staging_signature(connection) != transform_result['staging_signature']:
            raise RuntimeError('Staging changed since dbt finished; rerun the pipeline')
        upstream = transform_result['staging']
        batch_id = upstream.get('batch_id')
        require_pending_batch(connection, batch_id)
        window = batch_window(connection, batch_id) if batch_id else None
        expected = upstream['records_processed'] if upstream.get('_full_load_result') else None
        report = inspect_dwh(connection, expected_full_rows=expected, progress=progress)
        report.update(_dwh_check_result=True, dbt=transform_result['dbt'])
        if batch_id:
            report['incremental'] = {key: upstream[key] for key in
                                     ('batch_id', 'inserted', 'updated', 'unchanged')}
            report['incremental'].update(window)
        if upstream.get('outcome') == 'NO_VALID_RECORDS':
            report.update(outcome='NO_VALID_RECORDS', source_records=upstream['source_records'],
                          parser_rejected=upstream['parser_rejected'], bad_keys=upstream['bad_keys'],
                          records_processed=0)
        else:
            path = Path(transform_result['dbt']['artifact_dir']) / 'dwh_checks.json'
            path.write_text(json.dumps(report, indent=2), encoding='utf-8')
        if report['failed_checks']:
            raise RuntimeError('DWH reconciliation failed: ' + json.dumps(report['failed_checks']) +
                               '. Existing incremental dbt models do not refresh old games automatically.')
        audit(connection, 'steam_dwh_check', 'SUCCESS', report['row_counts']['fact_game_snapshot'],
              completed_batch=batch_id)
        if window:
            report['incremental']['lset_after'] = window['cet']
            progress(f"WATERMARK COMMITTED: LSET={window['lset']} -> {window['cet']}, CET={window['cet']}")
        if upstream.get('outcome') == 'NO_VALID_RECORDS':
            progress(f"PIPELINE SUCCESS: NO_VALID_RECORDS; all {upstream['source_records']} "
                     "source records rejected. DWH reconciliation passed; LSET/CET unchanged.")
        else:
            progress('PIPELINE SUCCESS: staging, dbt models/tests and DWH reconciliation passed.')
        return report
    except Exception as exc:
        prefix = failure(connection, 'steam_dwh_check', exc, progress)
        raise RuntimeError(prefix + f'DWH check failed: {exc}') from exc
    finally:
        connection.close()
