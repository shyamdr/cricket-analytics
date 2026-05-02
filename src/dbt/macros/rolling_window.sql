{%- macro rolling_window(expression, partition_by, order_by, rows) -%}
    {#-
        Rolling N-row window aggregate that EXCLUDES the current row.

        Expands to:
            <expression> over (
                partition by <partition_by>
                order by <order_by>
                rows between <rows> preceding and 1 preceding
            )

        Use for rolling-form metrics — rolling 10-innings strike rate, rolling
        5-match economy, last-N-balls boundary rate. The current row is
        excluded so the column reflects form heading INTO the current event,
        not form including it.

        Args:
            expression   — SQL aggregate expression, e.g. "avg(strike_rate)"
            partition_by — partition key(s), e.g. "batter"
            order_by     — deterministic ordering key(s), e.g.
                           "match_date, match_id"
            rows         — window size as an integer, e.g. 10

        Usage:
            {{ rolling_window(
                'avg(strike_rate)',
                partition_by='batter',
                order_by='match_date, match_id',
                rows=10
            ) }} as rolling_10_innings_sr

        For the first N matches of a career the window is not yet full; the
        aggregate computes over however many rows exist (0 to N-1) prior to the
        current row. For the very first match the window is empty and most
        aggregates return NULL. That is the correct behaviour — there is no
        "rolling form" before any matches have been played.

        See ADR-007.
    -#}
    {{ expression }} over (
        partition by {{ partition_by }}
        order by {{ order_by }}
        rows between {{ rows }} preceding and 1 preceding
    )
{%- endmacro -%}
