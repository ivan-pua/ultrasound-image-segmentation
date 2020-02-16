from types import FunctionType

from unittest2 import TestCase

from mesh.transport import Transport

def versions(version=None, min_version=None, max_version=None):
    def decorator(method):
        if version is not None:
            method.version = version
        if min_version is not None:
            method.min_version = min_version
        if max_version is not None:
            method.max_version = max_version
        return method
    return decorator

class MeshTestCaseMeta(type):
    def __new__(metatype, name, bases, namespace):
        tests = []
        for attr in namespace.keys():
            function = namespace[attr]
            if isinstance(function, FunctionType) and attr[:5] == 'test_':
                tests.append(namespace.pop(attr))

        testcase = type.__new__(metatype, name, bases, namespace)
        for test in tests:
            metatype._generate_tests(testcase, test)

        return testcase

    @staticmethod
    def _generate_tests(testcase, function):
        bundle = testcase.bundle
        versions = bundle.slice(getattr(function, 'version', None),
            getattr(function, 'min_version', None),
            getattr(function, 'max_version', None))

        for version in versions:
            specification = bundle.specify(version)
            for name in testcase.transports:
                transport = Transport.transports[name]
                def test(self):
                    server, client = transport.construct_fixture(bundle, specification)
                    function(self, client)

                test.__name__ = '%s_%d_%d_%s' % (function.__name__, version[0], version[1], name)
                setattr(testcase, test.__name__, test)

class MeshTestCase(TestCase):
    __metaclass__ = MeshTestCaseMeta

    bundle = None
    transports = ['internal']
