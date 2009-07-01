"""
Helper functions for manually adding news article NewsItems.
"""

from ebdata.blobs.models import Seed, Page
from ebdata.retrieval import UnicodeRetriever
from ebpub.db.models import Schema
from ebpub.geocoder import SmartGeocoder
from geotagging import geotag_page # relative import
import datetime

def add_newsitem(seed_url, seed_name, url, article_headline, article_date, name_excerpts):
    schema = Schema.objects.get(slug='news-articles')
    geocoder = SmartGeocoder()
    try:
        s = Seed.objects.get(url=seed_url)
    except Seed.DoesNotExist:
        s = Seed.objects.create(
            url=seed_url,
            base_url=seed_url,
            delay=0,
            depth=0,
            is_crawled=False,
            is_rss_feed=False,
            is_active='t',
            rss_full_entry=False,
            normalize_www=3,
            pretty_name=seed_name,
            schema=schema,
            autodetect_locations=True,
            guess_article_text=False,
            strip_noise=False,
            city='',
        )
    try:
        p = Page.objects.get(url=url)
    except Page.DoesNotExist:
        html = UnicodeRetriever().get_html(url)
        p = Page.objects.create(
            seed=s,
            url=url,
            scraped_url=url,
            html=html,
            when_crawled=datetime.datetime.now(),
            is_article=True,
            is_pdf=False,
            is_printer_friendly=False,
            article_headline=article_headline,
            article_date=article_date,
            has_addresses=None,
            when_geocoded=None,
            geocoded_by='',
            times_skipped=0,
            robot_report=''
        )
    data_tuples = []
    for location_name, excerpt in name_excerpts:
        point = geocoder.geocode(location_name) # Let exceptions bubble up.
        data_tuples.append((location_name, point['point'], excerpt, point['block']))
    return geotag_page(p.id, seed_name, schema, url, data_tuples, article_headline, article_date)
