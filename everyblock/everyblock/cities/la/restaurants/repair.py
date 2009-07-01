"""
Sets locaion=None on newsitems from cities in the suburbs table.
"""

from ebpub.db.models import NewsItem, Lookup
from ebpub.streets.models import Suburb
from everyblock.utils import queryset
import pprint

SCHEMA = 'food-inspections'
SUBURBS = [s[0] for s in Suburb.objects.values_list('normalized_name')]
CITIES = {}
for city_id, city_name in Lookup.objects.filter(schema_field__name='city', schema_field__schema__slug=SCHEMA).values_list('id', 'name'):
    CITIES[city_id] = city_name

def deloacte_suburbs():
    stats = {}
    for start, end, total, qs in queryset.batch(NewsItem.objects.filter(schema__slug=SCHEMA)):
        print "processing %s to %s of %s" % (start, end, total)
        for ni in qs:
            city = CITIES[ni.attributes['city']]
            if ni.location is not None and city in SUBURBS:
                ni.location = None
                stats[city] = stats.get(city, 0) + 1
                ni.save()
    print pprint.pprint(stats)

if __name__ == '__main__':
    deloacte_suburbs()
