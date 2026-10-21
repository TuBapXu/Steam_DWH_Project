select game_id
from {{ ref('stg_steam_games_cleaned') }}
where
    (price is null and is_free is not null)
    or (price = 0 and (is_free is null or is_free <> 1))
    or (price > 0 and (is_free is null or is_free <> 0))
    or (release_date is null and (release_year is not null or release_month is not null))
    or (release_date is not null and
        (release_year is null or release_month is null
         or release_year <> year(release_date) or release_month <> month(release_date)))
    or ((positive_reviews is null or negative_reviews is null
         or positive_reviews + negative_reviews = 0) and positive_review_ratio is not null)
    or (positive_reviews + negative_reviews > 0 and
        (positive_review_ratio is null
         or abs(positive_review_ratio - cast(positive_reviews as decimal(28, 10))
                / (positive_reviews + negative_reviews)) > 0.000000001))
