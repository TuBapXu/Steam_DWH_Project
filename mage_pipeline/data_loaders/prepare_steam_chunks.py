from pathlib import Path
import os, sys
from mage_ai.settings.repo import get_repo_path
project = Path(os.environ.get('USER_CODE_PATH', get_repo_path())).resolve().parent
sys.path.insert(0, str(project))
from pipeline_support.dynamic_chunks import prepare, run_step
from pipeline_support.mage_dwh import mage_context
if 'data_loader' not in globals():
    from mage_ai.data_preparation.decorators import data_loader
@data_loader
def prepare_steam_chunks(*args, **kwargs):
    return run_step(prepare, project, connect=mage_context()[1], **kwargs)
