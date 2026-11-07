import csv
from contextlib import redirect_stdout
import io
from pathlib import Path
import shutil
import unittest
from unittest.mock import Mock
import uuid

import pandas as pd

from pipeline_support.dynamic_chunks import prepare, extract, validate, finalize
from pipeline_support.full_load import CSV_COLUMNS, read_chunks, prepare_chunk


class DynamicChunkTests(unittest.TestCase):
    def setUp(self):
        output = (Path(__file__).resolve().parents[1] / 'output').resolve()
        self.root = output / ('test_dynamic_' + uuid.uuid4().hex)
        self.root.mkdir(parents=True)
        assert self.root.resolve().is_relative_to(output)
        self.addCleanup(shutil.rmtree, self.root)
        with (self.root / 'games.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=CSV_COLUMNS)
            writer.writeheader()
            for appid, name in [(7, 'first'), ('bad', 'invalid'), (8, ''), (7, 'last')]:
                writer.writerow({'AppID': appid, 'Name': name, 'Release date': 'Jan 01, 2020'})

    def prepare(self):
        with redirect_stdout(io.StringIO()):
            return prepare(self.root, source_file='games.csv', chunk_size=2)

    def test_prepare_logs_physical_line_ranges_and_rejection_reasons(self):
        with (self.root / 'games.csv').open('a', newline='', encoding='utf-8') as stream:
            stream.write('9,"bad\nname"x\n')
            stream.write(','.join(['extra'] * 41) + '\n')

        log = io.StringIO()
        with redirect_stdout(log):
            chunks, _ = prepare(self.root, source_file='games.csv', chunk_size=2)

        self.assertEqual(len(chunks), 2)
        self.assertIn("CSV REJECTED | games.csv:lines 6-7 | record 5 | reason: ',' expected", log.getvalue())
        self.assertIn('CSV REJECTED | games.csv:line 8 | record 6 | reason: '
                      'Too many fields: expected at most 40, found 41', log.getvalue())

    def test_round_trip_preserves_validation_and_global_source_order(self):
        chunks, metadata = self.prepare()
        self.assertEqual(len(chunks), 2)
        self.assertEqual(len({m['block_uuid'] for m in metadata}), 2)
        indices = []
        for (index, original), chunk in zip(read_chunks(chunks[0]['plan']), chunks):
            with redirect_stdout(io.StringIO()):
                raw, descriptor = extract(chunk)
                cleaned, result = validate(raw, descriptor)
                expected, stats = prepare_chunk(index, original, chunk['plan']['loaded_at'])
            pd.testing.assert_frame_equal(raw, original)
            pd.testing.assert_frame_equal(cleaned, expected)
            self.assertEqual(result['counts'], stats)
            indices.extend(cleaned.index)
        self.assertEqual(indices, [0, 2, 3])

    def test_reducer_rejects_incomplete_duplicate_and_mixed_receipts_before_sql(self):
        chunks, _ = self.prepare()
        receipts = []
        for chunk in chunks:
            with redirect_stdout(io.StringIO()):
                frame, descriptor = extract(chunk)
                cleaned, result = validate(frame, descriptor)
            receipts.append(dict(result, loaded_rows=len(cleaned)))
        mixed = dict(receipts[1], plan=dict(receipts[1]['plan'], run_id='0' * 32))
        for invalid in ([], receipts[:1], [receipts[0], receipts[0]], [receipts[0], mixed]):
            connection = Mock()
            with self.assertRaises(ValueError):
                finalize(invalid, connection)
            connection.assert_not_called()


if __name__ == '__main__':
    unittest.main()
