from django.db import models

class City(models.Model):
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=2, blank=True)

    def __unicode__(self):
        return self.pretty_name

    def pretty_name(self):
        if self.state:
            return u'%s, %s' % (self.city, self.state)
        return self.city

    def url(self):
        return '/citypoll/%s/' % self.id

class Vote(models.Model):
    # The "normalized" version of the requested city.
    city = models.ForeignKey(City, blank=True, null=True)

    # The raw data that's submitted to us.
    city_text = models.CharField(max_length=64)
    email = models.CharField(max_length=128)
    notes = models.TextField()

    # Metadata about the submission.
    ip_address = models.CharField(max_length=225, blank=True) # Might be comma-separated list.
    date_received = models.DateTimeField()

    def __unicode__(self):
        return u'%s at %s' % (self.city_text, self.date_received)
