"""
Screen scraper for Chicago restaurant-inspection data
http://webapps.cityofchicago.org/healthinspection/inspection.jsp
"""

from django.utils.text import get_text_list
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebdata.retrieval.utils import norm_dict_space
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
from ebpub.utils.text import clean_address
import re

list_aka_re = re.compile(r'<br><font color=blue><i>\((.*?)\)</i></font>')
detail_violations_re = re.compile(r"<a href='inspectiondesc\.jsp\?v=.*?'>(.*?)</a></td><td.*?</td><td align='center' valign='middle'>(.*?)</td>", re.DOTALL)

detail_url = lambda list_record: 'http://webapps.cityofchicago.org/healthinspection/inspectiondate.jsp?eid=%s' % list_record['city_id']

class RestaurantScraper(NewsItemListDetailScraper):
    schema_slugs = ('restaurant-inspections',)
    parse_list_re = re.compile(r'<tr>\s*<td valign="middle"[^>]*><a href="inspectiondate\.jsp\?eid=(?P<city_id>\d+)">(?P<name>.*?)</a><br><font color=green><i>\((?P<dba>.*?)\)</i></font>(?P<aka><br><font color=blue><i>\(.*?\)</i></font>)?\s+<br>.*?Address:</font></b>(?P<address>.*?)</td>\s*<td align="center"[^>]*>(?P<last_inspection_date>.*?)\s*</td>\s*<td align="center"[^>]*>(?P<result>.*?)\s*</td>\s*<td align="center"[^>]*>(?P<license_status>.*?)\s*</td>', re.DOTALL)
    parse_detail_re = re.compile(r'<b>Last Inspection Date: </b>(?P<inspection_date>.*?)<br><b>Inspection Result: </b>(?P<inspection_result>.*?)<br>.*?(?P<violations><table.*?</table>)', re.DOTALL)

    def list_pages(self):
        # Submit a search for the address range "0-99999".
        yield self.get_html('http://webapps.cityofchicago.org/healthinspection/inspectionresultrow.jsp?REST=&STR_NBR=0&STR_NBR2=99999&STR_DIRECTION=&STR_NM=&ZIP=&submit=Search')

    def clean_list_record(self, record):
        if record['last_inspection_date'].lower() == 'not available':
            raise SkipRecord('No inspection available')
        else:
            record['last_inspection_date'] = parse_date(record['last_inspection_date'], '%m/%d/%Y')
        if record['aka']:
            record['aka'] = list_aka_re.findall(record['aka'])[0]
        else:
            record['aka'] = ''
        norm_dict_space(record, 'name', 'dba', 'address')
        record['result'] = record['result'].replace('&nbsp;', '').strip()
        record['city_id'] = int(record['city_id'])

        # Remove the trailing ZIP code from the address, if it exists.
        m = re.search(r'(.*?)\s+\d\d\d\d\d$', record['address'])
        if m:
            record['address'] = m.group(1)
        record['address'] = clean_address(record['address'])

        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['last_inspection_date'])
            qs = qs.by_attribute(self.schema_fields['city_id'], record['city_id'])
            return qs[0]
        except IndexError:
            return None

    def detail_required(self, list_record, old_record):
        # If we've never seen this restaurant before, then a detail page is
        # required.
        if old_record is None:
            self.logger.debug('detail_required: True, because old_record is None')
            return True

        # Otherwise, check each field against the stored version to see whether
        # anything has changed. If at least one field has changed, then check
        # the detail page.
        if old_record.item_date != list_record['last_inspection_date']:
            self.logger.debug('detail_required: True, because last_inspection_date has changed')
            return True
        for field in ('name', 'dba', 'aka'):
            if old_record.attributes.get(field, '').encode('utf8') != list_record[field]:
                self.logger.debug('detail_required: True, because %s has changed (%r, %r)', field, old_record.attributes.get(field, '').encode('utf8'), list_record[field])
                return True
        return False

    def get_detail(self, record):
        url = detail_url(record)
        return self.get_html(url)

    def clean_detail_record(self, record):
        try:
            record['inspection_date'] = parse_date(record['inspection_date'], '%m/%d/%Y')
        except KeyError:
            # Sometimes the inspection_date is missing, for whatever reason.
            # Raise a warning in this case.
            self.logger.info('Record %r has no inspection_date. Skipping.', record)
            raise SkipRecord
        record['violations'] = [(i[0], i[1] == 'Yes') for i in detail_violations_re.findall(record['violations'])]

        # Determine the notes (a textual representation of which violations,
        # if any, were corrected during the inspection).
        corrected_violations = [v[0] for v in record['violations'] if v[1]]
        if record['violations']:
            if not corrected_violations:
                if len(corrected_violations) == 1:
                    note_bit = 'violation was not'
                else:
                    note_bit = 'violations were not'
            elif len(corrected_violations) == 1:
                if len(record['violations']) == 1:
                    note_bit = 'violation was'
                else:
                    note_bit = '%s violation was' % corrected_violations[0]
            else: # Multiple corrected violations.
                note_bit = '%s violations were' % get_text_list(corrected_violations, 'and')
            notes = 'The %s corrected during the inspection.' % note_bit
        else:
            # There's no need for notes if there were no violations.
            notes = ''
        record['notes'] = notes

        return record

    def save(self, old_record, list_record, detail_record):
        if detail_record is None:
            return # No need to update the record.
        result = self.get_or_create_lookup('result', list_record['result'], list_record['result'])
        violations = [self.get_or_create_lookup('violation', v[0], v[0]) for v in detail_record['violations']]
        violations_text = ','.join([str(v.id) for v in violations])
        result_past_tense = {
            'Pass': 'passed inspection',
            'Pass With Conditions': 'passed inspection with conditions',
            'Fail': 'failed inspection',
        }[list_record['result']]
        title = u'%s %s' % (list_record['dba'], result_past_tense)

        new_attributes = {
            'name': list_record['name'],
            'dba': list_record['dba'],
            'aka': list_record['aka'],
            'result': result.id,
            'violation': violations_text,
            'city_id': list_record['city_id'],
            'notes': detail_record['notes'],
        }

        if old_record is None:
            self.create_newsitem(
                new_attributes,
                title=title,
                url=detail_url(list_record),
                item_date=detail_record['inspection_date'],
                location_name=list_record['address'],
            )
        else:
            # This already exists in our database, but check whether any
            # of the values have changed.
            new_values = {'title': title, 'item_date': detail_record['inspection_date'], 'location_name': list_record['address']}
            self.update_existing(old_record, new_values, new_attributes)

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    RestaurantScraper().update()
