{{
    config(
        materialized         = 'incremental',
        schema               = 'dwh',
        unique_key           = 'appid_nk',
        incremental_strategy = 'delete+insert'
    )
}}

-- Chiều sản phẩm: mỗi dòng = 1 tựa game duy nhất trên Steam
-- Surrogate key: ROW_NUMBER() thay thế IDENTITY (dbt không hỗ trợ IDENTITY)
-- unique_key = appid_nk: khi game có thay đổi thuộc tính → DELETE + INSERT lại
select
    row_number() over (order by game_id)  as game_key,
    game_id                               as appid_nk,
    game_title                            as game_name,
    required_age,
    genres,
    categories,
    supported_languages
from {{ ref('stg_steam_games_cleaned') }}

{% if is_incremental() %}
-- Chỉ xử lý game chưa có hoặc đã thay đổi so với bảng đích
where game_id not in (select appid_nk from {{ this }})
{% endif %}
