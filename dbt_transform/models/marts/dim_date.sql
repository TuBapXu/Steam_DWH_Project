{{
    config(
        materialized         = 'incremental',
        schema               = 'dwh',
        unique_key           = 'date_key',
        incremental_strategy = 'delete+insert'
    )
}}

-- Tạo date spine từ 2010-01-01 đến 2024-12-31
-- Dùng cross join numbers table thay vì recursive CTE để tránh giới hạn MAXRECURSION
-- incremental: lần đầu INSERT toàn bộ; lần sau chỉ INSERT ngày chưa có
with
l0 as (select 1 as c union all select 1),
l1 as (select 1 as c from l0 a cross join l0 b),
l2 as (select 1 as c from l1 a cross join l1 b),
l3 as (select 1 as c from l2 a cross join l2 b),
l4 as (select 1 as c from l3 a cross join l3 b),  -- 65,536 rows
nums as (
    select row_number() over (order by (select null)) - 1 as n
    from l4
),
dates as (
    select dateadd(day, n, cast('2010-01-01' as date)) as full_date
    from nums
    where dateadd(day, n, cast('2010-01-01' as date)) <= cast('2024-12-31' as date)
)
select
    convert(int, format(full_date, 'yyyyMMdd'))    as date_key,
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
where convert(int, format(full_date, 'yyyyMMdd'))
      not in (select date_key from {{ this }})
{% endif %}
