from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils import timezone


class CashDrawerSession(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('closed', 'Closed'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cash_drawer_sessions',
    )
    opened_at = models.DateTimeField(default=timezone.now)
    closed_at = models.DateTimeField(null=True, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    expected_closing = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')
    notes = models.TextField(blank=True, default='')
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='closed_cash_drawer_sessions',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cash_drawer_sessions'
        ordering = ['-opened_at']
        verbose_name = 'Cash Drawer Session'
        verbose_name_plural = 'Cash Drawer Sessions'

    def __str__(self):
        return f"Session #{self.id} ({self.user.email}) - {self.status}"


class CashTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('sale', 'Sale'),
        ('refund', 'Refund'),
        ('cash_in', 'Cash In'),
        ('cash_out', 'Cash Out'),
        ('drop', 'Cash Drop'),
        ('void_sale', 'Void Sale'),
        ('no_sale', 'No Sale'),
        ('opening_balance', 'Opening Balance'),
        ('closing_balance', 'Closing Balance'),
        ('adjustment', 'Adjustment'),
    ]

    session = models.ForeignKey(
        CashDrawerSession,
        on_delete=models.CASCADE,
        related_name='transactions',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cash_transactions',
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_before = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    balance_after = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'))
    reference_number = models.CharField(max_length=100, blank=True, null=True, help_text="Invoice/Return/Reference number")
    reference_model = models.CharField(max_length=50, blank=True, null=True, help_text="Model name (Invoice, ReturnInvoice, etc.)")
    reference_id = models.IntegerField(null=True, blank=True, help_text="Model PK")
    payment_method = models.CharField(max_length=20, blank=True, null=True, help_text="Only cash affects drawer")
    notes = models.TextField(blank=True, default='')
    idempotency_key = models.CharField(max_length=100, unique=True, null=True, blank=True, help_text="Prevent duplicate processing")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cash_transactions'
        ordering = ['-created_at']
        verbose_name = 'Cash Transaction'
        verbose_name_plural = 'Cash Transactions'

    def __str__(self):
        return f"{self.transaction_type}: {self.amount} (Session #{self.session_id})"


class DenominationCount(models.Model):
    session = models.ForeignKey(
        CashDrawerSession,
        on_delete=models.CASCADE,
        related_name='denomination_counts',
    )
    denomination_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Value of denomination (e.g. 1000, 500, 100, 50, 20, 10, 5, 1, 0.25)")
    count = models.PositiveIntegerField(default=0, help_text="Number of notes/coins of this denomination")
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0'), help_text="denomination_value * count")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cash_denomination_counts'
        ordering = ['-denomination_value']
        verbose_name = 'Denomination Count'
        verbose_name_plural = 'Denomination Counts'

    def __str__(self):
        return f"{self.count} x {self.denomination_value} = {self.subtotal}"


class CashApproval(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    TYPE_CHOICES = [
        ('refund', 'Refund Approval'),
        ('void', 'Void Approval'),
        ('override', 'Override Approval'),
    ]

    session = models.ForeignKey(
        CashDrawerSession,
        on_delete=models.CASCADE,
        related_name='approvals',
    )
    approval_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField(blank=True, default='')
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='cash_approval_requests',
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='cash_approval_decisions',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, default='')
    reference_number = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cash_approvals'
        ordering = ['-created_at']
        verbose_name = 'Cash Approval'
        verbose_name_plural = 'Cash Approvals'

    def __str__(self):
        return f"{self.approval_type} #{self.id} - {self.status}"


class NoSaleTransaction(models.Model):
    session = models.ForeignKey(
        CashDrawerSession,
        on_delete=models.CASCADE,
        related_name='no_sale_transactions',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='no_sale_transactions',
    )
    reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'cash_no_sale_transactions'
        ordering = ['-created_at']
        verbose_name = 'No Sale Transaction'
        verbose_name_plural = 'No Sale Transactions'

    def __str__(self):
        return f"No Sale #{self.id} by {self.user.email}"
