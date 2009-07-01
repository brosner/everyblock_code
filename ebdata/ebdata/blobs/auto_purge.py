from ebdata.blobs.models import Page, IgnoredDateline
from ebdata.nlp.datelines import guess_datelines
from ebpub.streets.models import Suburb
import re

def dateline_should_be_purged(dateline):
    dateline = dateline.upper()
    try:
        IgnoredDateline.objects.get(dateline=dateline)
        return True
    except IgnoredDateline.DoesNotExist:
        pass
    try:
        Suburb.objects.get(normalized_name=dateline)
        return True
    except Suburb.DoesNotExist:
        pass
    return False

def all_relevant_datelines():
    """
    Prints all datelines that are in articles but not in ignored_datelines,
    for all unharvested Pages in the system.
    """
    seen = {}
    for page in Page.objects.filter(has_addresses__isnull=True, is_pdf=False):
        for bit in page.mine_page():
            for dateline in guess_datelines(bit):
                dateline = dateline.upper()
                if dateline not in seen and not dateline_should_be_purged(dateline):
                    print dateline
                    seen[dateline] = 1

def page_should_be_purged(paragraph_list):
    """
    Returns a tuple of (purge, reason). purge is True if the given list of
    strings can be safely purged. reason is a string.
    """
    datelines = []
    for para in paragraph_list:
        datelines.extend(guess_datelines(para))
    if datelines:
        dateline_text = ', '.join([str(d) for d in datelines])
        if not [d for d in datelines if not dateline_should_be_purged(d)]:
            return (True, 'Dateline(s) %s safe to purge' % dateline_text)
        else:
            return (False, 'Dateline(s) %s found but not safe to purge' % dateline_text)
    return (False, 'No datelines')
