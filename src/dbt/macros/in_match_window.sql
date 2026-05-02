{%- macro in_match_window(expression, partition_by, order_by) -%}
    {#-
        In-match running window aggregate that INCLUDES the current row.

        Expands to:
            <expression> over (
                partition by <partition_by>
                order by <order_by>
                rows between unbounded preceding and current row
            )

        Use ONLY for within-match running state — batter's score at the current
        ball, team total at the current ball, balls faced so far this innings,
        wickets lost in this innings. These columns carry the "*_at_ball"
        naming suffix.

        Why "current row" is safe here but not in point_in_time_window:
        because the partition is always scoped to a single match (or innings),
        there is no cross-match data leakage. The current ball's runs ARE part
        of "team score at this ball" — by definition.

        NEVER use this macro for cross-match windows. If your partition_by does
        not include match_id (or equivalent), use point_in_time_window or
        rolling_window instead.

        Args:
            expression   — SQL aggregate expression, e.g. "sum(batter_runs)"
            partition_by — must scope to a single match/innings/over, e.g.
                           "match_id, innings, batter"
            order_by     — deterministic ordering within the partition, e.g.
                           "over_num, ball_num"

        Usage:
            {{ in_match_window(
                'sum(batter_runs)',
                partition_by='match_id, innings, batter',
                order_by='over_num, ball_num'
            ) }} as batter_score_at_ball

        See ADR-007.
    -#}
    {{ expression }} over (
        partition by {{ partition_by }}
        order by {{ order_by }}
        rows between unbounded preceding and current row
    )
{%- endmacro -%}
