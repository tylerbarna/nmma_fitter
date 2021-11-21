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

"""Query the DataFind service for information.
"""

from __future__ import print_function

import argparse
import os.path
import re
import sys
from collections import namedtuple
from operator import (attrgetter, methodcaller)

from six.moves.urllib.parse import urlparse

from ligo import segments

from . import (__version__, ui)
from .utils import (get_default_host, filename_metadata)

__author__ = 'Duncan Macleod <duncan.macleod@ligo.org>'
__credits__ = 'Scott Koranda, The LIGO Scientific Collaboration'


# -- cache format utilities ---------------------------------------------------

class _CacheEntry(namedtuple('CacheEntry', ('obs', 'tag', 'segment', 'url'))):
    """Simplified version of `lal.utils.CacheEntry`

    This is provided so that we don't have to depend on lalsuite.
    """
    def __str__(self):
        seg = self.segment
        return '{0} {1} {2} {3} {4}'.format(
            self.obs, self.tag, seg[0], abs(seg), self.url)

    @classmethod
    def from_url(cls, url, **kwargs):
        obs, tag, seg = filename_metadata(url)
        return cls(obs, tag, seg, url)


class _OmegaCacheEntry(namedtuple(
        '_OmegaCacheEntry', ('obs', 'tag', 'segment', 'duration', 'url'))):
    """CacheEntry for an omega-style cache.

    Omega-style cache files contain one entry per contiguous directory of
    the form:

        <obs> <tag> <dir-start> <dir-end> <file-duration> <directory>
    """
    def __str__(self):
        return '{0} {1} {2[0]} {2[1]} {3} {4}'.format(
            self.obs, self.tag, self.segment, self.duration, self.url)


def _to_wcache(cache):
    """Convert a list of `_CacheEntry` into a list of `_OmegaCacheEntry`
    """
    wcache = []
    duration = 0
    for entry in sorted(
            cache, key=attrgetter('obs', 'tag', 'segment')):
        dir_ = os.path.dirname(entry.url)
        # if this file has the same attributes, goes into the same directory,
        # has the same duration, and overlaps with or is contiguous with
        # the last file, just add its segment to the last one:
        if wcache and (
                entry.obs == wentry.obs and
                entry.tag == wentry.tag and
                dir_ == wentry.url and
                abs(entry.segment) == wentry.duration and
                (entry.segment.connects(wentry.segment) or
                 entry.segment.intersects(wentry.segment))
        ):
            wcache[-1] = wentry = _OmegaCacheEntry(
                wentry.obs, wentry.tag, wentry.segment | entry.segment,
                wentry.duration, wentry.url)
        # otherwise create a new entry in the omega wcache
        else:
            wentry = _OmegaCacheEntry(entry.obs, entry.tag, entry.segment,
                                      abs(entry.segment), dir_)
            wcache.append(wentry)
    return wcache


# -- command line parsing -----------------------------------------------------


class DataFindArgumentParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(DataFindArgumentParser, self).__init__(*args, **kwargs)
        self._optionals.title = "Optional arguments"

    def parse_args(self, *args, **kwargs):
        args = super(DataFindArgumentParser, self).parse_args(*args, **kwargs)
        args.show_urls = not any((args.ping, args.show_observatories,
                                  args.show_types, args.show_times,
                                  args.filename, args.latest))
        self.sanity_check(args)
        return args

    def sanity_check(self, namespace):
        """Sanity check parsed command line options

        If any problems are found `argparse.ArgumentParser.error` is called,
        which in turn calls :func:`sys.exit`.

        Parameters
        ----------
        namespace : `argparse.Namespace`
            the output of the command-line parsing
        """
        if namespace.show_times and (
                not namespace.observatory or
                not namespace.type
        ):
            self.error("--observatory and --type must be given when using "
                         "--show-times.")
        if namespace.show_urls and not all(x is not None for x in (
                namespace.observatory,
                namespace.type,
                namespace.gpsstart,
                namespace.gpsend,
        )):
            self.error("--observatory, --type, --gps-start-time, and "
                       "--gps-end-time time all must be given when querying "
                       "for file URLs")
        if namespace.gaps and not namespace.show_urls:
            self.error('-g/--gaps only allowed when querying for file URLs')


