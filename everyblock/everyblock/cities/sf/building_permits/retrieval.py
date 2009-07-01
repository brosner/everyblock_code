"""
Screen scraper for San Francisco building permits data.
It's the "Building reports filed and issued" link here:
http://www.sfgov.org/site/dbi_page.asp?id=30605
"""

from ebdata.parsing.excel import ExcelDictReader
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from urlparse import urljoin
import os
import re

class PermitScraper(NewsItemListDetailScraper):
    schema_slugs = ('building-permits',)
    has_detail = False

    def __init__(self, month):
        """
        month is a datetime object representing the month to download.
        """
        super(PermitScraper, self).__init__(use_cache=False)
        self.month = month
        self._excel_url_cache = None

    def get_excel_url(self):
        """
        Returns the full URL for the Excel file for self.month.

        This value is cached the first time the function is called.
        """
        if self._excel_url_cache is None:
            # Download the index page and search all of the ".xls" links for
            # the given month/year.
            index_url = 'http://www.sfgov.org/site/dbi_page.asp?id=30608'
            html = self.get_html(index_url)
            excel_links = re.findall(r'<a href="(.*?\.xls)">(.*?)</a>', html)
            month_name, year = self.month.strftime('%B,%Y').split(',')
            this_month_links = [link[0] for link in excel_links if (month_name in link[0] or month_name in link[1]) and (year in link[0] or year in link[1])]
            if len(this_month_links) != 1:
                raise ScraperBroken('Found %s links for %s %s on %s' % (len(this_month_links), month_name, year, index_url))
            self._excel_url_cache = urljoin('http://www.sfgov.org/', this_month_links[0])
        return self._excel_url_cache

    def list_pages(self):
        workbook_path = self.retriever.get_to_file(self.get_excel_url())
        yield ExcelDictReader(workbook_path, sheet_index=0, header_row_num=0, start_row_num=1)
        os.unlink(workbook_path) # Clean up the temporary file.

    def parse_list(self, reader):
        for row in reader:
            yield row

    def clean_list_record(self, record):
        # Normalize inconsistent header names.
        norm_headers = (
            ('FORM_NUMBER', ('FORM_#', 'FORM #')),
            ('APPLICATION #', ('APPLICATION_NUMBER', 'APPLICATION NUMBER', 'APPLICATION NO.', 'APPLICATION NO')),
            ('EXISTING USE', ('EXISTING_USE', 'EXISTINGUSE')),
            ('EXISTING UNITS', ('EXISTING_UNITS', 'EXISTINGUNITS')),
            ('PROPOSED USE', ('PROPOSED_USE', 'PROPOSEDUSE')),
            ('PROPOSED UNITS', ('PROPOSED_UNITS', 'PROPOSEDUNITS')),
        )
        for good_header, bad_headers in norm_headers:
            if good_header not in record:
                for bad_header in bad_headers:
                    if bad_header in record:
                        record[good_header] = record[bad_header]
                        break

        if not str(record['STATUS_DATE']).strip():
            raise SkipRecord
        if not isinstance(record['APPLICATION #'], basestring):
            record['APPLICATION #'] = str(int(record['APPLICATION #']))

        # Drop the '#', if it's in there.
        record['APPLICATION #'] = record['APPLICATION #'].replace('#', '')

        try:
            block = int(record['STREET_NUMBER']) # '12.0' -> '12'
        except ValueError:
            block = record['STREET_NUMBER'] # '12A'
        record['address'] = '%s %s %s' % (block, record['AVS_STREET_NAME'], record['AVS_STREET_SFX'])
        record['existing_units'] = record['EXISTING UNITS'] and int(record['EXISTING UNITS']) or ''
        record['proposed_units'] = record['PROPOSED UNITS'] and int(record['PROPOSED UNITS']) or ''

        # This lookup comes from http://www.sfgov.org/site/uploadedfiles/dbi/reports/ReportLegend.xls
        record['project_type'] = {
            1: 'New construction: Non-wood',
            2: 'New construction: Wood',
            3: 'Additions, alterations or repairs: Major',
            4: 'Erect sign: Erector',
            5: 'Grading, excavation, fill or quarry',
            6: 'Demolition',
            7: 'Erect sign: Wall or painted',
            8: 'Additions, alterations or repairs: Non-major / over the counter',
        }[int(record['FORM_NUMBER'])]
        record['STATUS'] = record['STATUS'].title()
        return record

    def existing_record(self, list_record):
        list_record['status_object'] = self.get_or_create_lookup('status', list_record['STATUS'], list_record['STATUS'])
        lookup = {
            'schema__id': self.schema.id,
            'attribute__%s' % str(self.schema_field_mapping['application_number']): list_record['APPLICATION #'],
            'attribute__%s' % str(self.schema_field_mapping['status']): list_record['status_object'].id,
        }
        try:
            return NewsItem.objects.get(**lookup)
        except NewsItem.DoesNotExist:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            # Records never change, so we don't have to
            # worry about changing ones that already exist.
            self.logger.info('Permit record already exists: %s' % old_record)
            return

        status = list_record['status_object']
        status = self.get_or_create_lookup('status', list_record['STATUS'], list_record['STATUS'])
        project_type = self.get_or_create_lookup('project_type', list_record['project_type'], list_record['project_type'])
        existing_use = self.get_or_create_lookup('existing_use', list_record['EXISTING USE'], list_record['EXISTING USE'])
        proposed_use = self.get_or_create_lookup('proposed_use', list_record['PROPOSED USE'], list_record['PROPOSED USE'])
        title = calculate_title(list_record['APPLICATION #'], status, project_type, existing_use, proposed_use)

        attributes = {
            'application_number': list_record['APPLICATION #'],
            'project_type': project_type.id,
            'file_date': list_record['FILE_DATE'],
            'status': status.id,
            'expiration_date': list_record['EXPIRATION_DATE'] or None,
            'existing_use': existing_use.id,
            'existing_units': list_record['existing_units'],
            'proposed_use': proposed_use.id,
            'proposed_units': list_record['proposed_units'],
            'description': list_record['DESCRIPTION'],
        }
        self.create_newsitem(
            attributes,
            title=title,
            url=self.get_excel_url(),
            item_date=list_record['STATUS_DATE'],
            location_name=list_record['address'],
        )

def calculate_title(application_number, status, project_type, existing_use, proposed_use):
    title = '%s %s: %s' % (application_number, status.name.lower(), project_type.name)
    if project_type.code == 'New construction' and proposed_use.code:
        title += ' of %s' % proposed_use.name
    elif project_type.code == 'Demolition' and existing_use.code:
        title += ' of %s' % existing_use.name
    elif project_type.code == 'Additions, alterations or repairs' and existing_use.code:
        title += ' to %s' % existing_use.name
    return title

def refresh_titles():
    """
    Refreshes the titles of all building-permit NewsItems.

    This is useful if any of the Lookups' values have changed.
    """
    from ebpub.db.models import Lookup
    for ni in NewsItem.objects.filter(schema__slug='building-permits'):
        atts = ni.attributes
        title = calculate_title(atts['application_number'],
            Lookup.objects.get(id=atts['status']),
            Lookup.objects.get(id=atts['project_type']),
            Lookup.objects.get(id=atts['existing_use']),
            Lookup.objects.get(id=atts['proposed_use'])
        )
        if ni.title != title:
            print "%s\n%s\n" % (ni.title, title)
            ni.title = title
            ni.save()
