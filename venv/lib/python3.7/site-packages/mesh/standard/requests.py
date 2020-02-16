from mesh.constants import *
from mesh.exceptions import *
from mesh.request import *
from mesh.resource import *
from mesh.util import pluralize
from scheme import *

def filter_schema_for_response(resource):
    id_field = resource.id_field
    schema = {}
    for name, field in resource.filter_schema(exclusive=False, readonly=True).iteritems():
        if name == id_field.name:
            schema[name] = field.clone(required=True)
        elif field.required:
            schema[name] = field.clone(required=False)
        else:
            schema[name] = field
    return schema

class construct_model_request(object):
    def _construct_exclude_field(self, id_field, fields):
        tokens = []
        for name, field in fields.iteritems():
            if name != id_field.name and not field.deferred:
                tokens.append(name)
        if tokens:
            return Sequence(Enumeration(sorted(tokens), nonnull=True),
                description='Fields which should not be returned for this query.')

    def _construct_include_field(self, fields):
        tokens = []
        for name, field in fields.iteritems():
            if field.deferred:
                tokens.append(name)
        if tokens:
            return Sequence(Enumeration(sorted(tokens), nonnull=True),
                description='Deferred fields which should be returned for this query.')

class construct_query_request(construct_model_request):
    operators = {
        'eq': 'Equals.',
        'ieq': 'Case-insensitive equals.',
        'ne': 'Not equal.',
        'ine': 'Case-insensitive not equal.',
        'pre': 'Prefix search.',
        'ipre': 'Case-insensitive prefix search.',
        'suf': 'Suffix search.',
        'isuf': 'Case-insensitive suffix search.',
        'cnt': 'Contains.',
        'icnt': 'Case-insensitive contains.',
        'gt': 'Greater then.',
        'gte': 'Greater then or equal to.',
        'lt': 'Less then.',
        'lte': 'Less then or equal to.',
        'nul': 'Is null.',
        'len': 'Length.',
        'in': 'In given values.',
        'nin': 'Not in given values.',
    }

    def __call__(self, resource):
        fields = filter_schema_for_response(resource)
        schema = {
            'offset': Integer(minimum=0, default=0,
                description='The offset into the result set of this query.'),
            'limit': Integer(minimum=0,
                description='The maximum number of resources to return for this query.'),
            'total': Boolean(default=False, nonnull=True,
                description='If true, only return the total for this query.'),
        }

        include_field = self._construct_include_field(fields)
        if include_field:
            schema['include'] = include_field

        exclude_field = self._construct_exclude_field(resource.id_field, fields)
        if exclude_field:
            schema['exclude'] = exclude_field

        sort_field = self._construct_sort_field(fields)
        if sort_field:
            schema['sort'] = sort_field

        operators = {}
        for name, field in fields.iteritems():
            if field.operators:
                operator_field = self._construct_operator_field(field)
                if operator_field:
                    operators[name] = operator_field

        if operators:
            schema['query'] = Structure(operators,
                description='The query to filter resources by.')

        response_schema = Structure({
            'total': Integer(nonnull=True, minimum=0,
                description='The total number of resources in the result set for this query.'),
            'resources': Sequence(Structure(fields), nonnull=True),
        })

        return Request(
            name = 'query',
            endpoint = (GET, resource.name),
            auto_constructed = True,
            resource = resource,
            title = 'Querying %s' % pluralize(resource.title.lower()),
            schema = Structure(schema),
            responses = {
                OK: Response(response_schema),
                INVALID: Response(Errors),
            }
        )

    def _construct_sort_field(self, fields):
        tokens = []
        for name, field in fields.iteritems():
            if field.sortable:
                for suffix in ('', '+', '-'):
                    tokens.append(name + suffix)
        if tokens:
            return Sequence(Enumeration(sorted(tokens), nonnull=True),
                description='The sort order for this query.')

    def _construct_operator_field(self, field):
        if field.operators == ['eq']:
            return self._construct_eq_operator(field, self.operators['eq'])

        operators = Structure({})
        for operator in field.operators:
            description = self.operators.get(operator)
            if description and operator != 'eq':
                constructor = getattr(self, '_construct_%s_operator' % operator, None)
                if constructor:
                    op = constructor(field, description)
                else:
                    op = type(field)(name='$' + operator, description=description, nonnull=True)
                operators.structure[op.name] = op

        if 'eq' in field.operators:
            op = self._construct_eq_operator(field, self.operators['eq'])
            operators = Union((operators, op))

        return operators

    def _construct_eq_operator(self, field, description):
        return type(field)(name=field.name, description=description, nonnull=True)

    def _construct_nul_operator(self, field, description):
        return Boolean(name='$nul', description=description, nonnull=True)

    def _construct_len_operator(self, field, description):
        return Integer(name='$len', description=description,
            nonnull=True, minimum=0)

    def _construct_in_operator(self, field, description):
        return Sequence(type(field)(nonnull=True), name='$in',
            description=description, nonnull=True, min_length=1)

    def _construct_nin_operator(self, field, description):
        return Sequence(type(field)(nonnull=True), name='$nin',
            description=description, nonnull=True, min_length=1)

