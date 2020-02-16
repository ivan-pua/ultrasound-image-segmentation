import BaseHTTPServer
import re
from httplib import HTTPConnection

from mesh.constants import *
from mesh.exceptions import *
from mesh.transport.base import *
from scheme.formats import *

__all__ = ('HttpClient', 'HttpRequest', 'HttpResponse', 'HttpServer', 'WsgiServer')

STATUS_CODES = {
    OK: 200,
    CREATED: 201,
    ACCEPTED: 202,
    PARTIAL: 206,
    BAD_REQUEST: 400,
    FORBIDDEN: 403,
    NOT_FOUND: 404,
    METHOD_NOT_ALLOWED: 405,
    INVALID: 406,
    TIMEOUT: 408,
    CONFLICT: 409,
    GONE: 410,
    SERVER_ERROR: 500,
    UNIMPLEMENTED: 501,
    UNAVAILABLE: 503,
}

STATUS_CODES.update(dict((code, status) for status, code in STATUS_CODES.items()))

STATUS_LINES = {
    OK: '200 OK',
    CREATED: '201 Created',
    ACCEPTED: '202 Accepted',
    PARTIAL: '206 Partial Content',
    BAD_REQUEST: '400 Bad Request',
    FORBIDDEN: '403 Forbidden',
    NOT_FOUND: '404 Not Found',
    METHOD_NOT_ALLOWED: '405 Method Not Allowed',
    INVALID: '406 Not Acceptable',
    TIMEOUT: '408 Request Timeout',
    CONFLICT: '409 Conflict',
    GONE: '410 Gone',
    SERVER_ERROR: '500 Internal Server Error',
    UNIMPLEMENTED: '501 Not Implemented',
    UNAVAILABLE: '503 Service Unavailable',
}

PATH_EXPR = r"""(?x)^%s
    /(?P<bundle>\w+)
    /(?P<major>\d+)[.](?P<minor>\d+)
    /(?P<resource>\w+)
    (?:/(?P<subject>\w+)(?P<tail>(?:/\w+)+)?)?
    (?:[.](?P<format>\w+))?
    /?$"""

class Connection(object):
    def __init__(self, host):
        self.connection = HTTPConnection(host)
        self.host = host

    def request(self, method, url, body=None, headers={}):
        self.connection.request(method, url, body, headers)
        response = self.connection.getresponse()

        content = response.read() or None
        mimetype = response.getheader('Content-Type', None)
        return HttpResponse(STATUS_CODES[response.status], content, mimetype)

class HttpRequest(ServerRequest):
    """An HTTP API request."""

    def __init__(self, method=None, path=None, mimetype=None, headers=None, serialized=True, **params):
        super(HttpRequest, self).__init__(serialized=serialized, **params)
        self.headers = headers
        self.method = method
        self.mimetype = mimetype
        self.path = path

class HttpResponse(ServerResponse):
    """An HTTP response."""

    @property
    def status_code(self):
        return STATUS_CODES[self.status]

    @property
    def status_line(self):
        return STATUS_LINES[self.status]

class Path(object):
    """An HTTP request path."""

    def __init__(self, server, path):
        self.path = path

        match = server.path_expr.match(path)
        if not match:
            raise ValueError(path)

        self.bundle = match.group('bundle')
        if self.bundle not in server.bundles:
            raise ValueError(path)

        self.resource = match.group('resource')
        resource_path = [self.resource]

        self.subject = match.group('subject')
        if self.subject:
            resource_path.append('id')

        self.tail = match.group('tail')
        if self.tail:
            resource_path.append(self.tail)

        self.format = match.group('format')
        if self.format is not None and self.format not in server.formats:
            raise ValueError(path)

        self.version = (int(match.group('major')), int(match.group('minor')))
        self.resource_path = '/'.join(resource_path)

class EndpointGroup(object):
    """An HTTP endpoint group."""

    def __init__(self, signature, method, resource, controller):
        self.controller = controller
        self.default_request = None
        self.filtered_requests = []
        self.method = method
        self.resource = resource
        self.signature = signature

    def attach(self, request):
        if request.filter is not None:
            self.filtered_requests.append(request)
        elif self.default_request is None:
            self.default_request = request
        else:
            raise SpecificationError()

    def dispatch(self, request, response):
        definition = self.default_request
        for filtered_request in self.filtered_requests:
            if filtered_request.claim(request.data):
                definition = filtered_request
                break

        if not definition:
            return response(BAD_REQUEST)
        definition.process(self.controller, request, response)

