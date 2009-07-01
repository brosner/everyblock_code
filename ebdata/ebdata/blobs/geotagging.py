from django.conf import settings
from ebdata.blobs.auto_purge import page_should_be_purged
from ebdata.blobs.models import Page
from ebdata.nlp.addresses import parse_addresses
from ebpub.db.models import NewsItem, SchemaField, Lookup
from ebpub.geocoder import SmartGeocoder, AmbiguousResult, DoesNotExist, InvalidBlockButValidStreet
from ebpub.geocoder.parser.parsing import normalize, ParsingError
from ebpub.streets.models import Suburb
from ebpub.utils.text import slugify, smart_excerpt
import datetime
import time


def save_locations_for_page(p):
    """
    Given a Page object, this function parses the text, finds all valid
    locations and creates a NewsItem for each location.
    """
    paragraph_list = p.auto_excerpt()
    do_purge, no_purge_reason = page_should_be_purged(paragraph_list)
    robot_report = [no_purge_reason]
    if do_purge:
        p.set_no_locations(geocoded_by='confidentrobot')
    else:
        if p.seed.autodetect_locations:
            if not p.article_headline:
                return
            if not p.article_date:
                return

            # Add a paragraph of the article's headline so that we find any/all
            # addresses in the headline, too.
            paragraph_list = [p.article_headline] + paragraph_list

            locations, location_report = auto_locations(paragraph_list, p.seed.city)
            if location_report:
                robot_report.append(location_report)

            if locations:
                # Check for existing NewsItems with this exact pub_date,
                # headline, location_name and source.
                do_geotag = True
                try:
                    source_schemafield = SchemaField.objects.get(schema__id=p.seed.schema_id, name='source')
                except SchemaField.DoesNotExist:
                    pass
                else:
                    existing_newsitems = NewsItem.objects.filter(schema__id=p.seed.schema_id,
                        pub_date=p.article_date, title=p.article_headline,
                        location_name=locations[0][0]).by_attribute(source_schemafield, p.seed.pretty_name, is_lookup=True).count()
                    if existing_newsitems:
                        robot_report.append('article appears to exist already')
                        do_geotag = False
                if do_geotag:
                    geotag_page(p.id, p.seed.pretty_name, p.seed.schema, p.url,
                        locations, p.article_headline, p.article_date)
            p.has_addresses = bool(locations)
            p.when_geocoded = datetime.datetime.now()
            p.geocoded_by = 'robot'
        p.robot_report = '; '.join(robot_report)[:255]
    p.save()

def geotag_page(page_id, source, schema, url, data_tuples, article_headline, article_date):
    """
    Given a Page ID and a list of (location, wkt, excerpt, block) tuples
    representing the addresses in the page, creates a NewsItem for each
    address. Returns a list of all created NewsItems.
    """
    if not data_tuples:
        return
    if not source:
        raise ValueError('Provide a source')
    if not url:
        raise ValueError('Provide a URL')
    if not article_headline:
        raise ValueError('Provide an article headline')
    if not article_date:
        raise ValueError('Provide an article date')
    if not isinstance(article_date, datetime.date):
        article_date = datetime.date(*time.strptime(article_date, '%Y-%m-%d')[:3])

    # If this schema has a "source" SchemaField, then get or create it.
    try:
        sf = SchemaField.objects.get(schema__id=schema.id, name='source')
    except SchemaField.DoesNotExist:
        source = None
    else:
        try:
            source = Lookup.objects.get(schema_field__id=sf.id, code=source)
        except Lookup.DoesNotExist:
            source = Lookup.objects.create(
                schema_field_id=sf.id,
                name=source,
                code=source,
                slug=slugify(source)[:32],
                description=''
            )
    ni_list = []
    for location, wkt, excerpt, block in data_tuples:
        description = excerpt = excerpt.replace('\n', ' ')
        if source is not None:
            # u'\u2014' is an em dash.
            description = u'%s \u2014 %s' % (source.name, description)
        ni = NewsItem.objects.create(
            schema=schema,
            title=article_headline,
            description=description,
            url=url,
            pub_date=article_date,
            item_date=article_date,
            location=wkt,
            location_name=location,
            block=block,
        )
        atts = {'page_id': page_id, 'excerpt': excerpt}
        if source is not None:
            atts['source'] = source.id
        ni.attributes = atts
        ni_list.append(ni)
    return ni_list

def auto_locations(paragraph_list, default_city=''):
    """
    Given a list of strings, detects all valid, unique addresses and returns a
    tuple (result, report), where result is a list of tuples in the format
    (address, wkt, excerpt, block) and report is a string of what happened.

    If default_city is given, it will be used in the geocoding for detected
    addresses that don't specify a city.
    """
    result, report = [], []
    addresses_seen = set()
    geocoder = SmartGeocoder()
    for para in paragraph_list:
        for addy, city in parse_addresses(para):
            # Skip addresses if they have a city that's a known suburb.
            if city and Suburb.objects.filter(normalized_name=normalize(city)).count():
                report.append('got suburb "%s, %s"' % (addy, city))
                continue

            # Try geocoding the address. If a city was provided, first try
            # geocoding with the city, then fall back to just the address
            # (without the city).
            point = None
            attempts = [addy]
            if default_city:
                attempts.insert(0, '%s, %s' % (addy, default_city))
            if city and city.lower() != default_city.lower():
                attempts.insert(0, '%s, %s' % (addy, city))
            for attempt in attempts:
                try:
                    point = geocoder.geocode(attempt)
                    break
                except AmbiguousResult:
                    report.append('got ambiguous address "%s"' % attempt)
                    # Don't try any other address attempts, because they only
                    # get *more* ambiguous. Plus, the subsequent attempts could
                    # be incorrect. For example, with this:
                    #    addy = '100 Broadway'
                    #    city = 'Manhattan'
                    #    default_city = 'Brooklyn'
                    # There are multiple "100 Broadway" addresses in Manhattan,
                    # so geocoding should fail at this point. It should not
                    # roll back to try the default_city (Brooklyn).
                    break
                except (DoesNotExist, InvalidBlockButValidStreet):
                    report.append('got nonexistent address "%s"' % attempt)
                except ParsingError:
                    report.append('got parsing error "%s"' % attempt)
            if point is None:
                continue # This address could not be geocoded.

            if point['address'] in addresses_seen:
                continue
            if len(para) > 300:
                try:
                    excerpt = smart_excerpt(para, addy)
                except ValueError:
                    excerpt = para
            else:
                excerpt = para
            result.append((addy, point['point'], excerpt, point['block']))
            addresses_seen.add(point['address'])
    return (result, '; '.join(report))

def save_locations_for_ungeocoded_pages():
    for p in Page.objects.filter(when_geocoded__isnull=True).iterator():
        save_locations_for_page(p)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    save_locations_for_ungeocoded_pages()
