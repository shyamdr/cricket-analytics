
-- Player dimension: one row per player who appeared in match data.
-- Enriched with ESPN biographical data (DOB, batting/bowling styles, playing roles).
-- Image URLs from standalone espn_images enrichment.
-- Deduplicates by player_id — some players appear with multiple name
-- spellings in the registry. Prefers the people.csv canonical name.
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
),

-- ESPN player bio: pick latest appearance per player (most recent match)
-- to get the most up-to-date biographical data
espn_latest as (
    select
        ep.*,
        row_number() over (
            partition by ep.espn_player_id
            order by ep.espn_match_id desc
        ) as rn
    from {{ ref('stg_espn_players') }} ep
),

-- Player images from standalone image enrichment
player_images as (
    select entity_id, image_url, headshot_url
    from {{ ref('stg_espn_images') }}
    where entity_type = 'player'
)

select
    d.player_id,
    coalesce(p.player_name, d.player_name) as player_name,
    p.unique_name,
    p.key_cricinfo,
    p.key_cricbuzz,
    p.key_bcci,
    -- ESPN enrichment: biographical data
    el.espn_player_id,
    el.date_of_birth,
    el.batting_styles,
    el.bowling_styles,
    el.long_batting_styles,
    el.long_bowling_styles,
    el.playing_roles,
    el.country_team_id,
    el.is_overseas,
    -- Image URLs (CMS paths — prepend https://img1.hscicdn.com/image/upload/f_auto at display time)
    pi.image_url,
    pi.headshot_url as headshot_image_url
from deduped d
left join people p on d.player_id = p.player_id
left join espn_latest el
    on p.key_cricinfo is not null
    and el.espn_player_id = try_cast(p.key_cricinfo as bigint)
    and el.rn = 1
left join player_images pi
    on p.key_cricinfo is not null
    and pi.entity_id = p.key_cricinfo
