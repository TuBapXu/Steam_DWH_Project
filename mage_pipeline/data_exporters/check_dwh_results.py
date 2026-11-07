from pathlib import Path
import os
import sys
from mage_ai.settings.repo import get_repo_path

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def check_dwh_results(transform_result, *args, **kwargs):
    repo = Path(os.environ.get('USER_CODE_PATH', get_repo_path())).resolve()
    root = repo if (repo / 'pipeline_support').is_dir() else repo.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from pipeline_support.mage_dwh import mage_context, check_results
    _, connect, _ = mage_context()
    return check_results(transform_result, connect=connect,
                         progress=lambda message: print(message, flush=True))
