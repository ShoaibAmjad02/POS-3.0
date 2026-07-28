"""Tests for field_matcher.py — alias matching, field detection, mapping."""

from megaone.users.data_migration.field_matcher import (
    match_field, detect_fields, suggest_mapping, _normalize,
)


class TestNormalize:
    def test_lowercase(self):
        assert _normalize('Product Name') == 'product name'

    def test_strip(self):
        assert _normalize('  SKU  ') == 'sku'

    def test_underscore_to_space(self):
        assert _normalize('product_name') == 'product name'

    def test_hyphen_to_space(self):
        assert _normalize('product-name') == 'product name'

    def test_slash_to_space(self):
        assert _normalize('credit/debit') == 'credit debit'

    def test_multiple_spaces(self):
        assert _normalize('product   name') == 'product name'


class TestMatchField:
    def test_exact_name(self):
        assert match_field('name') == 'name'

    def test_alias_name(self):
        assert match_field('Product Name') == 'name'
        assert match_field('item name') == 'name'

    def test_sku_variants(self):
        assert match_field('SKU') == 'sku'
        assert match_field('Product Code') == 'sku'
        assert match_field('Item Code') == 'sku'

    def test_barcode_variants(self):
        assert match_field('Barcode') == 'barcode'
        assert match_field('UPC') == 'barcode'
        assert match_field('EAN') == 'barcode'

    def test_price_variants(self):
        assert match_field('Price') == 'price'
        assert match_field('Selling Price') == 'price'
        assert match_field('MRP') == 'price'
        assert match_field('Unit Price') in ('price', 'unit_price')

    def test_wholesale_price(self):
        assert match_field('Wholesale Price') == 'wholesale_price'
        assert match_field('Trade Price') == 'wholesale_price'

    def test_cost_price(self):
        assert match_field('Cost Price') == 'cost_price'
        assert match_field('Purchase Price') == 'cost_price'

    def test_stock_variants(self):
        assert match_field('Stock') == 'stock'
        assert match_field('Quantity') == 'stock'
        assert match_field('Qty') == 'stock'
        assert match_field('On Hand') == 'stock'

    def test_category_variants(self):
        assert match_field('Category') == 'category'
        assert match_field('Department') == 'category'
        assert match_field('Product Group') == 'category'

    def test_email_variants(self):
        assert match_field('Email') == 'email'
        assert match_field('Email Address') == 'email'
        assert match_field('E-mail') == 'email'

    def test_phone_variants(self):
        assert match_field('Phone') == 'phone'
        assert match_field('Mobile') == 'phone'
        assert match_field('Telephone') == 'phone'

    def test_address_variants(self):
        assert match_field('Address') == 'address'
        assert match_field('Street') == 'address'

    def test_card_number(self):
        assert match_field('Card Number') == 'card_number'
        assert match_field('Loyalty Card') == 'card_number'

    def test_invoice_number(self):
        assert match_field('Invoice Number') == 'invoice_number'
        assert match_field('Invoice No') == 'invoice_number'

    def test_unknown_field(self):
        assert match_field('SomeRandomField') is None

    def test_empty_field(self):
        assert match_field('') is None


class TestDetectFields:
    def test_basic_mapping(self):
        columns = ['Product Name', 'SKU', 'Price', 'Stock']
        target = ['name', 'sku', 'price', 'stock']
        mapping = detect_fields(columns, target)
        assert mapping['name'] == 'Product Name'
        assert mapping['sku'] == 'SKU'
        assert mapping['price'] == 'Price'
        assert mapping['stock'] == 'Stock'

    def test_partial_mapping(self):
        columns = ['Product Name', 'Barcode', 'Category']
        target = ['name', 'sku', 'barcode', 'price', 'stock', 'category']
        mapping = detect_fields(columns, target)
        assert 'name' in mapping
        assert 'barcode' in mapping
        assert 'category' in mapping
        assert 'sku' not in mapping
        assert 'price' not in mapping

    def test_short_names(self):
        columns = ['Item', 'Code', 'SP', 'Qty', 'Cat']
        target = ['name', 'sku', 'price', 'stock', 'category']
        mapping = detect_fields(columns, target)
        assert mapping['name'] == 'Item'
        assert mapping['sku'] == 'Code'
        assert mapping['price'] == 'SP'
        assert mapping['stock'] == 'Qty'
        assert mapping['category'] == 'Cat'

    def test_underscore_names(self):
        columns = ['product_name', 'item_code', 'unit_price', 'quantity_on_hand']
        target = ['name', 'sku', 'price', 'stock']
        mapping = detect_fields(columns, target)
        assert mapping['name'] == 'product_name'
        assert mapping['sku'] == 'item_code'
        assert mapping['price'] == 'unit_price'
        assert mapping['stock'] == 'quantity_on_hand'

    def test_first_match_wins(self):
        columns = ['Name', 'Product Name', 'Item Name']
        target = ['name']
        mapping = detect_fields(columns, target)
        assert mapping['name'] == 'Name'

    def test_no_match(self):
        columns = ['A', 'B', 'C']
        target = ['name', 'sku', 'price']
        mapping = detect_fields(columns, target)
        assert mapping == {}


class TestSuggestMapping:
    def test_suggests_all_matches(self):
        columns = ['Product Name', 'SKU', 'Price', 'Random']
        suggestions = suggest_mapping(columns, [])
        assert suggestions['Product Name'] == 'name'
        assert suggestions['SKU'] == 'sku'
        assert suggestions['Price'] == 'price'
        assert 'Random' not in suggestions
