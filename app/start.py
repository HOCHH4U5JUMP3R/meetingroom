from .main import app
from . import extra_routes  # noqa: F401
from . import import_routes  # noqa: F401
from . import model_routes  # noqa: F401
from . import modernization_routes  # noqa: F401

__all__ = ['app']
