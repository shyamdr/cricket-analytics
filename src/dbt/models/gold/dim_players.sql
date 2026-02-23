-- Player dimension: one row per player who appeared in IPL
with registry_entries as (
    select distinct
        trim(j.value::varchar, '"') as player_id,
        j.key as player_name
    from {{ ref('stg_matches') }} m,
    lateral (select key, value from json_each(m.registry_json::json)) j
),

people as (
    select * from {{ ref('stg_people') }}
)

select
    r.player_id,
    r.player_name,
    p.unique_name,
    p.key_cricinfo,
    p.key_cricbuzz,
    p.key_bcci
from registry_entries r
left join people p on r.player_id = p.player_id
