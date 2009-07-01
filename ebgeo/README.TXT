=====
ebgeo
=====

The eb map system. The ebgeo package provides for two main bits of
functionality:

 1. A `maps' subpackage for rendering map tiles with Mapnik, and

 2. A `utils' subpackage which is a collection of useful modules when
    working with geospatial data, including clustering.

Requirements
============

Mapnik version 0.6.0 or greater -- http://mapnik.org/
TileCache 2.10 -- http://tilecache.org/
processing 0.50 or greater (optional) -- http://pypi.python.org/pypi/processing

Background
==========

You should be familiar with the mapping toolkit Mapnik before getting
started with this package. Installation of Mapnik is non-trivial,
although it has gotten easier over time. You'll also need to provide
your own styles for the map tiles, which means creating Mapnik style
XML. Cascadenik_ provides a CSS-like syntax that compiles to Mapnik
XML; you may find this an friendy way to get started creating styles:

.. _Cascadenik: http://code.google.com/p/mapnik-utils/wiki/Cascadenik

You'll also be responsible for your own source geospatial data. This
is a database of features (i.e., individual roads, parks, bodies of
water, etc.) with attributes (i.e., road types, areas of parks, names
and labels, etc.) that Mapnik queries and, combined with styles
defined in the Mapnik XML format, represents in the graphical output
of the rendering engine. There are two main freely available sources
of streets data, TIGER/Line_ (produced by the Census for U.S. streets)
and OpenStreetMap_ (a user-contributed database of streets
world-wide).

.. _TIGER/Line: http://www.census.gov/geo/www/tiger/
.. _OpenStreetMap: http://www.openstreetmap.org/

Geospatial data
---------------

Mapnik provides a number of different ways to access geospatial data,
from shapefiles to PostGIS databases. The ebgeo code assumes that your
data is stored in a PostGIS database. It also makes some assumptions
about which layers and attribute field names are defined. The
ebgeo.maps.mapserver module source code should be your reference for
this information; refer to the draw_map() method.

Installation
============

After downloading the ebgeo tarball and unpacking, put the ebgeo package
on your Python path. Then create a directory called "mapnik" within your
`sys.prefix` directory (which you can get by running
"python -c 'import sys; print sys.prefix'"). This is the directory where
you should place your Mapnik style XML files.

Rendering map tiles
===================

The `render_tiles' executable iterates over a number of zoom levels
and renders the map tiles contained within.

    Usage: render_tiles [<options>] /path/to/config <layername>
    
    Options:
      -h, --help            show this help message and exit
      -s START, --start=START
                            starting zoom level
      -t STOP, --stop=STOP  ending zoom level
      -c CITY, --city=CITY  only render this city's tiles (use city slug)
      -v, --verbose         
      -D, --debug           
      -n NUM_PROCS, --num-procs=NUM_PROCS
                            number of render processes (defaults to 1)

The /path/to/config argument is a path to a TileCache config. Please
see the TileCache docs for the syntax, which is a .ini-type file.

The <layername> argument is a string that should match a defined layer
section in the TileCache config file and the Mapnik style XML
filename.

The -s and -t options indicate the starting and stopping zoom level
for rendering. The starting, -s, option is inclusive: in other words,
if the value of -s is 1, the rendering will start at level 1. However,
the stopping, -t, option is exclusive: in other words, if the value of
-t is 10, the rendering will stop upon completing level 9. The number
of zoom levels is defined in the TileCache config.

The -c option allows you to constrain tile rendering to the bounding
box of a city defined in your application. The value of -c is the slug
that represents that city. (See ebpub.metros)

The -n options allows you to spread rendering over multiple CPUs,
utilizing the great Python package `processing.'

Dynamic map tiles
=================

There's an alternate way to view map tiles other than rendering them
first and serving them statically. ebgeo.maps.views has a get_tile()
view that will render individual tiles and serve them directly to the
requesting browser. See ebgeo.maps.urls for the URLconf that wires up
a URL request to the get_tile() view.