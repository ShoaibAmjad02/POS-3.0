from decimal import Decimal
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model

from cash_handling.models import CashDrawerSession, CashTransaction
from cash_handling.services import CashDrawerService, CashDrawerError

User = get_user_model()


class TestCashDrawerService(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='cashier@test.com',
            password='testpass123',
            name='Test Cashier',
            is_operator=True,
        )

    def test_open_session(self):
        session = CashDrawerService.open_session(
            user=self.user,
            opening_balance=Decimal('100.00'),
        )
        self.assertEqual(session.status, 'open')
        self.assertEqual(session.opening_balance, Decimal('100.00'))
        self.assertEqual(session.user, self.user)
        session_balance = CashDrawerService.get_session_balance(session)
        self.assertEqual(session_balance, Decimal('100.00'))

    def test_open_session_twice_fails(self):
        CashDrawerService.open_session(user=self.user, opening_balance=Decimal('0'))
        with self.assertRaises(CashDrawerError):
            CashDrawerService.open_session(user=self.user, opening_balance=Decimal('0'))

    def test_close_session(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('0'))
        closed = CashDrawerService.close_session(
            session=session,
            user=self.user,
            closing_balance=Decimal('150.00'),
        )
        self.assertEqual(closed.status, 'closed')
        self.assertIsNotNone(closed.closed_at)
        self.assertEqual(closed.closing_balance, Decimal('150.00'))
        self.assertEqual(closed.closed_by, self.user)

    def test_close_closed_session_fails(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('0'))
        CashDrawerService.close_session(session=session, user=self.user)
        with self.assertRaises(CashDrawerError):
            CashDrawerService.close_session(session=session, user=self.user)

    def test_record_cash_in(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('100.00'))
        txn = CashDrawerService.record_cash_in(
            session=session,
            user=self.user,
            amount=Decimal('50.00'),
            reason='Additional cash',
        )
        self.assertEqual(txn.transaction_type, 'cash_in')
        self.assertEqual(txn.amount, Decimal('50.00'))
        self.assertEqual(txn.balance_after, Decimal('150.00'))

    def test_record_cash_out(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('200.00'))
        txn = CashDrawerService.record_cash_out(
            session=session,
            user=self.user,
            amount=Decimal('50.00'),
            reason='Petty cash',
        )
        self.assertEqual(txn.transaction_type, 'cash_out')
        self.assertEqual(txn.amount, Decimal('50.00'))
        self.assertEqual(txn.balance_after, Decimal('150.00'))

    def test_cash_out_insufficient_funds(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('10.00'))
        with self.assertRaises(CashDrawerError):
            CashDrawerService.record_cash_out(
                session=session,
                user=self.user,
                amount=Decimal('50.00'),
                reason='Not enough',
            )

    def test_record_drop(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('500.00'))
        txn = CashDrawerService.record_drop(
            session=session,
            user=self.user,
            amount=Decimal('200.00'),
            reason='Bank deposit',
        )
        self.assertEqual(txn.transaction_type, 'drop')
        self.assertEqual(txn.amount, Decimal('200.00'))
        self.assertEqual(txn.balance_after, Decimal('300.00'))

    def test_record_sale(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('100.00'))
        txn = CashDrawerService.record_sale(
            session=session,
            user=self.user,
            amount=Decimal('150.00'),
            reference_number='INV-001',
            reference_model='Invoice',
            reference_id=1,
            idempotency_key='sale_1',
        )
        self.assertEqual(txn.transaction_type, 'sale')
        self.assertEqual(txn.amount, Decimal('150.00'))
        self.assertEqual(txn.balance_after, Decimal('250.00'))
        self.assertEqual(txn.reference_number, 'INV-001')

    def test_record_sale_idempotency(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('100.00'))
        txn1 = CashDrawerService.record_sale(
            session=session,
            user=self.user,
            amount=Decimal('150.00'),
            idempotency_key='sale_dup',
        )
        balance_after_first = txn1.balance_after
        # Second call with same key should return existing transaction
        txn2 = CashDrawerService.record_sale(
            session=session,
            user=self.user,
            amount=Decimal('99999.00'),
            idempotency_key='sale_dup',
        )
        self.assertEqual(txn1.id, txn2.id)
        self.assertEqual(txn2.amount, Decimal('150.00'))
        self.assertEqual(txn2.balance_after, balance_after_first)

    def test_record_refund(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('500.00'))
        txn = CashDrawerService.record_refund(
            session=session,
            user=self.user,
            amount=Decimal('50.00'),
            reference_number='RI-001',
        )
        self.assertEqual(txn.transaction_type, 'refund')
        self.assertEqual(txn.amount, Decimal('50.00'))
        self.assertEqual(txn.balance_after, Decimal('450.00'))

    def test_record_adjustment(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('100.00'))
        txn = CashDrawerService.record_adjustment(
            session=session,
            user=self.user,
            amount=Decimal('-20.00'),
            reason='Correction',
        )
        self.assertEqual(txn.transaction_type, 'adjustment')
        self.assertEqual(txn.balance_after, Decimal('80.00'))

    def test_get_session_metrics(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('0'))
        CashDrawerService.record_sale(session=session, user=self.user, amount=Decimal('200'))
        CashDrawerService.record_sale(session=session, user=self.user, amount=Decimal('100'))
        CashDrawerService.record_refund(session=session, user=self.user, amount=Decimal('50'))
        CashDrawerService.record_drop(session=session, user=self.user, amount=Decimal('30'))

        self.assertEqual(CashDrawerService.get_session_cash_sales(session), Decimal('300'))
        self.assertEqual(CashDrawerService.get_session_cash_refunds(session), Decimal('50'))
        self.assertEqual(CashDrawerService.get_session_drops(session), Decimal('30'))
        self.assertEqual(CashDrawerService.get_session_balance(session), Decimal('220'))

    def test_get_or_create_active_session_returns_existing(self):
        session1 = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('0'))
        session2 = CashDrawerService.get_or_create_active_session(self.user)
        self.assertEqual(session1.id, session2.id)

    def test_get_or_create_active_session_creates_new(self):
        session = CashDrawerService.get_or_create_active_session(
            self.user,
            opening_balance=Decimal('500'),
        )
        self.assertIsNotNone(session)
        self.assertEqual(session.status, 'open')
        self.assertEqual(session.opening_balance, Decimal('500'))

    def test_session_operations_require_open_session(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('0'))
        CashDrawerService.close_session(session=session, user=self.user)
        with self.assertRaises(CashDrawerError):
            CashDrawerService.record_sale(session=session, user=self.user, amount=Decimal('10'))
        with self.assertRaises(CashDrawerError):
            CashDrawerService.record_refund(session=session, user=self.user, amount=Decimal('10'))
        with self.assertRaises(CashDrawerError):
            CashDrawerService.record_cash_in(session=session, user=self.user, amount=Decimal('10'))
        with self.assertRaises(CashDrawerError):
            CashDrawerService.record_cash_out(session=session, user=self.user, amount=Decimal('10'))
        with self.assertRaises(CashDrawerError):
            CashDrawerService.record_drop(session=session, user=self.user, amount=Decimal('10'))

    def test_invalid_amounts(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('100'))
        with self.assertRaises(CashDrawerError):
            CashDrawerService.record_cash_in(session=session, user=self.user, amount=Decimal('0'))
        with self.assertRaises(CashDrawerError):
            CashDrawerService.record_cash_in(session=session, user=self.user, amount=Decimal('-10'))
        with self.assertRaises(CashDrawerError):
            CashDrawerService.record_cash_out(session=session, user=self.user, amount=Decimal('0'))
        with self.assertRaises(CashDrawerError):
            CashDrawerService.record_drop(session=session, user=self.user, amount=Decimal('-5'))

    def test_zero_amount_sale_returns_none(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('0'))
        result = CashDrawerService.record_sale(session=session, user=self.user, amount=Decimal('0'))
        self.assertIsNone(result)

    def test_zero_amount_refund_returns_none(self):
        session = CashDrawerService.open_session(user=self.user, opening_balance=Decimal('0'))
        result = CashDrawerService.record_refund(session=session, user=self.user, amount=Decimal('0'))
        self.assertIsNone(result)
