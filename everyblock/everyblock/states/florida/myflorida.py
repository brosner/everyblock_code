"""
Base class for scrapers that get stuff via FTP from http://www.myflorida.com/
"""

from ebdata.parsing.unicodecsv import UnicodeDictReader
from ebdata.retrieval.scrapers.base import ScraperBroken
from ebdata.retrieval.scrapers.newsitem_list_detail import NewsItemListDetailScraper
from cStringIO import StringIO
import ftplib
import zipfile

class MyFloridaScraper(NewsItemListDetailScraper):
    # Subclasses must set these attributes before list_pages() is called.
    florida_ftp_filename = None
    florida_csv_fieldnames = None
    florida_csv_filename = None

    def list_pages(self):
        self.logger.debug('Connecting via FTP')
        ftp = ftplib.FTP('dbprftp.state.fl.us')
        ftp.login() # This is a necessary step; otherwise we get "530 Please login with USER and PASS".
        ftp.set_pasv(False) # Turn off passive mode, which is on by default.
        ftp.cwd('/pub/llweb')
        self.logger.debug('Retrieving file %s' % self.florida_ftp_filename)
        f = StringIO() # This buffer stores the retrieved file in memory.
        ftp.retrbinary('RETR %s' % self.florida_ftp_filename, f.write)
        self.logger.debug('Done downloading')
        f.seek(0)
        ftp.quit() # Note that we quit the connection before scraping starts -- otherwise we get a timeout!
        yield f
        f.close()

    def parse_list(self, file_obj):
        # Unzip the file. Although it has an .exe extension, we can treat it
        # just like a ZIP file.
        zf = zipfile.ZipFile(file_obj)
        if self.florida_csv_filename is None:
            csv_names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
            if len(csv_names) != 1:
                raise ScraperBroken('Found %s CSV file(s) in the zip' % len(csv_names))
            csv_filename = csv_names[0]
        else:
            csv_filename = self.florida_csv_filename
        csv_text = zf.read(csv_filename)
        # The data is in iso-8859-1 encoding, so we use UnicodeDictReader so
        # that it gets converted properly to Unicode objects.
        reader = UnicodeDictReader(StringIO(csv_text), self.florida_csv_fieldnames, encoding='iso8859-1')
        for row in reader:
            yield row
