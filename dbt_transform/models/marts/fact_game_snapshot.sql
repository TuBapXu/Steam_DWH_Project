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
with
cleaned as (
    select * from {{ ref('stg_steam_games_cleaned') }}
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
    dim_d.date_key,                             -- FK → dwh.dim_date (NULL nếu ngoài 2010-2024)
    dim_p.platform_key,                         -- FK → dwh.dim_platform
    dim_pub.publisher_key,                      -- FK → dwh.dim_publisher (NULL nếu trống)

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
    on dim_pub.publisher_name = gpp.primary_publisher

-- Dim_Date: LEFT JOIN — NULL nếu ngày phát hành ngoài 2010–2024
left join dim_d
    on dim_d.date_key = try_convert(
        int,
        format(try_convert(date, c.release_date), 'yyyyMMdd')
    )

{% if is_incremental() %}
-- Chỉ xử lý game chưa có trong Fact (tránh duplicate khi chạy lại)
where dim_g.game_key not in (select game_key from {{ this }})
{% endif %}
