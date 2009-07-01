"""
Scraper for Dallas crime.
http://66.97.146.94/dpdpublic/offense.aspx
ftp://66.97.146.94/
"""

from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.streets.models import Street
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title, address_to_block
from cStringIO import StringIO
from decimal import Decimal
from lxml import etree
from ucrmapping import CATEGORY_MAPPING, UCR_MAPPING # relative import
import datetime
import zipfile
import ftplib
import time
import re

FTP_SERVER = '66.97.146.94'
FTP_USERNAME = ''
FTP_PASSWORD = ''

# UCR prefixes of things like attempted suidicide that we shouldn't publish.
SKIPPED_UCR_PREFIXES = [
    '38', # suicide
    '39', # attempted suicide
]

class StreetNormalizer(object):
    def __init__(self):
        # Store a mapping of condensed and normalized street names to street
        # names that are in our database. We use this to look up actual street
        # names since they come to us stripped of any internal spaces.
        self.streets = {}
        for street in Street.objects.values('street'):
            street_name = street['street']
            normalized_name = re.sub(r'\s+', '', street_name.upper())
            self.streets[normalized_name] = street_name
        self.records_seen = 0
        self.matches_found = 0

    def print_stats(self):
        pct_normalized = Decimal(self.matches_found) / Decimal(self.records_seen)
        print "Normalized %s out of %s addresses. (%s%%)" % (self.matches_found, self.records_seen, pct_normalized)

    def normalize_address(self, record):
        """
        Addresses are provided with no spaces, so try to find the suffix if
        there is one, then compare the reamining part to the streets table.
        """
        if record['offensestreet'] is None:
            raise SkipRecord('Skipping record with no street')

        street = record['offensestreet']
        matching_suffix = ''

        suffix_groups = [
            ('EXPWY', 'PKWY', 'FRWY', 'BLVD'),
            ('HWY', 'FRW', 'AVE', 'CIR', 'EXT', 'BLV', 'PKW', 'ROW', 'WAY', 'EXP'),
            ('DR', 'ST', 'RD', 'LN', 'BL', 'TR', 'WY', 'CT', 'PL', 'AV', 'CI'),
            ('P', 'R', 'F', 'D', 'S', 'L')
        ]

        match_found = False
        for group in suffix_groups:
            if match_found:
                break
            for suffix in group:
                if record['offensestreet'].endswith(suffix):
                    street_name = record['offensestreet'][:-len(suffix)]
                    # Try looking up the street name from a dictionary mapping
                    # collapsed street names to names in the streets table.
                    try:
                        street = self.streets[street_name]
                        matching_suffix = suffix
                        match_found = True
                        break
                    except KeyError:
                        # SAINT is encoded as ST in the data, but Saint in the streets table,
                        # so try that if the address starts with ST.
                        if street_name.startswith('ST'):
                            street_name = 'SAINT%s' % street_name[2:]
                            try:
                                street = self.streets[street_name]
                                matching_suffix = suffix
                                match_found = True
                                break
                            except KeyError:
                                continue

        if match_found:
            self.matches_found += 1
        self.records_seen += 1

        normalized_block = record['offenseblock'].lstrip('0')
        if normalized_block[-2:] == 'xx':
            normalized_block = normalized_block.replace('xx', '00')
        address = '%s %s %s %s' % (
            normalized_block, record['offensedirection'] or '', street, matching_suffix
        )
        address = re.sub(r'\s+', ' ', address)
        return address_to_block(address)

class BaseScraper(NewsItemListDetailScraper):
    schema_slugs = ('crime-reports',)
    has_detail = False
    def __init__(self, filename=None, get_all=False):
        super(BaseScraper, self).__init__(self)
        self.filename = filename
        self.get_all = get_all

    def retrieve_file(self, date):
        yesterday = datetime.date.today() - datetime.timedelta(days=1)
        ftp_filename = self.filename_pattern % (date.month, date.day, date.year)
        f = StringIO() # This buffer stores the retrieved file in memory.
        self.logger.debug('Connecting via FTP to %s', FTP_SERVER)
        ftp = ftplib.FTP(FTP_SERVER, FTP_USERNAME, FTP_PASSWORD)
        ftp.set_pasv(False)
        if date.year != yesterday.year or date.month != yesterday.month:
            dirname = date.strftime('/%Y/%B/')
            self.logger.debug('Changing to %s' % dirname)
            ftp.cwd(dirname)
        self.logger.debug('Retrieving file %s', ftp_filename)
        try:
            ftp.retrbinary('RETR %s' % ftp_filename, f.write)
        except ftplib.error_perm:
            self.logger.warn("Couldn't find file %s" % ftp_filename)
            return None
        ftp.quit()
        self.logger.debug('Done downloading')
        f.seek(0)
        return f

    def list_pages(self):
        if self.filename is None and self.get_all:
            date = datetime.date(2009, 1, 31)
            while 1:
                date = date + datetime.timedelta(days=1)
                if date == datetime.date.today():
                    break
                f = self.retrieve_file(date)
                if f is None:
                    continue
                zf = zipfile.ZipFile(f, 'r')
                xml_filename = zf.namelist()[0]
                yield StringIO(zf.read(xml_filename))
                zf.close()
                f.close()
        elif self.filename is None:
            date = datetime.date.today() - datetime.timedelta(days=1)
            f = self.retrieve_file(date)
            zf = zipfile.ZipFile(f, 'r')
            xml_filename = zf.namelist()[0]
            yield StringIO(zf.read(xml_filename))
            zf.close()
            f.close()
        else:
            f = open(self.filename, 'r')
            zf = zipfile.ZipFile(f, 'r')
            xml_filename = zf.namelist()[0]
            yield StringIO(zf.read(xml_filename))
            zf.close()
            f.close()

    def parse_list(self, xml_file):
        tree = etree.parse(xml_file)
        for record_element in tree.xpath('/NewDataSet/Record'):
            record = {}
            for element in record_element:
                record[element.tag] = element.text
            yield record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['offensedate'])
            return qs.by_attribute(self.schema_fields['service_number'], record['offenseservicenumber'])[0]
        except IndexError:
            return None

