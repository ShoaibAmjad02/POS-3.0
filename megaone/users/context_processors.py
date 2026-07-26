from django.conf import settings
from .permissions import has_permission, has_module_access, _get_enabled_modules


PERMISSION_FLAT_MAP = {
    'return_invoice': 'can_returns',
}

PERMISSION_MAP = {
    'dashboard': {'view': None},
    'sales': {
        'create': 'can_create_invoice',
        'view': None,
        'edit': 'can_edit_invoice',
        'delete': 'can_delete_invoice',
        'discount': 'can_apply_discount',
        'print': 'can_print_invoice',
        'cancel': 'can_cancel_invoice',
    },
    'purchases': {
        'create': None,
        'view': None,
        'edit': None,
        'delete': None,
    },
    'products': {
        'create': 'can_manage_products',
        'view': None,
        'edit': 'can_manage_products',
        'delete': 'can_manage_products',
        'categories': 'can_manage_categories',
    },
    'customers': {
        'manage': 'can_manage_customers',
    },
    'suppliers': {
        'manage': None,
    },
    'inventory': {
        'view': 'can_manage_inventory',
        'stock_position': 'can_stock_position',
        'stock_adjustment': 'can_stock_adjustment',
    },
    'reports': {
        'view': 'can_view_reports',
        'export': 'can_export_reports',
        'dashboard_analytics': 'can_view_dashboard_analytics',
    },
    'users': {
        'manage': 'can_manage_users',
    },
    'settings': {
        'manage': None,
        'access': 'can_access_settings',
    },
    'company': {
        'manage': 'can_manage_company',
    },
    'wholesale': {
        'access': 'can_access_wholesale',
        'deposits': {
            'view': 'can_view_wholesale_deposits',
            'create': 'can_create_wholesale_deposit',
            'edit': 'can_edit_wholesale_deposits',
            'delete': 'can_delete_wholesale_deposits',
            'export': 'can_export_wholesale_deposits',
        },
        'credit': {
            'manage': 'can_manage_wholesale_credit',
            'reports': 'can_view_wholesale_credit_reports',
        },
    },
    'expenses': {
        'create': 'can_create_expense',
        'view': 'can_view_expenses',
        'edit': 'can_edit_expenses',
        'delete': 'can_delete_expenses',
        'categories': 'can_manage_expense_categories',
        'reports': 'can_view_expense_reports',
    },
    'cash_handling': {
        'dashboard_view': 'cash_dashboard_view',
        'drawer_view': 'cash_drawer_view',
        'session_open': 'cash_session_open',
        'session_close': 'cash_session_close',
        'session_view': 'cash_session_view',
        'session_view_all': 'cash_session_view_all',
        'session_force_close': 'cash_session_force_close',
        'session_reopen': 'cash_session_reopen',
        'transaction_view': 'cash_transaction_view',
        'cash_in': 'cash_in',
        'cash_out': 'cash_out',
        'cash_drop': 'cash_drop',
        'no_sale': 'cash_no_sale',
        'denomination_count': 'cash_denomination_count',
        'reconciliation': 'cash_reconciliation',
        'refund_approve': 'cash_refund_approve',
        'void_approve': 'cash_void_approve',
        'override': 'cash_override',
        'report_view': 'cash_report_view',
        'audit_logs': 'cash_audit_logs',
        'settings_manage': 'cash_settings_manage',
    },
}


