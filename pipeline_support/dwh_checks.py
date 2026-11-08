"""Read-only reconciliation between current staging, cleaned games, and DWH."""
import json


TABLES = {
    'staging': 'dbo.stg_steam_games',
    'cleaned': 'dbt_staging.stg_steam_games_cleaned',
    'dim_game': 'dwh.dim_game',
    'dim_platform': 'dwh.dim_platform',
    'dim_publisher': 'dwh.dim_publisher',
    'dim_date': 'dwh.dim_date',
    'fact_game_snapshot': 'dwh.fact_game_snapshot',
}


def staging_signature(connection):
    row = connection.execute('SELECT COUNT_BIG(*), MIN(_loaded_at), MAX(_loaded_at), '
                             'CHECKSUM_AGG(BINARY_CHECKSUM(appid, _loaded_at, _run_mode)) '
                             'FROM dbo.stg_steam_games').fetchone()
    connection.commit()
    return [str(value) if value is not None else None for value in row]


def inspect_dwh(connection, *, expected_full_rows=None, progress=print):
    def scalar(sql):
        return int(connection.execute(sql).fetchone()[0])
    for name in TABLES.values():
        if connection.execute('SELECT OBJECT_ID(?)', name).fetchone()[0] is None:
            raise RuntimeError(f'Missing {name}; run the dbt transform block first')
    counts = {key: scalar('SELECT COUNT_BIG(*) FROM ' + table)
              for key, table in TABLES.items()}
    checks = {
        'empty_staging': int(counts['staging'] == 0),
        'empty_cleaned': int(counts['cleaned'] == 0),
        'platform_count_not_8': int(counts['dim_platform'] != 8),
        'positive_source_count_mismatch': abs(
            scalar('SELECT COUNT_BIG(*) FROM dbo.stg_steam_games WHERE appid > 0') - counts['cleaned']),
    }
    if expected_full_rows is not None:
        checks['full_load_count_mismatch'] = abs(counts['staging'] - int(expected_full_rows))
    queries = {
        'duplicate_staging_keys': '''SELECT COUNT_BIG(*) FROM (
            SELECT appid FROM dbo.stg_steam_games GROUP BY appid HAVING COUNT_BIG(*) > 1) x''',
        'duplicate_game_keys': '''SELECT COUNT_BIG(*) FROM (
            SELECT appid_nk FROM dwh.dim_game GROUP BY appid_nk HAVING COUNT_BIG(*) > 1) x''',
        'duplicate_fact_keys': '''SELECT COUNT_BIG(*) FROM (
            SELECT game_key FROM dwh.fact_game_snapshot GROUP BY game_key HAVING COUNT_BIG(*) > 1) x''',
        'missing_games_in_dim': '''SELECT COUNT_BIG(*) FROM dbt_staging.stg_steam_games_cleaned c
            LEFT JOIN dwh.dim_game g ON g.appid_nk=c.game_id WHERE g.game_key IS NULL''',
        'extra_games_in_dim': '''SELECT COUNT_BIG(*) FROM dwh.dim_game g
            LEFT JOIN dbt_staging.stg_steam_games_cleaned c ON c.game_id=g.appid_nk WHERE c.game_id IS NULL''',
        'missing_games_in_fact': '''SELECT COUNT_BIG(*) FROM dbt_staging.stg_steam_games_cleaned c
            LEFT JOIN dwh.dim_game g ON g.appid_nk=c.game_id
            LEFT JOIN dwh.fact_game_snapshot f ON f.game_key=g.game_key WHERE f.game_key IS NULL''',
        'extra_games_in_fact': '''SELECT COUNT_BIG(*) FROM dwh.fact_game_snapshot f
            LEFT JOIN dwh.dim_game g ON g.game_key=f.game_key
            LEFT JOIN dbt_staging.stg_steam_games_cleaned c ON c.game_id=g.appid_nk WHERE c.game_id IS NULL''',
        'orphan_fact_keys': '''SELECT COUNT_BIG(*) FROM dwh.fact_game_snapshot f
            LEFT JOIN dwh.dim_game g ON g.game_key=f.game_key
            LEFT JOIN dwh.dim_platform p ON p.platform_key=f.platform_key
            LEFT JOIN dwh.dim_date d ON d.date_key=f.date_key
            LEFT JOIN dwh.dim_publisher pub ON pub.publisher_key=f.publisher_key
            WHERE g.game_key IS NULL OR p.platform_key IS NULL
               OR (f.date_key IS NOT NULL AND d.date_key IS NULL)
               OR (f.publisher_key IS NOT NULL AND pub.publisher_key IS NULL)''',
        'fact_measure_mismatches': '''SELECT COUNT_BIG(*) FROM (
            SELECT game_id, price, discount_percentage, peak_ccu, positive_reviews,
                   negative_reviews, metacritic_score, user_score, avg_playtime_forever_mins
            FROM dbt_staging.stg_steam_games_cleaned
            EXCEPT
            SELECT g.appid_nk, f.price, f.discount, f.peak_ccu, f.positive_reviews,
                   f.negative_reviews, f.metacritic_score, f.user_score, f.average_playtime
            FROM dwh.fact_game_snapshot f JOIN dwh.dim_game g ON g.game_key=f.game_key) x''',
        'game_attribute_mismatches': '''SELECT COUNT_BIG(*) FROM (
            SELECT game_id, game_title, required_age, genres, categories, supported_languages
            FROM dbt_staging.stg_steam_games_cleaned
            EXCEPT SELECT appid_nk, game_name, required_age, genres, categories, supported_languages
            FROM dwh.dim_game) x''',
        'platform_mismatches': '''SELECT COUNT_BIG(*)
            FROM dbt_staging.stg_steam_games_cleaned c
            JOIN dwh.dim_game g ON g.appid_nk=c.game_id
            JOIN dwh.fact_game_snapshot f ON f.game_key=g.game_key
            JOIN dwh.dim_platform p ON p.platform_key=f.platform_key
            WHERE CAST(p.is_windows AS int) <> COALESCE(c.supports_windows,0)
               OR CAST(p.is_mac AS int) <> COALESCE(c.supports_mac,0)
               OR CAST(p.is_linux AS int) <> COALESCE(c.supports_linux,0)''',
        'date_mismatches': '''SELECT COUNT_BIG(*)
            FROM dbt_staging.stg_steam_games_cleaned c
            JOIN dwh.dim_game g ON g.appid_nk=c.game_id
            JOIN dwh.fact_game_snapshot f ON f.game_key=g.game_key
            LEFT JOIN dwh.dim_date d ON d.full_date=TRY_CONVERT(date,c.release_date) AND d.date_key<>0
            WHERE COALESCE(f.date_key,-1) <> CASE WHEN c.release_date IS NULL THEN 0
                                                ELSE COALESCE(d.date_key,-1) END''',
    }
    checks.update({name: scalar(sql) for name, sql in queries.items()})
    checks['release_dates_outside_calendar'] = scalar('''SELECT COUNT_BIG(*)
        FROM dbt_staging.stg_steam_games_cleaned c
        LEFT JOIN dwh.dim_date d ON d.full_date=TRY_CONVERT(date,c.release_date) AND d.date_key<>0
        WHERE c.release_date IS NOT NULL AND d.date_key IS NULL''')
    info = {'release_dates_outside_calendar': checks['release_dates_outside_calendar']}
    connection.commit()
    failed = {name: count for name, count in checks.items() if count}
    report = dict(status='FAILED' if failed else 'SUCCESS', row_counts=counts,
                  checks=checks, failed_checks=failed, info=info)
    progress('DWH ROW COUNTS: ' + json.dumps(counts))
    progress('DWH CHECKS: ' + json.dumps(checks))
    progress('DWH INFO: ' + json.dumps(info))
    return report
