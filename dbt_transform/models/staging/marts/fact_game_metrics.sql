{{ config(materialized='table') }}

select
    game_id,
    price,
    discount_percentage,
    positive_reviews,
    negative_reviews,
    (positive_reviews + negative_reviews) as total_reviews,
    positive_review_ratio,
    metacritic_score,
    user_score,
    peak_ccu,
    avg_playtime_forever_mins
from {{ ref('stg_steam_games_cleaned') }}