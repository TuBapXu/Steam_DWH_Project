{% set recompute = env_var('STEAM_RECOMPUTE_CONFIG', '') != '' %}
{% set change_batch = env_var('STEAM_CHANGE_BATCH', '') != '' %}
{% set aaa_min_games = var('kpi_publisher_aaa_min_games', 10) | int %}
{{
    config(
        materialized          = 'incremental',
        schema                = 'dwh',
        unique_key            = 'publisher_name',
        incremental_strategy  = 'merge' if (change_batch or recompute) else 'delete+insert',
        merge_exclude_columns = ['publisher_key']
    )
}}

-- Chiều nhà phát hành: trích xuất publisher chính (đầu tiên trong chuỗi CSV)
-- publisher_tier: 'AAA' nếu publisher có >= kpi_publisher_aaa_min_games game, 'Indie' nếu < ngưỡng
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
),
publisher_candidates as (
    select
        pwd.publisher_name,
        pwd.developer_name,
        case
            when pc.game_count >= {{ aaa_min_games }} then 'AAA'
            else 'Indie'
        end as publisher_tier
    from publisher_with_dev pwd
    join publisher_game_count pc
        on pc.publisher_name = pwd.publisher_name
    where pwd.rn = 1
),
max_key as (
    {% if is_incremental() %}
    select coalesce(max(publisher_key), 0) as max_key
    from {{ this }}
    {% else %}
    select cast(0 as int) as max_key
    {% endif %}
),
source_to_load as (
    select p.*
        {% if is_incremental() and (change_batch or recompute) %}, existing.publisher_key as existing_key{% endif %}
    from publisher_candidates p
    {% if is_incremental() and (change_batch or recompute) %}
    left join {{ this }} existing
        on existing.publisher_name = p.publisher_name and existing.publisher_key <> 0
    {% elif is_incremental() %}
    where not exists (
        select 1
        from {{ this }} existing
        where existing.publisher_name = p.publisher_name and existing.publisher_key <> 0
    )
    {% endif %}
)
select
    {% if is_incremental() and (change_batch or recompute) %}
    coalesce(s.existing_key, cast(m.max_key + row_number() over (
        order by case when s.existing_key is null then 0 else 1 end, s.publisher_name
    ) as int)) as publisher_key,
    {% else %}
    cast(m.max_key + row_number() over (order by s.publisher_name) as int) as publisher_key,
    {% endif %}
    s.publisher_name,
    s.developer_name,
    s.publisher_tier
from source_to_load s
cross join max_key m

union all
select 0, N'Unknown Publisher', null, N'Unknown'
{% if is_incremental() %}
where not exists (select 1 from {{ this }} where publisher_key = 0)
{% endif %}
