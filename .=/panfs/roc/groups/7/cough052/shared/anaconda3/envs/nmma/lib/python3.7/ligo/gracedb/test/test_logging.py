import logging
try:
    from unittest import mock
except ImportError:  # py < 3
    import mock
import time
import types

from ligo.gracedb.logging import GraceDbLogHandler


def test_logger(safe_client):
    # Data
    obj_id = 'T123456'
    comment = 'test comment'
    logger_name = 'testing'
    log_method = 'warning'

    # Set up logger
    logging.basicConfig()
    log = logging.getLogger(logger_name)
    log.propagate = False  # Don't write to console

    # For some reason, mocking with mock.patch() and a context manager
    # was not working well, so we're doing this instead.
    mock_write_log = mock.MagicMock()
    safe_client.writeLog = types.MethodType(mock_write_log, safe_client)

    # Set up the handler and use the logger
    handler = GraceDbLogHandler(safe_client, obj_id)
    log.addHandler(handler)
    getattr(log, log_method)(comment)

    # Check results - there must be something weird with threading going on
    # since if we don't sleep here, mock_write_log.call_args returns as None
    time.sleep(0.01)
    call_args, call_kwargs = mock_write_log.call_args
    assert mock_write_log.call_count == 1
    assert call_kwargs == {}
    assert len(call_args) == 3
    assert call_args[1] == obj_id
    expected_comment = '{lvl}:{logger_name}:{comment}'.format(
        lvl=log_method.upper(), logger_name=logger_name, comment=comment)
    assert expected_comment in call_args[2]
