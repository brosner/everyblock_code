from django.utils.simplejson import JSONEncoder
from bunch import Bunch # relative import

class ClusterJSON(JSONEncoder):
    def default(self, o):
        if isinstance(o, Bunch):
            return [o.objects, o.center]
        else:
            return JSONEncoder.default(self, o)
