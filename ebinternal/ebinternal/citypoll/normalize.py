from ebinternal.citypoll.models import Vote

def normalize_cities():
    total = 0
    for v in Vote.objects.distinct().filter(city__id__isnull=False).values('city_text', 'city'):
        total += Vote.objects.filter(city__id__isnull=True, city_text__iexact=v['city_text']).update(city=v['city'])
    return total

if __name__ == "__main__":
    print normalize_cities()
