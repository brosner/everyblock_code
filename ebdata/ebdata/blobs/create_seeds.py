from ebdata.blobs.models import Seed
from ebpub.db.models import Schema

def create_rss_seed(url, base_url, rss_full_entry, pretty_name, guess_article_text=True, strip_noise=False):
    if rss_full_entry:
        guess_article_text = strip_noise = False
    if 'www.' in base_url:
        normalize_www = 2
    else:
        normalize_www = 1
    Seed.objects.create(
        url=url,
        base_url=base_url,
        delay=3,
        depth=1,
        is_crawled=False,
        is_rss_feed=True,
        is_active=True,
        rss_full_entry=rss_full_entry,
        normalize_www=normalize_www,
        pretty_name=pretty_name,
        schema=Schema.objects.get(slug='news-articles'),
        autodetect_locations=True,
        guess_article_text=guess_article_text,
        strip_noise=strip_noise,
        city='',
    )
