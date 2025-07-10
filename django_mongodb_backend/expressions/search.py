from django.db import NotSupportedError
from django.db.models import Expression, FloatField


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
        return self._combine(self, Operator(Operator.OR), other)


class SearchExpression(SearchCombinable, Expression):
    output_field = FloatField()

    def __str__(self):
        cls = self.identity[0]
        kwargs = dict(self.identity[1:])
        arg_str = ", ".join(f"{k}={v!r}" for k, v in kwargs.items())
        return f"{cls.__name__}({arg_str})"

    def __repr__(self):
        return str(self)

    def as_sql(self, compiler, connection):
        return "", []

    def _get_query_index(self, fields, compiler):
        fields = set(fields)
        for search_indexes in compiler.collection.list_search_indexes():
            mappings = search_indexes["latestDefinition"]["mappings"]
            if mappings["dynamic"] or fields.issubset(set(mappings["fields"])):
                return search_indexes["name"]
        return "default"

    def search_operator(self):
        raise NotImplementedError

    def as_mql(self, compiler, connection):
        index = self._get_query_index(self.get_search_fields(), compiler)
        return {"$search": {**self.search_operator(), "index": index}}


class SearchAutocomplete(SearchExpression):
    def __init__(self, path, query, fuzzy=None, score=None):
        self.path = path
        self.query = query
        self.fuzzy = fuzzy
        self.score = score
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "path": self.path,
            "query": self.query,
        }
        if self.score is not None:
            params["score"] = self.score
        if self.fuzzy is not None:
            params["fuzzy"] = self.fuzzy
        return {"autocomplete": params}


class SearchEquals(SearchExpression):
    def __init__(self, path, value, score=None):
        self.path = path
        self.value = value
        self.score = score
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "path": self.path,
            "value": self.value,
        }
        if self.score is not None:
            params["score"] = self.score
        return {"equals": params}


class SearchExists(SearchExpression):
    def __init__(self, path, score=None):
        self.path = path
        self.score = score
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "path": self.path,
        }
        if self.score is not None:
            params["score"] = self.score
        return {"exists": params}


class SearchIn(SearchExpression):
    def __init__(self, path, value, score=None):
        self.path = path
        self.value = value
        self.score = score
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "path": self.path,
            "value": self.value,
        }
        if self.score is not None:
            params["score"] = self.score
        return {"in": params}


class SearchPhrase(SearchExpression):
    def __init__(self, path, query, slop=None, synonyms=None, score=None):
        self.path = path
        self.query = query
        self.score = score
        self.slop = slop
        self.synonyms = synonyms
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "path": self.path,
            "query": self.query,
        }
        if self.score is not None:
            params["score"] = self.score
        if self.slop is not None:
            params["slop"] = self.slop
        if self.synonyms is not None:
            params["synonyms"] = self.synonyms
        return {"phrase": params}


class SearchQueryString(SearchExpression):
    def __init__(self, path, query, score=None):
        self.path = path
        self.query = query
        self.score = score
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "defaultPath": self.path,
            "query": self.query,
        }
        if self.score is not None:
            params["score"] = self.score
        return {"queryString": params}


class SearchRange(SearchExpression):
    def __init__(self, path, lt=None, lte=None, gt=None, gte=None, score=None):
        self.path = path
        self.lt = lt
        self.lte = lte
        self.gt = gt
        self.gte = gte
        self.score = score
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "path": self.path,
        }
        if self.score is not None:
            params["score"] = self.score
        if self.lt is not None:
            params["lt"] = self.lt
        if self.lte is not None:
            params["lte"] = self.lte
        if self.gt is not None:
            params["gt"] = self.gt
        if self.gte is not None:
            params["gte"] = self.gte
        return {"range": params}


class SearchRegex(SearchExpression):
    def __init__(self, path, query, allow_analyzed_field=None, score=None):
        self.path = path
        self.query = query
        self.allow_analyzed_field = allow_analyzed_field
        self.score = score
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "path": self.path,
            "query": self.query,
        }
        if self.score:
            params["score"] = self.score
        if self.allow_analyzed_field is not None:
            params["allowAnalyzedField"] = self.allow_analyzed_field
        return {"regex": params}


