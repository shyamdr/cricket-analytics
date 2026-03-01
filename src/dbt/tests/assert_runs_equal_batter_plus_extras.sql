-- total_runs must equal batter_runs + extras_runs on every delivery
select *
from {{ ref('fact_deliveries') }}
where total_runs != batter_runs + extras_runs
