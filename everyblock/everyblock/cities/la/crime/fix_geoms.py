from ebdata.retrieval.utils import locations_are_close
from ebpub.db.models import NewsItem
from ebpub.geocoder import SmartGeocoder, ParsingError, GeocodingException
from django.contrib.gis.geos import Point

geocoder = SmartGeocoder()
THRESHOLD = 375

def fix_crime_geom():
    qs = NewsItem.objects.filter(schema__slug='crime', location__isnull=False)
    count = qs.count()
    for i, ni in enumerate(qs.iterator()):
        print '# => Checking %s of %s' % (i, count)
        x, y = [float(n) for n in ni.attributes['xy'].split(';')]
        pt = Point((x, y))
        pt.srid = 4326
        location_name = ni.location_name.replace('XX', '01')
        try:
            result = geocoder.geocode(location_name)
        except (GeocodingException, ParsingError):
            print '     Could not geocode'
            NewsItem.objects.filter(id=ni.id).update(location=None)
        else:
            is_close, distance = locations_are_close(ni.location, pt, THRESHOLD)
            if not is_close:
                print '     Too far: %s' % distance
                NewsItem.objects.filter(id=ni.id).update(location=None)
            else:
                print '     Fine'

if __name__ == "__main__":
    fix_crime_geom()
