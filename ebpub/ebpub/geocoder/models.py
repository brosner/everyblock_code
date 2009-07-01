from django.contrib.gis.db import models
from ebpub.streets.models import Block
from ebpub.streets.models import Intersection

class GeocoderCache(models.Model):
    normalized_location = models.CharField(max_length=255, db_index=True)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=255)
    state = models.CharField(max_length=2)
    zip = models.CharField(max_length=10)
    location = models.PointField()
    block = models.ForeignKey(Block, blank=True, null=True)
    intersection = models.ForeignKey(Intersection, blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    objects = models.GeoManager()

    def __unicode__(self):
        return self.normalized_location

    @classmethod
    def populate(cls, normalized_location, address):
        """
        Populates the cache from an Address object.
        """
        if address['point'] is None:
            return
        obj = cls()
        obj.normalized_location = normalized_location
        for field in ('address', 'city', 'state', 'zip'):
            setattr(obj, field, address[field])
        for relation in ['block', 'intersection_id']:
            if relation in address:
                setattr(obj, relation, address[relation])
        obj.location = address['point']
        obj.save()
