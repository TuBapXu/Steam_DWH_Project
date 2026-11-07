"""Write rejected records independently of the staging publication transaction."""

FIELDS = ('source_record_no', 'line_start', 'line_end', 'chunk_id', 'rejected_stage',
          'reason_code', 'reason_detail', 'raw_appid', 'raw_record')


def read_rejections(connect, run_id):
    connection = connect()
    try:
        cursor = connection.execute("""
            SELECT source_file, source_record_no, line_start, line_end, chunk_id,
                   rejected_stage, reason_code, reason_detail, raw_appid
            FROM dbo.stg_steam_games_rejected
            WHERE run_id = ?
            ORDER BY line_start, source_record_no, rejected_stage, reason_code
        """, run_id)
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor]
    finally:
        connection.close()


def write_rejections(connect, run_id, source_file, records):
    if not records:
        return
    sql = """
        INSERT dbo.stg_steam_games_rejected
            (run_id, source_file, source_record_no, line_start, line_end, chunk_id,
             rejected_stage, reason_code, reason_detail, raw_appid, raw_record)
        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        WHERE NOT EXISTS (
            SELECT 1 FROM dbo.stg_steam_games_rejected WITH (UPDLOCK, HOLDLOCK)
            WHERE run_id=? AND source_record_no=? AND rejected_stage=? AND reason_code=?
        );
    """
    connection = connect()
    try:
        cursor = connection.cursor()
        for record in records:
            cursor.execute(sql, run_id, source_file, *(record[k] for k in FIELDS),
                           run_id, record['source_record_no'], record['rejected_stage'],
                           record['reason_code'])
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
