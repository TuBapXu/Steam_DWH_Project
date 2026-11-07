{{ config(
    materialized='table',
    as_columnstore=false,
    post_hook=[
        "alter table {{ this }} alter column game_key int not null",
        "alter table {{ this }} alter column operating_system_key int not null",
        "alter table {{ this }} add primary key (game_key, operating_system_key)",
        "alter table {{ this }} add foreign key (game_key) references {{ ref('dim_game') }} (game_key)",
        "alter table {{ this }} add foreign key (operating_system_key) references {{ ref('dim_operating_system') }} (operating_system_key)"
    ]
) }}

-- Rebuild relationships from the current fact so platform removals also take effect.
select f.game_key, os.operating_system_key
from {{ ref('fact_game_snapshot') }} f
join {{ ref('dim_platform') }} p on p.platform_key = f.platform_key
cross join {{ ref('dim_operating_system') }} os
where (os.operating_system_key = 1 and p.is_windows = 1)
   or (os.operating_system_key = 2 and p.is_mac = 1)
   or (os.operating_system_key = 3 and p.is_linux = 1)
