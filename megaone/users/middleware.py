import zoneinfo
from django.utils import timezone
from django.db.models import prefetch_related_objects


class KeepMultipleSessionsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response


class UserTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_tz = request.session.get("user_timezone")
        if not user_tz:
            user_tz = request.COOKIES.get("user_timezone")
        if not user_tz and request.user.is_authenticated and request.user.timezone:
            user_tz = request.user.timezone
        if user_tz:
            try:
                timezone.activate(zoneinfo.ZoneInfo(user_tz))
            except Exception:
                timezone.activate(zoneinfo.ZoneInfo("UTC"))
        else:
            timezone.activate(zoneinfo.ZoneInfo("UTC"))
        return self.get_response(request)


class PermissionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if getattr(request.user, 'is_operator', False) or request.user.is_staff:
                try:
                    prefetch_related_objects([request.user], 'operator_permissions')
                except Exception:
                    pass
        response = self.get_response(request)
        return response
