import pytest

from ligo.gracedb.cli.client import CommandLineInterface, main


@pytest.fixture
def expected_subcommands():
    """Names of expected subcommands for CLI"""
    return ['add', 'create', 'delete', 'get', 'list', 'remove', 'search',
            'update', 'confirm_as_gw', 'expose', 'hide', 'ping', 'info',
            'credentials']


@pytest.fixture
def CLI():
    """Instantiated command-line interface"""
    return CommandLineInterface()


@pytest.fixture
def main_tester():
    """Get main() function which is used as a wrapper for the CLI"""
    return main
