================
Atlas search
================

The database functions in the ``django_mongodb_backend.expressions.search``
module ease the use of MongoDB Atlas search's `full text and vector search
engine <https://www.mongodb.com/docs/atlas/atlas-search/>`_.

For the examples in this document, we'll use the following models:

.. code-block:: pycon

    from django.db import models
    from django_mongodb_backend.models import EmbeddedModel
    from django_mongodb_backend.fields import ArrayField, EmbeddedModelField

    class Writer(EmbeddedModel):
        name = models.CharField(max_length=10)


    class Article(models.Model):
        headline = models.CharField(max_length=100)
        number = models.IntegerField()
        body = models.TextField()
        location = models.JSONField(null=True)
        plot_embedding = ArrayField(models.FloatField(), size=3, null=True)
        writer = EmbeddedModelField(Writer, null=True)


``SearchEquals``
================
Atlas Search expression that matches documents where a field is equal to a
given value.

This expression uses the ``equals`` operator to perform exact matches
on fields indexed in a MongoDB Atlas Search index.

`SearchEquals docs <https://www.mongodb.com/docs/atlas/atlas-search/equals/>`_


.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchEquals
    >>> Article.objects.annotate(score=SearchEquals(path="headline", value="title"))
    <QuerySet [<Article: Article object (6882f074359a4b191381b2e4)>]>

The ``path`` argument can be either the name of a field (as a string), or a
:class:`~django.db.models.expressions.Col` instance. The ``value`` argument
must be a string or a :class:`~django.db.models.expressions.Value`.

``SearchEquals`` objects can be reused and combined with other search
expressions.

See :ref:`search-operations-combinable`


``SearchAutocomplete``
======================

Atlas Search expression that enables autocomplete behavior on string fields.

This expression uses the ``autocomplete`` operator to match the input query
against a field indexed with ``"type": "autocomplete"`` in a MongoDB Atlas
Search index.

`SearchAutocomplete docs <https://www.mongodb.com/docs/atlas/atlas-search/autocomplete/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchAutocomplete
    >>> Article.objects.annotate(score=SearchAutocomplete(path="headline", query="harry"))
    <QuerySet [
       <Article: title: Harry and the History of Magic>,
       <Article: title: Harry Potter’s Cultural Impact on Literature>
    ]>

The ``path`` argument specifies the field to search and can be a string or a
:class:`~django.db.models.expressions.Col`. The ``query`` is the user input
string to autocomplete and can be passed as a string or a
:class:`~django.db.models.expressions.Value`.

Optional arguments:

- ``fuzzy``: A dictionary with fuzzy matching options such as
  ``{"maxEdits": 1}``.
- ``token_order``: Controls token sequence behavior. Accepts values like
  ``"sequential"`` or ``"any"``.
- ``score``: An optional score expression such as ``{"boost": {"value": 5}}``.

``SearchAutocomplete`` expressions can be reused and composed with other
search expressions.

See also: :ref:`search-operations-combinable`


``SearchExists``
================

Atlas Search expression that matches documents where a field exists.

This expression uses the ``exists`` operator to check whether the specified
path is present in the document. It's useful for filtering documents that
include (or exclude) optional fields.

`SearchExists docs <https://www.mongodb.com/docs/atlas/atlas-search/exists/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchExists
    >>> Article.objects.annotate(score=SearchExists(path="writer__name"))
    <QuerySet [
        <Article: title: Exploring Atlas Search Capabilities (by Ana)>,
        <Article: title: Indexing Strategies with MongoDB (by Miguel)>
    ]>

The ``path`` argument specifies the document path to check and can be provided
as a string or a :class:`~django.db.models.expressions.Col`.

An optional ``score`` argument can be used to modify the relevance score of the
result.

``SearchExists`` expressions can be reused and combined with other search
expressions.

See also: :ref:`search-operations-combinable`


``SearchIn``
============

Atlas Search expression that matches documents where a field's value is in a
given list.

This expression uses the ``in`` operator to match documents whose field
contains a value from the provided array.

