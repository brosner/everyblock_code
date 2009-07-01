"""
Import script for Chicago film locations data.

This data is imported from a CSV file, which is generated from an Excel file
that the film office sends us.

IMPORTANT NOTE: The script doesn't check whether a filming exists in the
database yet, so ensure that you don't import the same data twice.
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.utils.dates import parse_date
from ebpub.utils.text import smart_title
from csv import DictReader

class FilmingImporter(NewsItemListDetailScraper):
    schema_slugs = ("filmings",)
    has_detail = False

    def __init__(self, csvfile, *args, **kwargs):
        super(FilmingImporter, self).__init__(*args, **kwargs)
        self.csvfile = csvfile

    def list_pages(self):
        return [DictReader(self.csvfile)]

    def parse_list(self, reader):
        for row in reader:
            yield row

    def clean_list_record(self, record):
        try:
            record['Date'] = parse_date(record['Date'], '%m/%d/%Y') # 12/31/2007
        except ValueError:
            record['Date'] = parse_date(record['Date'], '%m/%d/%y') # 12/31/07
        for key in ('Location', 'Notes', 'Title', 'Type'):
            if key in record and record[key]:
                record[key] = record[key].strip()
            else:
                record[key] = ''

        record['Location'] = smart_title(record['Location'])
        record['Title'] = smart_title(record['Title'])

        # This is temporary! The CSV files we get are inconsistent -- sometimes
        # they're only films and don't have a "Type" field.
        if record['Type'] == '':
            record['Type'] = 'Film'

        # Normalize inconsistent data.
        if record['Type'] in ('Stills', 'Still'):
            record['Type'] = 'Still photography'
        if record['Type'] in ('Fim', 'Movie'):
            record['Type'] = 'Film'

        return record

    def existing_record(self, record):
        # Assume that none of this data exists in the database yet.
        return None

    def save(self, old_record, list_record, detail_record):
        filming_type = self.get_or_create_lookup('type', list_record['Type'], list_record['Type'])
        film_title = self.get_or_create_lookup('title', list_record['Title'], list_record['Title'])
        newsitem_title = u'%s "%s" filmed' % (filming_type.name, list_record['Title'])
        attributes = {
            'title': film_title.id,
            'type': filming_type.id,
            'notes': list_record['Notes'],
        }
        self.create_newsitem(
            attributes,
            title=newsitem_title,
            item_date=list_record['Date'],
            location_name=list_record['Location'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    import sys
    filename = sys.argv[1]
    importer = FilmingImporter(open(filename, 'rb'))
    importer.update()
