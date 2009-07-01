from ebpub.db.models import NewsItem
from ebpub.geocoder import SmartGeocoder, GeocodingException, AmbiguousResult, InvalidBlockButValidStreet
from ebpub.geocoder.parser.parsing import ParsingError

def geocode(schema=None):
    """
    Geocode NewsItems with null locations.

    If ``schema`` is provided, only geocode NewsItems with that particular
    schema slug.
    """
    geocoder = SmartGeocoder()
    qs = NewsItem.objects.filter(location__isnull=True).order_by('-id')
    if schema is not None:
        print "Geocoding %s..." % schema
        qs = qs.filter(schema__slug=schema)
    else:
        print "Geocoding all ungeocoded newsitems..."

    geocoded_count = 0
    not_found_count = 0
    ambiguous_count = 0
    parsing_error_count = 0
    invalid_block_count = 0

    for ni in qs.iterator():
        loc_name = ni.location_name
        try:
            add = geocoder.geocode(loc_name)
        except InvalidBlockButValidStreet:
            print '      invalid block but valid street: %s' % loc_name
            invalid_block_count += 1
        except AmbiguousResult, e:
            print '      ambiguous: %s' % loc_name
            ambiguous_count += 1
        except GeocodingException, e:
            print '      not found: %s' % loc_name
            not_found_count += 1
        except ParsingError:
            print '      parse error: %s' % loc_name
            parsing_error_count += 1
        except:
            raise
        else:
            ni.location = add['point']
            ni.block = add['block']
            ni.save()
            print '%s (%s)' % (loc_name, ni.item_url())
            geocoded_count += 1

    print "------------------------------------------------------------------"
    print "Geocoded:       %s" % geocoded_count
    print "Not found:      %s" % not_found_count
    print "Ambiguous:      %s" % ambiguous_count
    print "Parse errors:   %s" % parsing_error_count
    print "Invalid blocks: %s" % invalid_block_count

if __name__ == "__main__":
    import sys
    try:
        schema_slug = sys.argv[1]
    except IndexError:
        geocode()
    else:
        geocode(schema_slug)
