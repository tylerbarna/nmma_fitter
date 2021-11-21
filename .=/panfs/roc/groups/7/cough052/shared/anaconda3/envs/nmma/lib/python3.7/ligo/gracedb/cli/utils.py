# Utils for command processing


def parse_delimited_string(data, delim=",", cast=None):
    """
    Parse a delimited string into a list. Can cast list elements to a type by
    setting 'cast' to a callable, like int.

    Examples:
        data='a,b,c,d' should give output ['a', 'b', 'c', 'd']
        data='1.2,1.4' should give output [1.2, 1.4] (with cast=float)
    """
    # Split data
    split_data = data.split(delim)

    # Cast data
    if cast is not None:
        split_data = [cast(element) for element in split_data]

    return split_data


def parse_delimited_string_or_single(data, delim=",", cast=None):
    """
    Parse a possibly-delimited string into a list or a single item.
    See docstring for 'parse_delimited_string' for more information.

    Examples:
        data='a,b,c,d' should give output ['a', 'b', 'c', 'd']
        data='one_item' should give output 'one_item'
        data='1.2,1.4' should give output [1.2, 1.4] (with cast=float)
        data='10.2' should give output 10.2 (with cast=float)
        data=None should give output None
    """
    if data is None:
        return None

    # Split and cast data
    split_data = parse_delimited_string(data, delim, cast)

    # Check if single element
    if (len(split_data) == 1):
        split_data = split_data[0]

    return split_data
