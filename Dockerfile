FROM mageai/mageai:0.9.79@sha256:440970d14b6e1c66e879650c35564cf5125cbbed56032c0fb8337808fdf012fe
USER root
RUN apt-get update && apt-get install -y curl apt-transport-https gnupg2 \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/debian/11/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 unixodbc-dev

# Keep dbt's dependencies separate from Mage's Python environment.
COPY dbt_transform/requirements.txt /tmp/requirements-dbt.txt
RUN python -m venv /opt/dbt-venv \
    && /opt/dbt-venv/bin/pip install --no-cache-dir -r /tmp/requirements-dbt.txt
ENV DBT_EXECUTABLE=/opt/dbt-venv/bin/dbt \
    DBT_SEND_ANONYMOUS_USAGE_STATS=false