def command_line():
    """Build an `~argparse.ArgumentParser` for the `gwdatafind` CLI
    """
    try:
        defhost = get_default_host()
    except ValueError:
        defhost = None

    parser = DataFindArgumentParser(description=__doc__)

    parser.add_argument('-V', '--version', action='version',
                        version=__version__,
                        help='show version number and exit')

    qargs = parser.add_argument_group(
        "Query types", "Select one of the following, if none are selected a "
                       "query for frame URLS will be performed"
    )
    qtype = qargs.add_mutually_exclusive_group(required=False)
    parser._mutually_exclusive_groups.append(qtype)  # bug in argparse
    qtype.add_argument('-p', '--ping', action='store_true', default=False,
                       help='ping the DataFind server')
    qtype.add_argument('-w', '--show-observatories', action='store_true',
                       default=False, help='list available observatories')
    qtype.add_argument('-y', '--show-types', action='store_true',
                       default=False, help='list available file types')
    qtype.add_argument('-a', '--show-times', action='store_true',
                       default=False, help='list available segments')
    qtype.add_argument('-f', '--filename', action='store', metavar='FILE',
                       help='resolve URL(s) for a particular file name')
    qtype.add_argument('-T', '--latest', action='store_true', default=False,
                       help='resolve URL(s) for the most recent file of the '
                            'specified type')

    dargs = parser.add_argument_group(
        "Data options", "Parameters for your query. Which options are "
                        "required depends on the query type"
    )
    dargs.add_argument('-o', '--observatory', metavar='OBS',
                       help='observatory(ies) that generated frame file; use '
                            '--show-observatories to see what is available.')
    dargs.add_argument('-t', '--type', help='type of frame file, use --show-'
                                            'types to see what is available.')
    dargs.add_argument('-s', '--gps-start-time', type=int, dest='gpsstart',
                       metavar='GPS', help='start of GPS time search')
    dargs.add_argument('-e', '--gps-end-time', type=int, dest='gpsend',
                       metavar='GPS', help='end of GPS time search')

    sargs = parser.add_argument_group(
        'Connection options', 'Authentication and connection options.')
    sargs.add_argument('-r', '--server', metavar='HOST:PORT', default=defhost,
                       required=not defhost,
                       help='hostname and optional port of server to query '
                            '(default: %(default)s)')
    sargs.add_argument('-P', '--no-proxy', action='store_true',
                       help='attempt to authenticate without a grid proxy '
                            '(default: %(default)s)')

    oargs = parser.add_argument_group(
        'Output options', 'Parameters for parsing and writing output.')
    oform = oargs.add_mutually_exclusive_group()
    parser._mutually_exclusive_groups.append(oform)  # bug in argparse
    oform.add_argument('-l', '--lal-cache', action='store_true',
                       help='format output for use as a LAL cache file')
    oform.add_argument('-W', '--frame-cache', action='store_true',
                       help='format output for use as a frame cache file')
    oform.add_argument('-n', '--names-only', action='store_true',
                       help='display only the basename of each file')
    oargs.add_argument('-m', '--match', help='return only results that match '
                                             'a regular expression')
    oargs.add_argument('-u', '--url-type', default='file',
                       help='return only URLs with a particular scheme or '
                            'head such as \'file\' or \'gsiftp\'')
    oargs.add_argument('-g', '--gaps', action='store_true',
                       help='check the returned list of URLs or paths to see '
                            'if the files cover the requested interval; a '
                            'return value of zero (0) indicates the interval '
                            'is covered, a value of one (1) indicates at '
                            'least one gap exists and the interval is not , '
                            'covered and a value of (2) indicates that the '
                            'entire interval is not covered; missing gaps are '
                            'printed to stderr (default: %(default)s)')
    oargs.add_argument('-O', '--output-file', metavar='PATH',
                       help='path to output file, defaults to stdout')

    return parser


# -- actions ------------------------------------------------------------------

def ping(args, out):
    """Worker for the --ping option.

    Parameters
    ----------
    args : `argparse.Namespace`
        the parsed command-line options.

    out : `file`
        the open file object to write to.

    Returns
    -------
    exitcode : `int` or `None`
        the return value of the action or `None` to indicate success.
    """
    ui.ping(host=args.server)
    print("LDRDataFindServer at {0.server} is alive".format(args), file=out)


def show_observatories(args, out):
    """Worker for the --show-observatories option

    Parameters
    ----------
    args : `argparse.Namespace`
        the parsed command-line options.

    out : `file`
        the open file object to write to.

    Returns
    -------
    exitcode : `int` or `None`
        the return value of the action or `None` to indicate success.
    """
    sitelist = ui.find_observatories(host=args.server, match=args.match)
    print("\n".join(sitelist), file=out)


def show_types(args, out):
    """Worker for the --show-types option

    Parameters
    ----------
    args : `argparse.Namespace`
        the parsed command-line options.

    out : `file`
        the open file object to write to.

    Returns
    -------
    exitcode : `int` or `None`
        the return value of the action or `None` to indicate success.
    """
    typelist = ui.find_types(site=args.observatory, match=args.match,
                             host=args.server)
    print("\n".join(typelist), file=out)


