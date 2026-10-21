select counts.*
from (
    select
        (select count_big(*) from {{ source('staging_source', 'stg_steam_games') }}
         where try_convert(bigint, appid) > 0) as expected_rows,
        (select count_big(*) from {{ ref('stg_steam_games_cleaned') }}) as actual_rows
) as counts
where expected_rows <> actual_rows
