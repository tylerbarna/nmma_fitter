import os
import shutil
import textwrap

from .base import RegisteredCommandBase, RegisteredSubCommandBase
from ..parsers import object_id_parser, graceid_parser, superevent_id_parser


# Command registry - don't touch!
registry = []


###############################################################################
# Base command
###############################################################################
class GetCommand(RegisteredCommandBase):
    name = "get"
    description = textwrap.dedent("""\
        Download a file or get information about a log entry, label,
        EM observation, VOEvent, signoff, event, or superevent
    """).rstrip()
    subcommands = registry


###############################################################################
# Subcommands - registered to base command automatically
###############################################################################
class GetChildBase(RegisteredSubCommandBase):
    _registry = registry


class GetEmobservationCommand(GetChildBase):
    name = "emobservation"
    description = textwrap.dedent("""\
        Retrieve information about a single EM observation associated with an
        event or superevent
    """).rstrip()
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "N",
            type=int,
            help="Index number of the EM observation"
        )
        return parser

    def run(self, client, args):
        return client.emobservations(args.object_id,
                                     emobservation_num=args.N)


class GetEventCommand(GetChildBase):
    name = "event"
    description = "Retrieve information about a single event"
    parent_parsers = (graceid_parser,)

    def run(self, client, args):
        return client.event(args.graceid)


class GetFileCommand(GetChildBase):
    name = "file"
    description = "Download a file associated with an event or superevent"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "filename",
            type=str,
            help="Name of file (on the server) to download"
        )
        parser.add_argument(
            "destination",
            type=str,
            nargs='?',
            help=("Path to save file at. Default is '-', which prints "
                  "the contents to stdout"),
            default='-'
        )
        return parser

    def run(self, client, args):
        # Check that we *could* write the file before we go to the trouble
        # of getting it.  Also, try not to open a file until we know that we
        # we have data.
        if args.destination != '-':
            full_dir_path = os.path.dirname(os.path.abspath(args.destination))
            if not os.access(full_dir_path, os.W_OK):
                raise IOError("{0}: permission denied".format(
                              args.destination))

        # Get file content
        response = client.files(args.object_id, args.filename)

        # Handle response
        if response.status_code == 200:
            if args.destination == '-':
                # For stdout, return string contents of file
                file_contents = response.read()
                return file_contents
            else:
                # Otherwise, save to file and return string message
                with open(args.destination, 'wb') as fh:
                    shutil.copyfileobj(response, fh)
                return "File '{fname}' for {obj_id} saved at {path}".format(
                    fname=args.filename, obj_id=args.object_id,
                    path=args.destination)
        else:
            # On error, return full response
            return response


class GetLabelCommand(GetChildBase):
    name = "label"
    description = \
        "Get information about a label attached to an event or superevent"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument("label", type=str, help="Label name")
        return parser

    def run(self, client, args):
        return client.labels(args.object_id, label=args.label)


class GetLogCommand(GetChildBase):
    name = "log"
    description = "Retrieve an event or superevent log entry"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "N",
            type=int,
            help="Index number of the log entry"
        )
        return parser

    def run(self, client, args):
        return client.logs(args.object_id, log_number=args.N)


class GetSignoffCommand(GetChildBase):
    name = "signoff"
    description = "Retrieve a superevent signoff"
    long_description = textwrap.dedent("""\
        Retrieve a signoff attached to a superevent. Event signoff retrieval
        is not presently implemented.
    """).rstrip()
    parent_parsers = (superevent_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "signoff_type",
            type=str,
            help=("Signoff type (do '{prog} info signoff_types' to see "
                  "options)").format(prog=self.base_prog)
        )
        parser.add_argument(
            "instrument",
            type=str,
            nargs='?',
            help=("Instrument code (do '{prog} info instruments' to see "
                  "options). Required for operator signoffs.")
            .format(prog=self.base_prog)
        )
        return parser

    def run(self, client, args):
        instrument = args.instrument or ''  # Convert None to ''
        return client.signoffs(
            args.superevent_id, signoff_type=args.signoff_type,
            instrument=instrument
        )


class GetSupereventCommand(GetChildBase):
    name = "superevent"
    description = "Retrieve information about a single superevent"
    parent_parsers = (superevent_id_parser,)

    def run(self, client, args):
        return client.superevent(args.superevent_id)


class GetVoeventCommand(GetChildBase):
    name = "voevent"
    description = "Retrieve a VOEvent associated with an event or superevent"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument("N", type=int, help="Index number of the VOEvent")
        return parser

    def run(self, client, args):
        return client.voevents(args.object_id, voevent_num=args.N)
