from ebpub.db.models import Schema, NewsItem, Lookup

schema = Schema.objects.get(slug='liquor-licenses')
schema_fields = {}
for f in schema.schemafield_set.all():
    schema_fields[f.name] = f

# Run over the newsitems in reverse id order, if any duplicated were found for
# the current newsitem, delete the newsitem. This way, we will look at each
# newsitem once, and nothing will be deleted before we get to it in the loop.

for ni in NewsItem.objects.filter(schema=schema).order_by('-id').iterator():
    qs = NewsItem.objects.filter(schema=schema, item_date=ni.item_date).exclude(id=ni.id)
    qs = qs.by_attribute(schema_fields['page_id'], ni.attributes['page_id'])
    qs = qs.by_attribute(schema_fields['type'], ni.attributes['type'])

    record_type = Lookup.objects.get(pk=ni.attributes['record_type'])

    if record_type.code == 'STATUS_CHANGE':
        qs = qs.by_attribute(schema_fields['old_status'], ni.attributes['old_status'])
        qs = qs.by_attribute(schema_fields['new_status'], ni.attributes['new_status'])
    else:
        qs = qs.by_attribute(schema_fields['action'], ni.attributes['action'])

    duplicate_count = qs.count()
    if duplicate_count > 0:
        ni.delete()
        print "Deleting %s because %s duplicates were found." % (ni, duplicate_count)