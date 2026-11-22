from pathlib import Path
import os
import sys

from mage_ai.settings.repo import get_repo_path

if 'callback' not in globals():
    from mage_ai.data_preparation.decorators import callback


@callback('failure')
def callback_failure(*args, **kwargs):
    # Mage passes the block exception as `__error` (global variables arrive as the other kwargs).
    error = kwargs.get('__error') or kwargs.get('error') or 'unknown error'
    if any(marker in str(error) for marker in ('[FULL_LOAD_AUDITED]', '[DWH_STEP_AUDITED]')):
        return  # The responsible step already committed one FAILED audit entry.
    repo = Path(os.environ.get('USER_CODE_PATH', get_repo_path())).resolve()
    root = repo if (repo / 'pipeline_support').is_dir() else repo.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from pipeline_support.audit import write_audit
    from pipeline_support.mage_dwh import mage_context

    run_mode = str(kwargs.get('run_mode', 'incremental')).strip().lower()
    _, connect, _ = mage_context()
    connection = connect()
    try:
        # Parameterised insert; the run_id is unknown here, so the row is matched by time/trigger.
        write_audit(connection, pipeline_name=f'steam_staging_{run_mode}', step='pipeline',
                    status='FAILED', records_processed=0,
                    error=str(error)[:4000],
                    run_mode=run_mode, trigger_name=kwargs.get('trigger_name'))
    finally:
        connection.close()
