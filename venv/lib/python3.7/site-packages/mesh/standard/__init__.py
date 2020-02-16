from mesh.bundle import *
from mesh.constants import *
from mesh.exceptions import *
from mesh.request import *
from mesh.resource import *
from mesh.standard.controllers import *
from mesh.standard.requests import STANDARD_REQUESTS, VALIDATED_REQUESTS
from mesh.util import import_object
from scheme import *

STANDARD_CONFIGURATION = Configuration(
    standard_requests=STANDARD_REQUESTS,
    validated_requests=VALIDATED_REQUESTS,
    #default_controller=MockController,
)

class Resource(Resource):
    configuration = STANDARD_CONFIGURATION
