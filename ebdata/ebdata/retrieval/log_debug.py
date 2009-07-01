"""
Import this file to send all 'eb.retrieval' messages (of any level, including
logger.DEBUG) to the console. This is convenient for debugging.
"""

from ebdata.retrieval import log
import logging

# Send all DEBUG messages to the console.
printer = logging.StreamHandler()
printer.setLevel(logging.DEBUG)
eb_root_logger = logging.getLogger('eb.retrieval')
eb_root_logger.addHandler(printer)

# Remove the e-mail handler.
eb_root_logger.removeHandler(log.emailer)
