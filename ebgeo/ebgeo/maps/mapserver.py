import sys
import os.path
from cStringIO import StringIO
from mapnik import *
from django.conf import settings
import PIL.Image
from ebgeo.maps import bins
from ebgeo.maps.constants import TILE_SIZE

def xml_path(maptype):
    path = os.path.join(sys.prefix, 'mapnik', '%s.xml' % maptype)
    return path

def get_mapserver(maptype):
    return {
        'main': MainMap,
        'locator': LocatorMap,
        'thematic': ThematicMap,
        'homepage': HomepageMap
    }[maptype]

class MapServer(Map):
    """
    A simple wrapper class around Mapnik's Map that provides a little
    friendlier interface to setting up a basic map and for common
    tasks.
    """
    def __init__(self, proj4, width=None, height=None):
        width = width or TILE_SIZE
        height = height or TILE_SIZE
        super(MapServer, self).__init__(width, height, '+init=epsg:900913')
        load_map(self, xml_path(self.maptype))

    def zoom_to_bbox(self, minx, miny, maxx, maxy):
        """
        Zooms map to bounding box - convenience method
        """
        return self.zoom_to_box(Envelope(minx, miny, maxx, maxy))

    def render_image(self, mimetype='image/png'):
        """
        Renders the map as an Mapnik image
        """
        img = Image(self.width, self.height)
        render(self, img)
        return img

    def get_graphic(self, mapnik_img, mimetype='image/png'):
        """
        Returns the raw bytes of graphic in the target format (PNG, JPG, GIF,
        etc.)
        """
        img = PIL.Image.fromstring('RGBA', (self.width, self.height), mapnik_img.tostring())
        buf = StringIO()
        if mimetype.find('/') != -1:
            format = mimetype.split('/')[1]
        else:
            format = mimetype
        img.save(buf, format)
        try:
            return buf.getvalue()
        finally:
            buf.close()

    def export_pdf(self, filename):
        """
        Renders map as a PDF, exporting to file given.
        """
        import cairo
        surface = cairo.PDFSurface(filename, self.width, self.height)
        render(self, surface)

    def create_layer(self, layer_name, style_name, postgis_table):
        """
        Convenience shortcut method for setting up a new layer with
        a defined style and PostGIS table name.
        """
        layer = Layer(layer_name)
        layer.datasource = PostGIS(host=settings.MAPS_POSTGIS_HOST, user=settings.MAPS_POSTGIS_USER, password=settings.MAPS_POSTGIS_PASS, dbname=settings.MAPS_POSTGIS_DB, table=postgis_table)
        layer.styles.append(style_name)
        return layer 

    def add_layer(self, layer_name, style_name, postgis_table, skip_if_missing=True):
        layer = self.create_layer(layer_name, style_name, postgis_table)
        self.layers.append(layer)

    def draw_map(self):
        raise NotImplementedError('subclasses must implement draw_map() method')

    def __call__(self, mimetype='image/png'):
        self.draw_map()
        img = self.render_image()
        return self.get_graphic(img, mimetype)

class MainMap(MapServer):
    maptype = 'main'

    def draw_map(self):
        self.add_layer('coastline', 'coastline', 'coastlines')
        self.add_layer('city', 'city-fill', 'cities')
        self.add_layer('major-water', 'water', 'water')
        self.add_layer('landmarks', 'landmarks', 'landmarks')
        self.add_layer('airports', 'airports', 'airports')
        self.add_layer('parks', 'parks', 'parks')

        # Streets
        streets = Layer('streets')
        streets.datasource = PostGIS(host=settings.MAPS_POSTGIS_HOST, user=settings.MAPS_POSTGIS_USER, password=settings.MAPS_POSTGIS_PASS, dbname=settings.MAPS_POSTGIS_DB, table='streets')
        # Add street styles -- order matters
        for style in [
            'road-fill',
            'arterial-fill',
            'highway-fill',
            'ramp-border',
            'ramp-fill',
            'interstate-border',
            'interstate-fill',
            'road-label',
            'arterial-label',
            'highway-label',
            'interstate-label'
        ]:
            streets.styles.append(style)
        self.layers.append(streets)

        self.add_layer('neighborhoods', 'neighborhoods', 'neighborhoods')
        self.add_layer('city-border', 'city-border', 'city')

class LocatorMap(MapServer):
    maptype = 'locator'

    def draw_map(self):
        self.add_layer('city', 'city-fill', 'cities')

class HomepageMap(LocatorMap):
    maptype = 'homepage'

# TODO: Move this somewhere else.
BINNING_METHOD = bins.EqualSize

# TODO: Move this to a config file, maybe subclass from a generic ColorTheme class.
class GreenTheme:
    no_value = '#D9FCC3'
    range = ['#D9FCC3', '#A0E673', '#5ACC2D', '#22944E', '#13552D']
    border = '#C0CCC4'

class ThematicMap(MapServer):
    """
    Generates a cloropleth or "thematic" map for a LocationType.

    Data values are given as a dict, and keys are ids of the Location objects
    that comprise the LocationType.
    """
    maptype = 'thematic'

    def __init__(self, location_type, theme_data, key_field, colors=None, num_bins=5, **kwargs):
        super(ThematicMap, self).__init__(**kwargs)
        self.location_type = location_type
        self.theme_data = theme_data
        self.key_field = key_field
        self.colors = colors or GreenTheme
        num_bins = num_bins or len(self.colors.range)
        self.bins = BINNING_METHOD(theme_data.values(), num_bins)

    def draw_map(self):
        style = Style()
        # Add a default Rule for features that aren't in the values list
        default_rule = Rule()
        default_rule.symbols.append(PolygonSymbolizer(Color(self.colors.no_value)))
        default_rule.symbols.append(LineSymbolizer(Color(self.colors.border), 1.0))
        style.rules.append(default_rule)
        # TODO: Instead of one rule per object, compose a filter
        # expression for the objects with the same value; also, contend
        # with string v. numeric in the DBF
        for key, value in self.theme_data.iteritems():
            rule = Rule()
            # The Mapnik C++ signature requires strings, not Unicode
            filter_exp = "[%s] = '%s'" % (self.key_field, str(key))
            rule.filter = Filter(filter_exp)
            color = self.colors.range[self.bins.which_bin(value)]
            rule.symbols.append(PolygonSymbolizer(Color(color)))
            rule.symbols.append(LineSymbolizer(Color(self.colors.border), 1.0))
            style.rules.append(rule)
        self.append_style('theme', style)
        layer = Layer('theme')
        layer.datasource = LocationDatasource(self.location_type)
        layer.styles.append('theme')
        self.layers.append(layer)

def LocationDatasource(location_type):
    """
    Use ebpub.db.Location objects as a datasource for Mapnik layers.
    """
    table_sql = """\
        (SELECT * FROM db_location WHERE location_type_id = %s) AS db_location
    """.strip() % (location_type.id,)
    host = settings.DATABASE_HOST and settings.DATABASE_HOST or settings.MAPS_POSTGIS_HOST
    port = settings.DATABASE_PORT and settings.DATABASE_PORT or 5432
    return PostGIS(host=host,
                   port=port,
                   dbname=settings.DATABASE_NAME,
                   user=settings.DATABASE_USER,
                   password=settings.DATABASE_PASSWORD,
                   table=str(table_sql), # Mapnik can't handle any Unicode
                   estimate_extent=True)
