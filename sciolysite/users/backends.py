from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

UserModel = get_user_model()


class UsernameOrEmailBackend(ModelBackend):
    """Log in with either a username or the email attached to the account.

    The exact username is always tried first, so existing accounts log in
    exactly as before. The email lookup only happens when no account has that
    username. Either way the password still has to match that account.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(UserModel.USERNAME_FIELD)
        if username is None or password is None:
            return None

        candidates = list(UserModel._default_manager.filter(username=username))
        email = username.strip()
        # Only look up by email if it looks like one. The explicit non-empty
        # check matters: accounts with no recovery email store '' and must
        # never be matched by an email lookup.
        if not candidates and email and "@" in email:
            candidates = list(UserModel._default_manager.filter(email__iexact=email).exclude(email=""))

        if not candidates:
            # Hash anyway so response time doesn't reveal whether the account exists.
            UserModel().set_password(password)
            return None

        for user in candidates:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
