from django.urls import path, include
from .views import (
    food_delivery_restaurant_detail,
    logout_view, add_product, product_list,
    edit_product, delete_product,
    admin_dashboard, food_delivery_login,
    register_view, search_users,
    user_detail_view, user_redirect_view, user_update_view,
    products_export_csv,
    categories_export_csv,
    expense_categories_export_csv,
    loyalty_cards_export_csv,
    stock_movements_export_csv, stock_position_export_csv,
    invoices_export_csv, wholesale_invoices_export_csv,
    returns_export_csv, suppliers_export_csv, customers_export_csv,
    offers_export_csv, deals_export_csv,
    wholesale_customers_export_csv,
)
from megaone.users import views

app_name = "users"

urlpatterns = [
    path("logout/", logout_view, name="logout"),
    path("register/", register_view, name="register"),
    path("checkout/", views.checkout_invoice, name="checkout_invoice"),
    path("guest-checkout/", views.guest_checkout, name="guest_checkout"),

    # Operator
    path("operator/dashboard/", views.operator_dashboard, name="operator_dashboard"),
    # Operator User Management
    path("create-operator/", views.create_operator, name="create_operator"),
    path("operators/", views.operator_list, name="operator_list"),
    path("edit-operator/<int:id>/", views.edit_operator, name="edit_operator"),
    path("delete-operator/<int:id>/", views.delete_operator, name="delete_operator"),
    path("toggle-operator/<int:id>/", views.toggle_operator_active, name="toggle_operator_active"),
    path("reset-operator-password/<int:id>/", views.reset_operator_password, name="reset_operator_password"),

    # Search
    path("search-invoice/", views.search_invoice, name="search_invoice"),
    path("search-products/", views.search_products, name="search_products"),
    path("search-users/", search_users, name="search_users"),

    # Timezone
    path("set-timezone/", views.set_timezone, name="set_timezone"),

    # Invoice PDF (secure token-based)
    path("invoice/<str:uuid_token>/", views.invoice_pdf, name="invoice_pdf"),

    # Invoice Verify (for QR scanning)
    path("invoice/<str:uuid_token>/verify/", views.invoice_verify, name="invoice_verify"),

    # Secure Invoice View -> Redirects to PDF
    path("invoice/<str:uuid_token>/details/", views.secure_invoice_view, name="secure_invoice_view"),
    path("bulk-invoice-pdf/", views.bulk_invoice_pdf, name="bulk_invoice_pdf"),

    # Invoice Detail (by invoice_no, legacy) -> Redirects to PDF
    path("invoice-detail/<str:invoice_no>/", views.invoice_detail, name="invoice_detail"),

    # Admin
    path("dashboard/", admin_dashboard, name="admin_dashboard"),
    path("dashboard/data/", views.dashboard_data, name="dashboard_data"),
    path("pos/", views.admin_pos, name="admin_pos"),
    path("revenue-filter/", views.revenue_filter, name="revenue_filter"),
    path("tax-analytics/", views.tax_analytics, name="tax_analytics"),
    path("profit-loss-data/", views.profit_loss_data, name="profit_loss_data"),
    path("chart-data/", views.chart_data, name="chart_data"),
    path("profit-loss-statement/", views.profit_loss_statement, name="profit_loss_statement"),
    path("profit-loss-statement/pdf/", views.profit_loss_export_pdf, name="profit_loss_export_pdf"),
    path("profit-loss-statement/excel/", views.profit_loss_export_excel, name="profit_loss_export_excel"),

    # Products
    path("products/", product_list, name="product_list"),
    path("products/add/", add_product, name="add_product"),
    path("products/<int:pk>/edit/", edit_product, name="edit_product"),
    path("products/<int:pk>/delete/", delete_product, name="delete_product"),
    path("products/add-stock/", views.add_stock, name="add_stock"),

    # Invoice Search Page
    path("invoices/", views.invoice_search_page, name="invoice_search_page"),

    # Operator Users Page
    path("operator-users/", views.operator_users_page, name="operator_users_page"),

    # Categories
    path("categories/", views.category_list, name="category_list"),
    path("categories/add/", views.category_add, name="category_add"),
    path("categories/<int:pk>/edit/", views.category_edit, name="category_edit"),
    path("categories/<int:pk>/delete/", views.category_delete, name="category_delete"),
    path("categories/<int:pk>/toggle/", views.category_toggle_active, name="category_toggle_active"),

    # Stock Position & Movement
    path("stock-position/", views.stock_position, name="stock_position"),
    path("stock-history/", views.stock_history, name="stock_history"),
    path("stock-movement-report/", views.stock_movement_report, name="stock_movement_report"),

    # Store Detail
    path("restaurant-detail/", food_delivery_restaurant_detail, name="food_delivery_restaurant_detail"),

    # Auth
    path("login/", food_delivery_login, name="login"),
    path("mysql-backup/", views.mysql_backup, name="mysql_backup"),
    path("backup/run/", views.backup_run, name="backup_run"),
    path("backup/toggle-auto/", views.backup_toggle_auto, name="backup_toggle_auto"),
    path("backup/download/", views.backup_download, name="backup_download"),

    # User
    path("<int:pk>/", user_detail_view, name="detail"),
    path("~redirect/", user_redirect_view, name="redirect"),
    path("update/", user_update_view, name="update"),

    # Loyalty Card
    path("loyalty-card/", views.loyalty_card_view, name="loyalty_card_view"),
    path("loyalty-card/history/", views.loyalty_transactions, name="loyalty_transactions"),
    path("loyalty-card/pdf/<str:card_number>/", views.download_loyalty_pdf, name="download_loyalty_pdf"),
    path("loyalty-card/image/<str:card_number>/", views.download_loyalty_image, name="download_loyalty_image"),
    path("loyalty-card/data/", views.loyalty_card_data, name="loyalty_card_data"),
    path("loyalty-card/checkout-info/", views.loyalty_checkout_info, name="loyalty_checkout_info"),
    path("loyalty-card/checkout-validate/", views.loyalty_checkout_validate, name="loyalty_checkout_validate"),
    path("loyalty-card/verify-qr/<str:qr_token>/", views.verify_loyalty_qr, name="verify_loyalty_qr"),
    path("loyalty-card/from-qr/<str:qr_token>/", views.qr_loyalty_redirect, name="qr_loyalty_redirect"),

    # Admin Loyalty
    path("loyalty-card/admin/list/", views.admin_loyalty_list, name="admin_loyalty_list"),
    path("loyalty-card/admin/card/<str:card_number>/", views.admin_loyalty_detail, name="admin_loyalty_detail"),
    path("loyalty-card/admin/card/<str:card_number>/toggle/", views.admin_toggle_card_status, name="admin_toggle_card_status"),
    path("loyalty-card/admin/card/<str:card_number>/reset/", views.admin_reset_points, name="admin_reset_points"),

    # Offers & Deals API
    path("offers/active-data/", views.active_offer_data, name="active_offer_data"),
    path("deals/active-data/", views.active_deal_data, name="active_deal_data"),
    path("offers/banner-data/", views.offer_banner_data, name="offer_banner_data"),

    # Offer CRUD
    path("offers/", views.offer_list, name="offer_list"),
    path("offers/add/", views.offer_add, name="offer_add"),
    path("offers/<int:pk>/", views.offer_detail, name="offer_detail"),
    path("offers/<int:pk>/edit/", views.offer_edit, name="offer_edit"),
    path("offers/<int:pk>/delete/", views.offer_delete, name="offer_delete"),

    # Deal CRUD
    path("deals/", views.deal_list, name="deal_list"),
    path("deals/add/", views.deal_add, name="deal_add"),
    path("deals/<int:pk>/", views.deal_detail, name="deal_detail"),
    path("deals/<int:pk>/edit/", views.deal_edit, name="deal_edit"),
    path("deals/<int:pk>/delete/", views.deal_delete, name="deal_delete"),

    # Public Deal Views
    path("deals/<int:pk>/public/", views.public_deal_detail, name="public_deal_detail"),
    path("deals/<int:pk>/checkout/", views.deal_checkout, name="deal_checkout"),
    path("clear-deal-cart/", views.clear_deal_cart, name="clear_deal_cart"),

    # Operator Cart AJAX
    path("operator/cart/", views.operator_cart_data, name="operator_cart_data"),
    path("operator/cart/add/", views.operator_cart_add, name="operator_cart_add"),
    path("operator/cart/update/", views.operator_cart_update, name="operator_cart_update"),
    path("operator/cart/remove/", views.operator_cart_remove, name="operator_cart_remove"),
    path("operator/cart/clear/", views.operator_cart_clear, name="operator_cart_clear"),
    path("operator/cart/set-discount/", views.operator_set_discount, name="operator_set_discount"),
    path("operator/cart/hold/", views.operator_hold_invoice, name="operator_hold_invoice"),
    path("operator/cart/held/", views.operator_held_invoices, name="operator_held_invoices"),
    path("operator/cart/resume/<int:held_id>/", views.operator_resume_held, name="operator_resume_held"),
    path("operator/cart/delete-held/<int:held_id>/", views.operator_delete_held, name="operator_delete_held"),
    path("operator/checkout/", views.operator_checkout, name="operator_checkout"),
    path("operator/customer-search/", views.operator_customer_search, name="operator_customer_search"),
    path("operator/loyalty-lookup/", views.operator_loyalty_lookup, name="operator_loyalty_lookup"),
    path("operator/session-status/", views.operator_session_status, name="operator_session_status"),

    # Barcode Printing & Lookup
    path("barcode/print/<int:pk>/", views.barcode_print, name="barcode_print"),
    path("barcode/print-multiple/", views.barcode_print_multiple, name="barcode_print_multiple"),
    path("barcode/lookup/", views.barcode_lookup, name="barcode_lookup"),

    # Operator Permissions
    path("operator-permissions/", views.admin_operator_permissions, name="admin_operator_permissions"),

    # Pending Approvals
    path("pending-approvals/", views.admin_pending_approvals, name="admin_pending_approvals"),
    path("pending-approvals/<int:pk>/approve/", views.admin_approve_request, name="admin_approve_request"),

    # Return Invoice
    path("return-invoice/", views.return_invoice_page, name="return_invoice_page"),
    path("return-invoice/search/", views.return_invoice_search, name="return_invoice_search"),
    path("return-invoice/items/<int:invoice_id>/", views.return_invoice_get_items, name="return_invoice_get_items"),
    path("return-invoice/save/", views.return_invoice_save, name="return_invoice_save"),
    path("return-invoice/history/", views.return_invoice_history, name="return_invoice_history"),
    path("return-invoice/receipt/<int:return_id>/", views.return_invoice_receipt, name="return_invoice_receipt"),
    path("return-invoice/print/<int:return_id>/", views.return_invoice_pdf, name="return_invoice_pdf"),

    # Wholesale Module
    path("wholesale/pos/", views.wholesale_pos_page, name="wholesale_pos_page"),
    path("wholesale/customer/search/", views.wholesale_customer_search, name="wholesale_customer_search"),
    path("wholesale/cart/", views.wholesale_cart_data, name="wholesale_cart_data"),
    path("wholesale/cart/add/", views.wholesale_cart_add, name="wholesale_cart_add"),
    path("wholesale/cart/update/", views.wholesale_cart_update, name="wholesale_cart_update"),
    path("wholesale/cart/remove/", views.wholesale_cart_remove, name="wholesale_cart_remove"),
    path("wholesale/cart/clear/", views.wholesale_cart_clear, name="wholesale_cart_clear"),
    path("wholesale/cart/set-discount/", views.wholesale_set_discount, name="wholesale_set_discount"),
    path("wholesale/checkout/", views.wholesale_checkout, name="wholesale_checkout"),
    path("wholesale/invoice/<str:uuid_token>/", views.wholesale_invoice_pdf, name="wholesale_invoice_pdf"),
    path("wholesale/invoice/<str:uuid_token>/verify/", views.wholesale_invoice_verify, name="wholesale_invoice_verify"),

    # Wholesale Customer Management
    path("wholesale/customers/", views.wholesale_customer_list, name="wholesale_customer_list"),
    path("wholesale/customers/add/", views.wholesale_customer_add, name="wholesale_customer_add"),
    path("wholesale/customers/<int:pk>/edit/", views.wholesale_customer_edit, name="wholesale_customer_edit"),
    path("wholesale/customers/<int:pk>/toggle/", views.wholesale_customer_toggle, name="wholesale_customer_toggle"),

    # Wholesale Reports
    path("wholesale/reports/sales/", views.wholesale_sales_report, name="wholesale_sales_report"),
    path("wholesale/reports/customers/", views.wholesale_customer_report, name="wholesale_customer_report"),
    path("wholesale/reports/invoices/", views.wholesale_invoice_report, name="wholesale_invoice_report"),
    path("wholesale/reports/revenue/", views.wholesale_revenue_summary, name="wholesale_revenue_summary"),

    # Wholesale Account / Wallet
    path("wholesale/account/info/", views.wholesale_account_info, name="wholesale_account_info"),
    path("wholesale/account/deposit/", views.wholesale_account_deposit, name="wholesale_account_deposit"),
    path("wholesale/account/transactions/", views.wholesale_account_transactions, name="wholesale_account_transactions"),
    path("wholesale/account/adjust/", views.wholesale_account_adjust, name="wholesale_account_adjust"),

    # Business Expenses
    path("expenses/categories/", views.expense_category_list, name="expense_category_list"),
    path("expenses/categories/add/", views.expense_category_add, name="expense_category_add"),
    path("expenses/categories/<int:pk>/edit/", views.expense_category_edit, name="expense_category_edit"),
    path("expenses/categories/<int:pk>/toggle/", views.expense_category_toggle, name="expense_category_toggle"),
    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/add/", views.expense_add, name="expense_add"),
    path("expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),
    path("expenses/<int:pk>/", views.expense_detail, name="expense_detail"),
    path("expenses/report/", views.expense_report, name="expense_report"),
    path("expenses/export/", views.expense_export, name="expense_export"),

    # Wholesale Deposits
    path("wholesale/deposits/", views.wholesale_deposit_list, name="wholesale_deposit_list"),
    path("wholesale/deposits/create/", views.wholesale_deposit_create, name="wholesale_deposit_create"),
    path("wholesale/deposits/<int:pk>/", views.wholesale_deposit_detail, name="wholesale_deposit_detail"),
    path("wholesale/deposits/<int:pk>/reverse/", views.wholesale_deposit_reverse, name="wholesale_deposit_reverse"),
    path("wholesale/deposits/report/", views.wholesale_deposit_report, name="wholesale_deposit_report"),
    path("wholesale/deposits/export/", views.wholesale_deposit_export, name="wholesale_deposit_export"),

    # Wholesale Customer Detail (full account + history)
    path("wholesale/customers/<int:pk>/detail/", views.wholesale_customer_detail, name="wholesale_customer_detail"),

    # Wholesale Credit Management
    path("wholesale/credit/settlements/", views.wholesale_credit_settlement_list, name="wholesale_credit_settlement_list"),
    path("wholesale/credit/settlements/create/", views.wholesale_credit_settlement_create, name="wholesale_credit_settlement_create"),
    path("wholesale/credit/settlements/<int:pk>/", views.wholesale_credit_settlement_detail, name="wholesale_credit_settlement_detail"),
    path("wholesale/credit/outstanding-invoices/", views.wholesale_customer_outstanding_invoices, name="wholesale_customer_outstanding_invoices"),
    path("wholesale/credit/report/", views.wholesale_credit_report, name="wholesale_credit_report"),

    # Data Migration
    path("data-migration/", include("megaone.users.data_migration.urls")),

    # Software Owner
    path("software-owner/dashboard/", views.software_owner_dashboard, name="software_owner_dashboard"),
    path("settings/", views.system_settings, name="system_settings"),
    path("settings/keyboard-shortcuts/", views.keyboard_shortcuts, name="keyboard_shortcuts"),
    path("settings/keyboard-shortcuts/pdf/", views.keyboard_shortcuts_pdf, name="keyboard_shortcuts_pdf"),
    path("settings/active-shortcuts/", views.active_shortcuts, name="active_shortcuts"),
    path("audit-logs/", views.audit_logs, name="audit_logs"),
    path("save-theme/", views.save_theme, name="save_theme"),

    # CSV Export
    path("products/export/", products_export_csv, name="products_export_csv"),
    path("categories/export/", categories_export_csv, name="categories_export_csv"),
    path("expense-categories/export/", expense_categories_export_csv, name="expense_categories_export_csv"),
    path("loyalty-cards/export/", loyalty_cards_export_csv, name="loyalty_cards_export_csv"),
    path("stock-movements/export/", stock_movements_export_csv, name="stock_movements_export_csv"),
    path("stock-position/export/", stock_position_export_csv, name="stock_position_export_csv"),
    path("invoices/export/", invoices_export_csv, name="invoices_export_csv"),
    path("wholesale-invoices/export/", wholesale_invoices_export_csv, name="wholesale_invoices_export_csv"),
    path("returns/export/", returns_export_csv, name="returns_export_csv"),
    path("wholesale-customers/export/", wholesale_customers_export_csv, name="wholesale_customers_export_csv"),
    path("suppliers/export/", suppliers_export_csv, name="suppliers_export_csv"),
    path("customers/export/", customers_export_csv, name="customers_export_csv"),
    path("offers/export/", offers_export_csv, name="offers_export_csv"),
    path("deals/export/", deals_export_csv, name="deals_export_csv"),

    # Bulk Actions
    path("bulk-action/", views.bulk_action, name="bulk_action"),

]
