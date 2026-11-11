import re

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

User = get_user_model()


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SITE_URL="https://example.test",
)
class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("crew", "crew@example.com", "OldPass!12345")

    def _request_reset(self, email, **extra):
        return self.client.post(reverse("password_reset"), {"email": email}, **extra)

    def test_full_reset_flow(self):
        resp = self._request_reset("crew@example.com")
        self.assertRedirects(resp, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 1)
        body = mail.outbox[0].body
        link = re.search(r"https://example\.test(/password-reset/\S+/)", body).group(1)

        resp = self.client.get(link, follow=True)  # redirects to the set-password URL
        self.assertTrue(resp.context["validlink"])
        set_url = resp.redirect_chain[-1][0]
        resp = self.client.post(set_url, {"new_password1": "NewPass!67890", "new_password2": "NewPass!67890"})
        self.assertRedirects(resp, reverse("password_reset_complete"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPass!67890"))

        # Link is single-use.
        resp = self.client.get(link, follow=True)
        self.assertFalse(resp.context["validlink"])

    def test_unknown_email_gives_same_response_and_sends_nothing(self):
        resp = self._request_reset("nobody@example.com")
        self.assertRedirects(resp, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)

    def test_link_ignores_spoofed_host_header(self):
        with self.settings(ALLOWED_HOSTS=["*"]):
            self._request_reset("crew@example.com", HTTP_HOST="evil.example")
        self.assertNotIn("evil.example", mail.outbox[0].body)
        self.assertIn("https://example.test/", mail.outbox[0].body)

    def test_login_page_links_to_reset(self):
        self.assertContains(self.client.get(reverse("loginView")), reverse("password_reset"))


class EmailChangeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("crew", "", "OldPass!12345")
        self.client.force_login(self.user)

    def test_requires_login(self):
        self.client.logout()
        resp = self.client.get(reverse("emailChangeView"))
        self.assertEqual(resp.status_code, 302)

    def test_requires_correct_password(self):
        self.client.post(reverse("emailChangeView"), {"email": "a@b.com", "current_password": "wrong"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "")

    def test_sets_email(self):
        self.client.post(reverse("emailChangeView"), {"email": "a@b.com", "current_password": "OldPass!12345"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "a@b.com")


class SignupEmailTests(TestCase):
    def test_signup_email_optional(self):
        self.client.post(reverse("signupView"), {"username": "u1", "password1": "Xyz!987654a", "password2": "Xyz!987654a"})
        self.assertEqual(User.objects.get(username="u1").email, "")

    def test_signup_saves_email(self):
        self.client.post(reverse("signupView"), {"username": "u2", "email": "u2@example.com", "password1": "Xyz!987654a", "password2": "Xyz!987654a"})
        self.assertEqual(User.objects.get(username="u2").email, "u2@example.com")


class LoginTests(TestCase):
    PW = "OldPass!12345"

    def setUp(self):
        self.user = User.objects.create_user("crew", "Crew@Example.com", self.PW)

    def _login(self, username, password=None):
        self.client.post(reverse("loginView"), {"username": username, "password": password or self.PW})
        return self.client.session.get("_auth_user_id")

    def test_username_login_still_works(self):
        self.assertEqual(self._login("crew"), str(self.user.pk))

    def test_email_login_case_insensitive(self):
        self.assertEqual(self._login("crew@example.com"), str(self.user.pk))
        self.client.logout()
        self.assertEqual(self._login("  CREW@EXAMPLE.COM "), str(self.user.pk))

    def test_wrong_password_fails(self):
        self.assertIsNone(self._login("crew@example.com", "nope"))
        self.assertIsNone(self._login("crew", "nope"))

    def test_user_without_email_unaffected(self):
        u = User.objects.create_user("noemail", "", self.PW)
        self.assertEqual(self._login("noemail"), str(u.pk))

    def test_legacy_username_with_at_sign_still_logs_in(self):
        # Accounts created before the '@' rule must keep working.
        legacy = User.objects.create_user("old@style", "", "Legacy!12345")
        self.assertEqual(self._login("old@style", "Legacy!12345"), str(legacy.pk))

    def test_exact_username_takes_priority_over_email(self):
        other = User.objects.create_user("x@y.com", "", "Other!12345")
        User.objects.create_user("z", "x@y.com", "Zpass!12345")
        self.assertEqual(self._login("x@y.com", "Other!12345"), str(other.pk))

    def test_password_change_with_old_password_still_works(self):
        self.client.force_login(self.user)
        self.client.post(reverse("passwordChangeView"), {
            "old_password": self.PW, "new_password1": "Brand!New9876", "new_password2": "Brand!New9876"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Brand!New9876"))


class UniqueEmailTests(TestCase):
    def setUp(self):
        self.a = User.objects.create_user("a", "taken@example.com", "Apass!12345")

    def test_signup_rejects_taken_email_any_case(self):
        resp = self.client.post(reverse("signupView"), {
            "username": "b", "email": "TAKEN@example.com", "password1": "Xyz!987654a", "password2": "Xyz!987654a"})
        self.assertFalse(User.objects.filter(username="b").exists())
        self.assertContains(resp, "already linked")

    def test_signup_rejects_at_in_username(self):
        self.client.post(reverse("signupView"), {
            "username": "me@x.com", "password1": "Xyz!987654a", "password2": "Xyz!987654a"})
        self.assertFalse(User.objects.filter(username="me@x.com").exists())

    def test_email_change_rejects_taken_email(self):
        b = User.objects.create_user("b", "", "Bpass!12345")
        self.client.force_login(b)
        self.client.post(reverse("emailChangeView"), {"email": "taken@example.com", "current_password": "Bpass!12345"})
        b.refresh_from_db()
        self.assertEqual(b.email, "")

    def test_resaving_own_email_is_fine(self):
        self.client.force_login(self.a)
        self.client.post(reverse("emailChangeView"), {"email": "Taken@example.com", "current_password": "Apass!12345"})
        self.a.refresh_from_db()
        self.assertEqual(self.a.email, "Taken@example.com")

    def test_multiple_users_without_email_allowed(self):
        for n in ("c", "d"):
            self.client.post(reverse("signupView"), {"username": n, "password1": "Xyz!987654a", "password2": "Xyz!987654a"})
        self.assertEqual(User.objects.filter(username__in=["c", "d"], email="").count(), 2)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class NoRecoveryEmailTests(TestCase):
    """Accounts with no email (every account created before this change)."""
    PW = "OldPass!12345"

    def setUp(self):
        self.user = User.objects.create_user("legacy", "", self.PW)
        self.user2 = User.objects.create_user("legacy2", "", self.PW)  # same password on purpose

    def _login(self, username, password=None):
        resp = self.client.post(reverse("loginView"), {"username": username, "password": password or self.PW})
        return resp, self.client.session.get("_auth_user_id")

    def test_username_login_works(self):
        _, uid = self._login("legacy")
        self.assertEqual(uid, str(self.user.pk))

    def test_wrong_password_shows_error_not_crash(self):
        resp, uid = self._login("legacy", "wrong")
        self.assertIsNone(uid)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "correct username/email")

    def test_email_style_input_never_matches_blank_emails(self):
        for attempt in ("@", " @ ", "x@y.com", "@example.com"):
            _, uid = self._login(attempt)
            self.assertIsNone(uid, attempt)

    def test_backend_never_matches_blank_email_directly(self):
        from django.contrib.auth import authenticate
        for attempt in ("", " ", "@"):
            self.assertIsNone(authenticate(username=attempt, password=self.PW))

    def test_change_password_with_old_password(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("passwordChangeView"))
        self.assertEqual(resp.status_code, 200)
        resp = self.client.post(reverse("passwordChangeView"), {
            "old_password": self.PW, "new_password1": "Brand!New9876", "new_password2": "Brand!New9876"})
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Brand!New9876"))
        # Still logged in after change, and can log in again with new password.
        self.assertEqual(self.client.session.get("_auth_user_id"), str(self.user.pk))
        self.client.logout()
        _, uid = self._login("legacy", "Brand!New9876")
        self.assertEqual(uid, str(self.user.pk))

    def test_change_password_wrong_old_password_rejected(self):
        self.client.force_login(self.user)
        self.client.post(reverse("passwordChangeView"), {
            "old_password": "wrong", "new_password1": "Brand!New9876", "new_password2": "Brand!New9876"})
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(self.PW))

    def test_reset_request_sends_nothing_and_does_not_error(self):
        resp = self.client.post(reverse("password_reset"), {"email": "someone@example.com"})
        self.assertRedirects(resp, reverse("password_reset_done"))
        self.assertEqual(len(mail.outbox), 0)
        resp = self.client.post(reverse("password_reset"), {"email": ""})
        self.assertEqual(resp.status_code, 200)  # form error, no crash
        self.assertEqual(len(mail.outbox), 0)

    def test_all_pages_render_for_logged_in_no_email_user(self):
        self.client.force_login(self.user)
        for name in ("home", "passwordChangeView", "emailChangeView", "deleteAccountView"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_all_public_pages_render(self):
        for name in ("home", "loginView", "signupView", "password_reset",
                     "password_reset_done", "password_reset_complete", "privacyPolicy"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200, name)

    def test_saving_blank_email_keeps_it_blank(self):
        self.client.force_login(self.user)
        self.client.post(reverse("emailChangeView"), {"email": "", "current_password": self.PW})
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "")

    def test_adding_email_then_email_login_and_old_username_login(self):
        self.client.force_login(self.user)
        self.client.post(reverse("emailChangeView"), {"email": "me@example.com", "current_password": self.PW})
        self.client.logout()
        _, uid = self._login("me@example.com")
        self.assertEqual(uid, str(self.user.pk))
        self.client.logout()
        _, uid = self._login("legacy")
        self.assertEqual(uid, str(self.user.pk))

    def test_password_with_spaces_accepted_on_email_page(self):
        u = User.objects.create_user("spacey", "", " pad Pass!123 ")
        self.client.force_login(u)
        self.client.post(reverse("emailChangeView"), {"email": "s@example.com", "current_password": " pad Pass!123 "})
        u.refresh_from_db()
        self.assertEqual(u.email, "s@example.com")
