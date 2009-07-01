"""
Screen scraper for SF zoning changes.
http://sfgov.org/site/planning_meeting.asp?id=15840

Input is a manually created text file in this format:

    http://sfgov.org/site/planning_page.asp?id=73133
    2008-01-10
    CONSIDERATION OF ITEMS PROPOSED FOR CONTINUANCE
    2007.0718C
    507 Columbus Avenue
    507 Columbus Avenue - west side between Union and Green Streets, Lot 005 in Assessor’s Block 0117 - Request for Conditional Use Authorization to establish a retail wine store and a bar (dba “Vino Divino”) of approximately 807 square feet within the vacant, existing ground-floor commercial space.  No physical expansion of the existing building is proposed.  The bar portion of the proposal is intended to be a “wine bar” which will sell beer and wine for consumption on- site with the retail wine store portion of the business selling beer and wine for consumption off-site. This site is within the North Beach Neighborhood Commercial District, and a 40-X Height and Bulk District.
    Request for Conditional Use Authorization
    Proposed for Continuance to January 17, 2008
"""

from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.utils.dates import parse_date

class ZoningScraper(NewsItemListDetailScraper):
    schema_slugs = ('zoning-agenda',)
    has_detail = False

    def __init__(self, text, *args, **kwargs):
        super(ZoningScraper, self).__init__(*args, **kwargs)
        self.text = text.decode('utf8')

    def list_pages(self):
        yield self.text

    def parse_list(self, text):
        for chunk in text.strip().split('\n\n'):
            yield chunk.split('\n')

    def existing_record(self, record):
        # Assume this is always being input manually.
        return None

    def save(self, old_record, list_record, detail_record):
        agenda_item = self.get_or_create_lookup('agenda_item', list_record[2], list_record[2], make_text_slug=False)
        action_requested = self.get_or_create_lookup('action_requested', list_record[6], list_record[6], make_text_slug=False)
        title = '%s at %s' % (action_requested.name, list_record[4])
        attributes = {
            'case_number': list_record[3],
            'agenda_item': agenda_item.id,
            'description': list_record[5],
            'action_requested': action_requested.id,
            'preliminary_recommendation': list_record[7],
        }
        self.create_newsitem(
            attributes,
            title=title,
            url=list_record[0],
            item_date=parse_date(list_record[1], '%Y-%m-%d'),
            location_name=list_record[4],
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    import sys
    text = open(sys.argv[1]).read()
    s = ZoningScraper(text)
    s.update()
