{{
    config(
        materialized         = 'incremental',
        schema               = 'dwh',
        unique_key           = 'publisher_name',
        incremental_strategy = 'delete+insert'
    )
}}

-- Chiều nhà phát hành: trích xuất publisher chính (đầu tiên trong chuỗi CSV)
-- publisher_tier: 'AAA' nếu publisher có >= 10 game, 'Indie' nếu < 10
-- unique_key = publisher_name: đảm bảo mỗi publisher chỉ có 1 dòng
with
-- Bước 1: Trích xuất publisher/developer đầu tiên từ chuỗi CSV
game_publisher as (
    select
        game_id,
        ltrim(rtrim(
            case
                when charindex(',', publishers) > 0
                then left(publishers, charindex(',', publishers) - 1)
                else publishers
            end
        )) as publisher_name,
        ltrim(rtrim(
            case
                when charindex(',', developers) > 0
                then left(developers, charindex(',', developers) - 1)
                else developers
            end
        )) as developer_name
    from {{ ref('stg_steam_games_cleaned') }}
    where publishers is not null
),
-- Bước 2: Đếm số game mỗi publisher để phân tầng AAA / Indie
publisher_game_count as (
    select
        publisher_name,
        count(*) as game_count
    from game_publisher
    group by publisher_name
),
-- Bước 3: Lấy 1 developer đại diện cho mỗi publisher (game đầu tiên theo game_id)
publisher_with_dev as (
    select
        publisher_name,
        developer_name,
        row_number() over (
            partition by publisher_name
            order by game_id
        ) as rn
    from game_publisher
)
select
    row_number() over (order by pwd.publisher_name) as publisher_key,
    pwd.publisher_name,
    pwd.developer_name,
    case
        when pc.game_count >= 10 then 'AAA'
        else 'Indie'
    end                                             as publisher_tier
from publisher_with_dev pwd
join publisher_game_count pc
    on pc.publisher_name = pwd.publisher_name
where pwd.rn = 1

{% if is_incremental() %}
-- Chỉ thêm publisher chưa tồn tại trong bảng đích
and pwd.publisher_name not in (select publisher_name from {{ this }})
{% endif %}
