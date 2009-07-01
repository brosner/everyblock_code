"""
Scraper for Charlotte health inspections.
"""

from django.core.serializers.json import DjangoJSONEncoder
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.retrievers import Retriever
from ebpub.db.models import NewsItem
from ebpub.utils.text import smart_title
from cStringIO import StringIO
from dateutil.parser import parse as parse_date
import datetime
import csv
import re

FOOD_SLUG = 'food-inspections'
POOL_SLUG = 'pool-inspections'

EXCLUDED_FACILITY_TYPES = ['20', '21', '22', '23', '41', '44', '03', '04']

# commented out types should be excluded
FACILITY_TYPES = {
    '01': {'schema': FOOD_SLUG, 'name': 'Restaurants'},
    '02': {'schema': FOOD_SLUG, 'name': 'Food Stands'},
    '05': {'schema': FOOD_SLUG, 'name': 'Private School Lunchrooms'},
    '11': {'schema': FOOD_SLUG, 'name': 'Public School Lunchrooms'},
    #'20': {'schema': FOOD_SLUG, 'name': 'Lodging'},
    #'21': {'schema': FOOD_SLUG, 'name': 'B&B Homes'},
    #'22': {'schema': FOOD_SLUG, 'name': 'Summer Camps'},
    #'23': {'schema': FOOD_SLUG, 'name': 'B&B Inns'},
    '30': {'schema': FOOD_SLUG, 'name': 'Meat Markets'},
    #'41': {'schema': FOOD_SLUG, 'name': 'Hospitals'},
    #'44': {'schema': FOOD_SLUG, 'name': 'School Building (Private & Public)'},
    #'03': {'schema': FOOD_SLUG, 'name': 'Mobile Food Units'},
    #'04': {'schema': FOOD_SLUG, 'name': 'Pushcarts'},

    '50': {'schema': POOL_SLUG, 'name': 'Seasonal Swimming Pools'},
    '51': {'schema': POOL_SLUG, 'name': 'Seasonal Wading Pools'},
    '52': {'schema': POOL_SLUG, 'name': 'Seasonal Spas'},
    '53': {'schema': POOL_SLUG, 'name': 'Year-Round Swimming Pools'},
    '54': {'schema': POOL_SLUG, 'name': 'Year-Round Wading Pools'},
    '55': {'schema': POOL_SLUG, 'name': 'Year-Round Spas'},
}

