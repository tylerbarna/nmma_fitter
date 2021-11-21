import textwrap

from .base import RegisteredCommandBase, RegisteredSubCommandBase
from ..parsers import object_id_parser, superevent_id_parser

# Command registry - don't touch!
registry = []


###############################################################################
# Base command
###############################################################################
class ListCommand(RegisteredCommandBase):
    name = "list"
    description = textwrap.dedent("""\
        List files, log entries, labels, EM observations, signoffs, or VOEvents
        associated with an event or superevent, or list tags attached to a log
        entry
    """).rstrip()
    subcommands = registry


###############################################################################
# Subcommands - registered to base command automatically
###############################################################################
class ListChildBase(RegisteredSubCommandBase):
    _registry = registry
    parent_parsers = (object_id_parser,)
    client_func = None

    def run(self, client, args):
        if self.client_func is not None:
            func = getattr(client, self.client_func)
        else:
            func = getattr(client, self.name)

        # Get either object_id, superevent_id, or graceid from args
        object_id_arg = None
        for arg_id in ['object_id', 'superevent_id', 'graceid']:
            if hasattr(args, arg_id):
                object_id_arg = getattr(args, arg_id)
                break
        return func(object_id_arg)


class ListEmobservationsCommand(ListChildBase):
    name = "emobservations"
    description = "List EM observations associated with an event or superevent"


class ListFilesCommand(ListChildBase):
    name = "files"
    description = "List files associated with an event or superevent"


class ListLabelsCommand(ListChildBase):
    name = "labels"
    description = "List labels attached to an event or superevent"


class ListLogsCommand(ListChildBase):
    name = "logs"
    description = "List log entries for an event or superevent"


class ListSignoffsCommand(ListChildBase):
    name = "signoffs"
    description = "List signoffs associated with a superevent"
    long_description = textwrap.dedent("""\
        List signoffs associated with a superevent. Event signoff retrieval
        is not presently implemented.
    """).rstrip()
    parent_parsers = (superevent_id_parser,)


class ListTagsCommand(ListChildBase):
    name = "tags"
    description = "List tags attached to an event or superevent log entry"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "N",
            type=int,
            help="Index number of the log entry"
        )
        return parser

    def run(self, client, args):
        return client.tags(args.object_id, args.N)


class ListVoeventsCommand(ListChildBase):
    name = "voevents"
    description = "List VOEvents associated with an event or superevent"
