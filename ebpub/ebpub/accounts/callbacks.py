# This is a lightweight framework for passing events that need to happen
# when users log in successfully. For example, there's a way to specify that
# an e-mail alert should be created for a given user as soon as he logs in.

from django.utils import simplejson
from ebpub.alerts.models import EmailAlert
import datetime

###############
# SERIALIZING #
###############

# We store compressed JSON in the PendingUserAction table.

def serialize(data):
    return simplejson.dumps(data)

def unserialize(data):
    return simplejson.loads(data)

#############
# CALLBACKS #
#############

def do_callback(callback_name, user, data):
    # callback_name is a key in CALLBACKS.
    # serialized_data is an unserialized Python object.
    try:
        callback = CALLBACKS[callback_name]
    except KeyError:
        return None
    return callback(user, data)

def create_alert(user, data):
    EmailAlert.objects.create(
        user_id=user.id,
        block_id=data['block_id'],
        location_id=data['location_id'],
        frequency=data['frequency'],
        radius=data['radius'],
        include_new_schemas=data['include_new_schemas'],
        schemas=data['schemas'],
        signup_date=datetime.datetime.now(),
        cancel_date=None,
        is_active=True,
    )
    return "Your e-mail alert was created successfully. Thanks for signing up!"

CALLBACKS = {
    'createalert': create_alert,
}
