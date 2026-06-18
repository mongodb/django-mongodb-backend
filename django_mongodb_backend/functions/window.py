from django.db.models.aggregates import Aggregate, Count, StdDev, Variance
from django.db.models.functions.window import (
    CumeDist,
    DenseRank,
    FirstValue,
    Lag,
    LastValue,
    Lead,
    NthValue,
    Ntile,
    PercentRank,
    Rank,
    RowNumber,
)


def aggregate(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    agg_mql = self.as_mql_expr(compiler, connection)
    return {alias: {**agg_mql, "window": default_frame()}}, {}


def count(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    # Count.as_mql_expr() returns {"$sum": lhs_mql} for non-distinct counts.
    # MongoDB's $count is a pipeline stage (not a window accumulator), so use
    # $sum instead.
    agg_mql = self.as_mql_expr(compiler, connection)
    return {alias: {**agg_mql, "window": default_frame()}}, {}


def cume_dist(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    # CumeDist = (rank + group_size - 1) / total. Use $rank for the base rank
    # (1-based, same value for ties), range:[0, 0] for group_size (count of all
    # rows with identical sort key value), and full-partition sum for total.
    rank_alias = f"__wtemp{next(idx)}"
    group_size_alias = f"__wtemp{next(idx)}"
    total_alias = f"__wtemp{next(idx)}"
    output = {
        rank_alias: {"$rank": {}},
        group_size_alias: {"$sum": 1, "window": {"range": [0, 0]}},
        total_alias: {"$sum": 1, "window": {"documents": ["unbounded", "unbounded"]}},
    }
    add_fields = {
        alias: {
            "$divide": [
                {"$subtract": [{"$add": [f"${rank_alias}", f"${group_size_alias}"]}, 1]},
                f"${total_alias}",
            ]
        }
    }
    return output, add_fields


def dense_rank(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    return {alias: {"$denseRank": {}}}, {}


def first_value(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    expr = self.get_source_expressions()[0]
    mql = expr.as_mql(compiler, connection, as_expr=True)
    return {alias: {"$first": mql, "window": default_frame()}}, {}


def lag(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    exprs = self.get_source_expressions()
    expr_mql = exprs[0].as_mql(compiler, connection, as_expr=True)
    offset = exprs[1].value
    mql = {"output": expr_mql, "by": -offset}
    if len(exprs) > 2:
        mql["default"] = exprs[2].as_mql(compiler, connection, as_expr=True)
    return {alias: {"$shift": mql}}, {}


def last_value(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    expr = self.get_source_expressions()[0]
    mql = expr.as_mql(compiler, connection, as_expr=True)
    return {alias: {"$last": mql, "window": default_frame()}}, {}


def lead(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    exprs = self.get_source_expressions()
    expr_mql = exprs[0].as_mql(compiler, connection, as_expr=True)
    offset = exprs[1].value
    mql = {"output": expr_mql, "by": offset}
    if len(exprs) > 2:
        mql["default"] = exprs[2].as_mql(compiler, connection, as_expr=True)
    return {alias: {"$shift": mql}}, {}


def nth_value(self, compiler, connection, alias, idx, default_frame):
    expr, nth_expr = self.get_source_expressions()
    mql = expr.as_mql(compiler, connection, as_expr=True)
    nth = nth_expr.value
    push_alias = f"__wtemp{next(idx)}"
    output = {push_alias: {"$push": mql, "window": default_frame()}}
    add_fields = {
        alias: {
            "$cond": {
                "if": {"$gte": [{"$size": f"${push_alias}"}, nth]},
                "then": {"$arrayElemAt": [f"${push_alias}", nth - 1]},
                "else": None,
            }
        }
    }
    return output, add_fields


def ntile(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    num_buckets = self.get_source_expressions()[0].value
    doc_num_alias = f"__wtemp{next(idx)}"
    total_alias = f"__wtemp{next(idx)}"
    output = {
        doc_num_alias: {"$documentNumber": {}},
        total_alias: {"$sum": 1, "window": {"documents": ["unbounded", "unbounded"]}},
    }
    # SQL NTILE: rows 1..extra*(per+1) go to the first `extra` buckets (each
    # gets per+1 rows); remaining rows are distributed evenly across the rest.
    # `$max [$$per, 1]` guards against division by zero in the else branch when
    # num_buckets > total (per==0), which is unreachable but may be evaluated.
    add_fields = {
        alias: {
            "$let": {
                "vars": {
                    "per": {"$floor": {"$divide": [f"${total_alias}", num_buckets]}},
                    "xtra": {"$mod": [f"${total_alias}", num_buckets]},
                },
                "in": {
                    "$let": {
                        "vars": {
                            "thr": {"$multiply": ["$$xtra", {"$add": ["$$per", 1]}]},
                        },
                        "in": {
                            "$cond": {
                                "if": {"$lte": [f"${doc_num_alias}", "$$thr"]},
                                "then": {
                                    "$add": [
                                        {
                                            "$floor": {
                                                "$divide": [
                                                    {"$subtract": [f"${doc_num_alias}", 1]},
                                                    {"$add": ["$$per", 1]},
                                                ]
                                            }
                                        },
                                        1,
                                    ]
                                },
                                "else": {
                                    "$add": [
                                        "$$xtra",
                                        {
                                            "$floor": {
                                                "$divide": [
                                                    {
                                                        "$subtract": [
                                                            f"${doc_num_alias}",
                                                            {"$add": ["$$thr", 1]},
                                                        ]
                                                    },
                                                    {"$max": ["$$per", 1]},
                                                ]
                                            }
                                        },
                                        1,
                                    ]
                                },
                            }
                        },
                    }
                },
            }
        }
    }
    return output, add_fields


def percent_rank(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    # Use document-position rank ($sum:1 docs unbounded-to-current)
    # instead of $rank, which MongoDB limits to a single sort field.
    row_num_alias = f"__wtemp{next(idx)}"
    count_alias = f"__wtemp{next(idx)}"
    output = {
        row_num_alias: {"$sum": 1, "window": {"documents": ["unbounded", "current"]}},
        count_alias: {"$sum": 1, "window": {"documents": ["unbounded", "unbounded"]}},
    }
    add_fields = {
        alias: {
            "$cond": {
                "if": {"$lte": [f"${count_alias}", 1]},
                "then": {"$literal": 0.0},
                "else": {
                    "$divide": [
                        {"$subtract": [f"${row_num_alias}", 1]},
                        {"$subtract": [f"${count_alias}", 1]},
                    ]
                },
            }
        }
    }
    return output, add_fields


def rank(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    return {alias: {"$rank": {}}}, {}


def row_number(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    return {alias: {"$documentNumber": {}}}, {}


def stddev(self, compiler, connection, alias, idx, default_frame):  # noqa: ARG001
    agg_mql = self.as_mql_expr(compiler, connection)
    return {alias: {**agg_mql, "window": default_frame()}}, {}


def variance(self, compiler, connection, alias, idx, default_frame):
    # MongoDB has no $varPop/$varSamp window accumulator; compute as stdDev².
    agg_mql = self.as_mql_expr(compiler, connection)
    stddev_alias = f"__wtemp{next(idx)}"
    output = {stddev_alias: {**agg_mql, "window": default_frame()}}
    add_fields = {alias: {"$pow": [f"${stddev_alias}", 2]}}
    return output, add_fields


def register_window():
    Aggregate.get_window_mql = aggregate
    Count.get_window_mql = count
    CumeDist.get_window_mql = cume_dist
    DenseRank.get_window_mql = dense_rank
    FirstValue.get_window_mql = first_value
    Lag.get_window_mql = lag
    LastValue.get_window_mql = last_value
    Lead.get_window_mql = lead
    NthValue.get_window_mql = nth_value
    Ntile.get_window_mql = ntile
    PercentRank.get_window_mql = percent_rank
    Rank.get_window_mql = rank
    RowNumber.get_window_mql = row_number
    StdDev.get_window_mql = stddev
    Variance.get_window_mql = variance
