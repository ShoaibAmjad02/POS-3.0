from collections import defaultdict


class DuplicateDetector:
    def __init__(self):
        self.duplicates = defaultdict(list)
        self.strategies = {
            'create_new': 'Create New',
            'update_existing': 'Update Existing',
            'skip': 'Skip',
            'merge': 'Merge',
        }

    def _get_key(self, row, key_fields):
        parts = []
        for field in key_fields:
            val = row.get(field, '')
            if val and str(val).strip():
                parts.append(str(val).strip().lower())
        return '|'.join(parts) if parts else None

    def detect_products(self, rows, existing_skus=None, existing_barcodes=None, existing_names=None):
        results = []
        seen = {}
        existing_skus = existing_skus or set()
        existing_barcodes = existing_barcodes or set()
        existing_names = existing_names or set()

        for i, row in enumerate(rows):
            sku = self._get_key(row, ['sku', 'product_code'])
            barcode = self._get_key(row, ['barcode', 'upc', 'ean'])
            name = self._get_key(row, ['name', 'product_name'])
            cat = self._get_key(row, ['category'])

            dup_reasons = []

            if sku and sku in existing_skus:
                dup_reasons.append(f'SKU "{sku}" already exists')
            if barcode and barcode in existing_barcodes:
                dup_reasons.append(f'Barcode "{barcode}" already exists')
            if name and cat:
                compound = f'{name}|{cat}'
                if compound in seen:
                    dup_reasons.append(f'Duplicate name+category: "{name}" + "{cat}"')

            if name:
                existing_skus.add(sku) if sku else None
                existing_barcodes.add(barcode) if barcode else None
                seen_key = f'{name}|{cat}' if cat else name
                if seen_key in seen:
                    if not dup_reasons:
                        dup_reasons.append(f'Duplicate name: "{name}"')
                else:
                    seen[seen_key] = i

            results.append({
                'row': i + 1,
                'is_duplicate': len(dup_reasons) > 0,
                'reasons': dup_reasons,
                'suggested_action': 'skip' if dup_reasons else 'create_new',
                'data': row,
            })
        return results

    def detect_customers(self, rows, existing_emails=None, existing_phones=None):
        results = []
        existing_emails = existing_emails or set()
        existing_phones = existing_phones or set()

        for i, row in enumerate(rows):
            email = self._get_key(row, ['email', 'customer_email'])
            phone = self._get_key(row, ['phone', 'customer_phone', 'mobile'])
            code = self._get_key(row, ['customer_code', 'customer_id'])

            dup_reasons = []
            if email and email in existing_emails:
                dup_reasons.append(f'Email "{email}" already exists')
            if phone and phone in existing_phones:
                dup_reasons.append(f'Phone "{phone}" already exists')

            if email:
                existing_emails.add(email)
            if phone:
                existing_phones.add(phone)

            results.append({
                'row': i + 1,
                'is_duplicate': len(dup_reasons) > 0,
                'reasons': dup_reasons,
                'suggested_action': 'skip' if dup_reasons else 'create_new',
                'data': row,
            })
        return results

    def detect_loyalty_cards(self, rows, existing_card_numbers=None):
        results = []
        existing_card_numbers = existing_card_numbers or set()

        for i, row in enumerate(rows):
            card = self._get_key(row, ['card_number', 'loyalty_card', 'membership_id'])
            dup_reasons = []
            if card and card in existing_card_numbers:
                dup_reasons.append(f'Card number "{card}" already exists')
            if card:
                existing_card_numbers.add(card)
            results.append({
                'row': i + 1,
                'is_duplicate': len(dup_reasons) > 0,
                'reasons': dup_reasons,
                'suggested_action': 'skip' if dup_reasons else 'create_new',
                'data': row,
            })
        return results

    def detect_suppliers(self, rows, existing_codes=None, existing_names=None):
        results = []
        existing_codes = existing_codes or set()
        existing_names = existing_names or set()

        for i, row in enumerate(rows):
            code = self._get_key(row, ['supplier_code', 'vendor_code'])
            name = self._get_key(row, ['supplier_name', 'company_name', 'supplier'])

            dup_reasons = []
            if code and code in existing_codes:
                dup_reasons.append(f'Supplier code "{code}" already exists')
            if name and name in existing_names:
                dup_reasons.append(f'Supplier name "{name}" already exists')

            if code:
                existing_codes.add(code)
            if name:
                existing_names.add(name)

            results.append({
                'row': i + 1,
                'is_duplicate': len(dup_reasons) > 0,
                'reasons': dup_reasons,
                'suggested_action': 'skip' if dup_reasons else 'create_new',
                'data': row,
            })
        return results

    def detect_all(self, module, rows, existing_data=None):
        if module == 'Products':
            return self.detect_products(rows)
        elif module == 'Customers':
            return self.detect_customers(rows)
        elif module == 'Loyalty Cards':
            return self.detect_loyalty_cards(rows)
        elif module == 'Suppliers':
            return self.detect_suppliers(rows)
        else:
            return [{'row': i + 1, 'is_duplicate': False, 'reasons': [], 'suggested_action': 'create_new', 'data': row} for i, row in enumerate(rows)]
