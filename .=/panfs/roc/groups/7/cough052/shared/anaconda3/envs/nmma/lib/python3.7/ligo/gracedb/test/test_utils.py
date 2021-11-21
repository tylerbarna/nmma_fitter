import pytest

from ligo.gracedb.utils import handle_str_or_list_arg


def test_str_or_list_arg_processor_str():
    data = 'test_str'
    out = handle_str_or_list_arg(data, 'arg_name')
    assert out == [data]


@pytest.mark.parametrize("data", [None, {}, (), [], False])
def test_str_or_list_arg_processor_falsey(data):
    out = handle_str_or_list_arg(data, 'arg_name')
    assert out == data


def test_str_or_list_arg_processor_list():
    data = [1, 2, 3]
    out = handle_str_or_list_arg(data, 'arg_name')
    assert out == data


@pytest.mark.parametrize("data", [{'a': 1}, (1, 2,), 1, 3.4, True])
def test_str_or_list_arg_processor_bad_data(data):
    arg_name = 'arg_name'
    err_msg = "{an} arg is {at}, should be str or list".format(
        an=arg_name, at=type(data))
    with pytest.raises(TypeError, match=err_msg):
        handle_str_or_list_arg(data, arg_name)
