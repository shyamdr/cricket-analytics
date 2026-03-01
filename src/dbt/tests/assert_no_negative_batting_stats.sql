-- Ensure no negative values in batting aggregates
select *
from {{ ref('fact_batting_innings') }}
where balls_faced < 0
   or runs_scored < 0
   or fours < 0
   or sixes < 0
   or dot_balls < 0
   or strike_rate < 0
