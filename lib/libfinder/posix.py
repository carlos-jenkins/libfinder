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
libfinder module for posix systems.

Based on ctypes.util:

https://github.com/python/cpython/blob/3.4/Lib/ctypes/util.py
"""

from __future__ import unicode_literals, absolute_import
from __future__ import print_function, division

from glob import glob
from errno import ENOENT
from struct import calcsize
from os import uname, getcwd
from re import escape, search
from logging import getLogger
from traceback import format_exc
from shlex import split as shsplit
from tempfile import NamedTemporaryFile
from subprocess import Popen, PIPE, DEVNULL
from distutils.spawn import find_executable
from os.path import isfile, normpath, realpath, join


log = getLogger(__name__)


def _abi_type():
    """
    Determine the system ABI.
    """
    try:
        machine = uname().machine
    except AttributeError:
        # Old Python 2.7
        machine = uname()[4]

    arch = '32' if calcsize('l') == 4 else '64'

    abi_map = {
        ('x86_64', '64'): 'libc6,x86-64',
        ('ppc64', '64'): 'libc6,64bit',
        ('sparc64', '64'): 'libc6,64bit',
        ('s390x', '64'): 'libc6,64bit',
        ('ia64', '64'): 'libc6,IA-64',
    }
    abi_type = abi_map.get((machine, arch), 'libc6')
    return abi_type


def _execute(command):
    """
    Execute a command safely and returns its output as ``utf-8``.
    """
    try:
        p = Popen(
            shsplit(command),
            stdin=DEVNULL,
            stderr=DEVNULL,
            stdout=PIPE,
            env={'LC_ALL': 'C', 'LANG': 'C'}
        )
        pstdout, _ = p.communicate()
    except OSError:  # E.g. command not found
        log.debug(format_exc())
        return None
    return pstdout.decode('utf-8')


def _final_path(library_path):
    """
    Returns the final path of a path by normalizing the path and following the
    symbolic links.
    """
    return realpath(normpath(library_path))


def _ldconfig_search(library):
    """
    Search a library path by calling and parsing a ``ldconfig`` call.

    Assuming GLIBC's ldconfig (with option -p):

    ::

        libm.so.6 (libc6,x86-64, OS ABI: Linux 2.6.24) => /lib/x86_64-linux-gnu/libm.so.6
    """  # noqa
    executable = find_executable('ldconfig')
    if executable is None:
        return None

    ldconfig = _execute('{} -p'.format(executable))
    if ldconfig is None:
        return None

    abi_type = _abi_type()

    expr = r'\s+(lib{library}\.[^\s]+)\s+\({abi_type}'.format(
        library=escape(library), abi_type=abi_type
    )

    match = search(expr, ldconfig)
    if not match:
        return None

    # After the matching get the line of the match
    end_of_line = ldconfig.find('\n', match.end())
    line = ldconfig[match.start():end_of_line].strip()
    library_path = line.split('=>')[-1].strip()

    return _final_path(library_path)


def _gcc_search(library):
    """
    Search a library path by calling and parsing a C linker call.

    Run GCC's linker with the -t (aka --trace) option and examine the library
    name it prints out. The GCC command will fail because we haven't supplied a
    proper program with main(), but that does not matter.
    """
    linker = find_executable('cc') or find_executable('gcc')
    if linker is None:
        return None

    try:
        with NamedTemporaryFile() as tmp:
            command = '{linker} -Wl,-t -o "{program}" -l"{library}"'.format(
                linker=linker, program=tmp.name, library=library
            )
            trace = _execute(command)
    except OSError as e:
        # ENOENT is raised if the file was already removed, which is the normal
        # behaviour of GCC if linking fails
        if e.errno != ENOENT:
            raise

    if trace is None:
        return None

    expr = r'[^\(\)\s]*lib{}\.[^\(\)\s]*'.format(escape(library))
    match = search(expr, trace)
    if not match:
        return None

    library_path = normpath(match.group(0))
    return _final_path(library_path)


def _local_search(library):
    """
    Search given library in current working directory.
    """
    search_glob = join(getcwd(), 'lib{library}.so*'.format(library=library))
    for filename in glob(search_glob):
        if isfile(filename):
            return _final_path(filename)
    return None


def find_library(library):
    """
    Find a dynamic library given it's name.

    For example:

    ::

        >>> find_library('m')
        '/lib/x86_64-linux-gnu/libm-2.23.so'

    :param str library: Library name without the ``lib`` prefix nor the ``.so``
     extension.

    :return: Full absolute path to library file.
    :rtype: str
    """
    return _ldconfig_search(library) or \
        _gcc_search(library) or \
        _local_search(library)


def soname(library_path):
    """
    Get the ``SONAME`` of a dynamic library.

    This is accomplish by calling ``objdump`` and parsing the output of the
    ``.dynamic`` section.

    For example:

    ::

        >>> lib = find_library('m')
        >>> lib
        '/lib/x86_64-linux-gnu/libm-2.23.so'
        >>> soname(lib)
        'libm.so.6'

    :param str library_path: Full absolute to a library file.

    :return: ``SONAME`` symbol of the library.
    :rtype: str
    """
    assert isfile(library_path), 'No such file {}'.format(library_path)
    dump = _execute('objdump -x -j .dynamic {}'.format(library_path))
    if dump is None:
        return None
    match = search(r'\sSONAME\s+([^\s]+)', dump)
    if not match:
        return None
    return match.group(1)


__all__ = ['find_library', 'soname']
