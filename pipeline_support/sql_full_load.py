"""SQL Server work table and bounded pyodbc array inserts; legacy schema intact."""
from datetime import datetime
import json
import re

from .full_load import SQL_COLUMNS


def identifier(name):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name):
        raise ValueError('Unsafe SQL identifier')
    return '['+name+']'


class SqlFullLoadStore:
    def __init__(self,connection_factory,run_id, *, run_mode='full'):
        if not re.fullmatch(r'[0-9a-f]{32}',run_id):
            raise ValueError('Invalid run identifier')
        self.connect=connection_factory
        self.table='dbo.'+identifier('_steam_full_'+run_id)
        self.run_id=run_id
        self.run_mode=run_mode
        self.main=None
        self.created=False

    def __enter__(self):
        self.main=self.connect()
        try:
            acquire_staging_lock(self.main)
            if self.run_mode != 'incremental':
                require_pending_batch(self.main)
            self.main.commit()
            return self
        except BaseException:
            self.main.close()
            raise

    def __exit__(self,*args):
        self.main.close()

    def create_buffer(self):
        self.main.execute('SELECT TOP(0) '+','.join(identifier(c) for c in SQL_COLUMNS)+
                          ' INTO '+self.table+' FROM dbo.stg_steam_games')
        self.main.execute('ALTER TABLE '+self.table+' ADD __source_row BIGINT NOT NULL')
        self.main.execute('CREATE UNIQUE CLUSTERED INDEX ix_source ON '+self.table+'(__source_row)')
        self.main.commit()  # Make DDL visible to independent worker connections.
        self.created=True

    def load_chunk(self,chunk_id,frame):
        # One connection per chunk: never share a pyodbc connection across threads.
        import pyodbc
        data=frame.astype(object).where(frame.notna(),None)
        rows=[tuple(values)+(int(source_row),) for source_row,values in zip(frame.index,data.values.tolist())]
        statement='INSERT INTO '+self.table+' ('+','.join(identifier(c) for c in SQL_COLUMNS)+',__source_row) VALUES ('+','.join('?' for _ in range(len(SQL_COLUMNS)+1))+')'
        connection=self.connect()
        try:
            try:
                cursor=connection.cursor()
                cursor.fast_executemany=True
                # Array binding can otherwise allocate max_text_width * all rows.
                # Bound each call to <=128 rows and approximately 16 MiB of text.
                widths=[max((len(v[i].encode('utf-16-le')) for v in rows if isinstance(v[i],str)),default=8)
                        for i in range(len(SQL_COLUMNS)+1)]
                batch_size=max(1,min(128,(16*1024*1024)//max(1,sum(widths))))
                for offset in range(0,len(rows),batch_size):
                    batch=rows[offset:offset+batch_size]
                    sizes=[]
                    for index in range(len(SQL_COLUMNS)+1):
                        text=[v[index] for v in batch if isinstance(v[index],str)]
                        sizes.append((pyodbc.SQL_WVARCHAR,max(1,max(len(v.encode('utf-16-le'))//2 for v in text)),0) if text else None)
                    cursor.setinputsizes(sizes)
                    cursor.executemany(statement,batch)
                connection.commit()
            except pyodbc.Error:
                # Roll back the entire chunk BEFORE retrying ordinary binding.
                # Handles driver limitations for NVARCHAR(MAX), NULL and dates.
                connection.rollback()
                cursor=connection.cursor()
                cursor.fast_executemany=False
                cursor.executemany(statement,rows)
                connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def count_winners(self):
        self.main.execute('CREATE NONCLUSTERED INDEX ix_appid ON '+self.table+'(appid,__source_row)')
        self.main.commit()
        return int(self.main.execute('SELECT COUNT_BIG(DISTINCT appid) FROM '+self.table).fetchone()[0])

    def publish(self,expected):
        try:
            self.main.execute('SET XACT_ABORT ON')
            self.main.execute('TRUNCATE TABLE dbo.stg_steam_games')
            columns=','.join(identifier(c) for c in SQL_COLUMNS)
            values=','.join('b.'+identifier(c) for c in SQL_COLUMNS)
            self.main.execute('INSERT INTO dbo.stg_steam_games ('+columns+') SELECT '+values+
                ' FROM '+self.table+' b JOIN (SELECT appid,MAX(__source_row) winner FROM '+self.table+
                ' GROUP BY appid) winners ON winners.appid=b.appid AND winners.winner=b.__source_row')
            actual=self.main.execute('SELECT COUNT_BIG(*) FROM dbo.stg_steam_games').fetchone()[0]
            if actual!=expected or actual==0:
                raise RuntimeError('Staging row count does not match the complete full load')
            self.main.execute('INSERT INTO dbo.etl_audit_log '
                '(pipeline_name,run_date,status,records_processed,error_message) VALUES (?,?,?,?,?)',
                'steam_staging_full',datetime.now(),'SUCCESS',actual,None)
            self.main.commit()
        except BaseException:
            self.main.rollback()
            raise

    def resume_incremental(self, plan):
        pending = pending_batch(self.main)
        if pending is None:
            return None
        if pending.source_hash != plan['source_hash']:
            raise RuntimeError(f'Finish pending batch {pending.batch_id} using its original CSV first')
        result = json.loads(pending.result_json)
        result.update(batch_window(self.main, pending.batch_id), resumed=True)
        return result

    def publish_incremental(self, plan, accepted, totals):
        ensure_incremental_schema(self.main)
        business_columns = SQL_COLUMNS[:-2]
        columns = ','.join(identifier(name) for name in SQL_COLUMNS)
        incoming = ','.join('b.' + identifier(name) for name in SQL_COLUMNS)
        updates = ','.join('s.' + identifier(name) + '=b.' + identifier(name)
                           for name in SQL_COLUMNS if name != 'appid')

        def hash_expression(alias):
            fields = ','.join(f'{alias}.{identifier(name)}' for name in business_columns)
            return (f"HASHBYTES('SHA2_256', (SELECT {fields} FOR JSON PATH, "
                    "INCLUDE_NULL_VALUES, WITHOUT_ARRAY_WRAPPER))")

        self.main.execute('SET XACT_ABORT ON')
        self.main.execute(f'''
            SELECT b.appid, b.__source_row, {hash_expression('b')} AS row_hash
            INTO #incoming_hashes
            FROM {self.table} b
            JOIN (SELECT appid, MAX(__source_row) AS winner FROM {self.table} GROUP BY appid) w
              ON w.winner = b.__source_row
        ''')
        self.main.execute('CREATE UNIQUE CLUSTERED INDEX ix_appid ON #incoming_hashes(appid)')
        self.main.execute(f'''
            UPDATE s SET row_hash = {hash_expression('s')}
            FROM dbo.stg_steam_games s JOIN #incoming_hashes h ON h.appid = s.appid
            WHERE s.row_hash IS NULL
        ''')
        self.main.execute('''
            INSERT dbo.etl_steam_changed_appids (batch_id, appid, is_new)
            SELECT ?, h.appid, CASE WHEN s.appid IS NULL THEN 1 ELSE 0 END
            FROM #incoming_hashes h LEFT JOIN dbo.stg_steam_games s ON s.appid = h.appid
            WHERE s.appid IS NULL OR s.row_hash <> h.row_hash
        ''', self.run_id)
        inserted, updated = self.main.execute('''
            SELECT COUNT_BIG(CASE WHEN is_new=1 THEN 1 END),
                   COUNT_BIG(CASE WHEN is_new=0 THEN 1 END)
            FROM dbo.etl_steam_changed_appids WHERE batch_id=?
        ''', self.run_id).fetchone()
        changes = (f'FROM {self.table} b JOIN #incoming_hashes h ON h.__source_row=b.__source_row '
                   'JOIN dbo.etl_steam_changed_appids d ON d.appid=h.appid AND d.batch_id=?')
        self.main.execute(f'''
            UPDATE s SET {updates}, s.row_hash=h.row_hash
            {changes} JOIN dbo.stg_steam_games s ON s.appid=d.appid
            WHERE d.is_new=0
        ''', self.run_id)
        self.main.execute(f'''
            INSERT dbo.stg_steam_games ({columns}, row_hash)
            SELECT {incoming}, h.row_hash {changes} WHERE d.is_new=1
        ''', self.run_id)
        lset = completed_batch_seq(self.main)
        cet = lset + 1
        result = dict(_staging_result=True, status='SUCCESS', run_mode='incremental',
                      batch_id=self.run_id, lset=lset, cet=cet, records_processed=inserted + updated,
                      inserted=inserted, updated=updated, unchanged=accepted - inserted - updated,
                      audit_logged=True, **totals)
        self.main.execute('''
            INSERT dbo.etl_steam_incremental_batch (batch_id, batch_seq, source_hash, result_json)
            VALUES (?, ?, ?, ?)
        ''', self.run_id, cet, plan['source_hash'], json.dumps(result))
        self.main.execute('''
            INSERT dbo.etl_audit_log (pipeline_name,run_date,status,records_processed,error_message)
            VALUES ('steam_staging_incremental',GETDATE(),'SUCCESS',?,NULL)
        ''', result['records_processed'])
        self.main.commit()
        return result

    def record_failure(self,message):
        try:
            self.main.rollback()
            self.main.execute('INSERT INTO dbo.etl_audit_log '
                '(pipeline_name,run_date,status,records_processed,error_message) VALUES (?,?,?,?,?)',
                f'steam_staging_{self.run_mode}',datetime.now(),'FAILED',0,f'run_id={self.run_id}: {message}')
            self.main.commit()
            return True
        except Exception:
            self.main.rollback()
            return False

    def cleanup(self):
        if self.created:
            self.main.execute('DROP TABLE '+self.table)
            self.main.commit()
            self.created=False


def acquire_staging_lock(connection):
    result=connection.execute("DECLARE @r INT; EXEC @r=sys.sp_getapplock "
        "@Resource='steam_staging_writer',@LockMode='Exclusive',@LockOwner='Session',"
        "@LockTimeout=0; SELECT @r;").fetchone()[0]
    if result<0:
        raise RuntimeError('Another staging load is already running; wait for it to finish')


def ensure_incremental_schema(connection):
    connection.execute('''
        IF COL_LENGTH('dbo.stg_steam_games', 'row_hash') IS NULL
            ALTER TABLE dbo.stg_steam_games ADD row_hash binary(32) NULL;
        IF OBJECT_ID('dbo.etl_steam_incremental_batch', 'U') IS NULL
            CREATE TABLE dbo.etl_steam_incremental_batch (
                batch_id char(32) NOT NULL PRIMARY KEY,
                batch_seq bigint NOT NULL UNIQUE,
                source_hash char(64) NOT NULL,
                result_json nvarchar(max) NOT NULL,
                completed_at datetime2 NULL
            );
        IF OBJECT_ID('dbo.etl_steam_changed_appids', 'U') IS NULL
            CREATE TABLE dbo.etl_steam_changed_appids (
                batch_id char(32) NOT NULL,
                appid bigint NOT NULL,
                is_new bit NOT NULL,
                PRIMARY KEY (batch_id, appid)
            );
    ''')
    if connection.execute(
        "SELECT COL_LENGTH('dbo.etl_steam_incremental_batch','batch_seq')"
    ).fetchone()[0] is None:
        connection.execute('ALTER TABLE dbo.etl_steam_incremental_batch ADD batch_seq bigint NULL')
        # Legacy batches completed serially. A pending batch belongs after them.
        connection.execute('''
            WITH ordered AS (
                SELECT batch_seq, ROW_NUMBER() OVER (
                    ORDER BY CASE WHEN completed_at IS NULL THEN 1 ELSE 0 END,
                             completed_at, batch_id
                ) AS seq
                FROM dbo.etl_steam_incremental_batch
            )
            UPDATE ordered SET batch_seq = seq;
            ALTER TABLE dbo.etl_steam_incremental_batch ALTER COLUMN batch_seq bigint NOT NULL;
            ALTER TABLE dbo.etl_steam_incremental_batch ADD UNIQUE (batch_seq);
        ''')
    connection.commit()


def completed_batch_seq(connection):
    return connection.execute('''
        SELECT COALESCE(MAX(batch_seq),0)
        FROM dbo.etl_steam_incremental_batch WHERE completed_at IS NOT NULL
    ''').fetchone()[0]


def batch_window(connection, batch_id):
    # Also supports retrying a pending batch written before batch_seq existed.
    if connection.execute(
        "SELECT COL_LENGTH('dbo.etl_steam_incremental_batch','batch_seq')"
    ).fetchone()[0] is None:
        ensure_incremental_schema(connection)
    row = connection.execute('''
        SELECT batch_seq FROM dbo.etl_steam_incremental_batch
        WHERE batch_id=? AND completed_at IS NULL
    ''', batch_id).fetchone()
    lset = completed_batch_seq(connection)
    if row is None or row.batch_seq != lset + 1:
        raise RuntimeError('Pending batch is outside the next incremental window')
    return dict(lset=lset, cet=row.batch_seq)


def pending_batch(connection):
    if connection.execute("SELECT OBJECT_ID('dbo.etl_steam_incremental_batch','U')").fetchone()[0] is None:
        return None
    return connection.execute('''
        SELECT batch_id, source_hash, result_json
        FROM dbo.etl_steam_incremental_batch WHERE completed_at IS NULL
    ''').fetchone()


def require_pending_batch(connection, batch_id=None):
    pending = pending_batch(connection)
    if (pending.batch_id if pending else None) != batch_id:
        raise RuntimeError('Pending incremental batch changed. Finish it before another staging run.')
