from mesh.exceptions import *
from mesh.resource import Controller
from mesh.util import import_object
from scheme.fields import Field

__all__ = ('Bundle', 'Specification', 'mount')

class mount(object):
    """A resource mount."""

    def __init__(self, resource, controller=None, min_version=None, max_version=None):
        self.controller = controller
        self.max_version = max_version
        self.min_version = min_version
        self.resource = resource

    def construct(self, bundle):
        """Constructs this mount for ``bundle``."""

        resource = self.resource
        if isinstance(resource, basestring):
            resource = self.resource = import_object(resource, True)
        if not resource:
            return False

        controller = self.controller
        if isinstance(controller, basestring):
            controller = import_object(controller, True)
        if not controller:
            controller = resource.configuration.create_controller(resource)

        self.controller = controller
        self.min_version = self._validate_version(resource, controller, self.min_version, 'minimum_version')
        self.max_version = self._validate_version(resource, controller, self.max_version, 'maximum_version')

        self.versions = []
        for candidate in controller.versions.keys():
            if candidate >= self.min_version and candidate <= self.max_version:
                self.versions.append(candidate)

        self.versions.sort()
        return True

    def get(self, version):
        """Get the resource/controller pair for ``version``."""

        for candidate in reversed(self.versions):
            if version >= candidate:
                return self.controller.versions[candidate]

    def _validate_version(self, resource, controller, value, attr):
        if value is not None:
            if isinstance(value, tuple) and len(value) == 2:
                if controller:
                    if value in controller.versions:
                        return value
                    else:
                        raise SpecificationError()
                elif value[0] in resource.versions and value[1] == 0:
                    return value
                else:
                    raise SpecificationError()
            else:
                raise SpecificationError()
        elif controller:
            return getattr(controller, attr)
        else:
            return (getattr(resource, attr), 0)

class Bundle(object):
    """A bundle of resources."""

    def __init__(self, name, *mounts, **params):
        self.description = params.get('description', None)
        self.name = name
        self.ordering = None
        self.versions = None

        self.mounts = []
        if mounts:
            self.attach(mounts)

    def attach(self, mounts):
        """Attaches ``mounts`` to this ``bundle``."""

        for mount in mounts:
            if mount.construct(self):
                self.mounts.append(mount)
        if self.mounts:
            self._collate_mounts()

    def describe(self, path_prefix=None, version=None):
        description = {'name': self.name, 'description': self.description}
        if version is not None:
            description.update(version=version, resources={})
            for name, (resource, controller) in self.versions[version].iteritems():
                description['resources'][name] = resource.describe(controller, path_prefix)
        else:
            versions = description['versions'] = {}
            for version, resources in self.versions.iteritems():
                versions[version] = {}
                for name, (resource, controller) in resources.iteritems():
                    versions[version][name] = resource.describe(controller, path_prefix)

        return description

    def slice(self, version=None, min_version=None, max_version=None):
        versions = self.versions
        if version is not None:
            if version in self.versions:
                return [version]
            else:
                return []

        versions = sorted(versions.keys())
        if min_version is not None:
            i = 0
            try:
                while versions[i] < min_version:
                    versions = versions[1:]
                    i += 1
            except IndexError:
                return versions

        if max_version is not None:
            i = len(versions) - 1
            try:
                while versions[i] > max_version:
                    versions = versions[:-1]
                    i -= 1
            except IndexError:
                return versions

        return versions

    def specify(self, version, path_prefix=None):
        return Specification(self.describe(path_prefix, version))

    def _collate_mounts(self):
        ordering = set()
        for mount in self.mounts:
            ordering.update(mount.versions)

        self.ordering = sorted(ordering)
        self.versions = dict()

        for mount in self.mounts:
            for version in self.ordering:
                controller = mount.get(version)
                if controller:
                    resource = mount.resource
                    if version not in self.versions:
                        self.versions[version] = {resource.name: (resource, controller)}
                    elif resource.name not in self.versions[version]:
                        self.versions[version][resource.name] = (resource, controller)
                    else:
                        raise SpecificationError()

class Specification(object):
    """A bundle specification for a particular version."""

    def __init__(self, specification):
        self.__dict__.update(specification)
        self.id = '%s:%d.%d' % (self.name, self.version[0], self.version[1])

        for resource in self.resources.itervalues():
            self._parse_resource(resource)

    def __repr__(self):
        return 'Specification(name=%r, version=%r)' % (self.name, self.version)

    def __str__(self):
        return self.id

    def _parse_resource(self, resource):
        schema = resource.get('schema')
        if isinstance(schema, dict):
            for name, field in schema.items():
                schema[name] = Field.reconstruct(field)

        requests = resource.get('requests')
        if isinstance(requests, dict):
            for request in requests.itervalues():
                request['schema'] = Field.reconstruct(request['schema'])
                for response in request['responses'].itervalues():
                    response['schema'] = Field.reconstruct(response['schema'])
