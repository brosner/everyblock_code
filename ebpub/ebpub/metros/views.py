from django.contrib.gis.geos import Point
from django.http import HttpResponse, Http404
from django.utils import simplejson as json
from ebpub.metros.models import Metro

def lookup_metro(request):
    """
    Lookups up a metro that contains the point represented by the two
    GET parameters, `lng' and `lat'.

    Returns a JSON object representing the Metro, minus the actual
    geometry.
    """
    try:
        lng = float(request.GET['lng'])
        lat = float(request.GET['lat'])
    except (KeyError, ValueError, TypeError):
        raise Http404('Missing/invalid lng and lat query parameters')

    try:
        metro = Metro.objects.containing_point(Point(lng, lat))
    except Metro.DoesNotExist:
        raise Http404("Couldn't find any metro matching that query")

    fields = [f.name for f in metro._meta.fields]
    fields.remove('location')
    metro = dict([(f, metro.serializable_value(f)) for f in fields])

    return HttpResponse(json.dumps(metro), mimetype='application/javascript')
