"""Integration regression checks against isolated SQL Server schemas.

Run: docker compose run --rm --no-deps --entrypoint python dbt scripts/verify_dbt.py
Only schemas created by this invocation are modified; real source rows stay intact.
"""

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import uuid
from decimal import Decimal

import pyodbc


PROJECT = Path(__file__).resolve().parents[1]


def identifier(value):
    return '[' + value.replace(']', ']]') + ']'


def connect(database):
    # ODBC braces protect semicolons and closing braces in credentials.
    def escaped(value):
        return '{' + str(value).replace('}', '}}') + '}'

    local = os.environ.get('DBT_TARGET', 'dev') == 'local'
    host = os.environ.get('MSSQL_LOCAL_HOST' if local else 'MSSQL_HOST',
                          'localhost' if local else 'sqlserver')
    port = os.environ.get('MSSQL_LOCAL_PORT' if local else 'MSSQL_PORT',
                          '1435' if local else '1433')
    settings = {
        'DRIVER': os.environ.get('MSSQL_DRIVER', 'ODBC Driver 18 for SQL Server'),
        'SERVER': host + ',' + port,
        'DATABASE': database,
        'UID': os.environ.get('MSSQL_USER', 'sa'),
        'PWD': os.environ['MSSQL_PASSWORD'],
        'Encrypt': 'yes', 'TrustServerCertificate': 'yes',
    }
    return pyodbc.connect(';'.join(k + '=' + escaped(v) for k, v in settings.items()),
                          timeout=15, autocommit=True)


