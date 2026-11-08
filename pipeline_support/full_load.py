"""Bounded-memory, parallel full load into the original staging schema.

run_id identifies an execution only. No source versions or snapshot schema.
"""
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path
import csv
import hashlib
import io
import uuid

import pandas as pd

from .cleaning import clean_frame

CSV_COLUMNS = ['AppID','Name','Release date','Estimated owners','Peak CCU',
    'Required age','Price','Discount','DLC count','About the game','Supported languages',
    'Full audio languages','Reviews','Header image','Website','Support url','Support email',
    'Windows','Mac','Linux','Metacritic score','Metacritic url','User score','Positive','Negative',
    'Score rank','Achievements','Recommendations','Notes','Average playtime forever',
    'Average playtime two weeks','Median playtime forever','Median playtime two weeks',
    'Developers','Publishers','Categories','Genres','Tags','Screenshots','Movies']
SQL_COLUMNS = [c.lower().replace(' ','_') for c in CSV_COLUMNS]+['_loaded_at','_run_mode']


def is_full_plan(value):
    return isinstance(value,dict) and value.get('_chunked_full_load') is True


def make_full_plan(file_path, *, chunk_size=1000, max_workers=2):
    if isinstance(chunk_size,bool) or isinstance(max_workers,bool):
        raise ValueError('chunk_size/max_workers must be integers')
    if ((not isinstance(chunk_size,str) and int(chunk_size)!=chunk_size)
            or (not isinstance(max_workers,str) and int(max_workers)!=max_workers)):
        raise ValueError('chunk_size/max_workers must be integers')
    if not 1<=int(chunk_size)<=10000 or not 1<=int(max_workers)<=4:
        raise ValueError('Use chunk_size 1..10000 and max_workers 1..4')
    source=Path(file_path).resolve(strict=True)
    with source.open(encoding='utf-8-sig',newline='') as stream:
        header=[c.strip() for c in next(csv.reader(stream),[])]
    merged=CSV_COLUMNS[:7]+['DiscountDLC count']+CSV_COLUMNS[9:]
    if header not in (CSV_COLUMNS,merged):
        raise ValueError('CSV header does not match the original Steam 40-column contract')
    stat=source.stat()
    return dict(_chunked_full_load=True,run_id=uuid.uuid4().hex,file_path=str(source),
                chunk_size=int(chunk_size),max_workers=int(max_workers),
                source_size=stat.st_size,source_mtime_ns=stat.st_mtime_ns,
                loaded_at=datetime.now().isoformat(timespec='microseconds'),run_mode='full')


def validate_full_plan(plan):
    checked=make_full_plan(plan['file_path'],chunk_size=plan['chunk_size'],max_workers=plan['max_workers'])
    if (checked['source_size'],checked['source_mtime_ns'])!=(plan['source_size'],plan['source_mtime_ns']):
        raise ValueError('Source file changed after extraction was prepared')
    return plan


def make_incremental_plan(file_path, **options):
    plan = make_full_plan(file_path, **options)
    digest = hashlib.sha256()
    with Path(plan['file_path']).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    plan.update(run_mode='incremental', source_hash=digest.hexdigest())
    return validate_full_plan(plan)


