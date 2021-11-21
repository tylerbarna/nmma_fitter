import textwrap

from .base import RegisteredCommandBase, RegisteredSubCommandBase
from ..parsers import superevent_id_parser, graceid_parser


# Command registry - don't touch!
registry = []


###############################################################################
# Base command
###############################################################################
class UpdateCommand(RegisteredCommandBase):
    name = "update"
    description = textwrap.dedent("""\
        Update an event with a new event file, update a superevent's
        parameters, update a GRB event's parameters, or update an existing
        superevent signoff
    """).rstrip()
    subcommands = registry


###############################################################################
# Subcommands - registered to base command automatically
###############################################################################
class UpdateChildBase(RegisteredSubCommandBase):
    _registry = registry


class UpdateEventCommand(UpdateChildBase):
    name = "event"
    description = "Update an event by uploading a new event data file"
    long_description = textwrap.dedent("""\
        Replace the initial data file which was uploaded to create an event.
        This will cause the event's parameters to be updated based on the newly
        provided data file.
    """).rstrip()
    parent_parsers = (graceid_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "filename",
            type=str,
            help="Path to new event file"
        )
        return parser

    def run(self, client, args):
        return client.replaceEvent(args.graceid, args.filename)


class UpdateSignoffCommand(UpdateChildBase):
    name = "signoff"
    description = "Update a superevent signoff"
    long_description = textwrap.dedent("""\
        Update a superevent signoff with a new status and/or comment.
        Event signoff is not presently implemented.
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
            "instrument",
            type=str,
            nargs='?',
            help=("Instrument code (do {prog} info instruments to see "
                  "options). Required for operator signoffs.")
            .format(prog=self.base_prog)
        )
        parser.add_argument(
            "--status",
            type=str,
            help=("Signoff status (do '{prog} info signoff_statuses') to see "
                  "options").format(prog=self.base_prog)
        )
        parser.add_argument(
            "--comment",
            type=str,
            help="Comment to update the signoff with"
        )
        return parser

    def run(self, client, args):
        instrument = args.instrument or ''  # Convert None to ''
        return client.update_signoff(
            args.superevent_id, args.signoff_type, status=args.status,
            comment=args.comment, instrument=instrument
        )


class UpdateSupereventCommand(UpdateChildBase):
    name = "superevent"
    description = "Update a superevent's parameters"
    long_description = textwrap.dedent("""\
        Update t_start, t_0, t_end, and/or the preferred_event for a superevent
    """).rstrip()
    parent_parsers = (superevent_id_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            '--t-start',
            type=float,
            help="New t_start value for superevent"
        )
        parser.add_argument(
            '--t-0',
            type=float,
            help="New t_0 value for superevent"
        )
        parser.add_argument(
            '--t-end',
            type=float,
            help="New t_end value for superevent"
        )
        parser.add_argument(
            '--preferred-event',
            type=str,
            help="Graceid of new preferred event for superevent"
        )
        return parser

    def run(self, client, args):
        return client.updateSuperevent(
            args.superevent_id, t_0=args.t_0, t_start=args.t_start,
            t_end=args.t_end, preferred_event=args.preferred_event
        )


class UpdateGrbEventCommand(UpdateChildBase):
    name = "grbevent"
    description = "Update GRB event-specific parameters"
    long_description = textwrap.dedent("""\
        Update ra, dec, error_radius, t90, redshift, and/or declination for
        a GRB event.
    """).rstrip()
    parent_parsers = (graceid_parser,)

    def add_custom_arguments(self, parser):
        parser.add_argument(
            '--ra',
            type=float,
            help="New right ascension value for the GRB event (degrees)"
        )
        parser.add_argument(
            '--dec',
            type=float,
            help="New declination value for the GRB event (degrees)"
        )
        parser.add_argument(
            '--error-radius',
            type=float,
            help="New error radius value for the GRB event (degrees)"
        )
        parser.add_argument(
            '--t90',
            type=float,
            help="New t90 value for the GRB event (seconds)"
        )
        parser.add_argument(
            '--redshift',
            type=float,
            help="New redshift value for the GRB event"
        )
        parser.add_argument(
            '--designation',
            type=str,
            help=("New designation for the GRB event (GRByymmddx or "
                  "GRByymmddfff format)")
        )
        return parser

    def run(self, client, args):
        return client.update_grbevent(
            args.graceid, ra=args.ra, dec=args.dec,
            error_radius=args.error_radius, t90=args.t90,
            redshift=args.redshift, designation=args.designation
        )
