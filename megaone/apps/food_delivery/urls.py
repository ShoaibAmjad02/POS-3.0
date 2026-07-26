from django.urls import path

from .views import (
    index_view,
    food_accounts_view,
    login_view,
    registration_view,
    restaurant_detail_view,
    restaurant_listing_view
)

app_name = "food_delivery"

urlpatterns = [
    path("", view=index_view, name="food_delivery_index"),
    path("accounts", view=food_accounts_view, name="food_delivery_accounts"),
    path("login", view=login_view, name="food_delivery_login"),    
    path("registration", view=registration_view, name="food_delivery_registration"),    
    path("restaurant-detail", view=restaurant_detail_view, name="food_delivery_restaurant_detail"),    
    path("restaurant-listing", view=restaurant_listing_view, name="food_delivery_restaurant_listing"),    
]
