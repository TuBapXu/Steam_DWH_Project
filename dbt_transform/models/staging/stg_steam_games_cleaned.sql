with standardized as (
    select * from {{ ref('stg_steam_games_standardized') }}
),
cleaned as (
    select
        appid as game_id,
        coalesce(name, N'Unknown game ' + convert(nvarchar(30), appid)) as game_title,
        case when name is null then 1 else 0 end as is_title_missing,
        release_date,
        year(release_date) as release_year,
        month(release_date) as release_month,
        {{ steam_nonnegative('price', 'decimal(10, 2)', false) }} as price,
        case when discount between 0 and 100 then cast(discount as int)
             else null end as discount_percentage,
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
        case when metacritic_score between 1 and 100 then cast(metacritic_score as int)
             else null end as metacritic_score,
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
    case when price = 0 then 1 when price > 0 then 0 else null end as is_free,
    case when positive_reviews + negative_reviews > 0
         then cast(cast(positive_reviews as decimal(28, 10))
                   / (positive_reviews + negative_reviews) as decimal(19, 10))
         else null end as positive_review_ratio
from cleaned
