# Commonly used argument parsers
import argparse
import textwrap

from .utils import parse_delimited_string, parse_delimited_string_or_single

# Custom parsers for specific arguments

# Object ID parser
object_id_parser = argparse.ArgumentParser(add_help=False)
object_id_parser.add_argument(
    "object_id", type=str, help="Event graceid or superevent id"
)

# Graceid parser
graceid_parser = argparse.ArgumentParser(add_help=False)
graceid_parser.add_argument("graceid", type=str, help="Event graceid")

# Superevent id parser
superevent_id_parser = argparse.ArgumentParser(add_help=False)
superevent_id_parser.add_argument(
    "superevent_id", type=str, help="Superevent id"
)

# Tag parser
tag_parser = argparse.ArgumentParser(add_help=False)
tag_parser.add_argument(
    "-t", "--tag-name", dest="tag_name",
    type=parse_delimited_string_or_single, default=None,
    help="Tag name or comma-separated list of tag names"
)
tag_parser.add_argument(
    "-d", "--tag-display-name", dest="tag_display_name",
    type=parse_delimited_string_or_single, default=None,
    help=("Tag display name or comma-separated list of tag display names "
          "(ignored for existing tags)")
)

# Label parser
label_parser = argparse.ArgumentParser(add_help=False)
label_parser.add_argument(
    "-l", "--labels", dest="labels",
    type=parse_delimited_string, default=None,
    help="Label name or comma-separated list of label names"
)

# Comment parser
comment_parser = argparse.ArgumentParser(add_help=False)
comment_parser.add_argument(
    "comment", type=str, default="",
    help="Comment to be added to the event or superevent log")


# Custom argument parser
class CustomHelpArgumentParser(argparse.ArgumentParser):
    """Must be paired with CommandBase or derived class"""
    _width = 80

    def __init__(self, subcommands=(), show_usage_args=True, *args, **kwargs):
        super(CustomHelpArgumentParser, self).__init__(*args, **kwargs)
        self.subcommands = subcommands
        self.show_usage_args = show_usage_args

    def format_subcommand_list(self):
        HEADER_INDENT = 2
        INITIAL_INDENT = 4
        CMD_COLUMN_WIDTH = 20

        # Header - write with hyphen separators initially so textwrap breaks
        # there and then replace with commas. Use double hyphens just to
        # be safe.
        subcommands = [sc for sc in self.subcommands if not sc[1].legacy]
        header = "Available commands:\n"
        header += textwrap.fill("{{{cmds}}}".format(cmds="--".join(
            [sc[0] for sc in subcommands])), width=self._width,
            initial_indent=' ' * HEADER_INDENT,
            subsequent_indent=' ' * (HEADER_INDENT + 1))
        header = header.replace('--', ',')

        # List of commands
        cmd_list = []
        ii_str = ' ' * INITIAL_INDENT + '{{cmd: <{ccw}}}'
        for cmd_name, cmd in subcommands:
            cmd_entry = ''
            if len(cmd_name) > CMD_COLUMN_WIDTH:
                # Handle case where command name is longer than the
                # allowed length for two nicely formatted columns. In this
                # situation, we put the description on the next line.
                cmd_entry += ' ' * INITIAL_INDENT + cmd_name + '\n'
                cmd_name = ''
            cmd_entry_kwargs = {
                'initial_indent': ii_str.format(ccw=CMD_COLUMN_WIDTH).format(
                    cmd=cmd_name),
                'width': self._width,
                'subsequent_indent': ' ' * (CMD_COLUMN_WIDTH + INITIAL_INDENT),
            }
            cmd_entry += textwrap.fill(cmd.description, **cmd_entry_kwargs)
            cmd_list.append(cmd_entry)

        return header + "\n\n" + "\n".join(cmd_list)

    def format_usage(self):
        # Run super
        usage = super(CustomHelpArgumentParser, self).format_usage()
        # Substitute [command] -> <command> and optionally add [<args>]
        usage = usage.replace('[command]', "<command>{args}".format(
            args=(" [<args>]" if self.show_usage_args else "")))
        return usage

    def format_help(self):
        formatter = self._get_formatter()

        # usage
        # CUSTOM: format usage
        formatter.add_usage(self.format_usage(), self._actions,
                            self._mutually_exclusive_groups, prefix='')

        # description
        # CUSTOM:
        formatter.add_text(textwrap.fill(self.description, width=self._width))

        # positionals, optionals, and user-defined groups
        # CUSTOM: skip positionals since they will only correspond
        # to the commands, which we will list ourselves.
        for action_group in self._action_groups:
            if action_group.title == 'positional arguments':
                continue
            formatter.start_section(action_group.title)
            formatter.add_text(action_group.description)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()

        # CUSTOM: add list of subcommands
        if self.subcommands:
            formatter.add_text(self.format_subcommand_list())

        # epilog
        formatter.add_text(self.epilog)

        # determine help from format above
        return formatter.format_help()
