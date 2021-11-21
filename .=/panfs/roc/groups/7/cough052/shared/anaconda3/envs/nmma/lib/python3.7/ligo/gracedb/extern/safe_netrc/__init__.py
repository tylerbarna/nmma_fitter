from netrc import netrc as _netrc
from netrc import NetrcParseError
import os
import stat

__all__ = ('netrc', 'NetrcParseError')


class netrc(_netrc):  # noqa: N801
    """Subclass of the Python standard library :class:`~netrc.netrc` class to
    add some custom behaviors.

    1.   If the ``NETRC`` environment variable is defined, then use it as
         the default netrc file path.

    2.   Backport permissions checks that were added in Python 3.1
         (see https://bugs.python.org/issue14984).

    3.   Apply permissions checks whether or or not we are reading from the
         default netrc file, and whether or not the file contains passwords.
    """

    def __init__(self, file=None):
        if file is None:
            file = os.environ.get('NETRC')
        _netrc.__init__(self, file)

    def _parse(self, file, fp, *args, **kwargs):
        # Adapted from Python 3.7
        if os.name == 'posix':
            prop = os.fstat(fp.fileno())
            if prop.st_uid != os.getuid():
                import pwd
                try:
                    fowner = pwd.getpwuid(prop.st_uid)[0]
                except KeyError:
                    fowner = 'uid %s' % prop.st_uid
                try:
                    user = pwd.getpwuid(os.getuid())[0]
                except KeyError:
                    user = 'uid %s' % os.getuid()
                raise NetrcParseError(
                    ("~/.netrc file owner (%s) does not match"
                     " current user (%s)") % (fowner, user),
                    file)
            if (prop.st_mode & (stat.S_IRWXG | stat.S_IRWXO)):
                raise NetrcParseError(
                    "~/.netrc access too permissive: access"
                    " permissions must restrict access to only"
                    " the owner", file)
        _netrc._parse(self, file, fp, *args, **kwargs)
