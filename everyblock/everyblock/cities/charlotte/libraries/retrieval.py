"""
Charlotte library scraper
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.db.models import NewsItem
from lxml import etree
import datetime
import re
import urllib

ITEM_TYPES = (
    ('afn', 'Fiction'),
    ('anfbn', 'Biography'),
    ('anfn', 'Nonfiction'),
    ('dvdn', 'DVD'),
)

BRANCHES = (
    ('Main library', 'ml', '310 North Tryon St.'),
    ('Beatties Ford Road Branch', 'bfr', '2412 Beatties Ford Road'),
    ('Belmont Center Branch', 'bc', '700 Parkwood Avenue'),
    ('Carmel Branch', 'ca', '6624 Walsh Boulevard'),
    ('Checkit Outlet', 'ckt', '435 South Tryon Street'),
    ('Freedom Regional', 'frl', '1230 Alleghany Street'),
    ('Hickory Grove Branch', 'hg', '7209 E. W.T. Harris Blvd.'),
    ('Imaginon: The Joe and Joan Martin Center', 'img', '300 East 7th St.'),
    ('Independence Regional', 'ib', '6015 Conference Drive'),
    ('Mountain Island', 'mti', '300 Hoyt Galvin Way'),
    ('Morrison Regional', 'mor', '7015 Morrison Boulevard'),
    ('Myers Park Branch', 'mpk', '1361 Queens Road'),
    ('Plaza Midwood Branch', 'pm', '1623 Central Avenue'),
    ('Scaleybark Branch', 'sc', '101 Scaleybark Road'),
    ('South County Regional', 'sor', '5801 Rea Road'),
    ('Steele Creek Branch', 'st', '13620 Steele Creek Road'),
    ('Sugar Creek Branch', 'sug', '4045 N. Tryon Street'),
    ('University City Regional', 'uc', '301 E. W.T. Harris Boulevard'),
    ('West Boulevard', 'wbl', '2157 West Boulevard'),
)

rows_xpath = etree.XPath('//row')

class LibraryScraper(NewsItemListDetailScraper):
    schema_slugs = ('new-library-items',)
    has_detail = False
    sleep = 3

    def list_pages(self):
        for item_type_code, item_type in ITEM_TYPES:
            for branch_name, branch_code, branch_address in BRANCHES:
                # Note that we use the hard-coded query string here instead of
                # urllib.urlencode because urllib.urlencode encodes pluses,
                # which seems to break the library site.
                url = 'http://hip.plcmc.org/ipac20/ipac.jsp?menu=search&profile=plcmc&index=.TW&term=*&oper=and&limitbox_1=CO01+%%3D+co_%s&limitbox_2=LO01+%%3D+%s&GetXML=true' % (item_type_code, branch_code)
                yield self.get_html(url), item_type, branch_name, branch_address

    def parse_list(self, bunch):
        html, item_type, branch_name, branch_address = bunch

        # The feed puts these comments (and whitespace) before the <?xml>
        # declaration, which lxml doesn't like.
        html = re.sub(r'\s*<!--searching-->\s*', '', html)

        tree = etree.fromstring(html)
        for row in rows_xpath(tree):
            yield {
                'item_type': item_type,
                'branch_name': branch_name,
                'branch_address': branch_address,
                'row': row,
            }

    def clean_list_record(self, record):
        row = record.pop('row')
        record['isbn'] = row.find('isbn') and row.find('isbn').text or None
        record['item_key'] = row.find('key').text
        record['image'] = urllib.unquote(row.find('small_ec_image_url').text)
        record['title'] = row.xpath('TITLE/data/text')[0].text.split(' / ')[0].replace('[DVD]', '').strip()
        record['url'] = 'http://hip.plcmc.org/ipac20/ipac.jsp?profile=plcmc&uri=%s' % row.xpath('TITLE/data/link/func')[0].text
        return record

    def existing_record(self, record):
        # Due to the nature of the data, there's no great way to tell whether
        # an item is "existing." We do it here by looking for any item at the
        # same library branch with the same item_key that was added in the past
        # 7 days.
        try:
            qs = NewsItem.objects.filter(schema__id=self.schema.id, item_date__gt=self.start_time - datetime.timedelta(days=7))
            qs = qs.by_attribute(self.schema_fields['branch'], record['branch_name'], is_lookup=True)
            qs = qs.by_attribute(self.schema_fields['item_key'], record['item_key'])
            return qs[0]
        except IndexError:
            return None

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            self.logger.debug('Record already exists')
            return

        branch = self.get_or_create_lookup('branch', list_record['branch_name'], list_record['branch_name'])
        item_type = self.get_or_create_lookup('item_type', list_record['item_type'], list_record['item_type'])

        attributes = {
            'image': list_record['image'],
            'isbn': list_record['isbn'],
            'item_type': item_type.id,
            'item_key': list_record['item_key'],
            'branch': branch.id,
        }
        self.create_newsitem(
            attributes,
            title=list_record['title'][:255],
            url=list_record['url'],
            item_date=self.start_time.date(),
            location_name=list_record['branch_address'],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    LibraryScraper().update()
