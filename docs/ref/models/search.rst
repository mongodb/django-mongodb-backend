====================
Atlas Search queries
====================

.. currentmodule:: django_mongodb_backend.expressions

.. versionadded:: 5.2.0b2

Atlas Search expressions
========================

Atlas search expressions ease the use of MongoDB Atlas search's :doc:`full text
and vector search engine <atlas:atlas-search>`.

For the examples in this document, we'll use the following models::

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
----------------

.. class:: SearchEquals(path, value, *, score=None)

Matches documents where a field is equal to a given value.

Uses the :doc:`equals operator <atlas:atlas-search/equals>` to perform exact
matches on fields indexed in a MongoDB Atlas Search index.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchEquals
    >>> Article.objects.annotate(score=SearchEquals(path="headline", value="title"))
    <QuerySet [<Article: headline: title>]>

**Arguments:**

- ``path``: The document path to the field.
- ``value``: The value to match.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchAutocomplete``
----------------------

.. class:: SearchAutocomplete(path, query, *, fuzzy=None, token_order=None, score=None)

Enables autocomplete behavior on string fields.

Uses the :doc:`autocomplete operator <atlas:atlas-search/autocomplete>` to
match the input query against a field indexed with ``"type": "autocomplete"``
in a MongoDB Atlas Search index.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchAutocomplete
    >>> Article.objects.annotate(score=SearchAutocomplete(path="headline", query="harry"))
    <QuerySet [
       <Article: title: Harry and the History of Magic>,
       <Article: title: Harry Potter’s Cultural Impact on Literature>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``query``: The value to match.
- ``fuzzy``: A dictionary of fuzzy matching options, e.g., ``{"maxEdits": 1}``.
- ``token_order``: Controls token sequence behavior. Accepts values like
  ``"sequential"`` or ``"any"``.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchExists``
----------------

.. class:: SearchExists(path, *, score=None)

Matches documents where a field exists.

Uses the :doc:`exists operator <atlas:atlas-search/exists>` to check whether
the specified path is present in the document. It's useful for filtering
documents that include (or exclude) optional fields.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchExists
    >>> Article.objects.annotate(score=SearchExists(path="writer__name"))
    <QuerySet [
        <Article: title: Exploring Atlas Search Capabilities (by Ana)>,
        <Article: title: Indexing Strategies with MongoDB (by Miguel)>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchIn``
------------

.. class:: SearchIn(path, value, *, score=None)

Matches documents where a field's value is in a given list.

Uses the :doc:`in operator <atlas:atlas-search/in>` to match documents whose
field contains a value from the provided array.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchIn
    >>> Article.objects.annotate(score=SearchIn(path="number", value=[1, 2]))
    <QuerySet [
        <Article: title: Introduction to Atlas Search (number=1)>,
        <Article: title: Boosting Relevance Scores (number=2)>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``value``: The value to match.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchPhrase``
----------------

.. class:: SearchPhrase(path, query, *, slop=None, synonyms=None, score=None)

Matches a phrase in the specified field.

Uses the :doc:`phrase operator <atlas:atlas-search/phrase>` to find exact or
near-exact sequences of terms. It supports optional slop (term distance) and
synonym mappings defined in the Atlas Search index.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchPhrase
    >>> Article.objects.annotate(
    ...     score=SearchPhrase(path="body", query="climate change", slop=2)
    ... )
    <QuerySet [
        <Article: title: Understanding Climate Change Models>,
        <Article: title: The Impact of Rapid Change in Climate Systems>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``query``: The value to match.
- ``slop``: The maximum number of terms allowed between phrase terms.
- ``synonyms``: The name of a synonym mapping defined in your Atlas index.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchQueryString``
---------------------

.. class:: SearchQueryString(path, query, *, score=None)

Matches using a Lucene-style query string.

Uses the :doc:`queryString operator <atlas:atlas-search/queryString>` to parse
and execute full-text queries written in a simplified Lucene syntax. It
supports features like boolean operators, wildcards, and field-specific terms.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchQueryString
    >>> Article.objects.annotate(
    ...     score=SearchQueryString(path="body", query="django AND (search OR query)")
    ... )
    <QuerySet [
        <Article: title: Building Search Features with Django>,
        <Article: title: Advanced Query Techniques in Django ORM>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``query``: A Lucene-style query string.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.


``SearchRange``
---------------

.. class:: SearchRange(path, *, lt=None, lte=None, gt=None, gte=None, score=None)

Filters documents within a specified range of values.

Uses the :doc:`range operator <atlas:atlas-search/range>` to match numeric,
date, or other comparable fields based on upper and/or lower bounds.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchRange
    >>> Article.objects.annotate(score=SearchRange(path="number", gte=2000, lt=2020))
    <QuerySet [
        <Article: title: Data Trends from the Early 2000s (number=2003)>,
        <Article: title: Pre-2020 Web Framework Evolution (number=2015)>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``lt``: Exclusive upper bound (``<``)
- ``lte``: Inclusive upper bound (``<=``)
- ``gt``: Exclusive lower bound (``>``)
- ``gte``: Inclusive lower bound (``>=``)
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchRegex``
---------------

.. class:: SearchRegex(path, query, *, allow_analyzed_field=None, score=None)

Matches string fields using a regular expression.

Uses the :doc:`regex operator <atlas:atlas-search/regex>` to match a regular
expression pattern to the contents of a specified field.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchRegex
    >>> Article.objects.annotate(score=SearchRegex(path="headline", query=r"^Breaking_"))
    <QuerySet [
        <Article: title: Breaking_News: MongoDB Release Update>,
        <Article: title: Breaking_Changes in Atlas Search API>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``query``: The regular expression to match.
- ``allow_analyzed_field``: A boolean indicating whether to match against an
  analyzed field. ``False`` if not specified.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchText``
--------------

.. class:: SearchText(path, query, *, fuzzy=None, match_criteria=None, synonyms=None, score=None)

Performs full-text search using the :doc:`text operator
<atlas:atlas-search/text>`.

Matches terms in the specified field. Supports fuzzy matching, match criteria,
and synonym mappings.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchText
    >>> Article.objects.annotate(
    ...     score=SearchText(
    ...         path="body", query="mongodb", fuzzy={"maxEdits": 1}, match_criteria="all"
    ...     )
    ... )
    <QuerySet [
        <Article: title: MongoDB Atlas: Features and Benefits>,
        <Article: title: Understanding MongoDB Query Optimization>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``query``: The search term or phrase.
- ``fuzzy``: A dictionary of fuzzy matching options, e.g., ``{"maxEdits": 1}``.
- ``match_criteria``: Whether to match ``"all"`` or ``"any"`` terms (defaults
  to Atlas Search behavior).
- ``synonyms``: The name of a synonym mapping defined in your Atlas index.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchWildcard``
------------------

.. class:: SearchWildcard(path, query, allow_analyzed_field=None, score=None)

Matches strings using wildcard patterns.

Uses the :doc:`wildcard operator <atlas:atlas-search/wildcard>` to search for
terms matching a pattern with ``*`` (any sequence of characters) and ``?`` (any
single character) wildcards.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchWildcard
    >>> Article.objects.annotate(
    ...     score=SearchWildcard(path="headline", query="report_202?_final*")
    ... )
    <QuerySet [
        <Article: title: report_2021_final_summary>,
        <Article: title: report_2022_final_review>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``query``: A wildcard string that may include ``*`` and ``?``.
- ``allow_analyzed_field``: A boolean indicating whether to match against an
  analyzed field. ``False`` if not specified.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchGeoShape``
------------------

.. class:: SearchGeoShape(path, relation, geometry, *, score=None)

Filters documents based on spatial relationships with a geometry.

Uses the :doc:`geoShape operator <atlas:atlas-search/geoShape>` to match
documents where a geo field has a specified spatial relation to a given GeoJSON
geometry.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchGeoShape
    >>> polygon = {"type": "Polygon", "coordinates": [[[0, 0], [3, 6], [6, 1], [0, 0]]]}
    >>> Article.objects.annotate(
    ...     score=SearchGeoShape(path="location", relation="within", geometry=polygon)
    ... )
    <QuerySet [
        <Article: title: Local Environmental Impacts Study (location: [2, 3])>,
       <Article: title: Urban Planning in District 5 (location: [1, 2])>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``relation``: The spatial relation to test. Valid values are ``"contains"``,
  ``"disjoint"``, ``"intersects"``, and ``"within"``.
- ``geometry``: A GeoJSON geometry object to compare against.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchGeoWithin``
-------------------

.. class:: SearchGeoWithin(path, kind, geometry, *, score=None)

Filters documents with geo fields contained within a specified shape.

Uses the :doc:`geoWithin operator <atlas:atlas-search/geoWithin>` to match
documents where the geo field lies entirely within the provided GeoJSON
geometry.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchGeoWithin
    >>> polygon = {"type": "Polygon", "coordinates": [[[0, 0], [3, 6], [6, 1], [0, 0]]]}
    >>> Article.objects.annotate(
    ...     score=SearchGeoWithin(path="location", kind="geometry", geo_object=polygon)
    ... )
    <QuerySet [
        <Article: title: Local Environmental Impacts Study (location: [2, 3])>,
       <Article: title: Urban Planning in District 5 (location: [1, 2])>
    ]>

**Arguments:**

- ``path``: The document path to the field.
- ``kind``: The GeoJSON geometry type: ``"circle"``, ``"box"``, or
  ``"geometry"``.
- ``geo_object``: The GeoJSON geometry defining the spatial boundary.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``SearchMoreLikeThis``
----------------------

.. class:: SearchMoreLikeThis(documents, *, score=None)

Finds documents similar to the provided examples.

Uses the :doc:`moreLikeThis operator <atlas:atlas-search/morelikethis>` to
retrieve documents that resemble one or more example documents.

.. code-block:: pycon

    >>> from bson import ObjectId
    >>> from django_mongodb_backend.expressions import SearchMoreLikeThis
    >>> Article.objects.annotate(
    ...     score=SearchMoreLikeThis(
    ...         [{"_id": ObjectId("66cabc1234567890abcdefff")}, {"title": "Example"}]
    ...     )
    ... )
    <QuerySet [
        <Article: title: Example Case Study on Data Indexing>,
        <Article: title: Similar Approaches in Database Design>
    ]>

**Arguments:**

- ``documents``: List of example documents or expressions that serve as
  references for similarity.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

``CompoundExpression``
======================

.. class:: CompoundExpression(must=None, must_not=None, should=None, filter=None, score=None, minimum_should_match=None)

Compound expression that combines multiple search clauses using boolean logic.

Uses the :doc:`compound operator <atlas:atlas-search/compound>` to combine
sub-expressions with ``must``, ``must_not``, ``should``, and ``filter``
clauses. It enables fine-grained control over how multiple conditions
contribute to document matching and scoring.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import CompoundExpression, SearchText
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

**Arguments:**

- ``must``: A list of expressions that **must** match.
- ``must_not``: A list of expressions that **must not** match.
- ``should``: A list of optional expressions that **should** match. These can
  improve scoring.
- ``filter``: A list of expressions used for filtering without affecting
  relevance scoring.
- ``minimum_should_match``: The minimum number of ``should`` clauses that must
  match.
- ``score``: A :class:`SearchScoreOption` to tune the relevance score.

Combinable expressions
----------------------

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

``SearchVector``
================

.. class:: SearchVector(path, query_vector, limit, *, num_candidates=None, exact=None, filter=None)

Performs vector similarity search using the :doc:`$vectorSearch stage
<atlas:atlas-vector-search/vector-search-stage>`.

Retrieves documents whose vector field is most similar to a given query vector,
using either approximate or exact nearest neighbor search.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchVector
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


**Arguments:**

- ``path``: The document path to the field.
- ``query_vector``: The input vector used for similarity comparison.
- ``limit``: The maximum number of matching documents to return.
- ``num_candidates``: The number of nearest neighbors to use during the search.
  Required if ``exact`` is ``False`` or omitted.
- ``exact``:  A boolean indicating whether run exact (``True``) or approximate
  (``False``) nearest neighbor search. Required if ``num_candidates`` is
  omitted. If omitted, defaults to ``False``.
- ``filter``: A MQL filter expression to restrict the candidate documents.

.. warning::

    ``SearchVector`` expressions cannot be combined using logical operators
    such as ``&``, ``|``, or ``~``. Attempting to do so will raise an error.

``SearchVector`` is typically used on its own in the ``score`` annotation and
cannot be nested or composed.

``SearchScoreOption``
=====================

.. class:: SearchScoreOption(definitions=None)

Controls the relevance score in an Atlas Search expression.

It can be passed to most Atlas Search operators through the ``score`` argument
to customize how MongoDB calculates and applies scoring.

It directly maps to the :doc:`score option <atlas:atlas-search/scoring>` of
the relevant Atlas Search operator.

.. code-block:: pycon

    >>> from django_mongodb_backend.expressions import SearchText, SearchScoreOption
    >>> boost = SearchScoreOption({"boost": {"value": 5}})
    >>> Article.objects.annotate(score=SearchText(path="body", query="django", score=boost))
    <QuerySet [<Article: Article object (6882f074359a4b191381b2e4)>]>

Accepted options depend on the underlying operator and may include:

- ``boost``: Increases the score of documents matching a specific clause.
- ``constant``: Applies a fixed score to all matches.
- ``function``: Uses a mathematical function to compute the score dynamically.
- ``path``: Scores documents based on the value of a field.

The ``search`` lookup
======================

Use the ``search`` lookup on :class:`~django.db.models.CharField` and
:class:`~django.db.models.TextField` to perform full-text searches using the
:doc:`text operator <atlas:atlas-search/text>`:

.. code-block:: pycon

    >>> Article.objects.filter(headline__search="mongodb")
    <QuerySet [
        <Article: title: Introduction to MongoDB>,
        <Article: title: MongoDB Atlas Overview>
    ]>

Internally, it creates a :class:`SearchText` expression and returns matching
documents with a score greater than or equal to zero.
