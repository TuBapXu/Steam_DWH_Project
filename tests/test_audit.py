"""etl_audit_log writer: parameterised insert, durations, metrics, run context."""
from datetime import datetime
import json
import unittest

from pipeline_support.audit import COLUMNS, INSERT_SQL, run_context, staging_metrics, write_audit


class FakeConnection:
    def __init__(self):
        self.calls, self.commits = [], 0

    def execute(self, sql, *params):
        self.calls.append((sql, params))

    def commit(self):
        self.commits += 1


RUN_ID = 'a' * 32


class AuditWriterTests(unittest.TestCase):
    def test_insert_is_parameterised_and_matches_the_column_list(self):
        connection = FakeConnection()
        write_audit(connection, pipeline_name='steam_dbt_transform', step='dbt', status='SUCCESS',
                    records_processed=10, run_id=RUN_ID, dbt_tests=91,
                    error="it's quoted; DROP TABLE x")
        sql, params = connection.calls[0]
        self.assertEqual(sql, INSERT_SQL)
        self.assertEqual(sql.count('?'), len(COLUMNS))
        self.assertEqual(len(params), len(COLUMNS))
        row = dict(zip(COLUMNS, params))
        self.assertEqual(row['error_message'], "it's quoted; DROP TABLE x")
        self.assertEqual((row['run_id'], row['step'], row['dbt_tests']), (RUN_ID, 'dbt', 91))
        self.assertEqual(row['trigger_name'], 'manual')
        self.assertEqual(connection.commits, 1)

    def test_duration_metrics_and_run_date(self):
        connection = FakeConnection()
        row = write_audit(connection, pipeline_name='steam_staging_full', step='staging',
                          status='FAILED', started_at='2026-11-22T10:00:00',
                          finished_at=datetime(2026, 11, 22, 10, 7, 30),
                          metrics={'source_records': 3, 'when': datetime(2026, 1, 1)}, commit=False)
        self.assertEqual(row['duration_sec'], 450)
        self.assertEqual(row['run_date'], row['finished_at'])
        self.assertEqual(json.loads(row['metrics_json'])['source_records'], 3)
        self.assertEqual(connection.commits, 0)

    def test_invalid_step_or_status_is_rejected_before_writing(self):
        connection = FakeConnection()
        with self.assertRaises(ValueError):
            write_audit(connection, pipeline_name='x', step='unknown', status='SUCCESS')
        with self.assertRaises(ValueError):
            write_audit(connection, pipeline_name='x', step='dbt', status='DONE')
        self.assertEqual(connection.calls, [])

    def test_run_context_follows_plan_staging_and_batch_ids(self):
        chunk = {'plan': {'run_id': RUN_ID, 'run_mode': 'full', 'trigger_name': 'monthly_incremental',
                          'started_at': '2026-11-22T00:00:00'}}
        self.assertEqual(run_context(chunk)['trigger_name'], 'monthly_incremental')
        transform = {'staging': {'batch_id': 'b' * 32, 'run_mode': 'incremental'}}
        self.assertEqual(run_context(transform), {'run_mode': 'incremental', 'run_id': 'b' * 32})
        self.assertNotIn('run_id', run_context({'run_id': 'not-a-run-id'}))
        self.assertEqual(run_context(None), {})

    def test_staging_metrics_for_full_and_incremental(self):
        full = staging_metrics({'run_mode': 'full', 'records_processed': 5, 'parser_rejected': 1,
                                'bad_keys': 2, 'source_records': 8})
        self.assertEqual((full['inserted'], full['updated'], full['unchanged'], full['rejected']),
                         (5, 0, 0, 3))
        incremental = staging_metrics({'run_mode': 'incremental', 'inserted': 1, 'updated': 1,
                                       'unchanged': 1, 'outcome': 'NO_VALID_RECORDS'})
        self.assertEqual((incremental['inserted'], incremental['rejected']), (1, 0))
        self.assertEqual(incremental['metrics']['outcome'], 'NO_VALID_RECORDS')


if __name__ == '__main__':
    unittest.main()
