{{ config(
    materialized='incremental',
    unique_key='operating_system_key',
    incremental_strategy='delete+insert',
    as_columnstore=false,
    post_hook="if not exists (select 1 from sys.indexes where object_id = object_id('{{ this }}') and name = 'uq_dim_operating_system_key') create unique index uq_dim_operating_system_key on {{ this }} (operating_system_key)"
) }}

select os.operating_system_key, os.operating_system_name
from (values (1, N'Windows'), (2, N'Mac'), (3, N'Linux'))
    os(operating_system_key, operating_system_name)
{% if is_incremental() %}
where not exists (
    select 1 from {{ this }} existing
    where existing.operating_system_key = os.operating_system_key
)
{% endif %}
