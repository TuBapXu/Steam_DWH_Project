{% set change_batch = env_var('STEAM_CHANGE_BATCH', '') %}
{% set recompute = env_var('STEAM_RECOMPUTE_CONFIG', '') != '' %}
{% set enforce_price = var('rule_price_non_negative', true) %}
{% set enforce_discount = var('rule_discount_range', true) %}
{% set enforce_metacritic = var('rule_metacritic_range', true) %}
{% set free_max_price = var('kpi_free_max_price', 0) %}
{% set free_include_100 = var('kpi_free_include_100_discount', false) %}
{% set ratio_formula = var('kpi_positive_ratio_formula', 'STANDARD') %}
{% set ratio_min_reviews = var('kpi_positive_ratio_min_reviews', 1) | int %}
{% set ratio_alpha = var('kpi_positive_ratio_alpha', 0) %}
{% if change_batch and not recompute %}
    {{ config(materialized='incremental', unique_key='game_id', incremental_strategy='delete+insert') }}
{% endif %}

with standardized as (
    select s.* from {{ ref('stg_steam_games_standardized') }} s
    {% if change_batch and is_incremental() and not recompute %}
    where {{ steam_changed_game('s.appid') }}
    {% endif %}
),
cleaned as (
    select
        appid as game_id,
        coalesce(name, N'Unknown game ' + convert(nvarchar(30), appid)) as game_title,
        case when name is null then 1 else 0 end as is_title_missing,
        release_date,
        year(release_date) as release_year,
        month(release_date) as release_month,
        {% if enforce_price %}
        {{ steam_nonnegative('price', 'decimal(10, 2)', false) }} as price,
        {% else %}
        cast(price as decimal(10, 2)) as price,
        {% endif %}
        {% if enforce_discount %}
        case when discount between 0 and 100 then cast(discount as int)
             else null end as discount_percentage,
        {% else %}
        cast(discount as int) as discount_percentage,
        {% endif %}
        {{ steam_nonnegative('required_age', 'bigint', false) }} as required_age,
        {% for source_column, output_column in [
            ('positive', 'positive_reviews'), ('negative', 'negative_reviews'),
            ('dlc_count', 'dlc_count'), ('achievements', 'achievements_count'),
            ('recommendations', 'recommendations_count'), ('peak_ccu', 'peak_ccu'),
            ('average_playtime_forever', 'avg_playtime_forever_mins'),
            ('average_playtime_two_weeks', 'avg_playtime_two_weeks_mins'),
            ('median_playtime_forever', 'median_playtime_forever_mins'),
            ('median_playtime_two_weeks', 'median_playtime_two_weeks_mins')
        ] %}
        {{ steam_nonnegative(source_column) }} as {{ output_column }},
        {% endfor %}
        {% if enforce_metacritic %}
        case when metacritic_score between 1 and 100 then cast(metacritic_score as int)
             else null end as metacritic_score,
        {% else %}
        cast(metacritic_score as int) as metacritic_score,
        {% endif %}
        case when user_score > 0 then user_score else null end as user_score,
        windows as supports_windows,
        mac as supports_mac,
        linux as supports_linux,
        {% for column in [
            'estimated_owners', 'about_the_game', 'supported_languages',
            'full_audio_languages', 'reviews', 'header_image', 'website',
            'support_url', 'support_email', 'metacritic_url', 'score_rank',
            'notes', 'developers', 'publishers', 'categories', 'genres',
            'tags', 'screenshots', 'movies', '_loaded_at', '_run_mode'
        ] %}
        {{ column }}{% if not loop.last %},{% endif %}
        {% endfor %}
    from standardized
    where appid > 0
)
select
    *,
    case
        when price is null or price < 0 then null
        when price <= cast({{ free_max_price }} as decimal(10, 2))
             {% if free_include_100 %}or discount_percentage = 100{% endif %} then 1
        else 0
    end as is_free,
    {% if ratio_formula == 'LAPLACE_SMOOTHED' %}
    case when positive_reviews + negative_reviews >= {{ ratio_min_reviews }}
              and positive_reviews + negative_reviews + 2.0 * cast({{ ratio_alpha }} as decimal(28, 10)) > 0
         then cast((cast(positive_reviews as decimal(28, 10)) + cast({{ ratio_alpha }} as decimal(28, 10)))
                   / (positive_reviews + negative_reviews + 2.0 * cast({{ ratio_alpha }} as decimal(28, 10))) as decimal(19, 10))
         else null end as positive_review_ratio
    {% else %}
    case when positive_reviews + negative_reviews >= {{ ratio_min_reviews }}
              and positive_reviews + negative_reviews > 0
         then cast(cast(positive_reviews as decimal(28, 10))
                   / (positive_reviews + negative_reviews) as decimal(19, 10))
         else null end as positive_review_ratio
    {% endif %}
from cleaned
