from django.db import NotSupportedError
from django.db.models import Expression, FloatField
from django.db.models.expressions import F, Value


def cast_as_value(value):
    if value is None:
        return None
    return Value(value) if not hasattr(value, "resolve_expression") else value


def cast_as_field(path):
    return F(path) if isinstance(path, str) else path


class Operator:
    AND = "AND"
    OR = "OR"
    NOT = "NOT"

    def __init__(self, operator):
        self.operator = operator

    def __eq__(self, other):
        if isinstance(other, str):
            return self.operator == other
        return self.operator == other.operator

    def negate(self):
        if self.operator == self.AND:
            return Operator(self.OR)
        if self.operator == self.OR:
            return Operator(self.AND)
        return Operator(self.operator)

    def __hash__(self):
        return hash(self.operator)

    def __str__(self):
        return self.operator

    def __repr__(self):
        return self.operator


class SearchCombinable:
    def _combine(self, other, connector):
        if not isinstance(self, CompoundExpression | CombinedSearchExpression):
            lhs = CompoundExpression(must=[self])
        else:
            lhs = self
        if other and not isinstance(other, CompoundExpression | CombinedSearchExpression):
            rhs = CompoundExpression(must=[other])
        else:
            rhs = other
        return CombinedSearchExpression(lhs, connector, rhs)

    def __invert__(self):
        return self._combine(None, Operator(Operator.NOT))

    def __and__(self, other):
        return self._combine(other, Operator(Operator.AND))

    def __rand__(self, other):
        return self._combine(other, Operator(Operator.AND))

    def __or__(self, other):
        return self._combine(other, Operator(Operator.OR))

    def __ror__(self, other):
        return self._combine(other, Operator(Operator.OR))


class SearchExpression(SearchCombinable, Expression):
    """Base expression node for MongoDB Atlas `$search` stages.

    This class bridges Django's `Expression` API with the MongoDB Atlas
    Search engine.  Subclasses produce the operator document placed under
    **$search** and expose the stage to queryset methods such as
    `annotate()`, `filter()`, or `order_by()`.
    """

    output_field = FloatField()

    def __str__(self):
        cls = self.identity[0]
        kwargs = dict(self.identity[1:])
        arg_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        return f"<{cls.__name__}({arg_str})>"

    def __repr__(self):
        return str(self)

    def as_sql(self, compiler, connection):
        return "", []

    def _get_indexed_fields(self, mappings):
        if isinstance(mappings, list):
            for definition in mappings:
                yield from self._get_indexed_fields(definition)
        else:
            for field, definition in mappings.get("fields", {}).items():
                yield field
                for path in self._get_indexed_fields(definition):
                    yield f"{field}.{path}"

    def _get_query_index(self, fields, compiler):
        fields = set(fields)
        for search_indexes in compiler.collection.list_search_indexes():
            mappings = search_indexes["latestDefinition"]["mappings"]
            indexed_fields = set(self._get_indexed_fields(mappings))
            if mappings["dynamic"] or fields.issubset(indexed_fields):
                return search_indexes["name"]
        return "default"

    def search_operator(self, compiler, connection):
        raise NotImplementedError

    def as_mql(self, compiler, connection):
        index = self._get_query_index(self.get_search_fields(compiler, connection), compiler)
        return {"$search": {**self.search_operator(compiler, connection), "index": index}}


