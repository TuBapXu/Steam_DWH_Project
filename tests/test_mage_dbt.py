"""Process-level tests: stream logs, fail closed, timeout, isolate artifacts."""
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
from unittest.mock import patch
import uuid

from pipeline_support.dbt_runner import build_dbt
from pipeline_support.mage_dwh import run_transform, check_results

ROOT = Path(__file__).resolve().parents[1]
FAKE = '''import json, os, pathlib, sys, time
mode = os.environ.get('FAKE_MODE', 'pass')
print('dbt log: ' + os.environ.get('MSSQL_PASSWORD', ''), flush=True)
if mode == 'slow': time.sleep(30)
if mode == 'error': sys.exit(2)
if mode == 'missing': sys.exit(0)
target = pathlib.Path(os.environ['DBT_TARGET_PATH'])
target.mkdir(parents=True, exist_ok=True)
results = [{'unique_id':'model.steam_dwh.dim_game','status':'success'}]
if mode != 'no_tests':
    results.append({'unique_id':'test.steam_dwh.unique_game',
                    'status':'fail' if mode == 'fail_test' else 'pass'})
(target/'run_results.json').write_text(json.dumps({'results':results}))
'''


class MageDbtTests(unittest.TestCase):
    def setUp(self):
        self.root = ROOT / 'output' / 'tests' / uuid.uuid4().hex
        project = self.root / 'dbt_transform'
        project.mkdir(parents=True)
        (project / 'dbt_project.yml').write_text('name: test')
        self.fake = self.root / 'fake_dbt.py'
        self.fake.write_text(FAKE)
        self.logs = []

    def tearDown(self):
        if self.root.resolve().parent == (ROOT / 'output' / 'tests').resolve():
            shutil.rmtree(self.root)

    def run_build(self, mode='pass', timeout=15):
        original = subprocess.Popen
        def launch(command, **kwargs):
            self.assertEqual(command[1], 'build')
            self.assertNotIn('--full-refresh', command)
            return original([sys.executable, str(self.fake), *command[1:]], **kwargs)
        with patch('pipeline_support.dbt_runner.subprocess.Popen', side_effect=launch):
            return build_dbt(self.root, {'FAKE_MODE': mode, 'MSSQL_PASSWORD': 'secret_for_test'},
                             executable='fake-dbt', timeout_seconds=timeout,
                             progress=self.logs.append)

    def test_success_streams_logs_redacts_password_and_counts_results(self):
        report = self.run_build()
        self.assertEqual((report['models'], report['tests'], report['total']), (1, 1, 2))
        self.assertIn('[REDACTED]', '\n'.join(self.logs))
        self.assertNotIn('secret_for_test', '\n'.join(self.logs))

    def test_exit_zero_with_failed_test_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'unique_game: fail'):
            self.run_build('fail_test')

    def test_nonzero_exit_is_rejected_and_redacted(self):
        with self.assertRaisesRegex(RuntimeError, 'exit 2') as error:
            self.run_build('error')
        self.assertNotIn('secret_for_test', str(error.exception))

    def test_missing_artifact_cannot_reuse_previous_success(self):
        self.run_build()
        with self.assertRaisesRegex(RuntimeError, 'without run_results.json'):
            self.run_build('missing')

    def test_empty_test_selection_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'empty build/test results'):
            self.run_build('no_tests')

    def test_timeout_terminates_the_child_process(self):
        with self.assertRaisesRegex(RuntimeError, 'exceeded 1 seconds'):
            self.run_build('slow', timeout=1)

    def test_artifacts_are_private_for_every_invocation(self):
        first = self.run_build()
        second = self.run_build()
        self.assertNotEqual(first['artifact_dir'], second['artifact_dir'])

    def test_failed_upstream_is_rejected_before_database_access(self):
        def forbidden():
            self.fail('Invalid upstream must not open a database connection')
        with self.assertRaises(ValueError):
            run_transform({'status':'FAILED'}, project_root=self.root,
                          connect=forbidden, environment={})
        with self.assertRaises(ValueError):
            check_results({'status':'FAILED'}, connect=forbidden)


if __name__ == '__main__':
    unittest.main()
