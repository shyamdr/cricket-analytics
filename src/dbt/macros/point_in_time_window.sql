{%- macro point_in_time_window(expression, partition_by, order_by) -%}
    {#-
        Cumulative as-of-prior-row window aggregate.

        Expands to:
            <expression> over (
                partition by <partition_by>
                order by <order_by>
                rows between unbounded preceding and 1 preceding
            )

        Use for any column whose value must reflect ONLY rows strictly before the
        current row — career totals, counters, flags at a point in time.

        The "1 preceding" frame bound is the critical safety: it excludes the
        current row, which is how we guarantee zero data leakage when computing
        as-of features for ML training or "career before this match" columns.

        Args:
            expression   — SQL aggregate expression, e.g. "sum(runs_scored)"
            partition_by — partition key(s), e.g. "batter"
            order_by     — ordering key(s), must be fully deterministic, e.g.
                           "match_date, match_id" (not just "match_date" — two
                           matches on the same day need a tiebreaker)

        Usage:
            {{ point_in_time_window(
                'sum(runs_scored)',
                partition_by='batter',
                order_by='match_date, match_id'
            ) }} as career_runs_before

        See ADR-007 for the full convention.
    -#}
    {{ expression }} over (
        partition by {{ partition_by }}
        order by {{ order_by }}
        rows between unbounded preceding and 1 preceding
    )
{%- endmacro -%}
