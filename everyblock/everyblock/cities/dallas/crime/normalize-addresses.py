from ebpub.db.models import NewsItem
from retrieval import StreetNormalizer # relative import

def normalize():
    normalizer = StreetNormalizer()
    for ni in NewsItem.objects.filter(schema__slug='crime-reports').iterator():
        block, direction, street = ni.attributes['street'].split(';')
        record = {
            'offensestreet': street,
            'offenseblock': block,
            'offensedirection': direction,
        }
        normalized_address = normalizer.normalize_address(record)
        if ni.location_name != normalized_address:
            ni.location_name = normalized_address
            ni.save()
            print ni.attributes['street']
            print normalized_address
    normalizer.print_stats()

if __name__ == "__main__":
    normalize()
