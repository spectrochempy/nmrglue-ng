from .fileio import *
from .process import *
from .util import *
from .analysis import *
from . import interop as interop

try:
    from setuptools_scm import get_version

    __version__ = get_version(root="..", relative_to=__file__)
except Exception:
    from importlib.metadata import PackageNotFoundError, version

    try:
        __version__ = version("nmrglue-ng")
    except PackageNotFoundError:  # pragma: no cover - only used from broken installs
        __version__ = "0+unknown"
