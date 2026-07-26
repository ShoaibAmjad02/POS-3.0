from django.contrib import admin
from .models import Food, Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "is_active", "discount_type", "discount_value")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "name",
        "category",
        "price",
        "cost_price",
        "stock",
        "barcode",
        "product_code",
        "discount_type",
        "discount_value",
        "available",
    )

    list_filter = (
        "is_popular",
        "available",
        "category",
        "discount_type",
    )

    search_fields = (
        "name",
        "barcode",
        "product_code",
        "sku",
        "category__name",
    )