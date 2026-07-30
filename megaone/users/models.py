import uuid
import io
import datetime
import qrcode
from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.core.files.base import ContentFile
from django.db import models
from django.utils import timezone as tz_utils
from django.utils.crypto import get_random_string
from .format_utils import get_currency_config
from django.conf import settings
from .managers import UserManager


class QRTableOffer(models.Model):
    is_active = models.BooleanField(default=False)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def check_and_update_status(self):
        now = tz_utils.now()
        if self.start_datetime <= now <= self.end_datetime:
            if not self.is_active:
                self.is_active = True
                self.save(update_fields=["is_active"])
        elif now > self.end_datetime:
            if self.is_active:
                self.is_active = False
                self.save(update_fields=["is_active"])

    def __str__(self):
        return f"QR Offer: {self.discount_percentage}% ({'Active' if self.is_active else 'Inactive'})"


class TimeBasedOffer(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    banner_image = models.ImageField(upload_to="offer_banners/", blank=True, null=True)
    background_color = models.CharField(max_length=20, default="#f59e0b")
    popup_image = models.ImageField(upload_to="offer_popups/", blank=True, null=True)
    start_date = models.DateField()
    start_time = models.TimeField()
    end_date = models.DateField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=0, help_text="Number of times this offer has been applied")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def check_and_update_status(self):
        now = tz_utils.now()
        start = tz_utils.make_aware(
            datetime.datetime.combine(self.start_date, self.start_time)
        )
        end = tz_utils.make_aware(
            datetime.datetime.combine(self.end_date, self.end_time)
        )
        should_be_active = start <= now <= end
        if should_be_active and not self.is_active:
            self.is_active = True
            self.save(update_fields=["is_active"])
        elif not should_be_active and self.is_active:
            self.is_active = False
            self.save(update_fields=["is_active"])
        return self.is_active

    def __str__(self):
        return f"{self.title} ({self.discount_percentage}%)"


class TodayDeal(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    products = models.ManyToManyField("menu.Food", blank=True, related_name="deals")
    free_product = models.ForeignKey("menu.Food", on_delete=models.SET_NULL, null=True, blank=True, related_name="free_deals")
    combo_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Special combo price for the deal")
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Discount percentage for percentage-based deals")
    deal_image = models.ImageField(upload_to="deal_images/", blank=True, null=True)
    deal_banner = models.ImageField(upload_to="deal_banners/", blank=True, null=True)
    start_date = models.DateField()
    start_time = models.TimeField()
    end_date = models.DateField()
    end_time = models.TimeField()
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def deal_type(self):
        if self.free_product:
            return 'free_product'
        elif self.combo_price:
            return 'combo_price'
        elif self.discount_percentage:
            return 'percentage'
        return None

    def check_and_update_status(self):
        now = tz_utils.now()
        start = tz_utils.make_aware(
            datetime.datetime.combine(self.start_date, self.start_time)
        )
        end = tz_utils.make_aware(
            datetime.datetime.combine(self.end_date, self.end_time)
        )
        should_be_active = start <= now <= end
        if should_be_active and not self.is_active:
            self.is_active = True
            self.save(update_fields=["is_active"])
        elif not should_be_active and self.is_active:
            self.is_active = False
            self.save(update_fields=["is_active"])
        return self.is_active

    def __str__(self):
        return self.title


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True, db_index=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_operator = models.BooleanField(default=False)
    is_software_owner = models.BooleanField(default=False)
    timezone = models.CharField(max_length=100, default="UTC")
    date_joined = models.DateTimeField(default=tz_utils.now)
    theme_preference = models.CharField(max_length=10, blank=True, default='', help_text="User theme preference: light, dark, or empty for system default")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()


class Invoice(models.Model):
    uuid_token = models.CharField(max_length=64, unique=True, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True, blank=True
    )
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_email = models.EmailField(blank=True, null=True)
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    customer_session_id = models.CharField(max_length=100, blank=True, null=True)
    invoice_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    payment_method = models.CharField(max_length=20, blank=True, null=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    customer_timezone = models.CharField(max_length=100, default="UTC")
    qr_code_image = models.ImageField(upload_to="invoice_qrcodes/", blank=True, null=True)
    is_loyalty_payment = models.BooleanField(default=False, help_text="Paid using loyalty points")
    loyalty_points_used = models.IntegerField(default=0, help_text="Loyalty points used for payment")
    loyalty_points_earned = models.IntegerField(default=0, help_text="Loyalty points earned from this order")
    loyalty_points_processed = models.BooleanField(default=False, help_text="Prevent duplicate point processing")
    qr_offer_discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="QR Table Offer discount %")
    qr_offer_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="QR Table Offer discount amount")
    deal = models.ForeignKey("TodayDeal", on_delete=models.SET_NULL, null=True, blank=True, help_text="Associated Today's Deal")
    deal_discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Today's Deal discount amount")
    total_returned_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total amount returned against this invoice")
    total_returned_qty = models.IntegerField(default=0, help_text="Total quantity returned against this invoice")
    cash_received = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Cash received from customer")
    change_due = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Change due to customer")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='invoices_created',
        help_text="Operator/cashier who created this invoice"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.uuid_token:
            self.uuid_token = uuid.uuid4().hex
        super().save(*args, **kwargs)

    def generate_qr_code(self, request=None):
        domain = settings.QR_CODE_BASE_URL
        if request:
            domain = f"{request.scheme}://{request.get_host()}"
        secure_url = f"{domain}/users/invoice/{self.uuid_token}/verify/"
        qr = qrcode.make(secure_url)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        filename = f"invoice_{self.invoice_number}_qr.png"
        self.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=False)

    def __str__(self):
        return self.invoice_number


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="items", on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost_at_sale = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Product cost per unit at time of sale")

    def __str__(self):
        return self.product_name


