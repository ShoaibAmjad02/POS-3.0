from allauth.account.decorators import secure_admin_login
from django.conf import settings
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.utils.translation import gettext_lazy as _

from .forms import UserAdminChangeForm
from .forms import UserAdminCreationForm
from .models import User, Invoice, LoyaltyCard, LoyaltyTransaction, QRTableOffer, TimeBasedOffer, TodayDeal, HeldCart

if settings.DJANGO_ADMIN_FORCE_ALLAUTH:
    # Force the `admin` sign in process to go through the `django-allauth` workflow:
    # https://docs.allauth.org/en/latest/common/admin.html#admin
    admin.autodiscover()
    admin.site.login = secure_admin_login(admin.site.login)  # type: ignore[method-assign]


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal info"), {"fields": ("name",)}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "date_joined")}),
    )
    list_display = ["email", "name", "is_superuser"]
    search_fields = ["name", "phone"]
    ordering = ["id"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ["invoice_number", "total_amount", "created_at"]
    search_fields = ["invoice_number"]


@admin.register(LoyaltyCard)
class LoyaltyCardAdmin(admin.ModelAdmin):
    list_display = ["card_number", "user", "total_points", "used_points", "remaining_points", "status", "created_at"]
    search_fields = ["card_number", "user__name", "user__phone"]
    list_filter = ["status"]


@admin.register(LoyaltyTransaction)
class LoyaltyTransactionAdmin(admin.ModelAdmin):
    list_display = ["card", "transaction_type", "earned_points", "redeemed_points", "remaining_balance", "order_number", "created_at"]
    search_fields = ["card__card_number", "order_number"]
    list_filter = ["transaction_type"]


@admin.register(QRTableOffer)
class QRTableOfferAdmin(admin.ModelAdmin):
    list_display = ["discount_percentage", "is_active", "start_datetime", "end_datetime", "updated_at"]
    list_filter = ["is_active"]
    fieldsets = (
        (None, {
            "fields": ("is_active", "discount_percentage"),
        }),
        ("Schedule", {
            "fields": ("start_datetime", "end_datetime"),
            "description": "Offer automatically activates at start and deactivates at end.",
        }),
    )


@admin.register(TimeBasedOffer)
class TimeBasedOfferAdmin(admin.ModelAdmin):
    list_display = ["title", "discount_percentage", "is_active", "start_date", "end_date", "usage_count"]
    list_filter = ["is_active"]
    search_fields = ["title"]
    readonly_fields = ["usage_count"]
    fieldsets = (
        (None, {
            "fields": ("title", "description", "discount_percentage", "is_active"),
        }),
        ("Media", {
            "fields": ("banner_image", "background_color", "popup_image"),
        }),
        ("Schedule", {
            "fields": (("start_date", "start_time"), ("end_date", "end_time")),
            "description": "Offer automatically activates during this period.",
        }),
    )


@admin.register(HeldCart)
class HeldCartAdmin(admin.ModelAdmin):
    list_display = ["id", "operator", "customer_name", "created_at"]
    search_fields = ["operator__email", "customer_name"]


@admin.register(TodayDeal)
class TodayDealAdmin(admin.ModelAdmin):
    list_display = ["title", "is_active", "start_date", "end_date"]
    list_filter = ["is_active"]
    search_fields = ["title"]
    fieldsets = (
        (None, {
            "fields": ("title", "description", "is_active"),
        }),
        ("Media", {
            "fields": ("deal_image", "deal_banner"),
        }),
        ("Schedule", {
            "fields": (("start_date", "start_time"), ("end_date", "end_time")),
            "description": "Deal automatically activates during this period.",
        }),
    )
