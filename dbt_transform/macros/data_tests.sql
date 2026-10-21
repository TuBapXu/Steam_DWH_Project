{% test valid_range(model, column_name, min_value=0, max_value=none) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} < {{ min_value }}
{% if max_value is not none %}or {{ column_name }} > {{ max_value }}{% endif %}
{% endtest %}

{% test normalized_text(model, column_name) %}
select {{ column_name }}
from {{ model }}
where {{ column_name }} is not null
  and ({{ steam_clean_text(column_name) }} is null
       or datalength({{ column_name }}) <> datalength({{ steam_clean_text(column_name) }}))
{% endtest %}
