"""
Screen scraper for SF public way permits.

There are three retrievers here, corresponding to three schemas.

The data is on an FTP site and is updated daily.
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebgeo.utils.geodjango import make_geomcoll, line_merge
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
from everyblock.cities.sf.models import SfStreet
from everyblock.utils import queryset
from django.utils.text import capfirst
from django.utils import simplejson
import csv
import datetime
import ftplib
import re
from cStringIO import StringIO

FTP_SERVER = 'bsm.sfdpw.org'
FTP_USERNAME = ''
FTP_PASSWORD = ''

remove_leading_zero = lambda x: re.sub(r'^0+', '', x)

VARIOUS = 'Various streets (see map)'

class BasePublicwayScraper(NewsItemListDetailScraper):
    has_detail = False

    def list_pages(self):
        f = StringIO() # This buffer stores the retrieved file in memory.
        self.logger.debug('Connecting via FTP to %s', FTP_SERVER)
        ftp = ftplib.FTP(FTP_SERVER, FTP_USERNAME, FTP_PASSWORD)
        ftp.set_pasv(False) # Turn off passive mode, which is on by default.
        ftp.cwd('/activepermits')
        self.logger.debug('Retrieving file %s', self.ftp_filename)
        ftp.retrbinary('RETR %s' % self.ftp_filename, f.write)
        self.logger.debug('Done downloading')
        f.seek(0)
        ftp.quit() # Note that we quit the connection before scraping starts -- otherwise we get a timeout!
        yield f
        f.close()

    def parse_list(self, csv_file):
        data = csv_file.read()
        csv_file.close()

        # Sometimes the data spans multiple lines without escaping the
        # newline character. In that case, remove the newlines. Note that this
        # regex assumes that EVERY value in the CSV is surrounded by double
        # quotes, which means this can't be used on any CSV.
        data = re.sub(r'([^"\s\\] *)(\r?\n)', r'\1 ', data)

        # The csv data sometimes includes unscaped double quotes, but is formatted
        # as a comma separated and double quoted file. This set of regexes
        # converts it into a tab delimited file with no quoting. This should
        # work in almost every case unless fields actually contain a comma
        # surrounded by double quotes.
        data = re.sub(r'","', r'\t', data)
        data = re.sub(r'"\r\n"', r'\n' , data)
        data = re.sub(r'^"', r'' , data)
        data = re.sub(r'"(?:\r\n)?$', r'' , data)

        csv_file = StringIO(data)

        reader = csv.DictReader(csv_file, self.csv_fieldnames, quoting=csv.QUOTE_NONE, delimiter='\t')
        for row in reader:
            yield row

    def existing_record(self, list_record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            return qs.by_attribute(self.schema_fields['permit_number'], list_record['permit_number'])[0]
        except IndexError:
            return None

class ExcavationPermitScraper(BasePublicwayScraper):
    schema_slugs = ('excavation-permits',)
    ftp_filename = 'excavation.txt'
    # The CSV file contains the fieldnames on the first row:
    #     ("permit_number", "streetname", "Cross Street 1", "Cross Street 2",
    #      "Utility / Contractor", "Permit Reason", "Utility Type",
    #      "Effective Date", "Expiration Date", "Status", "cnn")
    csv_fieldnames = None

    def clean_list_record(self, record):
        record['clean_street_name'] = smart_title(remove_leading_zero(record['streetname']))
        record['clean_cross_1'] = smart_title(remove_leading_zero(record['Cross Street 1'].replace(' \ ', ' / ')))
        record['clean_cross_2'] = smart_title(remove_leading_zero(record['Cross Street 2'].replace(' \ ', ' / ')))
        record['Permit Reason'] = capfirst(record['Permit Reason'].lower()).replace('Cut off service', 'Cut-off service')
        record['Effective Date'] = parse_date(record['Effective Date'], '%Y-%m-%d %H:%M:%S')
        record['Expiration Date'] = parse_date(record['Expiration Date'], '%Y-%m-%d %H:%M:%S')
        return record

    def verbose_detail(self, detail):
        clean_cross_1 = smart_title(detail['cross_street_1'])
        clean_cross_2 = smart_title(detail['cross_street_2'])
        if detail.has_key('street_name'):
            clean_street_name = smart_title(detail['street_name'])
            return '%s from %s to %s' % (clean_street_name, clean_cross_1, clean_cross_2)
        else:
            return 'Intersection of %s and %s' % (clean_cross_1, clean_cross_2)

    def save(self, old_record, list_record, detail_record):
        contractor = self.get_or_create_lookup('utility_contractor', list_record['Utility / Contractor'], list_record['Utility / Contractor'])
        permit_reason = self.get_or_create_lookup('reason', list_record['Permit Reason'], list_record['Permit Reason'])
        item_date = list_record['Effective Date']

        if list_record['Cross Street 2'].lower() in ('intersection', ''):
            detail = {
                'cnn': list_record['cnn'],
                'cross_street_1': list_record['streetname'].upper(),
                'cross_street_2': list_record['clean_cross_1'].upper()
            }
        else:
            detail = {
                'cnn': list_record['cnn'],
                'street_name': list_record['streetname'].upper(),
                'cross_street_1': list_record['clean_cross_1'].upper(),
                'cross_street_2': list_record['clean_cross_2'].upper()
            }

        if old_record is None:
            location_details = {'cnn_list': [], 'details': [detail]}
        else:
            location_details = simplejson.loads(old_record.attributes['location_details'])
            cnn_list = set(location_details['cnn_list'])
            details = location_details['details']

            # pop any old cnn's from cnn_list
            if list_record['cnn'] in cnn_list:
                cnn_list.remove(list_record['cnn'])
            # replace any old detail with the new details
            for i, d in enumerate(details):
                if detail['cross_street_1'] == d['cross_street_1'] and \
                   detail['cross_street_2'] == d['cross_street_2'] and \
                   detail.get('street_name', True) == d.get('street_name', True):
                    del details[i]
                    details.insert(i, detail)
            location_details['cnn_list'] = list(cnn_list)

        streets = set()
        for detail in location_details['details']:
            if detail.has_key('street_name'):
                streets.add(detail['street_name'])
            else:
                streets.add(detail['cross_street_1'])

        location_name = ', '.join([smart_title(street) for street in streets])
        if len(location_name) > 150:
            location_name = VARIOUS

        description = '; '.join([self.verbose_detail(loc) for loc in location_details['details']])

        attributes = {
            'location_details': simplejson.dumps(location_details),
            'permit_number': list_record['permit_number'],
            'reason': permit_reason.id,
            'expiration_date': list_record['Expiration Date'],
            'utility_contractor': contractor.id,
        }
        if old_record is None:
            self.create_newsitem(
                attributes,
                title='%s received permit to %s' % (contractor.name, permit_reason.name.lower()),
                item_date=item_date,
                location=None, # we'll compute this at the end of self.update()
                location_name=location_name,
            )
        else:
            new_values = {'description': description, 'location_name': location_name}
            self.update_existing(old_record, new_values, attributes)

    def set_location(self, ni):
        """
        Calculates and sets the location for this NewsItem from the cnn_list.
        """
        geom_set = []

        location_details = simplejson.loads(ni.attributes['location_details'])

        for cnn in location_details['cnn_list']:
            try:
                geom = SfStreet.objects.get(cnn=cnn).location
            except SfStreet.DoesNotExist:
                pass
            else:
                geom_set.append(geom)

        for detail in location_details['details']:
            # Try using the cnn first, but for some reason the sf streets db
            # doesn't have *every* cnn.
            if detail.has_key('cnn'):
                try:
                    geom = SfStreet.objects.get(cnn=detail['cnn']).location
                except SfStreet.DoesNotExist:
                    pass
                else:
                    geom_set.append(geom)

            # If the cnn wasn't found, and this is an itersection, try getting
            # the location by cross streets.
            else:
                geom = SfStreet.objects.get_intersection(
                    detail['cross_street_1'],
                    detail['cross_street_2']
                )
                if geom:
                    geom_set.append(geom)

        geom = line_merge(make_geomcoll(geom_set))
        if not geom.empty:
            ni.location = geom
        else:
            self.logger.debug('got an empty geometry from list of geoms: %r' % geom_set)

    def update(self):
        super(ExcavationPermitScraper, self).update()
        for start, end, total, qs in queryset.batch(NewsItem.objects.filter(schema=self.schema)):
            self.logger.debug("Updating location for %s - %s of %s" % (start, end, total))
            for ni in qs:
                self.set_location(ni)
                ni.save()

class StreetSpacePermitScraper(BasePublicwayScraper):
    schema_slugs = ('street-space-permits',)
    ftp_filename = 'StreetSpace.txt'
    csv_fieldnames = ('permit_number', 'Address', 'Cross Street 1', 'Cross Street 2', 'Description', 'From Date', 'To Date', 'Linear Feet', 'cnn')

    def clean_list_record(self, record):
        record['From Date'] = parse_date(record['From Date'], '%Y-%m-%d %H:%M:%S')
        record['To Date'] = parse_date(record['To Date'], '%Y-%m-%d %H:%M:%S')
        if record['From Date'] is None and isinstance(record['To Date'], datetime.date):
            record['From Date'] = record['To Date']
        elif record['To Date'] is None and isinstance(record['From Date'], datetime.date):
            record['To Date'] = record['From Date']
        record['Description'] = record['Description'].strip()
        return record

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return # Records don't change, so skip.
        location = SfStreet.objects.get_intersection_by_cnn(list_record['cnn'])
        attributes = {
            'permit_number': list_record['permit_number'],
            'description': list_record['Description'],
            'to_date': list_record['To Date'],
        }
        self.create_newsitem(
            attributes,
            title='Street space permit at %s' % list_record['Address'],
            item_date=list_record['From Date'],
            location=location,
            location_name=list_record['Address'],
        )

STREET_USE_PERMIT_TYPES = {
    'TempOccup': 'Temporary Occupancy',
    'OverwideDr': 'Overwide Driveway',
    'TankRemove': 'Underground Tank Removal',
    'PipeBarr': 'Sidewalk Pipe Barrier',
    'Boring': 'Boring/Monitoring Well',
    'Vault': 'Sidewalk Vault Encroachment',
    'SideSewer': 'Excavation - Side Sewer',
    'ExcStreet': 'General Street Excavation',
    'SpecSide': 'Special Sidewalk Surface',
    'StrtImprov': 'Street Improvement Excavation',
    'MinorEnc': 'Minor Sidewalk Encroachment',
    'minorenc': 'Minor Sidewalk Encroachment',
}

class StreetUsePermitScraper(BasePublicwayScraper):
    schema_slugs = ('street-use-permits',)
    ftp_filename = 'streetuse.txt'
    csv_fieldnames = ('permit_number', 'Location', 'Cross Street 1', 'Cross Street 2', 'Permit Type', 'Agent', 'Permit Purpose', 'Approved Date', 'Status', 'cnn')

    def clean_list_record(self, record):
        record['Approved Date'] = parse_date(record['Approved Date'], '%Y-%m-%d %H:%M:%S')
        record['clean_location'] = smart_title(remove_leading_zero(record['Location'])).strip()
        record['clean_cross_1'] = smart_title(remove_leading_zero(record['Cross Street 1'].replace(' \ ', ' / ')))
        record['clean_cross_2'] = smart_title(remove_leading_zero(record['Cross Street 2'].replace(' \ ', ' / ')))
        record['Agent'] = record['Agent'] and record['Agent'].strip() or 'Unknown agent'
        record['Permit Type'] = record['Permit Type'] or 'N/A'
        try:
            record['Permit Type'] = STREET_USE_PERMIT_TYPES[record['Permit Type']]
        except KeyError:
            pass
        return record

    def save(self, old_record, list_record, detail_record):
        if list_record['Approved Date'] is None:
            return
        agent = self.get_or_create_lookup('agent', list_record['Agent'], list_record['Agent'], make_text_slug=False)
        permit_type = self.get_or_create_lookup('permit_type', list_record['Permit Type'], list_record['Permit Type'], make_text_slug=False)
        item_date = list_record['Approved Date']

        if old_record is None:
            cnn_list = set([list_record['cnn']])
            location_name_list = set([list_record['clean_location']])
        else:
            json = simplejson.loads(old_record.attributes['json'])
            cnn_list = set(json['cnn_list'])
            location_name_list = set(json['locations'])
            if list_record['clean_location'] and list_record['clean_location'] not in location_name_list:
                location_name_list.add(list_record['clean_location'])
            if list_record['cnn'] not in cnn_list:
                cnn_list.add(list_record['cnn'])
        location_name = ', '.join(list(location_name_list))
        if len(location_name) > 150:
            location_name = VARIOUS

        json = simplejson.dumps({
            'cnn_list': [str(cnn) for cnn in list(cnn_list)],
            'purpose': list_record['Permit Purpose'].decode('latin-1'),
            'locations': list(location_name_list)
        })
        attributes = {
            'permit_number': list_record['permit_number'],
            'permit_type': permit_type.id,
            'agent': agent.id,
            'json': json
        }
        if old_record is None:
            self.create_newsitem(
                attributes,
                title='%s received permit for %s' % (agent.name, permit_type.name.lower()),
                item_date=item_date,
                location=None, # we'll compute this at the end of self.update()
                location_name=location_name,
            )
        else:
            new_values = {'location_name': location_name}
            self.update_existing(old_record, new_values, attributes)

    def set_location(self, ni):
        """
        Calculates and sets the location for this NewsItem from the cnn_list.
        """
        geom_set = []
        for cnn in simplejson.loads(ni.attributes['json'])['cnn_list']:
            try:
                geom = SfStreet.objects.get(cnn=cnn).location
            except SfStreet.DoesNotExist:
                pass
            else:
                geom_set.append(geom)

        geom = line_merge(make_geomcoll(geom_set))
        if not geom.empty:
            ni.location = geom
        else:
            self.logger.debug('got an empty geometry from list of geoms: %r' % geom_set)

    def update(self):
        super(StreetUsePermitScraper, self).update()
        for start, end, total, qs in queryset.batch(NewsItem.objects.filter(schema=self.schema)):
            self.logger.debug("Updating location for %s - %s of %s" % (start, end, total))
            for ni in qs:
                self.set_location(ni)
                ni.save()

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    ExcavationPermitScraper().update()
    StreetSpacePermitScraper().update()
    StreetUsePermitScraper().update()
