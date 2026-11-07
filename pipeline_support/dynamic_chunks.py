"""Mage dynamic chunk data flow with immutable raw files and per-chunk SQL buffers."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from .full_load import (SQL_COLUMNS, make_full_plan, make_incremental_plan,
                        prepare_chunk, read_chunks, validate_full_plan)
from .sql_full_load import SqlFullLoadStore, identifier
from .dwh_checks import staging_signature
from .rejected import write_rejections


def run_step(operation, *args, **kwargs):
    """Record failures without Mage trying to fetch an unfinished dynamic output."""
    try:
        return operation(*args, **kwargs)
    except Exception as error:
        from .mage_dwh import mage_context, failure
        try:
            _, connect, _ = mage_context()
            connection = connect()
            try:
                failure(connection, 'steam_' + operation.__name__, error, print)
            finally:
                connection.close()
        except Exception as audit_error:
            print(f'Could not record chunk failure: {audit_error}', flush=True)
        raise


def prepare(root, *, connect=None, **options):
    mode = str(options.get('run_mode', 'full')).strip().lower()
    if mode not in ('full', 'incremental'):
        raise ValueError('run_mode must be full or incremental')
    if mode == 'incremental' and (options.get('demo_lset') or options.get('demo_cet')):
        raise ValueError('Use null demo_lset/demo_cet for AppID + row_hash incremental. '
                         'Release-date demo slicing belongs to the legacy pipeline; '
                         'batch LSET/CET are managed automatically.')
    source = (root / (options.get('source_file') or 'data/games.csv')).resolve()
    if not source.is_relative_to(root.resolve()):
        raise ValueError('source_file must belong to this project')
    maker = make_full_plan if mode == 'full' else make_incremental_plan
    plan = maker(source, chunk_size=options.get('chunk_size', 1000),
                 max_workers=options.get('max_workers', 2))
    partition = options.get('_execution_partition') or options.get('execution_partition')
    if partition:
        identity = (str(partition), str(source), plan['source_size'], plan['source_mtime_ns'],
                    mode, plan['chunk_size'])
        plan['run_id'] = hashlib.sha256(json.dumps(identity).encode()).hexdigest()[:32]
    folder = root / 'output' / 'mage_chunks' / plan['run_id']
    folder.mkdir(parents=True, exist_ok=True)
    manifest_path = folder / 'manifest.json'
    if manifest_path.exists():
        plan = json.loads(manifest_path.read_text(encoding='utf-8'))['plan']
    diagnostics = {}
    chunks = []
    rejected = []

    def flush_rejected():
        write_rejections(connect, plan['run_id'], str(source.relative_to(root)), rejected)
        rejected.clear()

    def on_rejected(record):
        rejected.append(record)
        if len(rejected) >= 128:
            flush_rejected()

    def on_chunk_sources(index, frame, sources):
        invalid = pd.to_numeric(frame['AppID'], errors='coerce').isna().to_numpy()
        bad = []
        for record, rejected_key in zip(sources, invalid, strict=True):
            if rejected_key:
                missing = not record['raw_appid'].strip()
                bad.append(dict(record, chunk_id=index, rejected_stage='VALIDATE',
                                reason_code='MISSING_APPID' if missing else 'INVALID_APPID',
                                reason_detail='AppID is empty' if missing else 'AppID is not numeric'))
        if bad:
            (folder / f'rejected_{index}.json').write_text(json.dumps(bad), encoding='utf-8')

    for index, frame in read_chunks(plan, diagnostics, progress=lambda message: print(message, flush=True),
                                    on_rejected=on_rejected if connect else None,
                                    on_chunk_sources=on_chunk_sources if connect else None):
        path = folder / f'raw_{index}.parquet'
        frame.to_parquet(path, index=True)
        descriptor = dict(plan=plan, chunk_id=index, raw_path=str(path))
        rejected_path = folder / f'rejected_{index}.json'
        if connect and rejected_path.exists():
            descriptor.update(rejected_path=str(rejected_path), source_file=str(source.relative_to(root)))
        chunks.append(descriptor)
    flush_rejected()
    if not chunks:
        raise ValueError('CSV has no readable records')
    validate_full_plan(plan)
    manifest = dict(plan=plan, diagnostics=diagnostics, chunk_count=len(chunks))
    manifest_path.write_text(json.dumps(manifest), encoding='utf-8')
    print(f"Prepared {len(chunks)} raw chunks for {mode} load", flush=True)
    return [chunks, [dict(block_uuid=f"chunk_{item['chunk_id']:05d}") for item in chunks]]


def restore_csv_nulls(frame):
    """Parquet/Mage can turn CSV NaN objects into None; preserve astype(str) semantics."""
    frame = frame.copy()
    for column, dtype in frame.dtypes.items():
        if dtype == object:
            frame[column] = frame[column].where(frame[column].notna(), float('nan'))
    return frame


def extract(chunk):
    frame = restore_csv_nulls(pd.read_parquet(chunk['raw_path']))
    print(f"EXTRACT chunk={chunk['chunk_id']}, rows={len(frame)}", flush=True)
    return [frame, chunk]


def validate(frame, chunk, connect=None):
    frame = restore_csv_nulls(frame)
    plan = chunk['plan']
    cleaned, counts = prepare_chunk(chunk['chunk_id'], frame, plan['loaded_at'], plan['run_mode'])
    if connect and chunk.get('rejected_path'):
        records = json.loads(Path(chunk['rejected_path']).read_text(encoding='utf-8'))
        if len(records) != counts['bad_keys']:
            raise RuntimeError('Rejected AppID count does not match source record positions')
        write_rejections(connect, plan['run_id'], chunk['source_file'], records)
    print(f'VALIDATE chunk statistics: {counts}', flush=True)
    return [cleaned, dict(chunk, counts=counts)]


def chunk_store(connect, chunk):
    key = hashlib.sha256(f"{chunk['plan']['run_id']}:{chunk['chunk_id']}".encode()).hexdigest()[:32]
    return SqlFullLoadStore(connect, key, run_mode=chunk['plan']['run_mode'])


def load(frame, chunk, connect):
    store = chunk_store(connect, chunk)
    # Separate work tables allow independent Mage branches to write concurrently.
    store.main = connect()
    try:
        result = store.main.execute(
            "DECLARE @r int; EXEC @r=sys.sp_getapplock @Resource=?,"
            "@LockMode='Exclusive',@LockOwner='Session',@LockTimeout=0; SELECT @r",
            'steam_chunk_' + store.run_id).fetchone()[0]
        if result < 0:
            raise RuntimeError('This chunk is already being loaded')
        store.main.execute(f"IF OBJECT_ID('{store.table}','U') IS NOT NULL DROP TABLE {store.table}")
        store.main.commit()
        store.create_buffer()
        if not frame.empty:
            store.load_chunk(chunk['chunk_id'], frame)
        count = store.main.execute(f'SELECT COUNT_BIG(*) FROM {store.table}').fetchone()[0]
        if count != chunk['counts']['cleaned_rows']:
            raise RuntimeError('Chunk SQL count does not match validation')
        print(f"LOAD chunk={chunk['chunk_id']}, rows={count}", flush=True)
        return dict(chunk, loaded_rows=count)
    finally:
        store.main.close()


def finalize(receipts, connect):
    if not receipts:
        raise ValueError('No chunk outputs received')
    plan = receipts[0]['plan']
    folder = Path(receipts[0]['raw_path']).parent
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    expected_ids = set(range(manifest['chunk_count']))
    if (plan != manifest['plan'] or len(receipts) != len(expected_ids)
            or {r['chunk_id'] for r in receipts} != expected_ids
            or any(r['plan'] != plan or r['loaded_rows'] != r['counts']['cleaned_rows'] for r in receipts)):
        raise ValueError('Missing, duplicate, or mixed-run chunk outputs')
    validate_full_plan(plan)
    totals = {key: sum(r['counts'][key] for r in receipts) for key in
              ('rows_read', 'bad_keys', 'bad_dates', 'cleaned_rows', 'local_duplicates')}
    totals.update(manifest['diagnostics'])
    with SqlFullLoadStore(connect, plan['run_id'], run_mode=plan['run_mode']) as store:
        result_path = folder / 'published.json'
        if result_path.exists():
            saved = json.loads(result_path.read_text(encoding='utf-8'))
            if saved['signature'] != staging_signature(store.main):
                raise RuntimeError('Staging changed since this run was published. Start a new run.')
            return saved['result']

        def published(result):
            result = {**result, 'run_id': plan['run_id']}
            saved = dict(result=result, signature=staging_signature(store.main))
            result_path.write_text(json.dumps(saved), encoding='utf-8')
            for receipt in receipts:
                child = chunk_store(connect, receipt)
                store.main.execute(f"DROP TABLE IF EXISTS {child.table}")
            store.main.commit()
            return result

        try:
            if plan['run_mode'] == 'incremental':
                resumed = store.resume_incremental(plan)
                if resumed:
                    return published(resumed)
            store.create_buffer()
            columns = ','.join(identifier(c) for c in SQL_COLUMNS) + ',__source_row'
            for receipt in receipts:
                child = chunk_store(connect, receipt)
                store.main.execute(f'INSERT {store.table} ({columns}) SELECT {columns} FROM {child.table}')
            store.main.commit()
            accepted = store.count_winners()
            totals['cross_chunk_duplicates'] = totals['cleaned_rows'] - accepted
            totals['duplicates'] = totals['local_duplicates'] + totals['cross_chunk_duplicates']
            if (totals['rows_read'] != totals['bad_keys'] + totals['duplicates'] + accepted
                    or totals['source_records'] != totals['parser_rejected'] + totals['rows_read']):
                raise RuntimeError('Whole-file reconciliation failed')
            if not accepted:
                if plan['run_mode'] != 'incremental':
                    raise RuntimeError('No valid records; existing staging is preserved')
                return published(dict(_staging_result=True, run_id=plan['run_id'],
                                      status='SUCCESS', outcome='NO_VALID_RECORDS',
                                      run_mode='incremental', records_processed=0,
                                      inserted=0, updated=0, unchanged=0,
                                      chunks=len(receipts), **totals))
            if plan['run_mode'] == 'incremental':
                return published(store.publish_incremental(plan, accepted, dict(chunks=len(receipts), **totals)))
            store.publish(accepted)
            return published(dict(_full_load_result=True, run_id=plan['run_id'], status='SUCCESS',
                        run_mode='full', records_processed=accepted, chunks=len(receipts),
                        audit_logged=True, **totals))
        except Exception as error:
            store.record_failure(str(error))
            raise
        finally:
            store.main.rollback()
            store.cleanup()
