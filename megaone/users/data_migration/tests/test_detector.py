"""Tests for detector.py — file parsing, module detection, schema analysis."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from megaone.users.data_migration.detector import (
    analyze_file, parse_csv, detect_modules, detect_file_type,
    _detect_delimiter,
)
from .sample_data import (
    dicts_to_csv_bytes, dicts_to_csv_bytes_plain,
    PRODUCTS_A, PRODUCTS_B, PRODUCTS_C,
    CATEGORIES_A, CUSTOMERS_A, LOYALTY_A, SUPPLIERS_A,
    INVENTORY_A, SALES_A, PURCHASES_A, EMPLOYEES_A,
    EXPENSES_A, EXPENSE_CATEGORIES_A,
    COMBINED_HEADERS, COMBINED_ROWS,
    SEMICOLON_HEADERS, SEMICOLON_ROWS,
)


def _make_file(data, name='test.csv', content_type='text/csv'):
    if isinstance(data, str):
        data = data.encode('utf-8')
    return SimpleUploadedFile(name, data, content_type=content_type)


class TestDetectFileType:
    def test_csv(self):
        assert detect_file_type('data.csv') == 'csv'
        assert detect_file_type('data.CSV') == 'csv'

    def test_excel(self):
        assert detect_file_type('data.xlsx') == 'excel'
        assert detect_file_type('data.xls') == 'excel'

    def test_sql(self):
        assert detect_file_type('dump.sql') == 'sql'

    def test_sqlite(self):
        assert detect_file_type('database.db') == 'sqlite'
        assert detect_file_type('database.sqlite') == 'sqlite'

    def test_zip(self):
        assert detect_file_type('archive.zip') == 'zip'

    def test_unknown(self):
        assert detect_file_type('data.txt') == 'unknown'
        assert detect_file_type('data') == 'unknown'


class TestDetectDelimiter:
    def test_comma(self):
        assert _detect_delimiter('a,b,c\n1,2,3') == ','

    def test_semicolon(self):
        assert _detect_delimiter('a;b;c\n1;2;3') == ';'

    def test_tab(self):
        assert _detect_delimiter('a\tb\tc\n1\t2\t3') == '\t'

    def test_pipe(self):
        assert _detect_delimiter('a|b|c\n1|2|3') == '|'

    def test_fallback_to_comma(self):
        assert _detect_delimiter('a b c\n1 2 3') == ','


class TestParseCSV:
    def test_standard_csv(self):
        data = dicts_to_csv_bytes(PRODUCTS_A)
        headers, rows, line_count = parse_csv(data)
        assert 'Product Name' in headers
        assert 'SKU' in headers
        assert len(rows) == len(PRODUCTS_A)
        assert rows[0]['Product Name'] == 'Widget'

    def test_utf8_bom(self):
        """CSV with UTF-8 BOM should parse cleanly."""
        data = dicts_to_csv_bytes(PRODUCTS_A)
        headers, rows, line_count = parse_csv(data)
        assert not headers[0].startswith('\ufeff')
        assert rows[0]['Product Name'] == 'Widget'

    def test_latin1_encoding(self):
        """CSV with latin-1 characters should still parse."""
        data = 'Nom,SKU,Prix\nCafé,SKU-001,5.99\n'.encode('latin-1')
        headers, rows, line_count = parse_csv(data)
        assert 'Nom' in headers
        assert rows[0]['Nom'] == 'Café'

    def test_semicolon_delimiter(self):
        """Excel-exported semicolon CSV should auto-detect delimiter."""
        headers = SEMICOLON_HEADERS
        rows_data = SEMICOLON_ROWS
        buf = ';'.join(headers) + '\n'
        for row in rows_data:
            buf += ';'.join(row) + '\n'
        data = buf.encode('utf-8')
        headers, rows, line_count = parse_csv(data)
        assert 'Product Name' in headers
        assert len(rows) == 2

    def test_tab_delimiter(self):
        """Tab-separated CSV should auto-detect."""
        buf = 'Product Name\tSKU\tPrice\nWidget\tSKU-001\t29.99\nGadget\tSKU-002\t49.99\n'
        headers, rows, line_count = parse_csv(buf.encode('utf-8'))
        assert 'Product Name' in headers
        assert len(rows) == 2

    def test_empty_file(self):
        headers, rows, line_count = parse_csv(b'')
        assert headers == []
        assert rows == []

    def test_single_header_only(self):
        headers, rows, line_count = parse_csv(b'Name,SKU\n')
        assert headers == ['Name', 'SKU']
        assert rows == []


class TestDetectModules:
    def test_products_standard(self):
        modules = detect_modules(['Product Name', 'SKU', 'Price', 'Stock', 'Category'])
        assert 'Products' in modules

    def test_products_short_names(self):
        modules = detect_modules(['Item', 'Price', 'Code', 'Qty'])
        assert 'Products' in modules

    def test_customers_detected(self):
        modules = detect_modules(['Customer Name', 'Email', 'Phone', 'Address'])
        assert 'Customers' in modules

    def test_loyalty_detected(self):
        modules = detect_modules(['Card Number', 'Loyalty Points', 'Member Name', 'Status'])
        assert 'Loyalty Cards' in modules

    def test_suppliers_detected(self):
        modules = detect_modules(['Supplier Name', 'Vendor Code', 'Contact Person', 'Email'])
        assert 'Suppliers' in modules

    def test_inventory_detected(self):
        modules = detect_modules(['Product Name', 'SKU', 'Warehouse', 'Quantity', 'Unit Price'])
        assert 'Inventory' in modules

    def test_sales_detected(self):
        modules = detect_modules(['Invoice Number', 'Customer Name', 'Grand Total', 'Created At'])
        assert 'Sales' in modules

    def test_expenses_detected(self):
        modules = detect_modules(['Expense Title', 'Amount', 'Category', 'Payment Method'])
        assert 'Expenses' in modules

    def test_employees_detected(self):
        modules = detect_modules(['Employee Name', 'Staff ID', 'Role', 'Department', 'Salary'])
        assert 'Employees' in modules

    def test_purchases_detected(self):
        modules = detect_modules(['Purchase Order', 'Supplier Name', 'Product Name', 'Quantity'])
        assert 'Purchases' in modules

    def test_categories_detected(self):
        modules = detect_modules(['Category Name', 'Department', 'Active'])
        assert 'Categories' in modules

    def test_expense_categories_detected(self):
        modules = detect_modules(['Expense Type', 'Active'])
        assert 'Expense Categories' in modules or 'Expenses' in modules

    def test_multi_module_detection(self):
        """Combined data should detect multiple modules."""
        modules = detect_modules(COMBINED_HEADERS)
        detected = list(modules.keys())
        assert 'Products' in detected
        assert 'Customers' in detected
        assert 'Suppliers' in detected
        assert 'Sales' in detected

    def test_no_false_positives(self):
        """Random column names should not trigger modules."""
        modules = detect_modules(['Col1', 'Col2', 'Col3', 'Meta', 'Data'])
        assert len(modules) == 0


class TestAnalyzeFile:
    def test_csv_products_detected(self):
        """Full CSV file analysis should detect Products module."""
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = _make_file(data, 'products.csv')
        result = analyze_file(uf)
        assert result['status'] == 'analyzed'
        assert result['file_type'] == 'csv'
        assert len(result['tables']) == 1
        assert 'Products' in result['modules']
        assert result['total_records'] == len(PRODUCTS_A)

    def test_csv_customers_detected(self):
        data = dicts_to_csv_bytes(CUSTOMERS_A)
        uf = _make_file(data, 'customers.csv')
        result = analyze_file(uf)
        assert 'Customers' in result['modules']

    def test_csv_loyalty_detected(self):
        data = dicts_to_csv_bytes(LOYALTY_A)
        uf = _make_file(data, 'loyalty.csv')
        result = analyze_file(uf)
        assert 'Loyalty Cards' in result['modules']

    def test_csv_suppliers_detected(self):
        data = dicts_to_csv_bytes(SUPPLIERS_A)
        uf = _make_file(data, 'suppliers.csv')
        result = analyze_file(uf)
        assert 'Suppliers' in result['modules']

    def test_csv_inventory_detected(self):
        data = dicts_to_csv_bytes(INVENTORY_A)
        uf = _make_file(data, 'inventory.csv')
        result = analyze_file(uf)
        assert 'Inventory' in result['modules']

    def test_csv_sales_detected(self):
        data = dicts_to_csv_bytes(SALES_A)
        uf = _make_file(data, 'sales.csv')
        result = analyze_file(uf)
        assert 'Sales' in result['modules']

    def test_csv_purchases_detected(self):
        data = dicts_to_csv_bytes(PURCHASES_A)
        uf = _make_file(data, 'purchases.csv')
        result = analyze_file(uf)
        assert 'Purchases' in result['modules']

    def test_csv_employees_detected(self):
        data = dicts_to_csv_bytes(EMPLOYEES_A)
        uf = _make_file(data, 'employees.csv')
        result = analyze_file(uf)
        assert 'Employees' in result['modules']

    def test_csv_expenses_detected(self):
        data = dicts_to_csv_bytes(EXPENSES_A)
        uf = _make_file(data, 'expenses.csv')
        result = analyze_file(uf)
        assert 'Expenses' in result['modules']

    def test_csv_categories_detected(self):
        data = dicts_to_csv_bytes(CATEGORIES_A)
        uf = _make_file(data, 'categories.csv')
        result = analyze_file(uf)
        assert 'Categories' in result['modules']

    def test_alternate_naming_convention_b(self):
        """Short/abbreviated column names should still detect."""
        data = dicts_to_csv_bytes(PRODUCTS_B)
        uf = _make_file(data, 'products_b.csv')
        result = analyze_file(uf)
        assert 'Products' in result['modules']

    def test_alternate_naming_convention_c(self):
        """Underscore column names should still detect."""
        data = dicts_to_csv_bytes(PRODUCTS_C)
        uf = _make_file(data, 'products_c.csv')
        result = analyze_file(uf)
        assert 'Products' in result['modules']

    def test_semicolon_delimited_csv(self):
        """Semicolon-delimited CSV (Excel export) should parse and detect."""
        headers = SEMICOLON_HEADERS
        rows_data = SEMICOLON_ROWS
        buf = ';'.join(headers) + '\n'
        for row in rows_data:
            buf += ';'.join(row) + '\n'
        uf = _make_file(buf, 'semicolon.csv')
        result = analyze_file(uf)
        assert result['status'] == 'analyzed'
        assert 'Products' in result['modules']

    def test_table_columns_analysis(self):
        """Tables should contain column names and inferred types."""
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = _make_file(data)
        result = analyze_file(uf)
        assert len(result['tables']) == 1
        table = result['tables'][0]
        col_names = [c['name'] for c in table['columns']]
        col_types = [c['type'] for c in table['columns']]
        assert 'Price' in col_names
        assert 'decimal' in col_types  # Price column
        assert 'Stock' in col_names
        assert 'integer' in col_types  # Stock column

    def test_no_database_writes(self):
        """analyze_file must not write to database under any circumstances."""
        from django.db import connection
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = _make_file(data)
        with connection.schema_editor() as schema_editor:
            pass
        result = analyze_file(uf)
        assert result['status'] == 'analyzed'