class Scraper(NewsItemListDetailScraper):
    schema_slugs = (FOOD_SLUG, POOL_SLUG)
    has_detail = False

    def __init__(self, *args, **kwargs):
        super(Scraper, self).__init__(*args, **kwargs)
        # The file is around 41MB (as of 8/08) and takes awhile to start
        # downloading, so wait more than 20 seconds for it.
        self.retriever = Retriever(timeout=300)

    def list_pages(self):
        # There's only one page of data, so just return it as a list with a
        # single item.
        uri = ''
        data = self.get_html(uri)
        return [data]

    def parse_list(self, page):
        # Remove null bytes
        page = re.sub(r'\0', r' ', page)
        # Remove sequences of '''''''
        page = re.sub(r"'+", "'", page)
        reader = csv.DictReader(StringIO(page), quoting=csv.QUOTE_ALL, escapechar='\\')
        # There is one row in the data for each violation, not just each
        # inspection. Violations from the same inspection will be contiguous,
        # so roll up the violations until we see a different inspection.
        current_record = None
        for row in reader:
            if row['CITY'] != 'CHARLOTTE':
                continue
            row['comments'] = []
            # Strip any leading zeros. Both 01 and 1 appear sometimes, but
            # they mean the same thing.
            item_id = row['ITEM_NUM'].lstrip('0')
            violation = {'id': item_id, 'value': row['ITEM_VALUE'], 'comment': row['COMMENT']}
            if current_record is None:
                current_record = row
                current_record['violation'] = [violation]
            elif current_record['FAC_NAME'] != row['FAC_NAME'] or current_record['DATE'] != row['DATE']:
                yield current_record
                current_record = row
                current_record['violation'] = [violation]
            else:
                current_record['violation'].append(violation)
        # The final record won't be yielded from the loop above because it has
        # no following record to trigger it, so yield it here.
        yield current_record

    def clean_list_record(self, record):
        # The facility type is determied by the 6th and 7th digits in the
        # facility ID.
        facility_type = record['FAC_ID'][5:7]
        if facility_type in EXCLUDED_FACILITY_TYPES:
            raise SkipRecord('Excluding record from facility type %s' % facility_type)
        record['DATE'] = parse_date(record['DATE']).date()
        record['FAC_NAME'] = record['FAC_NAME'].decode('Latin-1')
        record['FIN_SCORE'] = float(record['FIN_SCORE']) + float(record['RAW_SCORE'])
        record['schema_slug'] = self.get_schema_slug(record)
        record['facility_type'] = self.clean_facility_type(facility_type)
        record['result'] = self.get_result(record)
        return record

    def clean_facility_type(self, facility_type):
        if FACILITY_TYPES.has_key(facility_type):
            return FACILITY_TYPES[facility_type]['name']
        return 'Unknown'

    def get_schema_slug(self, record):
        # The facility type is determied by the 6th and 7th digits in the
        # facility ID.
        value = record['FAC_ID'][5:7]
        return FACILITY_TYPES[value]['schema']

    def get_result(self, record):
        # Set pass/fail
        if record['TYPE_ACT'] in ['Status Change', 'Visit', 'CV Visit', 'CV Follow-up']:
            return 'N/A'
        if record['schema_slug'] == FOOD_SLUG:
            if record['facility_type'] in ['Mobile Food Units', 'Pushcarts']:
                if record['CLASSIFICATION'] == 'Approved':
                    result = 'Pass'
                elif record['CLASSIFICATION'] == 'Dispproved':
                    result = 'Fail'
                else:
                    result = 'Unknown'
            else:
                if record['FIN_SCORE'] in (None, ''):
                    result = 'Unknown'
                elif record['FIN_SCORE'] >= 70.0:
                    result = 'Pass'
                else:
                    result = 'Fail'
        elif record['schema_slug'] == POOL_SLUG:
            if record['ACT_PSC'] in ['A', 'I']:
                result = 'Pass'
            elif record['ACT_PSC'] in ['E', 'W']:
                result = 'Fail'
        return result

    def existing_record(self, record):
        schema_slug = record['schema_slug']
        schema = self.schemas[schema_slug]
        if not isinstance(record['DATE'], datetime.date):
            return None
        qs = NewsItem.objects.filter(schema__id=schema.id, item_date=record['DATE'])
        qs = qs.by_attribute(self.schema_fields[schema_slug]['name'], record['FAC_NAME'])
        try:
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if list_record['TYPE_ACT'] in ('Visit', 'CV Visit', 'Status Change', 'CV Follow-Up'):
            return

        schema_slug = list_record['schema_slug']
        schema = self.schemas[schema_slug]

        result_lookup = self.get_or_create_lookup('result', list_record['result'], list_record['result'], schema=schema_slug)
        facility_type_lookup = self.get_or_create_lookup('facility_type', list_record['facility_type'], list_record['facility_type'], schema=schema_slug, make_text_slug=False)
        facility_status_lookup = self.get_or_create_lookup('facility_status', list_record['ACT_PSC'], list_record['ACT_PSC'], schema=schema_slug, make_text_slug=False)
        classification_lookup = self.get_or_create_lookup('classification', list_record['CLASSIFICATION'], list_record['CLASSIFICATION'], schema=schema_slug, make_text_slug=False)
        action_type_lookup = self.get_or_create_lookup('action_type', list_record['TYPE_ACT'], list_record['TYPE_ACT'], schema=schema_slug, make_text_slug=False)

        if schema_slug == FOOD_SLUG:
            if list_record['DATE'] >= datetime.date(2008, 7, 1):
                prefix = '2.'
            else:
                prefix = '1.'
        else:
            prefix = ''
        v_type_lookup_list = []
        v_list = []
        for v in list_record['violation']:
            v_type_lookup = self.get_or_create_lookup('violation', prefix + v['id'], prefix + v['id'], schema=schema_slug, make_text_slug=False)
            v_type_lookup_list.append(v_type_lookup)
            v_list.append({'lookup_id': v_type_lookup.id, 'value': v['value'], 'comment': v['comment']})
        violations_json = DjangoJSONEncoder().encode(v_list)

        title = list_record['FAC_NAME']
        address = ' '.join([list_record['ADDR1'], list_record['ADDR2']])
        attributes = {
            'name': list_record['FAC_NAME'],
            'facility_type': facility_type_lookup.id,
            'facility_status': facility_status_lookup.id,
            'raw_score':list_record['RAW_SCORE'],
            'final_score': list_record['FIN_SCORE'],
            'result': result_lookup.id,
            'classification': classification_lookup.id,
            'facility_id': list_record['FAC_ID'],
            'violation': ','.join([str(v.id) for v in v_type_lookup_list]),
            'violation_detail': violations_json,
            'action_type': action_type_lookup.id
        }
        values = {
            'schema': schema,
            'title': title,
            'item_date': list_record['DATE'],
            'location_name': smart_title(address),
        }
        if old_record is None:
            self.create_newsitem(attributes, **values)
        else:
            self.update_existing(old_record, values, attributes)

if __name__ == '__main__':
    from ebdata.retrieval import log_debug
    Scraper().update()
