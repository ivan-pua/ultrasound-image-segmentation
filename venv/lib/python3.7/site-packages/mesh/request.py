import logging
import re
from copy import deepcopy
from textwrap import dedent
from types import ClassType

from mesh.constants import *
from mesh.exceptions import *
from mesh.util import LogHelper, pull_class_dict
from scheme.fields import INCOMING, OUTGOING, Field, Structure
from scheme.exceptions import *

__all__ = ('Context', 'Request', 'Response', 'validator')

log = LogHelper(logging.getLogger(__name__))

class Context(object):
    """A request context."""

    def __init__(self, request):
        self.request = request

class Response(object):
    """A response definition for a particular request."""

    def __init__(self, schema=None, status=None):
        if isinstance(schema, dict):
            schema = Structure(schema)
        if schema and not schema.name:
            schema.name = 'response'

        self.schema = schema
        self.status = status

    def __repr__(self):
        return 'Response(status=%r)' % self.status

    def describe(self):
        description = {'status': self.status, 'schema': None}
        if self.schema:
            description['schema'] = self.schema.describe(FIELD_PARAMETERS)
        return description

class Request(object):
    """A request definition for a resource.

    :param resource: The resource this request is declared on.
    :type resource: :class:`mesh.resource.Resource`

    :param string name: The name of this request; must be unique within the set of requests
        declared for a particular resource.

    :param tuple endpoint: Optional, default is ``None``; the HTTP endpoint for this request,
        specified as a two-tuple containing an HTTP method (``GET``, ``POST``, etc.) and a
        path segment.

    :param filter: Optional, default is ``None``; the filter specification for this request,
        used when it shares an HTTP endpoint with another request for a resource.

    :param schema: Optional, default is ``None``; the schema specifying the expected content.
    """

    ATTRS = ('batch', 'description', 'endpoint', 'filter', 'specific', 'title')

    def __init__(self, resource=None, name=None, endpoint=None, filter=None, schema=None,
        responses=None, specific=False, description=None, title=None, auto_constructed=False,
        batch=False, validators=None):

        self.auto_constructed = auto_constructed
        self.batch = batch
        self.description = description
        self.endpoint = endpoint
        self.filter = filter
        self.name = name
        self.resource = resource
        self.responses = responses or {}
        self.schema = schema
        self.specific = specific
        self.title = title
        self.validators = validators or []

        for status, response in self.responses.iteritems():
            if response.status is None:
                response.status = status

    def __repr__(self):
        return 'Request(resource=%r, name=%r)' % (self.resource, self.name)

    def __str__(self):
        return '%s:%s' % (self.resource, self.name)

    def claim(self, data):
        filter = self.filter
        if isinstance(filter, list) and isinstance(data, list):
            if filter and filter[0]:
                filter = filter[0]
                if data and data[0]:
                    data = data[0]
                else:
                    return False
            else:
                return True

        if isinstance(filter, dict) and isinstance(data, dict):
            if filter:
                for attr, value in filter.iteritems():
                    if data.get(attr) != value:
                        return False
                else:
                    return True
            else:
                return True
        else:
            return False

    @classmethod
    def construct(cls, resource, declaration):
        bases = declaration.__bases__
        if isinstance(declaration, (type, ClassType)) and bases:
            params = cls._pull_request(resource, bases[0])
        else:
            params = {}

        params.update(pull_class_dict(declaration, cls.ATTRS))
        if 'responses' not in params:
            params['responses'] = {}
        
        schema = getattr(declaration, 'schema', None)
        if schema is not None:
            if isinstance(schema, dict):
                schema = Structure(schema)
            if not schema.name:
                schema.name = 'request'
            params['schema'] = schema

        fields = getattr(declaration, 'fields', None)
        if fields:
            if isinstance(params['schema'], Structure):
                structure = params['schema'].structure
                for name, field in fields.iteritems():
                    if isinstance(field, Field):
                        if not field.name:
                            field.name = name
                        structure[name] = field
                    elif field is None and name in structure:
                        del structure[name]
            else:
                raise SpecificationError()

        responses = getattr(declaration, 'responses', {})
        for status, response in responses.iteritems():
            if not isinstance(response, Response):
                response = Response(response)
            response.status = status
            params['responses'][status] = response

        description = params.get('description')
        if not description and declaration.__doc__:
            params['description'] = dedent(declaration.__doc__)

        return cls(resource=resource, name=declaration.__name__, **params)

    @classmethod
    def _pull_request(cls, resource, request):
        try:
            get_request = request.get_request
        except AttributeError:
            pass
        else:
            request = get_request(resource)

        params = pull_class_dict(request, cls.ATTRS)

        schema = getattr(request, 'schema', None)
        if schema:
            params['schema'] = deepcopy(schema)

        responses = getattr(request, 'responses', None)
        if responses:
            params['responses'] = deepcopy(responses)
        return params

    def describe(self, path_prefix=None):
        description = {'endpoint': None, 'path': None}
        for attr in ('batch', 'description', 'filter', 'name', 'specific', 'title'):
            value = getattr(self, attr, None)
            if value is not None:
                description[attr] = value

        endpoint = self.endpoint
        if endpoint:
            description['endpoint'] = endpoint
            description['path'] = '%s%s' % (path_prefix or '/', endpoint[1])

        description['schema'] = None
        if self.schema:
            description['schema'] = self.schema.describe(FIELD_PARAMETERS)

        description['responses'] = {}
        for status, response in self.responses.iteritems():
            description['responses'][status] = response.describe()

        return description

    def process(self, controller, request, response):
        context = Context(request)

        subject = None
        if self.specific:
            subject = controller.acquire(request.subject)
            if not subject:
                log('info', 'request to %r specified unknown subject %r', str(self),
                    request.subject)
                return response(GONE)
        elif request.subject:
            log('info', 'request to %r improperly specified subject %r', str(self),
                request.subject)
            return response(BAD_REQUEST)

        data = None
        if self.schema:
            try:
                data = self.schema.process(request.data, INCOMING, request.serialized)
            except StructuralError, exception:
                error = exception.serialize()
                log('info', 'request to %s failed schema validation', str(self))
                response(INVALID, error)

            if self.validators:
                try:
                    self.validate(data)
                except StructuralError, exception:
                    error = exception.serialize()
                    log('info', 'request to %s failed resource validation', str(self))
                    response(INVALID, error)
        elif request.data:
            log('info', 'request to %r improperly specified data', str(self))
            return response(BAD_REQUEST)

        if not response.status:
            instance = controller()
            try:
                instance.dispatch(self, context, response, subject, data)
                if not response.status:
                    response.status = OK
            except StructuralError, exception:
                error = exception.serialize()
                log('info', 'request to %s failed controller invocation', str(self))
                response(INVALID, error)

        definition = self.responses[response.status]
        if definition.schema:
            try:
                response.content = definition.schema.process(response.content, OUTGOING, request.serialized)
            except StructuralError, exception:
                error = exception.serialize()
                log('error', 'response for %s failed schema validation', str(self))
                return response(SERVER_ERROR)
        elif response.content:
            log('error', 'response for %s improperly specified content', str(self))
            return response(SERVER_ERROR)

    def validate(self, data):
        if self.batch:
            errors = []
            for item in data:
                try:
                    self._validate_data(item)
                except StructuralError, exception:
                    errors.append(exception)
                else:
                    errors.append(None)
            if any(errors):
                raise ValidationError(structure=errors)
        else:
            self._validate_data(data)

    def _validate_data(self, data):
        error = ValidationError(structure={})
        for validator in self.validators:
            try:
                validator(data)
            except StructuralError, exception:
                attr = validator.attr
                if attr:
                    if attr in error.structure:
                        error.structure[attr].merge(exception)
                    else:
                        error.structure[attr] = exception
                else:
                    error.merge(exception)
        if error.substantive:
            raise error

def validator(attr=None, requests=None):
    """Marks the decorated method as a validator.

    :param string attr: Optional, the name of the field within the schema of the resource
        that will receive any validation errors raised by this validator.
    :param requests: Optional, a list of request names to which this validator should
        be attached; defaults to ``('create', 'update')``.

    The decorated method must be implemented as a class method, taking ``cls`` as its
    first argument, but should not be decorated with ``@classmethod``; ``validator`` will
    convert the method to a classmethod itself, as otherwise the method could not be
    annotated. The decorated method will receive on positional argument, the data received
    for the current request (which will already have passed standard validation), and
    should raise :exc:`ValidationError` if warranted.
    """

    if attr is not None and requests is None and not isinstance(attr, basestring):
        requests = attr
    if isinstance(requests, (list, tuple)):
        requests = list(requests)
    elif requests is not None:
        requests = [requests]

    if requests:
        for i in range(len(requests)):
            if isinstance(requests[i], (type, ClassType)):
                requests[i] = requests[i].__name__

    def decorator(method):
        method.__validates__ = True
        method.attr = attr
        method.requests = requests
        return classmethod(method)
    return decorator