def show_times(args, out):
    """Worker for the --show-times option

    Parameters
    ----------
    args : `argparse.Namespace`
        the parsed command-line options.

    out : `file`
        the open file object to write to.

    Returns
    -------
    exitcode : `int` or `None`
        the return value of the action or `None` to indicate success.
    """
    seglist = ui.find_times(site=args.observatory, frametype=args.type,
                            gpsstart=args.gpsstart, gpsend=args.gpsend,
                            host=args.server)
    print('# seg\tstart     \tstop      \tduration', file=out)
    for i, seg in enumerate(seglist):
        print(
            '{n}\t{segment[0]:10}\t{segment[1]:10}\t{duration}'.format(
                n=i, segment=seg, duration=abs(seg),
            ), file=out,
        )


def latest(args, out):
    """Worker for the --latest option

    Parameters
    ----------
    args : `argparse.Namespace`
        the parsed command-line options.

    out : `file`
        the open file object to write to.

    Returns
    -------
    exitcode : `int` or `None`
        the return value of the action or `None` to indicate success.
    """
    cache = ui.find_latest(args.observatory, args.type, urltype=args.url_type,
                           on_missing='warn', host=args.server)
    return postprocess_cache(cache, args, out)


def filename(args, out):
    """Worker for the --filename option

    Parameters
    ----------
    args : `argparse.Namespace`
        the parsed command-line options.

    out : `file`
        the open file object to write to.

    Returns
    -------
    exitcode : `int` or `None`
        the return value of the action or `None` to indicate success.
    """
    cache = ui.find_url(args.filename, urltype=args.url_type,
                        on_missing='warn', host=args.server)
    return postprocess_cache(cache, args, out)


def show_urls(args, out):
    """Worker for the default (show-urls) option

    Parameters
    ----------
    args : `argparse.Namespace`
        the parsed command-line options.

    out : `file`
        the open file object to write to.

    Returns
    -------
    exitcode : `int` or `None`
        the return value of the action or `None` to indicate success.
    """
    cache = ui.find_urls(args.observatory, args.type,
                         args.gpsstart, args.gpsend,
                         match=args.match, urltype=args.url_type,
                         host=args.server, on_gaps='ignore')
    return postprocess_cache(cache, args, out)


def postprocess_cache(urls, args, out):
    """Post-process a cache produced from a DataFind query

    This function checks for gaps in the file coverage, prints the cache
    in the requested format, then prints gaps to stderr if requested.
    """
    # if searching for SFTs replace '.gwf' file suffix with '.sft'
    if re.search(r'_\d+SFT(\Z|_)', str(args.type)):
        gwfreg = re.compile(r'\.gwf\Z')
        for i, url in enumerate(urls):
            urls[i] = gwfreg.sub('.sft', url)

    cache = list(map(_CacheEntry.from_url, urls))

    # determine output format for a given URL
    if args.lal_cache:
        fmt = str
    elif args.names_only:
        def fmt(url):
            return urlparse(url.url).path
    elif args.frame_cache:
        cache = _to_wcache(cache)
        fmt = str
    else:
        fmt = attrgetter('url')

    for entry in cache:
        print(fmt(entry), file=out)

    # check for gaps
    if args.gaps:
        span = segments.segment(args.gpsstart, args.gpsend)
        seglist = segments.segmentlist(e.segment for e in cache).coalesce()
        missing = (segments.segmentlist([span]) - seglist).coalesce()
        if missing:
            print("Missing segments:\n", file=sys.stderr)
            for seg in missing:
                print("%d %d" % tuple(seg), file=sys.stderr)
            if span in missing:
                return 2
            return 1


# -- CLI ----------------------------------------------------------------------

def main(args=None):
    """Run the thing
    """
    # parse command line
    parser = command_line()
    opts = parser.parse_args(args=args)

    # open output
    if opts.output_file:
        out = open(opts.output_file, 'w')
    else:
        out = sys.stdout

    try:
        # run query
        if opts.ping:
            return ping(opts, out)
        if opts.show_observatories:
            return show_observatories(opts, out)
        if opts.show_types:
            return show_types(opts, out)
        if opts.show_times:
            return show_times(opts, out)
        if opts.latest:
            return latest(opts, out)
        if opts.filename:
            return filename(opts, out)
        return show_urls(opts, out)
    finally:
        # close output file if we opened it
        if opts.output_file:
            out.close()


if __name__ == '__main__':  # pragma: no-cover
    sys.exit(main())