class HeldCart(models.Model):
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="held_carts"
    )
    cart_data = models.JSONField()
    customer_name = models.CharField(max_length=255, blank=True, default="")
    customer_email = models.EmailField(blank=True, default="")
    customer_phone = models.CharField(max_length=20, blank=True, default="")
    invoice_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Held Cart #{self.id} by {self.operator.email}"


class LoyaltyCard(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('BLOCKED', 'Blocked'),
    ]

    card_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='loyalty_cards',
        null=True, blank=True
    )
    total_points = models.IntegerField(default=0)
    used_points = models.IntegerField(default=0)
    remaining_points = models.IntegerField(default=0)
    qr_token = models.CharField(max_length=64, unique=True, blank=True)
    qr_code_image = models.ImageField(upload_to='loyalty_qr/', blank=True, null=True)
    card_pdf = models.FileField(upload_to='loyalty_cards/pdf/', blank=True, null=True)
    card_image = models.ImageField(upload_to='loyalty_cards/images/', blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    first_card_popup_shown = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'loyalty_cards_loyaltycard'

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.card_number:
            while True:
                cnum = f"LC{get_random_string(10).upper()}"
                if not LoyaltyCard.objects.filter(card_number=cnum).exists():
                    self.card_number = cnum
                    break
        if not self.qr_token:
            self.qr_token = get_random_string(32)
        self.remaining_points = self.total_points - self.used_points
        super().save(*args, **kwargs)
        if is_new and self.total_points == 0:
            self.total_points = 50
            self.remaining_points = 50
            self.save(update_fields=['total_points', 'remaining_points'])
            LoyaltyTransaction.objects.create(
                card=self,
                order_number="WELCOME",
                earned_points=50,
                redeemed_points=0,
                remaining_balance=50,
                transaction_type='EARN'
            )

    def add_points(self, points, order_number=""):
        if points < 0:
            raise ValueError("Points cannot be negative")
        self.total_points += points
        self.remaining_points = self.total_points - self.used_points
        self.save()
        LoyaltyTransaction.objects.create(
            card=self,
            order_number=order_number,
            earned_points=points,
            redeemed_points=0,
            remaining_balance=self.remaining_points,
            transaction_type='EARN'
        )

    def redeem_points(self, points, order_number=""):
        if points < 0:
            raise ValueError("Points cannot be negative")
        if self.remaining_points < points:
            raise ValueError("Insufficient points balance")
        self.used_points += points
        self.remaining_points = self.total_points - self.used_points
        self.save()
        LoyaltyTransaction.objects.create(
            card=self,
            order_number=order_number,
            earned_points=0,
            redeemed_points=points,
            remaining_balance=self.remaining_points,
            transaction_type='REDEEM'
        )

    def generate_qr_data(self):
        return {
            "token": self.qr_token,
            "card": self.card_number,
            "customer": self.user.id if self.user else 0,
        }

    def __str__(self):
        return f"Loyalty Card {self.card_number}"


class LoyaltyTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('EARN', 'Earn'),
        ('REDEEM', 'Redeem'),
    ]

    card = models.ForeignKey(LoyaltyCard, on_delete=models.CASCADE, related_name='transactions')
    order_number = models.CharField(max_length=50, blank=True, null=True)
    earned_points = models.IntegerField(default=0)
    redeemed_points = models.IntegerField(default=0)
    remaining_balance = models.IntegerField(default=0)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'loyalty_cards_loyaltytransaction'

    def __str__(self):
        return f"{self.transaction_type} - {self.card.card_number}"


