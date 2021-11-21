# -*- coding: utf-8 -*-
# Copyright (C) Brian Moe, Branson Stephens (2015)
#
# This file is part of gracedb
#
# gracedb is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# It is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with gracedb.  If not, see <http://www.gnu.org/licenses/>.
from io import open
# import mimetypes
import os
import six
import sys
from six.moves import map
from six.moves.urllib.parse import urlencode

from .exceptions import HTTPError
from .utils import event_or_superevent, dict_to_form_encoded, get_mimetype
from .client import GraceDBClient

DEFAULT_SERVICE_URL = "https://gracedb.ligo.org/api/"


# -----------------------------------------------------------------
# GraceDb REST client
# -----------------------------------------------------------------
class GraceDb(GraceDBClient):
    """GraceDb REST client class.

    Provides a client object for accessing the GraceDB server API.
    Various methods are provided for retrieving information about different
    objects and uploading information.

    Lookup of user credentials is done in the following order:

    #. If provided, import X.509 credentials from the certificate-key \
        pair or combined proxy file provided in the ``cred`` keyword arg.
    #. If provided, use the username and password provided in the \
        keyword arguments.
    #. If the ``X509_USER_CERT`` and ``X509_USER_KEY`` environment variables \
        are set, load the corresponding certificate and key.
    #. If the ``X509_USER_PROXY`` environment variable is set, load the \
        corresponding proxy file.
    #. Look for a X.509 proxy from ligo-proxy-init in the default location \
        (``/tmp/x509up_u${UID}``).
    #. Look for a certificate and key file in ``$HOME/.globus/usercert.pem`` \
        and ``$HOME/.globus/userkey.pem``.
    #. Look for a username and password for the server in ``$HOME/.netrc``.
    #. Continue with no authentication credentials.

    Args:
        url (:obj:`str`, optional): URL of server API root.
        cred (:obj:`tuple` or :obj:`str`, optional): a tuple or list of
            (``/path/to/cert/file``, ``/path/to/key/file``) or a single path to
            a combined proxy file. Used for X.509 authentication only.
        username (:obj:`str`, optional): username for basic auth.
        password (:obj:`str`, optional): password for basic auth.
        force_noauth (:obj:`bool`, optional): set to True if you want to
            skip credential lookup and use this client without
            authenticating to the server.
        fail_if_noauth (:obj:`bool`, optional): set to ``True`` if you want the
            client constructor to fail if no authentication credentials are
            provided or found.
        api_version (:obj:`str`, optional): choose the version of the server
            API to use.  At present, there is only one version, but this
            argument is provided with the expectation that this will change
            in the future.
        reload_certificate (:obj:`bool`, optional): if True, your certificate
            will be checked before each request whether it is within
            ``reload_buffer`` seconds of expiration, and if so, it will be
            reloaded. Useful for processes which may live longer than the
            certificate lifetime and have an automated method for certificate
            renewal. The path to the new/renewed certificate **must** be the
            same as for the old certificate.
        reload_buffer (:obj:`int`, optional): buffer (in seconds) for reloading
            a certificate in advance of its expiration. Only used if
            ``reload_certificate`` is ``True``.

    Examples:
        Instantiate a client to use the production GraceDB server:

        >>> g = GraceDb()

        /se another GraceDB server:

        >>> g = GraceDb(service_url='https://gracedb-playground.ligo.org/api/')

        Use a certificate and key in the non-default location:

        >>> g = GraceDb(cred=('/path/to/cert/file', '/path/to/key/file'))
    """
    def __init__(self, service_url=DEFAULT_SERVICE_URL,
                 cred=None, username=None, password=None,
                 force_noauth=False, fail_if_noauth=False, api_version=None,
                 reload_certificate=False, reload_buffer=300):
        """Create a client instance."""
        super(GraceDb, self).__init__(
            service_url,
            cred=cred, username=username, password=password,
            force_noauth=force_noauth, fail_if_noauth=fail_if_noauth,
            reload_certificate=reload_certificate, reload_buffer=reload_buffer
        )

        # Check version type
        if (api_version is not None and not
            isinstance(api_version, six.string_types)):
            # Raise error is not a string
            raise TypeError('api_version should be a string')

        # Sets default and versioned service URLs
        # (self._service_url, self._versioned_service_url)
        self._set_service_url(service_url, api_version)

        # Set version
        self._api_version = api_version

        # Set service_info to None, will be obtained from the server when
        # the user takes an action which needs this information.
        self._service_info = None

    def _set_service_url(self, service_url, api_version):
        """Sets versioned and unversioned service URLs"""
        # Make sure path ends with '/'
        if not service_url.endswith('/'):
            service_url += '/'

        # Default service url (unversioned)
        self._service_url = service_url

        # Versioned service url (if version provided)
        self._versioned_service_url = service_url
        if api_version and api_version != 'default':
            # If api_version is 'default', that is equivalent to not setting
            # the version and indicates that the user wants to use the
            # default/non-versioned API
            self._versioned_service_url += (api_version + '/')

    @property
    def service_url(self):
        # Will be removed in the future
        print("DEPRECATED: this attribute has been moved to '_service_url'")
        return self._service_url

    @property
    def service_info(self):
        """Gets the root API information."""
        if not self._service_info:
            # try-except block takes user-specified API version to use and
            # checks whether that version is available on the server
            try:
                r = self.request("GET", self._versioned_service_url)
            except HTTPError as e:
                # If we get a 404 error, that means that the versioned
                # service URL was not found. We assume that this happened
                # because the user requested an unavailable API version.
                if (e.status == 404):
                    # Get versions from unversioned API root
                    r = self.request("GET", self._service_url)
                    available_api_versions = r.json().get('API_VERSIONS', None)
                    if available_api_versions:
                        err_msg = ('Bad API version. Available versions for '
                                   'this server are: {0}').format(
                            available_api_versions)
                    else:
                        # Case where server doesn't have versions, for some
                        # reason.
                        err_msg = ('This server does not have a versioned '
                                   'API. Reinstantiate your client without a '
                                   'version.')

                    # Raise error
                    raise ValueError(err_msg)
                else:
                    # Not a 404 error, must be something else
                    raise e
            else:
                if r.status_code != 200:
                    raise HTTPError(r)
            self._service_info = r.json()
        return self._service_info

    @property
    def api_versions(self):
        """List of available API versions on the server."""
        return self.service_info.get('api-versions')

    @property
    def server_version(self):
        """Get the code version being run on the GraceDB server."""
        return self.service_info.get('server-version')

    @property
    def links(self):
        return self.service_info.get('links')

    @property
    def templates(self):
        return self.service_info.get('templates')

    @property
    def groups(self):
        """List of available analysis groups on the server."""
        return self.service_info.get('groups')

    @property
    def pipelines(self):
        """List of  available analysis pipelines on the server."""
        return self.service_info.get('pipelines')

    @property
    def searches(self):
        """List of available search types on the server."""
        return self.service_info.get('searches')

    # Would like to call this 'labels' to keep in line with how
    # other properties are named, but it's already used for a function.
    @property
    def allowed_labels(self):
        """List of available labels on the server."""
        return self.service_info.get('labels')

    @property
    def em_groups(self):
        """List of available EM groups on the server."""
        return self.service_info.get('em-groups')

    @property
    def voevent_types(self):
        """List of available VOEvent types on the server."""
        return self.service_info.get('voevent-types')

    @property
    def superevent_categories(self):
        """List of available superevent categories on the server."""
        return self.service_info.get('superevent-categories')

    @property
    def instruments(self):
        """List of available instruments on the server."""
        return self.service_info.get('instruments')

    @property
    def signoff_types(self):
        """List of available signoff types on the server."""
        return self.service_info.get('signoff-types')

    @property
    def signoff_statuses(self):
        """List of available signoff statuses on the server."""
        return self.service_info.get('signoff-statuses')

