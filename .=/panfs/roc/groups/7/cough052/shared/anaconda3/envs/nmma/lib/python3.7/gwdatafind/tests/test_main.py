# -*- coding: utf-8 -*-
# Copyright Duncan Macleod 2018
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

"""Tests for :mod:`gwdatafind.__main__` (the CLI)
"""

import argparse
import os
from six.moves import StringIO

import pytest

try:
    from unittest import mock
except ImportError:  # python < 3
    import mock

from ligo.segments import segment

from .. import __main__ as main

__author__ = 'Duncan Macleod <duncan.macleod@ligo.org>'

URLS = [
    'file:///test/X-test-0-1.gwf',
    'file:///test/X-test-1-1.gwf',
    'file:///test2/X-test-2-1.gwf',
    'file:///test2/X-test-7-4.gwf',
]
OUTPUT_URLS = """
file:///test/X-test-0-1.gwf
file:///test/X-test-1-1.gwf
file:///test2/X-test-2-1.gwf
file:///test2/X-test-7-4.gwf
"""[1:]  # strip leading line return
OUTPUT_LAL_CACHE = """
X test 0 1 file:///test/X-test-0-1.gwf
X test 1 1 file:///test/X-test-1-1.gwf
X test 2 1 file:///test2/X-test-2-1.gwf
X test 7 4 file:///test2/X-test-7-4.gwf
"""[1:]
OUTPUT_NAMES_ONLY = """
/test/X-test-0-1.gwf
/test/X-test-1-1.gwf
/test2/X-test-2-1.gwf
/test2/X-test-7-4.gwf
"""[1:]
OUTPUT_OMEGA_CACHE = """
X test 0 2 1 file:///test
X test 2 3 1 file:///test2
X test 7 11 4 file:///test2
"""[1:]
GAPS = [(3, 7)]



@mock.patch.dict(os.environ, {'LIGO_DATAFIND_SERVER': 'something'})
def test_command_line():
    parser = main.command_line()
    assert isinstance(parser, argparse.ArgumentParser)
    assert parser.description == main.__doc__
    for query in ('ping', 'show_observatories', 'show_types', 'show_times',
                  'filename', 'latest'):
        assert not parser.get_default(query)
    assert parser.get_default('server') == os.getenv('LIGO_DATAFIND_SERVER')
    assert parser.get_default('url_type') is 'file'
    assert parser.get_default('gaps') is False

    # test parsing and types
    args = parser.parse_args([
        '-o', 'X', '-t', 'test', '--gps-start-time', '0', '-e', '1',
    ])
    assert args.gpsstart == 0.
    assert args.gpsend == 1.
    assert args.server == 'something'


@mock.patch.dict('os.environ')
@pytest.mark.parametrize('defserv', (None, 'test.datafind.com:443'))
def test_command_line_server(defserv):
    if defserv:
        os.environ['LIGO_DATAFIND_SERVER'] = defserv
    else:
        os.environ.pop('LIGO_DATAFIND_SERVER', None)
    parser = main.command_line()
    serveract = [act for act in parser._actions if act.dest == 'server'][0]
    assert serveract.required is (not defserv)


@mock.patch.dict(os.environ, {'LIGO_DATAFIND_SERVER': 'something'})
def test_sanity_check_pass():
    parser = main.command_line()
    args = parser.parse_args(['-o', 'X', '-t', 'test', '-s', '0', '-e', '1'])


@mock.patch.dict(os.environ, {'LIGO_DATAFIND_SERVER': 'something'})
@pytest.mark.parametrize('clargs', [
    ('--show-times', '--observatory', 'X'),
    ('--show-times', '--type', 'test'),
    ('--type', 'test', '--observatory', 'X', '--gps-start-time', '1'),
    ('--gaps', '--show-observatories'),
])
def test_sanity_check_fail(clargs):
    parser = main.command_line()
    with pytest.raises(SystemExit):
        args = parser.parse_args(clargs)


@mock.patch('gwdatafind.ui.ping')
def test_ping(mping):
    args = argparse.Namespace(server='test.datafind.com:443')
    out = StringIO()
    main.ping(args, out)
    assert mping.called_with(host=args.server)
    out.seek(0)
    assert out.read().rstrip() == (
        'LDRDataFindServer at test.datafind.com:443 is alive')


@mock.patch('gwdatafind.ui.find_observatories')
def test_show_observatories(mfindobs):
    mfindobs.return_value = ['A', 'B', 'C']
    args = argparse.Namespace(
        server='test.datafind.com:443',
        match='test',
    )
    out = StringIO()
    main.show_observatories(args, out)
    out.seek(0)
    assert mfindobs.called_with(host=args.server, match=args.match)
    assert list(map(str.rstrip, out.readlines())) == ['A', 'B', 'C']


@mock.patch('gwdatafind.ui.find_types')
def test_show_types(mfindtypes):
    mfindtypes.return_value = ['A', 'B', 'C']
    args = argparse.Namespace(
        server='test.datafind.com:443',
        observatory='X',
        match='test',
    )
    out = StringIO()
    main.show_types(args, out)
    out.seek(0)
    assert mfindtypes.called_with(host=args.server, match=args.match,
                                  site=args.observatory)
    assert list(map(str.rstrip, out.readlines())) == ['A', 'B', 'C']


