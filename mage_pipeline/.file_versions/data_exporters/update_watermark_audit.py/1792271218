import pandas as pd  # Xử lý bảng dữ liệu
from os import path  # Ghép đường dẫn file
from mage_ai.io.config import ConfigFileLoader   # Đọc io_config.yaml
from mage_ai.io.mssql import MSSQL               # Kết nối SQL Server
from mage_ai.settings.repo import get_repo_path  # Đường dẫn gốc project

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter  # Đánh dấu hàm chính của block exporter
def update_watermark_audit(df, *args, **kwargs):
    # df là DataFrame từ load_to_staging (dùng để đếm số dòng đã nạp)

    # Lấy các tham số chạy từ giao diện
    run_mode = kwargs.get('run_mode', 'incremental')
    is_demo = bool(kwargs.get('demo_lset') and kwargs.get('demo_cet'))

    n_rows = len(df)  # Số bản ghi đã xử lý trong lần chạy này

    # Nạp cấu hình kết nối từ io_config.yaml
    config = ConfigFileLoader(
        path.join(get_repo_path(), 'io_config.yaml'), 'default'
    )

    with MSSQL.with_config(config) as db:

        # ---------- 1. GHI AUDIT LOG ----------
        # Tên pipeline gồm chế độ chạy, ví dụ: steam_staging_full
        pipeline_name = f"steam_staging_{'demo' if is_demo else run_mode}"
        db.execute(
            "INSERT INTO dbo.etl_audit_log "
            "(pipeline_name, run_date, status, records_processed, error_message) "
            f"VALUES ('{pipeline_name}', GETDATE(), 'SUCCESS', {n_rows}, NULL)"
        )

        # ---------- 2. DỜI WATERMARK ----------
        # Chỉ dời khi chạy incremental thật (bỏ qua full và demo),
        # nếu không sẽ làm sai mốc của các lần chạy sau
        if run_mode == 'incremental' and not is_demo:
            db.execute(
                "UPDATE dbo.etl_watermark "
                "SET lset = DATEADD(year, 2, lset) "
                "WHERE table_name = 'stg_steam_games'"
            )

        db.commit()  # Chốt giao dịch

    print(f"Audit: {pipeline_name} | {n_rows} dong | SUCCESS", flush=True)