from django import forms, http
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import capfirst
from ebpub.accounts import callbacks
from ebpub.accounts.models import User, PendingUserAction
from ebpub.accounts.utils import login_required, CREATE_TASK
from ebpub.accounts.views import login, send_confirmation_and_redirect
from ebpub.alerts.models import EmailAlert
from ebpub.db.models import Schema
from ebpub.db.views import generic_place_page, url_to_place, block_radius_value
from ebpub.streets.models import Block
from ebpub.utils.view_utils import eb_render
import datetime

FREQUENCY_CHOICES = (('1', 'Daily'), ('7', 'Weekly'))
RADIUS_CHOICES = (('1', '1 block'), ('3', '3 blocks'), ('8', '8 blocks'))

class SchemaMultipleChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        kwargs['queryset'] = Schema.public_objects.filter(is_special_report=False).order_by('plural_name')
        super(SchemaMultipleChoiceField, self).__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        return capfirst(obj.plural_name)

class LocationAlertForm(forms.Form):
    frequency = forms.ChoiceField(choices=FREQUENCY_CHOICES, widget=forms.RadioSelect)
    selected_schemas = SchemaMultipleChoiceField(widget=forms.CheckboxSelectMultiple)
    displayed_schemas = SchemaMultipleChoiceField(widget=forms.MultipleHiddenInput)
    include_new_schemas = forms.BooleanField(required=False)

    # This form is slightly complicated because the e-mail address doesn't need
    # to be entered if the user is logged in. The __init__() method takes an
    # `email_required` argument, which specifies whether the `email` field
    # should be included in the form.
    def __init__(self, *args, **kwargs):
        self.email_required = kwargs.pop('email_required', True)
        forms.Form.__init__(self, *args, **kwargs)
        if self.email_required:
            f = forms.EmailField(widget=forms.TextInput(attrs={'id': 'emailinput', 'class': 'textinput placeholder'}))
            self.fields['email'] = f

    def clean(self):
        # Normalize e-mail address to lower case.
        if self.cleaned_data.get('email'):
            self.cleaned_data['email'] = self.cleaned_data['email'].lower()

        # Set cleaned_data['schemas'], which we'll use later. Its value depends...
        if 'include_new_schemas' in self.cleaned_data and 'selected_schemas' in self.cleaned_data:
            if self.cleaned_data['include_new_schemas']:
                # Set it to the list of schemas to opt out of.
                self.cleaned_data['schemas'] = set(self.cleaned_data['displayed_schemas']) - set(self.cleaned_data['selected_schemas'])
            else:
                # Set it to the list of schemas to opt in to.
                self.cleaned_data['schemas'] = self.cleaned_data['selected_schemas']

        return self.cleaned_data

class BlockAlertForm(LocationAlertForm):
    radius = forms.ChoiceField(choices=RADIUS_CHOICES, widget=forms.RadioSelect)

def signup(request, *args, **kwargs):
    place = url_to_place(*args, **kwargs)
    schema_list = Schema.public_objects.filter(is_special_report=False).order_by('plural_name')
    if isinstance(place, Block):
        FormClass, type_code = BlockAlertForm, 'b'
    else:
        FormClass, type_code = LocationAlertForm, 'l'
    email_required = request.user is None
    if request.method == 'POST':
        form = FormClass(request.POST, email_required=email_required)
        if form.is_valid():
            return finish_signup(request, place, form.cleaned_data)
    else:
        schema_ids = [s.id for s in schema_list]
        form = FormClass(initial={
            'email': 'Enter your e-mail address',
            'radius': block_radius_value(request)[1],
            'frequency': '1',
            'include_new_schemas': True,
            'selected_schemas': schema_ids,
            'displayed_schemas': schema_ids,
        }, email_required=email_required)
    return generic_place_page(request, 'alerts/signup_form.html', place, {'form': form, 'schema_list': schema_list})

def finish_signup(request, place, data):
    # This is called from signup(), after `data` (the alert options) is
    # validated/cleaned. This is a separate function so signup() doesn't get
    # too unwieldy.

    # First, delete displayed_schemas and selected_schemas, because neither is
    # used in serialization. Also, convert `schemas` to be a string list of IDs
    # instead of the model objects, because that's what we end up storing in
    # the database.
    del data['displayed_schemas']
    del data['selected_schemas']
    data['schemas'] = ','.join([str(s.id) for s in data['schemas']])
    if isinstance(place, Block):
        data['block_id'] = place.id
        data['location_id'] = None
    else:
        data['block_id'] = None
        data['location_id'] = place.id
        data['radius'] = None

    if request.user:
        email = request.user.email
    else:
        email = data['email']

    if request.user:
        message = callbacks.create_alert(request.user, data)
        request.session['login_message'] = message
        return http.HttpResponseRedirect('/accounts/dashboard/')

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # We haven't seen this e-mail address yet, so send out a confirmation
        # e-mail to create the account. But first, save the user's alert
        # information so we can create the alert once the user confirms the
        # e-mail address. (We don't want to send the alert options in that
        # confirmation e-mail, because that's too much data to pass in a URL.)
        PendingUserAction.objects.create(
            email=email,
            callback='createalert',
            data=callbacks.serialize(data),
            action_date=datetime.datetime.now(),
        )
        return send_confirmation_and_redirect(request, email, CREATE_TASK)
    else:
        # This e-mail address already has an account, so show a password
        # confirmation screen.
        msg = "You already have an account with this e-mail address. " \
              "Please enter your password to confirm this alert subscription."
        request.session['pending_login'] = ('createalert', data)
        return login(request, custom_message=msg, force_form=True, initial_email=email)

@login_required
def unsubscribe(request, alert_id):
    a = get_object_or_404(EmailAlert.active_objects.all(), id=alert_id, user_id=request.user.id)
    if request.method == 'POST':
        EmailAlert.objects.filter(id=alert_id).update(cancel_date=datetime.datetime.now(), is_active=False)
        request.session['login_message'] = "We've unsubscribed you from the alert for %s" % a.name()
        return http.HttpResponseRedirect('/accounts/dashboard/')
    return eb_render(request, 'alerts/confirm_unsubscription.html', {'alert': a})
