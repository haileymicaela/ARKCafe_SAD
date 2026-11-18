from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

HOME = {"admin": "admin_dashboard", "staff": "staff_dashboard"}


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role != role:
                home = HOME.get(request.user.role)
                if home is None:  # unknown role: don't redirect-loop
                    raise PermissionDenied
                return redirect(home)  # wrong side: send them to their own dashboard
            return view(request, *args, **kwargs)
        return wrapper
    return decorator


admin_required = role_required("admin")
staff_required = role_required("staff")