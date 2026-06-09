from django.db import NotSupportedError
from django.db.models.functions.text import (
    MD5,
    SHA256,
    Concat,
    ConcatPair,
    Left,
    Length,
    Lower,
    LPad,
    LTrim,
    Repeat,
    Replace,
    Reverse,
    Right,
    RPad,
    RTrim,
    StrIndex,
    Substr,
    Trim,
    Upper,
)

from ..query_utils import process_lhs


def concat(self, compiler, connection):
    return self.get_source_expressions()[0].as_mql(compiler, connection, as_expr=True)


def concat_pair(self, compiler, connection):
    # null on either side results in null for expression, wrap with coalesce.
    coalesced = self.coalesce()
    return super(type(self), coalesced).as_mql_expr(compiler, connection)


def hash_func(algorithm):
    def wrapped(self, compiler, connection):
        if not connection.features.is_mongodb_8_3:
            raise NotSupportedError(f"{self.__class__.__name__} requires MongoDB 8.3+.")
        lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
        return {
            "$cond": {
                "if": {"$eq": [lhs_mql, None]},
                "then": None,  # Return null for null input.
                "else": {
                    "$toLower": {
                        "$convert": {
                            "input": {"$hash": {"input": lhs_mql, "algorithm": algorithm}},
                            "to": "string",
                            "format": "hex",
                        }
                    }
                },
            }
        }

    return wrapped


def left(self, compiler, connection):
    return self.get_substr().as_mql(compiler, connection, as_expr=True)


def length(self, compiler, connection):
    # Check for null first since $strLenCP only accepts strings.
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    return {"$cond": {"if": {"$eq": [lhs_mql, None]}, "then": None, "else": {"$strLenCP": lhs_mql}}}


def pad(is_left=False):
    def wrapped(self, compiler, connection):
        expression, length, fill_text = process_lhs(self, compiler, connection, as_expr=True)
        # Use $ifNull to avoid $strLenCP failing on null during pipeline
        # optimization.
        str_len = {"$strLenCP": {"$ifNull": [expression, ""]}}
        pad_needed = {"$subtract": [length, str_len]}
        # Repeat fill_text enough times to cover the padding, then trim to
        # pad_needed characters using $substrCP.
        repeated_fill = {
            "$reduce": {
                "input": {
                    "$range": [
                        0,
                        {
                            "$toInt": {
                                "$ceil": {
                                    "$divide": [
                                        pad_needed,
                                        {"$max": [{"$strLenCP": {"$ifNull": [fill_text, " "]}}, 1]},
                                    ]
                                }
                            }
                        },
                    ]
                },
                "initialValue": "",
                "in": {"$concat": ["$$value", fill_text]},
            }
        }
        padding = {"$substrCP": [repeated_fill, 0, pad_needed]}
        padded = {"$concat": [padding, expression] if is_left else [expression, padding]}
        return {
            "$cond": {
                "if": {"$or": [{"$eq": [expression, None]}, {"$eq": [length, None]}]},
                "then": None,  # Return null for null inputs.
                "else": {
                    "$cond": {
                        "if": {"$gte": [str_len, length]},
                        "then": {"$substrCP": [expression, 0, length]},
                        "else": padded,
                    }
                },
            }
        }

    return wrapped


def preserve_null(operator):
    # If the argument is null, the function should return null, not
    # $toLower/Upper's behavior of returning an empty string.
    def wrapped(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
        return {
            "$cond": {
                "if": connection.mongo_expr_operators["isnull"](lhs_mql, True),
                "then": None,
                "else": {f"${operator}": lhs_mql},
            }
        }

    return wrapped


def repeat(self, compiler, connection):
    expression, number = process_lhs(self, compiler, connection, as_expr=True)
    return {
        "$cond": {
            "if": {"$or": [{"$eq": [expression, None]}, {"$eq": [number, None]}]},
            "then": None,  # Return null if any inputs are null.
            "else": {
                "$reduce": {
                    # $ifNull needed because $range fails during MongoDB
                    # pipeline optimization when number is null, even inside a
                    # $cond "else" branch.
                    "input": {"$range": [0, {"$ifNull": [number, 0]}]},
                    "initialValue": "",
                    "in": {"$concat": ["$$value", expression]},
                }
            },
        }
    }


def replace(self, compiler, connection):
    expression, text, replacement = process_lhs(self, compiler, connection, as_expr=True)
    return {"$replaceAll": {"input": expression, "find": text, "replacement": replacement}}


def reverse(self, compiler, connection):
    lhs_mql = process_lhs(self, compiler, connection, as_expr=True)
    chars = {
        "$map": {
            "input": {"$range": [0, {"$strLenCP": lhs_mql}]},
            "as": "i",
            "in": {"$substrCP": [lhs_mql, "$$i", 1]},
        }
    }
    return {
        "$cond": {
            "if": {"$eq": [lhs_mql, None]},
            "then": None,  # Return null for null input.
            "else": {
                "$reduce": {
                    "input": {"$reverseArray": chars},
                    "initialValue": "",
                    "in": {"$concat": ["$$value", "$$this"]},
                }
            },
        }
    }


def right(self, compiler, connection):
    expression, length = (
        expr.as_mql(compiler, connection, as_expr=True) for expr in self.get_source_expressions()
    )
    # Calculate substring's start value by subtracting the requested length
    # from the total length of the string.
    start = {"$max": [{"$subtract": [{"$strLenCP": expression}, length]}, 0]}
    return {
        "$cond": {
            "if": {"$eq": [length, None]},
            # $substrCP returns "" for null length; return null instead.
            "then": None,
            "else": {"$substrCP": [expression, start, length]},
        }
    }


def str_index(self, compiler, connection):
    lhs = process_lhs(self, compiler, connection, as_expr=True)
    # StrIndex should be 0-indexed (not found) but it's -1-indexed on MongoDB.
    return {"$add": [{"$indexOfCP": lhs}, 1]}


def substr(self, compiler, connection):
    lhs = process_lhs(self, compiler, connection, as_expr=True)
    # The starting index is zero-indexed on MongoDB rather than one-indexed.
    lhs[1] = {"$add": [lhs[1], -1]}
    # If no limit is specified, use the length of the string since $substrCP
    # requires one.
    if len(lhs) == 2:
        lhs.append({"$strLenCP": lhs[0]})
    return {"$substrCP": lhs}


def trim(operator):
    def wrapped(self, compiler, connection):
        lhs = process_lhs(self, compiler, connection, as_expr=True)
        return {f"${operator}": {"input": lhs}}

    return wrapped


def register_text():
    Concat.as_mql_expr = concat
    ConcatPair.as_mql_expr = concat_pair
    Left.as_mql_expr = left
    Length.as_mql_expr = length
    Lower.as_mql_expr = preserve_null("toLower")
    LPad.as_mql_expr = pad(is_left=True)
    LTrim.as_mql_expr = trim("ltrim")
    MD5.as_mql_expr = hash_func("md5")
    Repeat.as_mql_expr = repeat
    Replace.as_mql_expr = replace
    Reverse.as_mql_expr = reverse
    Right.as_mql_expr = right
    RPad.as_mql_expr = pad(is_left=False)
    RTrim.as_mql_expr = trim("rtrim")
    SHA256.as_mql_expr = hash_func("sha256")
    StrIndex.as_mql_expr = str_index
    Substr.as_mql_expr = substr
    Trim.as_mql_expr = trim("trim")
    Upper.as_mql_expr = preserve_null("toUpper")
