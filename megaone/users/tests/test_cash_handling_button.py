import json
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from cash_handling.models import CashDrawerSession, CashTransaction
from cash_handling.services import CashDrawerService
from megaone.users.models import AuditLog, OperatorPermission, SystemSetting, User
from megaone.users.tests.factories import UserFactory


pytestmark = pytest.mark.django_db


class TestCashHandlingButtonVisibility:
    BUTTON_MARKER = "Cash Handling"

    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def _create_operator(self, cash_dashboard_view=False):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(
            user=user,
            defaults={"cash_dashboard_view": cash_dashboard_view},
        )
        return user

    def test_operator_with_cash_handling_perm_sees_button(self):
        user = self._create_operator(cash_dashboard_view=True)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:operator_dashboard"))
        assert response.status_code == 200
        assert self.BUTTON_MARKER in response.content.decode()

    def test_operator_without_cash_handling_perm_hides_button(self):
        user = self._create_operator(cash_dashboard_view=False)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:operator_dashboard"))
        assert response.status_code == 200
        assert self.BUTTON_MARKER not in response.content.decode()


class TestNewPermissionsExist:
    def _create_operator(self, **perm_kwargs):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(user=user, defaults=perm_kwargs)
        return User.objects.get(pk=user.pk)  # Refresh to bust cached relations

    def test_cash_session_view_field_exists(self):
        user = self._create_operator(cash_session_view=True)
        assert user.operator_permissions.cash_session_view is True

    def test_cash_session_view_all_field_exists(self):
        user = self._create_operator(cash_session_view_all=True)
        assert user.operator_permissions.cash_session_view_all is True

    def test_cash_session_force_close_field_exists(self):
        user = self._create_operator(cash_session_force_close=True)
        assert user.operator_permissions.cash_session_force_close is True

    def test_cash_session_reopen_field_exists(self):
        user = self._create_operator(cash_session_reopen=True)
        assert user.operator_permissions.cash_session_reopen is True


class TestSessionContextProcessor:
    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def _create_operator(self, **perm_kwargs):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(user=user, defaults=perm_kwargs)
        return User.objects.get(pk=user.pk)

    def test_session_view_in_user_perms(self):
        user = self._create_operator(cash_session_view=True)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:operator_dashboard"))
        assert response.status_code == 200

    def test_session_view_all_true_when_permission_granted(self):
        from megaone.users.context_processors import user_permissions as ctx_user_permissions
        user = self._create_operator(cash_session_view_all=True)
        from django.http import HttpRequest
        req = HttpRequest()
        req.user = user
        result = ctx_user_permissions(req)
        assert result['user_perms']['cash_handling']['session_view_all'] is True

    def test_session_view_all_false_when_not_granted(self):
        from megaone.users.context_processors import user_permissions as ctx_user_permissions
        user = self._create_operator(cash_session_view_all=False)
        from django.http import HttpRequest
        req = HttpRequest()
        req.user = user
        result = ctx_user_permissions(req)
        assert result['user_perms']['cash_handling']['session_view_all'] is False


