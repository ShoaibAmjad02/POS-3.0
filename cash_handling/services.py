from decimal import Decimal
from django.db import transaction as db_transaction
from django.utils import timezone
from django.db.models import Sum
from .models import CashDrawerSession, CashTransaction


class CashDrawerError(Exception):
    pass


class CashDrawerService:

    @staticmethod
    def get_active_session(user):
        return CashDrawerSession.objects.filter(
            user=user,
            status='open',
        ).first()

    @staticmethod
    def get_or_create_active_session(user, opening_balance=Decimal('0')):
        session = CashDrawerSession.objects.filter(
            user=user,
            status='open',
        ).first()
        if session:
            return session
        return CashDrawerService.open_session(
            user=user,
            opening_balance=Decimal(str(opening_balance)),
        )

    @staticmethod
    @db_transaction.atomic
    def open_session(user, opening_balance=Decimal('0'), notes=''):
        active = CashDrawerSession.objects.filter(
            user=user,
            status='open',
        ).first()
        if active:
            raise CashDrawerError(f"User already has an open session (#{active.id})")

        session = CashDrawerSession.objects.create(
            user=user,
            opening_balance=opening_balance,
            status='open',
            notes=notes,
        )

        CashTransaction.objects.create(
            session=session,
            user=user,
            transaction_type='opening_balance',
            amount=opening_balance,
            balance_before=Decimal('0'),
            balance_after=opening_balance,
            notes=f"Opening balance: {opening_balance}",
        )

        return session

    @staticmethod
    @db_transaction.atomic
    def close_session(session, user, closing_balance=None, notes=''):
        if session.status != 'open':
            raise CashDrawerError("Session is not open")

        current_balance = CashDrawerService.get_session_balance(session)
        expected_closing = current_balance

        if closing_balance is None:
            closing_balance = current_balance

        session.closing_balance = Decimal(str(closing_balance))
        session.expected_closing = expected_closing
        session.closed_at = timezone.now()
        session.closed_by = user
        session.status = 'closed'
        session.notes = notes or session.notes
        session.save()

        CashTransaction.objects.create(
            session=session,
            user=user,
            transaction_type='closing_balance',
            amount=session.closing_balance,
            balance_before=current_balance,
            balance_after=session.closing_balance,
            notes=f"Closing balance: {closing_balance}, Expected: {expected_closing}",
        )

        return session

    @staticmethod
    @db_transaction.atomic
    def record_cash_in(session, user, amount, reason='', reference=None):
        if session.status != 'open':
            raise CashDrawerError("Session is not open")
        amount = Decimal(str(amount))
        if amount <= 0:
            raise CashDrawerError("Amount must be positive")

        balance_before = CashDrawerService.get_session_balance(session)
        balance_after = balance_before + amount

        txn = CashTransaction.objects.create(
            session=session,
            user=user,
            transaction_type='cash_in',
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            notes=reason,
            reference_number=reference,
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def record_cash_out(session, user, amount, reason='', reference=None):
        if session.status != 'open':
            raise CashDrawerError("Session is not open")
        amount = Decimal(str(amount))
        if amount <= 0:
            raise CashDrawerError("Amount must be positive")

        balance_before = CashDrawerService.get_session_balance(session)
        if balance_before < amount:
            raise CashDrawerError("Insufficient cash in drawer")
        balance_after = balance_before - amount

        txn = CashTransaction.objects.create(
            session=session,
            user=user,
            transaction_type='cash_out',
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            notes=reason,
            reference_number=reference,
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def record_drop(session, user, amount, reason='', reference=None):
        if session.status != 'open':
            raise CashDrawerError("Session is not open")
        amount = Decimal(str(amount))
        if amount <= 0:
            raise CashDrawerError("Amount must be positive")

        balance_before = CashDrawerService.get_session_balance(session)
        if balance_before < amount:
            raise CashDrawerError("Insufficient cash in drawer")
        balance_after = balance_before - amount

        txn = CashTransaction.objects.create(
            session=session,
            user=user,
            transaction_type='drop',
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            notes=reason,
            reference_number=reference,
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def record_sale(session, user, amount, reference_number='', reference_model='', reference_id=None, payment_method='cash', idempotency_key=None):
        if session.status != 'open':
            raise CashDrawerError("Session is not open")
        amount = Decimal(str(amount))
        if amount <= 0:
            return None

        if idempotency_key:
            existing = CashTransaction.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing

        balance_before = CashDrawerService.get_session_balance(session)
        balance_after = balance_before + amount

        txn = CashTransaction.objects.create(
            session=session,
            user=user,
            transaction_type='sale',
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_number=reference_number,
            reference_model=reference_model,
            reference_id=reference_id,
            payment_method=payment_method,
            idempotency_key=idempotency_key,
            notes=f"Sale {reference_number} - {payment_method}",
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def record_refund(session, user, amount, reference_number='', reference_model='', reference_id=None, payment_method='cash', idempotency_key=None):
        if session.status != 'open':
            raise CashDrawerError("Session is not open")
        amount = Decimal(str(amount))
        if amount <= 0:
            return None

        if idempotency_key:
            existing = CashTransaction.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing

        balance_before = CashDrawerService.get_session_balance(session)
        balance_after = balance_before - amount

        txn = CashTransaction.objects.create(
            session=session,
            user=user,
            transaction_type='refund',
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_number=reference_number,
            reference_model=reference_model,
            reference_id=reference_id,
            payment_method=payment_method,
            idempotency_key=idempotency_key,
            notes=f"Refund {reference_number}",
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def record_adjustment(session, user, amount, reason=''):
        if session.status != 'open':
            raise CashDrawerError("Session is not open")
        amount = Decimal(str(amount))

        balance_before = CashDrawerService.get_session_balance(session)
        balance_after = balance_before + amount

        txn = CashTransaction.objects.create(
            session=session,
            user=user,
            transaction_type='adjustment',
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            notes=reason,
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def record_void_sale(session, user, amount, reference_number='', reason='', idempotency_key=None):
        if session.status != 'open':
            raise CashDrawerError("Session is not open")
        amount = Decimal(str(amount))
        if amount <= 0:
            return None

        if idempotency_key:
            existing = CashTransaction.objects.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing

        balance_before = CashDrawerService.get_session_balance(session)
        balance_after = balance_before - amount

        txn = CashTransaction.objects.create(
            session=session,
            user=user,
            transaction_type='void_sale',
            amount=amount,
            balance_before=balance_before,
            balance_after=balance_after,
            reference_number=reference_number,
            notes=reason or f"Void sale {reference_number}",
            idempotency_key=idempotency_key,
        )
        return txn

    @staticmethod
    @db_transaction.atomic
    def record_no_sale(session, user, reason=''):
        if session.status != 'open':
            raise CashDrawerError("Session is not open")

        balance_before = CashDrawerService.get_session_balance(session)
        txn = CashTransaction.objects.create(
            session=session,
            user=user,
            transaction_type='no_sale',
            amount=Decimal('0'),
            balance_before=balance_before,
            balance_after=balance_before,
            notes=reason or 'No sale drawer open',
        )
        return txn

    @staticmethod
    def get_session_balance(session):
        last_txn = CashTransaction.objects.filter(
            session=session,
        ).order_by('-id').first()
        if last_txn:
            return last_txn.balance_after
        return Decimal('0')

    @staticmethod
    def get_session_cash_sales(session):
        result = CashTransaction.objects.filter(
            session=session,
            transaction_type='sale',
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        return result

    @staticmethod
    def get_session_cash_refunds(session):
        result = CashTransaction.objects.filter(
            session=session,
            transaction_type='refund',
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        return result

    @staticmethod
    def get_session_drops(session):
        result = CashTransaction.objects.filter(
            session=session,
            transaction_type='drop',
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        return result

    @staticmethod
    def get_session_cash_in(session):
        result = CashTransaction.objects.filter(
            session=session,
            transaction_type='cash_in',
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        return result

    @staticmethod
    def get_session_cash_out(session):
        result = CashTransaction.objects.filter(
            session=session,
            transaction_type='cash_out',
        ).aggregate(
            total=Sum('amount')
        )['total'] or Decimal('0')
        return result

    @staticmethod
    def get_user_open_sessions_count():
        return CashDrawerSession.objects.filter(status='open').count()
