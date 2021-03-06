# -*- coding: utf-8 -*-
#
# Copyright (C) 2016 Carlos Jenkins
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

"""
libfinder module entry point.
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

from os import name as osname

if osname == 'posix':
    from .posix import find_library
    from .posix import soname

else:
    raise ImportError('Sorry libfinder currently works in POSIX systems only')


__author__ = 'Carlos Jenkins'
__email__ = 'carlos@jenkins.co.cr'
__version__ = '0.1.0'

__all__ = ['find_library', 'soname']
