from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # user_account has no last_login column, so Django's default
        # "update last_login on login" handler must be disconnected.
        from django.contrib.auth import user_logged_in
        from django.contrib.auth.models import update_last_login

        user_logged_in.disconnect(update_last_login, dispatch_uid="update_last_login")
