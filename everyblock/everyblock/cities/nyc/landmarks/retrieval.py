"""
Screen scraper for NYC Landmarks Preservation Commission data, as found on
citylaw.org.

To replicate what this scraper does, go here:
   http://www.nyls.edu/centers/harlan_scholar_centers/center_for_new_york_city_law/cityadmin_library/

Check the "LANDMARKS" checkbox, then enter "cofa" in the search keywords box
and click "Search." Each resulting PDF is converted to text and parsed with a
regex.
"""

from ebdata.parsing.pdftotext import pdfstring_to_text
from ebdata.retrieval.scrapers.list_detail import StopScraping, SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import re
import urlparse

issued_re = re.compile('(?s)^ISSUED TO:.*?\n\n')

class LandmarkScraper(NewsItemListDetailScraper):
    schema_slugs = ('landmark-building-permits',)
    parse_list_re = re.compile(r'<a href="http://archive\.citylaw\.org/lpc/permit/(?P<pdf_year>\d{4})/(?P<pdf_id>\d+).pdf" target="_blank">(?P<link_text>.*?)</a>', re.DOTALL)
    parse_detail_re = re.compile(r'CERTIFICATE OF APPROPRIATENESS\n\s+ISSUE DATE:\s{5,}EXPIRATION DATE:\s{5,}DOCKET #:\s{5,}COFA #:\n+\s+(?P<issue_date>\d\d?/\d\d?/\d\d\d\d)\s{5,}(?P<expiration_date>\d\d?/\d\d?/\d\d\d\d)?\s{5,}(?P<docket>[-\d]+)\s{5,}(?P<cofa>COFA [-\d]+)\n+\s+ADDRESS\s{5,}BOROUGH:\s{5,}BLOCK/LOT:\n+\s+(?P<address>.*?)\n+\s+(?P<district_or_landmark>HISTORIC DISTRICT|INDIVIDUAL LANDMARK|INTERIOR LANDMARK)\n\s+(?P<historic_district>.*?)\s{5,}(?P<borough>.*?)\s{5,}\d+/\d+\n(?P<second_line_of_district>[^\n]*?)\n\n\s*(?P<text>.+)\s*$', re.DOTALL)

    def list_pages(self):
        # This relies on a subsequent part of the scraper to raise StopScraping.
        start = 0
        while 1:
            params = '?sort=date%%3AD%%3AS%%3Ad1&num=10&q=cofa&site=cl_lpc&start=%s' % start
            page_url = urlparse.urljoin('http://www.nyls.edu/centers/harlan_scholar_centers/center_for_new_york_city_law/cityadmin_library/', params)
            yield self.get_html(page_url)
            start += 10

    def clean_list_record(self, record):
        record['pdf_url'] = 'http://archive.citylaw.org/lpc/permit/%s/%s.pdf' % (record['pdf_year'], record['pdf_id'])
        return record

    def existing_record(self, record):
        # We can't determine whether there's an existing record until we see
        # list_record, so this decision is deferred until clean_detail_record().
        return None

    def detail_required(self, list_record, old_record):
        return True

    def get_detail(self, record):
        # Save the URL so that we can refer to it from parse_detail().
        self.__current_url = record['pdf_url']
        return self.get_html(record['pdf_url'])

    def parse_detail(self, page, list_record):
        text = pdfstring_to_text(page)
        m = self.parse_detail_re.search(text)
        if m:
            self.logger.debug('Got a match for parse_detail_re')
            return m.groupdict()
        else:
            self.logger.warning("Regex failed on %s", self.__current_url)
            raise SkipRecord

    def clean_detail_record(self, record):
        record['expiration_date'] = parse_date(record['expiration_date'], '%m/%d/%Y')
        record['issue_date'] = parse_date(record['issue_date'], '%m/%d/%Y')

        # The PDF text is in the ISO-8859-1 encoding. Convert it here so that
        # we don't get an encoding error when we save it to the database.
        record['text'] = record['text'].decode('iso-8859-1')
        record['text'] = record['text'].replace('Display This Permit While Work Is In Progress', '')
        record['text'] = record['text'].strip()

        # Remove the "ISSUED TO" section, as it contains the name of the person
        # who owns the property, and we have a policy of not displaying names.
        # Note that we include a sanity check that the "ISSUED TO" section
        # doesn't contain more than 9 newlines, as that would signify a broken
        # regular expression.
        m = issued_re.search(record['text'])
        if m and m.group(0).count('\n') < 10:
            record['text'] = issued_re.sub('', record['text'])

        if record['second_line_of_district'].strip():
            record['historic_district'] += record['second_line_of_district']

        if record['district_or_landmark'] == 'HISTORIC DISTRICT':
            record['landmark'] = 'N/A'
        else:
            record['landmark'] = record['historic_district']
            record['historic_district'] = 'N/A'

        # Check for a duplicate record. Because the scraper works in
        # reverse-chronological order, we can safely raise StopScraping if we
        # reach a duplicate.
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id)
            qs = qs.by_attribute(self.schema_fields['docket'], record['docket'])
            qs = qs.by_attribute(self.schema_fields['cofa'], record['cofa'])
            old_record = qs[0]
        except IndexError:
            pass
        else:
            raise StopScraping('Found a duplicate record %s' % old_record.id)

        return record

    def save(self, old_record, list_record, detail_record):
        historic_district = self.get_or_create_lookup('historic_district', detail_record['historic_district'], detail_record['historic_district'])
        address = '%s, %s' % (detail_record['address'], detail_record['borough'])

        if detail_record['historic_district'] == 'N/A':
            title = 'Landmark permit issued for %s' % address
        else:
            title = 'Landmark permit issued for %s in %s' % (address, historic_district.name)

        attributes = {
            'cofa': detail_record['cofa'],
            'docket': detail_record['docket'],
            'historic_district': historic_district.id,
            'landmark_name': detail_record['landmark'],
            'expiration_date': detail_record['expiration_date'],
            'text': detail_record['text'],
        }
        self.create_newsitem(
            attributes,
            title=title,
            url=list_record['pdf_url'],
            item_date=detail_record['issue_date'],
            location_name=address,
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    s = LandmarkScraper()
    s.update()
