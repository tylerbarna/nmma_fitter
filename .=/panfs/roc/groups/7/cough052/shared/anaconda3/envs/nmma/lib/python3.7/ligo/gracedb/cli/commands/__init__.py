# Instructions for adding new commands
# Most are double-level commands (i.e., gracedb create event [params]) vs.
# single-level commands (gracedb expose [params])

# The command registry is populated by a custom metaclass when new commands
# are created. The commands must be imported here to ensure that they are added
# to the registry.
# Note that this command_registry is imported in ligo.gracedb.cli.commands.base
# so that it can be populated there.
command_registry = []


from .add import AddCommand
from .create import CreateCommand
from .delete import DeleteCommand
from .get import GetCommand
from .list import ListCommand
from .remove import RemoveCommand
from .search import SearchCommand
from .update import UpdateCommand

# Other single-level commands
from .subcommands import (
    ConfirmAsGwCommand, CredentialsCommand, ExposeCommand, HideCommand,
    PingCommand, InfoCommand, ShowCommand,
)


__all__ = ['command_registry']
