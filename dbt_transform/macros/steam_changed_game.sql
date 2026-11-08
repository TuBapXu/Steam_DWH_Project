{% macro steam_changed_game(game_id) %}
    {% set source_database = adapter.quote(source('staging_source', 'stg_steam_games').database) %}
    exists (
        select 1
        from {{ source_database }}.dbo.etl_steam_changed_appids delta
        join {{ source_database }}.dbo.etl_steam_incremental_batch batch
          on batch.batch_id = delta.batch_id
        where delta.batch_id = '{{ env_var("STEAM_CHANGE_BATCH", "") }}'
          and batch.batch_seq > {{ env_var("STEAM_CHANGE_LSET", "0") | int }}
          and batch.batch_seq <= {{ env_var("STEAM_CHANGE_CET", "0") | int }}
          and delta.appid = {{ game_id }}
    )
{% endmacro %}
