-- One row per game/type/value; no arbitrary split of developer/company names.
with expanded as (
    select
        games.game_id,
        lists.classification_type,
        lower({{ steam_clean_text('items.value') }}) as classification_value
    from {{ ref('stg_steam_games_cleaned') }} as games
    cross apply (values
        (N'category', games.categories),
        (N'genre', games.genres),
        (N'tag', games.tags)
    ) as lists(classification_type, list_value)
    cross apply string_split(lists.list_value, N',') as items
)
select distinct game_id, classification_type, classification_value
from expanded
where classification_value is not null
