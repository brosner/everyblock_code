#!/usr/bin/env python
import sys
from ebpub.db.models import Location

def alphabetize_locations(location_type_slug=None):
    if location_type_slug is None:
        location_type_slug = 'neighborhoods'
    for i, loc in enumerate(Location.objects.filter(location_type__slug=location_type_slug).order_by('name').iterator()):
        print loc.name
        loc.display_order = i
        loc.save()

if __name__ == "__main__":
    location_type_slug = len(sys.argv[1:]) and sys.argv[1] or None
    sys.exit(alphabetize_locations(location_type_slug))
