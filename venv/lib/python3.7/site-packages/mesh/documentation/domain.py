import re

from docutils import nodes
from docutils.parsers.rst import directives

from sphinx import addnodes
from sphinx.roles import XRefRole
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain, Index, ObjType
from sphinx.util.compat import Directive
from sphinx.util.nodes import make_refnode
from sphinx.util.docfields import Field, GroupedField, TypedField

def container(*classes):
    node = nodes.container()
    node['classes'].extend(classes)
    return node

def emphasis(text, *classes):
    node = nodes.emphasis(text, text)
    node['classes'].extend(classes)
    return node

def fieldlist(fields, *classes):
    node = nodes.field_list('')
    node['classes'].extend(classes)
    for name, value in fields:
        node += nodes.field('',
            nodes.field_name('', name),
            nodes.field_body('', nodes.paragraph('', value)),
        )
    return node

def inline(text, *classes):
    node = nodes.inline(text, text)
    node['classes'].extend(classes)
    return node

def literal(text, *classes):
    node = nodes.literal(text, text)
    node['classes'].extend(classes)
    return node

def paragraph(*classes):
    node = nodes.paragraph()
    node['classes'].extend(classes)
    return node

def section(id, title):
    node = nodes.section('', nodes.title('', title))
    node['ids'].append(id)
    return node

def strong(text, *classes):
    node = nodes.strong(text, text)
    node['classes'].extend(classes)
    return node

def text(text):
    return nodes.Text(text)

def aspect_block(name, value, element=text):
    block = paragraph('field-aspect')
    block += inline('%s: ' % name, 'aspect-name')
    block += element(value)
    return block

def format_value(value):
    if isinstance(value, basestring):
        if value.lower() in ('true', 'false'):
            return value.lower()
        for datatype in (float, int):
            try:
                datatype(value)
                return value
            except Exception:
                pass
        return repr(value)
    else:
        return str(value)

class FieldDefinition(Directive):
    has_content = True
    required_arguments = 0
    optional_arguments = 1
    final_argument_whitespace = True
    option_spec = {
        'type': directives.unchanged,
        'subtype': directives.unchanged,
        'description': directives.unchanged,
        'constraints': directives.unchanged,
        'default': directives.unchanged,
        'example': directives.unchanged,
        'pattern': directives.unchanged,
        'values': directives.unchanged,
        'required_keys': directives.unchanged,
        'nonnull': directives.flag,
        'required': directives.flag,
        'readonly': directives.flag,
        'deferred': directives.flag,
        'sectional': directives.flag,
    }

    aspects = {
        'pattern': literal,
        'values': literal,
        'required_keys': literal,
    }

    def run(self):
        sectional = ('sectional' if 'sectional' in self.options else '')
        definition = container('field', sectional)
        signature = nodes.paragraph('', '', classes=['field-signature'])

        field = (self.arguments[0] if len(self.arguments) == 1 else None)
        if field:
            required = ('required' if 'required' in self.options else '')
            separator = ':'
            if ' ' not in field:
                try:
                    int(field)
                except ValueError:
                    pass
                else:
                    separator = '.'
            signature += strong(field + separator, 'field-name', required, sectional)

        type = self.options.get('type')
        if type:
            signature += text(' ')
            signature += emphasis(type, 'field-type')

        subtype = self.options.get('subtype')
        if subtype:
            span = inline('<', 'field-subtype')
            aspects = None
            if ' ' in subtype:
                subtype, aspects = subtype.split(' ', 1)
            span += emphasis(subtype, 'field-type')
            if aspects:
                span += text(' ')
                span += inline(aspects, 'field-flags')
            span += text('>')
            signature += text(' ')
            signature += span

        default = self.options.get('default')
        if default:
            signature += literal(' default=%s' % default, 'field-default')

        constraints = self.options.get('constraints')
        if constraints:
            signature += literal(' %s' % constraints, 'field-constraints')

        flags = []
        for flag in ('required', 'nonnull', 'readonly', 'deferred'):
            if flag in self.options:
                flags.append(flag)
        if flags:
            signature += text(' ')
            signature += inline(' '.join(flags), 'field-flags')

        description = self.options.get('description')
        if description:
            signature += text(' ')
            signature += inline(description, 'field-description')

        definition += signature
        block = nodes.block_quote('')

        for aspect, element in self.aspects.iteritems():
            value = self.options.get(aspect)
            if value:
                block += aspect_block(aspect, value, element)

        self.state.nested_parse(self.content, self.content_offset, block)
        if block.children:
            definition += block

        return [definition]

class ResourceDefinition(Directive):
    has_content = True
    required_arguments = 2
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {
        'module': directives.unchanged,
        'version': directives.unchanged,
    }

    def run(self):
        name, title = self.arguments
        definition = section(name, '%s (%s)' % (title, self.options['version']))

        self.state.nested_parse(self.content, self.content_offset, definition)
        return [definition]

class RequestDefinition(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = False
    option_spec = {
        'title': directives.unchanged,
        'endpoint': directives.unchanged,
    }

    def run(self):
        name = title = self.arguments[0]
        if 'title' in self.options:
            title = '%s: %s' % (title, self.options['title'])

        paragraph = nodes.paragraph('', '')
        if 'endpoint' in self.options:
            paragraph += strong(self.options['endpoint'])

        block = section(name, title)
        block += paragraph

        self.state.nested_parse(self.content, self.content_offset, block)
        return [block]

class StructureDefinition(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 0
    final_argument_whitespace = True

    def run(self):
        block = nodes.block_quote('', classes=['structure-block'])
        self.state.nested_parse(self.content, self.content_offset, block)

        header = nodes.paragraph('', '', strong(self.arguments[0]), classes=['structure-header'])
        if block.children:
            return [header, block]
        else:
            return [header]

class ResourceIndex(Index):
    name = 'resourceindex'
    localname = 'Resource Index'
    shortname = 'resources'

    def generate(self, docnames=None):
        pass

class APIDomain(Domain):
    name = 'api'
    label = 'API'
    object_types = {
        'resource': ObjType('resource', 'resource'),
    }
    directives = {
        'field': FieldDefinition,
        'request': RequestDefinition,
        'resource': ResourceDefinition,
        'structure': StructureDefinition,
    }
    roles = {}
    initial_data = {
        'objects': {},
        'resources': {},
    }
    indices = []

    def get_objects(self):
        for refname, (docname, type) in self.data['objects'].iteritems():
            yield (refname, refname, type, docname, refname, 1)

def setup(app):
    app.add_domain(APIDomain)