def run_dbt(env, *arguments):
    subprocess.run(['dbt', *arguments, '--profiles-dir', str(PROJECT)],
                   cwd=PROJECT, env=env, check=True, timeout=180)


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    database = os.environ.get('DWH_DATABASE', 'steam_games_DWH')
    staging_database = os.environ.get('STAGING_DATABASE', database)
    staging_schema = os.environ.get('STAGING_SCHEMA', 'dbo')
    suffix = uuid.uuid4().hex[:12]
    source_schema = 'dbt_verify_source_' + suffix
    target_schema = 'dbt_verify_target_' + suffix
    conn = connect(database)
    created = []
    temp = tempfile.TemporaryDirectory(prefix='steam_dbt_verify_')
    try:
        for schema in (source_schema, target_schema):
            conn.execute('CREATE SCHEMA ' + identifier(schema))
            created.append(schema)
        source = identifier(source_schema) + '.[stg_steam_games]'
        real_source = '.'.join(map(identifier, (staging_database, staging_schema, 'stg_steam_games')))
        # SELECT INTO copies column types without copying the real PK, so dirty IDs can be tested.
        conn.execute('SELECT TOP (0) * INTO ' + source + ' FROM ' + real_source)
        fixtures = [
            # Paid game: Unicode name, trim/control characters, duplicate classifications.
            dict(appid=910001, name='\t Trò chơi Việt \n', price=25, discount=10,
                 positive=3, negative=1, release_date='2020-02-29', windows=1, mac=0,
                 developers='  Studio Việt  ', genres=' Action,action, RPG, ,None ',
                 categories=' Single-player, Single-player ', tags=' Indie,INDIE, null '),
            dict(appid=910002, name='   ', price=None, positive=None, negative=5,
                 release_date=None, windows=None),
            dict(appid=910003, name='nan', price=-1, positive=-3, negative=2,
                 discount=101, peak_ccu=-1, dlc_count=-1, achievements=-1,
                 recommendations=-1, required_age=-1, average_playtime_forever=-1,
                 average_playtime_two_weeks=-1, median_playtime_forever=-1,
                 median_playtime_two_weeks=-1, metacritic_score=101, user_score=-1),
            dict(appid=910004, name=None, price=0, positive=0, negative=0,
                 discount=-1, mac=1, linux=0, metacritic_score=0, user_score=0),
            dict(appid=910005, name='  NULL  ', price=5, positive=2147483647,
                 negative=2147483647, discount=100, metacritic_score=100, user_score=80),
            dict(appid=910006, name='Valid', price=0, positive=1, negative=None,
                 discount=0, genres='\tRPG\n, Strategy,Strategy'),
            dict(appid=0, name='Invalid ID zero'),
            dict(appid=-1, name='Invalid negative ID'),
            dict(appid=None, name='Missing ID'),
        ]
        # Original source appid is NOT NULL. SELECT INTO preserves nullability;
        # allow NULL here solely to exercise the model's filtering policy.
        conn.execute('ALTER TABLE ' + source + ' ALTER COLUMN [appid] bigint NULL')
        for row in fixtures:
            columns = ','.join(identifier(k) for k in row)
            markers = ','.join('?' for _ in row)
            conn.execute('INSERT INTO ' + source + ' (' + columns + ') VALUES (' + markers + ')',
                         *row.values())
        env = os.environ.copy()
        env.update(STAGING_DATABASE=database, STAGING_SCHEMA=source_schema,
                   DBT_SCHEMA=target_schema, DBT_TARGET_PATH=temp.name + '/target',
                   DBT_LOG_PATH=temp.name + '/logs', DBT_SEND_ANONYMOUS_USAGE_STATS='false')
        # Source not_null intentionally fails on this dirty fixture. Run the models first;
        # evaluate every model/consistency test separately after confirming filtering.
        run_dbt(env, 'run')
        view = identifier(target_schema) + '.[stg_steam_games_cleaned]'
        cursor = conn.execute('SELECT * FROM ' + view)
        columns = [c[0] for c in cursor.description]
        rows = {r[0]: dict(zip(columns, r)) for r in cursor.fetchall()}
        check(set(rows) == set(range(910001, 910007)), 'Invalid keys were not filtered correctly')
        a, b, c, d, e, f = (rows[i] for i in range(910001, 910007))
        check(a['game_title'] == 'Trò chơi Việt' and a['developers'] == 'Studio Việt', 'Unicode/text cleanup')
        check(a['is_title_missing'] == 0 and a['is_free'] == 0, 'Paid/title flags')
        check(a['positive_review_ratio'] == Decimal('0.75'), 'Paid game review ratio')
        check((a['release_year'], a['release_month']) == (2020, 2), 'Date extraction')
        check(b['price'] is None and b['is_free'] is None, 'Unknown price must not imply free')
        check(b['positive_reviews'] == 0 and b['positive_review_ratio'] == 0, 'NULL numerator')
        check(b['release_year'] is None and b['supports_windows'] is None, 'Unknown date/platform')
        for row in (b, c, d, e):
            check(row['game_title'] == 'Unknown game ' + str(row['game_id'])
                  and row['is_title_missing'] == 1, 'Missing title policy')
        for field in ('price', 'is_free', 'positive_reviews', 'positive_review_ratio',
                      'discount_percentage', 'peak_ccu', 'dlc_count', 'achievements_count',
                      'recommendations_count', 'required_age', 'avg_playtime_forever_mins',
                      'avg_playtime_two_weeks_mins', 'median_playtime_forever_mins',
                      'median_playtime_two_weeks_mins', 'metacritic_score', 'user_score'):
            check(c[field] is None, 'Invalid negative/out-of-range field: ' + field)
        check(d['is_free'] == 1 and d['positive_review_ratio'] is None, 'Free/zero reviews')
        check(d['discount_percentage'] is None and d['metacritic_score'] is None, 'Invalid discount/missing score')
        check(e['positive_review_ratio'] == Decimal('0.5'), 'Review sum overflow')
        check(e['discount_percentage'] == 100 and e['metacritic_score'] == 100, 'Upper boundaries')
        check(f['positive_review_ratio'] == 1 and f['negative_reviews'] == 0, 'NULL denominator operand')
        classification = identifier(target_schema) + '.[stg_steam_game_classifications]'
        actual = set(tuple(r) for r in conn.execute('SELECT * FROM ' + classification))
        expected = {(910001, 'genre', 'action'), (910001, 'genre', 'rpg'),
                    (910001, 'category', 'single-player'), (910001, 'tag', 'indie'),
                    (910006, 'genre', 'rpg'), (910006, 'genre', 'strategy')}
        check(actual == expected, 'Classification splitting, blanks, placeholders or duplicates')
        # Remove only the deliberately invalid NULL key, then all source tests must pass too.
        conn.execute('DELETE FROM ' + source + ' WHERE appid IS NULL')
        run_dbt(env, 'test')
        result = json.loads(Path(env['DBT_TARGET_PATH'], 'run_results.json').read_text())
    finally:
        # Names must belong to this invocation; never drop user or source schemas.
        for schema in reversed(created):
            if not re.fullmatch(r'dbt_verify_(source|target)_' + suffix, schema):
                raise RuntimeError('Unsafe cleanup schema')
            objects = conn.execute(
                'SELECT o.name, rtrim(o.type) FROM sys.objects o JOIN sys.schemas s ON s.schema_id=o.schema_id '
                "WHERE s.name=? AND o.type IN ('U','V')", schema).fetchall()
            for name, kind in sorted(objects, key=lambda obj: obj[1] != 'V'):
                conn.execute('DROP ' + ('VIEW ' if kind == 'V' else 'TABLE ')
                             + identifier(schema) + '.' + identifier(name))
            conn.execute('DROP SCHEMA ' + identifier(schema))
        conn.close()
        temp.cleanup()
    print('REGRESSION PASS: 9 dirty fixtures; 6 retained games; 6 classification rows; '
          + str(len(result['results'])) + ' dbt data tests passed; temporary schemas removed.', flush=True)


if __name__ == '__main__':
    main()
