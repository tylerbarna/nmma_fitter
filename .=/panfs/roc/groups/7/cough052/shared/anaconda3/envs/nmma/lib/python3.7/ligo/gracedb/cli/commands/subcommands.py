import six
import textwrap

from .base import RegisteredSubCommandBase
from ..parsers import superevent_id_parser


class ConfirmAsGwCommand(RegisteredSubCommandBase):
    name = "confirm_as_gw"
    description = "Confirm a superevent as a GW"
    long_description = textwrap.dedent("""\
        Confirm a superevent as a gravitational wave. Specific permissions are
        required to perform this action on non-Test superevents.
    """).rstrip()
    parent_parsers = (superevent_id_parser,)

    def run(self, client, args):
        return client.confirm_superevent_as_gw(args.superevent_id)


class CredentialsCommand(RegisteredSubCommandBase):
    name = "credentials"
    description = "Display your credentials"
    long_description = textwrap.dedent("""\
        Display the credentials that the client will use to make API requests
        or get information about your user account on the server. Useful for
        debugging and ensuring that your credentials and user account
        information are what you expect them to be.
    """).rstrip()

    def add_custom_arguments(self, parser):
        parser.add_argument(
            'type',
            type=str,
            choices=['client', 'server'],
            help=('View credentials found by the client or get your user '
                  'account information from the server')
        )
        return parser

    def run(self, client, args):
        if (args.type == 'client'):
            return client.show_credentials(print_output=False)
        else:
            return client.get_user_info()


class ExposeCommand(RegisteredSubCommandBase):
    name = "expose"
    description = "Expose a superevent to non-internal users"
    long_description = textwrap.dedent("""\
        Expose a superevent to LV-EM and public users. Special permissions
        are required to perform this action.
    """).rstrip()

    def add_custom_arguments(self, parser):
        parser.add_argument(
            'superevent_id',
            type=str,
            help="ID of the superevent to expose"
        )
        return parser

    def run(self, client, args):
        return client.modify_permissions(args.superevent_id, 'expose')


class HideCommand(RegisteredSubCommandBase):
    name = "hide"
    description = \
        "Make an exposed superevent accessible to internal users only"
    long_description = textwrap.dedent("""\
        Make a superevent accessible to internal users only. Specific
        permissions are required to perform this action.
    """).rstrip()

    def add_custom_arguments(self, parser):
        parser.add_argument(
            'superevent_id',
            type=str,
            help="ID of the superevent to hide"
        )
        return parser

    def run(self, client, args):
        return client.modify_permissions(args.superevent_id, 'hide')


class PingCommand(RegisteredSubCommandBase):
    name = "ping"
    description = \
        "Make a basic request to check your connection to the server"

    def run(self, client, args):
        response = client.ping()
        output = 'Response from {server}: {status}'.format(
            server=client._service_url, status=response.status_code)
        if (response.status_code == 200):
            output += ' OK'
        return output


class InfoCommand(RegisteredSubCommandBase):
    """
    These commands all just print basic information obtained from the API root
    and attached to the client instance as a property. Each dict in 'options'
    corresponds to a command.
    """
    name = "info"
    description = "Get information from the server"
    long_description = textwrap.dedent("""\
        Get available EM groups, LVC analysis groups, pipelines, searches,
        labels, signoff types, signoff statuses, superevent categories,
        VOEvent types, or server code version from the server
    """).rstrip()

    # Mapping from argument value to client property
    options = {
        'emgroups': 'em_groups',
        'groups': 'groups',
        'instruments': 'instruments',
        'labels': 'allowed_labels',
        'pipelines': 'pipelines',
        'searches': 'searches',
        'server_version': 'server_version',
        'signoff_statuses': 'signoff_statuses',
        'signoff_types': 'signoff_types',
        'superevent_categories': 'superevent_categories',
        'voevent_types': 'voevent_types',
    }

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "items",
            type=str,
            choices=sorted(list(self.options)),
            help="Information to display"
        )
        return parser

    def run(self, client, args):
        # Get list of objects from server, sort, and print
        data = getattr(client, self.options.get(args.items))

        # Convert dict to list of key (value) strings
        if isinstance(data, dict):
            data = ['{k} ({v})'.format(k=k, v=v) for k, v in
                    six.iteritems(data)]

        # Join list into comma-separated string
        if isinstance(data, list):
            data = ", ".join(sorted(data))

        # Handle None response
        if data is None:
            data = 'Data not found on server.'

        return data


class ShowCommand(InfoCommand):
    """Legacy version of InfoCommand. Same functionality"""
    legacy = True
    name = "show"
    description = "DEPRECATED: see 'gracedb info'"
    long_description = description
