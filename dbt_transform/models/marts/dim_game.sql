{{
    config(
        materialized         = 'incremental',
        schema               = 'dwh',
        unique_key           = 'appid_nk',
        incremental_strategy = 'delete+insert'
    )
}}

-- Mỗi dòng là một tựa game duy nhất trên Steam.
-- Cấp surrogate key mới sau khóa lớn nhất đang có để incremental không đánh lại từ 1.
with cleaned as (
    select
        game_id,
        game_title,
        required_age,
        genres,
        categories,
        supported_languages
    from {{ ref('stg_steam_games_cleaned') }}
),
max_key as (
    {% if is_incremental() %}
    select coalesce(max(game_key), 0) as max_key
    from {{ this }}
    {% else %}
    select cast(0 as int) as max_key
    {% endif %}
),
source_to_load as (
    select c.*
    from cleaned c
    {% if is_incremental() %}
    where not exists (
        select 1
        from {{ this }} existing
        where existing.appid_nk = c.game_id
    )
    {% endif %}
)
select
    cast(m.max_key + row_number() over (order by s.game_id) as int) as game_key,
    s.game_id as appid_nk,
    s.game_title as game_name,
    s.required_age,
    s.genres,
    s.categories,
    s.supported_languages
from source_to_load s
cross join max_key m
