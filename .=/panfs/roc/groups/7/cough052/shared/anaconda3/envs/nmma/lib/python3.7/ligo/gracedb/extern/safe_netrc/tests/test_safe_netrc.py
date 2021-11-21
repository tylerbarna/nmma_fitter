import os
import stat

import pytest

from .. import netrc, NetrcParseError

try:
    FileNotFoundError
except NameError:
    FileNotFoundError = IOError


def check(filename):
    # Check that an exception is raised when the netrc file does not exist.
    with pytest.raises(FileNotFoundError) as excinfo:
        netrc()
    assert excinfo.value.filename == filename

    with open(filename, 'w') as f:
        fd = f.fileno()
        # Check that an exception is raised when the permissions too relaxed.
        os.fchmod(fd, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
        with pytest.raises(NetrcParseError) as excinfo:
            netrc()
        assert excinfo.value.filename == filename

        # Check that no exceptions are raised if the permissions are correct.
        os.fchmod(fd, stat.S_IRWXU)
        netrc()


def test_netrc_in_environ(monkeypatch, tmpdir):
    """Check file specified by NETRC environment variable"""
    filename = str(tmpdir / 'netrc')
    monkeypatch.setenv('NETRC', filename)
    check(filename)


def test_netrc_in_homedir(monkeypatch, tmpdir):
    """Check file specified by home directory"""
    filename = str(tmpdir / '.netrc')
    monkeypatch.setenv('HOME', str(tmpdir))
    check(filename)
