import json
import logging
import time
from decimal import Decimal
from datetime import datetime
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


IMPORT_ORDER = [
    'Expense Categories',
    'Categories',
    'Suppliers',
    'Customers',
    'Loyalty Cards',
    'Products',
    'Inventory',
    'Purchases',
    'Sales',
    'Expenses',
    'Employees',
]


class ImportEngine:
    def __init__(self, user=None):
        self.user = user
        self.results = {
            'imported': 0,
            'updated': 0,
            'skipped': 0,
            'merged': 0,
            'failed': 0,
            'total': 0,
            'modules': {},
            'errors': [],
            'warnings': [],
            'started_at': None,
            'completed_at': None,
        }
        self._progress = {
            'current_module': '',
            'records_processed': 0,
            'total_records': 0,
            'percentage': 0,
            'estimated_remaining': 0,
            'current_operation': '',
            'success_count': 0,
            'error_count': 0,
            'skip_count': 0,
            'update_count': 0,
        }

    def get_progress(self):
        return self._progress

    def _update_progress(self, **kwargs):
        self._progress.update(kwargs)
        if self._progress['total_records'] > 0:
            self._progress['percentage'] = int(
                (self._progress['records_processed'] / self._progress['total_records']) * 100
            )

    def import_expense_categories(self, rows, dup_action, field_map, progress_callback=None):
        from megaone.users.models import ExpenseCategory
        imported = updated = skipped = failed = 0
        for i, row in enumerate(rows):
            try:
                name = str(row.get(field_map.get('name', 'name'), '') or '').strip()
                if not name:
                    failed += 1
                    continue
                existing = ExpenseCategory.objects.filter(name=name).first()
                if existing:
                    if dup_action == 'skip':
                        skipped += 1
                    else:
                        updated += 1
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                ExpenseCategory.objects.create(name=name, is_active=True)
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def import_categories(self, rows, dup_action, field_map, progress_callback=None):
        from menu.models import Category
        imported = updated = skipped = failed = 0
        for i, row in enumerate(rows):
            try:
                name = str(row.get(field_map.get('name', 'name'), '') or '').strip()
                if not name:
                    failed += 1
                    continue
                existing = Category.objects.filter(name=name).first()
                if existing:
                    if dup_action == 'skip':
                        skipped += 1
                    else:
                        updated += 1
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                Category.objects.create(name=name, is_active=True)
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def import_suppliers(self, rows, dup_action, field_map, progress_callback=None):
        imported = updated = skipped = failed = 0
        from megaone.users.models import WholesaleCustomer
        for i, row in enumerate(rows):
            try:
                company = str(row.get(field_map.get('company_name', 'company_name'), '') or
                              row.get(field_map.get('supplier_name', 'supplier_name'), '') or '').strip()
                if not company:
                    failed += 1
                    continue
                contact = str(row.get(field_map.get('contact_person', 'contact_person'), '') or '').strip()
                email = str(row.get(field_map.get('email', 'email'), '') or '').strip()
                phone = str(row.get(field_map.get('phone', 'phone'), '') or '').strip()
                existing = WholesaleCustomer.objects.filter(company_name=company).first()
                if existing:
                    if dup_action == 'skip':
                        skipped += 1
                    elif dup_action in ('update_existing', 'merge'):
                        existing.contact_person = contact or existing.contact_person
                        existing.email = email or existing.email
                        existing.phone = phone or existing.phone
                        existing.save()
                        updated += 1
                    else:
                        skipped += 1
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                WholesaleCustomer.objects.create(
                    company_name=company, contact_person=contact,
                    email=email, phone=phone, is_active=True,
                )
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def import_customers(self, rows, dup_action, field_map, progress_callback=None):
        from megaone.users.models import User
        imported = updated = skipped = failed = 0
        for i, row in enumerate(rows):
            try:
                name = str(row.get(field_map.get('name', 'name'), '') or row.get(field_map.get('company_name', 'company_name'), '') or '').strip()
                if not name:
                    failed += 1
                    continue
                email = str(row.get(field_map.get('email', 'email'), '') or '').strip()
                phone = str(row.get(field_map.get('phone', 'phone'), '') or '').strip()
                existing = None
                if email:
                    existing = User.objects.filter(email=email).first()
                if not existing and phone:
                    existing = User.objects.filter(phone=phone).first()
                if existing:
                    if dup_action == 'skip':
                        skipped += 1
                    elif dup_action in ('update_existing', 'merge'):
                        existing.name = name
                        if phone:
                            existing.phone = phone
                        existing.save()
                        updated += 1
                    else:
                        skipped += 1
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                User.objects.create(
                    name=name, email=email or f'{name.replace(" ", "").lower()}@imported.local',
                    phone=phone, is_staff=False,
                )
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def import_loyalty_cards(self, rows, dup_action, field_map, progress_callback=None):
        from megaone.users.models import LoyaltyCard
        imported = updated = skipped = failed = 0
        for i, row in enumerate(rows):
            try:
                card = str(row.get(field_map.get('card_number', 'card_number'), '') or '').strip()
                if not card:
                    failed += 1
                    continue
                email = str(row.get(field_map.get('email', 'email'), '') or '').strip()
                points_raw = row.get(field_map.get('total_points', 'total_points'), 0)
                try:
                    points = int(float(points_raw)) if points_raw else 0
                except (ValueError, TypeError):
                    points = 0
                existing = LoyaltyCard.objects.filter(card_number=card).first()
                if existing:
                    if dup_action == 'skip':
                        skipped += 1
                    elif dup_action in ('update_existing', 'merge'):
                        existing.total_points = points
                        existing.remaining_points = points - existing.used_points
                        existing.save()
                        updated += 1
                    else:
                        skipped += 1
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                LoyaltyCard.objects.create(
                    card_number=card, total_points=points,
                    remaining_points=points, status='ACTIVE',
                )
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def import_products(self, rows, dup_action, field_map, progress_callback=None):
        from menu.models import Food, Category
        imported = updated = skipped = failed = 0
        for i, row in enumerate(rows):
            try:
                name = row.get(field_map.get('name', 'name'), '')
                if not name or not str(name).strip():
                    failed += 1
                    self.results['errors'].append(f'Row {i+1}: Missing product name')
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                price_raw = row.get(field_map.get('price', 'price'), '0')
                try:
                    price = float(price_raw) if price_raw else 0
                except (ValueError, TypeError):
                    price = 0
                sku = str(row.get(field_map.get('sku', 'sku'), '') or '').strip()
                barcode = str(row.get(field_map.get('barcode', 'barcode'), '') or '').strip()
                cat_name = str(row.get(field_map.get('category', 'category'), '') or '').strip()
                if cat_name:
                    category, _ = Category.objects.get_or_create(name=cat_name)
                else:
                    category, _ = Category.objects.get_or_create(name='Imported')
                existing = None
                if sku:
                    existing = Food.objects.filter(sku=sku).first()
                if not existing and barcode:
                    existing = Food.objects.filter(barcode=barcode).first()
                if not existing:
                    existing = Food.objects.filter(name=name).first()
                if existing:
                    if dup_action == 'skip':
                        skipped += 1
                    elif dup_action == 'update_existing' or dup_action == 'merge':
                        existing.price = price
                        if sku:
                            existing.sku = sku
                        if barcode:
                            existing.barcode = barcode
                        if category:
                            existing.category = category
                        existing.save()
                        updated += 1
                    else:
                        skipped += 1
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                Food.objects.create(
                    name=name, price=price, category=category,
                    sku=sku, barcode=barcode,
                    stock=int(float(row.get(field_map.get('stock', 'stock'), 0) or 0)),
                    available=True,
                )
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def import_inventory(self, rows, dup_action, field_map, progress_callback=None):
        from menu.models import Food
        from megaone.users.models import StockMovement
        imported = updated = skipped = failed = 0
        for i, row in enumerate(rows):
            try:
                product_key = (row.get(field_map.get('product_name', 'product_name'), '') or
                               row.get(field_map.get('product_code', 'product_code'), '') or
                               row.get(field_map.get('sku', 'sku'), '') or
                               row.get(field_map.get('barcode', 'barcode'), '') or '')
                if not product_key:
                    failed += 1
                    continue
                food = (
                    Food.objects.filter(sku=product_key).first() or
                    Food.objects.filter(barcode=product_key).first() or
                    Food.objects.filter(name=product_key).first()
                )
                if not food:
                    failed += 1
                    self.results['errors'].append(f'Row {i+1}: Product not found for inventory: {product_key}')
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                qty_raw = row.get(field_map.get('quantity', 'quantity'), 0) or 0
                try:
                    qty = int(float(qty_raw))
                except (ValueError, TypeError):
                    qty = 0
                if qty == 0:
                    skipped += 1
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                food.stock += qty
                food.save()
                StockMovement.objects.create(
                    food=food,
                    transaction_type='opening_stock',
                    quantity_change=qty,
                    stock_before=food.stock - qty,
                    stock_after=food.stock,
                    created_by=self.user,
                )
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def import_purchases(self, rows, dup_action, field_map, progress_callback=None):
        from menu.models import Food
        from megaone.users.models import InventoryBatch, StockMovement
        imported = updated = skipped = failed = 0
        for i, row in enumerate(rows):
            try:
                product_key = (row.get(field_map.get('product_name', 'product_name'), '') or
                               row.get(field_map.get('sku', 'sku'), '') or '')
                if not product_key:
                    failed += 1
                    continue
                food = (
                    Food.objects.filter(sku=product_key).first() or
                    Food.objects.filter(name=product_key).first()
                )
                if not food:
                    failed += 1
                    self.results['errors'].append(f'Row {i+1}: Product not found for purchase: {product_key}')
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                qty_raw = row.get(field_map.get('quantity', 'quantity'), 0) or 0
                try:
                    qty = int(float(qty_raw))
                except (ValueError, TypeError):
                    qty = 0
                unit_cost_raw = row.get(field_map.get('unit_price', 'unit_price'), 0) or 0
                try:
                    unit_cost = float(unit_cost_raw)
                except (ValueError, TypeError):
                    unit_cost = 0
                ref = str(row.get(field_map.get('reference_number', 'reference_number'), '') or
                          row.get(field_map.get('invoice_number', 'invoice_number'), '') or '').strip()
                supplier = str(row.get(field_map.get('supplier_name', 'supplier_name'), '') or '').strip()
                food.stock += qty
                food.save()
                batch = InventoryBatch.objects.create(
                    food=food,
                    quantity=qty,
                    remaining_quantity=qty,
                    unit_cost=unit_cost,
                    total_cost=unit_cost * qty,
                    selling_price=food.price,
                    supplier=supplier or None,
                    purchase_reference=ref or None,
                )
                StockMovement.objects.create(
                    food=food,
                    transaction_type='stock_purchase',
                    reference_number=ref or None,
                    quantity_change=qty,
                    stock_before=food.stock - qty,
                    stock_after=food.stock,
                    created_by=self.user,
                )
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def import_sales(self, rows, dup_action, field_map, progress_callback=None):
        from megaone.users.models import Invoice, InvoiceItem
        imported = updated = skipped = failed = 0
        for i, row in enumerate(rows):
            try:
                invoice_number = str(row.get(field_map.get('invoice_number', 'invoice_number'), '') or '').strip()
                if not invoice_number:
                    failed += 1
                    continue
                existing = Invoice.objects.filter(invoice_number=invoice_number).first()
                if existing:
                    if dup_action == 'skip':
                        skipped += 1
                    elif dup_action in ('update_existing', 'merge'):
                        updated += 1
                    else:
                        skipped += 1
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                customer_name = str(row.get(field_map.get('customer_name', 'customer_name'), '') or '').strip()
                customer_email = str(row.get(field_map.get('customer_email', 'customer_email'), '') or '').strip()
                customer_phone = str(row.get(field_map.get('customer_phone', 'customer_phone'), '') or '').strip()
                payment_method = str(row.get(field_map.get('payment_method', 'payment_method'), '') or '').strip()
                total_raw = row.get(field_map.get('grand_total', 'grand_total'), 0) or 0
                try:
                    total = float(total_raw)
                except (ValueError, TypeError):
                    total = 0
                subtotal_raw = row.get(field_map.get('subtotal', 'subtotal'), total) or total
                try:
                    subtotal = float(subtotal_raw)
                except (ValueError, TypeError):
                    subtotal = total
                tax_raw = row.get(field_map.get('tax_amount', 'tax_amount'), 0) or 0
                try:
                    tax = float(tax_raw)
                except (ValueError, TypeError):
                    tax = 0
                invoice = Invoice.objects.create(
                    invoice_number=invoice_number,
                    customer_name=customer_name or None,
                    customer_email=customer_email or None,
                    customer_phone=customer_phone or None,
                    payment_method=payment_method or None,
                    subtotal_amount=subtotal,
                    tax_amount=tax,
                    total_amount=total,
                    created_by=self.user,
                )
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def import_expenses(self, rows, dup_action, field_map, progress_callback=None):
        from megaone.users.models import BusinessExpense, ExpenseCategory
        imported = updated = skipped = failed = 0
        for i, row in enumerate(rows):
            try:
                title = str(row.get(field_map.get('title', 'title'), '') or '').strip()
                amount_raw = row.get(field_map.get('amount', 'amount'), '0')
                try:
                    amount = float(amount_raw) if amount_raw else 0
                except (ValueError, TypeError):
                    amount = 0
                if not title:
                    failed += 1
                    continue
                cat_name = str(row.get(field_map.get('category', 'category'), '') or '').strip()
                if cat_name:
                    category, _ = ExpenseCategory.objects.get_or_create(name=cat_name)
                else:
                    category, _ = ExpenseCategory.objects.get_or_create(name='General')
                payment_method = str(row.get(field_map.get('payment_method', 'payment_method'), '') or '').strip()
                date_raw = row.get(field_map.get('expense_date', 'expense_date'), '')
                BusinessExpense.objects.create(
                    title=title, amount=amount, category=category,
                    payment_method=payment_method or 'cash',
                    expense_date=timezone.now(),
                    created_by=self.user,
                )
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def import_employees(self, rows, dup_action, field_map, progress_callback=None):
        from megaone.users.models import User
        imported = updated = skipped = failed = 0
        for i, row in enumerate(rows):
            try:
                name = str(row.get(field_map.get('employee_name', 'employee_name'), '') or
                           row.get(field_map.get('name', 'name'), '') or '').strip()
                emp_id = str(row.get(field_map.get('employee_id', 'employee_id'), '') or '').strip()
                if not name:
                    failed += 1
                    continue
                email = str(row.get(field_map.get('email', 'email'), '') or
                            (f'emp{emp_id}@imported.local' if emp_id else '')).strip()
                phone = str(row.get(field_map.get('phone', 'phone'), '') or '').strip()
                role = str(row.get(field_map.get('role', 'role'), '') or '').strip().lower()
                existing = None
                if email:
                    existing = User.objects.filter(email=email).first()
                if not existing and phone:
                    existing = User.objects.filter(phone=phone).first()
                if existing:
                    if dup_action == 'skip':
                        skipped += 1
                    elif dup_action in ('update_existing', 'merge'):
                        existing.name = name
                        if phone:
                            existing.phone = phone
                        existing.save()
                        updated += 1
                    else:
                        skipped += 1
                    self._update_progress(records_processed=self._progress['records_processed'] + 1)
                    if progress_callback:
                        progress_callback(self._progress)
                    continue
                User.objects.create(
                    name=name,
                    email=email or f'{name.replace(" ", "").lower()}@imported.local',
                    phone=phone,
                    is_staff=True,
                    is_operator=True,
                )
                imported += 1
            except Exception as e:
                failed += 1
                self.results['errors'].append(f'Row {i+1}: {str(e)}')
            self._update_progress(records_processed=self._progress['records_processed'] + 1)
            if progress_callback:
                progress_callback(self._progress)
        return imported, updated, skipped, failed

    def run_module(self, module, rows, dup_action, field_map):
        import_functions = {
            'Expense Categories': self.import_expense_categories,
            'Categories': self.import_categories,
            'Suppliers': self.import_suppliers,
            'Customers': self.import_customers,
            'Loyalty Cards': self.import_loyalty_cards,
            'Products': self.import_products,
            'Inventory': self.import_inventory,
            'Purchases': self.import_purchases,
            'Sales': self.import_sales,
            'Expenses': self.import_expenses,
            'Employees': self.import_employees,
        }
        func = import_functions.get(module)
        if not func:
            return 0, 0, 0, 0
        return func(rows, dup_action, field_map)

    def run_import(self, plan):
        self.results['started_at'] = time.time()
        total_records = sum(len(p['rows']) for p in plan.values())
        self._progress['total_records'] = total_records
        total_imported = total_updated = total_skipped = total_failed = 0
        total_merged = 0

        sorted_modules = [m for m in IMPORT_ORDER if m in plan]

        logger.info('[MIGRATION] Starting import: %d modules, %d total records', len(sorted_modules), total_records)

        for module in sorted_modules:
            config = plan[module]
            logger.info('[MIGRATION] Importing %s (%d rows)', module, len(config.get('rows', [])))
            self._update_progress(current_module=module, current_operation=f'Importing {module}...')
            rows = config['rows']
            dup_action = config.get('dup_action', 'create_new')
            field_map = config.get('field_map', {})

            with transaction.atomic():
                imp, upd, skip, fail = self.run_module(module, rows, dup_action, field_map)

            total_imported += imp
            total_updated += upd
            total_skipped += skip
            total_failed += fail

            self.results['modules'][module] = {
                'imported': imp,
                'updated': upd,
                'skipped': skip,
                'failed': fail,
                'total': len(rows),
            }

        import math
        elapsed = time.time() - self.results['started_at']
        self.results.update({
            'imported': total_imported,
            'updated': total_updated,
            'skipped': total_skipped,
            'merged': total_merged,
            'failed': total_failed,
            'total': total_records,
            'completed_at': time.time(),
            'elapsed_seconds': int(elapsed),
            'elapsed_formatted': self._format_elapsed(elapsed),
        })
        logger.info(
            '[MIGRATION] Import completed: %d imported, %d updated, %d skipped, %d failed in %s',
            total_imported, total_updated, total_skipped, total_failed,
            self.results['elapsed_formatted'],
        )
        return self.results

    def _format_elapsed(self, seconds):
        m, s = divmod(int(seconds), 60)
        h, m = divmod(m, 60)
        if h:
            return f'{h}h {m}m {s}s'
        if m:
            return f'{m}m {s}s'
        return f'{s}s'
