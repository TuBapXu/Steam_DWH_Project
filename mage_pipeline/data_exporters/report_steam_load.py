from pathlib import Path
import os, sys
from mage_ai.settings.repo import get_repo_path
project = Path(os.environ.get('USER_CODE_PATH', get_repo_path())).resolve().parent
sys.path.insert(0, str(project))
from pipeline_support.mage_dwh import mage_context
from pipeline_support.rejected import read_rejections
if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
@data_exporter
def report_steam_load(result, *args, **kwargs):
    if result.get('status') != 'SUCCESS':
        raise RuntimeError('Staging did not succeed')
    if result.get('outcome') == 'NO_VALID_RECORDS':
        print(f"NO_VALID_RECORDS: 0/{result['source_records']} valid records; "
              f"{result['parser_rejected']} CSV rejects, {result['bad_keys']} invalid AppIDs. "
              "Staging unchanged.", flush=True)
    print(result, flush=True)
    run_id = result.get('run_id') or result.get('batch_id')
    rejected_records = read_rejections(mage_context()[1], run_id) if run_id else []
    print(f"Rejected records for run {run_id}: {len(rejected_records)}", flush=True)
    return {**result, 'run_id': run_id, 'rejected_record_count': len(rejected_records),
            'rejected_records': rejected_records}
