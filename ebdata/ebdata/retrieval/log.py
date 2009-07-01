# This module is registered by ebdata.retrieval.__init__ so that
# client code can simply use 'import logging' instead of having to set up
# the logging infrastructure on a case-by-case basis.
#
# Client code should use this like so:
#     import logging
#     # logger name should start with 'eb.retrieval.' to use this.
#     logger = logging.getLogger('eb.retrieval.scrapers.chicago.crime')
#     logger.warn('...')
#     logger.info('...')

from django.conf import settings
import logging
import logging.handlers

# Set up the file handler.
logfile = logging.FileHandler(settings.SCRAPER_LOGFILE_NAME)
logfile.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(name)-12s: %(levelname)-8s %(message)s')
logfile.setFormatter(formatter)

# Set up the e-mail handler.
class EbdataSMTPHandler(logging.handlers.SMTPHandler):
    def getSubject(self, record):
        return '%s[Log error]: %s' % (settings.EMAIL_SUBJECT_PREFIX, record.name)

emailer = EbdataSMTPHandler(settings.EMAIL_HOST, "example@example.com",
    [a[1] for a in settings.ADMINS], '')
emailer.setLevel(logging.WARNING)

# Add the handler to the 'eb.retrieval' logger. This means that only loggers
# whose names begin with 'eb.retrieval.' will get this functionality.
eb_root_logger = logging.getLogger('eb.retrieval')
eb_root_logger.addHandler(logfile)
eb_root_logger.addHandler(emailer)

# Set the logger's threshold to INFO. By default, it seems to ignore everything
# under the level WARNING.
eb_root_logger.setLevel(logging.DEBUG)
