import re
import six
import mimetypes
import requests
from functools import wraps
from .exceptions import HTTPError

EVENT_PREFIXES = ['G', 'E', 'H', 'M', 'T']
event_prefix_regex = re.compile(r'^({prefixes})\d+'.format(
    prefixes="|".join(EVENT_PREFIXES)))


# Decorator for class methods so that they work for events or superevents
def event_or_superevent(func):
    @wraps(func)
    def inner(self, object_id, *args, **kwargs):
        is_superevent = True
        if event_prefix_regex.match(object_id):
            is_superevent = False
        return func(self, object_id, is_superevent=is_superevent, *args,
                    **kwargs)
    return inner


# Function for checking arguments which can be strings or lists
# If a string, converts to list for ease of processing
def handle_str_or_list_arg(arg, arg_name):
    if arg:
        if isinstance(arg, six.string_types):
            arg = [arg]
        elif isinstance(arg, list):
            pass
        else:
            raise TypeError("{0} arg is {1}, should be str or list"
                            .format(arg_name, type(arg)))
    return arg


# Convert a dictionary into a list of tuples. This is used when uploading
# MultipartEncoded form data (basically uploading with files). The encoding
# fails when converting dicts of lists {'fruit': ['apple', 'orange']} into
# form-encoded data.
# Source: https://toolbelt.readthedocs.io/en/latest/
#     uploading-data.html#requests_toolbelt.multipart.encoder.MultipartEncoder
def dict_to_form_encoded(body):
    fields = []
    for k, v in body.items():
        if isinstance(v, list):
            for item in v:
                fields.append((k, item))
        else:
            fields.append((k, v))
    return fields


# Guess and return the mimetype of a given file. Otherwise return
# application/octect-stream
def get_mimetype(file_to_send):
    mtype, mencoding = mimetypes.guess_type(file_to_send)
    if not mtype:
        mtype = 'application/octet-stream'
    return mtype


# Add a response "hook" that adds old compatibility methods to request's
# httpresonse. source:
# https://requests.readthedocs.io/en/master/user/advanced/#event-hooks
def hook_response(r, *args, **kwargs):
    r.status = r.status_code


# Another hook: return the raise_for_status behavior which was previously
# enabled in the adjustResponse function.
def raise_status_exception(r, *args, **kwargs):
    try:
        r.raise_for_status()
    except requests.HTTPError as e:
        raise HTTPError(response=e.response)
