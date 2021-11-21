# Import SWIG wrappings, if available
from .lalpulsar import *

__version__ = "3.1.0"

## \addtogroup lalpulsar_python
"""This package provides Python wrappings and extensions to LALPulsar"""



#
# This section was added automatically to support using LALSuite as a wheel.
#
import os
try:
    from importlib import resources
except ImportError:
    # FIXME: remove after dropping support for Python < 3.7
    import importlib_resources as resources
with resources.path('lalapps', '__init__.py') as new_path:
    new_path = str(new_path.parent / 'data')
path = os.environ.get('LAL_DATA_PATH')
path = path.split(':') if path else []
if new_path not in path:
    path.append(new_path)
os.environ['LAL_DATA_PATH'] = ':'.join(path)
