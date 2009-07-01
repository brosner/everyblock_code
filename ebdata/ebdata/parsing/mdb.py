"""
Utilities for reading data from Microsoft Access MDB files.

These require the mdbtools binaries, available here:
    http://mdbtools.sourceforge.net/
    http://prdownloads.sourceforge.net/mdbtools/mdbtools-0.5.tar.gz
    sudo apt-get install mdbtools
"""

import csv
from subprocess import Popen, PIPE

def list_tables(filename):
    """
    Returns a list of all the table names in the given MDB filename.
    """
    # Tell it to delimit the names with the pipe character.
    output = Popen(["mdb-tables", "-d", '|', "-t", "table", filename], stdout=PIPE).communicate()[0]
    return [t.strip() for t in output.split('|') if t.strip()]

class TableReader(csv.DictReader):
    """
    Like csv.DictReader, but it takes the MDB filename and table name.
    
    Example usage:
        for row in TableReader('mydb.mdb', 'some_table'):
            print row
    """
    def __init__(self, filename, table_name):
        f = Popen(['mdb-export', '-D', '%Y-%m-%d', filename, table_name], stdout=PIPE).stdout
        csv.DictReader.__init__(self, f)