class OperatorPermission(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='operator_permissions'
    )
    can_create_invoice = models.BooleanField(default=False)
    can_edit_invoice = models.BooleanField(default=False)
    can_delete_invoice = models.BooleanField(default=False)
    can_apply_discount = models.BooleanField(default=False)
    can_view_reports = models.BooleanField(default=False)
    can_manage_inventory = models.BooleanField(default=False)
    can_manage_products = models.BooleanField(default=False)
    can_manage_categories = models.BooleanField(default=False)
    can_stock_adjustment = models.BooleanField(default=False)
    can_manage_customers = models.BooleanField(default=False)
    can_view_dashboard_analytics = models.BooleanField(default=False)
    can_export_reports = models.BooleanField(default=False)
    can_print_invoice = models.BooleanField(default=False)
    can_cancel_invoice = models.BooleanField(default=False)
    can_stock_position = models.BooleanField(default=False)
    can_returns = models.BooleanField(default=False)
    can_access_wholesale = models.BooleanField(default=False, help_text="Can access wholesale POS and management")
    can_manage_users = models.BooleanField(default=False)
    can_view_wholesale_deposits = models.BooleanField(default=False)
    can_create_wholesale_deposit = models.BooleanField(default=False)
    can_edit_wholesale_deposits = models.BooleanField(default=False)
    can_delete_wholesale_deposits = models.BooleanField(default=False)
    can_export_wholesale_deposits = models.BooleanField(default=False)
    can_create_expense = models.BooleanField(default=False)
    can_view_expenses = models.BooleanField(default=False)
    can_edit_expenses = models.BooleanField(default=False)
    can_delete_expenses = models.BooleanField(default=False)
    can_manage_expense_categories = models.BooleanField(default=False)
    can_view_expense_reports = models.BooleanField(default=False)
    can_manage_wholesale_credit = models.BooleanField(default=False, help_text="Can manage credit settlements and adjustments")
    can_view_wholesale_credit_reports = models.BooleanField(default=False, help_text="Can view wholesale credit reports")
    can_access_settings = models.BooleanField(default=False, help_text="Can access system settings (admin level)")
    can_manage_company = models.BooleanField(default=False, help_text="Can manage company profile and branding (admin level)")

    # Cash Handling Permissions
    cash_session_open = models.BooleanField(default=False, help_text="Can open a cash drawer session")
    cash_session_close = models.BooleanField(default=False, help_text="Can close a cash drawer session")
    cash_session_view = models.BooleanField(default=False, help_text="Can view own cash drawer session details")
    cash_session_view_all = models.BooleanField(default=False, help_text="Can view all cash drawer sessions across users (admin)")
    cash_session_force_close = models.BooleanField(default=False, help_text="Can force close any user's cash drawer session (admin)")
    cash_session_reopen = models.BooleanField(default=False, help_text="Can reopen a closed cash drawer session (admin)")
    cash_in = models.BooleanField(default=False, help_text="Can add cash to drawer")
    cash_out = models.BooleanField(default=False, help_text="Can remove cash from drawer")
    cash_drop = models.BooleanField(default=False, help_text="Can record cash drops")
    cash_refund_approve = models.BooleanField(default=False, help_text="Can approve cash refunds")
    cash_void_approve = models.BooleanField(default=False, help_text="Can approve cash voids")
    cash_override = models.BooleanField(default=False, help_text="Can override cash handling limits")
    cash_report_view = models.BooleanField(default=False, help_text="Can view cash handling reports")
    cash_dashboard_view = models.BooleanField(default=False, help_text="Can view cash handling dashboard")
    cash_drawer_view = models.BooleanField(default=False, help_text="Can view cash drawers list")
    cash_transaction_view = models.BooleanField(default=False, help_text="Can view cash transactions")
    cash_no_sale = models.BooleanField(default=False, help_text="Can perform no-sale operations")
    cash_denomination_count = models.BooleanField(default=False, help_text="Can count denominations")
    cash_reconciliation = models.BooleanField(default=False, help_text="Can perform closing reconciliation")
    cash_audit_logs = models.BooleanField(default=False, help_text="Can view cash audit logs")
    cash_settings_manage = models.BooleanField(default=False, help_text="Can manage cash handling settings")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'operator_permissions'
        verbose_name = 'Operator Permission'
        verbose_name_plural = 'Operator Permissions'

    def __str__(self):
        return f"Permissions for {self.user.email}"


