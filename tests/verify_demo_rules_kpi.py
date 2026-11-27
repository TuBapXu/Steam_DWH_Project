"""Live E2E verification inside Mage container for all 4 demo scenarios + original rule cross-checks."""
import csv
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch
import uuid

if __name__ == '__main__':
    metadata_path = Path(__file__).resolve().parents[1] / 'output' / ('mage_demo_verify_' + uuid.uuid4().hex + '.db')
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ['MAGE_DATABASE_CONNECTION_URL'] = 'sqlite:///' + str(metadata_path)

import pyodbc
from mage_ai.data_preparation.executors.pipeline_executor import PipelineExecutor
from mage_ai.orchestration.db import db_connection, engine
from mage_ai.orchestration.db.models.base import Base
from mage_ai.orchestration.db.models.schedules import PipelineRun
from mage_ai.data_preparation.models.pipeline import Pipeline
from mage_ai.io.config import ConfigFileLoader

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from database_setup.bootstrap import initialize


def connect(database):
    password = os.environ['MSSQL_PASSWORD'].replace('}', '}}')
    return pyodbc.connect(
        'DRIVER={ODBC Driver 17 for SQL Server};SERVER=sqlserver,1433;'
        f'DATABASE={database};UID=sa;PWD={{{password}}};TrustServerCertificate=yes',
        timeout=15, autocommit=True,
    )