class construct_get_request(construct_model_request):
    def __call__(self, resource):
        fields = filter_schema_for_response(resource)
        schema = {}

        include_field = self._construct_include_field(fields)
        if include_field:
            schema['include'] = include_field

        exclude_field = self._construct_exclude_field(resource.id_field, fields)
        if exclude_field:
            schema['exclude'] = exclude_field

        response_schema = Structure(fields)
        return Request(
            name = 'get',
            endpoint = (GET, resource.name + '/id'),
            specific = True,
            auto_constructed = True,
            resource = resource,
            title = 'Getting a specific %s' % resource.title.lower(),
            schema = schema and Structure(schema) or None,
            responses = {
                OK: Response(response_schema),
                INVALID: Response(Errors),
            }
        )

def construct_create_request(resource):
    resource_schema = resource.filter_schema(exclusive=False, readonly=False)
    if resource.id_field.name in resource_schema:
        del resource_schema[resource.id_field.name]

    response_schema = {
        resource.id_field.name: resource.id_field.clone(required=True),
    }
    
    return Request(
        name = 'create',
        endpoint = (POST, resource.name),
        auto_constructed = True,
        resource = resource,
        title = 'Creating a new %s' % resource.title.lower(),
        schema = Structure(resource_schema),
        responses = {
            OK: Response(Structure(response_schema)),
            INVALID: Response(Errors),
        }
    )

def construct_update_request(resource):
    schema = {}
    for name, field in resource.filter_schema(exclusive=False, readonly=False).iteritems():
        if name != resource.id_field.name:
            if field.required:
                field = field.clone(required=False)
            schema[name] = field

    response_schema = {
        resource.id_field.name: resource.id_field.clone(required=True),
    }

    return Request(
        name = 'update',
        endpoint = (POST, resource.name + '/id'),
        specific = True,
        auto_constructed = True,
        resource = resource,
        title = 'Updating a specific %s' % resource.title.lower(),
        schema = Structure(schema),
        responses = {
            OK: Response(Structure(response_schema)),
            INVALID: Response(Errors),
        }
    )

def construct_create_update_request(resource):
    schema = {}
    for name, field in resource.filter_schema(exclusive=False, readonly=False).iteritems():
        if field.required:
            field = field.clone(required=False)
        schema[name] = field

    schema = Sequence(Structure(schema))
    response_schema = Sequence(Structure({
        resource.id_field.name: resource.id_field.clone(required=True),
    }))

    return Request(
        name = 'create_update',
        endpoint = (PUT, resource.name),
        specific = False,
        auto_constructed = True,
        resource = resource,
        title = 'Creating and updating multiple %s' % pluralize(resource.title.lower()),
        schema = schema,
        responses = {
            OK: Response(response_schema),
            INVALID: Response(Errors),
        }
    )

def construct_delete_request(resource):
    id_field = resource.id_field
    response_schema = Structure({
        id_field.name: id_field.clone(required=True)
    })

    return Request(
        name = 'delete',
        endpoint = (DELETE, resource.name + '/id'),
        specific = True,
        auto_constructed = True,
        resource = resource,
        title = 'Deleting a specific %s' % resource.title.lower(),
        schema = None,
        responses = {
            OK: Response(response_schema),
        }
    )

STANDARD_REQUESTS = {
    'query': construct_query_request(),
    'get': construct_get_request(),
    'create': construct_create_request,
    'update': construct_update_request,
#    'create_update': construct_create_update_request,
    'delete': construct_delete_request,
}
VALIDATED_REQUESTS = ['create', 'update']