class HttpServer(Server):
    """The HTTP API server."""

    def __init__(self, bundles, path_prefix=None, default_format=Json, available_formats=None):
        super(HttpServer, self).__init__(bundles, default_format, available_formats)
        prfx = path_prefix and ('/' + path_prefix.strip('/')) or ''
        self.path_expr = re.compile(PATH_EXPR % prfx)

        self.groups = dict()
        for name, bundle in self.bundles.iteritems():
            for version, resources in bundle.versions.iteritems():
                for resource, controller in resources.itervalues():
                    for request in resource.requests.itervalues():
                        if request.endpoint:
                            self._construct_endpoint(name, version, resource, controller, request)

    def dispatch(self, method, path, mimetype, headers, data):
        request = HttpRequest(method=method, mimetype=mimetype, headers=headers)
        response = HttpResponse()

        try:
            request.path = path = Path(self, path)
        except Exception:
            return response(NOT_FOUND)

        signature = (path.bundle, path.version, path.resource_path)
        if signature in self.groups:
            groups = self.groups[signature]
            if method in groups:
                group = groups[method]
            else:
                return response(METHOD_NOT_ALLOWED)
        else:
            return response(NOT_FOUND)

        request.subject = path.subject
        if data:
            try:
                request.data = self.formats[mimetype].unserialize(data)
            except Exception:
                import traceback;traceback.print_exc()
                return response(BAD_REQUEST)

        try:
            group.dispatch(request, response)
        except Exception:
            from traceback import print_exc;print_exc()
            return response(SERVER_ERROR)

        format = self.default_format
        if path.format:
            format = self.formats[path.format]
        elif mimetype and mimetype != URLENCODED:
            format = self.formats[mimetype]

        if response.content:
            response.mimetype = format.mimetype
            response.content = format.serialize(response.content)

        return response

    def _construct_endpoint(self, bundle, version, resource, controller, request):
        method, path = request.endpoint
        signature = (bundle, version, path)

        if signature in self.groups:
            groups = self.groups[signature]
        else:
            self.groups[signature] = groups = dict()

        try:
            group = groups[method]
        except KeyError:
            group = groups[method] = EndpointGroup(signature, method, resource, controller)
        group.attach(request)

class HttpClient(Client):
    """An HTTP API client."""

    def __init__(self, host, specification, environ=None, format=Json, formats=None,
            secondary=False, prefix=None):

        super(HttpClient, self).__init__(specification, environ, format, formats, secondary)
        self.connection = Connection(host)
        self.prefix = prefix and ('/' + prefix.strip('/')) or ''
        self.paths = {}
        self.initial_path = '%s/%s/%d.%d/' % (self.prefix, specification.name,
            specification.version[0], specification.version[1])

    def execute(self, resource, request, subject=None, data=None, format=None):
        format = format or self.format
        request = self.specification.resources[resource]['requests'][request]

        method, path = request['endpoint']
        mimetype = None

        if data is not None:
            data = request['schema'].process(data, OUTGOING, True)
            if method == GET:
                data = UrlEncoded.serialize(data)
                mimetype = UrlEncoded.mimetype
            else:
                data = format.serialize(data)
                mimetype = format.mimetype

        path = self._get_path(path)
        if subject:
            path = path % (subject, format.name)
        else:
            path = path % format.name

        headers = {}
        if mimetype:
            headers['Content-Type'] = mimetype

        response = self.connection.request(method, path, data, headers)
        if response.status in request['responses']:
            schema = request['responses'][response.status]['schema']
        else:
            exception = RequestError.construct(response.status)
            if exception:
                raise exception
            else:
                raise Exception('unknown status')

        if response.content:
            format = self.formats[response.mimetype]
            response.content = schema.process(format.unserialize(response.content), INCOMING, True)

        if response.ok:
            return response
        else:
            raise RequestError.construct(response.status, response.content)

    def _get_path(self, path):
        try:
            return self.paths[path]
        except KeyError:
            template = '%s%s.%%s' % (self.initial_path, re.sub(r'\/id(?=\/|$)', '/%s', path))
            self.paths[path] = template
            return template

class WsgiServer(HttpServer):
    def __call__(self, environ, start_response):
        try:
            return self._dispatch_wsgi_request(environ, start_response)
        except Exception, exception:
            start_response('500 Internal Server Error', {})
            return None

    def _dispatch_wsgi_request(self, environ, start_response):
        method = environ['REQUEST_METHOD']
        if method == GET:
            data = environ['QUERY_STRING']
        else:
            data = environ['wsgi.input'].read()

        mimetype = environ.get('CONTENT_TYPE', URLENCODED)
        if ';' in mimetype:
            mimetype, charset = mimetype.split(';', 1)

        path = environ['PATH_INFO']
        response = self.dispatch(method, path, mimetype, environ, data)

        headers = []
        if response.mimetype:
            headers.append(('Content-Type', response.mimetype))

        start_response(response.status_line, headers)
        return response.content

class TestingHttpServer(HttpServer):
    def run(self, address):
        this = self
        class handler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_GET(self):
                print self.headers
                headers = None
                mimetype = None
                response = this.dispatch(GET, self.path, mimetype, headers, self.rfile.read())

        server = BaseHTTPServer.HTTPServer(address, handler)
        server.serve_forever()

class HttpTransport(Transport):
    name = 'http'
    request = HttpRequest
    response = HttpResponse
    server = HttpServer
    client = HttpClient

    @classmethod
    def construct_fixture(cls, bundle, specification, environ=None):
        pass