class SearchText(SearchExpression):
    def __init__(self, path, query, fuzzy=None, match_criteria=None, synonyms=None, score=None):
        self.path = path
        self.query = query
        self.fuzzy = fuzzy
        self.match_criteria = match_criteria
        self.synonyms = synonyms
        self.score = score
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "path": self.path,
            "query": self.query,
        }
        if self.score:
            params["score"] = self.score
        if self.fuzzy is not None:
            params["fuzzy"] = self.fuzzy
        if self.match_criteria is not None:
            params["matchCriteria"] = self.match_criteria
        if self.synonyms is not None:
            params["synonyms"] = self.synonyms
        return {"text": params}


class SearchWildcard(SearchExpression):
    def __init__(self, path, query, allow_analyzed_field=None, score=None):
        self.path = path
        self.query = query
        self.allow_analyzed_field = allow_analyzed_field
        self.score = score
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "path": self.path,
            "query": self.query,
        }
        if self.score:
            params["score"] = self.score
        if self.allow_analyzed_field is not None:
            params["allowAnalyzedField"] = self.allow_analyzed_field
        return {"wildcard": params}


class SearchGeoShape(SearchExpression):
    def __init__(self, path, relation, geometry, score=None):
        self.path = path
        self.relation = relation
        self.geometry = geometry
        self.score = score
        super().__init__()

    def get_search_fields(self):
        return {self.path}

    def search_operator(self):
        params = {
            "path": self.path,
            "relation": self.relation,
            "geometry": self.geometry,
        }
        if self.score:
            params["score"] = self.score
        return {"geoShape": params}


class SearchGeoWithin(SearchExpression):
    def __init__(self, path, kind, geo_object, score=None):
        self.path = path
        self.kind = kind
        self.geo_object = geo_object
        self.score = score
        super().__init__()

    def search_operator(self):
        params = {
            "path": self.path,
            self.kind: self.geo_object,
        }
        if self.score:
            params["score"] = self.score
        return {"geoWithin": params}

    def get_search_fields(self):
        return {self.path}


class SearchMoreLikeThis(SearchExpression):
    def __init__(self, documents, score=None):
        self.documents = documents
        self.score = score
        super().__init__()

    def search_operator(self):
        params = {
            "like": self.documents,
        }
        if self.score:
            params["score"] = self.score
        return {"moreLikeThis": params}

    def get_search_fields(self):
        needed_fields = set()
        for doc in self.documents:
            needed_fields.update(set(doc.keys()))
        return needed_fields


class CompoundExpression(SearchExpression):
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

    def get_search_fields(self):
        fields = set()
        for clause in self.must + self.should + self.filter + self.must_not:
            fields.update(clause.get_search_fields())
        return fields

    def search_operator(self):
        params = {}
        if self.must:
            params["must"] = [clause.search_operator() for clause in self.must]
        if self.must_not:
            params["mustNot"] = [clause.search_operator() for clause in self.must_not]
        if self.should:
            params["should"] = [clause.search_operator() for clause in self.should]
        if self.filter:
            params["filter"] = [clause.search_operator() for clause in self.filter]
        if self.minimum_should_match is not None:
            params["minimumShouldMatch"] = self.minimum_should_match

        return {"compound": params}

    def negate(self):
        return CompoundExpression(must_not=[self])


class CombinedSearchExpression(SearchExpression):
    def __init__(self, lhs, operator, rhs):
        self.lhs = lhs
        self.operator = operator
        self.rhs = rhs

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
    def __init__(
        self,
        path,
        query_vector,
        limit,
        num_candidates=None,
        exact=None,
        filter=None,
    ):
        self.path = path
        self.query_vector = query_vector
        self.limit = limit
        self.num_candidates = num_candidates
        self.exact = exact
        self.filter = filter
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

    def get_search_fields(self):
        return {self.path}

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
            "index": self._get_query_index(self.get_search_fields(), compiler),
            "path": self.path,
            "queryVector": self.query_vector,
            "limit": self.limit,
        }
        if self.num_candidates is not None:
            params["numCandidates"] = self.num_candidates
        if self.exact is not None:
            params["exact"] = self.exact
        if self.filter is not None:
            params["filter"] = self.filter
        return {"$vectorSearch": params}


class SearchScoreOption:
    """Class to mutate scoring on a search operation"""

    def __init__(self, definitions=None):
        self.definitions = definitions