class SearchAutocomplete(SearchExpression):
    """
    Atlas Search expression that matches input using the `autocomplete` operator.

    This expression enables autocomplete behavior by querying against a field
    indexed as `"type": "autocomplete"` in MongoDB Atlas. It can be used in
    `filter()`, `annotate()` or any context that accepts a Django expression.

    Example:
        SearchAutocomplete("title", "harry", fuzzy={"maxEdits": 1})

    Args:
        path: The document path to search (as string or expression).
        query: The input string to autocomplete.
        fuzzy: Optional dictionary of fuzzy matching parameters.
        token_order: Optional value for `"tokenOrder"`; controls sequential vs.
            any-order token matching.
        score: Optional expression to adjust score relevance (e.g., `{"boost": {"value": 5}}`).

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/autocomplete/
    """

    def __init__(self, path, query, fuzzy=None, token_order=None, score=None):
        self.path = cast_as_field(path)
        self.query = cast_as_value(query)
        self.fuzzy = cast_as_value(fuzzy)
        self.token_order = cast_as_value(token_order)
        self.score = score
        super().__init__()

    def get_source_expressions(self):
        return [self.path, self.query, self.fuzzy, self.token_order]

    def set_source_expressions(self, exprs):
        self.path, self.query, self.fuzzy, self.token_order = exprs

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query.value,
        }
        if self.score is not None:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.fuzzy is not None:
            params["fuzzy"] = self.fuzzy.value
        if self.token_order is not None:
            params["tokenOrder"] = self.token_order.value
        return {"autocomplete": params}


class SearchEquals(SearchExpression):
    """
    Atlas Search expression that matches documents with a field equal to the given value.

    This expression uses the `equals` operator to perform exact matches
    on fields indexed in a MongoDB Atlas Search index.

    Example:
        SearchEquals("category", "fiction")

    Args:
        path: The document path to compare (as string or expression).
        value: The exact value to match against.
        score: Optional expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/equals/
    """

    def __init__(self, path, value, score=None):
        self.path = cast_as_field(path)
        self.value = cast_as_value(value)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path, self.value]

    def set_source_expressions(self, exprs):
        self.path, self.value = exprs

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "value": self.value.value,
        }
        if self.score is not None:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"equals": params}


class SearchExists(SearchExpression):
    """
    Atlas Search expression that matches documents where a field exists.

    This expression uses the `exists` operator to check whether a given
    path is present in the document. Useful for filtering documents that
    include (or exclude) optional fields.

    Example:
        SearchExists("metadata__author")

    Args:
        path: The document path to check (as string or expression).
        score: Optional expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/exists/
    """

    def __init__(self, path, score=None):
        self.path = cast_as_field(path)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path]

    def set_source_expressions(self, exprs):
        (self.path,) = exprs

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
        }
        if self.score is not None:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"exists": params}


class SearchIn(SearchExpression):
    """
    Atlas Search expression that matches documents where the field value is in a given list.

    This expression uses the `in` operator to match documents whose field
    contains a value from the provided array of values.

    Example:
        SearchIn("status", ["pending", "approved", "rejected"])

    Args:
        path: The document path to match against (as string or expression).
        value: A list of values to check for membership.
        score: Optional expression to adjust the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/in/
    """

    def __init__(self, path, value, score=None):
        self.path = cast_as_field(path)
        self.value = cast_as_value(value)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path, self.value]

    def set_source_expressions(self, exprs):
        self.path, self.value = exprs

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "value": self.value.value,
        }
        if self.score is not None:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"in": params}


class SearchPhrase(SearchExpression):
    """
    Atlas Search expression that matches a phrase in the specified field.

    This expression uses the `phrase` operator to search for exact or near exact
    sequences of terms. It supports optional slop (word distance) and synonym sets.

    Example:
        SearchPhrase("description__text", "climate change", slop=2)

    Args:
        path: The document path to search (as string or expression).
        query: The phrase to match as a single string or list of terms.
        slop: Optional maximum word distance allowed between phrase terms.
        synonyms: Optional name of a synonym mapping defined in the Atlas index.
        score: Optional expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/phrase/
    """

    def __init__(self, path, query, slop=None, synonyms=None, score=None):
        self.path = cast_as_field(path)
        self.query = cast_as_value(query)
        self.slop = cast_as_value(slop)
        self.synonyms = cast_as_value(synonyms)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path, self.query, self.slop, self.synonyms]

    def set_source_expressions(self, exprs):
        self.path, self.query, self.slop, self.synonyms = exprs

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query.value,
        }
        if self.score is not None:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.slop is not None:
            params["slop"] = self.slop.value
        if self.synonyms is not None:
            params["synonyms"] = self.synonyms.value
        return {"phrase": params}


