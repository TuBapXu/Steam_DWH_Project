import pandas as pd
import pyodbc
from os import path
from mage_ai.io.config import ConfigFileLoader
from mage_ai.io.mssql import MSSQL
from mage_ai.settings.repo import get_repo_path

if 'data_exporter' not in globals():
    from mage_ai.data_preparation.decorators import data_exporter


@data_exporter
def load_to_staging(df, *args, **kwargs):
    run_mode = str(kwargs.get('run_mode', 'incremental')).strip().lower()

    if df.empty:
        print("Batch rong, khong nap gi.", flush=True)
        return df

    # NaN/NaT/NA -> None để SQL Server nhận là NULL
    data = df.astype(object).where(df.notna(), None)

    cols = list(df.columns)
    col_sql = ", ".join(f"[{c}]" for c in cols)
    placeholders = ", ".join("?" for _ in cols)

    # Dùng đúng cấu hình đã chạy được ở các block khác
    config = ConfigFileLoader(path.join(get_repo_path(), 'io_config.yaml'), 'default')

    with MSSQL.with_config(config) as db:
        # Mở kết nối riêng bằng connection string của Mage để tự kiểm soát commit
        conn = pyodbc.connect(db.connection_string, autocommit=False)
        try:
            cur = conn.cursor()

            if run_mode == 'full':
                cur.execute("TRUNCATE TABLE dbo.stg_steam_games")
            else:
                ids = df['appid'].astype('int64').tolist()
                for i in range(0, len(ids), 1000):
                    chunk = ",".join(str(x) for x in ids[i:i + 1000])
                    cur.execute(f"DELETE FROM dbo.stg_steam_games WHERE appid IN ({chunk})")

            cur.fast_executemany = True
            cur.executemany(
                f"INSERT INTO dbo.stg_steam_games ({col_sql}) VALUES ({placeholders})",
                data.values.tolist(),
            )
            conn.commit()

            cur.execute("SELECT COUNT(*) FROM dbo.stg_steam_games")
            total = cur.fetchone()[0]
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    if total == 0:
        raise RuntimeError("Nap xong nhung staging van rong")

    print(f"Da nap {len(df)} dong | Tong dong trong staging: {total}", flush=True)
    return df