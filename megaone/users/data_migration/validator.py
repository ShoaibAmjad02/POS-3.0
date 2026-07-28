from datetime import datetime
from decimal import Decimal, InvalidOperation


class DataValidator:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.validation_results = {}

    def validate_product(self, row, idx):
        issues = []
        name = row.get('name', '')
        price = row.get('price', '')
        if not name or not str(name).strip():
            issues.append(f'Row {idx}: Missing product name')
        if price:
            try:
                if float(price) < 0:
                    issues.append(f'Row {idx}: Negative price {price}')
            except (ValueError, TypeError):
                issues.append(f'Row {idx}: Invalid price "{price}"')
        return issues

    def validate_customer(self, row, idx):
        issues = []
        name = row.get('name', '') or row.get('company_name', '')
        if not name or not str(name).strip():
            issues.append(f'Row {idx}: Missing customer name')
        email = row.get('email', '')
        if email and '@' not in str(email):
            issues.append(f'Row {idx}: Invalid email "{email}"')
        return issues

    def validate_sale(self, row, idx):
        issues = []
        invoice = row.get('invoice_number', '') or row.get('invoice_no', '')
        if not invoice:
            issues.append(f'Row {idx}: Missing invoice number')
        total = row.get('total_amount', '') or row.get('grand_total', '') or row.get('total', '')
        if total:
            try:
                if float(total) < 0:
                    issues.append(f'Row {idx}: Negative total {total}')
            except (ValueError, TypeError):
                issues.append(f'Row {idx}: Invalid total "{total}"')
        return issues

    def validate_date(self, value, field_name, idx):
        if not value:
            return None
        for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%d %H:%M', '%d-%m-%Y', '%m-%d-%Y', '%Y/%m/%d',
                    '%d/%m/%y', '%d-%b-%Y', '%Y.%m.%d', '%d.%m.%Y'):
            try:
                return datetime.strptime(str(value).strip(), fmt)
            except ValueError:
                continue
        self.errors.append(f'Row {idx}: Invalid date "{value}" in {field_name}')
        return None

    def validate_decimal(self, value, field_name, idx):
        if not value or not str(value).strip():
            return None
        v = str(value).strip().replace('$', '').replace('€', '').replace('£', '')
        v = v.replace(',', '').replace(' ', '')
        try:
            d = Decimal(v)
            return float(d)
        except (InvalidOperation, TypeError):
            self.errors.append(f'Row {idx}: Invalid number "{value}" in {field_name}')
            return None

    def validate_rows(self, module, rows, field_map):
        details = []
        error_list = []
        warning_list = []
        valid_count = 0

        def _val(key):
            src = field_map.get(key, key)
            return row.get(src, '')

        for i, row in enumerate(rows):
            issues = []
            if module == 'Products':
                mapped = {'name': _val('name'), 'price': _val('price'), 'sku': _val('sku'), 'barcode': _val('barcode'), 'stock': _val('stock'), 'category': _val('category')}
                issues = self.validate_product(mapped, i + 1)
            elif module == 'Customers':
                mapped = {'name': _val('name'), 'company_name': _val('company_name'), 'email': _val('email'), 'phone': _val('phone')}
                issues = self.validate_customer(mapped, i + 1)
            elif module == 'Sales':
                mapped = {'invoice_number': _val('invoice_number'), 'total_amount': _val('total_amount'), 'grand_total': _val('grand_total'), 'total': _val('total')}
                issues = self.validate_sale(mapped, i + 1)
            else:
                has_data = any(str(v).strip() for v in row.values())
                if not has_data:
                    issues.append(f'Row {i + 1}: Empty row')
            if issues:
                for issue in issues:
                    error_list.append({'row': i + 1, 'field': '', 'message': issue})
            else:
                valid_count += 1
            details.append({'row': i + 1, 'issues': issues, 'data': row})
        self.validation_results[module] = {
            'total_rows': len(rows),
            'valid': valid_count,
            'errors': error_list,
            'warnings': warning_list,
            'details': details,
        }
        return self.validation_results[module]

    def generate_report(self):
        report_lines = []
        total_valid = 0
        total_errors = 0
        total_warnings = 0
        for module, result in self.validation_results.items():
            err_count = len(result.get('errors', []))
            warn_count = len(result.get('warnings', []))
            report_lines.append(f'{module}: {result["valid"]} valid, {err_count} errors')
            total_valid += result['valid']
            total_errors += err_count
            total_warnings += warn_count
        return {
            'report': '\n'.join(report_lines),
            'total_valid': total_valid,
            'total_errors': total_errors,
            'total_warnings': total_warnings,
            'modules': self.validation_results,
        }
