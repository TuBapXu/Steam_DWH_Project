{{ config(materialized='ephemeral') }}

-- Keep the source read-only; normalize all 42 source columns before deriving metrics.
select
    try_convert(bigint, appid) as appid,
    try_convert(date, release_date) as release_date,
    {% for column in [
        'name', 'estimated_owners', 'about_the_game', 'supported_languages',
        'full_audio_languages', 'reviews', 'header_image', 'website',
        'support_url', 'support_email', 'metacritic_url', 'score_rank',
        'notes', 'developers', 'publishers', 'categories', 'genres',
        'tags', 'screenshots', 'movies'
    ] %}
    {{ steam_clean_text(column) }} as {{ column }},
    {% endfor %}
    {% for column in [
        'peak_ccu', 'required_age', 'discount', 'dlc_count', 'metacritic_score',
        'positive', 'negative', 'achievements', 'recommendations',
        'average_playtime_forever', 'average_playtime_two_weeks',
        'median_playtime_forever', 'median_playtime_two_weeks'
    ] %}
    try_convert(bigint, {{ column }}) as {{ column }},
    {% endfor %}
    try_convert(decimal(10, 2), price) as price,
    try_convert(decimal(10, 2), user_score) as user_score,
    {% for column in ['windows', 'mac', 'linux'] %}
    case when try_convert(int, {{ column }}) in (0, 1)
         then try_convert(int, {{ column }}) else null end as {{ column }},
    {% endfor %}
    try_convert(datetime2, _loaded_at) as _loaded_at,
    lower({{ steam_clean_text('_run_mode') }}) as _run_mode
from {{ source('staging_source', 'stg_steam_games') }}
