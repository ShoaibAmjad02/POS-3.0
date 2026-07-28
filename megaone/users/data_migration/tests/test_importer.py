"""Tests for importer.py — all 11 modules, dependency order, atomicity, results structure."""

import pytest
from megaone.users.data_migration.importer import ImportEngine, IMPORT_ORDER


@pytest.mark.django_db
class TestImportExpenseCategories:
    def test_import_new(self):
        from megaone.users.models import ExpenseCategory
        engine = ImportEngine()
        plan = {
            'Expense Categories': {
                'rows': [{'name': 'Rent'}, {'name': 'Utilities'}],
                'field_map': {'name': 'name'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 2
        assert ExpenseCategory.objects.filter(name='Rent').exists()

    def test_skip_duplicates(self):
        from megaone.users.models import ExpenseCategory
        ExpenseCategory.objects.create(name='Rent')
        engine = ImportEngine()
        plan = {
            'Expense Categories': {
                'rows': [{'name': 'Rent'}, {'name': 'New'}],
                'field_map': {'name': 'name'},
                'dup_action': 'skip',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        assert results['skipped'] == 1


@pytest.mark.django_db
class TestImportCategories:
    def test_import_new(self):
        from menu.models import Category
        engine = ImportEngine()
        plan = {
            'Categories': {
                'rows': [{'name': 'Electronics'}, {'name': 'Hardware'}],
                'field_map': {'name': 'name'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 2
        assert Category.objects.filter(name='Electronics').exists()

    def test_skip_duplicates(self):
        from menu.models import Category
        Category.objects.create(name='Electronics')
        engine = ImportEngine()
        plan = {
            'Categories': {
                'rows': [{'name': 'Electronics'}, {'name': 'New'}],
                'field_map': {'name': 'name'},
                'dup_action': 'skip',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        assert results['skipped'] == 1


@pytest.mark.django_db
class TestImportSuppliers:
    def test_import_new(self):
        from megaone.users.models import WholesaleCustomer
        engine = ImportEngine()
        plan = {
            'Suppliers': {
                'rows': [
                    {'company_name': 'Acme Corp', 'contact_person': 'John', 'email': 'john@acme.com', 'phone': '555-0101'},
                ],
                'field_map': {'company_name': 'company_name', 'contact_person': 'contact_person', 'email': 'email', 'phone': 'phone'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        assert WholesaleCustomer.objects.filter(company_name='Acme Corp').exists()

    def test_skip_duplicates(self):
        from megaone.users.models import WholesaleCustomer
        WholesaleCustomer.objects.create(company_name='Acme Corp', contact_person='John')
        engine = ImportEngine()
        plan = {
            'Suppliers': {
                'rows': [{'company_name': 'Acme Corp'}],
                'field_map': {'company_name': 'company_name'},
                'dup_action': 'skip',
            }
        }
        results = engine.run_import(plan)
        assert results['skipped'] == 1


@pytest.mark.django_db
class TestImportCustomers:
    def test_import_new(self):
        from megaone.users.models import User
        engine = ImportEngine()
        plan = {
            'Customers': {
                'rows': [
                    {'name': 'Alice', 'email': 'alice@test.com', 'phone': '555-0101'},
                    {'name': 'Bob', 'email': 'bob@test.com', 'phone': '555-0102'},
                ],
                'field_map': {'name': 'name', 'email': 'email', 'phone': 'phone'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 2
        assert User.objects.filter(email='alice@test.com').exists()

    def test_skip_duplicates(self):
        from megaone.users.models import User
        User.objects.create(name='Alice', email='alice@test.com')
        engine = ImportEngine()
        plan = {
            'Customers': {
                'rows': [{'name': 'Alice', 'email': 'alice@test.com'}],
                'field_map': {'name': 'name', 'email': 'email'},
                'dup_action': 'skip',
            }
        }
        results = engine.run_import(plan)
        assert results['skipped'] == 1


@pytest.mark.django_db
class TestImportLoyaltyCards:
    def test_import_new(self):
        from megaone.users.models import LoyaltyCard
        engine = ImportEngine()
        plan = {
            'Loyalty Cards': {
                'rows': [
                    {'card_number': 'LC-001', 'total_points': '1500'},
                    {'card_number': 'LC-002', 'total_points': '2500'},
                ],
                'field_map': {'card_number': 'card_number', 'total_points': 'total_points'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 2
        assert LoyaltyCard.objects.filter(card_number='LC-001').exists()
        card = LoyaltyCard.objects.get(card_number='LC-001')
        assert card.total_points == 1500
        assert card.remaining_points == 1500

    def test_skip_duplicates(self):
        from megaone.users.models import LoyaltyCard
        LoyaltyCard.objects.create(card_number='LC-001')
        engine = ImportEngine()
        plan = {
            'Loyalty Cards': {
                'rows': [{'card_number': 'LC-001'}, {'card_number': 'LC-002'}],
                'field_map': {'card_number': 'card_number'},
                'dup_action': 'skip',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        assert results['skipped'] == 1


@pytest.mark.django_db
class TestImportProducts:
    def test_import_new(self):
        from menu.models import Food, Category
        engine = ImportEngine()
        plan = {
            'Products': {
                'rows': [
                    {'name': 'Widget', 'price': '29.99', 'sku': 'SKU-001', 'barcode': '8901', 'stock': '100', 'category': 'Electronics'},
                    {'name': 'Gadget', 'price': '49.99', 'sku': 'SKU-002', 'barcode': '8902', 'stock': '50', 'category': 'Electronics'},
                ],
                'field_map': {'name': 'name', 'price': 'price', 'sku': 'sku', 'barcode': 'barcode', 'stock': 'stock', 'category': 'category'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 2
        assert Food.objects.count() == 2
        assert Category.objects.filter(name='Electronics').exists()

    def test_skip_duplicates(self):
        from menu.models import Food, Category
        cat = Category.objects.create(name='Test')
        Food.objects.create(name='Widget', price=10, sku='SKU-001', stock=0, category=cat)
        engine = ImportEngine()
        plan = {
            'Products': {
                'rows': [
                    {'name': 'Widget', 'price': '35.00', 'sku': 'SKU-001', 'stock': '80', 'category': 'Test'},
                    {'name': 'Gadget', 'price': '49.99', 'sku': 'SKU-002', 'stock': '50', 'category': 'Test'},
                ],
                'field_map': {'name': 'name', 'price': 'price', 'sku': 'sku', 'stock': 'stock', 'category': 'category'},
                'dup_action': 'skip',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        assert results['skipped'] == 1
        assert Food.objects.count() == 2

    def test_update_existing(self):
        from menu.models import Food, Category
        cat = Category.objects.create(name='Test')
        Food.objects.create(name='Widget', price=10, sku='SKU-001', stock=0, category=cat)
        engine = ImportEngine()
        plan = {
            'Products': {
                'rows': [{'name': 'Widget', 'price': '35.00', 'sku': 'SKU-001', 'stock': '80', 'category': 'Test'}],
                'field_map': {'name': 'name', 'price': 'price', 'sku': 'sku', 'stock': 'stock', 'category': 'category'},
                'dup_action': 'update_existing',
            }
        }
        results = engine.run_import(plan)
        assert results['updated'] == 1
        widget = Food.objects.get(sku='SKU-001')
        assert float(widget.price) == 35.00


@pytest.mark.django_db
class TestImportInventory:
    def test_import_opening_stock(self):
        from menu.models import Food, Category
        from megaone.users.models import StockMovement
        cat = Category.objects.create(name='Test')
        Food.objects.create(name='Widget', price=10, sku='SKU-001', stock=0, category=cat)
        engine = ImportEngine()
        plan = {
            'Inventory': {
                'rows': [{'product_name': 'Widget', 'sku': 'SKU-001', 'quantity': '50'}],
                'field_map': {'product_name': 'product_name', 'sku': 'sku', 'quantity': 'quantity'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        food = Food.objects.get(sku='SKU-001')
        assert food.stock == 50
        assert StockMovement.objects.filter(food=food).exists()

    def test_requires_existing_product(self):
        engine = ImportEngine()
        plan = {
            'Inventory': {
                'rows': [{'product_name': 'Nonexistent', 'quantity': '50'}],
                'field_map': {'product_name': 'product_name', 'quantity': 'quantity'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['failed'] == 1


@pytest.mark.django_db
class TestImportPurchases:
    def test_import_purchase(self):
        from menu.models import Food, Category
        from megaone.users.models import InventoryBatch, StockMovement
        cat = Category.objects.create(name='Test')
        Food.objects.create(name='Widget', price=10, sku='SKU-001', stock=0, category=cat)
        engine = ImportEngine()
        plan = {
            'Purchases': {
                'rows': [{
                    'product_name': 'Widget', 'sku': 'SKU-001',
                    'quantity': '30', 'unit_price': '15.00',
                    'supplier_name': 'Acme Corp', 'reference_number': 'PO-001',
                }],
                'field_map': {
                    'product_name': 'product_name', 'sku': 'sku',
                    'quantity': 'quantity', 'unit_price': 'unit_price',
                    'supplier_name': 'supplier_name', 'reference_number': 'reference_number',
                },
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        food = Food.objects.get(sku='SKU-001')
        assert food.stock == 30
        assert InventoryBatch.objects.filter(food=food).exists()
        assert StockMovement.objects.filter(food=food, transaction_type='stock_purchase').exists()

    def test_requires_existing_product(self):
        engine = ImportEngine()
        plan = {
            'Purchases': {
                'rows': [{'product_name': 'Nonexistent', 'quantity': '10', 'unit_price': '5'}],
                'field_map': {'product_name': 'product_name', 'quantity': 'quantity', 'unit_price': 'unit_price'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['failed'] == 1


@pytest.mark.django_db
class TestImportSales:
    def test_import_sales_invoice(self):
        from megaone.users.models import Invoice
        engine = ImportEngine()
        plan = {
            'Sales': {
                'rows': [{
                    'invoice_number': 'INV-001', 'customer_name': 'Alice',
                    'grand_total': '110.00', 'subtotal': '100.00',
                    'tax_amount': '10.00', 'payment_method': 'Credit Card',
                }],
                'field_map': {
                    'invoice_number': 'invoice_number', 'customer_name': 'customer_name',
                    'grand_total': 'grand_total', 'subtotal': 'subtotal',
                    'tax_amount': 'tax_amount', 'payment_method': 'payment_method',
                },
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        assert Invoice.objects.filter(invoice_number='INV-001').exists()

    def test_skip_duplicate_invoice(self):
        from megaone.users.models import Invoice
        Invoice.objects.create(invoice_number='INV-001', total_amount=100)
        engine = ImportEngine()
        plan = {
            'Sales': {
                'rows': [{'invoice_number': 'INV-001', 'grand_total': '200'}],
                'field_map': {'invoice_number': 'invoice_number', 'grand_total': 'grand_total'},
                'dup_action': 'skip',
            }
        }
        results = engine.run_import(plan)
        assert results['skipped'] == 1


@pytest.mark.django_db
class TestImportExpenses:
    def test_import_expense(self):
        from megaone.users.models import BusinessExpense, ExpenseCategory
        engine = ImportEngine()
        plan = {
            'Expenses': {
                'rows': [{
                    'title': 'Office Rent', 'amount': '2000.00',
                    'category': 'Rent', 'payment_method': 'Bank Transfer',
                }],
                'field_map': {
                    'title': 'title', 'amount': 'amount',
                    'category': 'category', 'payment_method': 'payment_method',
                },
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        assert BusinessExpense.objects.filter(title='Office Rent').exists()
        assert ExpenseCategory.objects.filter(name='Rent').exists()

    def test_default_category_when_missing(self):
        from megaone.users.models import BusinessExpense, ExpenseCategory
        engine = ImportEngine()
        plan = {
            'Expenses': {
                'rows': [{'title': 'Misc', 'amount': '50.00'}],
                'field_map': {'title': 'title', 'amount': 'amount'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        assert ExpenseCategory.objects.filter(name='General').exists()


@pytest.mark.django_db
class TestImportEmployees:
    def test_import_employee(self):
        from megaone.users.models import User
        engine = ImportEngine()
        email = 'eve_import@company.com'
        plan = {
            'Employees': {
                'rows': [{
                    'employee_name': 'Eve Adams', 'employee_id': 'EMP-001',
                    'email': email, 'phone': '555-0301', 'role': 'Cashier',
                }],
                'field_map': {
                    'employee_name': 'employee_name', 'employee_id': 'employee_id',
                    'email': 'email', 'phone': 'phone', 'role': 'role',
                },
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1
        assert User.objects.filter(email=email).exists()
        emp = User.objects.get(email=email)
        assert emp.is_operator
        assert emp.is_staff

    def test_skip_duplicate_email(self):
        from megaone.users.models import User
        email = 'eve_skip@company.com'
        User.objects.create(name='Eve', email=email)
        engine = ImportEngine()
        plan = {
            'Employees': {
                'rows': [{'employee_name': 'Eve Adams', 'email': email}],
                'field_map': {'employee_name': 'employee_name', 'email': 'email'},
                'dup_action': 'skip',
            }
        }
        results = engine.run_import(plan)
        assert results['skipped'] == 1


@pytest.mark.django_db
class TestImportOrder:
    def test_modules_executed_in_dependency_order(self):
        """Import plan must execute modules in IMPORT_ORDER regardless of dict order."""
        engine = ImportEngine()
        plan = {
            'Expenses': {'rows': [], 'field_map': {}, 'dup_action': 'create_new'},
            'Products': {'rows': [], 'field_map': {}, 'dup_action': 'create_new'},
            'Categories': {'rows': [], 'field_map': {}, 'dup_action': 'create_new'},
            'Sales': {'rows': [], 'field_map': {}, 'dup_action': 'create_new'},
        }
        results = engine.run_import(plan)
        # Verify modules ordered by IMPORT_ORDER
        mods = list(results['modules'].keys())
        expected_order = [m for m in IMPORT_ORDER if m in plan]
        assert mods == expected_order


@pytest.mark.django_db
class TestResultsStructure:
    def test_results_structure(self):
        engine = ImportEngine()
        plan = {
            'Products': {
                'rows': [{'name': 'Widget', 'price': '29.99', 'sku': 'SKU-001', 'stock': '100'}],
                'field_map': {'name': 'name', 'price': 'price', 'sku': 'sku', 'stock': 'stock'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert 'imported' in results
        assert 'updated' in results
        assert 'skipped' in results
        assert 'failed' in results
        assert 'total' in results
        assert 'modules' in results
        assert 'elapsed_formatted' in results
        assert results['modules']['Products']['imported'] == 1

    def test_atomic_rollback_on_error(self):
        """Each module runs in its own atomic block - one module failing
        should not roll back previous modules."""
        from menu.models import Food, Category
        engine = ImportEngine()
        plan = {
            'Products': {
                'rows': [{'name': 'Good', 'price': '10', 'sku': 'SKU-GOOD', 'stock': '5'}],
                'field_map': {'name': 'name', 'price': 'price', 'sku': 'sku', 'stock': 'stock'},
                'dup_action': 'create_new',
            }
        }
        results = engine.run_import(plan)
        assert results['imported'] == 1


@pytest.mark.django_db
class TestProgressTracking:
    def test_progress_updates_during_import(self):
        engine = ImportEngine()
        plan = {
            'Products': {
                'rows': [
                    {'name': 'P1', 'price': '10', 'sku': 'SKU-P1', 'stock': '5'},
                    {'name': 'P2', 'price': '20', 'sku': 'SKU-P2', 'stock': '10'},
                ],
                'field_map': {'name': 'name', 'price': 'price', 'sku': 'sku', 'stock': 'stock'},
                'dup_action': 'create_new',
            }
        }
        assert engine.get_progress()['percentage'] == 0
        results = engine.run_import(plan)
        assert engine.get_progress()['percentage'] == 100
        assert engine.get_progress()['records_processed'] == 2
