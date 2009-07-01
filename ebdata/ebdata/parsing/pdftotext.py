"""
Utilities for reading data from PDF files.

These require the pdftotext binary, available in the Xpdf package:
    http://www.foolabs.com/xpdf/download.html
"""

import os

PDFTOTEXT_BINARY = 'pdftotext'

def pdf_to_text(filename, keep_layout=True, raw=False):
    """
    Returns the text of the PDF with the given filename on the local filesystem.
    """
    if keep_layout and raw:
        raise ValueError('The "keep_layout" and "raw" arguments may not be used together')
    options = []
    if keep_layout:
        options.append('-layout')
    if raw:
        options.append('-raw')
    cmd = "%s %s '%s' -" % (PDFTOTEXT_BINARY, ' '.join(options), filename)
    return os.popen(cmd).read()

def pdfstring_to_text(pdf_string, keep_layout=True, raw=False):
    """
    Returns the text of the given PDF (provided as a string).
    """
    import os
    from tempfile import mkstemp
    fd, name = mkstemp()
    fp = os.fdopen(fd, 'wb')
    fp.write(pdf_string)
    fp.close()
    try:
        result = pdf_to_text(name, keep_layout, raw)
    finally:
        os.unlink(name)
    return result
