======
ebblog
======

The blog application used by http://blog.everyblock.com

Requirements
============

A recent Django release. It has been tested with Django revision 11079 from
Subversion. When Django 1.1 is released, that should work as well.

Quickstart
==========

0. Install Django.

1. Install the ebblog package by putting it on your Python path.

2. Start a Django project (using Django 1.1, not 1.0). See the Django Book and
   Django docs for more:

       http://djangobook.com/en/2.0/
       http://docs.djangoproject.com/en/dev/

3. Update your settings file. It's probably easiest to just start with the
   file ebblog/settings.py and tweak that (or import from it in your own
   settings file). The application won't work until you set the following:

       DATABASE_USER
       DATABASE_NAME
       DATABASE_HOST
       DATABASE_PORT

   If you decide not to start with ebblog.settings, you'll also need to add
   ebblob.urls to your URLconf and add the absolute path to ebblog/templates
   to your TEMPLATE_DIRS setting.

4. Run "django-admin.py syncdb" to create all of the database tables.

5. Run "django-admin.py runserver" and go to http://127.0.0.1:8000/ in your
   Web browser to see the site in action. Go to http://127.0.0.1:8000/admin/
   to add and edit blog entries.

Customization
=============

The title, description, and link of the RSS feed should be set in
ebblog/blog/feeds.py. Also, most of the visual customization can be
accomplished by editing ebblog/templates/base.html. All of the other templates
inherit from base.html, so any styles added there will apply to the other
pages.