def run_all_cases(conn, database, token):
    repo = str(ROOT / 'mage_pipeline')
    pipeline = Pipeline.get('steam_staging_pipeline', repo_path=repo)
    config_get = ConfigFileLoader.__getitem__

    def test_config(config, key):
        return database if key == 'MSSQL_DATABASE' else config_get(config, key)

    def execute(label, source_file, mode='incremental'):
        variables = dict(
            run_mode=mode,
            chunk_size=100,
            max_workers=2,
            dbt_timeout_seconds=300,
            trigger_name='demo_' + label,
            source_file=source_file,
            execution_partition=f'{token}-{label}',
        )
        run = PipelineRun.create(pipeline_uuid=pipeline.uuid, variables=variables, status='running')
        try:
            PipelineExecutor(pipeline, execution_partition=run.execution_partition).execute(
                pipeline_run_id=run.id, global_vars=variables
            )
            if not run.all_blocks_completed():
                raise RuntimeError(f'Mage run {label} did not complete every block')
            run.update(status='completed')
        except Exception:
            run.update(status='failed')
            raise

    def latest_run_summary():
        row = conn.execute("""
            SELECT TOP 1 run_id FROM dbo.etl_audit_log
            WHERE run_id IS NOT NULL ORDER BY log_id DESC
        """).fetchone()
        run_id = row[0]
        rows = conn.execute("""
            SELECT step, status, records_processed, inserted, updated, unchanged,
                   rejected, dbt_tests, checks_failed, metrics_json
            FROM dbo.etl_audit_log WHERE run_id = ? ORDER BY log_id
        """, run_id).fetchall()
        cols = ['step', 'status', 'records_processed', 'inserted', 'updated',
                'unchanged', 'rejected', 'dbt_tests', 'checks_failed', 'metrics_json']
        return run_id, {r[0]: dict(zip(cols, r)) for r in rows}

    def rejections_for(run_id):
        return conn.execute("""
            SELECT line_start, rejected_stage, reason_code, raw_appid, reason_detail
            FROM dbo.stg_steam_games_rejected
            WHERE run_id = ?
            ORDER BY line_start, reason_code
        """, run_id).fetchall()

    with patch.object(ConfigFileLoader, '__getitem__', test_config):
        # ── TC1: Valid Incremental Insert ────────────────────────────────────────
        execute('tc1', 'tests/fixtures/demo/tc1_valid_incremental.csv')
        rid, steps = latest_run_summary()
        assert [(k, v['status']) for k, v in steps.items()] == [
            ('staging', 'SUCCESS'), ('dbt', 'SUCCESS'), ('check', 'SUCCESS')
        ], steps
        assert (steps['staging']['inserted'], steps['staging']['updated'],
                steps['staging']['unchanged'], steps['staging']['rejected']) == (3, 0, 0, 0), steps['staging']
        assert steps['dbt']['dbt_tests'] > 0 and steps['check']['checks_failed'] == 0
        row_920103 = conn.execute("""
            SELECT c.is_free, c.positive_review_ratio, p.publisher_tier
            FROM dbt_staging.stg_steam_games_cleaned c
            JOIN dwh.dim_game g ON g.appid_nk = c.game_id
            JOIN dwh.fact_game_snapshot f ON f.game_key = g.game_key
            JOIN dwh.dim_publisher p ON p.publisher_key = f.publisher_key
            WHERE c.game_id = 920103
        """).fetchone()
        assert row_920103[0] == 0 and abs(float(row_920103[1]) - 0.75) < 1e-6 and row_920103[2] == 'Indie', row_920103
        print(f'TC1 PASS: inserted=3, rejected=0, dbt_tests={steps["dbt"]["dbt_tests"]}, 920103={tuple(row_920103)}', flush=True)

        # ── TC1b: Valid Incremental Update + Unchanged + Idempotency ─────────────
        execute('tc1b', 'tests/fixtures/demo/tc1b_valid_update.csv')
        rid, steps = latest_run_summary()
        assert (steps['staging']['inserted'], steps['staging']['updated'],
                steps['staging']['unchanged'], steps['staging']['rejected']) == (1, 1, 2, 0), steps['staging']
        pos_920101 = conn.execute("SELECT positive_reviews FROM dwh.fact_game_snapshot f JOIN dwh.dim_game g ON g.game_key=f.game_key WHERE g.appid_nk=920101").fetchone()[0]
        assert pos_920101 == 150, pos_920101
        execute('tc1b_repeat', 'tests/fixtures/demo/tc1b_valid_update.csv')
        _, steps_rep = latest_run_summary()
        assert (steps_rep['staging']['inserted'], steps_rep['staging']['updated'],
                steps_rep['staging']['unchanged']) == (0, 0, 4), steps_rep['staging']
        print('TC1b PASS: inserted=1, updated=1 (920101 pos=150), unchanged=2; repeat unchanged=4', flush=True)

        # ── TC2: Mixed Valid + Invalid (Parser, AppID, Dirty Columns) ────────────
        execute('tc2', 'tests/fixtures/demo/tc2_invalid_mixed.csv')
        rid, steps = latest_run_summary()
        assert (steps['staging']['inserted'], steps['staging']['rejected']) == (2, 4), steps['staging']
        rej = rejections_for(rid)
        assert [(r[1], r[2]) for r in rej] == [
            ('VALIDATE', 'INVALID_APPID'),
            ('VALIDATE', 'MISSING_APPID'),
            ('PREPARE', 'INVALID_CSV'),
            ('PREPARE', 'TOO_MANY_FIELDS'),
        ], rej
        dirty = conn.execute("""
            SELECT c.price, c.discount_percentage, c.metacritic_score, c.release_date, f.date_key
            FROM dbt_staging.stg_steam_games_cleaned c
            JOIN dwh.dim_game g ON g.appid_nk = c.game_id
            JOIN dwh.fact_game_snapshot f ON f.game_key = g.game_key
            WHERE c.game_id = 920203
        """).fetchone()
        assert tuple(dirty) == (None, None, None, None, 0), dirty
        print(f'TC2 PASS: inserted=2, rejected=4 {[r[2] for r in rej]}, 920203 dirty cols nullified -> {tuple(dirty)}', flush=True)

        # ── TC3a: Baseline Rules on tc3_rule_toggle.csv ──────────────────────────
        execute('tc3a', 'tests/fixtures/demo/tc3_rule_toggle.csv')
        rid, steps = latest_run_summary()
        assert (steps['staging']['inserted'], steps['staging']['rejected']) == (4, 0), steps['staging']
        tc3_rows = dict((r[0], tuple(r[1:])) for r in conn.execute("""
            SELECT game_id, game_title, is_title_missing, price, discount_percentage
            FROM dbt_staging.stg_steam_games_cleaned
            WHERE game_id IN (920301, 920302, 920303, 920304)
        """).fetchall())
        assert tc3_rows[920302][2] is None  # price -5.00 nullified
        assert tc3_rows[920303][0] == 'Unknown game 920303' and tc3_rows[920303][1] == 1
        assert tc3_rows[920304][3] is None  # discount 150 nullified
        print('TC3a PASS: default rules pass 4 rows and nullify dirty values/fill Unknown title', flush=True)

        # ── TC3b: Enable REJECT_NEGATIVE_PRICE & REQUIRE_GAME_NAME via SQL ───────
        conn.execute("""
            UPDATE dbo.etl_validation_rules SET is_active = 1
            WHERE rule_code IN ('REJECT_NEGATIVE_PRICE', 'REQUIRE_GAME_NAME')
        """)
        execute('tc3b', 'tests/fixtures/demo/tc3_rule_toggle.csv')
        rid, steps = latest_run_summary()
        assert steps['staging']['rejected'] == 2, steps['staging']
        rej = rejections_for(rid)
        assert [(r[2], r[3]) for r in rej] == [
            ('REJECT_NEGATIVE_PRICE', '920302'),
            ('REQUIRE_GAME_NAME', '920303'),
        ], rej
        print(f'TC3b PASS: dynamic REJECT rules caught {[(r[2], r[3]) for r in rej]} without code changes', flush=True)

        # ── TC3c: Add brand-new rule MAX_PRICE_10 via SQL INSERT ─────────────────
        conn.execute("""
            UPDATE dbo.etl_validation_rules SET is_active = 0
            WHERE rule_code IN ('REJECT_NEGATIVE_PRICE', 'REQUIRE_GAME_NAME')
        """)
        conn.execute("""
            INSERT INTO dbo.etl_validation_rules
                (rule_code, rule_name, target_column, rule_type, params_json, on_fail_action, is_active, sort_order)
            VALUES ('MAX_PRICE_10', N'Chan gia > 10', 'Price', 'MAX_VALUE', '{"max": 10}', 'REJECT_ROW', 1, 85)
        """)
        execute('tc3c', 'tests/fixtures/demo/tc3_rule_toggle.csv')
        rid, steps = latest_run_summary()
        rej = rejections_for(rid)
        assert [(r[2], r[3]) for r in rej] == [('MAX_PRICE_10', '920301')], rej
        print(f'TC3c PASS: newly inserted SQL rule MAX_PRICE_10 caught {rej[0][3]}', flush=True)

        # ── TC3d: Remove MAX_PRICE_10 & Disable PRICE_NON_NEGATIVE NULLIFY rule ──
        conn.execute("DELETE FROM dbo.etl_validation_rules WHERE rule_code = 'MAX_PRICE_10'")
        conn.execute("UPDATE dbo.etl_validation_rules SET is_active = 0 WHERE rule_code = 'PRICE_NON_NEGATIVE'")
        # Write a fresh game 920305 with negative price -7.50 to prove raw negative price passes when rule removed
        tc3d_path = ROOT / 'output' / f'tc3d_{token}.csv'
        with (ROOT / 'tests/fixtures/demo/tc3_rule_toggle.csv').open('r', encoding='utf-8', newline='') as f:
            reader = list(csv.DictReader(f))
            fields = list(reader[0].keys())
        new_row = dict(reader[1], AppID='920305', Name='Demo Negative Allowed', Price='-7.50')
        with tc3d_path.open('w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerow(new_row)
        try:
            execute('tc3d_off', str(tc3d_path.relative_to(ROOT)))
            price_off = conn.execute("SELECT price FROM dwh.fact_game_snapshot f JOIN dwh.dim_game g ON g.game_key=f.game_key WHERE g.appid_nk=920305").fetchone()[0]
            assert float(price_off) == -7.50, price_off
            # Re-enable PRICE_NON_NEGATIVE -> recomputes 920305 back to NULL automatically!
            conn.execute("UPDATE dbo.etl_validation_rules SET is_active = 1 WHERE rule_code = 'PRICE_NON_NEGATIVE'")
            execute('tc3d_on', str(tc3d_path.relative_to(ROOT)))
            price_on = conn.execute("SELECT price FROM dwh.fact_game_snapshot f JOIN dwh.dim_game g ON g.game_key=f.game_key WHERE g.appid_nk=920305").fetchone()[0]
            assert price_on is None, price_on
            print(f'TC3d PASS: PRICE_NON_NEGATIVE off -> {price_off}; re-enabled -> recomputed {price_on}', flush=True)
        finally:
            if tc3d_path.exists():
                tc3d_path.unlink()

        # ── TC4a: Baseline KPIs on tc4_kpi_change.csv ────────────────────────────
        execute('tc4a', 'tests/fixtures/demo/tc4_kpi_change.csv')
        pub_before = conn.execute("SELECT publisher_key, publisher_tier FROM dwh.dim_publisher WHERE publisher_name = N'KPI Demo Pub'").fetchone()
        assert pub_before[1] == 'Indie', pub_before
        kpi_before = dict((r[0], tuple(r[1:])) for r in conn.execute("""
            SELECT game_id, is_free, CAST(positive_review_ratio AS FLOAT)
            FROM dbt_staging.stg_steam_games_cleaned WHERE game_id IN (920401, 920402, 920403)
        """).fetchall())
        assert kpi_before[920401][0] == 0 and abs(kpi_before[920401][1] - 1.0) < 1e-6, kpi_before
        assert kpi_before[920402][0] == 0 and abs(kpi_before[920402][1] - 0.8) < 1e-6, kpi_before
        print(f'TC4a PASS (Baseline KPIs): pub={tuple(pub_before)}, 920401={kpi_before[920401]}, 920402={kpi_before[920402]}', flush=True)

        # ── TC4b: Change all 3 KPI definitions via SQL UPDATE & rerun incremental ─
        conn.execute("""
            UPDATE dbo.etl_kpi_definitions SET kpi_value = '3', params_json = '{"min_games": 3}', version_no = version_no + 1
            WHERE kpi_code = 'PUBLISHER_AAA_MIN_GAMES';
            UPDATE dbo.etl_kpi_definitions SET kpi_value = 'INCLUDE_100_DISCOUNT', params_json = '{"max_price": 0.99, "include_100_discount": true}', version_no = version_no + 1
            WHERE kpi_code = 'FREE_GAME_RULE';
            UPDATE dbo.etl_kpi_definitions SET kpi_value = 'LAPLACE_SMOOTHED', params_json = '{"min_reviews": 1, "alpha": 1}', version_no = version_no + 1
            WHERE kpi_code = 'POSITIVE_RATIO_FORMULA';
        """)
        execute('tc4b', 'tests/fixtures/demo/tc4_kpi_change.csv')
        rid, steps = latest_run_summary()
        assert json.loads(steps['dbt']['metrics_json'])['recompute_config'] is True, steps['dbt']
        pub_after = conn.execute("SELECT publisher_key, publisher_tier FROM dwh.dim_publisher WHERE publisher_name = N'KPI Demo Pub'").fetchone()
        assert pub_after[0] == pub_before[0] and pub_after[1] == 'AAA', (pub_before, pub_after)
        kpi_after = dict((r[0], tuple(r[1:])) for r in conn.execute("""
            SELECT game_id, is_free, CAST(positive_review_ratio AS FLOAT)
            FROM dbt_staging.stg_steam_games_cleaned WHERE game_id IN (920401, 920402, 920403)
        """).fetchall())
        assert kpi_after[920401][0] == 1 and abs(kpi_after[920401][1] - 0.75) < 1e-6, kpi_after
        assert kpi_after[920402][0] == 1 and abs(kpi_after[920402][1] - (21 / 27)) < 1e-6, kpi_after
        assert kpi_after[920403][0] == 0 and abs(kpi_after[920403][1] - (81 / 102)) < 1e-6, kpi_after
        print(f'TC4b PASS (KPI v2): pub={tuple(pub_after)}, 920401={kpi_after[920401]}, 920402={kpi_after[920402]}', flush=True)

        # ── TC4c: Change POSITIVE_RATIO_FORMULA to STANDARD min_reviews=5 ─────────
        conn.execute("""
            UPDATE dbo.etl_kpi_definitions SET kpi_value = 'STANDARD', params_json = '{"min_reviews": 5, "alpha": 0}', version_no = version_no + 1
            WHERE kpi_code = 'POSITIVE_RATIO_FORMULA';
        """)
        execute('tc4c', 'tests/fixtures/demo/tc4_kpi_change.csv')
        kpi_v3 = dict((r[0], tuple(r[1:])) for r in conn.execute("""
            SELECT game_id, is_free, CAST(positive_review_ratio AS FLOAT)
            FROM dbt_staging.stg_steam_games_cleaned WHERE game_id IN (920401, 920402, 920403)
        """).fetchall())
        assert kpi_v3[920401][1] is None and abs(kpi_v3[920402][1] - 0.8) < 1e-6, kpi_v3
        print(f'TC4c PASS (KPI v3 min_reviews=5): 920401={kpi_v3[920401]}, 920402={kpi_v3[920402]}', flush=True)
        print('ALL DEMO METADATA E2E TESTS PASSED!', flush=True)


def main():
    Base.metadata.create_all(engine)
    db_connection.start_session()
    token = uuid.uuid4().hex[:12]
    database = 'steam_demo_verify_' + token
    master = connect('master')
    try:
        initialize(master, database)
        master.execute('USE master')
        try:
            conn = connect(database)
            try:
                run_all_cases(conn, database, token)
            finally:
                conn.close()
        finally:
            master.execute(f'DROP DATABASE [{database}]')
    finally:
        master.close()


if __name__ == '__main__':
    main()
