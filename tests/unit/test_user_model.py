from django.contrib.auth import get_user_model


def test_custom_user_model_is_configured():
    assert get_user_model()._meta.label == "accounts.User"
