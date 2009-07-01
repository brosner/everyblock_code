"""
Screen scraper for NYC crime aggregate data
http://www.nyc.gov/html/nypd/html/crime_prevention/crime_statistics.shtml
"""

from ebdata.parsing.pdftotext import pdfstring_to_text
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem, Location
from ebpub.utils.dates import parse_date
import re

PRECINCTS = (
    1, 5, 6, 7, 9, 10, 13, 14, 17, 18, 19, 20, 22, 23, 24, 25, 26, 28, 30, 32,
    33, 34, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 52, 60, 61, 62, 63, 66,
    67, 68, 69, 70, 71, 72, 73, 75, 76, 77, 78, 79, 81, 83, 84, 88, 90, 94,
    100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114,
    115, 120, 122, 123
)

pdf_re = re.compile(r'Report Covering the Week (?:of )?(?P<start_date>\d\d?/\d\d?/\d\d\d\d) Through (?P<end_date>\d\d?/\d\d?/\d\d\d\d).*?Murder Rape Robbery Fel\. Assault Burglary Gr. Larceny G\.L\.A\.\s*(?P<murder>\d+) (?P<rape>\d+) (?P<robbery>\d+) (?P<felony_assault>\d+) (?P<burglary>\d+) (?P<grand_larceny>\d+) (?P<grand_larceny_auto>\d+)', re.DOTALL)

class CrimeScraper(NewsItemListDetailScraper):
    schema_slugs = ("crime",)
    has_detail = False

    def list_pages(self):
        for precinct in PRECINCTS:
            url = 'http://www.nyc.gov/html/nypd/downloads/pdf/crime_statistics/cs%03dpct.pdf' % precinct
            yield precinct, self.get_html(url)

    def parse_list(self, page):
        precinct, raw_pdf = page
        pdf_text = pdfstring_to_text(raw_pdf, keep_layout=False)
        m = pdf_re.search(pdf_text)
        if not m:
            raise ScraperBroken("Didn't find data in PDF for precinct %s" % precinct)
        else:
            yield dict(m.groupdict(), precinct=precinct)

    def clean_list_record(self, record):
        record['start_date'] = parse_date(record['start_date'], '%m/%d/%Y')
        record['end_date'] = parse_date(record['end_date'], '%m/%d/%Y')
        crime_types = ('murder', 'rape', 'robbery', 'felony_assault', 'burglary', 'grand_larceny', 'grand_larceny_auto')
        for key in crime_types:
            record[key] = int(record[key])
        record['total'] = sum([record[key] for key in crime_types])
        return record

    def existing_record(self, record):
        record['precinct_obj'] = self.get_or_create_lookup('precinct', 'Precinct %s' % record['precinct'], record['precinct'])
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['start_date'])
            qs = qs.by_attribute(self.schema_fields['precinct'], record['precinct_obj'].id)
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            # This data never changes, so we don't have to
            # worry about changing data that already exists.
            self.logger.debug('Data already exists')
            return

        num_crimes = list_record['total'] == 0 and 'No' or list_record['total']
        newsitem_title = '%s crime%s reported in Precinct %s' % (num_crimes, list_record['total'] != 1 and 's' or '', list_record['precinct'])
        location_object = Location.objects.get(location_type__slug='police-precincts', slug=list_record['precinct'])

        attributes = {
            'end_date': list_record['end_date'],
            'precinct': list_record['precinct_obj'].id,
            'murder': list_record['murder'],
            'rape': list_record['rape'],
            'robbery': list_record['robbery'],
            'felony_assault': list_record['felony_assault'],
            'burglary': list_record['burglary'],
            'grand_larceny': list_record['grand_larceny'],
            'grand_larceny_auto': list_record['grand_larceny_auto'],
        }
        self.create_newsitem(
            attributes,
            title=newsitem_title,
            item_date=list_record['start_date'],
            location=location_object.location,
            location_name='Precinct %s' % list_record['precinct'],
            location_object=location_object,
        )

class ArchivedCrimeScraper(CrimeScraper):
    """
    A scraper that gets its data from archived PDF files off the local
    filesystem. This is useful for loading backdated data.
    """
    def __init__(self, dir_name):
        super(ArchivedCrimeScraper, self).__init__()
        self.dir_name = dir_name

    def list_pages(self):
        import os
        for precinct in PRECINCTS:
            filename = os.path.join(self.dir_name, 'cs%03dpct.pdf' % precinct)
            yield precinct, open(filename).read()

if __name__ == "__main__":
    s = CrimeScraper()
    s.update()
