from django.db import connection, transaction
from ebpub.db.models import Schema
import sys

def set_schema_min_date(schema):
    """
    Sets the schema's min_date to the earliest item_date found in news items.
    """
    cursor = connection.cursor()
    cursor.execute("""
        update db_schema
              set min_date = (select min(item_date) from db_newsitem where schema_id=%s)
          where id=%s;
    """, (schema.id, schema.id))
    transaction.commit_unless_managed()

def fix_initial_pub_dates(schema):
    """
    Sets pub_date equal to item_date for the earliest import of the given schema.
    """
    cursor = connection.cursor()
    cursor.execute("""
        update db_newsitem
              set pub_date = item_date
         where pub_date = (select min(pub_date) from db_newsitem where schema_id=%s)
             and schema_id=%s;
    """, (schema.id, schema.id))
    transaction.commit_unless_managed()

def activate_schema(schema):
    """
    Fixes the given schema's min_date, its news item pub_dates, and makes it
    public.
    """
    fix_initial_pub_dates(schema)
    set_schema_min_date(schema)
    # Re-fetch the schema so we don't overwrite the previous changes.
    schema = Schema.objects.get(pk=schema.pk)
    schema.is_public = True
    schema.save()

if __name__ == '__main__':
    try:
        schema = Schema.objects.get(slug__exact=sys.argv[1])
    except Schema.DoesNotExist:
        print "Schema with slug %s could not be found." % sys.argv[1]
        sys.exit(-1)
    activate_schema(schema)
    print "%s: fixed schema.min_date, associated pub_dates, and set is_public=True." % schema.slug
