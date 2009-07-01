#!/usr/bin/env python
"""
Extracts location strings and geocoder results from Civic Footprint
application log.

Example of log is below:

Attempting to geocode 4155 N Wolcott, Chicago, IL
[#<struct Geocoder::Result latitude="41.957265", longitude="-87.676214", address="4155 N WOLCOTT AVE", city="CHICAGO", state="IL", zip="60613-2681", country="US", precision="address", warning="The exact location could not be found, here is the closest match: 4155 N Wolcott Ave, Chicago, IL 60613">]
--
Attempting to geocode 2450 E 91 ST          , Chicago IL
[#<struct Geocoder::Result latitude="41.730037", longitude="-87.564174", address="2450 E 91ST ST", city="CHICAGO", state="IL", zip="60617-3822", country="US", precision="address", warning="The exact location could not be found, here is the closest match: 2450 E 91st St, Chicago, IL 60617">]
--
Attempting to geocode 2038 damen ave chicago il
[#<struct Geocoder::Result latitude="41.854524", longitude="-87.676083", address="2038 S DAMEN AVE", city="CHICAGO", state="IL", zip="60608-2625", country="US", precision="address", warning="The exact location could not be found, here is the closest match: 2038 S Damen Ave, Chicago, IL 60608">, #<struct Geocoder::Result latitude="41.918759", longitude="-87.677699", address="2038 N DAMEN AVE", city="CHICAGO", state="IL", zip="60647-4564", country="US", precision="address", warning="The exact location could not be found, here is the closest match: 2038 N Damen Ave, Chicago, IL 60647">]
--
Attempting to geocode 29 W. division st. 
Geocoding error: unable to parse location
--
"""
import re, sys

location_re = re.compile(r"Attempting to geocode (.+)$")
find_result = re.compile(r"#<struct Geocoder::Result ([^>]+?)>").findall
find_ruby_pairs = re.compile(r'([a-z]+)="([^"]+)"').findall
keys_to_delete = "precision country warning latitude longitude".split()

def extract_tests(f):
    results = []
    seen = set()
    for line in f:
        line = line.strip()
        # Records are delimited with lines containing exactly the
        # text "--"
        if line == "--": continue
        m = location_re.match(line)
        if m:
            input = m.group(1)
            # Get the next line if we've got a location string
            line = f.next().strip()
            m = find_result(line)
            if m:
                if input not in seen:
                    seen.add(input)
                else:
                    continue
                output = []
                for r in m:
                    r = dict(find_ruby_pairs(r))
                    if r["precision"] != "address" or \
                       ("city" in r and r["city"].upper() != "CHICAGO"):
                       continue
                    r["point"] = (r["latitude"], r["longitude"])
                    for k in keys_to_delete:
                        if k in r: del r[k]
                    output.append(r)
                if output:
                    results.append((input, output))
    return results

if __name__ == "__main__":
    print "cf_addrs = {"
    for (l, r) in extract_tests(sys.stdin):
        print "    %r:" % l
        print "    %r," % r
    print "}"
