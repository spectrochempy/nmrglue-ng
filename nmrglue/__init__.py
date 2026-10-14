from .fileio import *
from .process import *
from .util import *
from .analysis import *

try:
    from setuptools_scm import get_version

    __version__ = get_version(root="..", relative_to=__file__)
except Exception:
    try:
        from importlib.metadata import PackageNotFoundError, version
    except ImportError:  # pragma: no cover - Python >= 3.10 always has importlib.metadata
        PackageNotFoundError = Exception
        version = None

    try:
        __version__ = version("nmrglue-ng")
    except PackageNotFoundError:  # pragma: no cover - only used from broken installs
        __version__ = "0+unknown"