@mock.patch('gwdatafind.ui.find_times')
def test_show_times(mfindtimes):
    mfindtimes.return_value = [segment(0, 1), segment(1, 2), segment(3, 4)]
    args = argparse.Namespace(
        server='test.datafind.com:443',
        observatory='X',
        type='test',
        gpsstart=0,
        gpsend=10,
    )
    out = StringIO()
    main.show_times(args, out)
    assert mfindtimes.called_with(host=args.server, site=args.observatory,
                                  frametype=args.type, gpsstart=args.gpsstart,
                                  gpsend=args.gpsend)
    out.seek(0)
    for i, line in enumerate(out.readlines()[1:]):
        seg = mfindtimes.return_value[i]
        assert line.split() == list(map(str, (i, seg[0], seg[1], abs(seg))))


@mock.patch('gwdatafind.ui.find_latest')
def test_latest(mlatest):
    mlatest.return_value = ['file:///test/X-test-0-10.gwf']
    args = argparse.Namespace(
        server='test.datafind.com:443',
        observatory='X',
        type='test',
        url_type='file',
        lal_cache=False,
        names_only=False,
        frame_cache=False,
        gaps=None,
    )
    out = StringIO()
    main.latest(args, out)
    assert mlatest.called_with(args.observatory, args.type,
                               urltype=args.url_type, on_missing='warn',
                               host=args.server)
    out.seek(0)
    assert out.read().rstrip() == mlatest.return_value[0]


@mock.patch('gwdatafind.ui.find_url')
def test_filename(mfindurl):
    mfindurl.return_value = ['file:///test/X-test-0-10.gwf']
    args = argparse.Namespace(
        server='test.datafind.com:443',
        filename='X-test-0-10.gwf',
        url_type='file',
        type=None,
        lal_cache=False,
        names_only=False,
        frame_cache=False,
        gaps=None,
    )
    out = StringIO()
    main.filename(args, out)
    assert mfindurl.called_with(args.filename, urltype=args.url_type,
                                on_missing='warn', host=args.server)
    out.seek(0)
    assert out.read().rstrip() == mfindurl.return_value[0]


@mock.patch('gwdatafind.ui.find_urls')
def test_show_urls(mfindurls):
    mfindurls.return_value = URLS
    args = argparse.Namespace(
        server='test.datafind.com:443',
        observatory='X',
        type='test',
        gpsstart=0,
        gpsend=10,
        url_type='file',
        match=None,
        lal_cache=False,
        names_only=False,
        frame_cache=False,
        gaps=None,
    )
    out = StringIO()
    main.show_urls(args, out)
    assert mfindurls.called_with(args.observatory, args.type, args.gpsstart,
                                 args.gpsend, match=args.match,
                                urltype=args.url_type, on_gaps='ignore',
                                host=args.server)
    out.seek(0)
    assert list(map(str.rstrip, out.readlines())) == URLS


@pytest.mark.parametrize('fmt,result', [
    (None, OUTPUT_URLS),
    ('lal_cache', OUTPUT_LAL_CACHE),
    ('names_only', OUTPUT_NAMES_ONLY),
    ('frame_cache', OUTPUT_OMEGA_CACHE),
])
def test_postprocess_cache_format(fmt, result):
    # create namespace for parsing
    args = argparse.Namespace(
        type=None,
        lal_cache=False,
        names_only=False,
        frame_cache=False,
        gaps=None,
    )
    if fmt:
        setattr(args, fmt, True)

    # run
    out = StringIO()
    assert not main.postprocess_cache(URLS, args, out)
    out.seek(0)
    assert out.read() == result


def test_postprocess_cache_sft():
    args = argparse.Namespace(
        type='TEST_1800SFT',
        lal_cache=False,
        names_only=False,
        frame_cache=False,
        gaps=None,
    )
    out = StringIO()
    main.postprocess_cache(URLS, args, out)
    out.seek(0)
    assert out.read() == OUTPUT_URLS.replace('.gwf', '.sft')


def test_postprocess_cache_gaps(capsys):
    args = argparse.Namespace(
        gpsstart=0,
        gpsend=10,
        type=None,
        lal_cache=False,
        names_only=False,
        frame_cache=False,
        gaps=True,
    )
    out = StringIO()
    assert main.postprocess_cache(URLS, args, out) is 1
    _, err = capsys.readouterr()
    assert err == 'Missing segments:\n\n{0}\n'.format(
        '\n'.join('{0[0]:d} {0[1]:d}'.format(seg) for seg in GAPS),
    )

    args.gpsstart = 4
    args.gpsend = 7
    assert main.postprocess_cache(URLS, args, out) is 2


@mock.patch.dict(os.environ, {'LIGO_DATAFIND_SERVER': 'something'})
@pytest.mark.parametrize('args,patch', [
    (['--ping'], 'ping'),
    (['--show-observatories'], 'show_observatories'),
    (['--show-types'], 'show_types'),
    (['--show-times', '-o', 'X', '-t', 'test'], 'show_times'),
    (['--latest', '-o', 'X', '-t', 'test'], 'latest'),
    (['--filename', 'X-test-0-1.gwf'], 'filename'),
    (['-o', 'X', '-t', 'test', '-s', '0', '-e', '10'], 'show_urls'),
])
def test_main(args, patch, tmpname):
    with mock.patch('gwdatafind.__main__.{0}'.format(patch)) as mocked:
        main.main(args)
        assert mocked.call_count == 1
    # call again with output file
    args.extend(('--output-file', tmpname))
    with mock.patch('gwdatafind.__main__.{0}'.format(patch)) as mocked:
        main.main(args)
        assert mocked.call_count == 1