class SearchQueryString(SearchExpression):
    """
    Atlas Search expression that matches using a Lucene-style query string.

    This expression uses the `queryString` operator to parse and execute
    full-text queries written in a simplified Lucene syntax. It supports
    advanced constructs like boolean operators, wildcards, and field-specific terms.

    Example:
        SearchQueryString("content__text", "django AND (search OR query)")

    Args:
        path: The document path to query (as string or expression).
        query: The Lucene-style query string.
        score: Optional expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/queryString/
    """

    def __init__(self, path, query, score=None):
        self.path = cast_as_field(path)
        self.query = cast_as_value(query)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path, self.query]

    def set_source_expressions(self, exprs):
        self.path, self.query = exprs

    def search_operator(self, compiler, connection):
        params = {
            "defaultPath": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query.value,
        }
        if self.score is not None:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"queryString": params}


class SearchRange(SearchExpression):
    """
    Atlas Search expression that filters documents within a range of values.

    This expression uses the `range` operator to match numeric, date, or
    other comparable fields based on upper and/or lower bounds.

    Example:
        SearchRange("published__year", gte=2000, lt=2020)

    Args:
        path: The document path to filter (as string or expression).
        lt: Optional exclusive upper bound (`<`).
        lte: Optional inclusive upper bound (`<=`).
        gt: Optional exclusive lower bound (`>`).
        gte: Optional inclusive lower bound (`>=`).
        score: Optional expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/range/
    """

    def __init__(self, path, lt=None, lte=None, gt=None, gte=None, score=None):
        self.path = cast_as_field(path)
        self.lt = cast_as_value(lt)
        self.lte = cast_as_value(lte)
        self.gt = cast_as_value(gt)
        self.gte = cast_as_value(gte)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path, self.lt, self.lte, self.gt, self.gte]

    def set_source_expressions(self, exprs):
        self.path, self.lt, self.lte, self.gt, self.gte = exprs

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
        }
        if self.score is not None:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.lt is not None:
            params["lt"] = self.lt.value
        if self.lte is not None:
            params["lte"] = self.lte.value
        if self.gt is not None:
            params["gt"] = self.gt.value
        if self.gte is not None:
            params["gte"] = self.gte.value
        return {"range": params}


class SearchRegex(SearchExpression):
    """
    Atlas Search expression that matches strings using a regular expression.

    This expression uses the `regex` operator to apply a regular expression
    against the contents of a specified field.

    Example:
        SearchRegex("username", r"^admin_")

    Args:
        path: The document path to match (as string or expression).
        query: The regular expression pattern to apply.
        allow_analyzed_field: Whether to allow matching against analyzed fields (default is False).
        score: Optional expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/regex/
    """

    def __init__(self, path, query, allow_analyzed_field=None, score=None):
        self.path = cast_as_field(path)
        self.query = cast_as_value(query)
        self.allow_analyzed_field = cast_as_value(allow_analyzed_field)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path, self.query, self.allow_analyzed_field]

    def set_source_expressions(self, exprs):
        self.path, self.query, self.allow_analyzed_field = exprs

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query.value,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.allow_analyzed_field is not None:
            params["allowAnalyzedField"] = self.allow_analyzed_field.value
        return {"regex": params}


class SearchText(SearchExpression):
    """
    Atlas Search expression that performs full-text search using the `text` operator.

    This expression matches terms in a specified field with options for
    fuzzy matching, match criteria, and synonyms.

    Example:
        SearchText("description__content", "mongodb", fuzzy={"maxEdits": 1}, match_criteria="all")

    Args:
        path: The document path to search (as string or expression).
        query: The search term or phrase.
        fuzzy: Optional dictionary to configure fuzzy matching parameters.
        match_criteria: Optional criteria for term matching (e.g., "all" or "any").
        synonyms: Optional name of a synonym mapping defined in the Atlas index.
        score: Optional expression to adjust relevance scoring.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/text/
    """

    def __init__(self, path, query, fuzzy=None, match_criteria=None, synonyms=None, score=None):
        self.path = cast_as_field(path)
        self.query = cast_as_value(query)
        self.fuzzy = cast_as_value(fuzzy)
        self.match_criteria = cast_as_value(match_criteria)
        self.synonyms = cast_as_value(synonyms)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path, self.query, self.fuzzy, self.match_criteria, self.synonyms]

    def set_source_expressions(self, exprs):
        self.path, self.query, self.fuzzy, self.match_criteria, self.synonyms = exprs

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query.value,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.fuzzy is not None:
            params["fuzzy"] = self.fuzzy.value
        if self.match_criteria is not None:
            params["matchCriteria"] = self.match_criteria.value
        if self.synonyms is not None:
            params["synonyms"] = self.synonyms.value
        return {"text": params}


