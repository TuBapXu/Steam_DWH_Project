{# ============================================================
   Override schema naming: dùng đúng tên schema tùy chỉnh
   thay vì dbt mặc định ghép prefix target.schema + custom_schema.
   Ví dụ: +schema: dwh → tạo đúng schema 'dwh', không phải 'dbt_staging_dwh'
   ============================================================ #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
