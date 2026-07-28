"""Tests for duplicate_detector.py — duplicate detection per key field."""

from megaone.users.data_migration.duplicate_detector import DuplicateDetector


class TestDetectProducts:
    def test_no_duplicates(self):
        d = DuplicateDetector()
        rows = [
            {'name': 'Widget', 'sku': 'SKU-001', 'barcode': '8901'},
            {'name': 'Gadget', 'sku': 'SKU-002', 'barcode': '8902'},
        ]
        results = d.detect_products(rows)
        assert all(not r['is_duplicate'] for r in results)

    def test_duplicate_sku(self):
        d = DuplicateDetector()
        rows = [
            {'name': 'Widget', 'sku': 'SKU-001'},
            {'name': 'Widget Duplicate', 'sku': 'SKU-001'},
        ]
        results = d.detect_products(rows)
        assert not results[0]['is_duplicate']
        assert results[1]['is_duplicate']
        assert 'SKU' in results[1]['reasons'][0]

    def test_duplicate_barcode(self):
        d = DuplicateDetector()
        rows = [
            {'name': 'Widget', 'barcode': '8901'},
            {'name': 'Gadget', 'barcode': '8901'},
        ]
        results = d.detect_products(rows)
        assert not results[0]['is_duplicate']
        assert results[1]['is_duplicate']

    def test_duplicate_name_same_category(self):
        d = DuplicateDetector()
        rows = [
            {'name': 'Widget', 'category': 'Electronics'},
            {'name': 'Widget', 'category': 'Electronics'},
        ]
        results = d.detect_products(rows)
        assert not results[0]['is_duplicate']
        assert results[1]['is_duplicate']

    def test_same_name_different_category(self):
        d = DuplicateDetector()
        rows = [
            {'name': 'Widget', 'category': 'Electronics'},
            {'name': 'Widget', 'category': 'Hardware'},
        ]
        results = d.detect_products(rows)
        assert not results[0]['is_duplicate']
        assert not results[1]['is_duplicate']

    def test_suggested_action(self):
        d = DuplicateDetector()
        rows = [
            {'name': 'Widget', 'sku': 'SKU-001'},
            {'name': 'Gadget', 'sku': 'SKU-001'},
        ]
        results = d.detect_products(rows)
        assert results[0]['suggested_action'] == 'create_new'
        assert results[1]['suggested_action'] == 'skip'


class TestDetectCustomers:
    def test_no_duplicates(self):
        d = DuplicateDetector()
        rows = [
            {'email': 'alice@test.com'},
            {'email': 'bob@test.com'},
        ]
        results = d.detect_customers(rows)
        assert all(not r['is_duplicate'] for r in results)

    def test_duplicate_email(self):
        d = DuplicateDetector()
        rows = [
            {'email': 'alice@test.com'},
            {'email': 'alice@test.com'},
        ]
        results = d.detect_customers(rows)
        assert not results[0]['is_duplicate']
        assert results[1]['is_duplicate']
        assert 'Email' in results[1]['reasons'][0]

    def test_duplicate_phone(self):
        d = DuplicateDetector()
        rows = [
            {'phone': '555-0101'},
            {'phone': '555-0101'},
        ]
        results = d.detect_customers(rows)
        assert not results[0]['is_duplicate']
        assert results[1]['is_duplicate']


class TestDetectLoyaltyCards:
    def test_no_duplicates(self):
        d = DuplicateDetector()
        rows = [
            {'card_number': 'LC-001'},
            {'card_number': 'LC-002'},
        ]
        results = d.detect_loyalty_cards(rows)
        assert all(not r['is_duplicate'] for r in results)

    def test_duplicate_card(self):
        d = DuplicateDetector()
        rows = [
            {'card_number': 'LC-001'},
            {'card_number': 'LC-001'},
        ]
        results = d.detect_loyalty_cards(rows)
        assert not results[0]['is_duplicate']
        assert results[1]['is_duplicate']


class TestDetectSuppliers:
    def test_no_duplicates(self):
        d = DuplicateDetector()
        rows = [
            {'supplier_code': 'SUP-001', 'company_name': 'Acme Corp'},
            {'supplier_code': 'SUP-002', 'company_name': 'Globex Inc'},
        ]
        results = d.detect_suppliers(rows)
        assert all(not r['is_duplicate'] for r in results)

    def test_duplicate_code(self):
        d = DuplicateDetector()
        rows = [
            {'supplier_code': 'SUP-001', 'company_name': 'Acme Corp'},
            {'supplier_code': 'SUP-001', 'company_name': 'Other Corp'},
        ]
        results = d.detect_suppliers(rows)
        assert not results[0]['is_duplicate']
        assert results[1]['is_duplicate']

    def test_duplicate_name(self):
        d = DuplicateDetector()
        rows = [
            {'supplier_code': 'SUP-001', 'company_name': 'Acme Corp'},
            {'supplier_code': 'SUP-002', 'company_name': 'Acme Corp'},
        ]
        results = d.detect_suppliers(rows)
        assert not results[0]['is_duplicate']
        assert results[1]['is_duplicate']


class TestDetectAll:
    def test_products_dispatch(self):
        d = DuplicateDetector()
        results = d.detect_all('Products', [{'name': 'Widget', 'sku': 'SKU-001'}])
        assert len(results) == 1

    def test_customers_dispatch(self):
        d = DuplicateDetector()
        results = d.detect_all('Customers', [{'email': 'alice@test.com'}])
        assert len(results) == 1

    def test_other_module_no_duplicates(self):
        """Non-keyed modules should report no duplicates."""
        d = DuplicateDetector()
        results = d.detect_all('Expenses', [{'title': 'Rent'}])
        assert not results[0]['is_duplicate']
