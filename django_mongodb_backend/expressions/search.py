from django.db import NotSupportedError
from django.db.models import CharField, Expression, FloatField, TextField
from django.db.models.expressions import F, Value
from django.db.models.lookups import Lookup

from ..query_utils import process_lhs, process_rhs


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
    """
    Base expression for MongoDB Atlas `$search` stage.

    Subclasses produce the operator document placed under $search and expose
    the stage to queryset methods such as annotate(), filter(), or order_by().
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

    def get_source_expressions(self):
        return [self.path]

    def set_source_expressions(self, exprs):
        (self.path,) = exprs

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
    Match input using the `autocomplete` operator.

    Enables autocomplete behavior by querying against a field indexed as
    `"type": "autocomplete"`.

    Example:
        SearchAutocomplete("title", "harry", fuzzy={"maxEdits": 1})

    Args:
        path: The document path to search (as string or expression).
        query: The input string to autocomplete.
        fuzzy: Optional dictionary of fuzzy matching parameters.
        token_order: Optional value for `"tokenOrder"`; controls sequential vs.
                     any-order token matching.
        score: Optional[SearchScore] expression to adjust score relevance
               (e.g., `{"boost": {"value": 5}}`).

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/autocomplete/
    """

    def __init__(self, path, query, *, fuzzy=None, token_order=None, score=None):
        self.path = cast_as_field(path)
        self.query = query
        self.fuzzy = fuzzy
        self.token_order = token_order
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.fuzzy is not None:
            params["fuzzy"] = self.fuzzy
        if self.token_order:
            params["tokenOrder"] = self.token_order
        return {"autocomplete": params}


class SearchEquals(SearchExpression):
    """
    Match documents with a field equal to the given value (`equals` operator).

    Example:
        SearchEquals("category", "fiction")

    Args:
        path: The document path to compare (as string or expression).
        value: The exact value to match against.
        score: Optional[SearchScore] expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/equals/
    """

    def __init__(self, path, value, *, score=None):
        self.path = cast_as_field(path)
        self.value = value
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "value": self.value,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"equals": params}


class SearchExists(SearchExpression):
    """
    Match documents where a field exists.

    Use the `exists` operator to check whether a given path is present in the
    document. Useful for filtering documents that include (or exclude) optional
    fields.

    Example:
        SearchExists("metadata__author")

    Args:
        path: The document path to check (as string or expression).
        score: Optional[SearchScore] expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/exists/
    """

    def __init__(self, path, *, score=None):
        self.path = cast_as_field(path)
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"exists": params}


class SearchIn(SearchExpression):
    """
    Match documents where the field value is in a given list (`in` operator).

    Example:
        SearchIn("status", ["pending", "approved", "rejected"])

    Args:
        path: The document path to match against (as string or expression).
        value: A list of values to check for membership.
        score: Optional[SearchScore] expression to adjust the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/in/
    """

    def __init__(self, path, value, *, score=None):
        self.path = cast_as_field(path)
        self.value = value
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "value": self.value,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"in": params}


class SearchPhrase(SearchExpression):
    """
    Match a phrase in the specified field.

    Use the `phrase` operator to search for exact or near exact sequences of
    terms. It supports optional slop (word distance) and synonym sets.

    Example:
        SearchPhrase("description__text", "climate change", slop=2)

    Args:
        path: The document path to search (as string or expression).
        query: The phrase to match as a single string or list of terms.
        slop: Optional maximum word distance allowed between phrase terms.
        synonyms: Optional name of a synonym mapping defined in an Atlas index.
        score: Optional[SearchScore] expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/phrase/
    """

    def __init__(self, path, query, *, slop=None, synonyms=None, score=None):
        self.path = cast_as_field(path)
        self.query = query
        self.slop = slop
        self.synonyms = synonyms
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.slop:
            params["slop"] = self.slop
        if self.synonyms:
            params["synonyms"] = self.synonyms
        return {"phrase": params}


