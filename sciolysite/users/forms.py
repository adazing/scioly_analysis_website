
from django import forms

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=False,
        help_text="Optional. Only used so you can reset your password if you forget it.",
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_username(self):
        parent = getattr(super(), 'clean_username', None)
        username = parent() if parent else self.cleaned_data.get('username')
        # '@' is reserved for email logins so a username can't look like
        # someone else's email. (Existing accounts are not affected.)
        if '@' in username:
            raise forms.ValidationError("Usernames can't contain '@'.")
        return username

    def clean_email(self):
        return clean_unique_email(self.cleaned_data.get('email', ''))

class CustomAuthenticationForm(AuthenticationForm):
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': "Please enter a correct username/email and password. Note that the password is case-sensitive.",
    }

    class Meta:
        model = User
        fields = ('username', 'password')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow emails (up to 254 chars) in the username box.
        self.fields['username'].label = "Username or email"
        self.fields['username'].max_length = 254
        self.fields['username'].widget.attrs['maxlength'] = 254

class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class DeleteConfirmationForm(forms.Form):
    confirm = forms.BooleanField()


def clean_unique_email(email, exclude_user=None):
    """Normalize an email and make sure no other account already uses it."""
    email = (email or '').strip()
    if not email:
        return ''
    email = User.objects.normalize_email(email)
    others = User.objects.filter(email__iexact=email)
    if exclude_user is not None:
        others = others.exclude(pk=exclude_user.pk)
    if others.exists():
        raise forms.ValidationError("That email is already linked to another account.")
    return email


class EmailChangeForm(forms.Form):
    """Set or change the account email. Requires the current password so that
    someone with access to an unlocked session can't hijack account recovery."""
    email = forms.EmailField(
        required=False,
        help_text="Used only for password resets. Leave blank to remove it.",
    )
    current_password = forms.CharField(strip=False, widget=forms.PasswordInput)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial['email'] = user.email

    def clean_email(self):
        return clean_unique_email(self.cleaned_data.get('email', ''), exclude_user=self.user)

    def clean_current_password(self):
        password = self.cleaned_data.get('current_password')
        if not self.user.check_password(password):
            raise forms.ValidationError("Incorrect password.")
        return password

    def save(self):
        self.user.email = self.cleaned_data['email']
        self.user.save(update_fields=['email'])
        return self.user
