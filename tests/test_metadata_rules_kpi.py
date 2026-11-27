from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch
import uuid

from pipeline_support.audit import staging_metrics
from pipeline_support.dbt_runner import build_dbt
from pipeline_support.dynamic_chunks import extract, prepare, validate
from pipeline_support.full_load import prepare_chunk
from pipeline_support.mage_dwh import run_transform
from pipeline_support.metadata_config import (
    DEFAULT_KPI_DEFINITIONS,
    DEFAULT_VALIDATION_RULES,
    build_dbt_vars,
    compute_config_hash,
    evaluate_reject_rules,
    load_kpi_definitions,
    load_validation_rules,
)

ROOT = Path(__file__).resolve().parents[1]


class FakeMetaCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class FakeMetaConnection:
    def __init__(self, rules_rows=None, kpi_rows=None, applied_hash=None):
        self.rules_rows = rules_rows or []
        self.kpi_rows = kpi_rows or []
        self.applied_hash = applied_hash
        self.commits = 0
        self.rollbacks = 0

    def execute(self, sql, *params):
        text = ' '.join(sql.split())
        if "OBJECT_ID('dbo.etl_validation_rules'" in text:
            return FakeMetaCursor([(1,)])
        if "FROM dbo.etl_validation_rules" in text:
            return FakeMetaCursor(self.rules_rows)
        if "OBJECT_ID('dbo.etl_kpi_definitions'" in text:
            return FakeMetaCursor([(1,)])
        if "FROM dbo.etl_kpi_definitions" in text:
            return FakeMetaCursor(self.kpi_rows)
        if "OBJECT_ID('dbo.etl_metadata_state'" in text:
            return FakeMetaCursor([(1,)])
        if "FROM dbo.etl_metadata_state" in text:
            return FakeMetaCursor([(self.applied_hash,)] if self.applied_hash else [])
        if "OBJECT_ID('dbo.etl_steam_incremental_batch'" in text:
            return FakeMetaCursor([(None,)])
        if "sp_getapplock" in text:
            return FakeMetaCursor([(0,)])
        if "FROM dbo.stg_steam_games" in text:
            return FakeMetaCursor([(3, '2026-11-27', '2026-11-27', 123)])
        return FakeMetaCursor([])

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        pass


