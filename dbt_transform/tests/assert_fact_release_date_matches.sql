select c.game_id, c.release_date, f.date_key, d.full_date
from {{ ref('stg_steam_games_cleaned') }} c
join {{ ref('dim_game') }} g on g.appid_nk = c.game_id
join {{ ref('fact_game_snapshot') }} f on f.game_key = g.game_key
left join {{ ref('dim_date') }} d on d.date_key = f.date_key
where (c.release_date is not null and
       (d.full_date is null or d.date_key = 0 or d.full_date <> c.release_date))
   or (c.release_date is null and coalesce(f.date_key, -1) <> 0)
