from django.contrib.gis.gdal import DataSource

class EsriImporter(DataSource):
    def __init__(self, shapefile, model, ...)