def read_chunks(plan,diagnostics=None, *, progress=None, on_rejected=None, on_chunk_sources=None):
    """Stream CSV records, skipping malformed rows like the legacy full reader.

    pandas' Python chunk iterator can raise csv.Error despite on_bad_lines=skip.
    Use CSV record boundaries, validate the original quoting, and give pandas a
    canonical in-memory chunk to retain its NA/type inference behavior.
    When provided, progress receives rejection details with physical CSV line numbers.
    """
    diagnostics=diagnostics if diagnostics is not None else {}
    diagnostics.update(source_records=0,parser_rejected=0)
    csv.field_size_limit(64*1024*1024)
    class CapturedLines:
        def __init__(self,stream):
            self.stream=stream
            self.lines=[]
        def __iter__(self):
            return self
        def __next__(self):
            line=next(self.stream)
            self.lines.append(line)
            return line
        def take(self):
            result=''.join(self.lines)
            self.lines=[]
            return result
    date_anchor=None
    def dataframe(rows,offset):
        nonlocal date_anchor
        text=io.StringIO(newline='')
        csv.writer(text,lineterminator='\n').writerows(rows)
        text.seek(0)
        frame=pd.read_csv(text,engine='python',on_bad_lines='skip',header=None,names=CSV_COLUMNS,quotechar='"')
        frame.index=pd.RangeIndex(offset,offset+len(frame))
        dates=frame['Release date'].astype(str).str.strip()
        if date_anchor is None:
            first=dates.dropna()
            if not first.empty:
                date_anchor=first.iloc[0]
        if date_anchor is None:
            parsed=pd.to_datetime(dates,errors='coerce')
        else:
            # pandas infers the date format from the first non-null value.
            # Reuse the file's first value so chunk boundaries cannot change it.
            anchored=pd.concat([pd.Series([date_anchor]),dates],ignore_index=True)
            parsed=pd.to_datetime(anchored,errors='coerce').iloc[1:].set_axis(frame.index)
        frame['Release date']=parsed
        return frame
    with Path(plan['file_path']).open(encoding='utf-8-sig',newline='') as stream:
        captured=CapturedLines(stream)
        reader=csv.reader(captured,strict=False)
        next(reader,None)  # Header was validated by make_full_plan.
        captured.take()
        previous_line = reader.line_num
        rows=[]
        sources=[]
        offset=0
        chunk_id=0
        for _ in reader:
            original=captured.take()
            start_line = previous_line + 1
            end_line = reader.line_num
            previous_line = end_line
            diagnostics['source_records']+=1
            if on_rejected or on_chunk_sources:
                source = dict(source_record_no=diagnostics['source_records'],
                              line_start=start_line, line_end=end_line, raw_record=original)
            reason_code = 'INVALID_CSV'
            try:
                strict_values=next(csv.reader(io.StringIO(original,newline=''),strict=True))
                if len(strict_values)>len(CSV_COLUMNS):
                    reason_code = 'TOO_MANY_FIELDS'
                    raise csv.Error(f'Too many fields: expected at most {len(CSV_COLUMNS)}, '
                                    f'found {len(strict_values)}')
            except (csv.Error,StopIteration) as error:
                diagnostics['parser_rejected']+=1
                reason = str(error) or 'No CSV record found'
                if on_rejected:
                    on_rejected(dict(source, chunk_id=None, rejected_stage='PREPARE',
                                     reason_code=reason_code, reason_detail=reason, raw_appid=None))
                if progress is not None:
                    location = (f'line {start_line}' if start_line == end_line
                                else f'lines {start_line}-{end_line}')
                    progress(f"CSV REJECTED | {Path(plan['file_path']).name}:{location} | "
                             f"record {diagnostics['source_records']} | reason: {reason}")
                continue
            # The old pandas reader pads short records with NULL fields.
            rows.append(strict_values+['']*(len(CSV_COLUMNS)-len(strict_values)))
            if on_chunk_sources:
                sources.append(dict(source, raw_appid=rows[-1][0]))
            if len(rows)==plan['chunk_size']:
                frame=dataframe(rows,offset)
                if on_chunk_sources:
                    on_chunk_sources(chunk_id, frame, sources)
                yield chunk_id,frame
                offset+=len(frame)
                chunk_id+=1
                rows=[]
                sources=[]
        if rows:
            frame=dataframe(rows,offset)
            if on_chunk_sources:
                on_chunk_sources(chunk_id, frame, sources)
            yield chunk_id,frame


