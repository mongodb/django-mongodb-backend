__version__ = "5.2.0"

# Check Django compatibility before other imports which may fail if the
# wrong version of Django is installed.
from .utils import check_django_compatability, parse_uri

check_django_compatability()

from .aggregates import register_aggregates  # noqa: E402
from .checks import register_checks  # noqa: E402
from .expressions.builtins import register_expressions  # noqa: E402
from .fields import register_fields  # noqa: E402
from .functions import register_functions  # noqa: E402
from .indexes import register_indexes  # noqa: E402
from .lookups import register_lookups  # noqa: E402
from .query import register_nodes  # noqa: E402

__all__ = ["parse_uri"]

register_aggregates()
register_checks()
register_expressions()
register_fields()
register_functions()
register_indexes()
register_lookups()
register_nodes()
