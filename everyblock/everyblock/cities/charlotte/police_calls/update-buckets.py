from ebpub.db.models import NewsItem, SchemaField, Lookup
from everyblock.cities.charlotte.police_calls.retrieval import CATEGORIES
from django.template.defaultfilters import capfirst

if __name__ == '__main__':
    schema_slug = 'police-calls'
    schema_field = SchemaField.objects.get(schema__slug=schema_slug, name='category')
    for ni in NewsItem.objects.filter(schema__slug=schema_slug):
        event = Lookup.objects.get(pk=ni.attributes['event'])
        category_code = CATEGORIES[event.name.upper()]
        category_name = capfirst(category_code.lower())
        bucket = Lookup.objects.get_or_create_lookup(schema_field, category_name, category_code)
        old_bucket_id = ni.attributes['category']
        if old_bucket_id is None or bucket.id != old_bucket_id:
            ni.attributes['category'] = bucket.id
            print "Bucket changed"
            print old_bucket_id
            print bucket