class TestSessionForceCloseReopen:
    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def _create_admin_user(self):
        user = UserFactory(is_operator=False, is_staff=True, is_superuser=False)
        OperatorPermission.objects.update_or_create(
            user=user,
            defaults={
                "cash_session_force_close": True,
                "cash_session_reopen": True,
                "cash_drawer_view": True,
            },
        )
        return user

    def _create_operator_with_session(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(
            user=user,
            defaults={"cash_session_open": True, "cash_session_close": True},
        )
        session = CashDrawerService.open_session(user=user, opening_balance=Decimal("100"))
        return user, session

    def test_force_close_session(self):
        admin = self._create_admin_user()
        operator, session = self._create_operator_with_session()
        client = Client()
        client.force_login(admin)
        response = client.post(
            reverse("cash_handling:session_force_close", args=[session.id]),
            json.dumps({"notes": "Force closed for testing"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is True
        session.refresh_from_db()
        assert session.status == "closed"
        assert session.closed_by == admin

    def test_force_close_creates_audit_log(self):
        admin = self._create_admin_user()
        operator, session = self._create_operator_with_session()
        client = Client()
        client.force_login(admin)
        client.post(
            reverse("cash_handling:session_force_close", args=[session.id]),
            json.dumps({"notes": "Force closed for testing"}),
            content_type="application/json",
        )
        assert AuditLog.objects.filter(action="session_force_close").count() == 1

    def test_reopen_session(self):
        admin = self._create_admin_user()
        operator, session = self._create_operator_with_session()
        CashDrawerService.close_session(session=session, user=operator)
        client = Client()
        client.force_login(admin)
        response = client.post(
            reverse("cash_handling:session_reopen", args=[session.id]),
            json.dumps({"notes": "Reopened for testing"}),
            content_type="application/json",
        )
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["success"] is True
        session.refresh_from_db()
        assert session.status == "open"
        assert session.closed_by is None
        assert session.closed_at is None

    def test_reopen_creates_audit_log(self):
        admin = self._create_admin_user()
        operator, session = self._create_operator_with_session()
        CashDrawerService.close_session(session=session, user=operator)
        client = Client()
        client.force_login(admin)
        client.post(
            reverse("cash_handling:session_reopen", args=[session.id]),
            json.dumps({"notes": "Reopened for testing"}),
            content_type="application/json",
        )
        assert AuditLog.objects.filter(action="session_reopen").count() == 1

    def test_force_close_without_permission_denied(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(user=user, defaults={"cash_session_force_close": False, "cash_drawer_view": True})
        operator, session = self._create_operator_with_session()
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse("cash_handling:session_force_close", args=[session.id]),
            json.dumps({"notes": "Should fail"}),
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_reopen_without_permission_denied(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(user=user, defaults={"cash_session_reopen": False, "cash_drawer_view": True})
        operator, session = self._create_operator_with_session()
        CashDrawerService.close_session(session=session, user=operator)
        client = Client()
        client.force_login(user)
        response = client.post(
            reverse("cash_handling:session_reopen", args=[session.id]),
            json.dumps({"notes": "Should fail"}),
            content_type="application/json",
        )
        assert response.status_code == 403


class TestPOSSessionStatus:
    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def test_pos_session_status_no_session(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(user=user)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:operator_session_status"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["has_active_session"] is False

    def test_pos_session_status_with_session(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(user=user, defaults={"cash_session_open": True, "cash_session_close": True})
        user = User.objects.get(pk=user.pk)
        CashDrawerService.open_session(user=user, opening_balance=Decimal("200"))
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:operator_session_status"))
        assert response.status_code == 200
        data = json.loads(response.content)
        assert data["has_active_session"] is True
        assert data["opening_balance"] == 200.0
        assert data["current_balance"] == 200.0

    def test_pos_session_status_shows_permissions(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(
            user=user,
            defaults={"cash_session_open": True, "cash_session_close": False},
        )
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:operator_session_status"))
        data = json.loads(response.content)
        assert data["session_open_perm"] is True
        assert data["session_close_perm"] is False


class TestOperatorCannotCloseOthersSession:
    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def test_operator_cannot_close_another_operators_session(self):
        op1 = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        op2 = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(user=op1, defaults={"cash_session_open": True, "cash_session_close": True})
        OperatorPermission.objects.update_or_create(user=op2, defaults={"cash_session_close": True})
        CashDrawerService.open_session(user=op1, opening_balance=Decimal("100"))
        client = Client()
        client.force_login(op2)
        response = client.post(
            reverse("cash_handling:session_close"),
            json.dumps({"closing_balance": 100}),
            content_type="application/json",
        )
        data = json.loads(response.content)
        assert "No open session" in data.get("error", "")


class TestSessionAuditLogging:
    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def test_session_open_creates_audit_log(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(
            user=user,
            defaults={"cash_session_open": True, "cash_dashboard_view": True},
        )
        client = Client()
        client.force_login(user)
        client.post(
            reverse("cash_handling:session_open"),
            json.dumps({"opening_balance": 500}),
            content_type="application/json",
        )
        assert AuditLog.objects.filter(action="session_open").count() == 1

    def test_session_close_creates_audit_log(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(
            user=user,
            defaults={"cash_session_open": True, "cash_session_close": True, "cash_dashboard_view": True},
        )
        CashDrawerService.open_session(user=user, opening_balance=Decimal("300"))
        client = Client()
        client.force_login(user)
        client.post(
            reverse("cash_handling:session_close"),
            json.dumps({"closing_balance": 300}),
            content_type="application/json",
        )
        assert AuditLog.objects.filter(action="session_close").count() == 1


class TestAdminStaffCashHandlingSidebar:
    BUTTON_MARKER = "Cash Handling"

    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def _create_admin(self, cash_dashboard_view=True):
        user = UserFactory(is_operator=False, is_staff=True, is_superuser=False)
        OperatorPermission.objects.update_or_create(
            user=user,
            defaults={"cash_dashboard_view": cash_dashboard_view},
        )
        return user

    def test_admin_sees_cash_handling_in_sidebar(self):
        user = self._create_admin(cash_dashboard_view=True)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        assert response.status_code == 200
        assert self.BUTTON_MARKER in response.content.decode()

    def test_admin_hidden_when_permission_disabled(self):
        user = self._create_admin(cash_dashboard_view=False)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        assert response.status_code == 200
        assert self.BUTTON_MARKER not in response.content.decode()

    def test_admin_hidden_when_module_disabled(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos"]},
        )
        user = self._create_admin(cash_dashboard_view=True)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        assert response.status_code == 200
        assert self.BUTTON_MARKER not in response.content.decode()


class TestAdminStaffCashHandlingDashboardWidget:
    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def _create_admin(self, cash_dashboard_view=True):
        user = UserFactory(is_operator=False, is_staff=True, is_superuser=False)
        OperatorPermission.objects.update_or_create(
            user=user,
            defaults={"cash_dashboard_view": cash_dashboard_view},
        )
        return user

    def test_admin_sees_cash_drawer_widget(self):
        user = self._create_admin(cash_dashboard_view=True)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        assert response.status_code == 200
        assert "Cash Drawer" in response.content.decode()

    def test_admin_hides_widget_when_permission_disabled(self):
        user = self._create_admin(cash_dashboard_view=False)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        assert response.status_code == 200
        assert "Cash Drawer" not in response.content.decode()

    def test_admin_hides_widget_when_module_disabled(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos"]},
        )
        user = self._create_admin(cash_dashboard_view=True)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        assert response.status_code == 200
        assert "Cash Drawer" not in response.content.decode()


class TestOperatorCashHandlingButtonRegression:
    BUTTON_MARKER = "Cash Handling"

    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def _create_operator(self, cash_dashboard_view=True):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(
            user=user,
            defaults={"cash_dashboard_view": cash_dashboard_view},
        )
        return user

    def test_operator_hidden_when_module_disabled_but_permission_enabled(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos"]},
        )
        user = self._create_operator(cash_dashboard_view=True)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:operator_dashboard"))
        assert response.status_code == 200
        assert self.BUTTON_MARKER not in response.content.decode()

    def test_operator_hidden_when_module_disabled_and_permission_disabled(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos"]},
        )
        user = self._create_operator(cash_dashboard_view=False)
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:operator_dashboard"))
        assert response.status_code == 200
        assert self.BUTTON_MARKER not in response.content.decode()


class TestSoftwareOwnerCashHandling:
    BUTTON_MARKER = "Cash Handling"

    def _create_software_owner(self):
        return UserFactory(is_operator=False, is_staff=False, is_superuser=False, is_software_owner=True)

    def test_software_owner_sees_all_cash_permissions_in_context(self):
        from megaone.users.context_processors import user_permissions as ctx_user_permissions
        from django.http import HttpRequest
        user = self._create_software_owner()
        SystemSetting.objects.update_or_create(pk=1, defaults={"enabled_modules": []})
        req = HttpRequest()
        req.user = user
        result = ctx_user_permissions(req)
        assert result['user_perms']['cash_handling']['session_open'] is True
        assert result['user_perms']['cash_handling']['dashboard_view'] is True


class TestContextProcessorModuleGating:
    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos"]},
        )

    def _create_staff_user(self, cash_session_open=True):
        user = UserFactory(is_operator=False, is_staff=True, is_superuser=False)
        OperatorPermission.objects.update_or_create(
            user=user,
            defaults={"cash_session_open": cash_session_open},
        )
        return User.objects.get(pk=user.pk)

    def test_permission_forced_false_when_module_disabled(self):
        from megaone.users.context_processors import user_permissions as ctx_user_permissions
        from django.http import HttpRequest
        user = self._create_staff_user(cash_session_open=True)
        req = HttpRequest()
        req.user = user
        result = ctx_user_permissions(req)
        assert result['user_perms']['cash_handling']['session_open'] is False

    def test_module_disabled_gates_all_cash_permissions(self):
        from megaone.users.context_processors import user_permissions as ctx_user_permissions
        from django.http import HttpRequest
        user = self._create_staff_user(cash_session_open=True)
        OperatorPermission.objects.filter(user=user).update(
            cash_dashboard_view=True, cash_drawer_view=True
        )
        user = User.objects.get(pk=user.pk)
        req = HttpRequest()
        req.user = user
        result = ctx_user_permissions(req)
        assert result['user_perms']['cash_handling']['session_open'] is False
        assert result['user_perms']['cash_handling']['dashboard_view'] is False
        assert result['user_perms']['cash_handling']['drawer_view'] is False


class TestStaffPermissionInitialization:
    def test_new_staff_user_gets_all_cash_permissions(self):
        user = UserFactory(is_operator=False, is_staff=True, is_superuser=False)
        perm = OperatorPermission.objects.get(user=user)
        cash_fields = [f.name for f in OperatorPermission._meta.get_fields()
                       if f.name.startswith('cash_')
                       and hasattr(f, 'get_internal_type')
                       and f.get_internal_type() == 'BooleanField']
        for field in cash_fields:
            assert getattr(perm, field) is True, f"{field} should be True for new staff"

    def test_new_operator_gets_default_false_cash_permissions(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        perm = OperatorPermission.objects.get(user=user)
        cash_fields = [f.name for f in OperatorPermission._meta.get_fields()
                       if f.name.startswith('cash_')
                       and hasattr(f, 'get_internal_type')
                       and f.get_internal_type() == 'BooleanField']
        for field in cash_fields:
            assert getattr(perm, field) is False, f"{field} should be False for new operator"

    def test_operator_promoted_to_staff_gets_cash_permissions(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        perm = OperatorPermission.objects.get(user=user)
        for field in [f.name for f in OperatorPermission._meta.get_fields()
                      if f.name.startswith('cash_')
                      and hasattr(f, 'get_internal_type')
                      and f.get_internal_type() == 'BooleanField']:
            assert getattr(perm, field) is False
        user.is_staff = True
        user.save()
        perm = OperatorPermission.objects.get(user=user)
        for field in [f.name for f in OperatorPermission._meta.get_fields()
                      if f.name.startswith('cash_')
                      and hasattr(f, 'get_internal_type')
                      and f.get_internal_type() == 'BooleanField']:
            assert getattr(perm, field) is True, f"{field} should be True after promotion to staff"

    def test_staff_user_with_stale_permissions_fixed_on_save(self):
        user = UserFactory(is_operator=False, is_staff=True, is_superuser=False)
        OperatorPermission.objects.filter(user=user).update(cash_dashboard_view=False)
        user.save()
        perm = OperatorPermission.objects.get(user=user)
        assert perm.cash_dashboard_view is True


class TestDataMigrations:
    def test_cash_handling_module_added_when_missing(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos"]},
        )
        from django.core.management import call_command
        call_command('migrate', 'users', '0037', fake=True, verbosity=0)
        s = SystemSetting.objects.get(pk=1)
        assert 'cash_handling' in s.enabled_modules
        assert 'pos' in s.enabled_modules

    def test_cash_handling_not_duplicated_when_already_present(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )
        from django.core.management import call_command
        call_command('migrate', 'users', '0037', fake=True, verbosity=0)
        s = SystemSetting.objects.get(pk=1)
        assert len([m for m in s.enabled_modules if m == 'cash_handling']) == 1


class TestOperatorPromotedToStaffIntegration:
    BUTTON_MARKER = "Cash Handling"

    @pytest.fixture(autouse=True)
    def _enable_modules(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def test_promoted_operator_sees_cash_handling_on_admin_dashboard(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        user.is_staff = True
        user.save()
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        assert response.status_code == 200
        assert self.BUTTON_MARKER in response.content.decode()

    def test_promoted_operator_sidebar_includes_cash_handling(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        user.is_staff = True
        user.save()
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        html = response.content.decode()
        assert 'Cash Handling' in html
        assert 'sub-cash-handling' in html

    def test_check_operator_permission_returns_true_after_promotion(self):
        from megaone.users.permissions import _check_operator_permission
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        result_before = _check_operator_permission(user, 'cash_dashboard_view')
        assert result_before is False
        user.is_staff = True
        user.save()
        user = User.objects.get(pk=user.pk)
        result_after = _check_operator_permission(user, 'cash_dashboard_view')
        assert result_after is True

    def test_promoted_operator_staff_gets_can_permissions_too(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        perm_before = OperatorPermission.objects.get(user=user)
        assert perm_before.can_create_invoice is False
        assert perm_before.can_manage_products is False
        user.is_staff = True
        user.save()
        perm_after = OperatorPermission.objects.get(user=user)
        assert perm_after.can_create_invoice is True
        assert perm_after.can_manage_products is True


class TestRefactoredTemplatesUsePermissionOnly:
    BUTTON_MARKER = "Cash Handling"

    @pytest.fixture(autouse=True)
    def _setup(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )

    def test_admin_sidebar_shows_cash_handling(self):
        user = UserFactory(is_operator=False, is_staff=True, is_superuser=False)
        OperatorPermission.objects.update_or_create(user=user, defaults={"cash_dashboard_view": True})
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        html = response.content.decode()
        assert 'Cash Handling' in html
        assert 'sub-cash-handling' in html

    def test_admin_sidebar_hides_cash_handling_when_permission_disabled(self):
        user = UserFactory(is_operator=False, is_staff=True, is_superuser=False)
        OperatorPermission.objects.update_or_create(user=user, defaults={"cash_dashboard_view": False})
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        html = response.content.decode()
        assert 'Cash Handling' not in html

    def test_operator_button_shows_cash_handling(self):
        user = UserFactory(is_operator=True, is_staff=False, is_superuser=False)
        OperatorPermission.objects.update_or_create(user=user, defaults={"cash_dashboard_view": True})
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:operator_dashboard"))
        html = response.content.decode()
        assert 'Cash Handling' in html
        assert '/cash/' in html

    def test_software_owner_sees_cash_handling_in_sidebar(self):
        SystemSetting.objects.update_or_create(
            pk=1,
            defaults={"enabled_modules": ["pos", "cash_handling"]},
        )
        user = UserFactory(is_operator=False, is_staff=True, is_superuser=False, is_software_owner=True)
        OperatorPermission.objects.update_or_create(user=user, defaults={"cash_dashboard_view": True})
        client = Client()
        client.force_login(user)
        response = client.get(reverse("users:admin_dashboard"))
        html = response.content.decode()
        assert 'Cash Handling' in html
        assert 'sub-cash-handling' in html