from .base import register_base
from .comparison import register_comparison
from .datetime import register_datetime
from .json import register_json
from .math import register_math
from .text import register_text
from .window import register_window


def register_functions():
    register_base()
    register_comparison()
    register_datetime()
    register_json()
    register_math()
    register_text()
    register_window()
