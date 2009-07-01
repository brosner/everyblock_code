from django.db import models
from ebpub.db.models import Location
from ebpub.streets.models import Block

class ActiveAlertsManager(models.Manager):
    def get_query_set(self):
        return super(ActiveAlertsManager, self).get_query_set().filter(is_active=True)

class EmailAlert(models.Model):
    user_id = models.IntegerField()
    block = models.ForeignKey(Block, blank=True, null=True)
    location = models.ForeignKey(Location, blank=True, null=True)
    frequency = models.PositiveIntegerField() # 1=daily, 7=weekly
    radius = models.PositiveIntegerField(blank=True, null=True)

    # If True, schemas should be treated as an exclusion list instead of an
    # inclusion list. This allows people to exclude existing schemas, but
    # but still receive updates for new schemas when we add them later.
    include_new_schemas = models.BooleanField()

    # A comma-separated list of schema IDs. Semantics depend on the value of
    # include_new_schemas (see above comment).
    schemas = models.TextField()

    signup_date = models.DateTimeField()
    cancel_date = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField()

    objects = models.Manager()
    active_objects = ActiveAlertsManager()

    def __unicode__(self):
        return u'User %s: %u' % (self.user_id, self.name())

    def unsubscribe_url(self):
        return '/alerts/unsubscribe/%s/' % self.id

    def name(self):
        if self.block:
            return u'%s block%s around %s' % (self.radius, (self.radius != 1 and 's' or ''), self.block.pretty_name)
        else:
            return self.location.pretty_name

    def pretty_frequency(self):
        return {1: 'daily', 7: 'weekly'}[self.frequency]

    def _get_user(self):
        if not hasattr(self, '_user_cache'):
            from ebpub.accounts.models import User
            try:
                self._user_cache = User.objects.get(id=self.user_id)
            except User.DoesNotExist:
                self._user_cache = None
        return self._user_cache
    user = property(_get_user)
