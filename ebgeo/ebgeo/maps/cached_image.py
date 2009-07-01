from django.http import HttpResponse
from django.core.cache import cache

def set_cache_raw(key, data, timeout=None):
    """
    Works around a Django bug that tries to typecast a regular
    byte string as a Unicode string.
    """
    cache.set(key, (data,), timeout)

def get_cache_raw(key):
    """
    Corresponding `get` function to the `raw_cache_set` workaround
    """
    data = cache.get(key)
    if data is not None:
        return data[0]

class CachedImageResponse(HttpResponse):
    def __init__(self, key, image_gen_fn, expiry_seconds=None, mimetype='image/png'):

        img_bytes = get_cache_raw(key)

        if img_bytes is None:
            img_bytes = image_gen_fn()
            set_cache_raw(key, img_bytes, expiry_seconds)
        
        super(CachedImageResponse, self).__init__(content=img_bytes,
                                                  mimetype=mimetype)
