import textwrap

from .base import RegisteredCommandBase, RegisteredSubCommandBase
from ..parsers import object_id_parser, superevent_id_parser, graceid_parser


# Command registry - don't touch!
registry = []


###############################################################################
# Base command
###############################################################################
class RemoveCommand(RegisteredCommandBase):
    name = "remove"
    description = textwrap.dedent("""\
        Remove a label from an event or superevent, a tag from a log
        entry, or an event from a superevent
    """).rstrip()
    subcommands = registry


###############################################################################
# Subcommands - registered to base command automatically
###############################################################################
class RemoveChildBase(RegisteredSubCommandBase):
    _registry = registry


class RemoveLabelCommand(RemoveChildBase):
    name = "label"
    description = "Remove a label from an event or superevent"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument("label", type=str, help="Name of label to remove")
        return parser

    def run(self, client, args):
        return client.removeLabel(args.object_id, args.label)


class RemoveTagCommand(RemoveChildBase):
    name = "tag"
    description = "Remove a tag from a log entry"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "log_number",
            type=int,
            help="Index number of log entry"
        )
        parser.add_argument("tag_name", type=str, help="Name of tag to remove")
        return parser

    def run(self, client, args):
        return client.removeTag(args.object_id, args.log_number, args.tag_name)


class RemoveEventCommand(RemoveChildBase):
    name = "event"
    description = "Remove an event from a superevent"
    parent_parsers = (superevent_id_parser, graceid_parser,)

    def run(self, client, args):
        return client.removeEventFromSuperevent(args.superevent_id,
                                                args.graceid)