class WholesaleDeposit(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('mobile_payment', 'Mobile Payment'),
        ('card', 'Card'),
        ('other', 'Other'),
    ]

    customer = models.ForeignKey(
        'WholesaleCustomer', on_delete=models.CASCADE,
        related_name='deposits'
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    notes = models.TextField(blank=True, default='')
    deposit_date = models.DateTimeField()
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='wholesale_deposits'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, default='')
    is_reversed = models.BooleanField(default=False)
    reversed_at = models.DateTimeField(null=True, blank=True)
    reversed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reversed_wholesale_deposits'
    )
    reverse_reason = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'wholesale_deposits'
        ordering = ['-created_at']
        verbose_name = 'Wholesale Deposit'
        verbose_name_plural = 'Wholesale Deposits'

    def __str__(self):
        return f"Deposit #{self.id} - {self.customer.company_name} - {get_currency_config()['symbol']}{self.amount}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new:
            WholesaleAccountTransaction.objects.create(
                customer=self.customer,
                transaction_type='deposit',
                amount=self.amount,
                balance_before=self.balance_before,
                balance_after=self.balance_after,
                performed_by=self.created_by,
                notes=f"Deposit #{self.id}: {self.notes}" if self.notes else f"Deposit #{self.id}",
            )


class PendingApproval(models.Model):
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='pending_approvals'
    )
    invoice = models.ForeignKey(
        'Invoice', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='pending_approvals'
    )
    cart_data = models.JSONField()
    customer_name = models.CharField(max_length=255, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    payment_method = models.CharField(max_length=50, default="cash")
    invoice_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)
    notes = models.TextField(blank=True, default="")
    loyalty_points_to_redeem = models.IntegerField(default=0)

    class Meta:
        db_table = 'pending_approvals'
        ordering = ['-created_at']

    def __str__(self):
        return f"Pending #{self.id} by {self.operator.email}"


class ReturnInvoice(models.Model):
    INVOICE_TYPE_CHOICES = [
        ('retail', 'Retail'),
        ('wholesale', 'Wholesale'),
    ]

    original_invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='returns', null=True, blank=True)
    wholesale_original_invoice = models.ForeignKey('WholesaleInvoice', on_delete=models.CASCADE, related_name='returns', null=True, blank=True)
    invoice_type = models.CharField(max_length=20, choices=INVOICE_TYPE_CHOICES, default='retail')
    returned_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    return_date = models.DateTimeField(auto_now_add=True)
    return_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    total_refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_phone = models.CharField(max_length=15, blank=True, null=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'return_invoices'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)
        if is_new and not self.return_number:
            self.return_number = f"RI-{self.id:06d}"
            self.save(update_fields=["return_number"])

    def __str__(self):
        return self.return_number or f"Return #{self.id}"


