# -*- coding: utf-8 -*-
# Copyright Duncan Macleod 2017
#
# This file is part of GWDataFind.
#
# GWDataFind is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GWDataFind is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GWDataFind.  If not, see <http://www.gnu.org/licenses/>.

"""The client library for the LIGO Data Replicator (LDR) service.

The DataFind service allows users to query for the location of
Gravitational-Wave Frame (GWF) files containing data from the current
gravitational-wave detectors.

This package provides the :class:`~HTTPConnection` and
:class:`~HTTPSConnection` class objects, for connecting to an LDR server
in open and authenticated access modes respectively.
The authenticated :class:`~HTTPSConnection` requires users have a valid X509
certificate that is registered with the server in question.

-----------
Quick-start
-----------

A high-level :meth:`connect` function is provided that will automatically
select the correct protocol based on the host given, and will attempt to
access any required X509 credentials.
"""

from .http import *
from .ui import *

__author__ = 'Duncan Macleod <duncan.macleod@ligo.org>'
__credits__ = 'Scott Koranda <scott.koranda@ligo.org>'
__version__ = '1.0.4'
