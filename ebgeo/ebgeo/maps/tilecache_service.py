import re
import subprocess
import tempfile
from TileCache.Service import Service, Request, TileCacheException
from TileCache.Caches.Disk import Disk
import TileCache.Layer as Layer

request_pat = r'/(?P<version>\d{1,2}\.\d{1,3})/(?P<layername>[a-z]{1,64})/(?P<z>\d{1,10})/(?P<x>\d{1,10}),(?P<y>\d{1,10})\.(?P<extension>(?:png|jpg|gif))'
request_re = re.compile(request_pat)

class PostRenderingError(Exception):
    pass

class EBRequest(Request):
    def _parse_path(self, path):
        m = request_re.search(path)
        if not m:
            raise TileCacheException('unexpected request path format %r: should '
                                     'be of form /version/layername/z/x,y.ext' % path)
        else:
            return m.groups()

    def parse(self, fields, path, host):
        # /1.0/main/0/0,0.png -> /version/layername/z/x,y.ext
        version, layername, z, x, y, extension = self._parse_path(path)
        layer = self.getLayer(layername)
        return Layer.Tile(layer, int(x), int(y), int(z))

class EBService(Service):
    def dispatchRequest(self, params, path_info='/', req_method='GET',
                        host='http://example.com/'):
        tile = EBRequest(self).parse(params, path_info, host)
        if isinstance(tile, Layer.Tile):
            if req_method == 'DELETE':
                self.expireTile(tile)
                return ('text/plain', 'OK')
            else:
                return self.renderTile(tile)
        else:
            return (tile.format, tile.data)

class EBCache(Disk):
    def set(self, tile, data):
        data = optimize_png(data)
        Disk.set(self, tile, data)

def optimize_png(data):
    """
    Optimize a PNG's file size with optipng(1).
    """
    # Create a named temp file with the PNG data because optipng doesn't read
    # from stdin.
    temp_f = tempfile.NamedTemporaryFile(prefix='evb', suffix='.png')
    temp_f.file.write(data)
    temp_f.file.flush()
    try:
        rc = subprocess.call(['optipng', '-q', temp_f.name])
        if rc < 0:
            raise PostRenderingError('optipng was terminated by signal %s' % -rc)
        elif rc != 0:
            raise PostRenderingError('optipng returned non-zero %s' % rc)
    except OSError, e:
        PostRenderingError('optipng execution failed: %s' % e)
    opt_f = open(temp_f.name, 'r')
    try:
        return opt_f.read()
    finally:
        opt_f.close()
        temp_f.close()
