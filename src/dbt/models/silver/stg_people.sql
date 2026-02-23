-- Staged people registry
with source as (
    select * from {{ source('bronze', 'people') }}
)

select
    identifier as player_id,
    name as player_name,
    unique_name,
    key_cricinfo,
    key_cricbuzz,
    key_bcci
from source
