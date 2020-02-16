from mesh.bundle import Specification
from mesh.constants import *
from mesh.exceptions import *
from mesh.util import subclass_registry
from scheme.fields import Field
from scheme.formats import *

__all__ = ('STANDARD_FORMATS', 'Client', 'Server', 'ServerRequest', 'ServerResponse', 'Transport')

STANDARD_FORMATS = (Json, UrlEncoded)

class ServerRequest(object):
    """An API request."""

    def __init__(self, endpoint=None, environ=None, subject=None, data=None, serialized=False):
        self.data = data
        self.endpoint = endpoint
        self.environ = environ
        self.serialized = serialized
        self.subject = subject

    def __repr__(self):
        return '%s(endpoint=%r)' % (type(self).__name__, self.endpoint)

class ServerResponse(object):
    """An API response."""

    def __init__(self, status=None, content=None, mimetype=None):
        self.content = content
        self.mimetype = mimetype
        self.status = status

    def __call__(self, status=None, content=None):
        return self.construct(status, content)

    def __repr__(self):
        return '%s(status=%r)' % (type(self).__name__, self.status)

    @property
    def ok(self):
        return (self.status in VALID_STATUS_CODES)

    def construct(self, status=None, content=None):
        if status in STATUS_CODES:
            self.status = status
        else:
            content = status

        if content is not None:
            self.content = content
        return self

class Server(object):
    """An API server."""

    def __init__(self, bundles, default_format=None, available_formats=None):
        self.bundles = {}
        for bundle in bundles:
            if bundle.name not in self.bundles:
                self.bundles[bundle.name] = bundle
            else:
                raise Exception()

        self.formats = {}
        for format in (available_formats or STANDARD_FORMATS):
            self.formats[format.name] = self.formats[format.mimetype] = format

        self.default_format = default_format

    def dispatch(self):
        raise NotImplementedError()

class Client(object):
    """An API client."""

    clients = {}

    def __init__(self, specification, environ=None, format=None, formats=None, secondary=False):
        self.environ = environ or {}
        self.format = format
        self.specification = specification

        self.formats = {}
        for format in (formats or STANDARD_FORMATS):
            for key in (format, format.name, format.mimetype):
                self.formats[key] = format

        id = specification.id
        if not secondary and id not in self.clients:
            self.clients[id] = self
        
    def execute(self, resource, request, subject, data, format=None):
        raise NotImplementedError()

    @classmethod
    def get(cls, specification):
        if isinstance(specification, Specification):
            id = specification.id
        else:
            id = specification
        return cls.clients.get(id)

    @classmethod
    def register(cls, client):
        cls.clients[client.specification.id] = client

class Transport(object):
    """A mesh transport."""

    __metaclass__ = subclass_registry('transports', 'name')
    transports = {}

    request = ServerRequest
    response = ServerResponse
    server = Server
    client = Client

    @classmethod
    def construct_fixture(cls, bundle, specification, environ=None):
        raise NotImplementedError()
