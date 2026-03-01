-- Every completed match should have exactly 2 batting teams in match summary
-- Excludes no-result matches
select s.match_id, count(distinct s.batting_team) as team_count
from {{ ref('fact_match_summary') }} s
join {{ ref('dim_matches') }} m on s.match_id = m.match_id
where m.match_result_type != 'no_result'
group by s.match_id
having count(distinct s.batting_team) != 2
