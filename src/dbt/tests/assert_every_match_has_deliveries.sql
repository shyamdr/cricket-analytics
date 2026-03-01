-- Every completed match should have at least 1 delivery
-- Excludes no-result matches where no play occurred
select m.match_id
from {{ ref('dim_matches') }} m
left join {{ ref('fact_deliveries') }} d on m.match_id = d.match_id
where m.match_result_type != 'no_result'
group by m.match_id
having count(d.match_id) = 0
