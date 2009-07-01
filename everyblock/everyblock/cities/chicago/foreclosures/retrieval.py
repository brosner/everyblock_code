"""
Importer for Chicago foreclosure data from the Woodstock Institute.

The data is in a ZIP file on a site protected with HTTP authentication.
"""

from ebdata.parsing import dbf, excel
from ebdata.retrieval.scrapers.list_detail import SkipRecord
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from ebpub.geocoder.parser.parsing import strip_unit
from ebpub.utils.dates import parse_date
from ebpub.utils.text import address_to_block, clean_address
from cStringIO import StringIO
from tempfile import mkstemp
import base64
import os
import zipfile

USERNAME = ''
PASSWORD = ''

def strip_dict(d):
    for k, v in d.items():
        if isinstance(v, basestring):
            d[k] = v.strip()

class WoodstockScraper(NewsItemListDetailScraper):
    """
    Generic base class for the two Woodstock schemas.
    """
    has_detail = False

    source_url = 'http://www.woodstockinst.org/3683123610/junetooct.zip'

    def __init__(self, filename=None):
        self.woodstock_filename = filename
        NewsItemListDetailScraper.__init__(self)

    def list_pages(self):
        if self.woodstock_filename:
            yield open(self.woodstock_filename).read()
        else:
            # Our scraper infrastructure doesn't have a nice API to handle
            # usernames/passwords in basic HTTP authentication, so we have to
            # do it manually by passing in a base64 header.
            # See http://en.wikipedia.org/wiki/Basic_access_authentication
            auth_header = 'Basic %s' % base64.encodestring('%s:%s' % (USERNAME, PASSWORD)).strip()
            yield self.get_html(self.source_url, headers={'Authorization': auth_header})

    def parse_list(self, raw_zip_data):
        # The input is a ZIP file full of directories and/or files. Files can
        # be ZIP, DBF or XLS.
        zf = zipfile.ZipFile(StringIO(raw_zip_data))
        for zi in zf.filelist:
            if zi.file_size == 0:
                continue # Skip directories.
            if zi.filename.lower().endswith('.zip'):
                for data in self.parse_list(zf.read(zi.filename)):
                    yield data
            elif zi.filename.lower().endswith('.dbf'):
                try:
                    reader = dbf.dict_reader(StringIO(zf.read(zi.filename)))
                    for row in reader:
                        yield row
                except ValueError:
                    self.logger.warn('Skipping file %r: could not be parsed as DBF', zi.filename)
            elif zi.filename.lower().endswith('.xls'):
                # The Excel parser requires that the file be on the filesystem,
                # so write out a temp file.
                fd, filename = mkstemp()
                fp = os.fdopen(fd, 'wb')
                fp.write(zf.read(zi.filename))
                fp.close()

                # The workbook might have multiple worksheets, so we loop over
                # the ones we care about (by checking the worksheet's name
                # against self.excel_sheet_name).
                reader = excel.ExcelDictReader(filename, header_row_num=0, start_row_num=1)
                sheet_indexes = [sheet.number for sheet in reader.workbook.sheets() if self.excel_sheet_name == sheet.name.lower()]
                for index in sheet_indexes:
                    reader.sheet_index = index
                    for row in reader:
                        yield row
            else:
                self.logger.warn('Got unknown file type: %r', zi.filename)

    def clean_list_record(self, record):
        strip_dict(record)
        try:
            record['filing_date'] = parse_date(str(int(record['filing_dat'])), '%m%d%y')
        except ValueError:
            record['filing_date'] = None
        if record['filing_date'] is None:
            self.logger.info('Skipping invalid filing date %r', record['filing_dat'])
            raise SkipRecord
        record['address'] = clean_address(record.pop('address'))
        record['case_number'] = record.pop('case_#')
        record['document_number'] = record.pop('document_#')
        record['pin_number'] = record.pop('pin_number')
        try:
            record['year_of_mortgage'] = str(record.pop('year_of_mo').year)
        except AttributeError:
            record['year_of_mortgage'] = 'Unknown'

        # Normalize inconsistent headers
        for old, new in (('SF', 'sf'), ('SMF', 'smf'), ('Condo', 'condo')):
            try:
                record[new] = record.pop(old)
            except KeyError:
                pass

        if int(record['sf']):
            record['property_type'] = 'Single family'
        elif int(record['smf']):
            record['property_type'] = 'Multi-unit'
        elif int(record['condo']):
            record['property_type'] = 'Condo'
        else:
            record['property_type'] = 'Unknown'

        return record

    def existing_record(self, list_record):
        # Each time we run the scrape, we assume the data hasn't been seen yet.
        return None

