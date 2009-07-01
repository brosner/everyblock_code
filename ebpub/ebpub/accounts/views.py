from django import http
from django.conf import settings
from django.template.loader import render_to_string
from ebpub.accounts import callbacks
from ebpub.accounts.models import User, PendingUserAction
from ebpub.alerts.models import EmailAlert
from ebpub.db.models import Schema
from ebpub.metros.allmetros import get_metro
from ebpub.preferences.models import HiddenSchema
from ebpub.savedplaces.models import SavedPlace
from ebpub.utils.view_utils import eb_render
import forms, utils # relative import
import datetime

###########################
# VIEWS FOR USER ACCOUNTS #
###########################

def login(request, custom_message=None, force_form=False, initial_email=None):
    # custom_message is a string to display at the top of the login form.
    # force_form is used when you want to force display of the original
    # form (regardless of whether it's a POST request).

    # If the user is already logged in, redirect to the dashboard.
    if request.user:
        return http.HttpResponseRedirect('/accounts/dashboard/')

    if request.method == 'POST' and not force_form:
        form = forms.LoginForm(request, request.POST)
        if form.is_valid():
            utils.login(request, form.user)
            if request.session.test_cookie_worked():
                request.session.delete_test_cookie()

            # If the session contains a 'pending_login' variable, it will be a
            # tuple of (callback_name, data), where data is an unserialized
            # Python object and callback_name corresponds to a callback in
            # ebpub/accounts/callbacks.py.
            if 'pending_login' in request.session:
                try:
                    callback, data = request.session['pending_login']
                    message = callbacks.do_callback(callback, form.user, data)
                except (TypeError, ValueError):
                    message = None

                # We're done with the callbacks and don't want to risk them
                # happening again, so we delete the session value.
                del request.session['pending_login']

                # Save the login message in the session so we can display it
                # for the user.
                if message:
                    request.session['login_message'] = message

            next_url = request.session.pop('next_url', '/accounts/dashboard/')
            return http.HttpResponseRedirect(next_url)
    else:
        form = forms.LoginForm(request, initial={'email': initial_email})
    request.session.set_test_cookie()
    custom_message = request.session.pop('login_message', custom_message)
    return eb_render(request, 'accounts/login_form.html', {'form': form, 'custom_message': custom_message})

def logout(request):
    if request.method == 'POST':
        request.session.flush()
        request.user = None

        # The `next_url` can be specified either as POST data or in the
        # session. If it's in the session, it can be trusted. If it's in
        # POST data, it can't be trusted, so we do a simple check that it
        # starts with a slash (so that people can't hack redirects to other
        # sites).
        if 'next_url' in request.POST and request.POST['next_url'].startswith('/'):
            next_url = request.POST['next_url']
        elif 'next_url' in request.session:
            next_url = request.session.pop('next_url')
        else:
            request.session['login_message'] = "You're logged out. You can log in again below."
            next_url = '/accounts/login/'

        return http.HttpResponseRedirect(next_url)
    return eb_render(request, 'accounts/logout_form.html')

@utils.login_required
def dashboard(request):
    custom_message = request.session.get('login_message')
    if 'login_message' in request.session:
        del request.session['login_message']

    alert_list = EmailAlert.active_objects.filter(user_id=request.user.id)
    saved_place_list = SavedPlace.objects.filter(user_id=request.user.id)
    hidden_schema_ids = HiddenSchema.objects.filter(user_id=request.user.id).values('schema_id')
    hidden_schema_ids = set([x['schema_id'] for x in hidden_schema_ids])

    schema_list = []
    for schema in Schema.public_objects.filter(is_special_report=False).order_by('plural_name'):
        schema_list.append({'schema': schema, 'is_hidden': schema.id in hidden_schema_ids})

    return eb_render(request, 'accounts/dashboard.html', {
        'custom_message': custom_message,
        'user': request.user,
        'alert_list': alert_list,
        'saved_place_list': saved_place_list,
        'schema_list': schema_list,
    })

####################################
# UTILITIES USED BY MULTIPLE VIEWS #
####################################

# These utilities encapsulate some logic used by both the registration
# workflow and the "I forgot my password" workflow.