class SearchWildcard(SearchExpression):
    """
    Atlas Search expression that matches strings using wildcard patterns.

    This expression uses the `wildcard` operator to search for terms
    matching a pattern with `*` and `?` wildcards.

    Example:
        SearchWildcard("filename", "report_202?_final*")

    Args:
        path: The document path to search (as string or expression).
        query: The wildcard pattern to match.
        allow_analyzed_field: Whether to allow matching against analyzed fields (default is False).
        score: Optional expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/wildcard/
    """

    def __init__(self, path, query, allow_analyzed_field=None, score=None):
        self.path = cast_as_field(path)
        self.query = cast_as_value(query)
        self.allow_analyzed_field = cast_as_value(allow_analyzed_field)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path, self.query, self.allow_analyzed_field]

    def set_source_expressions(self, exprs):
        self.path, self.query, self.allow_analyzed_field = exprs

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query.value,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.allow_analyzed_field is not None:
            params["allowAnalyzedField"] = self.allow_analyzed_field.value
        return {"wildcard": params}


class SearchGeoShape(SearchExpression):
    """
    Atlas Search expression that filters documents by spatial relationship with a geometry.

    This expression uses the `geoShape` operator to match documents where
    a geo field relates to a specified geometry by a spatial relation.

    Example:
        SearchGeoShape("location", "within", {"type": "Polygon", "coordinates": [...]})

    Args:
        path: The document path to the geo field (as string or expression).
        relation: The spatial relation to test (e.g., "within", "intersects", "disjoint").
        geometry: The GeoJSON geometry to compare against.
        score: Optional expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/geoShape/
    """

    def __init__(self, path, relation, geometry, score=None):
        self.path = cast_as_field(path)
        self.relation = cast_as_value(relation)
        self.geometry = cast_as_value(geometry)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path, self.relation, self.geometry]

    def set_source_expressions(self, exprs):
        self.path, self.relation, self.geometry = exprs

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "relation": self.relation.value,
            "geometry": self.geometry.value,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"geoShape": params}


class SearchGeoWithin(SearchExpression):
    """
    Atlas Search expression that filters documents with geo fields
    contained within a specified shape.

    This expression uses the `geoWithin` operator to match documents where
    the geo field lies entirely within the given geometry.

    Example:
        SearchGeoWithin("location", "Polygon", {"type": "Polygon", "coordinates": [...]})

    Args:
        path: The document path to the geo field (as string or expression).
        kind: The GeoJSON geometry type (e.g., "Polygon", "MultiPolygon").
        geo_object: The GeoJSON geometry defining the boundary.
        score: Optional expression to adjust the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/geoWithin/
    """

    def __init__(self, path, kind, geo_object, score=None):
        self.path = cast_as_field(path)
        self.kind = cast_as_value(kind)
        self.geo_object = cast_as_value(geo_object)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [self.path, self.kind, self.geo_object]

    def set_source_expressions(self, exprs):
        self.path, self.kind, self.geo_object = exprs

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            self.kind.value: self.geo_object.value,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"geoWithin": params}