#   def request(self, method, url, body=None, headers=None, priming_url=None):
#       if (method.upper() in ['POST', 'PUT'] and self.auth_type == 'x509'):
#           priming_url = self._service_url
#       return super(GraceDb, self).request(
#           method, url, body, headers, priming_url)

    def _getCode(self, input_value, code_dict):
        """
        Check if input is valid and return coded version if it is
        code_dict is dict of {code: descriptive_name}
        """
        # Quick check for simple case where it's already coded
        if input_value in code_dict:
            return input_value

        # Loop over code_dict items, if we match either the key or
        # value (case-insensitive), return the code.
        input_lower = input_value.lower()
        for code, display in six.iteritems(code_dict):
            if (input_lower == code.lower()
                or input_lower == display.lower()):
                return code

        # Not found, return None
        return None

    # Search and filecontents are optional when creating an event.
    def createEvent(self, group, pipeline, filename, search=None, labels=None,
                    offline=False, filecontents=None, **kwargs):
        """Create a new event on the server.

        All LIGO-Virgo users can create events in the 'Test' group. Special
        permissions are required to create non-test events.

        Args:
            group (str): name of the analysis group which identified the
                candidate.
            pipeline (str): name of the analysis pipeline which identified the
                candidate.
            filename (str): path to event file to be uploaded. Use ``'-'`` to
                read from stdin.
            search (:obj:`str`, optional): type of search being run by the
                analysis pipeline.
            labels (:obj:`str` or :obj:`list[str]`, optional): label(s) to
                attach to the event upon creation. Should be a string (single
                label) or list of strings (multiple labels).
            offline (:obj:`bool`, optional): if ``True``, indicates that the
                event was found by an offline analysis.
            filecontents(:obj:`str`, optional): string to be uploaded to the
                server and saved into a file. If event data is uploaded via
                this mechanism, the ``filename`` argument is only used to
                set the name of the file once it is saved on the server.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.createEvent('CBC', 'gstlal', '/path/to/something.xml',
            ... labels='INJ', search='LowMass')
            >>> r.status_code
            201
        """
        if group not in self.groups:
            raise ValueError('bad group')
        if pipeline not in self.pipelines:
            raise ValueError('bad pipeline')
        if search and search not in self.searches:
            raise ValueError('bad search')
        # Process offline arg
        if not isinstance(offline, bool):
            raise TypeError('offline parameter should be a bool')
        # Process label args - convert non-empty strings to list
        # to ensure consistent processing
        if labels is not None:
            if isinstance(labels, six.string_types):
                # Convert to list
                labels = [labels]
            elif isinstance(labels, list):
                pass
            else:
                raise TypeError("labels arg is {0}, should be str or list"
                                .format(type(labels)))
            # Check labels against those in database
            for l in labels:
                if l not in self.allowed_labels:
                    raise ValueError(("Label '{0}' does not exist in the "
                                     "database").format(l))
        if filecontents is None:
            if filename == '-':
                filename = 'initial.data'
                filecontents = sys.stdin.read()
            else:
                filecontents = open(filename, 'rb')

        # Assemble dictionary before converting to multipart form
        # booleans can't be encoded, but the server will convert the
        # string.
        fields = {
            'group': group,
            'pipeline': pipeline,
            'offline': str(offline),
        }
        if search:
            fields.update({'search': search})
        if labels:
            fields.update({'labels': labels})

        # Update fields with additional keyword arguments
        for key, value in six.iteritems(kwargs):
            fields.update({key: value})

        # Assemble files dict and encode.
        files = {'eventFile': (filename,
                               filecontents,
                               get_mimetype(filename))}

        fields.update(files)
        fields = dict_to_form_encoded(fields)
        # fields = MultipartEncoder(fields=fields)
        # headers = {'Content-Type': fields.content_type}

        # Python httplib bug?  unicode link
        uri = str(self.links['events'])

        return self.post(uri, data=fields, files=files)

    def replaceEvent(self, graceid, filename, filecontents=None):
        """Replace an existing event by uploading a new event file.

        The event's parameters are updated from the new file. Only the user
        who originally created the event can update it.

        Args:
            graceid (str): GraceDB ID of the existing event
            filename (str): path to new event file
            filecontents(:obj:`str`, optional): string to be uploaded to the
                server and saved into a file. If event data is uploaded via
                this mechanism, the ``filename`` argument is only used to
                set the name of the file once it is saved on the server.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.replaceEvent('T101383', '/path/to/new/something.xml')
        """
        if filecontents is None:
            # Note: not allowing filename '-' here.  We want the event datafile
            # to be versioned.
            filecontents = open(filename, 'rb')
        return self.put(
            self.templates['event-detail-template'].format(graceid=graceid),
            files={'eventFile': (filename,
                                 filecontents,
                                 get_mimetype(filename))}
        )

    def update_grbevent(self, graceid, ra=None, dec=None, error_radius=None,
                        t90=None, redshift=None, designation=None):
        """Update a GRB event's parameters.

        This method only works on GRB events; i.e., External or Test events
        whose search is specified as 'GRB'.

        Only LIGO/Virgo users with permission to update GRB events will be
        able to utilize this method.

        Args:
            graceid (str): GraceDB ID of the existing event
            ra (:obj:`float`, optional): right ascension (degrees)
            dec (:obj:`float`, optional): declination (degrees)
            error_radius (:obj:`float`, optional): uncertainty in position
                as statistical ~1-sigma error radius from the reported right
                ascension and declination (degrees)
            t90 (:obj:`float`, optional): duration of the event in which 90%
                of the gamma-ray burst fluence was accumulated (seconds)
            redshift (:obj:`float`, optional): redshift
            designation (:obj:`str`, optional): name of the event, typically
                reported in GRByymmddx (where x is null, 'A', or 'B') or
                GRByymmddfff format, where fff is the three-digit fraction
                of the day

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.update_grbevent('E274955', redshift=2.33, ra=135.91)
            >>> r.status
            200
        """  # noqa: W605
        # Make sure that at least one parameter is provided
        if not (ra or dec or error_radius or t90 or redshift or designation):
            raise ValueError('Provide at least one of ra, dec, error_radius, '
                             't90, redshift, or designation')

        request_body = {}
        if ra is not None:
            request_body['ra'] = ra
        if dec is not None:
            request_body['dec'] = dec
        if error_radius is not None:
            request_body['error_radius'] = error_radius
        if t90 is not None:
            request_body['t90'] = t90
        if redshift is not None:
            request_body['redshift'] = redshift
        if designation is not None:
            request_body['designation'] = designation
        template = self.templates['update-grbevent-template']
        uri = template.format(graceid=graceid)
        return self.patch(uri, data=request_body)

    def event(self, graceid):
        """Get information about an individual event.

        Args:
            graceid (str): GraceDB ID of the event

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> event_dict = g.event('T101383').json()
        """
        return self.get(
            self.templates['event-detail-template'].format(graceid=graceid)
        )

    def events(self, query=None, orderby=None, max_results=None, **kwargs):
        """Search for events which match a query.

        Information on forming queries is available here:
        https://gracedb.ligo.org/documentation/queries.html

        Args:
            query (:obj:`str`, optional): query string.
            orderby (:obj:`str`, optional): field to order the results by.
            max_results (:obj:`int`, optional): maximum number of results to
                return (default: all).

        Returns:
            :obj:`Iterator[dict]`

            An iterator which yields individual event dictionaries.

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> for event in g.events('ER5 submitter: "gstlalcbc"'):
            ...     print(event['graceid'], event['far'], event['gpstime'])
        """
        columns = kwargs.pop('columns', None)
        count = kwargs.pop('count', None)
        uri = self.links['events']
        qdict = {}
        if query:
            qdict['query'] = query
        if count is not None:
            qdict['count'] = count
        if orderby:
            qdict['sort'] = orderby
        if columns:
            qdict['columns'] = columns
        if qdict:
            uri += "?" + urlencode(qdict)
        n = 0
        while uri:
            response = self.get(uri).json()
            events = response.get('events', [])
            uri = response.get('links', {}).get('next')

            for event in events:
                n += 1
                if (max_results is not None and n > max_results):
                    return
                yield event

    def numEvents(self, query=None):
        """Get the number of events satisfying a query.

        Args:
            query (:obj:`str`, optional): query string.

        Returns:
            int: The number of events which matched the given query.

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> g.numEvents('ER5 submitter: "gstlalcbc"')
            213
        """
        uri = self.links['events']
        if query:
            uri += "?" + urlencode({'query': query})
        return self.get(uri).json()['numRows']

    def createSuperevent(self, t_start, t_0, t_end, preferred_event,
                         category='production', events=None, labels=None):
        r"""Create a superevent.

        All LIGO-Virgo users can create test superevents, but special
        permissions are required to create production and MDC superevents.

        Args:
            t_start (float): t\ :sub:`start` of the superevent
            t_0 (float): t\ :sub:`0` of the superevent
            t_end (float): t\ :sub:`end` of the superevent
            preferred_event (str): graceid corresponding to the event which
                will be set as the preferred event for this superevent. This
                event must be in the same ``category`` as the superevent and
                not already attached to a superevent.
            category (:obj:`str`, optional): superevent category. Allowed
                choices are: 'production', 'test', 'mdc'.
            events (:obj:`str` or :obj:`list[str]`, optional): graceid or list
                of graceids corresponding to events which should be included in
                this superevent. Events must be in the same ``category`` as the
                superevent and not already attached to a superevent.
            labels (:obj:`str` or :obj:`list[str]`, optional): label or list of
                labels which should be attached to this superevent at creation.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:

            >>> g = GraceDb()
            >>> r = g.createSuperevent(1, 2, 3, 'G123456',
            ... category='production', events=['G100', 'G101'],
            ... labels=['EM_READY', 'DQV'])
            >>> r.status_code
            201
        """  # noqa: W605
        # Process label args - convert non-empty strings to list
        # to ensure consistent processing
        if labels:
            if isinstance(labels, six.string_types):
                labels = [labels]
            elif isinstance(labels, (list, tuple)):
                # Validate each entry
                if any([not isinstance(l, six.string_types) for l in labels]):
                    err_msg = "One of the provided labels is not a string"
                    raise TypeError(err_msg)
            else:
                raise TypeError("labels arg is {0}, should be str or list"
                                .format(type(labels)))
            # Check labels against those in database
            for l in labels:
                if l not in self.allowed_labels:
                    raise ValueError(("Label '{0}' does not exist in the "
                                     "database").format(l))
        if events:
            if isinstance(events, six.string_types):
                events = [events]
            elif isinstance(events, (list, tuple)):
                if any([not isinstance(e, six.string_types) for e in events]):
                    err_msg = \
                        "One of the provided event graceids is not a string"
                    raise TypeError(err_msg)
            else:
                raise TypeError("events arg is {0}, should be str or list"
                                .format(type(events)))

        # Validate category, convert to short form if necessary
        if not isinstance(category, six.string_types):
            err_msg = "category arg is {0}, should be a string".format(
                type(category))
            raise TypeError(err_msg)
        category = self._getCode(category, self.superevent_categories)
        # Note: category can be None here as a result of processing
        # by _getCode, which indicates failure to match the provided
        # superevent category
        if not category:
            raise ValueError("category must be one of: {0}".format(
                list(six.itervalues(self.superevent_categories))))

        # Set up request body for POST
        request_body = {
            't_start': t_start,
            't_0': t_0,
            't_end': t_end,
            'preferred_event': preferred_event,
            'category': category,
        }
        if events:
            request_body['events'] = events
        if labels:
            request_body['labels'] = labels

        # Python httplib bug?  unicode link
        uri = self.links['superevents']
        return self.post(uri, data=request_body)

    def updateSuperevent(self, superevent_id, t_start=None, t_0=None,
                         t_end=None, preferred_event=None, em_type=None,
                         time_coinc_far=None, space_coinc_far=None):
        r"""Update a superevent's parameters.

        The same permission restrictions apply as for
        :py:meth:`ligo.gracedb.rest.GraceDb.createSuperevent`. You must provide
        at least one parameter value to update, otherwise the request will be
        rejected for not providing any new information.

        Args:
            superevent_id (str): GraceDB ID of superevent to update
            t_start (:obj:`float`, optional): new t\ :sub:`start` value for
                superevent
            t_0 (:obj:`float`, optional): new t\ :sub:`0` value for superevent
            t_end (:obj:`float`, optional): new t\ :sub:`end` value for
                superevent
            preferred_event (:obj:`str`, optional): graceid corresponding to
                an event which will be set as the new preferred event for this
                superevent. This event must be in the same ``category`` as the
                superevent (``'production'``, ``'test'``, ``'mdc'``) and must
                either already be a part of this superevent, or not be in a
                superevent at all.
            em_type (:obj:`str`, optional): name of coincident EM search
                for "preferred" EM coincident event. Defined by analyst or
                pipeline (e.g., RAVEN). Default is null for new superevents.
            time_coinc_far (:obj:`float`, optional): new value for temporal
                coincident FAR with preferred EM coincident event. Defined by
                analyst or pipeline  (e.g., RAVEN). Default is null for new
                superevents.
            space_coinc_far (:obj:`float`, optional): new value for temporal
                coincident FAR with preferred EM coincident event. Defined by
                analyst or pipeline  (e.g., RAVEN). Default is null for new
                superevents.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.updateSuperevent('S181224a', t_start=12, preferred_event=
            ... 'G654321')
            >>> r.status_code
            200
        """  # noqa: W605
        # Make sure that at least one parameter is provided
        if not (t_start or t_0 or t_end or preferred_event
                or em_type or time_coinc_far or space_coinc_far):
            raise ValueError('Provide at least one of t_start, t_0, t_end, '
                             'preferred_event, em_type, time_coinc_far, '
                             'or space_coinc_far')

        request_body = {}
        if t_start is not None:
            request_body['t_start'] = t_start
        if t_0 is not None:
            request_body['t_0'] = t_0
        if t_end is not None:
            request_body['t_end'] = t_end
        if preferred_event is not None:
            request_body['preferred_event'] = preferred_event
        if em_type is not None:
            request_body['em_type'] = em_type
        if time_coinc_far is not None:
            request_body['time_coinc_far'] = time_coinc_far
        if space_coinc_far is not None:
            request_body['space_coinc_far'] = space_coinc_far
        template = self.templates['superevent-detail-template']
        uri = template.format(superevent_id=superevent_id)
        return self.patch(uri, data=request_body)

    def addEventToSuperevent(self, superevent_id, graceid):
        """Add an event to a superevent.

        The event must be in the same category as the superevent and must not
        already be part of a superevent.

        Args:
            superevent_id (str): GraceDB ID of the superevent to which the
                event will be added.
            graceid (str): graceid of the event to add to this superevent.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = addEventToSuperevent('S181224a', 'G123456')
            >>> r.status_code
            201
        """
        request_body = {'event': graceid}
        template = self.templates['superevent-event-list-template']
        uri = template.format(superevent_id=superevent_id)
        return self.post(uri, data=request_body)

    def removeEventFromSuperevent(self, superevent_id, graceid):
        """Remove an event from a superevent.

        The event must already be a part of the superevent.

        Args:
            superevent_id (str): GraceDB ID of the superevent from which the
                event will be removed.
            graceid (str): graceid of the event to remove from this superevent.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = removeEventFromSuperevent('S181224a', 'G123456')
            >>> r.status_code
            204
        """
        template = self.templates['superevent-event-detail-template']
        uri = template.format(superevent_id=superevent_id, graceid=graceid)
        return self.delete(uri)

    def superevent(self, superevent_id):
        """Get information about an individual superevent.

        Args:
            superevent_id (str): GraceDB ID of the superevent.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> superevent = g.superevent('S181224a').json()
        """
        return self.get(self.templates['superevent-detail-template'].format(
            superevent_id=superevent_id))

    def superevents(self, query='', orderby=None, count=None, columns=None,
                    max_results=None):
        """Search for superevents which match a query.

        Information on forming queries is available here:
        https://gracedb.ligo.org/documentation/queries.html

        Args:
            query (:obj:`str`, optional): query string.
            orderby (:obj:`str`, optional): field to order the results by.
            count (:obj:`int`, optional): each generator iteration will yield
                this many objects (default determined by the server).
            columns (:obj:`list[str]`, optional): list of attributes to return
                for each superevent (default: all).
            max_results (:obj:`int`, optional): maximum number of results to
                return (default: all).

        Returns:
            :obj:`Iterator[dict]`

            An iterator which yields individual superevent dictionaries.

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> for s in g.superevents(query='is_gw: True', orderby=
            ... ['-preferred_event'], columns=['superevent_id', 'events']):
            ...     print(s['superevent_id'])
        """
        # If columns is a comma-separated string, split it to a list
        if isinstance(columns, six.string_types):
            columns = columns.split(',')

        # If orderby is a list (should be), convert it to a comma-separated
        # string (that's what the server expects)
        if isinstance(orderby, (list, tuple)):
            orderby = ",".join(orderby)

        # Get URI
        uri = self.links['superevents']

        # Compile URL parameters
        qdict = {}
        if query:
            qdict['query'] = query
        if count is not None:
            qdict['count'] = count
        if orderby:
            qdict['sort'] = orderby
        if qdict:
            uri += "?" + urlencode(qdict)

        # Get superevent information and construct a generator
        n = 0
        while uri:
            response = self.get(uri).json()
            superevents = response.get('superevents', [])
            uri = response.get('links', {}).get('next')

            for superevent in superevents:
                n += 1
                if (max_results is not None and n > max_results):
                    return
                # If columns are specified, only return specific values
                if columns:
                    yield {k: superevent[k] for k in columns}
                else:
                    yield superevent

    def confirm_superevent_as_gw(self, superevent_id):
        """Upgrade a superevent's state to 'confirmed GW'.

        All LIGO-Virgo users can perform this action on test superevents,
        but special permissions are required for production and MDC
        superevents. This action cannot be undone!

        Args:
            superevent_id (str): GraceDB ID of the superevent to confirm as
                as GW.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = confirm_superevent_as_gw('S181224a')
            >>> r.status_code
            204
        """
        template = self.templates['superevent-confirm-as-gw-template']
        uri = template.format(superevent_id=superevent_id)
        return self.post(uri)

    @event_or_superevent
    def files(self, object_id, filename="", *args, **kwargs):
        """Get a list of files or download a file associated with an event or
        superevent.

        If ``filename`` is not provided, get a list of available files
        associated with the event or superevent. If ``filename`` *is*
        provided, download the contents of that file.

        Args:
            object_id (str): event graceid or superevent ID.
            filename (:obj:`str`, optional): name of file to download.

        Returns:
            :class:`requests.models.Response`

            When ``filename`` is not specified, ``response.json()`` contains a
            dict with file basename keys and full file URL values.
            When ``filename`` is specified, use ``response.read()`` to get the
            contents of the file.

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Examples:
            Get a list of files:

            >>> g = GraceDb()
            >>> event_files = g.files('T101383').json()
            >>> for filename in list(event_files):
            ...     # do something
            ...     pass

            Get a file's content:

            >>> outfile = open('my_skymap.png', 'w')
            >>> r = g.files('T101383', 'skymap.png')
            >>> outfile.write(r.content)
            >>> outfile.close()
        """
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            uri_kwargs = {'superevent_id': object_id}
            if filename:
                # Get specific file
                uri_kwargs['file_name'] = filename
                template = self.templates['superevent-file-detail-template']
            else:
                # Get list of files
                template = self.templates['superevent-file-list-template']
        else:
            template = self.templates['files-template']
            if not filename:
                filename = ""
            uri_kwargs = {'graceid': object_id, 'filename': filename}
        uri = template.format(**uri_kwargs)

        # Make request:
        if filename:
            return self.get_file(uri)
        else:
            return self.get(uri)

    @event_or_superevent
    def logs(self, object_id, log_number=None, *args, **kwargs):
        """Get log entries associated with an event or superevent.

        If ``log_number`` is specified, only a single log message is returned.
        Otherwise, all log messages attached to the event or superevent in
        question are returned.

        Args:
            object_id (str): event graceid or superevent ID.
            log_number (:obj:`int`, optional): ID number (N) of the log
                entry to retrieve.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Examples:

            Get all log messages:

            >>> g = GraceDb()
            >>> response_dict = g.logs('T101383').json()
            >>> print "Num logs = %d" % response_dict['numRows']
            >>> log_list = response_dict['log']
            >>> for log in log_list:
            ...     print log['comment']

        Get a single log message:

            >>> g = GraceDb()
            >>> log_info = g.logs('T101383', 10).json()
        """
        if log_number is not None and not isinstance(log_number, int):
            raise TypeError('log_number should be an int')

        # Set up template and object id
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            uri_kwargs = {'superevent_id': object_id}
            if log_number:
                template = self.templates['superevent-log-detail-template']
            else:
                template = self.templates['superevent-log-list-template']
        else:
            uri_kwargs = {'graceid': object_id}
            if log_number:
                template = self.templates['event-log-detail-template']
            else:
                template = self.templates['event-log-template']

        if log_number is not None:
            uri_kwargs['N'] = log_number

        uri = template.format(**uri_kwargs)
        return self.get(uri)

    @event_or_superevent
    def writeLog(self, object_id, message, filename=None, filecontents=None,
                 tag_name=[], displayName=[], *args, **kwargs):
        """Create a new log entry associated with an event or superevent.

        Args:
            object_id (str): event graceid or superevent ID.
            message (str): comment to post.
            filename (:obj:`str`, optional): path to file to be uploaded.
                Use ``'-'`` to read from stdin.
            filecontents (:obj:`file`, optional): handler pointing to a file to
                be read and uploaded. If this argument is specified, the
                contents will be saved as ``filename`` on the server.
            tag_name (:obj:`str` or :obj:`list[str]`, optional): tag name or
                list of tag names to be applied to the log message.
            displayName (:obj:`str` or :obj:`list[str]`, optional): tag display
                string or list of display strings for the tag(s) in
                ``tag_name``. If provided, there should be one for each tag.
                Not applicable for tags which already exist on the server.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.writeLog('T101383', 'Good stuff.', '/path/to/plot.png',
            ... tag_name='analyst_comments')
            >>> print r.status_code
            201
        """

        # Handle old usage of 'tagname' instead of 'tag_name'
        tagname = kwargs.pop('tagname', None)
        if tagname is not None and not tag_name:
            tag_name = tagname

        # Handle cases where tag_name is a string
        if isinstance(tag_name, str):
            tag_name = [tag_name]
        elif isinstance(tag_name, (tuple, set)):
            tag_name = list(tag_name)
        elif tag_name is None:
            tag_name = []

        # Handle cases where displayName is a string
        if isinstance(displayName, str):
            displayName = [displayName]
        elif isinstance(displayName, (tuple, set)):
            displayName = list(displayName)
        elif displayName is None:
            displayName = []

        # Check displayName length - should be 0 or same as tag_name
        if (displayName and isinstance(tag_name, list)
            and len(displayName) != len(tag_name)):
            raise ValueError("For a list of tags, either provide no display "
                             "names or a display name for each tag")

        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates['superevent-log-list-template']
            uri_kwargs = {'superevent_id': object_id}
        else:
            template = self.templates['event-log-template']
            uri_kwargs = {'graceid': object_id}
        uri = template.format(**uri_kwargs)
        files = None
        if filename:
            if filecontents is None:
                if filename == '-':
                    filename = 'stdin'
                    filecontents = sys.stdin.read()
                else:
                    filecontents = open(filename, 'rb')
            files = {'upload': (os.path.basename(filename),
                                filecontents,
                                get_mimetype(filename))}

        # Set up body of request
        body = {
            'comment': message,
            'tagname': tag_name,
            'displayName': displayName,
        }

        # If files are attached, we have to encode the request body
        # differently, so we convert from a dict to a list of tuples.
        if files:
            body = dict_to_form_encoded(body)

        return self.post(uri, data=body, files=files)

    @event_or_superevent
    def emobservations(self, object_id, emobservation_num=None, *args,
                       **kwargs):
        """Get EM observation data associated with an event or superevent.

        If ``emobservation_num`` is provided, get a single EM observation data
        entry. Otherwise, retrieve all EM observation data associated with the
        event or superevent in question.

        Args:
            object_id (str): event graceid or superevent ID.
            emobservation_num (:obj:`int`, optional): ID number (N) of the EM
                observation to retrieve.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Examples:

            Get a list of EM observations:

            >>> g = GraceDb()
            >>> r = g.emobservations('T101383')
            >>> full_dictionary = r.json()
            >>> emo_list = full_dictionary['observations']

            Get a single EM observation:

            >>> g = GraceDb()
            >>> r = g.emobservations('T101383', 2)
            >>> observation_dict = r.json()
        """
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            uri_kwargs = {'superevent_id': object_id}
            if emobservation_num:
                template = \
                    self.templates['superevent-emobservation-detail-template']
            else:
                template = \
                    self.templates['superevent-emobservation-list-template']
        else:
            uri_kwargs = {'graceid': object_id}
            if emobservation_num:
                template = self.templates['emobservation-detail-template']
            else:
                template = self.templates['emobservation-list-template']

        if emobservation_num is not None:
            uri_kwargs['N'] = emobservation_num

        uri = template.format(**uri_kwargs)
        return self.get(uri)

    @event_or_superevent
    def writeEMObservation(self, object_id, group, raList, raWidthList,
                           decList, decWidthList, startTimeList, durationList,
                           comment="", *args, **kwargs):
        """Create an EM observation data entry for an event or superevent.

        Args:
            object_id (str): event graceid or superevent ID.
            group (str): name of EM MOU group making the observation.
            raList (:obj:`list[float]`): list of right ascension coordinates
                (degrees).
            raWidthList (:obj:`list[float]` or :obj:`float`): list of right
                ascension measurement widths OR a single number if all
                measurements have the same width (degrees).
            decList (:obj:`list[float]`): list of declination coordinates
                (degrees).
            decWidthList (:obj:`list[float]` or :obj:`float`): list of
                declination measurement widths OR a single number if all
                measurements have the same width (degrees).
            startTimeList (:obj:`list[str]`): list of measurement start times
                in ISO 8601 format and UTC time zone.
            durationList (:obj:`list[float]` or :obj:`float`): list of exposure
                times OR a single number if all measurements have the same
                exposure (seconds).
            comment (:obj:`str`, optional): comment on observation.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.writeEMObservation('S190131g', 'ZTF', [1, 2, 3],
            ... [0.1, 0.1, 0.1], [4, 5, 6], 0.2, [],
            ... [10, 9, 11], comment="data uploaded")
            >>> r.status
            201
        """
        # Validate EM group
        if group not in self.em_groups:
            err_msg = "group must be one of {groups}".format(
                groups=", ".join(self.em_groups))
            raise ValueError(err_msg)

        # Argument checking
        num_measurements = len(raList)
        # convert any single number widths or durations into lists
        raWidthList, decWidthList, durationList = \
            [[l] * num_measurements if not isinstance(l, (list, tuple)) else l
                for l in [raWidthList, decWidthList, durationList]]

        # Compare all list lengths
        all_lists = [raList, decList, startTimeList, raWidthList,
                     decWidthList, durationList]
        if not all(map(lambda l: len(l) == num_measurements, all_lists)):
            raise ValueError('raList, decList, startTimeList, raWidthList, '
                             'decWidthList, and durationList should be the '
                             'same length')

        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates['superevent-emobservation-list-template']
            uri_kwargs = {'superevent_id': object_id}
        else:
            template = self.templates['emobservation-list-template']
            uri_kwargs = {'graceid': object_id}
        uri = template.format(**uri_kwargs)

        body = {
            'group': group,
            'ra_list': raList,
            'ra_width_list': raWidthList,
            'dec_list': decList,
            'dec_width_list': decWidthList,
            'start_time_list': startTimeList,
            'duration_list': durationList,
            'comment': comment,
        }
        return self.post(uri, json=body)

    @event_or_superevent
    def labels(self, object_id, label="", *args, **kwargs):
        """Get a label or labels attached to an event or superevent.

        Args:
            object_id (str): event graceid or superevent ID.
            label (:obj:`str`, optional): name of label.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Examples:

            Get a list of labels:

            >>> g = GraceDb()
            >>> label_list = g.labels('T101383').json()['labels']
            >>> for label in label_list:
            ...     print label['name']

            Get a single label:

            >>> g = GraceDb()
            >>> dqv_label = g.labels('T101383', 'DQV').json()
        """
        # Check label name
        if label and label not in self.allowed_labels:
            raise NameError(("Label '{0}' does not exist in the "
                            "database").format(label))

        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            uri_kwargs = {'superevent_id': object_id}
            if label:
                template = self.templates['superevent-label-detail-template']
                uri_kwargs['label_name'] = label
            else:
                template = self.templates['superevent-label-list-template']
        else:
            template = self.templates['event-label-template']
            uri_kwargs = {'graceid': object_id}
            uri_kwargs['label'] = label

        uri = template.format(**uri_kwargs)
        return self.get(uri)

    @event_or_superevent
    def writeLabel(self, object_id, label, *args, **kwargs):
        """Add a label to an event or superevent.

        Args:
            object_id (str): event graceid or superevent ID.
            label (str): label name. Use
                :py:attr:`ligo.gracedb.rest.GraceDb.allowed_labels` to get
                a list of available labels on the server.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.writeLabel('T101383', 'DQV')
            >>> r.status_code
            201
        """
        # Check label name
        if label not in self.allowed_labels:
            raise NameError(("Label '{0}' does not exist in the "
                            "database").format(label))

        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates['superevent-label-list-template']
            uri_kwargs = {'superevent_id': object_id}
            request_body = {'name': label}
            uri = template.format(**uri_kwargs)
            return self.post(uri, data=request_body)
        else:
            template = self.templates['event-label-template']
            uri_kwargs = {'graceid': object_id}
            uri_kwargs['label'] = label
            request_body = {}
            uri = template.format(**uri_kwargs)
            return self.put(uri, data=request_body)

    @event_or_superevent
    def removeLabel(self, object_id, label, *args, **kwargs):
        """Remove a label from an event or superevent.

        Args:
            object_id (str): event graceid or superevent ID.
            label (str): label name. The label must be presently applied
                to the event or superevent.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.removeLabel('T101383', 'DQV')
            >>> r.status_code
            204
        """
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates['superevent-label-detail-template']
            uri_kwargs = {'superevent_id': object_id}
            uri_kwargs['label_name'] = label
        else:
            template = self.templates['event-label-template']
            uri_kwargs = {'graceid': object_id}
            uri_kwargs['label'] = label
        uri = template.format(**uri_kwargs)
        return self.delete(uri)

    @event_or_superevent
    def tags(self, object_id, N, *args, **kwargs):
        """Get tags attached to an event or superevent log entry.

        Args:
            object_id (str): event graceid or superevent ID.
            N (int): ID number (N) of the log entry for which to get tags.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> tag_list = g.tags('T101383', 56).json()['tags']
            >>> print "Number of tags for message 56: %d" % len(tag_list)
        """
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            uri_kwargs = {'superevent_id': object_id}
            template = self.templates['superevent-log-tag-list-template']
        else:
            uri_kwargs = {'graceid': object_id}
            template = self.templates['taglist-template']
        uri_kwargs['N'] = N
        uri = template.format(**uri_kwargs)
        return self.get(uri)

    @event_or_superevent
    def addTag(self, object_id, N, tag_name, displayName=None, *args,
               **kwargs):
        """Add a tag to an event or superevent log entry.

        Args:
            object_id (str): event graceid or superevent ID.
            N (int): ID number of log entry.
            tag_name (str): name of tag to add; tags which don't already exist
                on the server will be created.
            displayName (:obj:`str`, optional): tag display name; only used
                to create new tags which don't already exist.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.createTag('T101383', 56, 'sky_loc')
            >>> r.status
            201
        """
        is_superevent = kwargs.pop('is_superevent', False)
        request_body = {}

        # Add displayName to requestBody, if applicable.
        if displayName is not None:
            request_body['displayName'] = displayName

        if is_superevent:
            template = self.templates['superevent-log-tag-list-template']
            uri_kwargs = {'superevent_id': object_id}
            uri_kwargs['N'] = N
            request_body['name'] = tag_name
            uri = template.format(**uri_kwargs)
            return self.post(uri, data=request_body)
        else:
            template = self.templates['tag-template']
            uri_kwargs = {'graceid': object_id, 'tag_name': tag_name}
            uri_kwargs['N'] = N
            uri = template.format(**uri_kwargs)
            return self.put(uri, data=request_body)

    @event_or_superevent
    def removeTag(self, object_id, N, tag_name, *args, **kwargs):
        """Remove a tag from an event or superevent log entry.

        Args:
            object_id (str): event graceid or superevent ID.
            N (int): ID number of log entry.
            tag_name (str): name of tag to add; tags which don't already exist
                on the server will be created.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.deleteTag('T101383', 56, 'sky_loc')
            >>> r.status
            200
        """
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates['superevent-log-tag-detail-template']
            uri_kwargs = {'superevent_id': object_id}
        else:
            template = self.templates['tag-template']
            uri_kwargs = {'graceid': object_id}
        uri_kwargs['N'] = N
        uri_kwargs['tag_name'] = tag_name
        uri = template.format(**uri_kwargs)
        return self.delete(uri)

    def ping(self):
        """Ping the server.

        Returns:
            :class:`requests.models.Response`

            ``response.json()`` contains the information from the API root.

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.
        """
        return self.get(self.links['self'])

    @event_or_superevent
    def voevents(self, object_id, voevent_num=None, *args, **kwargs):
        """Get a VOEvent or list of VOEvents for an event or superevent.

        To get the XML file associated with a VOEvent, use the ``filename``
        in the response JSON with :py:meth:`ligo.gracedb.rest.GraceDb.files`.

        Args:
            object_id (str): event graceid or superevent ID.
            voevent_num (:obj:`int`, optional): ID number (N) of the VOEvent
                to retrieve.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Examples:
            Get a list of VOEvents:

            >>> g = GraceDb()
            >>> r = g.voevents('T101383')
            >>> voevent_list = r.json()['voevents']

            Get a single VOEvent:

            >>> g = GraceDb()
            >>> r = g.voevents('T101383', 2)
            >>> voevent = r.json()
        """
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            uri_kwargs = {'superevent_id': object_id}
            if voevent_num:
                template = self.templates['superevent-voevent-detail-template']
            else:
                template = self.templates['superevent-voevent-list-template']
        else:
            uri_kwargs = {'graceid': object_id}
            if voevent_num:
                template = self.templates['voevent-detail-template']
            else:
                template = self.templates['voevent-list-template']

        if voevent_num is not None:
            uri_kwargs['N'] = voevent_num

        uri = template.format(**uri_kwargs)
        return self.get(uri)

    @event_or_superevent
    def createVOEvent(self, object_id, voevent_type, skymap_type=None,
                      skymap_filename=None, combined_skymap_filename=None,
                      internal=True, open_alert=False, raven_coinc=False,
                      hardware_inj=False, CoincComment=False, ProbHasNS=None,
                      ProbHasRemnant=None, BNS=None, NSBH=None, BBH=None,
                      Terrestrial=None, MassGap=None, *args, **kwargs):
        r"""Create a new VOEvent.

        Args:
            object_id (str): event graceid or superevent ID.
            voevent_type (str): VOEvent type (choose from ``'preliminary'``,
                ``'initial'``, ``'update'``, and ``'retraction'``).
            skymap_type (:obj:`str`, optional): skymap type. Required for
                VOEvents which include a skymap.
            skymap_filename (:obj:`str`, optional): name of skymap file on
                the GraceDB server (required for 'initial' and 'update' alerts,
                optional for 'preliminary' alerts).
            combined_skymap_file (:obj:`str`, optional): name of combined
                skymap file, if present
            internal (:obj:`bool`, optional): whether the VOEvent should be
                distributed to LIGO-Virgo members only.
            hardware_inj (:obj:`bool`, optional): whether the candidate is a
                hardware injection.
            open_alert (:obj:`bool`, optional): whether the candidate is an
                open alert or not.
            raven_coinc (:obj:`bool`, optional): is VOEvent result of
                coincidence from RAVEN pipeline. Tells GraceDB to look for
                `coinc_far` and `em_type` data models.
            CoincComment (:obj:`bool`, optional): whether the candidate has a
                possible counterpart GRB.
            ProbHasNS (:obj:`float`, optional): probability that at least one
                object in the binary is less than 3 M\ :sub:`sun` (CBC events
                only).
            ProbHasRemnant (:obj:`float`): probability that there is matter in
                the surroundings of the central object (CBC events only).
            BNS (:obj:`float`, optional): probability that the source is a
                binary neutron star merger (CBC events only).
            NSBH (:obj:`float`, optional): probability that the source is a
                neutron star-black hole merger (CBC events only).
            BBH (:obj:`float`, optional): probability that the source is a
                binary black hole merger (CBC events only).
            Terrestrial (:obj:`float`, optional): probability that the source
                is terrestrial (i.e., a background noise fluctuation or a
                glitch) (CBC events only).
            MassGap (:obj:`float`, optional): probability that at least one
                object in the binary has a mass between 3 and 5 M\ :sub:`sun`
                (CBC events only).

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.createVOEvent('T101383', 'initial', skymap_type='custom',
            ... skymap_filename='skymap.fits.gz', internal=True, ProbHasNS=0.7,
            ... MassGap=0.4, Terrestrial=0.05)
            >>> r.status
            201
        """  # noqa: W605
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates['superevent-voevent-list-template']
            uri_kwargs = {'superevent_id': object_id}
        else:
            template = self.templates['voevent-list-template']
            uri_kwargs = {'graceid': object_id}
        uri = template.format(**uri_kwargs)

        # validate voevent_type, convert to short form if necessary
        voevent_type = self._getCode(voevent_type.lower(), self.voevent_types)
        if not voevent_type:
            raise ValueError("voevent_type must be one of: {0}".format(
                ", ".join(list(six.itervalues(self.voevent_types)))))

        # Require skymaps for 'update' and 'initial'
        if voevent_type == 'IN':
            if not skymap_filename:
                raise ValueError("Skymap file is required for 'initial' "
                                 "VOEvents")

        # Construct request body
        body = {
            'voevent_type': voevent_type,
            'internal': internal,
            'open_alert': open_alert,
            'hardware_inj': hardware_inj,
            'CoincComment': CoincComment,
            'raven_coinc': raven_coinc,
        }
        # Add optional args
        if skymap_type is not None:
            body['skymap_type'] = skymap_type
        if skymap_filename is not None:
            body['skymap_filename'] = skymap_filename
        if combined_skymap_filename is not None:
            body['combined_skymap_filename'] = combined_skymap_filename
        if ProbHasNS is not None:
            body['ProbHasNS'] = ProbHasNS
        if ProbHasRemnant is not None:
            body['ProbHasRemnant'] = ProbHasRemnant
        if BNS is not None:
            body['BNS'] = BNS
        if NSBH is not None:
            body['NSBH'] = NSBH
        if BBH is not None:
            body['BBH'] = BBH
        if Terrestrial is not None:
            body['Terrestrial'] = Terrestrial
        if MassGap is not None:
            body['MassGap'] = MassGap

        return self.post(uri, data=body)

    @event_or_superevent
    def permissions(self, object_id, *args, **kwargs):
        """Get a list of permissions for a superevent.

        Only LIGO-Virgo members are allowed to access this information.
        This is not currently implemented for events.

        Args:
            object_id (str): superevent ID.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> g.permissions('S190304bc').json()['permissions']
            [
                {'group': 'group1', 'permission': 'view_superevent'},
                {'group': 'group1', 'permission': 'annotate_superevent'},
                {'group': 'group2', 'permission': 'view_superevent'},
            ]
        """
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates[
                'superevent-permission-list-template']
            uri_kwargs = {'superevent_id': object_id}
        else:
            raise NotImplementedError('Not implemented for events')

        uri = template.format(**uri_kwargs)
        return self.get(uri)

    @event_or_superevent
    def modify_permissions(self, object_id, action, *args, **kwargs):
        """Expose or hide a superevent to/from the public.

        This action requires special server-side permissions. It is not
        yet implemented for events.

        Args:
            object_id (str): superevent ID.
            action (str): ``'expose'`` or ``'hide'``.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:

            Expose a superevent:

            >>> g = GraceDb()
            >>> g.modify_permissions('S190304bc', 'expose').json()
            [
                {'group': 'group1', 'permission': 'view_superevent'},
                {'group': 'group1', 'permission': 'annotate_superevent'},
                {'group': 'group2', 'permission': 'view_superevent'},
            ]

            Hide a superevent:

            >>> g.modify_permissions('S190304bc', 'hide').json()
            []
        """

        if (action not in ['expose', 'hide']):
            raise ValueError('action should be \'expose\' or \'hide\'')

        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates[
                'superevent-permission-modify-template']
            uri_kwargs = {'superevent_id': object_id}
        else:
            raise NotImplementedError('Not implemented for events')

        uri = template.format(**uri_kwargs)

        body = {'action': action}
        return self.post(uri, data=body)

    def _signoff_helper(self, object_id, action, template, uri_kwargs,
                        signoff_type=None, instrument=None, status=None,
                        comment=None):
        # NOTE: uri_kwargs should already have the graceid or superevent_id
        # in it

        # Validate args
        if signoff_type:
            signoff_type = self._getCode(signoff_type, self.signoff_types)
            if not signoff_type:
                raise ValueError("signoff_type must be one of: {0}".format(
                    ", ".join(self.signoff_types)))
        if instrument:
            instrument = self._getCode(instrument, self.instruments)
            if not instrument:
                raise ValueError("instrument must be one of: {0}".format(
                    ", ".join(self.instruments)))
        if status:
            status = self._getCode(status, self.signoff_statuses)
            if not status:
                raise ValueError("status must be one of: {0}".format(
                    ", ".join(self.signoff_statuses)))
        if signoff_type == 'OP' and not instrument:
            raise ValueError('Operator signoffs require an instrument')

        # Get HTTP method and args
        body = {}
        if (action == 'create'):
            http_method = "POST"
            body['signoff_type'] = signoff_type
            body['instrument'] = instrument
            body['comment'] = comment
            body['status'] = status
        elif (action == 'update'):
            http_method = "PATCH"
            uri_kwargs['typeinst'] = signoff_type + instrument
            if comment is not None:
                body['comment'] = comment
            if status is not None:
                body['status'] = status
        elif (action == 'get'):
            http_method = "GET"
            if signoff_type is not None:
                uri_kwargs['typeinst'] = signoff_type + instrument
        elif (action == 'delete'):
            http_method = "DELETE"
            uri_kwargs['typeinst'] = signoff_type + instrument
        else:
            raise ValueError("action should be 'create', 'update', "
                             "'get', or 'delete'")
        uri = template.format(**uri_kwargs)

        # Get http method
        method = getattr(self, http_method.lower())
        if body:
            response = method(uri, data=body)
        else:
            response = method(uri)

        return response

    @event_or_superevent
    def signoffs(self, object_id, signoff_type=None, instrument='', *args,
                 **kwargs):
        """Get a signoff or list of signoffs for a superevent.

        This action is not yet implemented for events.

        Args:
            object_id (str): superevent ID.
            signoff_type (str): signoff type. Choices are: ``'OP'`` or
                ``'operator'`` (operator signoff), or ``'ADV'`` or
                ``'advocate'`` (advocate signoff).
            instrument (:obj:`str`, optional): instrument abbreviation
                (``'H1'``, ``'L1'``, etc.) for operator signoffs. Leave blank
                for advocate signoffs.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:

            Get a list of signoffs:

            >>> g = GraceDb()
            >>> signoffs = g.signoffs('S190221z').json()['signoffs']

            Get a single signoff:

            >>> signoff = g.signoffs('S190221z', 'H1').json()
        """
        # Get URI template
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            if signoff_type is not None:
                template = self.templates['superevent-signoff-detail-template']
            else:
                template = self.templates['superevent-signoff-list-template']
            uri_kwargs = {'superevent_id': object_id}
        else:
            raise NotImplementedError('Not yet implemented for events')

        return self._signoff_helper(
            object_id, 'get', template, uri_kwargs,
            signoff_type=signoff_type, instrument=instrument
        )

    @event_or_superevent
    def create_signoff(self, object_id, signoff_type, status, comment,
                       instrument='', *args, **kwargs):
        """Create a superevent signoff.

        This action requires special server-side permissions. You must be in
        the control room of an IFO to perform operator signoffs or in the
        'em_advocates' group to perform advocate signoffs. This action is not
        yet implemented for events.

        Args:
            object_id (str): superevent ID.
            signoff_type (str): signoff type. Choices are: ``'OP'`` or
                ``'operator'`` (operator signoff), or ``'ADV'`` or
                ``'advocate'`` (advocate signoff).
            status (str): signoff status (``'OK'`` or ``'NO'``).
            comment (str): comment on the signoff.
            instrument (:obj:`str`, optional): instrument abbreviation
                (``'H1'``, ``'L1'``, etc.) for operator signoffs. Leave blank
                for advocate signoffs.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.create_signoff('S190102p', 'OP', 'OK',
            ... 'LHO looks good.', instrument='H1')
            >>> r.status_code
            201
        """

        # Get URI template
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates['superevent-signoff-list-template']
            uri_kwargs = {'superevent_id': object_id}
        else:
            raise NotImplementedError('Not yet implemented for events')

        return self._signoff_helper(
            object_id, 'create', template, uri_kwargs,
            signoff_type=signoff_type, instrument=instrument, status=status,
            comment=comment
        )

    @event_or_superevent
    def update_signoff(self, object_id, signoff_type, status=None,
                       comment=None, instrument='', *args, **kwargs):
        """Update a superevent signoff.

        This action requires the same permissions as
        :py:meth:`ligo.gracedb.rest.GraceDb.create_signoff`.

        Args:
            object_id (str): superevent ID.
            signoff_type (str): signoff type. Choices are: ``'OP'`` or
                ``'operator'`` (operator signoff), or ``'ADV'`` or
                ``'advocate'`` (advocate signoff).
            status (:obj:`str`, optional): signoff status (if changed).
            comment (:obj:`str`, optional): comment on the signoff
                (if changed).
            instrument (:obj:`str`, optional): instrument abbreviation
                (``'H1'``, ``'L1'``, etc.) for operator signoffs. Leave blank
                for advocate signoffs.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.update_signoff('S190102p', 'OP', status='NO',
            ... comment='IFO status was actually bad.', instrument='H1')
            >>> r.status_code
            200
        """
        # This will make a PATCH request

        # Either status or comment must be included - otherwise the user
        # is not updating anything
        if not (status or comment):
            raise ValueError("Provide at least one of 'status' or 'comment'")

        # Get URI template
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates['superevent-signoff-detail-template']
            uri_kwargs = {'superevent_id': object_id}
        else:
            raise NotImplementedError('Not yet implemented for events')

        return self._signoff_helper(
            object_id, 'update', template, uri_kwargs,
            signoff_type=signoff_type, instrument=instrument, status=status,
            comment=comment
        )

    @event_or_superevent
    def delete_signoff(self, object_id, signoff_type, instrument='', *args,
                       **kwargs):
        """Delete a superevent signoff.

        This action requires the same permissions as ``create_signoff()``.

        Args:
            object_id (str): superevent ID.
            signoff_type (str): signoff type. Choices are: ``'OP'`` or
                ``'operator'`` (operator signoff), or ``'ADV'`` or
                ``'advocate'`` (advocate signoff).
            instrument (:obj:`str`, optional): instrument abbreviation
                (``'H1'``, ``'L1'``, etc.) for operator signoffs. Leave blank
                for advocate signoffs.

        Returns:
            :class:`requests.models.Response`

        Raises:
            ligo.gracedb.exceptions.HTTPError: if the response has a status
                code >= 400.

        Example:
            >>> g = GraceDb()
            >>> r = g.delete_signoff('S190102p', 'OP', instrument='H1')
            >>> r.status_code
            204
        """
        # Get URI template
        is_superevent = kwargs.pop('is_superevent', False)
        if is_superevent:
            template = self.templates['superevent-signoff-detail-template']
            uri_kwargs = {'superevent_id': object_id}
        else:
            raise NotImplementedError('Not yet implemented for events')

        return self._signoff_helper(
            object_id, 'delete', template, uri_kwargs,
            signoff_type=signoff_type, instrument=instrument
        )