class SearchQueryString(SearchExpression):
    """
    Match using a Lucene-style query string.

    Use the `queryString` operator to parse and execute full-text queries
    written in a simplified Lucene syntax. It supports advanced constructs like
    boolean operators, wildcards, and field-specific terms.

    Example:
        SearchQueryString("content__text", "django AND (search OR query)")

    Args:
        path: The document path to query (as string or expression).
        query: The Lucene-style query string.
        score: Optional[SearchScore] expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/queryString/
    """

    def __init__(self, path, query, *, score=None):
        self.path = cast_as_field(path)
        self.query = query
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "defaultPath": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"queryString": params}


class SearchRange(SearchExpression):
    """
    Filter documents within a range of values.

    Uses the `range` operator to match numeric, date, or other comparable
    fields based on upper and/or lower bounds.

    Example:
        SearchRange("published__year", gte=2000, lt=2020)

    Args:
        path: The document path to filter (as string or expression).
        lt: Optional exclusive upper bound (<).
        lte: Optional inclusive upper bound (≤).
        gt: Optional exclusive lower bound (>).
        gte: Optional inclusive lower bound (≥).
        score: Optional[SearchScore] expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/range/
    """

    def __init__(self, path, *, lt=None, lte=None, gt=None, gte=None, score=None):
        self.path = cast_as_field(path)
        self.lt = lt
        self.lte = lte
        self.gt = gt
        self.gte = gte
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.lt:
            params["lt"] = self.lt
        if self.lte:
            params["lte"] = self.lte
        if self.gt:
            params["gt"] = self.gt
        if self.gte:
            params["gte"] = self.gte
        return {"range": params}


class SearchRegex(SearchExpression):
    """
    Match strings using a regular expression (`regex` operator).

    Example:
        SearchRegex("username", r"^admin_")

    Args:
        path: The document path to match (as string or expression).
        query: The regular expression pattern to apply.
        allow_analyzed_field: Whether to allow matching against analyzed fields.
                              The server's default is False.
        score: Optional[SearchScore] expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/regex/
    """

    def __init__(self, path, query, *, allow_analyzed_field=None, score=None):
        self.path = cast_as_field(path)
        self.query = query
        self.allow_analyzed_field = allow_analyzed_field
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.allow_analyzed_field is not None:
            params["allowAnalyzedField"] = self.allow_analyzed_field
        return {"regex": params}


class SearchText(SearchExpression):
    """
    Perform full-text search using the `text` operator.

    Matches terms in a specified field with options for fuzzy matching, match
    criteria, and synonyms.

    Example:
        SearchText(
            "description__content",
            "mongodb",
            fuzzy={"maxEdits": 1},
            match_criteria="all",
        )

    Args:
        path: The document path to search (as string or expression).
        query: The search term or phrase.
        fuzzy: Optional dictionary to configure fuzzy matching parameters.
        match_criteria: Optional criteria for term matching (e.g., "all" or "any").
        synonyms: Optional name of a synonym mapping defined in an Atlas index.
        score: Optional[SearchScore] expression to adjust the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/text/
    """

    def __init__(self, path, query, *, fuzzy=None, match_criteria=None, synonyms=None, score=None):
        self.path = cast_as_field(path)
        self.query = query
        self.fuzzy = fuzzy
        self.match_criteria = match_criteria
        self.synonyms = synonyms
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.fuzzy is not None:
            params["fuzzy"] = self.fuzzy
        if self.match_criteria:
            params["matchCriteria"] = self.match_criteria
        if self.synonyms:
            params["synonyms"] = self.synonyms
        return {"text": params}


