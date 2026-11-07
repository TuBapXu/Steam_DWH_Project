import ast
from contextlib import contextmanager,redirect_stdout
import csv
import io
import json
from pathlib import Path
import shutil
import sqlite3
import threading
import time
import unittest
import uuid

import pandas as pd

from pipeline_support.cleaning import clean_frame
from pipeline_support.full_load import CSV_COLUMNS,make_full_plan,read_chunks,run_full_load,validate_full_plan

ROOT=Path(__file__).resolve().parents[1]


class SqliteTestStore:
    """Real file transactions offline; SQL Server binding is tested separately."""
    def __init__(self,path,fail_chunk=None):
        self.path=path
        self.fail_chunk=fail_chunk
        self.lock=threading.Lock()
        self.active=0
        self.peak=0
        self.audit=0
        with self.connect() as c:
            c.executescript('CREATE TABLE target(appid INTEGER PRIMARY KEY,payload TEXT);'
                            'CREATE TABLE work(source_row INTEGER PRIMARY KEY,appid INTEGER,payload TEXT);'
                            'CREATE TABLE audit(status TEXT,rows INTEGER);')
            c.execute("INSERT INTO target VALUES (999,'old staging')")

    @contextmanager
    def connect(self):
        connection=sqlite3.connect(self.path,timeout=15)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def create_buffer(self):
        pass

    def load_chunk(self,chunk_id,frame):
        with self.lock:
            self.active+=1
            self.peak=max(self.peak,self.active)
        try:
            time.sleep(0.01)
            if chunk_id==self.fail_chunk:
                raise RuntimeError('Injected chunk failure')
            data=frame.astype(object).where(frame.notna(),None)
            with self.connect() as c:
                for index,row in data.iterrows():
                    c.execute('INSERT INTO work VALUES (?,?,?)',
                              (int(index),int(row['appid']),json.dumps(row.to_dict(),default=str)))
        finally:
            with self.lock:
                self.active-=1

    def count_winners(self):
        with self.connect() as c:
            return c.execute('SELECT COUNT(DISTINCT appid) FROM work').fetchone()[0]

    def publish(self,expected):
        with self.connect() as c:
            c.execute('DELETE FROM target')
            c.execute('INSERT INTO target SELECT b.appid,b.payload FROM work b JOIN '
                      '(SELECT appid,MAX(source_row) winner FROM work GROUP BY appid) w '
                      'ON w.appid=b.appid AND w.winner=b.source_row')
            actual=c.execute('SELECT COUNT(*) FROM target').fetchone()[0]
            if actual!=expected:
                raise RuntimeError('Row count mismatch')
            c.execute("INSERT INTO audit VALUES ('SUCCESS',?)",(actual,))

    def record_failure(self,message):
        with self.connect() as c:
            c.execute("INSERT INTO audit VALUES ('FAILED',0)")
        return True

    def cleanup(self):
        with self.connect() as c:
            c.execute('DELETE FROM work')

    def rows(self):
        with self.connect() as c:
            return c.execute('SELECT appid,payload FROM target ORDER BY appid').fetchall()


