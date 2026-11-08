"""Initialize the SQL Server database before Mage starts."""
import os
from pathlib import Path
import re
import sys
import time

import pyodbc

SETUP = Path(__file__).resolve().parent
sys.path.insert(0, str(SETUP.parent))
from pipeline_support.sql_full_load import ensure_incremental_schema, require_pending_batch


def initialize(connection, database='steam_games_DWH'):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', database):
        raise ValueError('Invalid bootstrap database name')

    def execute_script(name):
        script = (SETUP / name).read_text(encoding='utf-8-sig')
        script = script.replace('steam_games_DWH', database)
        for batch in re.split(r'^\s*GO\s*$', script, flags=re.MULTILINE | re.IGNORECASE):
            if batch.strip():
                connection.execute(batch)

    execute_script('01_init_watermark_audit.sql')
    execute_script('02_create_star_schema_dwh.sql')
    execute_script('04_create_steam_rejected.sql')
    ensure_incremental_schema(connection)
    connection.execute("IF SCHEMA_ID('dbt_staging') IS NULL EXEC('CREATE SCHEMA dbt_staging')")
    orphans = connection.execute(f"""
        SELECT TABLE_NAME FROM [{database}].INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME LIKE '_steam_full_%'
    """).fetchall()
    for row in orphans:
        connection.execute(f"DROP TABLE [{database}].dbo.[{row[0]}]")
    needs_upgrade = connection.execute("""
        SELECT COUNT(*) FROM sys.key_constraints
        WHERE parent_object_id = OBJECT_ID('dwh.fact_game_snapshot')
          AND name = 'uq_fact_game_snapshot_game'
    """).fetchone()[0] == 0
    if needs_upgrade:
        require_pending_batch(connection)
        execute_script('03_migrate_fact_composite_key.sql')


def main():
    password = os.environ['MSSQL_PASSWORD'].replace('}', '}}')
    settings = ('DRIVER={ODBC Driver 17 for SQL Server};SERVER=sqlserver,1433;'
                f'DATABASE=master;UID=sa;PWD={{{password}}};Encrypt=yes;TrustServerCertificate=yes')
    deadline = time.monotonic() + 120
    while True:
        try:
            connection = pyodbc.connect(settings, timeout=5, autocommit=True)
            break
        except pyodbc.Error as error:
            if error.args[0] == '28000' or time.monotonic() >= deadline:
                raise RuntimeError(f'Cannot connect to SQL Server (SQLSTATE {error.args[0]})') from None
            time.sleep(2)
    try:
        initialize(connection)
        print('Steam database schema ready.', flush=True)
    finally:
        connection.close()


if __name__ == '__main__':
    main()
