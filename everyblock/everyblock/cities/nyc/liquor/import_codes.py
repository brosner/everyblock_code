from ebpub.db.models import Lookup, SchemaField, Schema
from ebpub.utils.text import smart_title
import re
import os.path

codes = re.compile(r"^([A-Z0-9]{3})\s+([0-9A-Z*]{1,2})\s+(.+)$").findall
schema = Schema.objects.get(slug="liquor-licenses")
schema_field = SchemaField.objects.get(schema=schema, name="license_class")
try:
    f = open(os.path.join(os.path.dirname(__file__), "codes.txt"))
    for line in f:
        class_code, license_type, name = codes(line[:-1])[0]
        name = " / ".join([smart_title(s, ["O.P."]).strip() for s in name.split("/")])
        lookup, created = Lookup.objects.get_or_create(
            schema_field=schema_field,
            name=name,
            code=class_code+"-"+license_type
        )
        if created:
            print "Created %r" % lookup
finally:
    f.close()