class ForeclosureAuctionResultScraper(WoodstockScraper):
    schema_slugs = ('foreclosure-auction-results',)
    excel_sheet_name = 'ar'

    def clean_list_record(self, record):
        record = WoodstockScraper.clean_list_record(self, record)
        if record['reo_y_n']:
            record['purchaser'] = 'Lender or bank'
        else:
            record['purchaser'] = 'Third party'
        record['sale_date'] = record['sheriffs']
        try:
            record['auction_price'] = int(record['sale_price'])
        except ValueError:
            record['auction_price'] = None
        return record

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return

        property_type = self.get_or_create_lookup('property_type', list_record['property_type'], list_record['property_type'])
        year_of_mortgage = self.get_or_create_lookup('year_of_mortgage', list_record['year_of_mortgage'], list_record['year_of_mortgage'])
        purchaser = self.get_or_create_lookup('purchaser', list_record['purchaser'], list_record['purchaser'])
        newsitem_title = 'Property on the %s sold at foreclosure auction' % address_to_block(strip_unit(list_record['address']))
        attributes = {
            'original_principal': list_record['original_i'],
            'property_type': property_type.id,
            'year_of_mortgage': year_of_mortgage.id,
            'pin_number': list_record['pin_number'],
            'case_number': list_record['case_number'],
            'document_number': list_record['document_number'],
            'filing_date': list_record['filing_date'],
            'raw_address': list_record['address'],
            'auction_price': list_record['auction_price'],
            'purchaser': purchaser.id,
        }
        self.create_newsitem(
            attributes,
            convert_to_block=True,
            title=newsitem_title,
            item_date=list_record['sale_date'],
            location_name=strip_unit(list_record['address']),
        )

class ForeclosureScraper(WoodstockScraper):
    schema_slugs = ('foreclosures',)
    excel_sheet_name = 'cha'

    def save(self, old_record, list_record, detail_record):
        if old_record is not None:
            return

        property_type = self.get_or_create_lookup('property_type', list_record['property_type'], list_record['property_type'])
        year_of_mortgage = self.get_or_create_lookup('year_of_mortgage', list_record['year_of_mortgage'], list_record['year_of_mortgage'])
        newsitem_title = 'Foreclosure filed for property in the %s' % address_to_block(strip_unit(list_record['address']))
        attributes = {
            'original_principal': list_record['original_i'],
            'property_type': property_type.id,
            'year_of_mortgage': year_of_mortgage.id,
            'pin_number': list_record['pin_number'],
            'filing_date': list_record['filing_date'],
            'case_number': list_record['case_number'],
            'document_number': list_record['document_number'],
            'raw_address': list_record['address'],
        }
        self.create_newsitem(
            attributes,
            convert_to_block=True,
            title=newsitem_title,
            item_date=list_record['filing_date'],
            location_name=strip_unit(list_record['address']),
        )

if __name__ == "__main__":
    from ebdata.retrieval import log_debug
    import sys
    if len(sys.argv) == 2:
        args = [sys.argv[1]]
    else:
        args = []
    ForeclosureAuctionResultScraper(*args).update()
    ForeclosureScraper(*args).update()
