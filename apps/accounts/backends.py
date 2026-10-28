from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class EmailBackend(ModelBackend):
    """Authenticate accounts by normalized email rather than username."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        email = kwargs.get("email", username)
        if email is None or password is None:
            return None

        UserModel = get_user_model()
        normalized_email = UserModel.objects.normalize_email(email).casefold()
        try:
            user = UserModel.objects.get(email__iexact=normalized_email)
        except UserModel.DoesNotExist:
            # Match the password-hash cost for unknown accounts.
            UserModel().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
