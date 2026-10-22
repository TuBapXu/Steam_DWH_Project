{{ config(materialized='table') }}

select
    game_id,
    game_title,
    is_free,
    release_year,
    release_month,
    required_age,
    supports_windows,
    supports_mac,
    supports_linux,
    developers,
    publishers
from {{ ref('stg_steam_games_cleaned') }}