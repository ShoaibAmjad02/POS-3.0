# ruff: noqa
import logging
import traceback

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponseServerError
from django.urls import include
from django.urls import path
from django.urls import re_path
from django.views import defaults as default_views
from django.views.generic import TemplateView
from django.views.static import serve as media_serve
from megaone.users.views import qr_menu_view, food_delivery_login

logger = logging.getLogger('django.request')


def custom_handler500(request):
    """Custom 500 handler that logs full traceback to django_error.log."""
    tb = traceback.format_exc()
    logger.error(
        "500 ERROR on %s %s\nFull traceback:\n%s\nRequest user: %s\nGET: %s\nPOST: %s",
        request.method,
        request.build_absolute_uri(),
        tb,
        request.user,
        request.GET,
        {k: v for k, v in request.POST.items() if k != 'password'},
    )
    try:
        from django.template.loader import render_to_string
        context = {'request': request}
        body = render_to_string("500.html", context)
        return HttpResponseServerError(body)
    except Exception:
        return HttpResponseServerError("<h1>Ooops!!! 500</h1><h3>Looks like something went wrong!</h3>")


handler500 = custom_handler500


urlpatterns = [
    path("", food_delivery_login, name="home"),

    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("megaone.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here

    path("food-delivery/", include("apps.food_delivery.urls", namespace="food-delivery")),

    # Cash Handling API
    path("cash/", include("cash_handling.urls", namespace="cash_handling")),

    # QR Menu Access (root level)
    path("menu/", qr_menu_view, name="qr_menu_view"),

    path("404-1/", TemplateView.as_view(template_name="404-1.html"), name="404-1"),
    path("404-2/", TemplateView.as_view(template_name="404-2.html"), name="404-2"),
    path("404-3/", TemplateView.as_view(template_name="404-3.html"), name="404-3"),
]

# Serve media files in all modes (including DEBUG=False for LAN EXE)
urlpatterns += [
    re_path(r"^media/(?P<path>.*)$", media_serve, {"document_root": settings.MEDIA_ROOT}),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