class SearchMoreLikeThis(SearchExpression):
    """
    Atlas Search expression that finds documents similar to given examples.

    This expression uses the `moreLikeThis` operator to search for documents
    that resemble the specified sample documents.

    Example:
        SearchMoreLikeThis([{"_id": ObjectId("...")}, {"title": "Example"}])

    Args:
        documents: A list of example documents or expressions to find similar documents.
        score: Optional expression to modify the relevance scoring.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/morelikethis/
    """

    def __init__(self, documents, score=None):
        self.documents = cast_as_value(documents)
        self.score = score
        super().__init__()

    def get_source_expressions(self):
        return [self.documents]

    def set_source_expressions(self, exprs):
        (self.documents,) = exprs

    def search_operator(self, compiler, connection):
        params = {
            "like": self.documents.as_mql(compiler, connection),
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"moreLikeThis": params}

    def get_search_fields(self, compiler, connection):
        needed_fields = set()
        for doc in self.documents.value:
            needed_fields.update(set(doc.keys()))
        return needed_fields


class CompoundExpression(SearchExpression):
    """
    Compound expression that combines multiple search clauses using boolean logic.

    This expression corresponds to the `compound` operator in MongoDB Atlas Search,
    allowing fine-grained control by combining multiple sub-expressions with
    `must`, `must_not`, `should`, and `filter` clauses.

    Example:
        CompoundExpression(
            must=[expr1, expr2],
            must_not=[expr3],
            should=[expr4],
            minimum_should_match=1
        )

    Args:
        must: List of expressions that **must** match.
        must_not: List of expressions that **must not** match.
        should: List of expressions that **should** match (optional relevance boost).
        filter: List of expressions to filter results without affecting relevance.
        score: Optional expression to adjust scoring.
        minimum_should_match: Minimum number of `should` clauses that must match.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/compound/
    """

    def __init__(
        self,
        must=None,
        must_not=None,
        should=None,
        filter=None,
        score=None,
        minimum_should_match=None,
    ):
        self.must = must or []
        self.must_not = must_not or []
        self.should = should or []
        self.filter = filter or []
        self.score = score
        self.minimum_should_match = minimum_should_match

    def get_search_fields(self, compiler, connection):
        fields = set()
        for clause in self.must + self.should + self.filter + self.must_not:
            fields.update(clause.get_search_fields(compiler, connection))
        return fields

    def resolve_expression(
        self, query=None, allow_joins=True, reuse=None, summarize=False, for_save=False
    ):
        c = self.copy()
        c.is_summary = summarize
        c.must = [
            expr.resolve_expression(query, allow_joins, reuse, summarize) for expr in self.must
        ]
        c.must_not = [
            expr.resolve_expression(query, allow_joins, reuse, summarize) for expr in self.must_not
        ]
        c.should = [
            expr.resolve_expression(query, allow_joins, reuse, summarize) for expr in self.should
        ]
        c.filter = [
            expr.resolve_expression(query, allow_joins, reuse, summarize) for expr in self.filter
        ]
        return c

    def search_operator(self, compiler, connection):
        params = {}
        if self.must:
            params["must"] = [clause.search_operator(compiler, connection) for clause in self.must]
        if self.must_not:
            params["mustNot"] = [
                clause.search_operator(compiler, connection) for clause in self.must_not
            ]
        if self.should:
            params["should"] = [
                clause.search_operator(compiler, connection) for clause in self.should
            ]
        if self.filter:
            params["filter"] = [
                clause.search_operator(compiler, connection) for clause in self.filter
            ]
        if self.minimum_should_match is not None:
            params["minimumShouldMatch"] = self.minimum_should_match
        return {"compound": params}

    def negate(self):
        return CompoundExpression(must_not=[self])


