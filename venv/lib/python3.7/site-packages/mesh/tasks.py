from bake import Task, param
from mesh.documentation.generator import DocumentationGenerator

class GenerateDocs(Task):
    name = 'mesh:docs'
    description = 'generate api documentation for a mesh bundle'
    params = [
        param('mesh.docroot', 'path to docroot', required=True),
        param('mesh.bundles', '...', required=True),
    ]
