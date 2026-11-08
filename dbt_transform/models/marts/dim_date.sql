{{
    config(
        materialized         = 'incremental',
        schema               = 'dwh',
        unique_key           = 'date_key',
        incremental_strategy = 'delete+insert'
    )
}}

-- Giữ lịch gốc và mở rộng theo ngày phát hành của nguồn.
with
bounds as (
    select
        case when min(release_date) < cast('20100101' as date)
             then min(release_date) else cast('20100101' as date) end as start_date,
        case when max(release_date) > cast('20241231' as date)
             then max(release_date) else cast('20241231' as date) end as end_date
    from {{ source('staging_source', 'stg_steam_games') }}
    where appid > 0
),
l0 as (select 1 as c union all select 1),
l1 as (select 1 as c from l0 a cross join l0 b),
l2 as (select 1 as c from l1 a cross join l1 b),
l3 as (select 1 as c from l2 a cross join l2 b),
l4 as (select 1 as c from l3 a cross join l3 b),  -- 65,536 rows
nums as (
    -- 4,194,304 offsets cover the full SQL Server DATE range.
    select top ((select datediff(day, start_date, end_date) + 1 from bounds))
        row_number() over (order by (select null)) - 1 as n
    from l4 cross join l2 cross join l1
    order by n
),
dates as (
    select dateadd(day, n, start_date) as full_date
    from nums cross join bounds
)
select
    convert(int, convert(char(8), full_date, 112))  as date_key,
    full_date,
    month(full_date)                               as month,
    datepart(quarter, full_date)                   as quarter,
    year(full_date)                                as year,
    case
        when month(full_date) in (3, 4, 5)   then N'Xuan'
        when month(full_date) in (6, 7, 8)   then N'Ha'
        when month(full_date) in (9, 10, 11)  then N'Thu'
        else                                       N'Dong'
    end                                            as season,
    cast(0 as bit)                                 as is_holiday
from dates

{% if is_incremental() %}
-- Chỉ thêm ngày chưa tồn tại trong bảng đích
where convert(int, convert(char(8), full_date, 112))
      not in (select date_key from {{ this }})
{% endif %}

union all
select 0, cast('00010101' as date), 1, 1, 1, N'Unknown', cast(0 as bit)
{% if is_incremental() %}
where not exists (select 1 from {{ this }} where date_key = 0)
{% endif %}
