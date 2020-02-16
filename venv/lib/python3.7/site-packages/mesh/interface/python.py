from mesh.bundle import Specification
from mesh.constants import *
from mesh.exceptions import *
from mesh.server import Client

class ReadOnlyError(Exception):
    """..."""

class Attribute(object):
    """A model attribute."""

    def __init__(self, name, field):
        self.field = field
        self.name = name

    def __get__(self, instance, owner):
        if instance is not None:
            try:
                return instance._data[self.name]
            except KeyError:
                return None
        else:
            return self

    def __set__(self, instance, value):
        if self.field.readonly:
            raise ReadOnlyError(self.name)
        instance._data[self.name] = value

class ModelMeta(type):
    def __new__(metatype, name, bases, namespace):
        resource = namespace.pop('__resource__', None)
        if resource is not None:
            specification, resource = resource
            if not isinstance(specification, Specification):
                raise Exception('bad specification')
        else:
            return type.__new__(metatype, name, bases, namespace)

        resource = specification.resources.get(resource)
        if not resource:
            raise Exception('unknown resource')

        namespace['_name'] = resource['name']
        namespace['_resource'] = resource
        namespace['_specification'] = specification

        attributes = namespace['_attributes'] = {}
        for attr, field in resource['schema'].iteritems():
            namespace[attr] = attributes[attr] = Attribute(attr, field)

        model = type.__new__(metatype, name, bases, namespace)
        return model

class Model(object):
    """A resource model."""

    __metaclass__ = ModelMeta

    def __init__(self, **params):
        self._data = {}
        if params:
            self._update_model(params)

    @classmethod
    def create(cls, **params):
        request = cls._resource['requests']['create']
        instance = cls(**request['schema'].extract(params))
        return instance.save(**params)

    def destroy(self, **params):
        if self.id is None:
            return self

        response = self._execute_request('delete', params or None)
        return response.content

    @classmethod
    def get(cls, id, **params):
        return cls(id=id).refresh(**params)

    def refresh(self, **params):
        if self.id is None:
            return self

        response = self._execute_request('get', params or None)
        self._update_model(response.content)
        return self

    @classmethod
    def query(cls, **params):
        return cls._get_client().execute(cls._name, 'query', None, params or None)

    def save(self, **params):
        action = ('create' if self.id is None else 'update')
        request = self._resource['requests'][action]

        data = request['schema'].extract(self._data)
        if params:
            data.update(params)

        response = self._execute_request(action, data)
        self._update_model(response.content)
        return self

    def update(self, attrs, **params):
        self._update_model(attrs)
        return self.save(**params)

    def _execute_request(self, request, data=None):
        return self._get_client().execute(self._name, request, self.id, data)

    @classmethod
    def _get_client(cls):
        return Client.get(cls._specification)

    def _update_model(self, data):
        self._data.update(data)
