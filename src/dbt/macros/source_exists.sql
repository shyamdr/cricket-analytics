{% macro source_exists(source_name, table_name) %}
    {#- Check if a source table exists in the database.
        Returns true/false. Useful for optional enrichment sources
        that may not exist on a fresh database. -#}
    {%- set source_relation = source(source_name, table_name) -%}
    {%- set schema = source_relation.schema -%}
    {%- set table = source_relation.identifier -%}

    {%- set query -%}
        select count(*) as cnt
        from information_schema.tables
        where table_schema = '{{ schema }}'
          and table_name = '{{ table }}'
    {%- endset -%}

    {%- set result = run_query(query) -%}
    {%- if execute -%}
        {{ return(result.columns[0].values()[0] > 0) }}
    {%- else -%}
        {{ return(false) }}
    {%- endif -%}
{% endmacro %}
