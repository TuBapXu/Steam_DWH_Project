"""One writer for dbo.etl_audit_log: one row per ETL step, rows of a run share run_id."""
from datetime import datetime, timezone
import json
import re

STEPS = ('staging', 'dbt', 'check', 'chunk', 'pipeline')
COLUMNS = ('pipeline_name', 'run_date', 'status', 'records_processed', 'error_message',
           'run_id', 'step', 'trigger_name', 'run_mode', 'started_at', 'finished_at',
           'duration_sec', 'inserted', 'updated', 'unchanged', 'rejected', 'dbt_tests',
           'checks_failed', 'metrics_json')
INSERT_SQL = ('INSERT INTO dbo.etl_audit_log (' + ','.join(COLUMNS) + ') VALUES (' +
              ','.join('?' for _ in COLUMNS) + ')')


def utc_now():
    # Same clock as the existing run_date values (the containers run on UTC).
    return datetime.now(timezone.utc).replace(tzinfo=None)


def parse_time(value):
    if value is None or isinstance(value, datetime):
        return value.replace(tzinfo=None) if value is not None and value.tzinfo else value
    return datetime.fromisoformat(str(value)).replace(tzinfo=None)


def run_context(source):
    """Pick run_id/run_mode/trigger_name/started_at from a plan, chunk or step result."""
    if not isinstance(source, dict):
        return {}
    plan = source.get('plan') if isinstance(source.get('plan'), dict) else {}
    staging = source.get('staging') if isinstance(source.get('staging'), dict) else {}
    found = {}
    for key in ('run_id', 'run_mode', 'trigger_name', 'started_at'):
        for candidate in (source, staging, plan):
            if candidate.get(key) is not None:
                found[key] = candidate[key]
                break
    if 'run_id' not in found:
        batch = source.get('batch_id') or staging.get('batch_id')
        if batch:
            found['run_id'] = batch
    run_id = found.get('run_id')
    if run_id is not None and not re.fullmatch(r'[0-9a-f]{32}', str(run_id)):
        found.pop('run_id')
    return found


def _int(value):
    return None if value is None else int(value)


def write_audit(connection, *, pipeline_name, step, status, records_processed=0, error=None,
                run_id=None, run_mode=None, trigger_name=None, started_at=None, finished_at=None,
                inserted=None, updated=None, unchanged=None, rejected=None, dbt_tests=None,
                checks_failed=None, metrics=None, commit=True):
    if step not in STEPS:
        raise ValueError(f'Unknown audit step {step!r}')
    if status not in ('SUCCESS', 'FAILED'):
        raise ValueError(f'Unknown audit status {status!r}')
    finished = parse_time(finished_at) or utc_now()
    started = parse_time(started_at)
    duration = max(0, int(round((finished - started).total_seconds()))) if started else None
    payload = None if metrics is None else json.dumps(metrics, ensure_ascii=False, default=str)
    values = (pipeline_name, finished, status, _int(records_processed) or 0,
              None if error is None else str(error)[:4000], run_id, step, trigger_name or 'manual',
              run_mode, started, finished, duration, _int(inserted), _int(updated),
              _int(unchanged), _int(rejected), _int(dbt_tests), _int(checks_failed), payload)
    connection.execute(INSERT_SQL, *values)
    if commit:
        connection.commit()
    return dict(zip(COLUMNS, values))


def staging_metrics(result):
    """Audit fields for a staging result produced by dynamic_chunks.finalize."""
    rejected = (int(result.get('parser_rejected') or 0)
                + int(result.get('bad_keys') or 0)
                + int(result.get('rule_rejected') or 0))
    keys = ('source_records', 'rows_read', 'parser_rejected', 'bad_keys', 'rule_rejected',
            'bad_dates', 'cleaned_rows', 'duplicates', 'chunks', 'outcome', 'lset', 'cet',
            'batch_id', 'resumed')
    if result.get('run_mode') == 'full':
        # A full load replaces staging: every accepted record is (re)inserted.
        changes = dict(inserted=result.get('records_processed'), updated=0, unchanged=0)
    else:
        changes = dict(inserted=result.get('inserted'), updated=result.get('updated'),
                       unchanged=result.get('unchanged'))
    return dict(**changes, rejected=rejected,
                metrics={key: result[key] for key in keys if key in result})
