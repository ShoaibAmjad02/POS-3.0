from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages


def _get_enabled_modules():
    try:
        from .models import SystemSetting
        s = SystemSetting.objects.filter(pk=1).first()
        return set(s.enabled_modules or []) if s else set()
    except Exception:
        return set()


def has_module_access(user, module_code):
    if not user.is_authenticated:
        return False
    if user.is_software_owner:
        return True
    return module_code in _get_enabled_modules()


def module_access_required(module_code):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({"error": "Authentication required"}, status=403)
                return redirect('users:login')
            if not has_module_access(request.user, module_code):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({"error": "Module access denied"}, status=403)
                messages.error(request, "You do not have access to this module.")
                if request.user.is_staff:
                    return redirect('users:admin_dashboard')
                return redirect('users:operator_dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def _check_operator_permission(user, perm_name):
    try:
        perms = user.operator_permissions
    except Exception:
        from .models import OperatorPermission
        if user.is_staff or getattr(user, 'is_operator', False):
            try:
                perms, created = OperatorPermission.objects.get_or_create(user=user)
                if created and user.is_staff:
                    for f in OperatorPermission._meta.get_fields():
                        if not f.name.startswith('cash_'):
                            continue
                        if not hasattr(f, 'get_internal_type'):
                            continue
                        if f.get_internal_type() == 'BooleanField':
                            setattr(perms, f.name, True)
                    perms.save()
            except Exception:
                return None
        else:
            return None
    return getattr(perms, perm_name, False)


def has_permission(user, perm_name):
    if not user.is_authenticated:
        return False
    if user.is_software_owner:
        return True
    if user.is_staff or getattr(user, 'is_operator', False):
        result = _check_operator_permission(user, perm_name)
        if result is not None:
            return result
        # Staff without operator_permissions record → deny by default
        return False
    return False


def operator_permission_required(perm_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({"error": "Authentication required"}, status=403)
            if request.user.is_software_owner:
                return view_func(request, *args, **kwargs)
            if not getattr(request.user, 'is_operator', False) and not request.user.is_staff:
                return JsonResponse({"error": "Access denied"}, status=403)
            result = _check_operator_permission(request.user, perm_name)
            if result is None:
                return JsonResponse({"error": "No permissions configured"}, status=403)
            if not result:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
                    return JsonResponse({"error": "Permission denied"}, status=403)
                messages.error(request, "You do not have permission to perform this action.")
                return redirect('users:operator_dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def has_admin_permission(user, perm_name):
    if not user.is_authenticated:
        return False
    if user.is_software_owner:
        return True
    if not user.is_staff:
        return False
    try:
        perms = user.operator_permissions
        return getattr(perms, perm_name, False)
    except Exception:
        return False


def admin_permission_required(perm_name):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return JsonResponse({"error": "Authentication required"}, status=403)
            if request.user.is_software_owner:
                return view_func(request, *args, **kwargs)
            if not request.user.is_staff:
                return JsonResponse({"error": "Access denied"}, status=403)
            try:
                perms = request.user.operator_permissions
            except Exception:
                return JsonResponse({"error": "No permissions configured"}, status=403)
            if not getattr(perms, perm_name, False):
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({"error": "Permission denied"}, status=403)
                messages.error(request, "You do not have permission to access this page.")
                return redirect('users:operator_dashboard')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def software_owner_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentication required"}, status=403)
        if not request.user.is_software_owner:
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"error": "Access denied. Software Owner only."}, status=403)
            messages.error(request, "Only the Software Owner can access this page.")
            return redirect('users:operator_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