class SearchWildcard(SearchExpression):
    """
    Match strings using wildcard patterns.

    Use the `wildcard` operator to search for terms matching a pattern with
    `*` and `?` wildcards.

    Example:
        SearchWildcard("filename", "report_202?_final*")

    Args:
        path: The document path to search (as string or expression).
        query: The wildcard pattern to match.
        allow_analyzed_field: Whether to allow matching against analyzed fields.
                              The server's default is False.
        score: Optional[SearchScore] expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/wildcard/
    """

    def __init__(self, path, query, allow_analyzed_field=None, score=None):
        self.path = cast_as_field(path)
        self.query = query
        self.allow_analyzed_field = allow_analyzed_field
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "query": self.query,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        if self.allow_analyzed_field is not None:
            params["allowAnalyzedField"] = self.allow_analyzed_field
        return {"wildcard": params}


class SearchGeoShape(SearchExpression):
    """
    Filter documents by spatial relationship with a geometry.

    Uses the `geoShape` operator to match documents where a geo field relates
    to a specified geometry by a spatial relation.

    Example:
        SearchGeoShape(
            "location",
            "within",
            {"type": "Polygon", "coordinates": [...]},
        )

    Args:
        path: The document path to the geo field (as string or expression).
        relation: The spatial relation to test (e.g., "within", "intersects",
                  "disjoint").
        geometry: The GeoJSON geometry to compare against.
        score: Optional[SearchScore] expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/geoShape/
    """

    def __init__(self, path, relation, geometry, *, score=None):
        self.path = cast_as_field(path)
        self.relation = relation
        self.geometry = geometry
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            "relation": self.relation,
            "geometry": self.geometry,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"geoShape": params}


class SearchGeoWithin(SearchExpression):
    """
    Filter documents with geo fields contained within a specified shape.

    Use the `geoWithin` operator to match documents where the geo field lies
    entirely within the given geometry.

    Example:
        SearchGeoWithin(
            "location",
            "Polygon",
            {"type": "Polygon", "coordinates": [...]},
        )

    Args:
        path: The document path to the geo field (as string or expression).
        kind: The GeoJSON geometry type (e.g., "Polygon", "MultiPolygon").
        geometry: The GeoJSON geometry defining the boundary.
        score: Optional[SearchScore] expression to adjust the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/geoWithin/
    """

    def __init__(self, path, kind, geometry, *, score=None):
        self.path = cast_as_field(path)
        self.kind = kind
        self.geometry = geometry
        self.score = score
        super().__init__()

    def get_search_fields(self, compiler, connection):
        return {self.path.as_mql(compiler, connection, as_path=True)}

    def search_operator(self, compiler, connection):
        params = {
            "path": self.path.as_mql(compiler, connection, as_path=True),
            self.kind: self.geometry,
        }
        if self.score:
            params["score"] = self.score.as_mql(compiler, connection)
        return {"geoWithin": params}