MODULE_PERMISSION_MAP = {
    'products.create': 'products',
    'products.view': 'products',
    'products.edit': 'products',
    'products.delete': 'products',
    'products.categories': 'products',
    'customers.manage': 'customers',
    'suppliers.manage': 'customers',
    'inventory.view': 'inventory',
    'inventory.stock_position': 'inventory',
    'inventory.stock_adjustment': 'inventory',
    'reports.view': 'reports',
    'reports.export': 'reports',
    'reports.dashboard_analytics': 'reports',
    'return_invoice': 'returns',
    'users.manage': 'user_management',
    'settings.access': 'settings',
    'company.manage': 'settings',
    'sales.create': 'pos',
    'sales.view': 'pos',
    'sales.edit': 'pos',
    'sales.delete': 'pos',
    'sales.discount': 'pos',
    'sales.print': 'pos',
    'sales.cancel': 'pos',
    'purchases.create': 'purchases',
    'purchases.view': 'purchases',
    'purchases.edit': 'purchases',
    'purchases.delete': 'purchases',
    'wholesale.access': 'wholesale',
    'wholesale.deposits.view': 'wholesale',
    'wholesale.deposits.create': 'wholesale',
    'wholesale.deposits.edit': 'wholesale',
    'wholesale.deposits.delete': 'wholesale',
    'wholesale.deposits.export': 'wholesale',
    'wholesale.credit.manage': 'wholesale',
    'wholesale.credit.reports': 'wholesale',
    'expenses.create': 'expenses',
    'expenses.view': 'expenses',
    'expenses.edit': 'expenses',
    'expenses.delete': 'expenses',
    'expenses.categories': 'expenses',
    'expenses.reports': 'expenses',
    'cash_handling.dashboard_view': 'cash_handling',
    'cash_handling.drawer_view': 'cash_handling',
    'cash_handling.session_open': 'cash_handling',
    'cash_handling.session_close': 'cash_handling',
    'cash_handling.session_view': 'cash_handling',
    'cash_handling.session_view_all': 'cash_handling',
    'cash_handling.session_force_close': 'cash_handling',
    'cash_handling.session_reopen': 'cash_handling',
    'cash_handling.transaction_view': 'cash_handling',
    'cash_handling.cash_in': 'cash_handling',
    'cash_handling.cash_out': 'cash_handling',
    'cash_handling.cash_drop': 'cash_handling',
    'cash_handling.no_sale': 'cash_handling',
    'cash_handling.denomination_count': 'cash_handling',
    'cash_handling.reconciliation': 'cash_handling',
    'cash_handling.refund_approve': 'cash_handling',
    'cash_handling.void_approve': 'cash_handling',
    'cash_handling.override': 'cash_handling',
    'cash_handling.report_view': 'cash_handling',
    'cash_handling.audit_logs': 'cash_handling',
    'cash_handling.settings_manage': 'cash_handling',
}


def allauth_settings(request):
    return {
        "ACCOUNT_ALLOW_REGISTRATION": settings.ACCOUNT_ALLOW_REGISTRATION,
    }


def _deep_resolve_flat(nested, prefix=''):
    """Convert nested PERMISSION_MAP to flat dict with dotted keys."""
    flat = {}
    for key, value in nested.items():
        dotted = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            flat.update(_deep_resolve_flat(value, dotted))
        else:
            flat[dotted] = value
    return flat


POS_ONLY_KEYS = {
    'sales.create', 'sales.view', 'sales.edit', 'sales.delete',
    'sales.discount', 'sales.print', 'sales.cancel',
    'customers.manage',
    'return_invoice',
    'wholesale.access',
    'cash_handling.dashboard_view', 'cash_handling.drawer_view',
    'cash_handling.session_open', 'cash_handling.session_close',
    'cash_handling.session_view', 'cash_handling.session_view_all',
    'cash_handling.session_force_close', 'cash_handling.session_reopen',
    'cash_handling.transaction_view',
    'cash_handling.cash_in', 'cash_handling.cash_out', 'cash_handling.cash_drop',
    'cash_handling.no_sale',
    'cash_handling.denomination_count', 'cash_handling.reconciliation',
    'cash_handling.refund_approve', 'cash_handling.void_approve',
    'cash_handling.override',
    'cash_handling.report_view', 'cash_handling.audit_logs',
    'cash_handling.settings_manage',
}


