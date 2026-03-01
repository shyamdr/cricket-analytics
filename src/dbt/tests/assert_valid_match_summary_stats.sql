-- Ensure match summary has no negative values and wickets <= 10
select *
from {{ ref('fact_match_summary') }}
where total_runs < 0
   or total_wickets < 0
   or total_wickets > 10
   or total_extras < 0
   or run_rate < 0
