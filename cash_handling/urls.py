from django.urls import path
from . import views

app_name = "cash_handling"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    path("dashboard/data/", views.dashboard_data, name="dashboard_data"),

    # Cash Drawers
    path("drawers/", views.cash_drawers, name="cash_drawers"),

    # Sessions
    path("session/open/", views.session_open, name="session_open"),
    path("session/open-page/", views.session_open_page, name="session_open_page"),
    path("session/close/", views.session_close, name="session_close"),
    path("session/close-page/", views.session_close_page, name="session_close_page"),
    path("session/status/", views.session_status, name="session_status"),
    path("session/<int:session_id>/", views.session_detail, name="session_detail"),
    path("session/<int:session_id>/force-close/", views.session_force_close, name="session_force_close"),
    path("session/<int:session_id>/reopen/", views.session_reopen, name="session_reopen"),
    path("sessions/", views.session_history, name="session_history"),

    # Cash Operations
    path("cash/in/", views.cash_in, name="cash_in"),
    path("cash/in-page/", views.cash_in_page, name="cash_in_page"),
    path("cash/out/", views.cash_out, name="cash_out"),
    path("cash/out-page/", views.cash_out_page, name="cash_out_page"),
    path("cash/drop/", views.cash_drop, name="cash_drop"),
    path("cash/drop-page/", views.cash_drop_page, name="cash_drop_page"),

    # No Sale
    path("no-sale/", views.no_sale, name="no_sale"),
    path("no-sale-page/", views.no_sale_page, name="no_sale_page"),

    # Denomination Count
    path("denomination-count/", views.denomination_count_page, name="denomination_count"),
    path("denomination-count/save/", views.denomination_count_save, name="denomination_count_save"),

    # Reconciliation
    path("reconciliation/", views.closing_reconciliation_page, name="closing_reconciliation"),

    # Refunds & Voids
    path("refunds/", views.refunds, name="refunds"),
    path("void-sales/", views.void_sales, name="void_sales"),

    # Approvals
    path("approvals/", views.approvals, name="approvals"),
    path("approvals/respond/", views.approval_respond, name="approval_respond"),
    path("approvals/request/", views.approval_request, name="approval_request"),

    # Transactions
    path("transactions/", views.transaction_list, name="transaction_list"),

    # Reports & Audit
    path("reports/", views.reports, name="reports"),
    path("audit-logs/", views.audit_logs, name="audit_logs"),
]
