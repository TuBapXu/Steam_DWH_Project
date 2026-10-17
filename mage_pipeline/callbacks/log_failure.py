from os import path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.mssql import MSSQL
from mage_ai.settings.repo import get_repo_path

if 'callback' not in globals():
    from mage_ai.data_preparation.decorators import callback


@callback('failure')
def callback_failure(*args, **kwargs):
    # Nội dung lỗi; nhân đôi dấu ' để không làm hỏng câu SQL
    err = str(kwargs.get('error', 'unknown error'))[:1000].replace("'", "''")
    run_mode = str(kwargs.get('run_mode', 'incremental')).strip().lower()

    config = ConfigFileLoader(
        path.join(get_repo_path(), 'io_config.yaml'), 'default'
    )
    with MSSQL.with_config(config) as db:
        db.execute(
            "INSERT INTO dbo.etl_audit_log "
            "(pipeline_name, run_date, status, records_processed, error_message) "
            f"VALUES ('steam_staging_{run_mode}', GETDATE(), 'FAILED', 0, N'{err}')"
        )
        db.commit()