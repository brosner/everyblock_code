from django.db import models
from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper
from django.conf import settings
from django.contrib.gis.db.models import GeoManager as BaseGeoManager
from django.core import signals

# Global that keeps the currently open connections, keyed by connection_name.
connections = {}

# Close all the connections after every request.
def close_connections(**kwargs):
    for conn in connections.values():
        conn.close()
signals.request_finished.connect(close_connections)

# Based loosely on http://www.eflorenzano.com/blog/post/easy-multi-database-support-django/
class Manager(models.Manager):
    """
    This Manager lets you set database connections on a per-model basis.
    """
    def __init__(self, connection_name, *args, **kwargs):
        # connection_name should correspond to a key in the DATABASES setting.
        models.Manager.__init__(self, *args, **kwargs)
        self.connection_name = connection_name
        self.database_settings = settings.DATABASES[connection_name] # Let KeyError propogate.

    def get_query_set(self):
        qs = models.Manager.get_query_set(self)
        try:
            # First, check the global connection dictionary, because this
            # connection might have already been created.
            conn = connections[self.connection_name]
        except KeyError:
            conn = DatabaseWrapper(self.database_settings)
            connections[self.connection_name] = conn
        qs.query.connection = conn
        return qs

    # TODO: Override _insert() to get inserts/updates/deletions working.

class GeoManager(BaseGeoManager):
    """
    Subclass of django.contrib.gis's GeoManager that lets you set database
    connections on a per-model basis.
    """
    def __init__(self, connection_name, *args, **kwargs):
        BaseGeoManager.__init__(self, *args, **kwargs)
        self.connection_name = connection_name
        self.database_settings = settings.DATABASES[connection_name]

    def get_query_set(self):
        qs = BaseGeoManager.get_query_set(self)
        try:
            # First, check the global connection dictionary, because this
            # connection might have already been created.
            conn = connections[self.connection_name]
        except KeyError:
            conn = DatabaseWrapper(self.database_settings)
            connections[self.connection_name] = conn
        qs.query.connection = conn
        return qs
