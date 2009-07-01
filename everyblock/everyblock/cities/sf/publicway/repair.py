"""
Change the ad-hoc encoding of Excavation permit details to json.
"""

from ebpub.db.models import NewsItem
from ebpub.utils.text import smart_title
from everyblock.cities.sf.publicway.retrieval import ExcavationPermitScraper
from everyblock.utils import queryset
from django.utils import simplejson
from pprint import pprint
import re

intersection_re = re.compile(r'\s?Intersection of (.*?) and (.*)')
segment_re = re.compile(r'(.*?) from (.*?) to (.*)')

VARIOUS = 'Various streets (see map)'

def repair_details(details):
    """
    Convert old-style details into a more structured format.
    """
    m = segment_re.match(details)
    if m is None:
        m = intersection_re.match(details)
        if m is None:
            raise Exception("No match was found for %s" % details)
        else:
            cross_street_1, cross_street_2 = m.groups()
            return {
                'cross_street_1': cross_street_1.upper().strip(),
                'cross_street_2': cross_street_2.upper().strip()
            }
    else:
        street_name, cross_street_1, cross_street_2 = m.groups()
        if cross_street_2 == '':
            # THE FOLLOWING RETURN VALUE IS NOT A TYPO. THERE IS NO cross_street_2, 
            # SO THIS REALLY IS AN ITERSECTION.
            return {
                'cross_street_1': street_name.upper().strip(),
                'cross_street_2': cross_street_1.upper().strip()
            }
        else:
            return {
                'street_name': street_name.upper().strip(),
                'cross_street_1': cross_street_1.upper().strip(),
                'cross_street_2': cross_street_2.upper().strip()
            }

def verbose_detail(detail):
    clean_cross_1 = smart_title(detail['cross_street_1'])
    clean_cross_2 = smart_title(detail['cross_street_2'])
    if detail.has_key('street_name'):
        clean_street_name = smart_title(detail['street_name'])
        return '%s from %s to %s' % (clean_street_name, clean_cross_1, clean_cross_2)
    else:
        return 'Intersection of %s and %s' % (clean_cross_1, clean_cross_2)

def convert_to_json():
    news_items = NewsItem.objects.filter(schema__slug='excavation-permits').order_by('id')
    for start, end, total, qs in queryset.batch(news_items):
        print "processing %s to %s of %s" % (start + 1, end, total)
        for ni in qs:
            #print ni.attributes['location_details']
            cnn_list, details = ni.attributes['location_details'].split('___')
            details = [repair_details(d) for d in details.split(';')]
            location_details = {
                'cnn_list': cnn_list.split(','),
                'details': details,
            }
            #pprint(location_details)
            ni.attributes['location_details'] = simplejson.dumps(location_details)


            streets = set()
            for detail in details:
                if detail.has_key('street_name'):
                    streets.add(detail['street_name'])
                else:
                    streets.add(detail['cross_street_1'])

            location_name = ', '.join([smart_title(street) for street in streets])
            if len(location_name) > 150:
                location_name = VARIOUS

            description = '; '.join([verbose_detail(loc) for loc in location_details['details']])


            ni.location_name = location_name
            ni.description = description
            ni.save()
            
            #cnn_list = cnn_list.split(',')
            #location_details = location_details.split(';')
            #
            #cnn_count = len(cnn_list)
            #cnn_count_distinct = len(set(cnn_list))
            #location_count = len(location_details)
            #location_count_distinct = len(set(location_details))
            #
            #if cnn_count != cnn_count_distinct:
            #    print "CNN MISMATCH"
            #    print cnn_list
            #    print set(cnn_list)
            #if location_count != location_count_distinct:
            #    print "LOCATION MISMATCH"
            #    print location_details
            #    print set(location_details)
            #if cnn_count != location_count:
            #    print "CNN/LOCATION MISMATCH"
            #    print cnn_list
            #    print location_details
            #if cnn_count_distinct != location_count_distinct:
            #    print "CNN/LOCATION MISMATCH"
            #    print set(cnn_list)
            #    print set(location_details)
            #if cnn_count != cnn_count_distinct != location_count != location_count_distinct:
            #    print ni.attributes['location_details']
            #    print '----------------------------------------------------------'


class Scraper(ExcavationPermitScraper):
    def save(self, old_record, list_record, detail_record):
        locations = simplejson.loads(old_record.attributes['location_details'])
        locations['old_locations'] = [tuple(loc) for loc in locations['old_locations']]
        locations['new_locations'] = [tuple(loc) for loc in locations['new_locations']]

        #pprint(location_list)

        detail = self.clean_detail(list_record)
        old_location = (list_record['cnn'], detail)

        try:
            # remove the old location and add the new one
            i = locations['old_locations'].index(old_location)
            del locations['old_locations'][i]
            locations['new_locations'].append((
                list_record['cnn'],
                detail,
                list_record['streetname'],
                list_record['Cross Street 1'],
                list_record['Cross Street 2']
            ))
            pprint(locations)
        except ValueError:
            pass

        old_record.attributes['location_details'] = simplejson.dumps(locations)
        old_record.save()


if __name__ == '__main__':
    convert_to_json()
    #Scraper().update()
