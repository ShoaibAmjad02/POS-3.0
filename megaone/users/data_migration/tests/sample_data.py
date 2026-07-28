"""Sample POS data generators for tests — all formats and naming conventions."""

import csv
import io

# ─── DATA SETS ──────────────────────────────────────────────────────────────

# Naming Convention A: Standard English
PRODUCTS_A = [
    {'Product Name': 'Widget', 'SKU': 'SKU-001', 'Barcode': '8901234567890', 'Category': 'Electronics', 'Price': '29.99', 'Stock': '100'},
    {'Product Name': 'Gadget', 'SKU': 'SKU-002', 'Barcode': '8901234567891', 'Category': 'Electronics', 'Price': '49.99', 'Stock': '50'},
    {'Product Name': 'Doohickey', 'SKU': 'SKU-003', 'Barcode': '8901234567892', 'Category': 'Hardware', 'Price': '9.99', 'Stock': '200'},
    {'Product Name': 'Thingamajig', 'SKU': 'SKU-004', 'Barcode': '8901234567893', 'Category': 'Hardware', 'Price': '14.99', 'Stock': '150'},
]

# Naming Convention B: Short/abbreviated
PRODUCTS_B = [
    {'Item': 'Widget', 'Code': 'WGT-001', 'Barcode': '8901234567890', 'Cat': 'Electronics', 'Price': '29.99', 'Qty': '100'},
    {'Item': 'Gadget', 'Code': 'GGT-002', 'Barcode': '8901234567891', 'Cat': 'Electronics', 'Price': '49.99', 'Qty': '50'},
]

# Naming Convention C: Foreign / mixed case / underscores
PRODUCTS_C = [
    {'product_name': 'Widget', 'item_code': 'SKU-001', 'bar_code': '8901234567890', 'product_category': 'Electronics', 'unit_price': '29.99', 'quantity_on_hand': '100'},
    {'product_name': 'Gadget', 'item_code': 'SKU-002', 'bar_code': '8901234567891', 'product_category': 'Electronics', 'unit_price': '49.99', 'quantity_on_hand': '50'},
]

# Duplicate products (for duplicate testing)
PRODUCTS_DUP = [
    {'Product Name': 'Widget', 'SKU': 'SKU-001', 'Barcode': '8901234567890', 'Category': 'Electronics', 'Price': '29.99', 'Stock': '100'},
    {'Product Name': 'Widget', 'SKU': 'SKU-001', 'Barcode': '8901234567890', 'Category': 'Electronics', 'Price': '35.00', 'Stock': '80'},
    {'Product Name': 'Gadget', 'SKU': 'SKU-002', 'Barcode': '8901234567891', 'Category': 'Electronics', 'Price': '49.99', 'Stock': '50'},
]

CATEGORIES_A = [
    {'Category Name': 'Electronics', 'Active': 'Yes'},
    {'Category Name': 'Hardware', 'Active': 'Yes'},
    {'Category Name': 'Software', 'Active': 'Yes'},
]

CUSTOMERS_A = [
    {'Customer Name': 'Alice Johnson', 'Email': 'alice@example.com', 'Phone': '+1-555-0101', 'Address': '123 Main St', 'City': 'New York', 'State': 'NY', 'Zip': '10001', 'Country': 'USA'},
    {'Customer Name': 'Bob Smith', 'Email': 'bob@example.com', 'Phone': '+1-555-0102', 'Address': '456 Oak Ave', 'City': 'Los Angeles', 'State': 'CA', 'Zip': '90001', 'Country': 'USA'},
]

CUSTOMERS_B = [
    {'Name': 'Charlie Brown', 'email address': 'charlie@example.com', 'mobile': '+1-555-0103'},
    {'Name': 'Diana Prince', 'email address': 'diana@example.com', 'mobile': '+1-555-0104'},
]

LOYALTY_A = [
    {'Card Number': 'LC-001', 'Member Email': 'alice@example.com', 'Member Name': 'Alice Johnson', 'Total Points': '1500', 'Status': 'Active'},
    {'Card Number': 'LC-002', 'Member Email': 'bob@example.com', 'Member Name': 'Bob Smith', 'Total Points': '2500', 'Status': 'Active'},
]

SUPPLIERS_A = [
    {'Company Name': 'Acme Corp', 'Contact Person': 'John Doe', 'Email': 'john@acme.com', 'Phone': '+1-555-0201', 'Supplier Code': 'SUP-001'},
    {'Company Name': 'Globex Inc', 'Contact Person': 'Jane Roe', 'Email': 'jane@globex.com', 'Phone': '+1-555-0202', 'Supplier Code': 'SUP-002'},
]

