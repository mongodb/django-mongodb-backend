from django.db.models import Expression


class SearchExpression(Expression):
    """Base expression node for MongoDB Atlas `$search` stages."""


class SearchVector(SearchExpression):
    """
    Atlas Search expression that performs vector similarity search on embedded vectors.
    """
