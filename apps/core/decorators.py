from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.contrib import messages

def role_required(allowed_roles):
    """
    Decorator for views that checks whether the logged-in user has one of the allowed roles.
    If not logged in, redirects to login.
    If logged in with wrong role, redirects to their designated panel or raises PermissionDenied.
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f'/accounts/login/?next={request.path}')
            
            # Superusers have full unrestricted access across all panels
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            if request.user.role not in allowed_roles:
                messages.error(request, "You do not have permission to access that area.")
                # Redirect user to their own role dashboard
                if request.user.role == 'kitchen_staff':
                    return redirect('/kitchen/dashboard/')
                elif request.user.role == 'delivery_partner':
                    return redirect('/delivery/dashboard/')
                elif request.user.role == 'admin':
                    return redirect('/admin-panel/')
                else:
                    return redirect('/')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

