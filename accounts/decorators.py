from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied


def admin_required(view_func):
    def check_admin(user):
        if user.is_authenticated and (user.role == 'admin' or user.is_superuser):
            return True
        raise PermissionDenied
    return user_passes_test(check_admin)(view_func)