class BadHash(Exception):
    def __init__(self, response):
        self.response = response

def send_confirmation_and_redirect(request, email, task):
    if settings.DEBUG:
        url = utils.verification_url(email, task)
        return http.HttpResponse('<a href="%s">Click here to simulate the e-mail confirmation</a>.' % url)
    else:
        utils.send_verification_email(email, task)
    return http.HttpResponseRedirect('/accounts/email-sent/')

def confirm_request_hash(request, task):
    if request.method == 'GET':
        d = request.GET
    elif request.method == 'POST':
        d = request.POST
    else:
        raise http.Http404('Invalid method')

    # Verify the hash.
    try:
        email, email_hash = d['e'], d['h']
        if email_hash != utils.make_email_hash(email, task):
            raise KeyError
    except KeyError:
        form_link = {utils.CREATE_TASK: '/accounts/register/', utils.RESET_TASK: '/accounts/password-change/'}[task]
        response = http.HttpResponseNotFound(render_to_string('accounts/hash_error.html', {'form_link': form_link}))
        raise BadHash(response)

    return email, email_hash

########################
# REGISTRATION PROCESS #
########################

# We want to avoid creating a database record until an e-mail address has been
# verified, so we use a hash of the e-mail address for security.

def register(request):
    # If the user is already logged in, redirect to the dashboard.
    if request.user:
        return http.HttpResponseRedirect('/accounts/dashboard/')

    if request.method == 'POST':
        form = forms.EmailRegistrationForm(request.POST)
        if form.is_valid():
            return send_confirmation_and_redirect(request, form.cleaned_data['email'], utils.CREATE_TASK)
    else:
        form = forms.EmailRegistrationForm()
    return eb_render(request, 'accounts/register_form_1.html', {'form': form})

def confirm_email(request):
    try:
        email, email_hash = confirm_request_hash(request, utils.CREATE_TASK)
    except BadHash, e:
        return e.response
    if request.method == 'POST':
        form = forms.PasswordRegistrationForm(request.POST)
        if form.is_valid():
            u = User.objects.create_user(
                email=form.cleaned_data['e'],
                password=form.cleaned_data['password1'],
                main_metro=get_metro()['short_name'],
                creation_date=datetime.datetime.now(),
                is_active=True,
            )
            utils.login(request, u)

            # Look for any PendingUserActions for this e-mail address and
            # execute the callbacks.
            for action in PendingUserAction.objects.filter(email=u.email):
                data = callbacks.unserialize(action.data)
                callbacks.do_callback(action.callback, u, data)
                action.delete()

            request.session['login_message'] = 'Your account was created! Thanks for signing up.'
            return http.HttpResponseRedirect('../dashboard/')
    else:
        form = forms.PasswordRegistrationForm(initial={'e': email, 'h': email_hash})
    return eb_render(request, 'accounts/register_form_2.html', {'form': form})

###################
# PASSWORD CHANGE #
###################

def request_password_change(request):
    if request.method == 'POST':
        form = forms.PasswordResetRequestForm(request.POST)
        if form.is_valid():
            return send_confirmation_and_redirect(request, form.cleaned_data['email'], utils.RESET_TASK)
    else:
        form = forms.PasswordResetRequestForm()
    return eb_render(request, 'accounts/request_password_change_form.html', {'form': form})

def password_reset(request):
    try:
        email, email_hash = confirm_request_hash(request, utils.RESET_TASK)
    except BadHash, e:
        return e.response
    if request.method == 'POST':
        form = forms.PasswordResetForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(is_active=True, email=email.lower())
            except User.DoesNotExist:
                # If we reach this point, then somebody managed to submit a
                # hash for a user that's not registered yet.
                raise http.Http404()
            User.objects.set_password(user.id, form.cleaned_data['password1'])
            request.session['login_message'] = 'Your password was changed successfully. Give it a shot by logging in below:'
            return http.HttpResponseRedirect('/accounts/login/')
    else:
        form = forms.PasswordResetForm(initial={'e': email, 'h': email_hash})
    return eb_render(request, 'accounts/password_change_form.html', {'form': form})
