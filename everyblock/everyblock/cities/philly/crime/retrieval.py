"""
Screen scraper for Philadelphia crime data.
http://citymaps.phila.gov/CrimeMap/
"""

from django.contrib.gis.gdal import OGRGeometry
from django.contrib.gis.gdal.srs import SpatialReference
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
from cStringIO import StringIO
import csv
import datetime
import time

# The SRS of the crime data, Pennsylvania State Plane South, isn't one
# that is part of the set of SRSes that come with PostGIS, so we
# define it here
SRS_WKT = """\
PROJCS["NAD_1983_StatePlane_Pennsylvania_South_FIPS_3702_Feet",
    GEOGCS["GCS_North_American_1983",
        DATUM["North_American_Datum_1983",
            SPHEROID["GRS_1980",6378137,298.257222101]],
        PRIMEM["Greenwich",0],
        UNIT["Degree",0.017453292519943295]],
    PROJECTION["Lambert_Conformal_Conic_2SP"],
    PARAMETER["False_Easting",1968500],
    PARAMETER["False_Northing",0],
    PARAMETER["Central_Meridian",-77.75],
    PARAMETER["Standard_Parallel_1",39.93333333333333],
    PARAMETER["Standard_Parallel_2",40.96666666666667],
    PARAMETER["Latitude_Of_Origin",39.33333333333334],
    UNIT["Foot_US",0.30480060960121924],
    AUTHORITY["EPSG","102729"]]"""
srs = SpatialReference(SRS_WKT)

class CrimeScraper(NewsItemListDetailScraper):
    schema_slugs = ('crime',)
    has_detail = False

    def __init__(self, start_date=None, end_date=None):
        super(CrimeScraper, self).__init__()
        self.start_date, self.end_date = start_date, end_date

    def list_pages(self):
        # Yields CSV documents
        for crime_type in (10, 11, 12, 13, 20, 30, 31, 32, 40, 41, 42, 50, 51, 52, 53, 54, 60, 61, 62, 63, 64, 65, 66, 67, 70, 71, 72):
            url = 'http://citymaps.phila.gov/CrimeMap/ExportCSV.aspx?crimetype=%s&from=%s&to=%s&bounds=2468450%%2C158500%%2C2941550%%2C348500' % \
                (crime_type, self.start_date.strftime('%m/%d/%Y'), self.end_date.strftime('%m/%d/%Y'))
            yield self.get_html(url)
            time.sleep(10) # Be nice to their servers.

    def parse_list(self, text):
        reader = csv.DictReader(StringIO(text))
        for row in reader:
            yield row

    def clean_list_record(self, record):
        dispatch_datetime = parse_date(record['DISPATCH_DATE_TIME'], '%m/%d/%Y %I:%M:%S %p', return_datetime=True)
        record['dispatch_date'] = dispatch_datetime.date()
        record['dispatch_time'] = dispatch_datetime.time()
        record['LOCATION'] = smart_title(record['LOCATION'])
        # Convert '531 - Burglary: Day; No Force: Prvt. Residence' to 'Burglary'.
        record['primary_type'] = record['UCR_TEXT'].split(':')[0].split(' - ')[1].title()

        # Clean up an inconsistency.
        if record['primary_type'] == 'Auto Theft':
            record['primary_type'] = 'Vehicle Theft'

        record['X_COORD'] = float(record['X_COORD'])
        record['Y_COORD'] = float(record['Y_COORD'])
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['dc_key'], record['DC_KEY'])
            return qs[0]
        except IndexError:
            return None

    def get_geom(self, list_record):
        ogrgeom = OGRGeometry('POINT(%s %s)' % (list_record['X_COORD'], list_record['Y_COORD']), srs)
        ogrgeom.transform(4326)
        return ogrgeom.geos

    def save(self, old_record, list_record, detail_record):
        premise = self.get_or_create_lookup('premise', list_record['PREMISE_TEXT'], list_record['PREMISE_TEXT'])
        sector = self.get_or_create_lookup('sector', list_record['SECTOR'], list_record['SECTOR'])
        primary_type = self.get_or_create_lookup('primary_type', list_record['primary_type'], list_record['primary_type'], make_text_slug=True)
        secondary_type = self.get_or_create_lookup('secondary_type', list_record['UCR_TEXT'], list_record['UCR_TEXT'], make_text_slug=False)
        attributes = {
            'dc_key': list_record['DC_KEY'],
            'premise': premise.id,
            'sector': sector.id,
            'primary_type': primary_type.id,
            'secondary_type': secondary_type.id,
            'xy': '%s;%s' % (list_record['X_COORD'], list_record['Y_COORD']),
            'dispatch_time': list_record['dispatch_time'],
        }
        if old_record is None:
            self.create_newsitem(
                attributes,
                title=secondary_type.name,
                item_date=list_record['dispatch_date'],
                location=self.get_geom(list_record),
                location_name=list_record['LOCATION'],
            )
        else:
            new_values = {'title': secondary_type.name, 'item_date': list_record['dispatch_date'], 'location_name': list_record['LOCATION']}
            self.update_existing(old_record, new_values, attributes)

def update_latest():
    # Do three 14-day chunks, instead of a single 50-day chunk, because the
    # police site has a limit of 500 records per result. We don't want to risk
    # not getting all of the data for a given date range.
    today = datetime.date.today()
    CrimeScraper(today - datetime.timedelta(days=14), today).update()
    CrimeScraper(today - datetime.timedelta(days=30), today - datetime.timedelta(days=15)).update()
    CrimeScraper(today - datetime.timedelta(days=46), today - datetime.timedelta(days=31)).update()

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    update_latest()