`SearchIn docs <https://www.mongodb.com/docs/atlas/atlas-search/in/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchIn
    >>> Article.objects.annotate(score=SearchIn(path="number", value=[1, 2]))
    <QuerySet [
        <Article: title: Introduction to Atlas Search (number=1)>,
        <Article: title: Boosting Relevance Scores (number=2)>
    ]>

The ``path`` argument can be the name of a field (as a string) or a
:class:`~django.db.models.expressions.Col`. The ``value`` must be a list
of values or a :class:`~django.db.models.expressions.Value`.

An optional ``score`` argument can be used to customize relevance scoring.

``SearchIn`` expressions can be reused and combined with other search
expressions.

See also: :ref:`search-operations-combinable`


``SearchPhrase``
================

Atlas Search expression that matches a phrase in the specified field.

This expression uses the ``phrase`` operator to find exact or near-exact
sequences of terms. It supports optional slop (term distance) and synonym
mappings defined in the Atlas Search index.

`SearchPhrase docs <https://www.mongodb.com/docs/atlas/atlas-search/phrase/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchPhrase
    >>> Article.objects.annotate(
    ...     score=SearchPhrase(path="body", query="climate change", slop=2)
    ... )
    <QuerySet [
        <Article: title: Understanding Climate Change Models>,
        <Article: title: The Impact of Rapid Change in Climate Systems>
    ]>

The ``path`` argument specifies the field to search and can be a string or a
:class:`~django.db.models.expressions.Col`. The ``query`` is the phrase to
match, passed as a string or a list of strings (terms).

Optional arguments:

- ``slop``: The maximum number of terms allowed between phrase terms.
- ``synonyms``: The name of a synonym mapping defined in your Atlas index.
- ``score``: An optional score expression to adjust relevance.

``SearchPhrase`` expressions can be reused and combined with other search
expressions.

See also: :ref:`search-operations-combinable`


``SearchQueryString``
=====================

Atlas Search expression that matches using a Lucene-style query string.

This expression uses the ``queryString`` operator to parse and execute
full-text queries written in a simplified Lucene syntax. It supports features
like boolean operators, wildcards, and field-specific terms.

`SearchQueryString docs <https://www.mongodb.com/docs/atlas/atlas-search/queryString/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchQueryString
    >>> Article.objects.annotate(
    ...     score=SearchQueryString(path="body", query="django AND (search OR query)")
    ... )
    <QuerySet [
        <Article: title: Building Search Features with Django>,
        <Article: title: Advanced Query Techniques in Django ORM>
    ]>

The ``path`` argument can be a string or a
:class:`~django.db.models.expressions.Col` representing the field to query.
The ``query`` argument is a Lucene-style query string.

An optional ``score`` argument may be used to adjust relevance scoring.

``SearchQueryString`` expressions can be reused and combined with other search
expressions.

See also: :ref:`search-operations-combinable`


``SearchRange``
===============

Atlas Search expression that filters documents within a specified range of
values.

This expression uses the ``range`` operator to match numeric, date, or other
comparable fields based on upper and/or lower bounds.

`SearchRange docs <https://www.mongodb.com/docs/atlas/atlas-search/range/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchRange
    >>> Article.objects.annotate(score=SearchRange(path="number", gte=2000, lt=2020))
    <QuerySet [
        <Article: title: Data Trends from the Early 2000s (number=2003)>,
        <Article: title: Pre-2020 Web Framework Evolution (number=2015)>
    ]>

The ``path`` argument specifies the field to filter and can be a string or a
:class:`~django.db.models.expressions.Col`.

Optional arguments:

- ``lt``: Exclusive upper bound (``<``)
- ``lte``: Inclusive upper bound (``<=``)
- ``gt``: Exclusive lower bound (``>``)
- ``gte``: Inclusive lower bound (``>=``)
- ``score``: An optional score expression to influence relevance

``SearchRange`` expressions can be reused and combined with other search
expressions.

See also: :ref:`search-operations-combinable`


``SearchRegex``
===============

Atlas Search expression that matches string fields using a regular expression.

This expression uses the ``regex`` operator to apply a regular expression
pattern to the contents of a specified field.

`SearchRegex docs <https://www.mongodb.com/docs/atlas/atlas-search/regex/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchRegex
    >>> Article.objects.annotate(score=SearchRegex(path="headline", query=r"^Breaking_"))
    <QuerySet [
        <Article: title: Breaking_News: MongoDB Release Update>,
        <Article: title: Breaking_Changes in Atlas Search API>
    ]>

The ``path`` argument specifies the field to search and can be provided as a
string or a :class:`~django.db.models.expressions.Col`. The ``query`` is a
regular expression string that will be applied to the field contents.

Optional arguments:

- ``allow_analyzed_field``: Boolean indicating whether to allow matching
  against analyzed fields (defaults to ``False``).
- ``score``: An optional score expression to adjust relevance.

``SearchRegex`` expressions can be reused and combined with other search
expressions.

See also: :ref:`search-operations-combinable`


``SearchText``
==============

Atlas Search expression that performs full-text search using the ``text``
operator.

This expression matches terms in the specified field and supports fuzzy
matching, match criteria, and synonym mappings.

`SearchText docs <https://www.mongodb.com/docs/atlas/atlas-search/text/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchText
    >>> Article.objects.annotate(
    ...     score=SearchText(
    ...         path="body", query="mongodb", fuzzy={"maxEdits": 1}, match_criteria="all"
    ...     )
    ... )
    <QuerySet [
        <Article: title: MongoDB Atlas: Features and Benefits>,
        <Article: title: Understanding MongoDB Query Optimization>
    ]>

