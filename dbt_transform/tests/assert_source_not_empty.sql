-- Avoid reporting success when the staging dataset has not been loaded.
select count_big(*) as source_rows
from {{ source('staging_source', 'stg_steam_games') }}
having count_big(*) = 0
