# Tests for subcommands below 'create'
#  Ex: 'gracedb create emobservation'
import pytest
import shlex
try:
    from unittest import mock
except ImportError:
    import mock

# Apply module-level mark
pytestmark = pytest.mark.cli


###############################################################################
# Tests of individual subcommands #############################################
###############################################################################
CMD_DATA = ['events', 'superevents']
@pytest.mark.parametrize("command", CMD_DATA)  # noqa: E302
def test_search_subcommand(CLI, command):
    """Test search events and superevents subcommands"""
    query = 'fake query'

    # Compile command
    cols = ['col1', 'col2.test']
    max_results = 4
    cmd = 'search {cmd} "{query}" --columns={cols} --max-results={N}' \
        .format(cmd=command, query=query, cols=','.join(cols), N=max_results)

    # Mock return value
    rv = [
        {'col1': 11, 'col2': {'test': 21}},
        {'col1': 12, 'col2': {'test': 22}},
        {'col1': 13, 'col2': {'test': 23}},
        {'col1': 14, 'col2': {'test': 24}},
    ]

    func = 'ligo.gracedb.rest.GraceDb.{cmd}'.format(cmd=command)
    with mock.patch(func) as mock_cli_func:
        mock_cli_func.return_value = iter(rv)
        response = CLI(shlex.split(cmd))

    # Check call count
    assert mock_cli_func.call_count == 1

    # Get args used in function call
    cli_args, cli_kwargs = mock_cli_func.call_args

    # Check args used in function call
    assert cli_args == (query,)
    assert cli_kwargs == {'max_results': max_results}

    # Check response
    lines = response.split('\n')
    assert lines[0] == '#{headers}'.format(headers="\t".join(cols))
    for i, line in enumerate(lines[1:]):
        assert line == '\t'.join(
            [str(rv[i]['col1']), str(rv[i]['col2']['test'])])
