select game_id, classification_type, classification_value, count_big(*) as occurrences
from {{ ref('stg_steam_game_classifications') }}
group by game_id, classification_type, classification_value
having count_big(*) > 1
