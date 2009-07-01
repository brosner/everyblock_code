from django.db import models
from ebpub.utils import multidb
import utils # relative import

class UserManager(multidb.Manager):
    # This method is necessary because ebpub.utils.multidb doesn't support
    # inserts or updates -- only reads.
    # TODO: Remove this once multidb gets that feature.
    def create_user(self, **kwargs):
        from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper
        connection = DatabaseWrapper(self.database_settings)
        cursor = connection.cursor()
        opts = self.model._meta
        fields = [f for f in opts.fields if f.name != 'id']
        try:
            kwargs['password'] = utils.make_password_hash(kwargs['password'])
            values = [kwargs[f.name] for f in fields]
        except KeyError, e:
            raise ValueError('Missing field: %s' % e)
        cursor.execute("INSERT INTO %s (%s) VALUES (%s)" % \
            (opts.db_table, ','.join([f.column for f in fields]), ','.join(['%s' for i in xrange(len(fields))])),
            values)
        cursor.execute("SELECT CURRVAL('\"%s_id_seq\"')" % opts.db_table)
        user_id = cursor.fetchone()[0]
        connection._commit()
        connection.close()
        return User.objects.get(id=user_id)

    def set_password(self, user_id, raw_password):
        from django.db.backends.postgresql_psycopg2.base import DatabaseWrapper
        connection = DatabaseWrapper(self.database_settings)
        cursor = connection.cursor()
        password = utils.make_password_hash(raw_password)
        cursor.execute("UPDATE %s SET password=%%s WHERE id=%%s" % self.model._meta.db_table,
            (password, user_id))
        connection._commit()
        connection.close()

    def user_by_password(self, email, raw_password):
        """
        Returns a User object for the given e-mail and raw password. If the
        e-mail address exists but the password is incorrect, returns None.
        """
        try:
            user = self.get(email=email)
        except self.model.DoesNotExist:
            return None
        if user.check_password(raw_password):
            return user
        return None

class User(models.Model):
    email = models.EmailField(unique=True) # Stored in all-lowercase.

    # Password uses '[algo]$[salt]$[hexdigest]', just like Django's auth.User.
    password = models.CharField(max_length=128)

    # The SHORT_NAME for the user's metro when they created the account.
    main_metro = models.CharField(max_length=32)

    creation_date = models.DateTimeField()
    is_active = models.BooleanField()

    objects = UserManager('users')

    def __unicode__(self):
        return self.email

    def set_password(self, new_password):
        self.password = utils.make_password_hash(new_password)

    def check_password(self, raw_password):
        "Returns True if the given raw password is correct for this user."
        return utils.check_password_hash(raw_password, self.password)

# Note that this class does *not* use the multidb Manager.
# It's city-specific because pending user actions are city-specific.

class PendingUserAction(models.Model):
    email = models.EmailField(db_index=True) # Stored in all-lowercase.
    callback = models.CharField(max_length=50)
    data = models.TextField() # Serialized into JSON.
    action_date = models.DateTimeField() # When the action was created (so we can clear out expired ones).

    def __unicode__(self):
        return u'%s for %s' % (self.callback, self.email)
