import os
import textwrap

from .base import RegisteredCommandBase, RegisteredSubCommandBase
from ..parsers import (
    object_id_parser, comment_parser, tag_parser,
    superevent_id_parser,
)
from ..utils import parse_delimited_string, parse_delimited_string_or_single

# Command registry - don't touch!
registry = []


###############################################################################
# Utilities
###############################################################################
def delimited_float(s):
    return parse_delimited_string(s, cast=float)


def delimited_or_single_float(s):
    return parse_delimited_string_or_single(s, cast=float)


###############################################################################
# Base command
###############################################################################
class CreateCommand(RegisteredCommandBase):
    name = "create"
    description = textwrap.dedent("""\
        Create an event, superevent, log entry, signoff, EM observation,
        or VOEvent
    """).rstrip()
    subcommands = registry


###############################################################################
# Subcommands - registered to base command automatically
###############################################################################
class CreateChildBase(RegisteredSubCommandBase):
    _registry = registry


class CreateEmobservationCommand(CreateChildBase):
    name = "emobservation"
    description = "Upload EM observation data for an event or superevent"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "group",
            type=str,
            help=("Name of EM MOU group making the observation "
                  "(do '{prog} info emgroups' to see options)")
            .format(prog=self.base_prog)
        )
        parser.add_argument(
            "right_ascension",
            type=delimited_float,
            help=("Comma-separated list of right ascension coordinates "
                  "(degrees)")
        )
        parser.add_argument(
            "right_ascension_width",
            type=delimited_or_single_float,
            help=("Comma-separated list of right ascension measurement widths "
                  "OR a single number if all measurements have the same width "
                  "(degrees)")
        )
        parser.add_argument(
            "declination",
            type=delimited_float,
            help=("Comma-separated list of declination coordinates (degrees)")
        )
        parser.add_argument(
            "declination_width",
            type=delimited_or_single_float,
            help=("Comma-separated list of declination measurement widths "
                  "OR a single number if all measurements have the same width "
                  "(degrees)")
        )
        parser.add_argument(
            "start_time",
            type=parse_delimited_string,
            help=("Comma-separated list of measurement start times in ISO "
                  "8601 format")
        )
        parser.add_argument(
            "duration",
            type=delimited_or_single_float,
            help=("List of exposure times OR a single number if all "
                  "measurements have the same exposure (seconds)")
        )
        parser.add_argument(
            "--comment", type=str, help="Comment about the observation"
        )
        return parser

    def run(self, client, args):
        return client.writeEMObservation(
            args.object_id, args.group, args.right_ascension,
            args.right_ascension_width, args.declination,
            args.declination_width, args.start_time, args.duration,
            comment=args.comment
        )


class CreateEventCommand(CreateChildBase):
    name = "event"
    description = "Create an event"
    long_description = textwrap.dedent("""\
        Create an event on the server by uploading an event data file.
    """).rstrip()

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "group",
            type=str,
            help=("Analysis group which identified the event "
                  "(do '{prog} info groups' to see options)")
            .format(prog=self.base_prog)
        )
        parser.add_argument(
            "pipeline",
            type=str,
            help=("Analysis pipeline which identified the event "
                  "(do '{prog} info pipelines' to see options)")
            .format(prog=self.base_prog)
        )
        parser.add_argument("event_file", type=str, help="Event data file")
        parser.add_argument(
            "search",
            type=str,
            nargs='?',
            help=("Search type (do '{prog} info searches' to see "
                  "options)").format(prog=self.base_prog)
        )
        parser.add_argument(
            "--labels",
            type=parse_delimited_string_or_single,
            help=("Label or comma-separated list of labels to apply to the "
                  "event upon creation")
        )
        parser.add_argument(
            "--offline",
            action="store_true",
            default=False,
            help="Signifies that the event was found by an offline analysis"
        )
        return parser

    def run(self, client, args):
        # Handle case where user reverses order of search and event file
        # We don't print a warning (for now) since this is mimicing
        # legacy behavior
        event_file = args.event_file
        search = args.search
        if event_file in client.searches and os.path.isfile(search):
            temp = event_file
            event_file = search
            search = temp

        return client.createEvent(
            args.group, args.pipeline, event_file, search=search,
            offline=args.offline, labels=args.labels
        )