class OffenseScraper(BaseScraper):
    filename_pattern = 'OFFENSE_%s_%s_%s.zip'

    def __init__(self, *args, **kwargs):
        super(OffenseScraper, self).__init__(*args, **kwargs)
        self.normalizer = StreetNormalizer()

    def clean_list_record(self, record):
        # Get the first 2 digits of the UCR, or None.
        ucr1_prefix = record['offenseucr1'] and record['offenseucr1'][:2] or None
        ucr2_prefix = record['offenseucr2'] and record['offenseucr2'][:2] or None

        if ucr1_prefix in SKIPPED_UCR_PREFIXES:
            raise SkipRecord('Skipping record with UCR %s' % record['offenseucr1'])
        if ucr2_prefix in SKIPPED_UCR_PREFIXES:
            raise SkipRecord('Skipping record with UCR %s' % record['offenseucr2'])

        record['address'] = self.normalizer.normalize_address(record)

        # If we can't find the code in the mapping, just use the code itself
        # as the value.
        record['category'] = CATEGORY_MAPPING.get(ucr1_prefix, ucr1_prefix)
        record['crime_type'] = UCR_MAPPING.get(record['offenseucr1'], record['offenseucr1'])
        record['secondary_category'] = CATEGORY_MAPPING.get(ucr2_prefix, ucr2_prefix)
        record['secondary_crime_type'] = UCR_MAPPING.get(record['offenseucr2'], record['offenseucr2'])

        record['offensedate'] = parse_date(record['offensedate'], '%m/%d/%Y')
        record['offensestarttime'] = datetime.time(*time.strptime(record['offensestarttime'], '%H:%M:%S')[3:5])
        record['offensebeat'] = record['offensebeat'] or ''
        return record

    def save(self, old_record, list_record, detail_record):
        category = self.get_or_create_lookup('category', list_record['category'], list_record['category'], make_text_slug=False)
        secondary_category = self.get_or_create_lookup('secondary_category', list_record['secondary_category'], list_record['secondary_category'], make_text_slug=False)
        beat = self.get_or_create_lookup('beat', list_record['offensebeat'], list_record['offensebeat'], make_text_slug=False)
        premises = self.get_or_create_lookup('premises', list_record['offensepremises'], list_record['offensepremises'], make_text_slug=False)
        crime_type = self.get_or_create_lookup('crime_type', list_record['crime_type'], list_record['crime_type'], make_text_slug=False)
        secondary_crime_type = self.get_or_create_lookup('secondary_crime_type', list_record['secondary_crime_type'], list_record['secondary_crime_type'], make_text_slug=False)

        kwargs = {
            'title': smart_title(list_record['offensedescription']),
            'item_date': list_record['offensedate'],
            'location_name': list_record['address']
        }
        attributes = {
            'category': category.id,
            'secondary_category': secondary_category.id,
            'service_number': list_record['offenseservicenumber'],
            'offense_time': list_record['offensestarttime'],
            'description': list_record['offensedescription'],
            'beat': beat.id,
            'premises': premises.id,
            'crime_type': crime_type.id,
            'secondary_crime_type': secondary_crime_type.id,
            'method': list_record['offensemethodofoffense'],
            # street is block;direction;street
            # This will allow us to reprocess the original data when we
            # improve the address normalizer.
            'street': ';'.join((list_record['offenseblock'] or '', list_record['offensedirection'] or '', list_record['offensestreet'] or '')),
            'ucr': ';'.join((list_record['offenseucr1'] or '', list_record['offenseucr2'] or ''))
        }
        if old_record is None:
            self.create_newsitem(attributes, **kwargs)
        else:
            self.update_existing(old_record, kwargs, attributes)

class NarrativeScraper(BaseScraper):
    filename_pattern = 'OFFENSENARRATIVE_%s_%s_%s.zip'

    def clean_list_record(self, record):
        record['offensedate'] = parse_date(record['offensedate'], '%m/%d/%Y')
        if record['offensenarrative'] is not None:
            record['offensenarrative'] = record['offensenarrative'].strip()
        return record

    def save(self, old_record, list_record, detail_record):
        # We're updating existing records, so if there isn't one, skip.
        if old_record is None:
            return
        attributes = {'narrative': list_record['offensenarrative']}
        self.update_existing(old_record, {}, attributes)

def update():
    os = OffenseScraper()
    ns = NarrativeScraper()
    os.update()
    ns.update()

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    os = OffenseScraper()
    ns = NarrativeScraper()
    os.update()
    ns.update()
    os.normalizer.print_stats()
