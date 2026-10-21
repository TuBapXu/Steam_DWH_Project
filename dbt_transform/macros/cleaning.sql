{% macro steam_clean_text(expression) -%}
    {%- set trimmed -%}
        ltrim(rtrim(replace(replace(replace(replace(
            {{ expression }}, nchar(9), N' '), nchar(10), N' '),
            nchar(13), N' '), nchar(160), N' ')))
    {%- endset -%}
    case when lower({{ trimmed }}) in (N'', N'nan', N'none', N'null', N'n/a')
         then null else {{ trimmed }} end
{%- endmacro %}

{% macro steam_nonnegative(expression, sql_type='bigint', missing_zero=true) -%}
    case
        {% if missing_zero %}when {{ expression }} is null then cast(0 as {{ sql_type }}){% endif %}
        when {{ expression }} >= 0 then cast({{ expression }} as {{ sql_type }})
        else cast(null as {{ sql_type }})
    end
{%- endmacro %}
