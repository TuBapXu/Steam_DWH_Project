{{
    config(
        materialized         = 'incremental',
        schema               = 'dwh',
        unique_key           = 'appid_nk',
        incremental_strategy = 'merge' if env_var('STEAM_CHANGE_BATCH', '') else 'delete+insert',
        merge_exclude_columns = ['game_key']
    )
}}

-- Mỗi dòng là một tựa game duy nhất trên Steam.
-- Cấp surrogate key mới sau khóa lớn nhất đang có để incremental không đánh lại từ 1.
{% set apply_changes = env_var('STEAM_CHANGE_BATCH', '') and is_incremental() %}
with cleaned as (
    select
        c.game_id,
        game_title,
        required_age,
        genres,
        categories,
        supported_languages
    from {{ ref('stg_steam_games_cleaned') }} c
    {% if apply_changes %}
    where {{ steam_changed_game('c.game_id') }}
    {% endif %}
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
        {% if apply_changes %}, existing.game_key as existing_key{% endif %}
    from cleaned c
    {% if apply_changes %}
    left join {{ this }} existing on existing.appid_nk = c.game_id
    {% elif is_incremental() %}
    where not exists (
        select 1
        from {{ this }} existing
        where existing.appid_nk = c.game_id
    )
    {% endif %}
)
select
    {% if apply_changes %}
    coalesce(s.existing_key, cast(m.max_key + row_number() over (
        order by case when s.existing_key is null then 0 else 1 end, s.game_id
    ) as int)) as game_key,
    {% else %}
    cast(m.max_key + row_number() over (order by s.game_id) as int) as game_key,
    {% endif %}
    s.game_id as appid_nk,
    s.game_title as game_name,
    s.required_age,
    s.genres,
    s.categories,
    s.supported_languages
from source_to_load s
cross join max_key m
