import os
import textwrap
from datetime import date, datetime, time

from mesh.constants import *
from mesh.resource import *
from mesh.util import format_url_path
from scheme import *

STATUS_CODES = (
    (OK, '200 OK'),
    (CREATED, '201 CREATED'),
    (ACCEPTED, '202 ACCEPTED'),
    (PARTIAL, '206 PARTIAL CONTENT'),
    (BAD_REQUEST, '400 BAD REQUEST'),
    (FORBIDDEN, '403 FORBIDDEN'),
    (NOT_FOUND, '404 NOT FOUND'),
    (METHOD_NOT_ALLOWED, '405 METHOD NOT ALLOWED'),
    (INVALID, '406 NOT ACCEPTABLE'),
    (TIMEOUT, '408 REQUEST TIMEOUT'),
    (CONFLICT, '409 CONFLICT'),
    (GONE, '410 GONE'),
    (SERVER_ERROR, '500 INTERNAL SERVER ERROR'),
    (UNIMPLEMENTED, '501 NOT IMPLEMENTED'),
    (UNAVAILABLE, '503 SERVICE UNAVAILABLE'),
)

RESOURCE_HEADER = """
.. default-domain:: api
"""

INDEX_TEMPLATE = """
================================
%(name)s
================================

%(description)s

%(sections)s
"""

SECTION_TEMPLATE = """
%(title)s
======================

.. toctree::
    :maxdepth: 2
    %(refs)s
"""

class directive(object):
    def __init__(self, directive, *args):
        self.args = list(args)
        self.content = []
        self.directive = directive
        self.params = []

    def add(self, arg):
        self.args.append(arg)
        return self

    def append(self, item):
        self.content.append(item)
        return self

    def extend(self, items):
        self.content.extend(items)
        return self

    def set(self, name, value):
        self.params.append((name, value))
        return self

    def render(self, indent=0):
        inner_indent = indent + 1
        inner_prefix = '    ' * inner_indent

        content = []
        for node in self.content:
            if isinstance(node, directive):
                content.append(node.render(inner_indent))
            elif isinstance(node, basestring):
                node = node.lstrip()
                content.append('\n'.join(textwrap.wrap(node, 80, expand_tabs=False,
                    initial_indent=inner_prefix,
                    subsequent_indent=inner_prefix)))


        params = []
        for name, value in self.params:
            value = str(value)
            if '\n' in value:
                values = value.split('\n')
                value = '\n'.join([values[0]] + ['%s    %s' % (inner_prefix, v) for v in values[1:]])
            params.append('%s:%s: %s' % (inner_prefix, name, value))

        return '\n%s.. %s:: %s\n%s\n\n%s' % (
            '    ' * indent,
            self.directive,
            ' '.join(str(arg) for arg in self.args),
            '\n'.join(params),
            '\n\n'.join(content),
        )

