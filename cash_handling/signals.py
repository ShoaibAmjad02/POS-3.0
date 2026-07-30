from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver


def _get_cash_handling_enabled():
    try:
        from megaone.users.models import SystemSetting
        s = SystemSetting.objects.filter(pk=1).first()
        if s:
            modules = s.enabled_modules or []
            return 'cash_handling' in modules
    except Exception:
        pass
    return False


def process_sale_cash(sender, instance, created, **kwargs):
    if not created:
        return
    if not _get_cash_handling_enabled():
        return

    try:
        from megaone.users.models import Invoice
        invoice = instance
        cash_amount = Decimal('0')
        payment_method = (invoice.payment_method or 'cash').lower()

        if payment_method == 'cash':
            cash_amount = Decimal(str(invoice.total_amount))
        elif payment_method in ('mixed', 'split'):
            cash_amount = Decimal(str(invoice.cash_received or 0)) - Decimal(str(invoice.change_due or 0))
            if cash_amount < 0:
                cash_amount = Decimal('0')

        if cash_amount <= 0:
            return

        operator = invoice.created_by or invoice.user
        if not operator:
            return

        from .services import CashDrawerService
        session = CashDrawerService.get_or_create_active_session(operator)
        if not session:
            return

        idempotency_key = f"sale_{invoice.id}"
        CashDrawerService.record_sale(
            session=session,
            user=operator,
            amount=cash_amount,
            reference_number=invoice.invoice_number,
            reference_model='Invoice',
            reference_id=invoice.id,
            payment_method=payment_method,
            idempotency_key=idempotency_key,
        )
    except Exception:
        import traceback
        traceback.print_exc()


def process_return_cash(sender, instance, created, **kwargs):
    if not _get_cash_handling_enabled():
        return

    try:
        from megaone.users.models import ReturnInvoice
        return_inv = instance
        total_refund = Decimal(str(return_inv.total_refund_amount or 0))
        if total_refund <= 0:
            return

        payment_method = (return_inv.payment_method or '').lower()
        if payment_method and payment_method != 'cash':
            return

        user = return_inv.returned_by
        if not user:
            return

        from .services import CashDrawerService
        session = CashDrawerService.get_or_create_active_session(user)
        if not session:
            return

        idempotency_key = f"refund_{return_inv.id}"
        CashDrawerService.record_refund(
            session=session,
            user=user,
            amount=total_refund,
            reference_number=return_inv.return_number or f"RI-{return_inv.id:06d}",
            reference_model='ReturnInvoice',
            reference_id=return_inv.id,
            payment_method=payment_method or 'cash',
            idempotency_key=idempotency_key,
        )
    except Exception:
        import traceback
        traceback.print_exc()


def register_signal_handlers():
    from megaone.users.models import Invoice, ReturnInvoice
    post_save.connect(process_sale_cash, sender=Invoice, weak=False)
    post_save.connect(process_return_cash, sender=ReturnInvoice, weak=False)
