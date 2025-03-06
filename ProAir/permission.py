from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps
from django.conf import settings

# Mixin for Class Based Views
class StaffAndAdminRequiredMixin:
    """
    Mixin to check if user is both staff and admin.
    Add this mixin to your class-based views.
    """
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page.")
            return redirect(settings.LOGIN_URL)
            
        if not (request.user.is_staff and request.user.is_superuser):
            messages.error(request, "You don't have permission to access this page.")
            raise PermissionDenied("User must be both staff and admin.")
            
        return super().dispatch(request, *args, **kwargs)

# Decorator for Function Based Views
def staff_admin_required(view_func):
    """
    Decorator to check if user is both staff and admin.
    Use this decorator on your function-based views.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, "Please login to access this page.")
            return redirect(settings.LOGIN_URL)
            
        if not (request.user.is_staff and request.user.is_superuser):
            messages.error(request, "You don't have permission to access this page.")
            raise PermissionDenied("User must be both staff and admin.")
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view