class SearchMoreLikeThis(SearchExpression):
    """
    Find documents similar to given examples.

    Use the `moreLikeThis` operator to search for documents that resemble the
    specified sample documents.

    Example:
        SearchMoreLikeThis([{"_id": ObjectId("...")}, {"title": "Example"}])

    Args:
        documents: A list of example documents or expressions to find similar
                   documents.
        score: Optional[SearchScore] expression to modify the relevance score.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/morelikethis/
    """

    def __init__(self, documents, *, score=None):
        self.documents = documents
        self.score = score
        super().__init__()

    def get_source_expressions(self):
        return []

    def set_source_expressions(self, exprs):
        pass

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
    Combine multiple search clauses using boolean logic.

    Use the `compound` operator to allow fine-grained control by combining
    multiple sub-expressions with `must`, `must_not`, `should`, and `filter`
    clauses.

    Example:
        CompoundExpression(
            must=[expr1, expr2],
            must_not=[expr3],
            should=[expr4],
            minimum_should_match=1,
        )

    Args:
        must: List of expressions that **must** match.
        must_not: List of expressions that **must not** match.
        should: List of expressions that **should** match (optional relevance
                boost).
        filter: List of expressions to filter results without affecting
                relevance.
        score: Optional[SearchScore] expression to adjust scoring.
        minimum_should_match: Minimum number of `should` clauses that
                              must match.

    Reference: https://www.mongodb.com/docs/atlas/atlas-search/compound/
    """

    def __init__(
        self,
        *,
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

    def get_source_expressions(self):
        return []

    def set_source_expressions(self, exprs):
        pass

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
        if self.minimum_should_match:
            params["minimumShouldMatch"] = self.minimum_should_match
        return {"compound": params}

    def negate(self):
        return CompoundExpression(must_not=[self])


class CombinedSearchExpression(SearchExpression):
    """
    Combine two search expressions with a logical operator such as `and`, `or`,
    or `not`.

    Example:
        CombinedSearchExpression(expr1, "and", expr2)

    Args:
        lhs: The left-hand search expression.
        operator: The boolean operator as a string (e.g., "and", "or", "not").
        rhs: The right-hand search expression.
    """

    def __init__(self, lhs, operator, rhs):
        self.lhs = lhs
        self.operator = Operator(operator) if not isinstance(operator, Operator) else operator
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
        if operator == Operator.NOT:
            return node.resolve(node.lhs, not negated)
        lhs_compound = node.resolve(node.lhs, negated)
        rhs_compound = node.resolve(node.rhs, negated)
        if operator == Operator.AND:
            return CompoundExpression(must=[lhs_compound, rhs_compound])
        return CompoundExpression(should=[lhs_compound, rhs_compound], minimum_should_match=1)

    def as_mql(self, compiler, connection):
        expression = self.resolve(self)
        return expression.as_mql(compiler, connection)


class SearchVector(SearchExpression):
    """
    Perform vector similarity search using `$vectorSearch`.

    Use the `$vectorSearch` stage to retrieve documents whose vector embeddings
    are most similar to a given query vector, according to approximate or exact
    nearest-neighbor search.

    Example:
        SearchVector("embedding", [0.1, 0.2, 0.3], limit=10, num_candidates=100)

    Args:
        path: The document path to the vector field (as string or expression).
        query_vector: The query vector to compare against.
        limit: Maximum number of matching documents to return.
        num_candidates: Optional number of candidates to consider during search.
        exact: Optional flag to enforce exact matching. The server's default is
               False, meaning approximate matching.
        filter: Optional MQL filter expression to narrow candidate documents.

    Reference: https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-stage/
    """

    def __init__(
        self,
        path,
        query_vector,
        limit,
        *,
        num_candidates=None,
        exact=None,
        filter=None,
    ):
        self.path = cast_as_field(path)
        self.query_vector = query_vector
        self.limit = limit
        self.num_candidates = num_candidates
        self.exact = exact
        self.filter = filter
        super().__init__()

    def __invert__(self):
        raise NotSupportedError("SearchVector cannot be negated")

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
            "queryVector": self.query_vector,
            "limit": self.limit,
        }
        if self.num_candidates:
            params["numCandidates"] = self.num_candidates
        if self.exact:
            params["exact"] = self.exact
        if self.filter:
            params["filter"] = self.filter
        return {"$vectorSearch": params}


class SearchScoreOption(Expression):
    """Mutate scoring on a search operation."""

    def __init__(self, definitions=None):
        self._definitions = definitions

    def as_mql(self, compiler, connection):
        return self._definitions


class SearchTextLookup(Lookup):
    """Allow QuerySet.filter(<field_name>__search="...")"""

    lookup_name = "search"

    def __init__(self, lhs, rhs):
        super().__init__(lhs, rhs)
        self.lhs = SearchText(self.lhs, self.rhs)
        self.rhs = Value(0)

    def __str__(self):
        return f"SearchText({self.lhs}, {self.rhs})"

    def __repr__(self):
        return f"SearchText({self.lhs}, {self.rhs})"

    def as_mql(self, compiler, connection):
        lhs_mql = process_lhs(self, compiler, connection)
        value = process_rhs(self, compiler, connection)
        return {"$gte": [lhs_mql, value]}


CharField.register_lookup(SearchTextLookup)
TextField.register_lookup(SearchTextLookup)
