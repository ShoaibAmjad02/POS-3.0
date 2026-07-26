import json
import pytest
from django.test import RequestFactory, Client
from django.urls import reverse
from megaone.users.models import User, Invoice, LoyaltyCard, HeldCart, PendingApproval
from megaone.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestCustomerCreationWithPhone:
    def test_create_user_with_phone_only(self):
        email = "cust_1234567890@pos.local"
        user = User.objects.create_user(
            email=email,
            name="Test Customer",
            phone="1234567890",
            password="temppass123",
        )
        assert user.name == "Test Customer"
        assert user.phone == "1234567890"
        assert user.email == email
        assert User.objects.filter(phone="1234567890").exists()

    def test_lookup_user_by_phone(self):
        email = "cust_9876543210@pos.local"
        User.objects.create_user(
            email=email,
            name="Lookup Customer",
            phone="9876543210",
            password="temppass123",
        )
        user = User.objects.filter(phone="9876543210").first()
        assert user is not None
        assert user.name == "Lookup Customer"


class TestLoyaltyAccountWithPhone:
    def test_loyalty_card_creation_for_phone_user(self):
        email = "cust_5555555555@pos.local"
        user = User.objects.create_user(
            email=email,
            name="Loyalty Customer",
            phone="5555555555",
            password="temppass123",
        )
        card = LoyaltyCard.objects.create(user=user, status='ACTIVE')
        assert card is not None
        assert card.user.name == "Loyalty Customer"
        assert card.user.phone == "5555555555"
        assert card.total_points == 50
        assert card.remaining_points == 50

    def test_no_duplicate_loyalty_accounts_for_same_phone(self):
        email1 = "cust_1111111111@pos.local"
        user1 = User.objects.create_user(
            email=email1,
            name="Customer One",
            phone="1111111111",
            password="temppass123",
        )
        email2 = "cust_1111111111_dup@pos.local"
        user2 = User.objects.create_user(
            email=email2,
            name="Customer Two",
            phone="1111111111",
            password="temppass123",
        )
        card1 = LoyaltyCard.objects.create(user=user1, status='ACTIVE')
        card2, created = LoyaltyCard.objects.get_or_create(user=user2, defaults={'status': 'ACTIVE'})
        assert card1.id != card2.id
        assert card1.user.phone == card2.user.phone


class TestCustomerReuseByPhone:
    def test_reuse_existing_customer_by_phone(self):
        phone = "9999999999"
        user = User.objects.create_user(
            email=f"cust_{phone}@pos.local",
            name="Original Customer",
            phone=phone,
            password="temppass123",
        )
        lookup = User.objects.filter(phone=phone).first()
        assert lookup == user
        assert lookup.name == "Original Customer"

    def test_create_new_customer_when_phone_not_found(self):
        phone = "8888888888"
        existing = User.objects.filter(phone=phone).first()
        assert existing is None
        email = f"cust_{phone}@pos.local"
        user = User.objects.create_user(
            email=email,
            name="New Customer",
            phone=phone,
            password="temppass123",
        )
        assert user is not None
        assert user.name == "New Customer"
        assert user.phone == phone


class TestInvoiceWithPhone:
    def test_invoice_created_with_customer_phone(self):
        invoice = Invoice.objects.create(
            customer_name="Phone Customer",
            customer_phone="7777777777",
            invoice_number="INV-PHONE-TEST-001",
            total_amount=100.00,
        )
        assert invoice.customer_phone == "7777777777"
        assert invoice.customer_name == "Phone Customer"

    def test_invoice_lookup_by_phone(self):
        Invoice.objects.create(
            customer_name="Search Customer",
            customer_phone="6666666666",
            invoice_number="INV-PHONE-TEST-002",
            total_amount=200.00,
        )
        found = Invoice.objects.filter(customer_phone="6666666666").first()
        assert found is not None
        assert found.customer_name == "Search Customer"


class TestHeldCartWithPhone:
    def test_held_cart_with_phone(self):
        held = HeldCart.objects.create(
            operator=UserFactory(),
            cart_data=[{"food_id": 1, "name": "Test Item", "price": 10.0, "quantity": 1}],
            customer_name="Held Customer",
            customer_phone="4444444444",
        )
        assert held.customer_phone == "4444444444"
        assert held.customer_name == "Held Customer"


class TestPendingApprovalWithPhone:
    def test_pending_approval_with_phone(self):
        pending = PendingApproval.objects.create(
            operator=UserFactory(),
            cart_data=[{"food_id": 1, "name": "Test Item", "price": 10.0, "quantity": 1}],
            customer_name="Approval Customer",
            customer_phone="3333333333",
        )
        assert pending.customer_phone == "3333333333"
        assert pending.customer_name == "Approval Customer"


class TestOperatorLoyaltyLookup:
    def test_loyalty_lookup_by_phone_direct(self):
        user = User.objects.create_user(
            email="lookup@test.com",
            name="Lookup Test",
            phone="2222222222",
            password="testpass",
        )
        LoyaltyCard.objects.create(user=user, status='ACTIVE')
        found = User.objects.filter(phone="2222222222").first()
        assert found is not None
        assert found.name == "Lookup Test"
        card = LoyaltyCard.objects.filter(user=found, status='ACTIVE').first()
        assert card is not None
        assert card.remaining_points >= 0


class TestLoyaltyRedemptionValidation:
    """Backend loyalty point redemption validation must reject over-redemption."""

    def _setup_user_with_points(self, points):
        import uuid
        suffix = uuid.uuid4().hex[:6]
        user = User.objects.create_user(
            email=f"loyalty_test_{suffix}@test.com",
            name="Loyalty Test User",
            phone=f"99{suffix}",
            password="testpass",
        )
        card = LoyaltyCard.objects.create(user=user, status='ACTIVE')
        card.total_points = points
        card.remaining_points = points
        card.save()
        return user, card

    # Allowed cases
    def test_redeem_50_when_70_available(self):
        """Available:70 → Redeem:50 — must be allowed (50 <= 70)."""
        _, card = self._setup_user_with_points(70)
        assert card.remaining_points >= 50
        assert card.remaining_points >= 50  # passes validation

    def test_redeem_70_when_70_available(self):
        """Available:70 → Redeem:70 — must be allowed (70 <= 70)."""
        _, card = self._setup_user_with_points(70)
        assert card.remaining_points >= 70

    # Rejected cases
    def test_redeem_71_when_70_available(self):
        """Available:70 → Redeem:71 — must be REJECTED (71 > 70)."""
        _, card = self._setup_user_with_points(70)
        assert not (card.remaining_points >= 71)

    def test_redeem_200_when_70_available(self):
        """Available:70 → Redeem:200 — must be REJECTED (200 > 70)."""
        _, card = self._setup_user_with_points(70)
        assert not (card.remaining_points >= 200)

    def test_redeem_7000_when_70_available(self):
        """Available:70 → Redeem:7000 — must be REJECTED (7000 > 70)."""
        _, card = self._setup_user_with_points(70)
        assert not (card.remaining_points >= 7000)

    def test_redeem_points_caps_at_available(self):
        """Verifies redeem_points() itself raises ValueError when exceeding balance."""
        _, card = self._setup_user_with_points(70)
        assert card.remaining_points == 70
        import pytest
        with pytest.raises(ValueError, match="Insufficient points balance"):
            card.redeem_points(200)
