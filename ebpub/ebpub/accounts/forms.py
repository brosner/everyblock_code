from django import forms
from ebpub.accounts.models import User

class UniqueEmailField(forms.EmailField):
    """
    Validates that the given value is an e-mail address and hasn't already
    been registered.
    """
    def clean(self, value):
        value = forms.EmailField.clean(self, value).lower() # Normalize to lowercase.
        if User.objects.filter(email=value).count():
            raise forms.ValidationError('This e-mail address is already registered.')
        return value

class EmailRegistrationForm(forms.Form):
    email = UniqueEmailField(label='Your e-mail address', widget=forms.TextInput(attrs={'size': 50}))

class BasePasswordForm(forms.Form):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Password (again)', widget=forms.PasswordInput)

    def clean_password2(self):
        p1 = self.cleaned_data['password1']
        p2 = self.cleaned_data['password2']
        if p1 != p2:
            raise forms.ValidationError("The passwords didn't match! Try entering them again.")
        return p2

class PasswordRegistrationForm(BasePasswordForm):
    e = UniqueEmailField(widget=forms.HiddenInput)
    h = forms.CharField(widget=forms.HiddenInput)

class PasswordResetForm(BasePasswordForm):
    e = forms.EmailField(widget=forms.HiddenInput)
    h = forms.CharField(widget=forms.HiddenInput)

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if not User.objects.filter(email=email).count():
            raise forms.ValidationError("This e-mail address isn't registered yet.")
        return email

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, request, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        self.request = request

    def clean(self):
        # Note that because this is the form-wide clean() method, any
        # validation errors raised here will not be tied to a particular field.
        # Instead, use form.non_field_errors() in the template.

        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        # Check that both email and password were valid. If they're not valid,
        # there's no need to run the following bit of validation.
        if email and password:
            self.user = User.objects.user_by_password(email.lower(), password)
            if self.user is None:
                raise forms.ValidationError("That e-mail and password combo isn't valid. Note that the password is case-sensitive.")
            elif not self.user.is_active:
                raise forms.ValidationError("This account is inactive.")

        if not self.request.session.test_cookie_worked():
            raise forms.ValidationError("Your Web browser doesn't appear to have cookies enabled. Enable cookies, then try again.")

        return self.cleaned_data
