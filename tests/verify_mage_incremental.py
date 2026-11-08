"""Run inside the Mage container from /home/src/mage_pipeline."""
import csv
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
import uuid

if __name__ == '__main__':
    metadata_path = Path(__file__).resolve().parents[1] / 'output' / ('mage_test_' + uuid.uuid4().hex + '.db')
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ['MAGE_DATABASE_CONNECTION_URL'] = 'sqlite:///' + str(metadata_path)

import pyodbc
from mage_ai.data_preparation.executors.pipeline_executor import PipelineExecutor
from mage_ai.orchestration.db.models.schedules import PipelineRun
from mage_ai.orchestration.db import db_connection, engine
from mage_ai.orchestration.db.models.base import Base
from mage_ai.data_preparation.models.pipeline import Pipeline
from mage_ai.io.config import ConfigFileLoader


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database_setup.bootstrap import initialize


def connect(database):
    password = os.environ['MSSQL_PASSWORD'].replace('}', '}}')
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};SERVER=sqlserver,1433;'
        f'DATABASE={database};UID=sa;PWD={{{password}}};TrustServerCertificate=yes',
        timeout=10, autocommit=True,
    )


def init_schema(conn):
    database = conn.execute('SELECT DB_NAME()').fetchone()[0]
    initialize(conn, database)


def facts(conn):
    return {r[0]: (r[1], r[2]) for r in conn.execute('''
        SELECT g.appid_nk, f.game_key, f.positive_reviews
        FROM dwh.fact_game_snapshot f JOIN dwh.dim_game g ON g.game_key=f.game_key
    ''')}


def cleaned_load_times(conn):
    return dict(tuple(row) for row in conn.execute(
        'SELECT game_id, _loaded_at FROM dbt_staging.stg_steam_games_cleaned'))


def batches(conn):
    return [(json.loads(r[0]), r[1]) for r in conn.execute('''
        SELECT result_json, completed_at
        FROM dbo.etl_steam_incremental_batch ORDER BY batch_seq
    ''')]


def assert_watermark(conn, label, lset, cet):
    actual = tuple(conn.execute('''
        SELECT COALESCE(MAX(CASE WHEN completed_at IS NOT NULL THEN batch_seq END), 0),
               COALESCE(MAX(batch_seq), 0)
        FROM dbo.etl_steam_incremental_batch
    ''').fetchone())
    assert actual == (lset, cet), (label, actual)
    print(f'WATERMARK DEMO {label}: LSET={lset}, CET={cet}', flush=True)


