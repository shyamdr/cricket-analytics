-- Ensure no negative values in bowling aggregates
select *
from {{ ref('fact_bowling_innings') }}
where legal_balls < 0
   or runs_conceded < 0
   or wickets < 0
   or dot_balls < 0
   or economy_rate < 0
