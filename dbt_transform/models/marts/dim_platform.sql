{{
    config(
        materialized         = 'incremental',
        schema               = 'dwh',
        unique_key           = 'platform_key',
        incremental_strategy = 'delete+insert'
    )
}}

-- Chiều nền tảng: 8 tổ hợp cố định Windows / Mac / Linux
-- Dùng danh sách tĩnh (không DISTINCT từ data) để đảm bảo
-- mọi tổ hợp đều tồn tại → Fact luôn JOIN được
-- Bảng này chỉ có 8 dòng, hiếm khi thay đổi
with platform_combos as (
    select 1 as is_windows, 1 as is_mac, 1 as is_linux
    union all select 1, 1, 0
    union all select 1, 0, 1
    union all select 1, 0, 0
    union all select 0, 1, 1
    union all select 0, 1, 0
    union all select 0, 0, 1
    union all select 0, 0, 0
)
select
    row_number() over (
        order by is_windows desc, is_mac desc, is_linux desc
    )                           as platform_key,
    case
        when is_windows = 1 and is_mac = 1 and is_linux = 1 then 'Cross-platform'
        when is_windows = 1 and is_mac = 1 and is_linux = 0 then 'Win & Mac'
        when is_windows = 1 and is_mac = 0 and is_linux = 1 then 'Win & Linux'
        when is_windows = 1 and is_mac = 0 and is_linux = 0 then 'Windows Only'
        when is_windows = 0 and is_mac = 1 and is_linux = 1 then 'Mac & Linux'
        when is_windows = 0 and is_mac = 1 and is_linux = 0 then 'Mac Only'
        when is_windows = 0 and is_mac = 0 and is_linux = 1 then 'Linux Only'
        else                                                       'Unknown'
    end                         as platform_combo,
    cast(is_windows as bit)     as is_windows,
    cast(is_mac     as bit)     as is_mac,
    cast(is_linux   as bit)     as is_linux
from platform_combos