def prepare_chunk(chunk_id,frame,loaded_at,run_mode='full'):
    keys=pd.to_numeric(frame['AppID'],errors='coerce')
    stats=dict(chunk_id=chunk_id,rows_read=len(frame),bad_keys=int(keys.isna().sum()),
               bad_dates=int(frame['Release date'].isna().sum()))
    cleaned=clean_frame(frame,run_mode=run_mode)
    if not cleaned.empty:
        cleaned['_loaded_at']=pd.Timestamp(loaded_at)
    stats['cleaned_rows']=len(cleaned)
    stats['local_duplicates']=stats['rows_read']-stats['bad_keys']-len(cleaned)
    return cleaned,stats


def run_full_load(plan,store, *, progress=print):
    """Store lock must remain held from buffer creation to atomic publication.

    At most max_workers DataFrames are submitted at once. Failures wait for all
    in-flight writers before dropping the private work table.
    """
    stats=[]
    parser_stats={}
    max_in_flight=0
    run_mode = plan['run_mode']
    def work(chunk_id,frame):
        cleaned,counts=prepare_chunk(chunk_id,frame,plan['loaded_at'],run_mode)
        if not cleaned.empty:
            store.load_chunk(chunk_id,cleaned)
        return counts
    try:
        validate_full_plan(plan)
        store.create_buffer()
        pending=set()
        def collect(futures):
            for future in futures:
                result=future.result()
                stats.append(result)
                progress(f"Chunk {result['chunk_id']}: loaded {result['cleaned_rows']} rows; "
                         f"completed {len(stats)} chunks")
        progress(f"{run_mode.upper()} LOAD: chunk_size={plan['chunk_size']}, max_workers={plan['max_workers']}")
        with ThreadPoolExecutor(max_workers=plan['max_workers'],thread_name_prefix='steam-full') as pool:
            try:
                for chunk_id,frame in read_chunks(plan,parser_stats):
                    pending.add(pool.submit(work,chunk_id,frame))
                    max_in_flight=max(max_in_flight,len(pending))
                    if len(pending)>=plan['max_workers']:
                        done,pending=wait(pending,return_when=FIRST_COMPLETED)
                        collect(done)
                while pending:
                    done,pending=wait(pending,return_when=FIRST_COMPLETED)
                    collect(done)
            except BaseException:
                for future in pending:
                    future.cancel()
                raise
        validate_full_plan(plan)
        totals={name:sum(s[name] for s in stats) for name in
                ('rows_read','bad_keys','bad_dates','cleaned_rows','local_duplicates')}
        totals.update(parser_stats)
        if not totals['cleaned_rows']:
            raise ValueError('No valid records; existing staging is preserved')
        progress('All chunks loaded. Deduplicating AppID across the complete file...')
        accepted=store.count_winners()
        totals['cross_chunk_duplicates']=totals['cleaned_rows']-accepted
        totals['duplicates']=totals['local_duplicates']+totals['cross_chunk_duplicates']
        if totals['rows_read']!=totals['bad_keys']+totals['duplicates']+accepted:
            raise RuntimeError('Source-to-staging reconciliation failed')
        if totals['source_records']!=totals['parser_rejected']+totals['rows_read']:
            raise RuntimeError('CSV parser reconciliation failed')
        if run_mode == 'incremental':
            progress(f'Reconciled {accepted} unique games. Applying staging changes...')
            return store.publish_incremental(plan, accepted, dict(chunks=len(stats), **totals))
        progress(f'Reconciled {accepted} unique games. Replacing staging in one transaction...')
        store.publish(accepted)
        return dict(_full_load_result=True,run_id=plan['run_id'],status='SUCCESS',run_mode='full',
                    records_processed=accepted,chunks=len(stats),max_in_flight=max_in_flight,
                    audit_logged=True,**totals)
    except Exception as exc:
        audited=store.record_failure(str(exc))
        prefix='[FULL_LOAD_AUDITED] ' if audited else ''
        raise RuntimeError(prefix+f"{run_mode.capitalize()} load {plan['run_id']} failed: {exc}") from exc
    finally:
        try:
            store.cleanup()
        except Exception as exc:
            progress(f'Work-table cleanup failed; inspect run {plan["run_id"]}: {exc}')
