{{
    config(
        materialized         = 'incremental',
        schema               = 'dwh',
        unique_key           = 'game_key',
        incremental_strategy = 'delete+insert'
    )
}}

-- Bảng Fact dạng Periodic Snapshot — trung tâm của Star Schema
-- Grain: 1 dòng = 1 tựa game tại thời điểm nạp dữ liệu vào DWH
-- Thứ tự load: 4 Dim phải có dữ liệu trước khi chạy model này (dbt tự sắp xếp qua ref())
{% set apply_changes = env_var('STEAM_CHANGE_BATCH', '') and is_incremental() %}
with
cleaned as (
    select s.* from {{ ref('stg_steam_games_cleaned') }} s
    {% if is_incremental() %}
    left join {{ ref('dim_game') }} existing_game
        on existing_game.appid_nk = s.game_id
    left join {{ this }} existing_fact
        on existing_fact.game_key = existing_game.game_key
    where existing_fact.game_key is null
       or coalesce(existing_fact.date_key, -1)
          <> coalesce(convert(int, convert(char(8), s.release_date, 112)), 0)
       or existing_fact.publisher_key is null
    {% if apply_changes %}
       or {{ steam_changed_game('s.game_id') }}
    {% endif %}
    {% endif %}
),
dim_g as (
    select * from {{ ref('dim_game') }}
),
dim_p as (
    select * from {{ ref('dim_platform') }}
),
dim_pub as (
    select * from {{ ref('dim_publisher') }}
),
dim_d as (
    select * from {{ ref('dim_date') }}
),
-- Trích xuất publisher chính để join dim_publisher
game_primary_publisher as (
    select
        game_id,
        ltrim(rtrim(
            case
                when charindex(',', publishers) > 0
                then left(publishers, charindex(',', publishers) - 1)
                else publishers
            end
        )) as primary_publisher
    from cleaned
)
select
    -- ── Foreign Keys ──────────────────────────────────────────────────────
    dim_g.game_key,                             -- PK + FK → dwh.dim_game
    case when c.release_date is null then 0 else dim_d.date_key end as date_key,
    dim_p.platform_key,                         -- FK → dwh.dim_platform
    case when nullif(gpp.primary_publisher, N'') is null then 0
         else dim_pub.publisher_key end as publisher_key,

    -- ── Measures ──────────────────────────────────────────────────────────
    c.price,                                    -- Non-additive: giá bán lẻ (USD)
    c.discount_percentage       as discount,    -- Non-additive: % giảm giá
    c.peak_ccu,                                 -- Semi-additive: CCU cao nhất
    c.positive_reviews,                         -- Additive: lượt review tích cực
    c.negative_reviews,                         -- Additive: lượt review tiêu cực
    c.metacritic_score,                         -- Non-additive: điểm Metacritic (1-100)
    c.user_score,                               -- Non-additive: điểm user
    c.avg_playtime_forever_mins as average_playtime  -- Non-additive: giờ chơi TB (phút)

from cleaned c

-- Dim_Game: INNER JOIN — mọi game hợp lệ đều có trong dim
join dim_g
    on dim_g.appid_nk = c.game_id

-- Dim_Platform: INNER JOIN — dùng COALESCE để map NULL về 0 → khớp 'Unknown'
join dim_p
    on  cast(dim_p.is_windows as int) = coalesce(c.supports_windows, 0)
    and cast(dim_p.is_mac     as int) = coalesce(c.supports_mac,     0)
    and cast(dim_p.is_linux   as int) = coalesce(c.supports_linux,   0)

-- Dim_Publisher: LEFT JOIN — NULL nếu publisher trống
left join game_primary_publisher gpp
    on gpp.game_id = c.game_id
left join dim_pub
    on dim_pub.publisher_name = gpp.primary_publisher and dim_pub.publisher_key <> 0

-- Giữ game chưa có ngày phát hành.
left join dim_d
    on dim_d.full_date = c.release_date and dim_d.date_key <> 0
