from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Rss201rev2Feed
from ebblog.blog.models import Entry

# RSS feeds powered by Django's syndication framework use MIME type
# 'application/rss+xml'. That's unacceptable to us, because that MIME type
# prompts users to download the feed in some browsers, which is confusing.
# Here, we set the MIME type so that it doesn't do that prompt.
class CorrectMimeTypeFeed(Rss201rev2Feed):
    mime_type = 'application/xml'

# This is a django.contrib.syndication.feeds.Feed subclass whose feed_type
# is set to our preferred MIME type.
class BlogFeed(Feed):
    feed_type = CorrectMimeTypeFeed

class BlogEntryFeed(Feed):
    title = ""
    link = ""
    description = ""

    def items(self):
        return Entry.objects.order_by('-pub_date')[:10]

    def item_link(self, item):
        return item.url()

    def item_pubdate(self, item):
        return item.pub_date
