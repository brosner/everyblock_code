#!/usr/bin/env python

"""
Calculates a version hash for each of static media files and stuffs
them in a cache.

There are two main ways to interact with this module. First is by
calling it, with one argument, from the commandline -- the argument
being the path to the root of the static media files. This will
populate the cache with the file version hashes.

The second way is by importing the module and calling the `lookup'
function with a single argument, that being the path of a single
static media file (path relative to the static media root, the same as
that used in the call to the commandline).
"""

import os
import sys
import md5
from django.conf import settings
from django.core.cache import cache

SALT = '1234567890'
CACHE_PREFIX = '' # Set this to your domain
EXTENSIONS = ['js', 'css', 'png', 'gif']
CACHE_TIMEOUT = 60 * 60 * 24

def media_root_join(path):
    if path.startswith('/'):
        path = path[1:]
    return os.path.join(settings.EB_MEDIA_ROOT, path)

def get_version(path, version_func=os.path.getmtime):
    """
    Returns the version for a single static media file.
    """
    try:
        return version_func(media_root_join(path))
    except OSError:
        return ''

def get_filelist():
    media_root = os.path.normpath(settings.EB_MEDIA_ROOT)
    filelist = []
    for root, dirs, files in os.walk(media_root):
        for name in files:
            (froot, ext) = os.path.splitext(name)
            if ext[1:].lower() in EXTENSIONS:
                filelist.append(os.path.join(root.replace(media_root, ''), name))
    return filelist
    
def get_versions(version_func=os.path.getmtime):
    """
    Returns a dictionary mapping filenames to their version numbers.

    Filenames are relative to the root of the static media directory.

    The kwarg `version_func' is a function that takes one argument,
    the file path, and returns a version / revision number.
    """
    return dict([(f, version_func(media_root_join(f)))
                 for f in get_filelist()])

def cache_key(filename):
    return '%s%s' % (CACHE_PREFIX, filename)

def version_hash(rev_num):
    return md5.new(str(rev_num) + SALT).hexdigest()

def cache_versions(fileversions):
    """
    Populates the cache with filenames and corresponding version
    hashes.
    
    `fileversions' is a dictionary mapping filename to version number,
    same as output of `get_versions()'.
    """
    for filename, rev_num in fileversions.iteritems():
        cache.set(cache_key(filename), version_hash(rev_num), CACHE_TIMEOUT)

def clear_cache():
    for filename in get_filelist():
        cache.delete(cache_key(filename))

def lookup(path):
    """
    Returns a version hash for a file. The `path' should be a path
    to the resource relative to the static media root, i.e., how it
    would be used in a reference in the HTML:

    >>> lookup('/scripts/maps.js')
    u'63fb5fa1cbdebb778b7396a522b9191a'
    """
    key = cache_key(path)
    vhash = cache.get(key, '')
    if not vhash:
        rev_num = get_version(path)
        if not rev_num:
            return ''
        vhash = version_hash(rev_num)
        cache.set(key, vhash, CACHE_TIMEOUT)
    return vhash

def main(argv=None):
    cache_versions(get_versions())

if __name__ == "__main__":
    sys.exit(main())
