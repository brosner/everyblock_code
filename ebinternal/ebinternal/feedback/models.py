from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=64)

    def __unicode__(self):
        return self.name

class Feedback(models.Model):
    # Stuff that's added when the feedback is created.
    city = models.CharField(max_length=32, blank=True)
    page_url = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    ip_address = models.CharField(max_length=225, blank=True) # Might be comma-separated list.
    email = models.CharField(max_length=255, blank=True)
    date_received = models.DateTimeField()

    # Stuff that's added by our staff.
    assigned_to = models.CharField(max_length=32, blank=True)
    date_responded = models.DateTimeField(blank=True, null=True)
    responder = models.CharField(max_length=32, blank=True)
    is_awesome = models.BooleanField()
    is_ignored = models.BooleanField()
    category = models.ForeignKey(Category)

    def __unicode__(self):
        return u'#%s: From %s' % (self.id, self.email or 'anonymous')

    def url(self):
        return '/feedback/%s/' % self.id

class Response(models.Model):
    feedback = models.ForeignKey(Feedback)
    date_sent = models.DateTimeField()
    to_email = models.CharField(max_length=255)
    from_email = models.CharField(max_length=255)
    message = models.TextField()

    def __unicode__(self):
        return unicode(self.id)

class CannedResponse(models.Model):
    name = models.CharField(max_length=128)
    message = models.TextField()

    def __unicode__(self):
        return self.name