class ReturnInvoiceItem(models.Model):
    return_invoice = models.ForeignKey(ReturnInvoice, on_delete=models.CASCADE, related_name='items')
    original_item_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Original InvoiceItem ID")
    product_name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    sku = models.CharField(max_length=100, blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'return_invoice_items'

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class WholesaleCustomer(models.Model):
    ACCOUNT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('frozen', 'Frozen'),
    ]

    company_name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255)
    email = models.EmailField(unique=True, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    account_status = models.CharField(max_length=20, choices=ACCOUNT_STATUS_CHOICES, default='active')
    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    used_credit = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total credit amount currently used across invoices")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_deposits = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_redeemed = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def available_credit(self):
        return max(0, self.credit_limit - self.used_credit)

    class Meta:
        db_table = 'wholesale_customers'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.company_name} ({self.contact_person})"


class WholesaleInvoice(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('paid', 'Paid'),
        ('partial', 'Partial Paid'),
        ('credit_due', 'Credit Due'),
        ('overdue', 'Overdue'),
        ('returned', 'Returned'),
    ]

    uuid_token = models.CharField(max_length=64, unique=True, blank=True)
    wholesale_customer = models.ForeignKey(
        WholesaleCustomer, on_delete=models.CASCADE, related_name='invoices'
    )
    invoice_number = models.CharField(max_length=50, unique=True, default=uuid.uuid4)
    payment_method = models.CharField(max_length=20, blank=True, null=True)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    subtotal_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Deposit made during this checkout")
    redeemed_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Amount redeemed from account during this checkout")
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Account balance before this transaction")
    cash_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    change_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    credit_used = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Amount covered by credit")
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total amount actually paid (cash + redeem + deposit)")
    remaining_due = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Outstanding amount still due")
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='paid')
    due_date = models.DateTimeField(null=True, blank=True, help_text="Expected payment due date for credit invoices")
    qr_code_image = models.ImageField(upload_to="wholesale_qrcodes/", blank=True, null=True)
    total_returned_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Total amount returned against this invoice")
    total_returned_qty = models.IntegerField(default=0, help_text="Total quantity returned against this invoice")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wholesale_invoices'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        if not self.uuid_token:
            self.uuid_token = uuid.uuid4().hex
        if isinstance(self.invoice_number, uuid.UUID):
            self.invoice_number = str(self.invoice_number)
        super().save(*args, **kwargs)
        if is_new and not self.invoice_number.startswith('WS-'):
            self.invoice_number = f"WS-{self.id:06d}"
            self.save(update_fields=["invoice_number"])

    def generate_qr_code(self, request=None):
        domain = settings.QR_CODE_BASE_URL
        if request:
            domain = f"{request.scheme}://{request.get_host()}"
        secure_url = f"{domain}/users/wholesale/invoice/{self.uuid_token}/verify/"
        qr = qrcode.make(secure_url)
        buffer = io.BytesIO()
        qr.save(buffer, format="PNG")
        filename = f"wholesale_invoice_{self.invoice_number}_qr.png"
        self.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=False)

    def __str__(self):
        return self.invoice_number


class WholesaleInvoiceItem(models.Model):
    wholesale_invoice = models.ForeignKey(WholesaleInvoice, related_name='items', on_delete=models.CASCADE)
    product_name = models.CharField(max_length=255)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost_at_sale = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Product cost per unit at time of sale")

    class Meta:
        db_table = 'wholesale_invoice_items'

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


class WholesaleCreditSettlement(models.Model):
    customer = models.ForeignKey(WholesaleCustomer, on_delete=models.CASCADE, related_name='credit_settlements')
    invoice = models.ForeignKey('WholesaleInvoice', on_delete=models.SET_NULL, null=True, blank=True, related_name='credit_settlements')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    settlement_date = models.DateTimeField(default=tz_utils.now)
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='wholesale_credit_settlements')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wholesale_credit_settlements'
        ordering = ['-created_at']

    def __str__(self):
        return f"Credit settlement #{self.id} - {self.customer.company_name} - {get_currency_config()['symbol']}{self.amount}"


class WholesaleAccountTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('redeem', 'Redeem'),
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('adjustment', 'Adjustment'),
        ('credit', 'Credit Usage'),
        ('credit_settlement', 'Credit Settlement'),
    ]

    customer = models.ForeignKey(WholesaleCustomer, on_delete=models.CASCADE, related_name='account_transactions')
    invoice = models.ForeignKey(WholesaleInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='account_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=12, decimal_places=2)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='wholesale_account_actions')
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'wholesale_account_transactions'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.transaction_type} - {self.customer.company_name} - {get_currency_config()['symbol']}{self.amount}"


class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'expense_categories'
        ordering = ['name']
        verbose_name = 'Expense Category'
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name


class BusinessExpense(models.Model):
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('card', 'Card'),
        ('mobile_payment', 'Mobile Payment'),
        ('other', 'Other'),
    ]

    category = models.ForeignKey(
        ExpenseCategory, on_delete=models.CASCADE,
        related_name='expenses'
    )
    title = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='cash')
    expense_date = models.DateTimeField()
    description = models.TextField(blank=True, default='')
    attachment = models.FileField(upload_to='expense_attachments/', blank=True, null=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='business_expenses'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='deleted_expenses'
    )

    class Meta:
        db_table = 'business_expenses'
        ordering = ['-created_at']
        verbose_name = 'Business Expense'
        verbose_name_plural = 'Business Expenses'

    def __str__(self):
        return f"{self.title} - {get_currency_config()['symbol']}{self.amount}"


