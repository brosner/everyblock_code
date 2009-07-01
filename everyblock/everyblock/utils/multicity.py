from django.utils.safestring import SafeUnicode, SafeString
from ebpub.metros.allmetros import METRO_LIST
import psycopg2
import psycopg2.extensions

# This is taken from django/db/backends/postgresql_psycopg2/base.py
psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
psycopg2.extensions.register_adapter(SafeString, psycopg2.extensions.QuotedString)
psycopg2.extensions.register_adapter(SafeUnicode, psycopg2.extensions.QuotedString)

USERNAME = 'username'
HOST = '192.168.1.100'

def run_query(sql, params):
    """
    Runs the given SQL query against every city database and returns a
    dictionary mapping the short_name to the result.
    """
    result = {}
    for metro in METRO_LIST:
        # The connection parameters are hard-coded rather than using the
        # settings files because Django doesn't yet work with multiple
        # settings files.
        connection = psycopg2.connect('user=%s dbname=%s host=%s' % (USERNAME, metro['short_name'], HOST))
        connection.set_client_encoding('UTF8')
        cursor = connection.cursor()
        cursor.execute(sql, params)
        result[metro['short_name']] = cursor.fetchall()
        connection.close()
    return result
