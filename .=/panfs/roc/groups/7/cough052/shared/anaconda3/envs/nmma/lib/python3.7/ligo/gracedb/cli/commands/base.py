import argparse
from six import with_metaclass
import sys

from . import command_registry
from ..parsers import CustomHelpArgumentParser


class CommandBase(object):
    """Class for a base or intermediate command"""
    name = None
    description = ""
    subcommands = []
    show_usage_args = True
    legacy = False

    def __init__(self, base_prog=None, parent_prog=None):
        # Get prog name
        prog = self.get_prog(parent_prog)

        # Set up list of tuples of subcommand name and the subcommand
        # object itself, sorted by name
        self.subcommand_list = sorted([(sc.name, sc) for sc in
                                      self.subcommands])

        # Set up dict of subcommands, where key is name and value is
        # the subcommand
        self.subcommand_dict = {sc.name: sc for sc in self.subcommands}

        # Set up parser description; add period to end if it doesn't have one
        description = getattr(self, 'long_description', self.description)
        if description and description[-1] != '.':
            description += '.'

        # Set up main parser
        parser_kwargs = {
            'description': description,
            'show_usage_args': self.show_usage_args,
            'subcommands': self.subcommand_list,
        }
        if prog:
            parser_kwargs['prog'] = prog
        parser = CustomHelpArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            **parser_kwargs)
        parser = self.add_custom_arguments(parser)

        # Attach parser to instance
        self.parser = parser

        # Set up epilog
        parser.epilog = ("\n\nUse '{prog} <command> --help' to read about a "
                         "specific command.").format(prog=parser.prog)

        # Store base prog name
        self.base_prog = base_prog

    def __call__(self, client, args=None):
        # Parse args
        cmd, main_args, cmd_args = self.parse_args(args)
        return cmd(client, cmd_args)

    def parse_args(self, args):
        # Modify args to allow passing --help flag to subcommands
        modified_args = [arg for arg in args if (arg != '--help'
                         and arg != '-h')]

        # Check if help is requested (or needed)
        send_help = False
        if (len(modified_args) < len(args)):
            send_help = True

        # Parse args
        main_args, cmd_args = self.parser.parse_known_args(modified_args)

        # Store the args specific to this level
        self.args = main_args

        # If send_help and no command is specified, print help and exit
        if main_args.command is None:
            if send_help:
                self.parser.print_help()
                sys.exit(0)
            else:
                self.parser.error('too few arguments')

        # Get subcommand and instantiate it
        try:
            sc_index = [sc.name for sc in self.subcommands].index(
                main_args.command)
        except ValueError:
            # Command not found
            error_str = ("Command '{prog} {cmd}' not found. Do "
                         "'{prog} --help' to see available commands.\n") \
                .format(prog=self.parser.prog, cmd=main_args.command)
            print(error_str)
            sys.exit(1)

        # If base_prog is not set, assume this is the base prog
        base_prog = self.base_prog or self.parser.prog
        subcommand = self.subcommands[sc_index](parent_prog=self.parser.prog,
                                                base_prog=base_prog)

        # Append --help to cmd_args, if needed
        if send_help:
            cmd_args.append('--help')

        return subcommand, main_args, cmd_args

    def add_custom_arguments(self, parser):
        parser.add_argument("command", nargs='?')
        return parser

    def get_prog(self, parent_prog=None):
        if parent_prog:
            prog = "{parent} {name}".format(parent=parent_prog, name=self.name)
        elif self.name is None:
            return None
        else:
            prog = self.name
        return prog


class SubCommandBase(object):
    """Class for a subcommand"""
    parent_parsers = ()
    legacy = False

    def __init__(self, base_prog=None, parent_prog=None):
        # Store base prog name
        self.base_prog = base_prog

        # Description - if no long description is given, use the description.
        # Add a period if it doesn't end in one; this looks better in the
        # individual command description, but not in the list of commands
        description = getattr(self, 'long_description', self.description)
        if description and description[-1] != '.':
            description += '.'

        # Set up parser
        parser = argparse.ArgumentParser(
            description=description,
            parents=self.parent_parsers,
            prog=self.get_prog(parent_prog),
            formatter_class=argparse.ArgumentDefaultsHelpFormatter
        )
        parser = self.add_custom_arguments(parser)
        self.parser = parser

    def __call__(self, client, args):
        parsed_args = self.parser.parse_args(args)
        return self.run(client, parsed_args)

    def get_prog(self, parent_prog=None):
        if parent_prog:
            prog = "{parent} {name}".format(parent=parent_prog, name=self.name)
        elif self.name is None:
            return None
        else:
            prog = self.name
        return prog

    def add_custom_arguments(self, parser):
        return parser

    def run(self, client, args):
        return NotImplemented


###############################################################################
# Registering commands
###############################################################################
class RegisteredCommandMeta(type):
    def __new__(meta, name, bases, attrs):
        cls = type.__new__(meta, name, bases, attrs)
        if (hasattr(cls, '_register') and callable(cls._register)):
            if ('Base' not in name):
                cls._register()
        return cls


class RegisteredCommandBase(
    with_metaclass(RegisteredCommandMeta, CommandBase)
):

    @classmethod
    def _register(cls):
        if hasattr(cls, '_registry'):
            cls._registry.append(cls)
        else:
            command_registry.append(cls)


class RegisteredSubCommandBase(SubCommandBase, RegisteredCommandBase):
    pass
