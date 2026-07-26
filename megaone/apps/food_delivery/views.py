from django.shortcuts import redirect


index_view = lambda request: redirect("users:login")
food_accounts_view = lambda request: redirect("users:login")
login_view = lambda request: redirect("users:login")
registration_view = lambda request: redirect("users:login")
restaurant_detail_view = lambda request: redirect("users:login")
restaurant_listing_view = lambda request: redirect("users:login")
