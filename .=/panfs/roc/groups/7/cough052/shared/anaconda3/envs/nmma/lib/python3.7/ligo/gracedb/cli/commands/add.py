import textwrap

from .base import RegisteredCommandBase, RegisteredSubCommandBase
from ..parsers import object_id_parser, superevent_id_parser


# Command registry - don't touch!
registry = []


###############################################################################
# Base command
###############################################################################
class AddCommand(RegisteredCommandBase):
    name = "add"
    description = textwrap.dedent("""\
        Add a label to an event or superevent, a tag to a log
        entry, or an event to a superevent
    """).rstrip()
    subcommands = registry


###############################################################################
# Subcommands - registered to base command automatically
###############################################################################
class AddChildBase(RegisteredSubCommandBase):
    _registry = registry


class AddEventCommand(AddChildBase):
    name = "event"
    description = "Add an event to a superevent"
    long_description = textwrap.dedent("""\
        Add an event to a superevent. They must fall in the same 'category';
        i.e., production, test, or MDC. Special permissions are required for
        non-Test events and superevents.
    """).rstrip()
    parent_parsers = (superevent_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            'graceid',
            type=str,
            help='Graceid of event to add to superevent'
        )
        return parser

    def run(self, client, args):
        return client.addEventToSuperevent(args.superevent_id, args.graceid)


class AddLabelCommand(AddChildBase):
    name = "label"
    description = "Add a label to an event or superevent"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "label",
            type=str,
            help=("Name of label to apply (do '{prog} info labels' to see "
                  "options)").format(prog=self.base_prog)
        )
        return parser

    def run(self, client, args):
        return client.writeLabel(args.object_id, args.label)


class AddTagCommand(AddChildBase):
    name = "tag"
    description = "Add a tag to an event or superevent log entry"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "log_number",
            metavar="N",
            type=int,
            help="Index number of log entry"
        )
        parser.add_argument(
            "tag_name",
            type=str,
            help="Name of tag to apply")
        parser.add_argument(
            "-d",
            "--tag-display-name",
            type=str,
            help="Display name for tag (new tags only)"
        )
        return parser

    def run(self, client, args):
        return client.addTag(
            args.object_id, args.log_number, tag_name=args.tag_name,
            displayName=args.tag_display_name
        )
