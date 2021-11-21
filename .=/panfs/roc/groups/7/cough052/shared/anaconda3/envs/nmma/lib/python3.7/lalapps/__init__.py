# Copyright (C) 2009  LIGO Scientific Collaboration
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by the
# Free Software Foundation; either version 2 of the License, or (at your
# option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


#
# =============================================================================
#
#                                   Preamble
#
# =============================================================================
#




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
