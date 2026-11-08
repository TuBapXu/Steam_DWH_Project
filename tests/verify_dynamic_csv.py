"""Read the real CSV through dynamic Extract/Validate without touching SQL."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from pipeline_support.dynamic_chunks import prepare, extract, validate
from pipeline_support.full_load import read_chunks, prepare_chunk


def main():
    chunks, _ = prepare(ROOT, source_file='data/games.csv', run_mode='full', chunk_size=1000)
    plan = chunks[0]['plan']
    totals = dict(rows_read=0, cleaned_rows=0, bad_keys=0, bad_dates=0, local_duplicates=0)
    for (index, original), chunk in zip(read_chunks(plan), chunks):
        with redirect_stdout(io.StringIO()):
            raw, metadata = extract(chunk)
            actual, result = validate(raw, metadata)
            expected, counts = prepare_chunk(index, original, plan['loaded_at'], 'full')
        pd.testing.assert_frame_equal(raw, original)
        pd.testing.assert_frame_equal(actual, expected)
        assert result['counts'] == counts
        for key in totals:
            totals[key] += counts[key]
    manifest = json.loads((Path(chunks[0]['raw_path']).parent / 'manifest.json').read_text())
    assert totals['rows_read'] + manifest['diagnostics']['parser_rejected'] == manifest['diagnostics']['source_records']
    print(json.dumps(dict(status='PASS', chunks=len(chunks), **totals, **manifest['diagnostics'])))


if __name__ == '__main__':
    main()