class DocumentationGenerator(object):
    def __init__(self, root_path):
        self.root_path = root_path

    def generate(self, bundle):
        bundle_path = os.path.join(self.root_path, bundle['name'])
        if not os.path.exists(bundle_path):
            os.mkdir(bundle_path)

        sections = []
        for version, resources in sorted(bundle['versions'].iteritems(), reverse=True):
            version_string = '%d.%d' % version
            path_prefix = '/%s/%s' % (bundle['name'], version_string)

            refs = ['']

            version_path = os.path.join(bundle_path, version_string)
            if not os.path.exists(version_path):
                os.mkdir(version_path)

            for name, specification in sorted(resources.iteritems()):
                content = self._document_resource(specification, version_string, path_prefix)
                openfile = open(os.path.join(version_path, '%s.rst' % name), 'w+')
                try:
                    openfile.write(content)
                finally:
                    openfile.close()
                refs.append(os.path.join(version_string, name))

            sections.append(SECTION_TEMPLATE % {
                'title': 'Version %s' % version_string,
                'refs': '\n    '.join(sorted(refs)),
            })

        self._generate_index(bundle, bundle_path, sections)

    def _collate_fields(self, fields):
        if 'id' in fields:
            yield 'id', fields['id']

        optional = []
        for name, field in sorted(fields.iteritems()):
            if name != 'id':
                if field['required']:
                    yield name, field
                else:
                    optional.append((name, field))

        for name, field in optional:
            yield name, field

    def _describe_date(self, field, block, role):
        constraints = []
        if isinstance(field['minimum'], date):
            constraints.append('min=%s' % field['minimum'])
        if isinstance(field['maximum'], date):
            constraints.append('max=%s' % field['maximum'])
        if constraints:
            block.set('constraints', ', '.join(constraints))

    def _describe_datetime(self, field, block, role):
        constraints = []
        if isinstance(field['minimum'], datetime):
            constraints.append('min=%s' % field['minimum'])
        if isinstance(field['maximum'], datetime):
            constraints.append('max=%s' % field['maximum'])
        if constraints:
            block.set('constraints', ', '.join(constraints))

    def _describe_enumeration(self, field, block, role):
        block.set('values', repr(field['enumeration']))

    def _describe_float(self, field, block, role):
        constraints = []
        if field['minimum'] is not None:
            constraints.append('min=%r' % field['minimum'])
        if field['maximum'] is not None:
            constraints.append('max=%r' % field['maximum'])
        if constraints:
            block.set('constraints', ' '.join(constraints))

    def _describe_integer(self, field, block, role):
        constraints = []
        if field['minimum'] is not None:
            constraints.append('min=%r' % field['minimum'])
        if field['maximum'] is not None:
            constraints.append('max=%r' % field['maximum'])
        if constraints:
            block.set('constraints', ' '.join(constraints))

    def _describe_map(self, field, block, role):
        if field['required_keys']:
            block.set('required_keys', repr(sorted(field['required_keys'])))
        if field['value']:
            value = field['value']
            if not value['description']:
                block.set('subtype', value['type'])
            else:
                block.append(self._document_field('', value, role))

    def _describe_sequence(self, field, block, role):
        constraints = []
        if field['min_length'] is not None:
            constraints.append('min=%d' % field['min_length'])
        if field['max_length'] is not None:
            constraints.append('max=%d' % field['max_length'])
        if constraints:
            block.set('constraints', ', '.join(constraints))
        if field['item']:
            item = field['item']
            block.append(self._document_field('', field['item'], role))

    def _describe_structure(self, field, block, role):
        if field['structure']:
            for name, subfield in self._collate_fields(field['structure']):
                block.append(self._document_field(name, subfield, role))

    def _describe_text(self, field, block, role):
        constraints = []
        if isinstance(field['min_length'], (int, long)):
            constraints.append('min=%r' % field['min_length'])
        if isinstance(field['max_length'], (int, long)):
            constraints.append('max=%r' % field['max_length'])
        if constraints:
            block.set('constraints', ', '.join(constraints))
        if field['pattern']:
            block.set('pattern', field['pattern'])

    def _describe_time(self, field, block, role):
        constraints = []
        if isinstance(field['minimum'], time):
            constraints.append('min=%s' % field['minimum'])
        if isinstance(field['maximum'], time):
            constraints.append('max=%s' % field['maximum'])
        if constraints:
            block.set('constraints', ', '.join(constraints))

    def _describe_tuple(self, field, block, role):
        if field['values']:
            for i, value in enumerate(field['values']):
                block.append(self._document_field('', value, role))

    def _describe_union(self, field, block, role):
        if field['fields']:
            for i, subfield in enumerate(field['fields']):
                block.append(self._document_field('', subfield, role))

    def _document_field(self, name, field, role=None, sectional=False):
        block = directive('field', name)
        block.set('type', field['type'])
        if sectional:
            block.set('sectional', '')

        for attr in ('description', 'notes'):
            if field[attr]:
                block.set(attr, field[attr])
        for attr in ('nonnull', 'readonly'):
            if field[attr]:
                block.set(attr, '')

        if field['required'] and role != 'schema':
            block.set('required', '')
        if field['deferred'] and role != 'request':
            block.set('deferred', '')
        if field['default'] is not None:
            block.set('default', repr(field['default']))
        
        formatter = getattr(self, '_describe_%s' % field['type'], None)
        if formatter:
            formatter(field, block, role)
        return block

    def _document_request(self, version, request, path_prefix):
        block = directive('request', request['name'])
        if request.get('title'):
            block.set('title', request['title'])
        if request.get('endpoint'):
            block.set('endpoint', '%s %s%s' % (request['endpoint'][0],
                path_prefix, request['path']))

        if request.get('description'):
            block.append(request['description'])
        if request['schema']:
            block.append(self._document_field('REQUEST', request['schema'],
                'request', sectional=True))
        
        responses = request['responses']
        for status, status_line in STATUS_CODES:
            if status in responses:
                response = responses[status]
                if response['schema']:
                    block.append(self._document_field(status_line, response['schema'],
                        'response', sectional=True))

        return block

    def _document_resource(self, specification, version, path_prefix):
        block = directive('resource', specification['name'], specification['title'])
        block.set('version', version)
        
        description = specification['description']
        if description:
            block.append(description)

        schema = directive('structure', 'SCHEMA')
        for name, field in self._collate_fields(specification['schema']):
            schema.append(self._document_field(name, field, 'schema'))

        block.append(schema)
        for name, request in sorted(specification['requests'].iteritems()):
            block.append(self._document_request(version, request, path_prefix))

        return RESOURCE_HEADER + block.render()

    def _generate_index(self, bundle, bundle_path, sections):
        content = INDEX_TEMPLATE % {
            'name': bundle['name'],
            'description': bundle['description'] or '',
            'sections': '\n\n'.join(sections),
        }

        openfile = open(os.path.join(bundle_path, 'index.rst'), 'w+')
        try:
            openfile.write(content)
        finally:
            openfile.close()