INVENTORY_A = [
    {'Product Name': 'Widget', 'SKU': 'SKU-001', 'Warehouse': 'Main', 'Quantity': '100', 'Unit Price': '29.99'},
    {'Product Name': 'Gadget', 'SKU': 'SKU-002', 'Warehouse': 'Main', 'Quantity': '50', 'Unit Price': '49.99'},
    {'Product Name': 'Doohickey', 'SKU': 'SKU-003', 'Warehouse': 'Secondary', 'Quantity': '200', 'Unit Price': '9.99'},
]

SALES_A = [
    {'Invoice #': 'INV-001', 'Customer Name': 'Alice Johnson', 'Subtotal': '100.00', 'Tax Amount': '10.00', 'Grand Total': '110.00', 'Payment Method': 'Credit Card', 'Created At': '2024-01-15'},
    {'Invoice #': 'INV-002', 'Customer Name': 'Bob Smith', 'Subtotal': '200.00', 'Tax Amount': '20.00', 'Grand Total': '220.00', 'Payment Method': 'Cash', 'Created At': '2024-01-16'},
]

PURCHASES_A = [
    {'Reference #': 'PO-001', 'Supplier Name': 'Acme Corp', 'Product Name': 'Widget', 'Quantity': '50', 'Unit Price': '15.00', 'Purchase Date': '2024-01-10'},
    {'Reference #': 'PO-002', 'Supplier Name': 'Globex Inc', 'Product Name': 'Gadget', 'Quantity': '30', 'Unit Price': '25.00', 'Purchase Date': '2024-01-11'},
]

EMPLOYEES_A = [
    {'Employee ID': 'EMP-001', 'Employee Name': 'Eve Adams', 'Email': 'eve@company.com', 'Phone': '+1-555-0301', 'Role': 'Cashier', 'Department': 'Sales', 'Joining Date': '2023-06-01', 'Salary': '35000'},
    {'Employee ID': 'EMP-002', 'Employee Name': 'Frank Lee', 'Email': 'frank@company.com', 'Phone': '+1-555-0302', 'Role': 'Manager', 'Department': 'Operations', 'Joining Date': '2022-03-15', 'Salary': '55000'},
]

EXPENSES_A = [
    {'Title': 'Office Rent', 'Amount': '2000.00', 'Category': 'Rent', 'Payment Method': 'Bank Transfer', 'Expense Date': '2024-01-01'},
    {'Title': 'Electricity Bill', 'Amount': '350.00', 'Category': 'Utilities', 'Payment Method': 'Bank Transfer', 'Expense Date': '2024-01-05'},
]

EXPENSE_CATEGORIES_A = [
    {'Category Name': 'Rent'},
    {'Category Name': 'Utilities'},
    {'Category Name': 'Supplies'},
]

# ─── ALL-IN-ONE SUPER SET ───────────────────────────────────────────────────
# Combined data for testing multi-module detection

COMBINED_HEADERS = [
    'Product Name', 'SKU', 'Barcode', 'Category', 'Price', 'Stock',
    'Customer Name', 'Email', 'Phone',
    'Card Number', 'Total Points',
    'Company Name', 'Supplier Code',
    'Invoice #', 'Grand Total', 'Created At',
]
COMBINED_ROWS = [
    ['Widget', 'SKU-001', '8901234567890', 'Electronics', '29.99', '100', 'Alice Johnson', 'alice@example.com', '+1-555-0101', 'LC-001', '1500', 'Acme Corp', 'SUP-001', 'INV-001', '110.00', '2024-01-15'],
    ['Gadget', 'SKU-002', '8901234567891', 'Electronics', '49.99', '50', 'Bob Smith', 'bob@example.com', '+1-555-0102', 'LC-002', '2500', 'Globex Inc', 'SUP-002', 'INV-002', '220.00', '2024-01-16'],
]

# ─── Semicolon-delimited data (Excel-style CSV) ──────────────────────────────
SEMICOLON_HEADERS = ['Product Name', 'SKU', 'Price', 'Stock']
SEMICOLON_ROWS = [
    ['Widget', 'SKU-001', '29.99', '100'],
    ['Gadget', 'SKU-002', '49.99', '50'],
]

# ─── GENERATORS ──────────────────────────────────────────────────────────────

def make_csv_bytes(headers, rows, delimiter=','):
    """Generate CSV bytes from headers and rows."""
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode('utf-8-sig')


def make_csv_bytes_plain(headers, rows):
    """Generate CSV without BOM."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    return buf.getvalue().encode('utf-8')


def dicts_to_csv_bytes(dicts, delimiter=','):
    """Convert list of dicts to CSV bytes."""
    if not dicts:
        return b''
    headers = list(dicts[0].keys())
    rows = [[row.get(h, '') for h in headers] for row in dicts]
    return make_csv_bytes(headers, rows, delimiter)


def dicts_to_csv_bytes_plain(dicts):
    if not dicts:
        return b''
    headers = list(dicts[0].keys())
    rows = [[row.get(h, '') for h in headers] for row in dicts]
    return make_csv_bytes_plain(headers, rows)