class CombinedSearchExpression(SearchExpression):
    """
    Combines two search expressions with a logical operator.

    This expression allows combining two Atlas Search expressions
    (left-hand side and right-hand side) using a boolean operator
    such as `and`, `or`, or `not`.

    Example:
        CombinedSearchExpression(expr1, "and", expr2)

    Args:
        lhs: The left-hand search expression.
        operator: The boolean operator as a string (e.g., "and", "or", "not").
        rhs: The right-hand search expression.
    """

    def __init__(self, lhs, operator, rhs):
        self.lhs = lhs
        self.operator = operator
        self.rhs = rhs

    def get_source_expressions(self):
        return [self.lhs, self.rhs]

    def set_source_expressions(self, exprs):
        self.lhs, self.rhs = exprs

    @staticmethod
    def resolve(node, negated=False):
        if node is None:
            return None
        # Leaf, resolve the compoundExpression
        if isinstance(node, CompoundExpression):
            return node.negate() if negated else node
        # Apply De Morgan's Laws.
        operator = node.operator.negate() if negated else node.operator
        negated = negated != (node.operator == Operator.NOT)
        lhs_compound = node.resolve(node.lhs, negated)
        rhs_compound = node.resolve(node.rhs, negated)
        if operator == Operator.OR:
            return CompoundExpression(should=[lhs_compound, rhs_compound], minimum_should_match=1)
        if operator == Operator.AND:
            return CompoundExpression(must=[lhs_compound, rhs_compound])
        return lhs_compound

    def as_mql(self, compiler, connection):
        expression = self.resolve(self)
        return expression.as_mql(compiler, connection)


class SearchVector(SearchExpression):
    """
    Atlas Search expression that performs vector similarity search on embedded vectors.

    This expression uses the **knnBeta** operator to find documents whose vector
    embeddings are most similar to a given query vector.

    Example:
        SearchVector("embedding", [0.1, 0.2, 0.3], limit=10, num_candidates=100)

    Args:
        path: The document path to the vector field (as string or expression).
        query_vector: The query vector to compare against.
        limit: Maximum number of matching documents to return.
        num_candidates: Optional number of candidates to consider during search.
        exact: Optional flag to enforce exact matching.
        filter: Optional filter expression to narrow candidate documents.

    Reference: https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-stage/
    """

    def __init__(
        self,
        path,
        query_vector,
        limit,
        num_candidates=None,
        exact=None,
        filter=None,
    ):
        self.path = cast_as_field(path)
        self.query_vector = cast_as_value(query_vector)
        self.limit = cast_as_value(limit)
        self.num_candidates = cast_as_value(num_candidates)
        self.exact = cast_as_value(exact)
        self.filter = cast_as_value(filter)
        super().__init__()

    def __invert__(self):
        return ValueError("SearchVector cannot be negated")

    def __and__(self, other):
        raise NotSupportedError("SearchVector cannot be combined")

    def __rand__(self, other):
        raise NotSupportedError("SearchVector cannot be combined")

    def __or__(self, other):
        raise NotSupportedError("SearchVector cannot be combined")

    def __ror__(self, other):
        raise NotSupportedError("SearchVector cannot be combined")

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def get_source_expressions(self):
        return [
            self.path,
            self.query_vector,
            self.limit,
            self.num_candidates,
            self.exact,
            self.filter,
        ]

    def set_source_expressions(self, exprs):
        (
            self.path,
            self.query_vector,
            self.limit,
            self.num_candidates,
            self.exact,
            self.filter,
        ) = exprs

    def _get_query_index(self, fields, compiler):
        for search_indexes in compiler.collection.list_search_indexes():
            if search_indexes["type"] == "vectorSearch":
                index_field = {
                    field["path"] for field in search_indexes["latestDefinition"]["fields"]
                }
                if fields.issubset(index_field):
                    return search_indexes["name"]
        return "default"

    def as_mql(self, compiler, connection):
        params = {
            "index": self._get_query_index(self.get_search_fields(compiler, connection), compiler),
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "queryVector": self.query_vector.value,
            "limit": self.limit.value,
        }
        if self.num_candidates is not None:
            params["numCandidates"] = self.num_candidates.value
        if self.exact is not None:
            params["exact"] = self.exact.value
        if self.filter is not None:
            params["filter"] = self.filter.as_mql(compiler, connection)
        return {"$vectorSearch": params}


class SearchScoreOption(Expression):
    """Class to mutate scoring on a search operation"""

    def __init__(self, definitions=None):
        self._definitions = definitions

    def as_mql(self, compiler, connection):
        return self._definitions
