from django.db import models
from ebpub.db.models import Schema

class HiddenSchema(models.Model):
    user_id = models.IntegerField()
    schema = models.ForeignKey(Schema)

    def _get_user(self):
        if not hasattr(self, '_user_cache'):
            from ebpub.accounts.models import User
            try:
                self._user_cache = User.objects.get(id=self.user_id)
            except User.DoesNotExist:
                self._user_cache = None
        return self._user_cache
    user = property(_get_user)

    def __unicode__(self):
        return u'<HiddenSchema %s for user %s>' % (self.user_id, self.schema.slug)