def _resolve_user_perms(user, enabled):
    try:
        op_perms = user.operator_permissions
    except Exception:
        from .models import OperatorPermission
        if user.is_staff or getattr(user, 'is_operator', False):
            try:
                op_perms, created = OperatorPermission.objects.get_or_create(user=user)
                if created and user.is_staff:
                    all_perms = []
                    for f in OperatorPermission._meta.get_fields():
                        name = f.name
                        if not (name.startswith('can_') or name.startswith('cash_')):
                            continue
                        if not hasattr(f, 'get_internal_type'):
                            continue
                        if f.get_internal_type() == 'BooleanField':
                            all_perms.append(name)
                    for pname in all_perms:
                        setattr(op_perms, pname, True)
                    op_perms.save()
            except Exception:
                return None
        else:
            return None
    flat_map = {}
    flat_map.update(_deep_resolve_flat(PERMISSION_MAP))
    flat_map.update(PERMISSION_FLAT_MAP)
    is_operator_only = getattr(user, 'is_operator', False) and not user.is_staff
    result = {}
    for key, field in flat_map.items():
        if is_operator_only and key not in POS_ONLY_KEYS:
            result[key] = False
            continue
        module = MODULE_PERMISSION_MAP.get(key)
        if module is not None and module not in enabled:
            result[key] = False
        elif field is None:
            result[key] = True
        else:
            result[key] = getattr(op_perms, field, False)
    return result


def _build_nested(flat):
    """Convert flat dict with dotted keys to nested dict for template access."""
    nested = {}
    for dotted_key, value in flat.items():
        parts = dotted_key.split('.')
        d = nested
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
            d = d[part]
        d[parts[-1]] = value
    return nested


def user_permissions(request):
    flat = {}
    if request.user.is_authenticated:
        enabled = _get_enabled_modules()
        if request.user.is_software_owner:
            flat_map = {}
            flat_map.update(_deep_resolve_flat(PERMISSION_MAP))
            flat_map.update(PERMISSION_FLAT_MAP)
            for key in flat_map:
                flat[key] = True
        elif request.user.is_staff or getattr(request.user, 'is_operator', False):
            resolved = _resolve_user_perms(request.user, enabled)
            if resolved is not None:
                flat = resolved
            else:
                flat_map = {}
                flat_map.update(_deep_resolve_flat(PERMISSION_MAP))
                flat_map.update(PERMISSION_FLAT_MAP)
                for key in flat_map:
                    flat[key] = False
    perms = _build_nested(flat)
    return {'user_perms': perms}


def client_branding(request):
    context = {
        'company_name': 'POS',
        'company_logo': None,
        'company_email': '',
        'company_phone': '',
        'company_address': '',
        'company_tax_number': '',
        'currency_symbol': '\u20b9',
        'currency_code': 'INR',
        'tax_label': 'GST',
        'tax_rate': 0,
        'enabled_modules': [],
        'theme_mode': 'dark',
        'theme_default': 'user_choice',
        'theme_allow_switch': True,
        'theme_dark_enabled': True,
        'user_theme_pref': '',
    }
    if request.user.is_authenticated:
        from .models import SystemSetting
        settings_obj = SystemSetting.objects.filter(pk=1).first()
        if settings_obj:
            context['company_name'] = settings_obj.company_name or 'POS'
            context['company_logo'] = settings_obj.company_logo
            context['company_email'] = settings_obj.company_email
            context['company_phone'] = settings_obj.company_phone
            context['company_address'] = settings_obj.company_address
            context['company_tax_number'] = settings_obj.tax_number
            context['currency_symbol'] = settings_obj.currency_symbol
            context['currency_code'] = settings_obj.currency_code
            context['tax_label'] = settings_obj.tax_label
            context['tax_rate'] = settings_obj.tax_rate
            context['enabled_modules'] = settings_obj.enabled_modules or []
            context['theme_default'] = settings_obj.default_theme
            context['theme_allow_switch'] = settings_obj.allow_theme_selection
            context['theme_dark_enabled'] = settings_obj.dark_mode_enabled

            # Resolve effective theme
            user_pref = getattr(request.user, 'theme_preference', '')
            context['user_theme_pref'] = user_pref

            if not settings_obj.dark_mode_enabled:
                context['theme_mode'] = 'light'
            elif not settings_obj.allow_theme_selection:
                default = settings_obj.default_theme
                context['theme_mode'] = 'light' if default == 'user_choice' else default
            elif user_pref in ('light', 'dark'):
                context['theme_mode'] = user_pref
            else:
                default = settings_obj.default_theme
                context['theme_mode'] = 'light' if default == 'user_choice' else default

        if request.user.is_staff or request.user.is_software_owner:
            from .models import PendingApproval
            context['pending_approvals_count'] = PendingApproval.objects.filter(is_approved=False, is_rejected=False).count()
        else:
            context['pending_approvals_count'] = 0
    return context