The ``path`` argument specifies the field to search and can be provided as a
string or a :class:`~django.db.models.expressions.Col`. The ``query`` argument
is the search term or phrase.

Optional arguments:

- ``fuzzy``: A dictionary of fuzzy matching options, such as
  ``{"maxEdits": 1}``.
- ``match_criteria``: Whether to match ``"all"`` or ``"any"`` terms (defaults
  to Atlas Search behavior).
- ``synonyms``: The name of a synonym mapping defined in your Atlas index.
- ``score``: An optional expression to influence relevance scoring.

``SearchText`` expressions can be reused and combined with other search
    expressions.

See also: :ref:`search-operations-combinable`


``SearchWildcard``
==================

Atlas Search expression that matches strings using wildcard patterns.

This expression uses the ``wildcard`` operator to search for terms matching
a pattern with ``*`` (any sequence of characters) and ``?`` (any single
character) wildcards.

`SearchWildcard docs <https://www.mongodb.com/docs/atlas/atlas-search/wildcard/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchWildcard
    >>> Article.objects.annotate(
    ...     score=SearchWildcard(path="headline", query="report_202?_final*")
    ... )
    <QuerySet [
        <Article: title: report_2021_final_summary>,
        <Article: title: report_2022_final_review>
    ]>

The ``path`` argument specifies the field to search and can be a string or a
:class:`~django.db.models.expressions.Col`. The ``query`` is a wildcard string
that may include ``*`` and ``?``.

Optional arguments:

- ``allow_analyzed_field``: Boolean that allows matching against analyzed
  fields (defaults to ``False``).
- ``score``: An optional expression to adjust relevance.

``SearchWildcard`` expressions can be reused and combined with other search
expressions.

See also: :ref:`search-operations-combinable`


``SearchGeoShape``
==================

Atlas Search expression that filters documents based on spatial relationships
with a geometry.

This expression uses the ``geoShape`` operator to match documents where a geo
field has a specified spatial relation to a given GeoJSON geometry.

`SearchGeoShape docs <https://www.mongodb.com/docs/atlas/atlas-search/geoShape/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchGeoShape
    >>> polygon = {"type": "Polygon", "coordinates": [[[0, 0], [3, 6], [6, 1], [0, 0]]]}
    >>> Article.objects.annotate(
    ...     score=SearchGeoShape(path="location", relation="within", geometry=polygon)
    ... )
    <QuerySet [
        <Article: title: Local Environmental Impacts Study (location: [2, 3])>,
       <Article: title: Urban Planning in District 5 (location: [1, 2])>
    ]>

The ``path`` argument specifies the field to filter and can be a string or a
:class:`~django.db.models.expressions.Col`.

Required arguments:

- ``relation``: The spatial relation to test. Valid values include
    ``"within"``, ``"intersects"``, and ``"disjoint"``.
- ``geometry``: A GeoJSON geometry object to compare against.

Optional:

- ``score``: An optional expression to modify the relevance score.

``SearchGeoShape`` expressions can be reused and combined with other search
expressions.

See also: :ref:`search-operations-combinable`


``SearchGeoWithin``
===================

Atlas Search expression that filters documents with geo fields contained within
a specified shape.

This expression uses the ``geoWithin`` operator to match documents where the
geo field lies entirely within the provided GeoJSON geometry.

