from django.conf import settings
from django.contrib.gis.db import models
from ebpub.utils import multidb

class MetroManager(multidb.GeoManager):
    def get_current(self):
        return self.get(short_name=settings.SHORT_NAME)

    def containing_point(self, point):
        # First pass, just check to see if it's in the bounding box --
        # this is faster for checking across all metros
        metros = self.filter(location__bbcontains=point)
        n = metros.count()
        if not n:
            raise Metro.DoesNotExist()
        else:
            # Now do the slower but more accurate lookup to see if the
            # point is completely within the actual bounds of the
            # metro. Note that we could also have hit two or more
            # metros if they have overlapping bounding boxes.
            matches = 0
            for metro in metros:
                if metro.location.contains(point):
                    matches += 1
            if matches > 1:
                # Something went wrong, it would mean the metros have
                # overlapping borders
                raise Exception('more than one metro found to contain this point')
            elif matches == 0:
                raise Metro.DoesNotExist()
            else:
                return metro

class Metro(models.Model):
    name = models.CharField(max_length=64)
    short_name = models.CharField(max_length=64, unique=True)
    metro_name = models.CharField(max_length=64)
    population = models.IntegerField(null=True, blank=True)
    area = models.IntegerField(null=True, blank=True)
    is_public = models.BooleanField(default=False)
    multiple_cities = models.BooleanField(default=False)
    state = models.CharField(max_length=2)
    state_name = models.CharField(max_length=64)
    location = models.MultiPolygonField()
    objects = MetroManager('metros')

    def __unicode__(self):
        return self.name

    class Meta:
        unique_together = ('name', 'state')
