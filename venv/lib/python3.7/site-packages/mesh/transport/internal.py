from mesh.bundle import Specification
from mesh.constants import *
from mesh.exceptions import *
from mesh.transport.base import *
from scheme.formats import *

__all__ = ('InternalClient', 'InternalServer', 'ServerRequest', 'ServerResponse')

class InternalServer(Server):
    """An API server."""

    def __init__(self, bundles, default_format=None, available_formats=None):
        super(InternalServer, self).__init__(bundles, default_format, available_formats)

        self.endpoints = {}
        for name, bundle in self.bundles.iteritems():
            for version, resources in bundle.versions.iteritems():
                for resource, controller in resources.itervalues():
                    for request in resource.requests.itervalues():
                        signature = (name, version, resource.name, request.name)
                        if signature not in self.endpoints:
                            self.endpoints[signature] = (resource, controller, request)
                        else:
                            raise Exception()

    def dispatch(self, endpoint, environ, subject, data, format=None):
        request = ServerRequest(endpoint, environ, subject, data)
        response = ServerResponse()

        endpoint = self.endpoints.get(endpoint)
        if endpoint:
            resource, controller, definition = endpoint
        else:
            return response(NOT_FOUND)

        if format:
            try:
                format = self.formats[format]
                request.data = format.unserialize(data)
            except Exception:
                return response(BAD_REQUEST)
            else:
                request.serialized = True

        try:
            definition.process(controller, request, response)
        except Exception, exception:
            import traceback;traceback.print_exc()
            return response(SERVER_ERROR)

        if format:
            response.mimetype = format.mimetype
            if response.content:
                response.content = format.serialize(response.content)
        return response

class InternalClient(Client):
    """An internal API client."""

    def __init__(self, server, specification, environ=None, format=None, formats=None, secondary=False):
        super(InternalClient, self).__init__(specification, environ, format, formats, secondary)
        self.server = server

    def execute(self, resource, request, subject, data, format=None):
        format = format or self.format
        if not format:
            return self._dispatch_request(resource, request, subject, data)

    def _dispatch_request(self, resource, request, subject, data):
        endpoint = (self.specification.name, self.specification.version, resource, request)
        response = self.server.dispatch(endpoint, self.environ, subject, data)

        if response.ok:
            return response
        else:
            raise RequestError.construct(response.status, response.content)

class InternalTransport(Transport):
    name = 'internal'
    server = InternalServer
    client = InternalClient

    @classmethod
    def construct_fixture(cls, bundle, specification, environ=None):
        server = InternalServer([bundle])
        client = InternalClient(server, specification, environ, secondary=True)
        return server, client
