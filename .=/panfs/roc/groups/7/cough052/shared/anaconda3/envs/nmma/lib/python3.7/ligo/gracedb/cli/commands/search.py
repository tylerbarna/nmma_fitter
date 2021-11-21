import textwrap
import sys

from .base import RegisteredCommandBase, RegisteredSubCommandBase
from ..utils import parse_delimited_string


# Command registry - don't touch!
registry = []


###############################################################################
# Base command
###############################################################################
class SearchCommand(RegisteredCommandBase):
    name = "search"
    description = "Get a list of events or superevents based on a search query"
    subcommands = registry


###############################################################################
# Subcommands - registered to base command automatically
###############################################################################
class SearchChildBase(RegisteredSubCommandBase):
    _registry = registry


class SearchSupereventsCommand(SearchChildBase):
    name = "superevents"
    description = "Get a list of superevents based on a search query"
    long_description = textwrap.dedent("""\
        Get a list of superevents matching a given search query and
        print their attributes as a list of delimited columns.
    """).rstrip()
    default_columns = \
        "superevent_id,preferred_event,gw_events,labels,far,links.files"
    client_func = "superevents"

    def add_custom_arguments(self, parser):
        parser.add_argument(
            "query",
            type=str,
            help="Search query (surround with quotes)"
        )
        parser.add_argument(
            "--columns",
            type=parse_delimited_string,
            help=("Comma-separated list of parameters to show for each search "
                  "result. Use '.' to get nested parameters "
                  "(ex: 'links.files')"),
            default=self.default_columns
        )
        parser.add_argument(
            "--max-results",
            type=int,
            help="Maximum number of results to show",
            default=None
        )
        parser.add_argument(
            "--delimiter",
            type=str,
            default="TAB",
            help="Delimiter for output"
        )
        return parser

    def run(self, client, args):
        # Call client function to get iterator
        func = getattr(client, self.client_func)
        iterator = func(args.query, max_results=args.max_results)

        # Compile output
        output = []
        for item in iterator:
            output.append([self.process_element(item, col) for col in
                           args.columns])

        # Kludge for handling delimiter (if we set the default directly as
        # \t, it's not obvious in the help message)
        delim = args.delimiter
        if args.delimiter == 'TAB':
            delim = '\t'

        # Add title line
        output = [args.columns] + output

        # Join it all into a string
        out = '#' + "\n".join([delim.join(row) for row in output])
        return out

    def process_element(self, item, col):
        """
        Get values from nested dictionaries and join lists into
        comma-separated strings.
        """
        col_levels = col.split('.')
        a = item
        for c in col_levels:
            try:
                a = a[c]
            except KeyError:
                msg = ("'{col}' is not available in the response JSON. Check "
                       "the format on the server or by using '{prog} get' to "
                       "retrieve an individual event or superevent.") \
                    .format(col=col, prog=self.base_prog)
                print(msg)
                sys.exit(1)

        # Join lists into a comma-separated string
        if isinstance(a, list):
            a = ",".join(a)

        # Convert to string and return
        return str(a)


class SearchEventsCommand(SearchSupereventsCommand):
    name = "events"
    description = "Get a list of events based on a search query"
    long_description = textwrap.dedent("""\
        Get a list of events matching a given search query and
        print their attributes as a list of delimited columns.
    """).rstrip()
    default_columns = \
        "graceid,labels,group,pipeline,far,gpstime,created"
    client_func = "events"