class AccountingEntry(models.Model):
    ENTRY_TYPES = (
        ('sale', 'Sale'),
        ('return', 'Return'),
        ('expense', 'Expense'),
    )
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    invoice = models.ForeignKey(Invoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_entries')
    return_invoice = models.ForeignKey(ReturnInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_entries')
    expense = models.ForeignKey('BusinessExpense', on_delete=models.SET_NULL, null=True, blank=True, related_name='accounting_entries')
    description = models.CharField(max_length=255)
    debit_account = models.CharField(max_length=100)
    credit_account = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'accounting_entries'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.entry_type}: {self.description} ({self.amount})"


class SystemSetting(models.Model):
    company_name = models.CharField(max_length=255, default='POS')
    company_logo = models.ImageField(upload_to='company/', blank=True, null=True)
    company_address = models.TextField(blank=True, default='')
    company_phone = models.CharField(max_length=50, blank=True, default='')
    company_email = models.EmailField(blank=True, default='')
    company_website = models.URLField(blank=True, default='')
    tax_number = models.CharField(max_length=100, blank=True, default='')
    tax_label = models.CharField(max_length=100, default='GST')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    currency_symbol = models.CharField(max_length=10, default='\u20b9')
    currency_code = models.CharField(max_length=10, default='INR')
    invoice_prefix = models.CharField(max_length=20, default='INV-')
    invoice_footer_text = models.TextField(blank=True, default='')
    receipt_prefix = models.CharField(max_length=20, default='RCP-')
    receipt_footer_text = models.TextField(blank=True, default='')
    default_payment_terms = models.CharField(max_length=255, blank=True, default='')
    timezone = models.CharField(max_length=100, default='Asia/Kolkata')
    enable_notifications = models.BooleanField(default=True)
    low_stock_threshold = models.PositiveIntegerField(default=10)
    enabled_modules = models.JSONField(default=list, blank=True, help_text="Module codes enabled for the business")
    superuser_created = models.BooleanField(default=False, help_text="Whether the first business superuser has been created")
    is_active = models.BooleanField(default=True)
    default_theme = models.CharField(max_length=20, default='user_choice', help_text="light, dark, or user_choice")
    allow_theme_selection = models.BooleanField(default=True, help_text="Allow users to switch themes")
    dark_mode_enabled = models.BooleanField(default=True, help_text="Enable dark mode availability")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='system_settings_updated'
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'system_settings'
        verbose_name = 'System Setting'
        verbose_name_plural = 'System Settings'

    def __str__(self):
        return self.company_name


class StockMovement(models.Model):
    TRANSACTION_TYPES = [
        ('opening_stock', 'Opening Stock'),
        ('stock_adjustment', 'Stock Adjustment'),
        ('retail_sale', 'Retail Sale'),
        ('wholesale_sale', 'Wholesale Sale'),
        ('stock_purchase', 'Stock Purchase'),
        ('retail_return', 'Retail Return'),
        ('wholesale_return', 'Wholesale Return'),
    ]
    food = models.ForeignKey('menu.Food', on_delete=models.CASCADE, related_name='stock_movements')
    transaction_type = models.CharField(max_length=30, choices=TRANSACTION_TYPES)
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Invoice/Return number")
    quantity_change = models.IntegerField(help_text="Positive for stock in, negative for stock out")
    stock_before = models.IntegerField()
    stock_after = models.IntegerField()
    notes = models.TextField(blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(default=tz_utils.now)

    class Meta:
        db_table = 'stock_movements'
        ordering = ['-created_at']
        verbose_name = 'Stock Movement'
        verbose_name_plural = 'Stock Movements'

    def __str__(self):
        return f"{self.get_transaction_type_display()}: {self.food.name} ({self.quantity_change:+d})"


class InventoryBatch(models.Model):
    food = models.ForeignKey('menu.Food', on_delete=models.CASCADE, related_name='inventory_batches')
    purchase_date = models.DateTimeField(default=tz_utils.now)
    quantity = models.PositiveIntegerField(help_text="Original purchase quantity")
    remaining_quantity = models.PositiveIntegerField(help_text="Quantity still in stock")
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, help_text="Cost per unit for this batch")
    total_cost = models.DecimalField(max_digits=12, decimal_places=2, help_text="Total cost of this batch")
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Selling price at time of purchase")
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Wholesale price at time of purchase")
    supplier = models.CharField(max_length=255, blank=True, null=True, help_text="Supplier name")
    purchase_reference = models.CharField(max_length=100, blank=True, null=True, help_text="Purchase order / reference number")
    notes = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inventory_batches'
        ordering = ['purchase_date', 'id']
        verbose_name = 'Inventory Batch'
        verbose_name_plural = 'Inventory Batches'

    def __str__(self):
        return f"{self.food.name} batch #{self.id} ({self.remaining_quantity} @ {self.unit_cost})"


class SaleItemCost(models.Model):
    inventory_batch = models.ForeignKey(InventoryBatch, on_delete=models.CASCADE, related_name='sale_costs')
    invoice_item = models.ForeignKey('InvoiceItem', on_delete=models.CASCADE, null=True, blank=True, related_name='sale_costs')
    wholesale_invoice_item = models.ForeignKey('WholesaleInvoiceItem', on_delete=models.CASCADE, null=True, blank=True, related_name='sale_costs')
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'sale_item_costs'
        verbose_name = 'Sale Item Cost'
        verbose_name_plural = 'Sale Item Costs'

    def __str__(self):
        return f"SaleItemCost: {self.quantity} x {self.unit_cost} (batch #{self.inventory_batch_id})"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('user_creation', 'User Creation'),
        ('user_deactivation', 'User Deactivation'),
        ('user_activation', 'User Activation'),
        ('permission_change', 'Permission Change'),
        ('company_update', 'Company Information Update'),
        ('logo_change', 'Logo Change'),
        ('settings_change', 'System Settings Change'),
        ('password_reset', 'Password Reset'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='audit_logs'
    )
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        username = self.user.email if self.user else 'System'
        return f"{self.get_action_display()} by {username} at {self.created_at}"


class KeyboardShortcut(models.Model):
    action = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=200)
    category = models.CharField(max_length=100, default='general')
    key = models.CharField(max_length=50, blank=True, default='')
    ctrl = models.BooleanField(default=False)
    shift = models.BooleanField(default=False)
    alt = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'keyboard_shortcuts'
        ordering = ['category', 'label']
        verbose_name = 'Keyboard Shortcut'
        verbose_name_plural = 'Keyboard Shortcuts'

    def __str__(self):
        return f"{self.label} ({self.display_key})"

    @property
    def display_key(self):
        parts = []
        if self.ctrl: parts.append('Ctrl')
        if self.alt: parts.append('Alt')
        if self.shift: parts.append('Shift')
        if self.key: parts.append(self.key.upper())
        return '+'.join(parts) if parts else 'None'
