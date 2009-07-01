"""
Support for reading CSV as Unicode objects.

This module is necessary because Python's csv library doesn't support reading
Unicode strings.

This code is mostly copied from the Python documentation:
http://www.python.org/doc/2.5.2/lib/csv-examples.html
The changes we've made are to implement a DictReader instead of a normal
Reader.
"""

import csv
import codecs

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8.
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode('utf-8')

class UnicodeDictReader:
    """
    A CSV dict reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding. Results will always be Unicode
    objects instead of bytestrings.
    """
    def __init__(self, f, fieldnames, dialect=csv.excel, encoding='utf-8', **kwargs):
        f = UTF8Recoder(f, encoding)
        self.fieldnames = fieldnames
        self.reader = csv.reader(f, dialect=dialect, **kwargs)

    def next(self):
        row = self.reader.next()
        row = [unicode(s, 'utf-8') for s in row]
        return dict(zip(self.fieldnames, row))

    def __iter__(self):
        return self