class FullLoadTests(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'output/tests'/uuid.uuid4().hex
        self.folder.mkdir(parents=True)

    def tearDown(self):
        if self.folder.parent==ROOT/'output/tests':
            shutil.rmtree(self.folder)

    def write(self,rows,header=None):
        path=self.folder/'games.csv'
        with path.open('w',encoding='utf-8',newline='') as stream:
            writer=csv.writer(stream)
            writer.writerow(header or CSV_COLUMNS)
            for row in rows:
                writer.writerow([row.get(c,'') for c in CSV_COLUMNS] if isinstance(row,dict) else row)
        return path

    def run_load(self,path,workers=2,chunk_size=2,fail_chunk=None):
        plan=make_full_plan(path,max_workers=workers,chunk_size=chunk_size)
        store=SqliteTestStore(self.folder/(uuid.uuid4().hex+'.db'),fail_chunk=fail_chunk)
        with redirect_stdout(io.StringIO()):
            result=run_full_load(plan,store,progress=lambda _:None)
        return result,store

    def fixture(self):
        return [{'AppID':10,'Name':'first','Release date':'2020-01-01','Price':1,'Windows':True},
                {'AppID':20,'Name':'Trò chơi Việt','Release date':'2020-01-02','Price':0},
                {'AppID':10,'Name':'last','Release date':'2020-01-03','Price':9,'Windows':False},
                {'AppID':'','Name':'invalid key'},
                {'AppID':30,'Name':'missing date','Price':-1}]

    def test_business_function_body_matches_legacy_exactly(self):
        original=(ROOT/'tests/fixtures/legacy_validate_clean.py').read_text(encoding='utf-8')
        old=next(n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef) and n.name=='validate_clean')
        current=next(n for n in ast.parse((ROOT/'pipeline_support/cleaning.py').read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef))
        self.assertEqual(ast.dump(ast.Module(body=old.body,type_ignores=[])),ast.dump(ast.Module(body=current.body,type_ignores=[])))

    def test_parallel_load_all_rows_and_cross_chunk_duplicate(self):
        result,store=self.run_load(self.write(self.fixture()))
        self.assertEqual((result['rows_read'],result['bad_keys'],result['duplicates'],result['records_processed']),(5,1,1,3))
        self.assertEqual(json.loads(store.rows()[0][1])['name'],'last')
        self.assertLessEqual(result['max_in_flight'],2)
        self.assertEqual(store.peak,2)
        with store.connect() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM work').fetchone()[0],0)
            self.assertEqual(c.execute('SELECT * FROM audit').fetchall(),[('SUCCESS',3)])

    def test_sequential_and_parallel_match_legacy_full_validation(self):
        path=self.write(self.fixture())
        frame=pd.read_csv(path,engine='python',on_bad_lines='skip',encoding='utf-8',header=0,names=CSV_COLUMNS,quotechar='"')
        frame['Release date']=pd.to_datetime(frame['Release date'].astype(str).str.strip(),errors='coerce')
        with redirect_stdout(io.StringIO()):
            expected=clean_frame(frame,run_mode='full').sort_values('appid')
        for workers in (1,2):
            result,store=self.run_load(path,workers=workers)
            actual=pd.DataFrame([json.loads(row[1]) for row in store.rows()]).sort_values('appid')
            expected_data=expected.astype(object).where(expected.notna(),None)
            expected_data=pd.DataFrame(json.loads(expected_data.to_json(orient='records',date_format='iso')))
            # Compare values except load timestamp and Python datetime serialization.
            columns=[c for c in expected.columns if c not in ('_loaded_at','release_date')]
            pd.testing.assert_frame_equal(actual[columns].reset_index(drop=True),expected_data[columns].reset_index(drop=True),check_dtype=False)

    def test_worker_failure_preserves_previous_staging(self):
        path=self.write(self.fixture())
        plan=make_full_plan(path,chunk_size=1,max_workers=2)
        store=SqliteTestStore(self.folder/'failed.db',fail_chunk=2)
        with redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError,'Injected chunk failure'):
                run_full_load(plan,store,progress=lambda _:None)
        self.assertEqual(store.rows(),[(999,'old staging')])
        self.assertEqual(store.active,0)
        with store.connect() as c:
            self.assertEqual(c.execute('SELECT * FROM audit').fetchall(),[('FAILED',0)])
            self.assertEqual(c.execute('SELECT COUNT(*) FROM work').fetchone()[0],0)

    def test_original_fractional_integer_validation_still_fails(self):
        path=self.write([{'AppID':1,'Name':'bad','User score':'8.5'}])
        plan=make_full_plan(path)
        store=SqliteTestStore(self.folder/'fraction.db')
        with redirect_stdout(io.StringIO()):
            with self.assertRaises(RuntimeError):
                run_full_load(plan,store,progress=lambda _:None)
        self.assertEqual(store.rows(),[(999,'old staging')])

    def test_empty_or_invalid_only_preserves_previous_staging(self):
        for rows in ([],[{'AppID':'bad'}]):
            path=self.write(rows)
            plan=make_full_plan(path)
            store=SqliteTestStore(self.folder/(uuid.uuid4().hex+'.db'))
            with redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError,'No valid records'):
                    run_full_load(plan,store,progress=lambda _:None)
            self.assertEqual(store.rows(),[(999,'old staging')])

    def test_source_change_after_prepare_fails(self):
        path=self.write(self.fixture())
        plan=make_full_plan(path)
        self.write([{'AppID':999}])
        with self.assertRaisesRegex(ValueError,'Source file changed'):
            validate_full_plan(plan)

    def test_bad_header_is_rejected(self):
        path=self.write(self.fixture(),header=list(reversed(CSV_COLUMNS)))
        with self.assertRaisesRegex(ValueError,'header'):
            make_full_plan(path)

    def test_known_merged_header_is_supported(self):
        path=self.write(self.fixture(),header=CSV_COLUMNS[:7]+['DiscountDLC count']+CSV_COLUMNS[9:])
        result,_=self.run_load(path)
        self.assertEqual(result['records_processed'],3)

    def test_unicode_multiline_and_long_text_preserved(self):
        long_text='Mô tả, "quoted"\n'+('x'*5000)
        path=self.write([{'AppID':1,'Name':'Unicode Việt','About the game':long_text}])
        result,store=self.run_load(path)
        self.assertEqual(json.loads(store.rows()[0][1])['about_the_game'],long_text)

    def test_repeated_full_load_replaces_instead_of_appending(self):
        path=self.write(self.fixture())
        store=SqliteTestStore(self.folder/'retry.db')
        with redirect_stdout(io.StringIO()):
            for _ in range(2):
                result=run_full_load(make_full_plan(path,chunk_size=2),store,progress=lambda _:None)
                self.assertEqual(result['records_processed'],3)
                self.assertEqual(len(store.rows()),3)

    def test_configuration_bounds(self):
        path=self.write(self.fixture())
        for chunk,workers in ((0,2),(10001,2),(1000,0),(1000,5),(1.5,2),(True,2)):
            with self.subTest(chunk=chunk,workers=workers):
                with self.assertRaises(ValueError):
                    make_full_plan(path,chunk_size=chunk,max_workers=workers)

    def test_numeric_strings_from_mage_variables(self):
        plan=make_full_plan(self.write(self.fixture()),chunk_size='1000',max_workers='2')
        self.assertEqual((plan['chunk_size'],plan['max_workers']),(1000,2))

    def test_bad_quote_and_extra_fields_are_skipped(self):
        path=self.write([{'AppID':1,'Name':'valid'}])
        with path.open('a',encoding='utf-8') as stream:
            stream.write('2,"bad"x,'+','.join(['extra']*46)+'\n')
            stream.write(','.join(['extra']*41)+'\n')
        result,store=self.run_load(path,chunk_size=1)
        self.assertEqual((result['source_records'],result['parser_rejected'],result['records_processed']),(3,2,1))
        self.assertEqual(store.rows()[0][0],1)

    def test_short_records_use_legacy_null_padding(self):
        path=self.write([{'AppID':1,'Name':'valid'}])
        with path.open('a',encoding='utf-8') as stream:
            stream.write('2,short record\n')
        result,store=self.run_load(path,chunk_size=1)
        self.assertEqual((result['parser_rejected'],result['records_processed']),(0,2))
        short=json.loads(store.rows()[1][1])
        self.assertEqual(short['name'],'short record')
        self.assertIsNone(short['price'])

    def test_date_inference_matches_whole_file_across_chunks(self):
        for first in ('Oct 31, 2024','2024-10-31',''):
            dates=[first,'June 26, 2024','Aug 13, 2024','Jul 28, 2020','2023-12-06','bad date']
            path=self.write([{'AppID':i+1,'Name':'game','Release date':date} for i,date in enumerate(dates)])
            legacy=pd.read_csv(path,engine='python',header=0,names=CSV_COLUMNS,on_bad_lines='skip')
            expected=pd.to_datetime(legacy['Release date'].astype(str).str.strip(),errors='coerce')
            for chunk_size in (1,2,3):
                plan=make_full_plan(path,chunk_size=chunk_size)
                actual=pd.concat([frame['Release date'] for _,frame in read_chunks(plan)],ignore_index=True)
                pd.testing.assert_series_equal(actual,expected,check_dtype=False)


if __name__=='__main__':
    unittest.main()