class MetadataRulesAndKpiTests(unittest.TestCase):
    def setUp(self):
        self.demo_dir = ROOT / 'tests' / 'fixtures' / 'demo'
        self.tmp_root = ROOT / 'output' / 'tests' / ('meta_' + uuid.uuid4().hex)
        self.tmp_root.mkdir(parents=True)
        shutil.copytree(self.demo_dir, self.tmp_root / 'demo')

    def tearDown(self):
        if self.tmp_root.exists():
            shutil.rmtree(self.tmp_root)

    def _rule_rows(self, overrides=None, extra=None):
        overrides = overrides or {}
        rows = []
        for idx, r in enumerate(DEFAULT_VALIDATION_RULES, start=1):
            active = overrides.get(r['rule_code'], r['is_active'])
            rows.append((
                r['rule_code'], r['rule_name'], r['target_column'], r['rule_type'],
                r['params_json'], r['on_fail_action'], active, r['sort_order'],
            ))
        for item in (extra or []):
            rows.append(item)
        return rows

    def test_tc1_valid_and_update_fixtures_parse_cleanly(self):
        for name, expected_rows in [('tc1_valid_incremental.csv', 3), ('tc1b_valid_update.csv', 4)]:
            with redirect_stdout(io.StringIO()):
                chunks, _ = prepare(self.tmp_root, source_file=f'demo/{name}', chunk_size=10)
                total = 0
                for chunk in chunks:
                    raw, desc = extract(chunk)
                    cleaned, res = validate(raw, desc)
                    self.assertEqual(res['counts']['bad_keys'], 0)
                    total += len(cleaned)
                self.assertEqual(total, expected_rows)

    def test_tc2_mixed_invalid_fixture_rejects_parser_and_key_errors_and_nullifies_dirty_cols(self):
        conn = FakeMetaConnection(rules_rows=self._rule_rows())
        # Verify prepare without writing to DB captures rejected_0.json and parser rejects
        with redirect_stdout(io.StringIO()):
            chunks, _ = prepare(self.tmp_root, source_file='demo/tc2_invalid_mixed.csv', chunk_size=10)
            raw, desc = extract(chunks[0])
            cleaned, res = validate(raw, desc)
        # 6 lines in tc2: 2 parser rejected (bad quote, 41 cols), 2 bad AppID, 2 valid (920201, 920203)
        self.assertEqual(res['counts']['bad_keys'], 2)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(list(cleaned['appid']), [920201, 920203])
        # Verify evaluate_reject_rules catches the 2 bad AppID rows
        rules = load_validation_rules(lambda: conn)
        sources = [
            {'source_record_no': i + 1, 'line_start': i + 2, 'line_end': i + 2,
             'raw_appid': str(v) if v is not None else '', 'raw_record': 'x'}
            for i, v in enumerate(raw['AppID'].tolist())
        ]
        mask, recs = evaluate_reject_rules(raw, rules, sources=sources, chunk_id=0)
        self.assertEqual(int(mask.sum()), 2)
        self.assertEqual([r['reason_code'] for r in recs], ['INVALID_APPID', 'MISSING_APPID'])

    def test_tc3_toggle_and_add_rules_without_code_changes(self):
        with redirect_stdout(io.StringIO()):
            chunks, _ = prepare(self.tmp_root, source_file='demo/tc3_rule_toggle.csv', chunk_size=10)
            raw, desc = extract(chunks[0])

        # 1. Default rules: 4 rows pass, negative price & invalid discount nullified
        default_rules = load_validation_rules(None)
        cleaned_default, stats_default = prepare_chunk(0, raw, '2026-11-27T00:00:00', 'incremental', rules=default_rules)
        self.assertEqual(len(cleaned_default), 4)
        self.assertEqual(stats_default['rule_rejected'], 0)
        neg_row = cleaned_default[cleaned_default['appid'] == 920302].iloc[0]
        self.assertTrue(neg_row['price'] is None or str(neg_row['price']) == 'nan')

        # 2. Enable REJECT_NEGATIVE_PRICE and REQUIRE_GAME_NAME in metadata DB -> 2 rows rejected
        conn_strict = FakeMetaConnection(rules_rows=self._rule_rows(extra=[
            ('REJECT_NEGATIVE_PRICE', 'Chan gia am', 'Price', 'MIN_VALUE', '{"min": 0}', 'REJECT_ROW', 1, 60),
            ('REQUIRE_GAME_NAME', 'Bat buoc ten game', 'Name', 'REQUIRED', '{"disallow_placeholders": ["nan"]}', 'REJECT_ROW', 1, 70),
        ]))
        strict_rules = load_validation_rules(lambda: conn_strict)
        cleaned_strict, stats_strict = prepare_chunk(0, raw, '2026-11-27T00:00:00', 'incremental', rules=strict_rules)
        self.assertEqual(stats_strict['rule_rejected'], 2)
        self.assertEqual(list(cleaned_strict['appid']), [920301, 920304])
        metrics = staging_metrics(dict(stats_strict, parser_rejected=0))
        self.assertEqual(metrics['rejected'], 2)

        # 3. Add brand-new custom rule MAX_PRICE_10 -> rejects 920301 (Price=12.99)
        conn_custom = FakeMetaConnection(rules_rows=self._rule_rows(extra=[
            ('MAX_PRICE_10', 'Gia toi da 10', 'Price', 'MAX_VALUE', '{"max": 10}', 'REJECT_ROW', 1, 80),
        ]))
        custom_rules = load_validation_rules(lambda: conn_custom)
        cleaned_custom, stats_custom = prepare_chunk(0, raw, '2026-11-27T00:00:00', 'incremental', rules=custom_rules)
        self.assertEqual(stats_custom['rule_rejected'], 1)
        self.assertNotIn(920301, list(cleaned_custom['appid']))

        # 4. Disable PRICE_NON_NEGATIVE NULLIFY rule -> negative price -5.00 passes through untouched
        conn_relaxed = FakeMetaConnection(rules_rows=self._rule_rows(overrides={'PRICE_NON_NEGATIVE': False}))
        relaxed_rules = load_validation_rules(lambda: conn_relaxed)
        cleaned_relaxed, _ = prepare_chunk(0, raw, '2026-11-27T00:00:00', 'incremental', rules=relaxed_rules)
        self.assertEqual(float(cleaned_relaxed[cleaned_relaxed['appid'] == 920302].iloc[0]['price']), -5.0)

    def test_tc4_kpi_definitions_build_dbt_vars_and_trigger_recompute(self):
        # Verify tc4 fixture parses cleanly
        with redirect_stdout(io.StringIO()):
            chunks, _ = prepare(self.tmp_root, source_file='demo/tc4_kpi_change.csv', chunk_size=10)
            raw, desc = extract(chunks[0])
            cleaned, _ = validate(raw, desc)
        self.assertEqual(len(cleaned), 3)

        # Load modified KPIs from metadata DB
        conn = FakeMetaConnection(
            rules_rows=self._rule_rows(),
            kpi_rows=[
                ('PUBLISHER_AAA_MIN_GAMES', 'AAA threshold', 'dim_publisher', 'THRESHOLD', '3', '{"min_games": 3}', 2),
                ('FREE_GAME_RULE', 'Free game', 'stg_steam_games_cleaned', 'FORMULA_VARIANT',
                 'INCLUDE_100_DISCOUNT', '{"max_price": 0.99, "include_100_discount": true}', 2),
                ('POSITIVE_RATIO_FORMULA', 'Ratio', 'stg_steam_games_cleaned', 'FORMULA_VARIANT',
                 'LAPLACE_SMOOTHED', '{"min_reviews": 5, "alpha": 1}', 2),
            ],
            applied_hash='old_hash_value',
        )
        rules = load_validation_rules(conn)
        kpis = load_kpi_definitions(conn)
        dbt_vars = build_dbt_vars(rules, kpis)
        self.assertEqual(dbt_vars['kpi_publisher_aaa_min_games'], 3)
        self.assertEqual(dbt_vars['kpi_free_max_price'], 0.99)
        self.assertTrue(dbt_vars['kpi_free_include_100_discount'])
        self.assertEqual(dbt_vars['kpi_positive_ratio_formula'], 'LAPLACE_SMOOTHED')
        self.assertEqual(dbt_vars['kpi_positive_ratio_min_reviews'], 5)
        self.assertEqual(dbt_vars['kpi_positive_ratio_alpha'], 1.0)
        self.assertNotEqual(
            compute_config_hash(rules, kpis),
            compute_config_hash(DEFAULT_VALIDATION_RULES, DEFAULT_KPI_DEFINITIONS),
        )

        # Verify run_transform passes STEAM_RECOMPUTE_CONFIG='1' and --vars to build_dbt
        captured = {}

        def fake_build_dbt(project_root, environment, **kwargs):
            captured['env'] = environment
            captured['vars'] = kwargs.get('vars')
            return {'status': 'SUCCESS', 'models': 9, 'tests': 91, 'total': 100, 'artifact_dir': str(self.tmp_root)}

        with patch('pipeline_support.mage_dwh.build_dbt', side_effect=fake_build_dbt):
            res = run_transform(
                {'_full_load_result': True, 'status': 'SUCCESS', 'records_processed': 3},
                project_root=self.tmp_root,
                connect=lambda: conn,
                environment={},
                progress=lambda _: None,
            )
        self.assertTrue(res['recompute_config'])
        self.assertEqual(captured['env']['STEAM_RECOMPUTE_CONFIG'], '1')
        self.assertEqual(captured['vars']['kpi_publisher_aaa_min_games'], 3)

    def test_dbt_runner_passes_vars_flag_only_when_provided(self):
        project = self.tmp_root / 'dbt_transform'
        project.mkdir(parents=True)
        (project / 'dbt_project.yml').write_text('name: test', encoding='utf-8')
        fake_script = self.tmp_root / 'fake_dbt.py'
        fake_script.write_text(
            "import json, os, pathlib, sys\n"
            "t = pathlib.Path(os.environ['DBT_TARGET_PATH']); t.mkdir(parents=True, exist_ok=True)\n"
            "(t/'run_results.json').write_text(json.dumps({'results':[{'unique_id':'model.x','status':'success'},{'unique_id':'test.x','status':'pass'}]}))\n",
            encoding='utf-8',
        )
        seen_cmds = []
        import subprocess
        orig_popen = subprocess.Popen

        def capture_popen(cmd, **kwargs):
            seen_cmds.append(cmd)
            return orig_popen(['python', str(fake_script), *cmd[1:]], **kwargs)

        with patch('pipeline_support.dbt_runner.subprocess.Popen', side_effect=capture_popen):
            build_dbt(self.tmp_root, {}, executable='fake-dbt', vars={'kpi_publisher_aaa_min_games': 5},
                      exclude='tag:demo_heavy', threads=4, progress=lambda _: None)
        self.assertIn('--vars', seen_cmds[0])
        self.assertIn('--exclude', seen_cmds[0])
        self.assertEqual(seen_cmds[0][seen_cmds[0].index('--exclude') + 1], 'tag:demo_heavy')
        self.assertEqual(seen_cmds[0][seen_cmds[0].index('--threads') + 1], '4')
        idx = seen_cmds[0].index('--vars')
        self.assertEqual(json.loads(seen_cmds[0][idx + 1]), {'kpi_publisher_aaa_min_games': 5})


if __name__ == '__main__':
    unittest.main()
