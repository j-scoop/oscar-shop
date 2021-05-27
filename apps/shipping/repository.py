from oscar.apps.shipping import repository
from . import methods

class Repository(repository.Repository):
    # Express removed for now. Can be added to tuple
    methods = (methods.Standard(),)
