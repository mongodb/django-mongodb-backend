__version__ = "6.0.1"

# Check Django compatibility before other imports which may fail if the
# wrong version of Django is installed.
from .utils import check_django_compatability

check_django_compatability()

from .aggregates import register_aggregates  # noqa: E402
from .expressions.builtins import register_expressions  # noqa: E402
from .fields import register_fields  # noqa: E402
from .functions import register_functions  # noqa: E402
from .indexes import register_indexes  # noqa: E402
from .lookups import register_lookups  # noqa: E402
from .query import register_nodes  # noqa: E402

register_aggregates()
register_expressions()
register_fields()
register_functions()
register_indexes()
register_lookups()
register_nodes()
