from django.conf import settings
from constants import EMAIL_SESSION_KEY # relative import

def user(request):
    # Makes 'USER' and 'USER_EMAIL' available in templates.
    if request.user:
        return {'DEBUG': settings.DEBUG, 'USER': request.user, 'USER_EMAIL': request.session[EMAIL_SESSION_KEY]}
    else:
        return {'DEBUG': settings.DEBUG, 'USER': None, 'USER_EMAIL': None}
