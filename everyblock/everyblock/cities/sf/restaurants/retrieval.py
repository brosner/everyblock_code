"""
Screen scraper for SF restaurant data
https://dph-tumble1.sfdph.org/
Username and password are in the code below.

This data is provided via Microsoft Access files behind a password-protected
file-administration interface, so the two interesting tasks with this scraper
are to screen-scrape that interface and parse the Access file.
"""

from ebdata.parsing.mdb import TableReader
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import re
import urlparse

USERNAME = ''
PASSWORD = ''
ENCODING = 'iso-8859-1' # Encoding of the data in the MDB file.
FILE_MANAGER_URL = 'https://dph-tumble1.sfdph.org/'

class RestaurantScraper(NewsItemListDetailScraper):
    schema_slugs = ('restaurant-inspections',)
    has_detail = False

    def __init__(self, mdb_filename=None):
        # If mdb_filename is given, it should be the name of an MDB file on the
        # local filesystem to import. Otherwise, this will try to find the
        # latest one available online.
        NewsItemListDetailScraper.__init__(self)
        self._local_mdb_filename = mdb_filename
        self._mdb_filename = None
        self._locations_cache = self._inspection_type_cache = self._violations_cache = self._violation_type_cache = None

    def mdb_filename(self):
        """
        Lazily loads the MDB filename so it's only done once per scraper
        instance.
        """
        if self._mdb_filename is None:
            if self._local_mdb_filename is None:
                self._mdb_filename = self.get_access_db()
            else:
                self._mdb_filename = self._local_mdb_filename
        return self._mdb_filename

    def locations(self):
        """
        Lazily loads *all* locations into memory and returns a dictionary
        keyed by location ID.
        """
        if self._locations_cache is None:
            self._locations_cache = dict([(row['LocationID'], row) for row in self.mdb_table('tblLocations')])
            if not self._locations_cache:
                raise ScraperBroken('tblLocations was either empty or nonexistent')
        return self._locations_cache

    def inspection_types(self):
        """
        Lazily loads *all* inspection types into memory and returns a dictionary
        keyed by inspection type ID.
        """
        if self._inspection_type_cache is None:
            self._inspection_type_cache = dict([(row['InspectionTypeID'], row) for row in self.mdb_table('tblInspectionTypes')])
            if not self._inspection_type_cache:
                raise ScraperBroken('tblInspectionTypes was either empty or nonexistent')
        return self._inspection_type_cache

    def violations(self):
        """
        Lazily loads *all* violations into memory and returns a dictionary
        keyed by inspection ID.
        """
        if self._violations_cache is None:
            vs = {}
            for row in self.mdb_table('tblViolations'):
                vs.setdefault(row['InspectionID'], []).append(row)
            self._violations_cache = vs
            if not self._violations_cache:
                raise ScraperBroken('tblViolations was either empty or nonexistent')
        return self._violations_cache

    def violation_types(self):
        """
        Lazily loads *all* violation types into memory and returns a dictionary
        keyed by violation type ID.
        """
        if self._violation_type_cache is None:
            self._violation_type_cache = dict([(row['ViolationTypeID'], row) for row in self.mdb_table('tblViolationTypes')])
            if not self._violation_type_cache:
                raise ScraperBroken('tblViolationTypes was either empty or nonexistent')
        return self._violation_type_cache

    def mdb_table(self, table_name):
        "Returns a TableReader instance for the given table name."
        return TableReader(self.mdb_filename(), table_name)

    def get_access_db(self, file_date=None):
        """
        Downloads the requested Microsoft Access file, saves it to a temporary
        file and returns the local file name.

        If file_date is None, then this will download the latest Access file.
        Otherwise, it will download the file with the given date, raising
        ScraperBroken if a file isn't available for that date.
        """
        # First, log into the file manager and get the list of all available
        # Microsoft Access (MDB) files.
        params = {'user': USERNAME, 'password': PASSWORD, 'start-url': '/', 'switch': 'Log In'}
        html = self.get_html(FILE_MANAGER_URL, params)
        mdb_files = re.findall(r'PrintFileURL\("(.*?\.mdb)"', html)
        if not mdb_files:
            raise ScraperBroken('Found no MDB files')
        mdb_files.sort()

        if file_date:
            requested_file = 'SFFOOD%s.mdb' % file_date.strftime('%m%d%Y')
            if requested_file not in mdb_files:
                raise ScraperBroken('%r not found. Choices are: %r' % (requested_file, mdb_files))
        else:
            # Assume the last filename in alphabetical order is the latest one.
            requested_file = mdb_files[-1]

        # Finally, download the file and return the local filename.
        mdb_url = urlparse.urljoin(FILE_MANAGER_URL, requested_file)
        filename = self.retriever.get_to_file(mdb_url)
        self.logger.debug('%s saved to %s', mdb_url, filename)
        return filename

    def list_pages(self):
        for row in self.mdb_table('tblInspections'):
            yield row

    def parse_list(self, row):
        yield row # It's already a dictionary, so just yield it.

    def clean_list_record(self, record):
        record['DateOfInspection'] = parse_date(record['DateOfInspection'], '%Y-%m-%d')
        if not record['DateOfInspection']:
            raise SkipRecord('Inspection date not given')
        record['Total Time'] = record['Total Time'].strip() or None
        record['EmployeeIDofInspector'] = record['EmployeeIDofInspector'].strip() or None

        # Calculate the score range.
        record['Score'] = record['Score'].strip() or None
        if record['Score']:
            try:
                record['Score'] = int(record['Score'])
            except ValueError:
                raise SkipRecord('Got sketchy non-integer score %r' % record['Score'])
            if record['Score'] >= 91:
                record['score_range'] = '91-100'
            elif record['Score'] >= 81:
                record['score_range'] = '81-90'
            elif record['Score'] >= 71:
                record['score_range'] = '71-80'
            elif record['Score'] >= 61:
                record['score_range'] = '61-70'
            elif record['Score'] >= 51:
                record['score_range'] = '51-60'
            elif record['Score'] >= 41:
                record['score_range'] = '41-50'
            elif record['Score'] >= 31:
                record['score_range'] = '31-40'
            elif record['Score'] >= 21:
                record['score_range'] = '21-30'
            elif record['Score'] >= 11:
                record['score_range'] = '11-20'
            else:
                record['score_range'] = '0-10'
        else:
            record['score_range'] = 'N/A'

        # Get the location data from the locations table.
        try:
            loc = self.locations()[record['LocationIDInspected']]
        except KeyError:
            raise SkipRecord('Location not found')
        # Explicitly convert to a Unicode object using the utf8 codec, because
        # this might contain funky characters.
        record['restaurant_dba'] = loc['DBA'].decode('utf8').strip()
        record['restaurant_type'] = loc['Type Description'].strip()
        record['address'] = loc['StreetAddress'].decode('utf8').strip()
        record['LocationIDInspected'] = int(record['LocationIDInspected'])

        # Get the inspection type data from the inspection types table.
        try:
            inspection_type = self.inspection_types()[record['InspectionTypeID']]
        except KeyError:
            raise SkipRecord('Inspection type not found')
        record['inspection_type'] = inspection_type['InspectionType']

        # Get the violation data from the violations table.
        try:
            vios = self.violations()[record['InspectionID']]
        except KeyError:
            record['violations'] = []
        else:
            vio_types = self.violation_types()
            record['violations'] = [dict(vio, type=vio_types[vio['ViolationTypeID']]) for vio in vios]

        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['inspection_id'], record['InspectionID'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        restaurant_type = self.get_or_create_lookup('restaurant_type', list_record['restaurant_type'], list_record['restaurant_type'], make_text_slug=False)
        inspection_type = self.get_or_create_lookup('inspection_type', list_record['inspection_type'], list_record['inspection_type'])
        score_range = self.get_or_create_lookup('score_range', list_record['score_range'], list_record['score_range'])
        violations = [self.get_or_create_lookup('violation', v['type']['ViolationType'], v['type']['ViolationType']) for v in list_record['violations']]
        violations_text = ','.join([str(v.id) for v in violations])
        item_date = list_record['DateOfInspection']
        title = u'%s inspection at %s' % (inspection_type.name, list_record['restaurant_dba'])

        # Create the notes by appending the violation-specific notes to the
        # inspection notes.
        notes = list_record['InspectionNotes'].decode('utf8')
        for vio in list_record['violations']:
            if vio['ViolationNotes'].strip():
                notes += u'\n\nNote on "%s" violation: %s' % (vio['type']['ViolationType'].decode('utf8').strip(), vio['ViolationNotes'].decode('utf8').strip())
        notes = notes.strip()

        new_attributes = {
            'inspection_id': list_record['InspectionID'],
            'total_time': list_record['Total Time'],
            'inspector': list_record['EmployeeIDofInspector'],
            'location': list_record['LocationIDInspected'],
            'restaurant_dba': list_record['restaurant_dba'],
            'restaurant_type': restaurant_type.id,
            'inspection_type': inspection_type.id,
            'violation': violations_text,
            'score': list_record['Score'],
            'score_range': score_range.id,
            'notes': notes,
        }

        if old_record is None:
            self.create_newsitem(
                new_attributes,
                title=title,
                item_date=item_date,
                location_name=list_record['address'],
            )
        else:
            # This already exists in our database, but check whether any
            # of the values have changed.
            new_values = {'title': title, 'item_date': item_date, 'location_name': list_record['address']}
            self.update_existing(old_record, new_values, new_attributes)

class CsvRestaurantScraper(RestaurantScraper):
    """
    A RestaurantScraper that gets its data from a directory of CSV files
    instead of an MDB file.

    This is useful for development in an environment that doesn't have
    mdbtools.

    CsvRestaurantScraper.__init__() takes a directory name. This directory
    must contain a CSV file for every table in the MDB file you're trying to
    emulate, named 'TABLENAME.txt'.
    """
    def __init__(self, mdb_directory):
        RestaurantScraper.__init__(self)
        self.mdb_directory = mdb_directory

    def mdb_table(self, table_name):
        "Returns a TableReader instance for the given table name."
        import csv
        import os.path
        csv_name = os.path.join(self.mdb_directory, table_name + '.txt')
        return csv.DictReader(open(csv_name))

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    RestaurantScraper().update()
