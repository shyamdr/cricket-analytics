-- Player dimension: one row per player who appeared in match data.
-- Deduplicates by player_id — some players appear with multiple name
-- spellings in the registry (e.g. "NA Saini" vs "Navdeep Saini").
-- Prefers the people.csv canonical name, falls back to the most
-- frequently used registry name.
with registry_entries as (
    select
        trim(j.value::varchar, '"') as player_id,
        j.key as player_name,
        count(*) as usage_count
    from {{ ref('stg_matches') }} m,
    lateral (select key, value from json_each(m.registry_json::json)) j
    group by 1, 2
),

-- Pick one name per player_id: most frequently used in match registries
ranked as (
    select
        player_id,
        player_name,
        row_number() over (
            partition by player_id
            order by usage_count desc, player_name
        ) as rn
    from registry_entries
),

deduped as (
    select player_id, player_name
    from ranked
    where rn = 1
),

people as (
    select * from {{ ref('stg_people') }}
)

select
    d.player_id,
    -- Prefer people.csv canonical name if available, else registry name
    coalesce(p.player_name, d.player_name) as player_name,
    p.unique_name,
    p.key_cricinfo,
    p.key_cricbuzz,
    p.key_bcci
from deduped d
left join people p on d.player_id = p.player_id
