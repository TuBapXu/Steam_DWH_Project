from pathlib import Path
import os, sys
from mage_ai.settings.repo import get_repo_path
project = Path(os.environ.get('USER_CODE_PATH', get_repo_path())).resolve().parent
sys.path.insert(0, str(project))
from pipeline_support.dynamic_chunks import load, run_step
from pipeline_support.mage_dwh import mage_context
if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter
@data_exporter
def load_steam_chunk(payload, *args, **kwargs):
    frame, chunk = (payload, args[0]) if args else payload
    return run_step(load, frame, chunk, mage_context()[1])
