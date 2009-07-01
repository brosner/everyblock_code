from ebpub.geocoder.parser.parsing import normalize
from ebpub.streets.models import Suburb

def populate_suburbs(suburb_list):
    for suburb in suburb_list:
        Suburb.objects.create(name=suburb, normalized_name=normalize(suburb))

if __name__ == "__main__":
    import sys
    suburb_list = [line for line in open(sys.argv[1], 'r').read().split('\n') if line]
    populate_suburbs(suburb_list)
