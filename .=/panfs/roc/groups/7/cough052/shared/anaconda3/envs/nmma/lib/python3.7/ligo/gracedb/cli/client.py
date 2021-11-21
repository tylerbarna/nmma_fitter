from __future__ import absolute_import, print_function
import json
import os
import six
import sys
import textwrap
from requests import Response

from ligo.gracedb.rest import GraceDb, DEFAULT_SERVICE_URL
from ligo.gracedb import __version__
from ligo.gracedb.exceptions import HTTPError
from ligo.gracedb.cli.commands.base import CommandBase
from ligo.gracedb.cli.commands.base import command_registry

# Version string
VERSION_STRING = "GraceDB Client {0}".format(__version__)


# Override and add a few methods to the base GraceDb client class
class CommandLineClient(GraceDb):
    # TP 2019: not sure if we still need to do this, but leaving it for now.
    # Hamstring 'adjustResponse' from the example REST client.
    # We don't want it messing with the response from the server.
    def adjustResponse(self, response):
        response.json = lambda: self.load_json_from_response(response)
        return response

    # TP 2019: not sure if we still need to override this from the GraceDb
    # class, but leaving it for now.
    # @classmethod
    # def output_and_die(cls, msg):
    #    sys.stderr.write(msg)
    #    sys.exit(1)


class CommandLineInterface(CommandBase):
    """Main class for base-level command-line interface"""
    subcommands = command_registry
    description = textwrap.dedent("""\
        Command-line interface to the ligo-gracedb client tools for
        interacting with the GraceDB API.
    """).rstrip()

    def __call__(self, args=None):
        if args is None:
            args = sys.argv[1:]

        # Parse args
        cmd, main_args, cmd_args = self.parse_args(args)

        # Set up client
        self.set_up_client(main_args)

        # Call subcommand and get output
        output = cmd(self.client, cmd_args)

        return output

    def add_custom_arguments(self, parser):
        # We set nargs='?' for handling legacy commands
        parser.add_argument("command", nargs='?')

        # Other options
        parser.add_argument(
            "-s",
            "--service-url",
            dest="service",
            type=str,
            metavar="URL",
            help="GraceDB service URL",
            default=os.environ.get("GRACEDB_SERVICE_URL", DEFAULT_SERVICE_URL)
        )
        parser.add_argument(
            "-p",
            "--proxy",
            dest="proxy",
            type=str,
            metavar="PROXY[:PORT]",
            help="HTTP Proxy",
            default=os.environ.get("HTTP_PROXY", None)
        )
        parser.add_argument(
            "-V",
            "--version",
            action='version',
            version=VERSION_STRING
        )
        parser.add_argument(
            "--output-type",
            dest='output_type',
            type=str,
            help=textwrap.dedent("""\
                Select output type: 'status' = status code
                only, 'json' = full response JSON. Doesn't
                apply to some some commands which have
                pre-defined outputs, like 'info', 'ping',
                'search', etc.""").rstrip(),
            default='json', choices=['status', 'json']
        )
        parser.add_argument(
            '--username',
            dest='username',
            type=str,
            help='Basic auth username',
            default=None
        )
        parser.add_argument(
            '--password',
            dest='password',
            type=str,
            help='Basic auth password',
            default=None
        )
        parser.add_argument(
            '--creds',
            dest='creds',
            type=str,
            help=textwrap.dedent("""\
                Paths to certficate file and key file
                (comma-separated) OR path to single combined
                proxy file. Used for X.509 authentication
            """).rstrip(),
            default=None
        )
        parser.add_argument(
            "-n",
            "--force-noauth",
            dest="force_noauth",
            action="store_true",
            help="Do not use any authentication credentials",
            default=False
        )
        parser.add_argument(
            "-f",
            "--fail-if-noauth",
            dest="fail_if_noauth",
            action="store_true",
            help="Fail if no authentication credentials are found",
            default=False
        )
        return parser

    # Utils -------------------------------------------------------------------
    def set_up_client(self, args):
        # Handle proxy args
        proxy = args.proxy
        proxyport = None
        if proxy and proxy.find(':') > 0:
            try:
                proxy, proxyport = proxy.split(':')
                proxyport = int(proxyport)
            except Exception:
                print("Malformed proxy: '{0}'".format(proxy))
                sys.exit(1)

        # Handle creds arg
        creds = args.creds
        if creds:
            creds = creds.split(",")
            if len(creds) == 1:
                # Combined proxy file
                creds = creds[0]
            elif len(creds) == 2:
                # Cert file and key file
                pass
            else:
                print("Malformed 'creds' argument: {0}".format(args.creds))
                sys.exit(1)

        # Define kwargs for initializing client
        client_kwargs = {
            'service_url': args.service,
            'force_noauth': args.force_noauth,
            'username': args.username,
            'password': args.password,
            'fail_if_noauth': args.fail_if_noauth,
            'cred': creds,
        }

        # Initialize client
        self.client = CommandLineClient(**client_kwargs)


# Define a function for the entry_point
def main(args=None):
    if args is None:
        args = sys.argv[1:]

    cli = CommandLineInterface()

    # Try to test response and handle errors
    try:
        response = cli(args)
    except HTTPError as e:
        print('Error: {code} {reason}. {text}.'.format(
            code=e.status_code,
            reason=e.reason,
            text=e.text))
        sys.exit(1)
    except Exception as e:
        print('Error: {msg}'.format(msg=str(e)))
        sys.exit(1)

    if isinstance(response, Response):
        if (cli.args.output_type == 'json'):
            # Handle errors
            if response.status_code >= 400:
                output = '{code} {reason}'.format(code=response.status_code,
                                                  reason=response.reason)
                # Only add message if it's not really long (i.e., it's not
                # an HTML error page)
                msg = response.text
                if isinstance(msg, bytes):
                    msg = msg.decode()
                if (len(msg) < 1000):
                    output += ': {msg}'.format(msg=msg)
                print(output)
                sys.exit(1)
            # Handle errors raised in load_json_or_die()
            if response.status_code in [202, 204]:
                output = {}
                print(output)
                sys.exit(1)
            else:
                try:
                    output = response.json()
                except Exception as e:
                    print(str(e))
                    sys.exit(1)

            print(json.dumps(output, indent=4))
        elif (cli.args.output_type == 'status'):
            print('Server returned {status}: {reason}'.format(
                status=response.status_code, reason=response.reason))
    elif isinstance(response, dict):
        print(json.dumps(response, indent=4))
    elif isinstance(response, six.string_types):
        print(response)
    elif isinstance(response, bytes):
        print(response.decode())
    else:
        print("Unexpected response type {tp}".format(tp=type(response)))
        print("Response: {resp}".format(resp=str(response)))
        sys.exit(1)


if __name__ == "__main__":
    main()
