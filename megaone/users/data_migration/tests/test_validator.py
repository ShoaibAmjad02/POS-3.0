"""Tests for validator.py — per-module data validation."""

import pytest
from megaone.users.data_migration.validator import DataValidator


class TestValidateProducts:
    def test_valid_product(self):
        v = DataValidator()
        result = v.validate_rows('Products', [{'name': 'Widget', 'price': '29.99'}], {})
        assert result['valid'] == 1
        assert len(result['errors']) == 0

    def test_missing_name(self):
        v = DataValidator()
        result = v.validate_rows('Products', [{'name': '', 'price': '29.99'}], {})
        assert len(result['errors']) > 0
        assert 'Missing product name' in result['errors'][0]['message']

    def test_negative_price(self):
        v = DataValidator()
        result = v.validate_rows('Products', [{'name': 'Widget', 'price': '-10'}], {})
        assert len(result['errors']) > 0
        assert 'Negative price' in result['errors'][0]['message']

    def test_invalid_price(self):
        v = DataValidator()
        result = v.validate_rows('Products', [{'name': 'Widget', 'price': 'abc'}], {})
        assert len(result['errors']) > 0
        assert 'Invalid price' in result['errors'][0]['message']


class TestValidateCustomers:
    def test_valid_customer(self):
        v = DataValidator()
        result = v.validate_rows('Customers', [{'name': 'Alice', 'email': 'alice@test.com'}], {})
        assert result['valid'] == 1
        assert len(result['errors']) == 0

    def test_missing_name(self):
        v = DataValidator()
        result = v.validate_rows('Customers', [{'name': '', 'email': ''}], {})
        assert len(result['errors']) > 0
        assert 'Missing customer name' in result['errors'][0]['message']

    def test_invalid_email(self):
        v = DataValidator()
        result = v.validate_rows('Customers', [{'name': 'Alice', 'email': 'not-an-email'}], {})
        assert len(result['errors']) > 0
        assert 'Invalid email' in result['errors'][0]['message']

    def test_company_name_as_name(self):
        v = DataValidator()
        result = v.validate_rows('Customers', [{'company_name': 'Acme Corp', 'email': 'info@acme.com'}], {})
        assert result['valid'] == 1


class TestValidateSales:
    def test_valid_sale(self):
        v = DataValidator()
        result = v.validate_rows('Sales', [{'invoice_number': 'INV-001', 'grand_total': '100.00'}], {})
        assert result['valid'] == 1

    def test_missing_invoice(self):
        v = DataValidator()
        result = v.validate_rows('Sales', [{'grand_total': '100.00'}], {})
        assert len(result['errors']) > 0
        assert 'Missing invoice number' in result['errors'][0]['message']

    def test_negative_total(self):
        v = DataValidator()
        result = v.validate_rows('Sales', [{'invoice_number': 'INV-001', 'total': '-50'}], {})
        assert len(result['errors']) > 0
        assert 'Negative total' in result['errors'][0]['message']


class TestValidateGeneric:
    def test_empty_row(self):
        v = DataValidator()
        result = v.validate_rows('Other', [{'col1': '', 'col2': ''}], {})
        assert len(result['errors']) > 0
        assert 'Empty row' in result['errors'][0]['message']

    def test_multiple_rows(self):
        v = DataValidator()
        rows = [
            {'name': 'Widget', 'price': '29.99'},
            {'name': '', 'price': '10.00'},
            {'name': 'Gadget', 'price': '-5'},
        ]
        result = v.validate_rows('Products', rows, {})
        assert result['total_rows'] == 3
        assert result['valid'] == 1
        assert len(result['errors']) == 2


class TestGenerateReport:
    def test_report_structure(self):
        v = DataValidator()
        v.validate_rows('Products', [{'name': 'Widget', 'price': '10'}], {})
        v.validate_rows('Customers', [{'name': 'Alice'}], {})
        report = v.generate_report()
        assert report['total_valid'] == 2
        assert report['total_errors'] == 0
        assert 'Products' in report['modules']
        assert 'Customers' in report['modules']
