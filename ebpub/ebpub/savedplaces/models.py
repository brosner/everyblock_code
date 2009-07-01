from django.db import models
from ebpub.db.models import Location
from ebpub.streets.models import Block

class SavedPlace(models.Model):
    user_id = models.IntegerField()
    block = models.ForeignKey(Block, blank=True, null=True)
    location = models.ForeignKey(Location, blank=True, null=True)
    nickname = models.CharField(max_length=128, blank=True)

    def __unicode__(self):
        return u'User %s: %u' % (self.user_id, self.place.pretty_name)

    def _get_place(self):
        return self.block_id and self.block or self.location
    place = property(_get_place)

    def _get_user(self):
        if not hasattr(self, '_user_cache'):
            from ebpub.accounts.models import User
            try:
                self._user_cache = User.objects.get(id=self.user_id)
            except User.DoesNotExist:
                self._user_cache = None
        return self._user_cache
    user = property(_get_user)

    def pid(self):
        if self.block_id:
            return 'b:%s.8' % self.block_id
        else:
            return 'l:%s' % self.location_id
