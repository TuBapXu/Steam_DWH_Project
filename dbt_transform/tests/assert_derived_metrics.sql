{% set free_max_price = var('kpi_free_max_price', 0) %}
{% set free_include_100 = var('kpi_free_include_100_discount', false) %}
{% set ratio_formula = var('kpi_positive_ratio_formula', 'STANDARD') %}
{% set ratio_min_reviews = var('kpi_positive_ratio_min_reviews', 1) | int %}
{% set ratio_alpha = var('kpi_positive_ratio_alpha', 0) %}

select game_id
from {{ ref('stg_steam_games_cleaned') }}
where
    ((price is null or price < 0) and is_free is not null)
    or (price >= 0 and (price <= cast({{ free_max_price }} as decimal(10, 2)) {% if free_include_100 %}or discount_percentage = 100{% endif %}) and (is_free is null or is_free <> 1))
    or (price > cast({{ free_max_price }} as decimal(10, 2)) {% if free_include_100 %}and coalesce(discount_percentage, 0) <> 100{% endif %} and (is_free is null or is_free <> 0))
    or (release_date is null and (release_year is not null or release_month is not null))
    or (release_date is not null and
        (release_year is null or release_month is null
         or release_year <> year(release_date) or release_month <> month(release_date)))
    or ((positive_reviews is null or negative_reviews is null
         or positive_reviews + negative_reviews < {{ ratio_min_reviews }}
         or positive_reviews + negative_reviews = 0) and positive_review_ratio is not null)
    {% if ratio_formula == 'LAPLACE_SMOOTHED' %}
    or (positive_reviews + negative_reviews >= {{ ratio_min_reviews }}
        and positive_reviews + negative_reviews + 2.0 * cast({{ ratio_alpha }} as decimal(28, 10)) > 0 and
        (positive_review_ratio is null
         or abs(positive_review_ratio - (cast(positive_reviews as decimal(28, 10)) + cast({{ ratio_alpha }} as decimal(28, 10)))
                / (positive_reviews + negative_reviews + 2.0 * cast({{ ratio_alpha }} as decimal(28, 10)))) > 0.000000001))
    {% else %}
    or (positive_reviews + negative_reviews >= {{ ratio_min_reviews }}
        and positive_reviews + negative_reviews > 0 and
        (positive_review_ratio is null
         or abs(positive_review_ratio - cast(positive_reviews as decimal(28, 10))
                / (positive_reviews + negative_reviews)) > 0.000000001))
    {% endif %}