`SearchGeoWithin docs <https://www.mongodb.com/docs/atlas/atlas-search/geoWithin/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchGeoWithin
    >>> polygon = {"type": "Polygon", "coordinates": [[[0, 0], [3, 6], [6, 1], [0, 0]]]}
    >>> Article.objects.annotate(
    ...     score=SearchGeoWithin(path="location", kind="Polygon", geo_object=polygon)
    ... )
    <QuerySet [
        <Article: title: Local Environmental Impacts Study (location: [2, 3])>,
       <Article: title: Urban Planning in District 5 (location: [1, 2])>
    ]>

The ``path`` argument specifies the geo field to filter and can be a string or
a :class:`~django.db.models.expressions.Col`.

Required arguments:

- ``kind``: The GeoJSON geometry type ``circle``, ``box``, or ``geometry``.
- ``geo_object``: The GeoJSON geometry defining the spatial boundary.

Optional:

- ``score``: An optional expression to adjust the relevance score.

``SearchGeoWithin`` expressions can be reused and combined with other search
    expressions.

See also: :ref:`search-operations-combinable`


``SearchMoreLikeThis``
======================

Atlas Search expression that finds documents similar to the provided examples.

This expression uses the ``moreLikeThis`` operator to retrieve documents that
resemble one or more example documents.

`SearchMoreLikeThis docs <https://www.mongodb.com/docs/atlas/atlas-search/morelikethis/>`_

.. code-block:: pycon

    >>> from bson import ObjectId
    >>> from django_mongodb_backend.expressions.search import SearchMoreLikeThis
    >>> Article.objects.annotate(
    ...     score=SearchMoreLikeThis(
    ...         [{"_id": ObjectId("66cabc1234567890abcdefff")}, {"title": "Example"}]
    ...     )
    ... )
    <QuerySet [
        <Article: title: Example Case Study on Data Indexing>,
        <Article: title: Similar Approaches in Database Design>
    ]>

The ``documents`` argument must be a list of example documents or expressions
that serve as references for similarity.

Optional:

- ``score``: An optional expression to adjust the relevance score of the
  results.

``SearchMoreLikeThis`` expressions can be reused and combined with other search
expressions.

See also: :ref:`search-operations-combinable`


``CompoundExpression``
======================

Compound expression that combines multiple search clauses using boolean logic.

This expression uses the ``compound`` operator in MongoDB Atlas Search to
combine sub-expressions with ``must``, ``must_not``, ``should``, and ``filter``
clauses. It enables fine-grained control over how multiple conditions
contribute to document matching and scoring.

`CompoundExpression docs <https://www.mongodb.com/docs/atlas/atlas-search/compound/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import CompoundExpression, SearchText
    >>> expr1 = SearchText("headline", "mongodb")
    >>> expr2 = SearchText("body", "atlas")
    >>> expr3 = SearchText("body", "deprecated")
    >>> expr4 = SearchText("headline", "database")
    >>> Article.objects.annotate(
    ...     score=CompoundExpression(
    ...         must=[expr1, expr2], must_not=[expr3], should=[expr4], minimum_should_match=1
    ...     )
    ... )
    <QuerySet [<Article: title: MongoDB Atlas Database Performance Optimization>]>

Arguments:

- ``must``: A list of expressions that **must** match.
- ``must_not``: A list of expressions that **must not** match.
- ``should``: A list of optional expressions that **should** match.
    These can improve scoring.
- ``filter``: A list of expressions used for filtering without affecting
    relevance scoring.
- ``minimum_should_match``: The minimum number of ``should`` clauses that
    must match.
- ``score``: An optional expression to adjust the final score.

``CompoundExpression`` is useful for building advanced and flexible query
    logic in Atlas Search.

See also: :ref:`search-operations-combinable`


``CombinedSearchExpression``
============================

Expression that combines two Atlas Search expressions using a boolean operator.

This expression is used internally when combining search expressions with
Python’s bitwise operators (``&``, ``|``, ``~``), and corresponds to
logical operators such as ``and``, ``or``, and ``not``.

.. note::
   This expression is typically created when using the combinable interface
   (e.g., ``expr1 & expr2``). It can also be constructed manually.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import CombinedSearchExpression
    >>> expr1 = SearchText("headline", "mongodb")
    >>> expr2 = SearchText("body", "atlas")
    >>> CombinedSearchExpression(expr1, "and", expr2)
    CombinedSearchExpression(
        lhs=SearchText(
            path='headline',
            query='mongodb',
            fuzzy=None,
            match_criteria=None,
            synonyms=None,
            score=None
        ),
        operator='and',
        rhs=SearchText(
            path='body',
            query='atlas',
            fuzzy=None,
            match_criteria=None,
            synonyms=None,
            score=None
        )
    )

Args:

- ``lhs``: The left-hand side search expression.
- ``operator``: A string representing the logical operator (``"and"``, ``"or"``
  , or ``"not"``).
- ``rhs``: The right-hand side search expression.

This is the underlying expression used to support operator overloading in
Atlas Search expressions.

.. _search-operations-combinable:

**Combinable expressions**
--------------------------

All Atlas Search expressions subclassed from ``SearchExpression``
can be combined using Python's bitwise operators:

- ``&`` → ``and``
- ``|`` → ``or``
- ``~`` → ``not`` (unary)

This allows for more expressive and readable search logic:

.. code-block:: pycon

    >>> expr = SearchText("headline", "mongodb") & ~SearchText("body", "deprecated")
    >>> Article.objects.annotate(score=expr)
    <QuerySet [
        <Article: title: MongoDB Best Practices>,
        <Article: title: Modern MongoDB Features>
    ]>

Under the hood, these expressions are translated into
``CombinedSearchExpression`` instances.

``CombinedSearchExpression`` can also be reused and nested with other compound
expressions.


``SearchVector``
================

Atlas Search expression that performs vector similarity search using the
``$vectorSearch`` stage.

This expression retrieves documents whose vector field is most similar to a
given query vector, using either approximate or exact nearest-neighbor search.

`SearchVector docs <https://www.mongodb.com/docs/atlas/atlas-vector-search/vector-search-stage/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchVector
    >>> Article.objects.annotate(
    ...     score=SearchVector(
    ...         path="plot_embedding",
    ...         query_vector=[0.1, 0.2, 0.3],
    ...         limit=10,
    ...         num_candidates=100,
    ...         exact=False,
    ...     )
    ... )
    <QuerySet [<Article: Article object (6882f074359a4b191381b2e4)>]>

