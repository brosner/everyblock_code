==========
everyblock
==========

This package contains code/templates that are specific to EveryBlock.com. They
are released to fulfill the terms of the grant that funded EveryBlock's
development and are likely not of general use.

Overview
========

The package is split into these directories:

    admin -- EveryBlock's internal admin application for managing its data
    cities -- City-specific data-acquisition scripts (for 15 U.S. cities)
    media -- CSS file for the admin
    states -- State-specific data-acquisition scripts
    staticmedia -- A Django template tag specific to EveryBlock.com media files
    templates -- Templates for the admin
    utils -- Various utilities used on EveryBlock.com

Quickstart
==========

0. Install PostgreSQL, PostGIS, Django, psycopg2.

1. Install the everyblock package by putting it on your Python path. Also
   install the ebdata, ebpub and ebgeo packages.

2. Start a Django project.

3. Put the smorgasbord of eb-specific settings in your settings file. It's
   probably easiest to just start with the file ebpub/settings.py and tweak
   that (or import from it in your own settings file). The application won't
   work until you set the following:

       DATABASE_USER
       DATABASE_NAME
       DATABASE_HOST
       DATABASE_PORT
       SHORT_NAME
       PASSWORD_CREATE_SALT
       PASSWORD_RESET_SALT
       METRO_LIST
       EB_MEDIA_ROOT
       EB_MEDIA_URL

   See the documentation/comments in ebpub/settings.py for info on what the
   various settings mean.

4. Run "django-admin.py syncdb" to create all of the database tables.

5. Run "django-admin.py runserver" and go to http://127.0.0.1:8000/ in your
   Web browser to see the site in action.
