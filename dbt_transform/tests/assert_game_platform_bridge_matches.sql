with expected as (
    select g.game_key, os.operating_system_key
    from {{ ref('stg_steam_games_cleaned') }} c
    join {{ ref('dim_game') }} g on g.appid_nk = c.game_id
    cross apply (values (1, c.supports_windows), (2, c.supports_mac), (3, c.supports_linux))
        os(operating_system_key, supported)
    where os.supported = 1
),
missing as (
    select game_key, operating_system_key from expected
    except
    select game_key, operating_system_key from {{ ref('bridge_game_platform') }}
),
extra as (
    select game_key, operating_system_key from {{ ref('bridge_game_platform') }}
    except
    select game_key, operating_system_key from expected
)
select * from missing
union all
select * from extra
