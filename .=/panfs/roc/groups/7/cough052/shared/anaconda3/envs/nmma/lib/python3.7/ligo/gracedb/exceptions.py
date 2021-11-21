# Custom exceptions
import requests.exceptions


class HTTPError(requests.exceptions.HTTPError):
    def __init__(self, response):
        self.response = response
        self.status_code = response.status_code
        self.status = response.status_code
        self.reason = response.reason
        self.message = response.text
        self.text = response.text
        Exception.__init__(self, response)