def verify(conn, database, token):
    repo = str(ROOT / 'mage_pipeline')
    pipeline = Pipeline.get('steam_staging_pipeline', repo_path=repo)
    config_get = ConfigFileLoader.__getitem__

    def test_config(config, key):
        return database if key == 'MSSQL_DATABASE' else config_get(config, key)

    def execute(label, version, mode, source_file=None):
        variables = dict(run_mode=mode, chunk_size=1, max_workers=2, dbt_timeout_seconds=300,
                         source_file=source_file or f'tests/fixtures/games_incremental_{version}.csv',
                         execution_partition=f'{token}-{label}')
        run = PipelineRun.create(pipeline_uuid=pipeline.uuid, variables=variables, status='running')
        try:
            PipelineExecutor(pipeline, execution_partition=run.execution_partition).execute(
                pipeline_run_id=run.id, global_vars=variables)
            if not run.all_blocks_completed():
                raise RuntimeError('Dynamic Mage run did not complete every block')
            expected_chunks = 3 if version == 'v2' else 2
            for name in ('extract_steam_chunk', 'validate_steam_chunk', 'load_steam_chunk'):
                children = [block for block in run.block_runs if block.block_uuid.startswith(name + ':')]
                assert len(children) == expected_chunks, (name, [b.block_uuid for b in children])
            print(f'DYNAMIC PASS {label}: {expected_chunks} Extract/Validate/Load branches', flush=True)
            run.update(status='completed')
        except Exception:
            run.update(status='failed')
            raise

    with patch.object(ConfigFileLoader, '__getitem__', test_config):
        execute('full-v1', 'v1', 'full')
        execute('v1', 'v1', 'incremental')
        baseline = facts(conn)
        times = cleaned_load_times(conn)
        assert set(baseline) == {910101, 910102} and baseline[910101][1] == 10, baseline
        init_schema(conn)
        assert facts(conn) == baseline and cleaned_load_times(conn) == times
        assert conn.execute('SELECT COUNT(*) FROM dbo.stg_steam_games').fetchone()[0] == 2
        assert_watermark(conn, 'V1 complete', 1, 1)

        # V2 really reaches dbt and fails when SQL Server rejects the changed rating.
        game_key = int(baseline[910101][0])
        conn.execute(f'''
            ALTER TABLE dwh.fact_game_snapshot ADD CONSTRAINT ck_watermark_demo_fact
            CHECK (game_key <> {game_key} OR positive_reviews <= 10)
        ''')
        try:
            execute('v2-failed', 'v2', 'incremental')
        except RuntimeError as error:
            assert 'ck_watermark_demo_fact' in str(error), error
        else:
            raise AssertionError('Expected the V2 dbt transform to fail')
        [_, (pending, completion)] = batches(conn)
        assert completion is None and facts(conn) == baseline
        assert (pending['lset'], pending['cet']) == (1, 2), pending
        assert_watermark(conn, 'V2 dbt failed', 1, 2)

        conn.execute('ALTER TABLE dwh.fact_game_snapshot DROP CONSTRAINT ck_watermark_demo_fact')
        execute('v2-resume', 'v2', 'incremental')
        [_, (done, completion)] = batches(conn)
        actual = facts(conn)
        updated_times = cleaned_load_times(conn)
        assert done == pending and completion is not None
        assert (done['inserted'], done['updated'], done['unchanged']) == (1, 1, 1), done
        assert set(actual) == {910101, 910102, 910103}
        assert actual[910101] == (baseline[910101][0], 15)
        assert actual[910102] == baseline[910102] and actual[910103][1] == 5
        assert updated_times[910102] == times[910102]
        assert_watermark(conn, 'V2 retry complete', 2, 2)
        print(f'V2 PASS: {actual}', flush=True)
        execute('v2-repeat', 'v2', 'incremental')
        [_, _, (repeat, completion)] = batches(conn)
        assert completion is not None and (repeat['inserted'], repeat['updated'], repeat['unchanged']) == (0, 0, 3)
        assert facts(conn) == actual and cleaned_load_times(conn) == updated_times
        assert_watermark(conn, 'V2 replay complete', 3, 3)
        staged = [tuple(row) for row in conn.execute('SELECT * FROM dbo.stg_steam_games ORDER BY appid')]
        previous_batches = batches(conn)
        with patch('pipeline_support.mage_dwh.build_dbt', side_effect=AssertionError('V3 must skip dbt')):
            execute('v3', 'v3', 'incremental')
        assert [tuple(row) for row in conn.execute('SELECT * FROM dbo.stg_steam_games ORDER BY appid')] == staged
        assert batches(conn) == previous_batches
        assert facts(conn) == actual and cleaned_load_times(conn) == updated_times
        assert_watermark(conn, 'V3 no valid records', 3, 3)
        print('V3 PASS: all blocks completed, staging and batch history unchanged', flush=True)
        path = ROOT / 'output' / f'platform_changes_{token}.csv'
        with (ROOT / 'tests/fixtures/games_incremental_v2.csv').open(encoding='utf-8', newline='') as stream:
            reader = csv.DictReader(stream)
            fields, rows = reader.fieldnames, list(reader)
        rows[0].update(Mac='True', Publishers='', **{'Release date': ''})
        rows[1].update(Windows='False')
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        execute('platform-changes', 'v2', 'incremental', str(path.relative_to(ROOT)))
        assert facts(conn) == actual
        assert tuple(conn.execute("""
            SELECT f.date_key, f.publisher_key FROM dwh.fact_game_snapshot f
            JOIN dwh.dim_game g ON g.game_key=f.game_key WHERE g.appid_nk=910101
        """).fetchone()) == (0, 0)
        assert [tuple(row) for row in conn.execute("""
            SELECT g.appid_nk, b.operating_system_key FROM dwh.bridge_game_platform b
            JOIN dwh.dim_game g ON g.game_key=b.game_key ORDER BY 1, 2
        """)] == [(910101, 1), (910101, 2), (910103, 1)]
        print('COMPOSITE FACT PASS: stable game keys, Unknown FKs, added and removed platform links', flush=True)
        verify_chunk_publish(conn, database, token)
        print('MAGE INCREMENTAL PASS: recovered a real dbt failure with the same batch window', flush=True)


def verify_chunk_publish(conn, database, token):
    """Exercise SQL reduction with cross-chunk duplicates and a retried chunk."""
    from pipeline_support.dynamic_chunks import prepare, extract, validate, load, finalize

    with (ROOT / 'tests/fixtures/games_incremental_v2.csv').open(newline='', encoding='utf-8') as stream:
        reader = csv.DictReader(stream)
        columns, rows = reader.fieldnames, list(reader)
    rows.append(dict(rows[0], Positive='19'))
    path = ROOT / 'output' / f'duplicate_chunks_{token}.csv'
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    chunks, _ = prepare(ROOT, source_file=str(path.relative_to(ROOT)), chunk_size=2)

    def connection():
        result = connect(database)
        result.autocommit = False
        return result

    baseline = conn.execute('SELECT SUM(positive) FROM dbo.stg_steam_games').fetchone()[0]
    receipts = []
    for chunk in reversed(chunks):
        raw, descriptor = extract(chunk)
        cleaned, descriptor = validate(raw, descriptor)
        receipt = load(cleaned, descriptor, connection)
        assert load(cleaned, descriptor, connection) == receipt  # retry replaces only its private table
        receipts.append(receipt)
        assert conn.execute('SELECT SUM(positive) FROM dbo.stg_steam_games').fetchone()[0] == baseline
    try:
        finalize(receipts[:1], connection)
    except ValueError:
        pass
    else:
        raise AssertionError('Missing chunk must block staging publication')
    result = finalize(receipts, connection)
    assert result['records_processed'] == 3 and result['cross_chunk_duplicates'] == 1, result
    assert conn.execute('SELECT positive FROM dbo.stg_steam_games WHERE appid=910101').fetchone()[0] == 19
    assert finalize(receipts, connection) == result
    print('SQL CHUNKS PASS: duplicate across chunks, reverse completion order, retry and publication gate', flush=True)


def main():
    Base.metadata.create_all(engine)
    db_connection.start_session()
    token = uuid.uuid4().hex[:12]
    database = 'steam_appid_test_' + token
    master = connect('master')
    try:
        initialize(master, database)
        master.execute('USE master')
        try:
            conn = connect(database)
            try:
                verify(conn, database, token)
            finally:
                conn.close()
        finally:
            master.execute(f'DROP DATABASE [{database}]')
    finally:
        master.close()


if __name__ == '__main__':
    main()