Arguments:

- ``path``: The document path to the vector field (string or
  :class:`~django.db.models.expressions.Col`).
- ``query_vector``: The input vector used for similarity comparison.
- ``limit``: The maximum number of matching documents to return.
- ``num_candidates``: (Optional) The number of candidate documents considered
  during search.
- ``exact``: (Optional) Whether to enforce exact search instead of approximate
  (defaults to ``False``).
- ``filter``: (Optional) A filter expression to restrict the candidate
  documents.

.. warning::

    ``SearchVector`` expressions cannot be combined using logical operators
    such as ``&``, ``|``, or ``~``. Attempting to do so will raise an error.

``SearchVector`` is typically used on its own in the ``score`` annotation and
cannot be nested or composed.


``SearchScoreOption``
=====================

Expression used to control or mutate the relevance score in an Atlas Search
expression.

This expression can be passed to most Atlas Search operators through the
``score`` argument to customize how MongoDB calculates and applies scoring.

It directly maps to the ``score`` option of the relevant Atlas Search operator.

`SearchScoreOption docs: <https://www.mongodb.com/docs/atlas/atlas-search/scoring/>`_

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions.search import SearchText, SearchScoreOption
    >>> boost = SearchScoreOption({"boost": {"value": 5}})
    >>> Article.objects.annotate(score=SearchText(path="body", query="django", score=boost))
    <QuerySet [<Article: Article object (6882f074359a4b191381b2e4)>]>

Accepted options depend on the underlying operator and may include:

- ``boost``: Increases the score of documents matching a specific clause.
- ``constant``: Applies a fixed score to all matches.
- ``function``: Uses a mathematical function to compute the score dynamically.
- ``path``: Scores documents based on the value of a field.

The ``SearchScoreOption`` is a low-level utility used to build the ``score``
subdocument and can be reused across multiple search expressions.

It is typically passed as the ``score`` parameter to any search expression that
supports it.


The ``search`` lookup
======================

Django lookup to enable Atlas Search full-text querying via the ``search``
lookup.

This lookup allows using the ``search`` lookup on Django ``CharField`` and
``TextField`` to perform Atlas Search ``text`` queries seamlessly within Django
ORM filters.

It internally creates a ``SearchText`` expression on the left-hand side and
compares its score with zero to filter matching documents.

.. code-block:: pycon

    >>> Article.objects.filter(headline__search="mongodb")
    <QuerySet [
        <Article: title: Introduction to MongoDB>,
        <Article: title: MongoDB Atlas Overview>
    ]>

The lookup is automatically registered on ``CharField`` and ``TextField``,
enabling expressions like ``fieldname__search='query'``.

Under the hood:

- The left-hand side of the lookup is wrapped into a ``SearchText`` expression.
- The lookup compiles to a MongoDB query that filters documents with a score
    greater or equal to zero.

This allows for concise and idiomatic integration of Atlas Search within Django
filters.
