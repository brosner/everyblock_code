==========
ebinternal
==========

Internal applications for the EveryBlock team.

ebinternal consists of two apps, citypoll and feedback.

citypoll powers EveryBlock's city voting system, both on EveryBlock.com and on
the iPhone app.

feeback manages the feedback received from the feedback forms at the bottom
of almost every page on EveryBlock.com.

Quickstart
==========

0. Install Django.

1. Install the ebinternal package by putting it on your Python path.

2. Start a Django project (using Django 1.1, not 1.0). See the Django Book and
   Django docs for more:

       http://djangobook.com/en/2.0/
       http://docs.djangoproject.com/en/dev/

3. Update your settings file. It's probably easiest to just start with the
   file ebinternal/settings.py and tweak that (or import from it in your own
   settings file). The application won't work until you set the following:

       DATABASE_USER
       DATABASE_NAME
       DATABASE_HOST
       DATABASE_PORT
       EMAIL_HOST (for sending responses from the feedback application)
       EB_FROM_EMAIL
       EB_STAFF

   If you decide not to start with ebinternal.settings you'll also need to add
   ebinternal.urls to your urlconf and add the absolute path to
   ebinternal/templates to your TEMPLATE_DIRS setting.

4. Run "django-admin.py syncdb" to create all of the database tables.

5. Run "django-admin.py runserver" and go to http://127.0.0.1:8000/ in your
   Web browser to see the site in action.