class CreateLogCommand(CreateChildBase):
    name = "log"
    description = "Create a log entry, with optional file upload"
    long_description = textwrap.dedent("""\
        Annotate an event or superevent by creating a log entry. The entry
        may include data, links, or other comments. Files may be uploaded
        along with the log entry. Tags can be applied to the log entry
        upon its creation.
    """).rstrip()
    parent_parsers = (object_id_parser, comment_parser, tag_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument("filename", type=str, nargs='?',
                            help="Path to file to be uploaded (optional)")
        return parser

    def run(self, client, args):
        return client.writeLog(
            args.object_id, args.comment, filename=args.filename,
            tag_name=args.tag_name, displayName=args.tag_display_name
        )


class CreateSignoffCommand(CreateChildBase):
    name = "signoff"
    description = "Create an operator or advocate signoff"
    long_description = textwrap.dedent("""\
        Create an operator or advocate signoff. Only allowed for superevents
        which are labeled with the corresponding *OPS or ADVREQ labels. Event
        signoff creation is not presently implemented.
    """).rstrip()
    parent_parsers = (superevent_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "signoff_type",
            type=str,
            help=("Signoff type (do '{prog} info signoff_types') to see "
                  "options").format(prog=self.base_prog)
        )
        parser.add_argument(
            "signoff_status",
            type=str,
            help=("Signoff type (do '{prog} info signoff_statuses') to see "
                  "options").format(prog=self.base_prog)
        )
        parser.add_argument(
            "comment",
            type=str,
            help="Justification for signoff status"
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
        return client.create_signoff(
            args.superevent_id, args.signoff_type, args.signoff_status,
            args.comment, instrument=instrument
        )


class CreateSupereventCommand(CreateChildBase):
    name = "superevent"
    description = "Create a superevent"
    long_description = textwrap.dedent("""\
        Create a superevent by specifying t_start, t_0, t_end, and the
        graceid of an event to set as the 'preferred_event'. An additional
        list of event graceids to include in the superevent can also be
        supplied.
    """).rstrip()

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "t_start",
            type=float,
            help="t_start of superevent"
        )
        parser.add_argument("t_0", type=float, help="t_0 of superevent")
        parser.add_argument("t_end", type=float, help="t_end of superevent")
        parser.add_argument(
            "preferred_event",
            type=str,
            help="Graceid of the preferred event"
        )
        parser.add_argument(
            "--category",
            type=str,
            default="production",
            help=("Superevent category (do '{prog} info superevent_categories "
                  "to see options'").format(prog=self.base_prog)
        )
        parser.add_argument(
            "--events",
            type=parse_delimited_string_or_single,
            help=("Comma-separated list of graceids corresponding to events "
                  "which should be added to this superevent")
        )
        parser.add_argument(
            "--labels",
            type=parse_delimited_string_or_single,
            help=("Label or comma-separated list of labels to apply to the "
                  "superevent upon creation")
        )
        return parser

    def run(self, client, args):
        return client.createSuperevent(
            args.t_start, args.t_0, args.t_end, args.preferred_event,
            category=args.category, events=args.events, labels=args.labels
        )


class CreateVoeventCommand(CreateChildBase):
    name = "voevent"
    description = "Create a VOEvent for an event or superevent"
    parent_parsers = (object_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "voevent_type",
            type=str,
            help=("VOEvent type (do '{prog} info voevent_types to"
                  "see options'").format(prog=self.base_prog)
        )
        parser.add_argument(
            "--skymap-type",
            type=str,
            help="Skymap type (required for VOEvents which include a skymap)"
        )
        parser.add_argument(
            "--skymap-filename",
            type=str,
            help=("Name of skymap file on the server (required for initial "
                  "and update alerts, optional for preliminary)")
        )
        parser.add_argument(
            "--external",
            action='store_true',
            default=False,
            help=("Signifies that the VOEvent should be distributed outside "
                  "the LVC")
        )
        parser.add_argument(
            "--open-alert",
            action='store_true',
            default=False,
            help="Signifies that the candidate is an open alert"
        )
        parser.add_argument(
            "--hardware-inj",
            action='store_true',
            default=False,
            help="The candidate is a hardware injection"
        )
        parser.add_argument(
            "--coinc-comment",
            action='store_true',
            default=False,
            help="The candidate has a possible counterpart GRB"
        )
        parser.add_argument(
            "--prob-has-ns",
            type=float,
            default=None,
            help=("Probability that one object in the binary has mass less "
                  "than 3 M_sun (0.0 - 1.0)")
        )
        parser.add_argument(
            "--prob-has-remnant",
            type=float,
            default=None,
            help=("Probability that there is matter in the surroundings of "
                  "the central object (0.0 - 1.0)")
        )
        parser.add_argument(
            "--bns",
            type=float,
            default=None,
            help=("Probability that the source is a binary neutron star "
                  "merger (0.0 - 1.0)")
        )
        parser.add_argument(
            "--nsbh",
            type=float,
            default=None,
            help=("Probability that the source is a neutron star-black hole "
                  "merger (0.0 - 1.0)")
        )
        parser.add_argument(
            "--bbh",
            type=float,
            default=None,
            help=("Probability that the source is a binary black hole "
                  "merger (0.0 - 1.0)")
        )
        parser.add_argument(
            "--terrestrial",
            type=float,
            default=None,
            help="Probability that the source is terrestrial (0.0 - 1.0)"
        )
        parser.add_argument(
            "--mass-gap",
            type=float,
            default=None,
            help=("Probability that at least one object in the binary is "
                  "between 3 and 5 solar masses")
        )
        return parser

    def run(self, client, args):
        return client.createVOEvent(
            args.object_id, args.voevent_type, skymap_type=args.skymap_type,
            skymap_filename=args.skymap_filename, internal=(not args.external),
            open_alert=args.open_alert, hardware_inj=args.hardware_inj,
            CoincComment=args.coinc_comment, ProbHasNS=args.prob_has_ns,
            ProbHasRemnant=args.prob_has_remnant, BNS=args.bns, NSBH=args.nsbh,
            BBH=args.bbh, Terrestrial=args.terrestrial, MassGap=args.mass_gap
        )
