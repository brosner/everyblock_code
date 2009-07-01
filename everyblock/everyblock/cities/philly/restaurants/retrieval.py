"""
Screen scraper for Philadelphia restaurant inspections.

http://www.phila.gov/health/units/ehs/Restaurant_Inspectio.html

The data is in PDFs, with a PDF for each section of Philly (7 total).
"""

from django.core.serializers.json import DjangoJSONEncoder
from ebdata.parsing.pdftotext import pdf_to_text
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from ebpub.utils.dates import parse_date
import md5
import re

class RestaurantScraper(NewsItemListDetailScraper):
    schema_slugs = ('restaurant-inspections',)
    has_detail = False

    def __init__(self, pdf_filename):
        super(RestaurantScraper, self).__init__()
        self.pdf_filename = pdf_filename

    def list_pages(self):
        yield pdf_to_text(self.pdf_filename, keep_layout=True, raw=False).split('\n')

    def parse_list(self, text):
        inspection_date = violations = address = city = restaurant_name = restaurant_type = None
        last_line_was_restaurant = False
        in_page_header = True
        for line in text:
            if line.startswith('\x0c'): # New page
                if address is not None and inspection_date is not None:
                    yield {
                        'restaurant_name': restaurant_name,
                        'address': address,
                        'city': city,
                        'restaurant_type': restaurant_type,
                        'violation_list': violations,
                        'inspection_date': inspection_date,
                    }

                inspection_date = violations = address = city = restaurant_name = restaurant_type = None
                last_line_was_restaurant = False
                in_page_header = True

            line = line.strip().decode('iso-8859-1')

            # Skip cruft, like page numbers, etc.
            if re.search(r'^Environmental Health Services\s{10,}\d\d?/\d\d?/\d\d\d\d$', line) \
                    or re.search(r'^Food Establishment Inspections,', line) \
                    or re.search('^Page \d+ of \d+$', line) \
                    or line == 'City of Philadelphia' \
                    or line == 'Environmental Health Services' \
                    or line == 'FOOD PROTECTIONS VIOLATIONS' \
                    or line == '':
                continue

            m = re.search(r'(.*?)\s{5,}((?:Retail Food|Institution|Vendor|Wholesale|Water Supply):.*)$', line)
            if m:
                in_page_header = False
                if address is not None:
                    yield {
                        'restaurant_name': restaurant_name,
                        'address': address,
                        'city': city,
                        'restaurant_type': restaurant_type,
                        'violation_list': violations,
                        'inspection_date': inspection_date,
                    }
                restaurant_name = m.group(1)
                restaurant_type = m.group(2)
                inspection_date = violations = address = city = None
                last_line_was_restaurant = True
                continue
            # Ugly special cases because these only have a single space between name and type.
            elif line in ('VALLE OLIMPICO RESTAURANT & SUPER BAKERY Retail Food: Restaurant, Eat-in', 'MCMILLAN CHRISTIAN FAMILY CHILD DAY CARE Institution: Child, Family Day Care Homes'):
                m = re.search(r'^(.*?) ((?:Retail Food|Institution):.*)$', line)
                restaurant_name = m.group(1)
                restaurant_type = m.group(2)
                inspection_date = violations = address = city = None
                last_line_was_restaurant = True
                continue
            elif in_page_header:
                continue

            if last_line_was_restaurant:
                m = re.search(r'(.*?)\s{10,}(.*)$', line)
                if not m:
                    print line
                    raise ValueError
                address = m.group(1)
                city = m.group(2)
                last_line_was_restaurant = False
                continue

            if line == 'Inspection Date':
                violations = []
                continue

            if re.search(r'^\d\d?/\d\d?/\d\d$', line):
                if address is not None and inspection_date is not None:
                    yield {
                        'restaurant_name': restaurant_name,
                        'address': address,
                        'city': city,
                        'restaurant_type': restaurant_type,
                        'violation_list': violations,
                        'inspection_date': inspection_date,
                    }
                    violations = []
                inspection_date = line
                continue

            # The remaining text must be the violation. It's either a new
            # violation, or a continuation of the violation text from the
            # previous line.
            if re.search(r'^(?:PM-\d+\.\d+|\d+-\d|\d+\.\d+|PLEASE NOTE:|Proper plans,|This inspection|Person in Control|Note: )', line):
                try:
                    violations.append(line)
                except AttributeError:
                    print repr(line)
                    raise
            elif line.lower() == 'no critical violations':
                pass
            else:
                try:
                    violations[-1] += ' ' + line
                except IndexError:
                    print repr(line)
                    raise
        if address is not None and inspection_date is not None:
            yield {
                'restaurant_name': restaurant_name,
                'address': address,
                'city': city,
                'restaurant_type': restaurant_type,
                'violation_list': violations,
                'inspection_date': inspection_date,
            }

    def clean_list_record(self, record):
        record['inspection_date'] = parse_date(record['inspection_date'], '%m/%d/%y')
        # The PDFs don't include any sort of unique ID for a restaurant, so we
        # create our own by hashing the restaurant name and address.
        record['restaurant_hash'] = md5.new('%s.%s' % (record['restaurant_name'].upper().encode('utf8'), record['address'].upper().encode('utf8'))).hexdigest()
        record['raw_address'] = record['address'].upper()
        record['raw_city'] = record['city'].upper()

        clean_violations = []
        notes = []
        for vio in record['violation_list']:
            # Split the violation into code and comment. The tricky part here
            # is that this text could be split over multiple lines, and
            # sometimes the text that begins a line *looks* like a code but
            # really isn't. The prime example is "215.685.7498" -- the phone
            # number for the health department -- which we special-case in the
            # following regex.
            m = re.search(r'^(?!215[-\.]685[-\.]74|856[-\.]912[-\.]4193)(\d[-\d\.]+(?::?\s*?\([A-Z]\))?)\s+(.*)$', vio)
            if m:
                vio_code, vio_comment = m.groups()
                vio_code = re.sub(r'\s\s+', ' ', vio_code) # Collapse multiple spaces into one.

                # Violation comments have stuff like 'foo-------bar', so clean that up.
                vio_comment = re.sub(r'\s*--+\s*', ' -- ', vio_comment)

                clean_violations.append((vio_code, vio_comment))
            else:
                notes.append(vio)
        record['violation_list'] = clean_violations
        record['notes'] = ' '.join(notes)
        return record

    def existing_record(self, record):
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date=record['inspection_date'])
            qs = qs.by_attribute(self.schema_fields['restaurant_hash'], record['restaurant_hash'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return # We already have this inspection.

        restaurant_type = self.get_or_create_lookup('restaurant_type', list_record['restaurant_type'], list_record['restaurant_type'])
        violation_lookups = [self.get_or_create_lookup('violation', v[0], v[0], make_text_slug=False) for v in list_record['violation_list']]
        violation_lookup_text = ','.join([str(v.id) for v in violation_lookups])

        # There's a bunch of data about every particular violation, and we
        # store it as a JSON object. Here, we create the JSON object.
        v_lookup_dict = dict([(v.code, v) for v in violation_lookups])
        v_list = [{'lookup_id': v_lookup_dict[code].id, 'comment': comment} for code, comment in list_record['violation_list']]
        details_json = DjangoJSONEncoder().encode({'notes': list_record['notes'], 'violations': v_list})

        title = u'%s inspected: ' % list_record['restaurant_name']
        if not list_record['violation_list']:
            title += u'No critical violations'
        else:
            num = len(list_record['violation_list'])
            title += u'%s critical violation%s' % (num, num != 1 and 's' or '')

        attributes = {
            'raw_address': list_record['raw_address'],
            'raw_city': list_record['raw_city'],
            'restaurant_hash': list_record['restaurant_hash'],
            'details': details_json,
            'restaurant_name': list_record['restaurant_name'],
            'restaurant_type': restaurant_type.id,
            'violation': violation_lookup_text,
        }
        self.create_newsitem(
            attributes,
            title=title,
            item_date=list_record['inspection_date'],
            location_name=list_record['address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    for name in ('w', 'cc', 'lne', 'ne', 'n', 'nw', 's'):
        RestaurantScraper('ehs_inspections_-_%s_jan09.pdf' % name).display_data()
