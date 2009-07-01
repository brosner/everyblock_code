from django.contrib.admin import ModelAdmin, site
from ebblog.blog.models import Entry

class EntryAdmin(ModelAdmin):
    list_display = ('pub_date', 'headline', 'author')

site.register(Entry, EntryAdmin)
