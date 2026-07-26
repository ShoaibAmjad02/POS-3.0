from django.contrib import admin

from .models import Cart, Order, OrderItem


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ["user", "food", "quantity", "created_at"]


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "user", "status", "total_amount", "created_at"]
    search_fields = ["user__email"]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ["order", "food", "quantity", "price"]
