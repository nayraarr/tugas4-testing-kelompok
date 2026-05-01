from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            if request.user.role not in roles:
                messages.error(request, 'Anda tidak memiliki akses ke halaman ini.')
                return redirect('accounts:dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped
    return decorator


def nasabah_only(view_func):
    return role_required('nasabah')(view_func)


def teller_only(view_func):
    return role_required('teller')(view_func)


def supervisor_only(view_func):
    return role_required('supervisor')(view_func)


def staff_only(view_func):
    return role_required('teller', 'supervisor')(view_func)
