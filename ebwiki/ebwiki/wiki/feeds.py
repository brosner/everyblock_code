from django.contrib.syndication.feeds import Feed
from django.utils.feedgenerator import Atom1Feed
from ebwiki.wiki.models import Page

class LatestEdits(Feed):
    title = "ebwiki"
    link = "/"
    subtitle = "Latest edits made to the ebwiki."
    title_template = "wiki/feeds/latest_title.html"
    description_template = "wiki/feeds/latest_description.html"

    feed_type = Atom1Feed

    def items(self):
        return Page.objects.order_by("-change_date")[:30]

    def item_link(self, item):
        return item.version_url()

    def item_author_name(self, item):
        return item.change_user

    def item_pubdate(self, item):
        return item.change_date
