import json
import logging
import pickle
import uuid
from collections import OrderedDict

from django.core.cache import cache

logger = logging.getLogger(__name__)

from .detector import analyze_file
from .field_matcher import detect_fields, suggest_mapping
from .validator import DataValidator
from .duplicate_detector import DuplicateDetector
from .importer import ImportEngine, IMPORT_ORDER


MIGRATION_SESSION_PREFIX = 'data_migration_session_'


MIGRATION_MODULES = [
    'Products',
    'Categories',
    'Customers',
    'Loyalty Cards',
    'Suppliers',
    'Expenses',
    'Expense Categories',
    'Inventory',
    'Sales',
    'Purchases',
    'Employees',
]


MODULE_FIELDS = {
    'Products': ['name', 'price', 'category', 'sku', 'barcode', 'wholesale_price',
                 'cost_price', 'stock', 'available', 'description', 'discount_type',
                 'discount_value', 'reward_points'],
    'Categories': ['name', 'is_active'],
    'Customers': ['name', 'company_name', 'email', 'phone', 'address', 'city',
                  'state', 'zip_code', 'country', 'is_active'],
    'Loyalty Cards': ['card_number', 'email', 'customer_name', 'customer_phone',
                      'total_points', 'used_points', 'remaining_points', 'status'],
    'Suppliers': ['company_name', 'contact_person', 'email', 'phone', 'address',
                  'credit_limit', 'is_active', 'supplier_code'],
    'Expenses': ['title', 'amount', 'category', 'payment_method', 'expense_date', 'description'],
    'Expense Categories': ['name', 'is_active'],
    'Inventory': ['product_name', 'product_code', 'sku', 'barcode', 'quantity', 'stock',
                  'warehouse', 'batch_number', 'expiry_date', 'unit_price', 'cost_price'],
    'Sales': ['invoice_number', 'customer_name', 'customer_email', 'customer_phone',
              'subtotal', 'tax_amount', 'discount_amount', 'grand_total', 'payment_method',
              'payment_status', 'created_at', 'items'],
    'Purchases': ['reference_number', 'supplier_name', 'supplier_email', 'product_name',
                  'quantity', 'unit_price', 'total_amount', 'purchase_date', 'status',
                  'invoice_number'],
    'Employees': ['employee_id', 'employee_name', 'email', 'phone', 'role', 'department',
                  'is_active', 'joining_date', 'salary'],
}

DUPLICATE_KEY_MAP = {
    'Products': ['sku', 'barcode', 'name'],
    'Customers': ['email', 'phone'],
    'Loyalty Cards': ['card_number'],
    'Suppliers': ['company_name', 'supplier_code'],
    'Categories': ['name'],
    'Expense Categories': ['name'],
}


def _session_key(session_id):
    return f'{MIGRATION_SESSION_PREFIX}{session_id}'


def create_session():
    session_id = str(uuid.uuid4())
    session = {
        'id': session_id,
        'step': 1,
        'file_name': None,
        'file_type': None,
        'file_size': 0,
        'analysis': None,
        'modules': OrderedDict(),
        'selected_modules': [],
        'module_data': {},
        'field_mappings': {},
        'dup_actions': {},
        'validation': {},
        'duplicate_results': {},
        'import_plan': None,
        'import_results': None,
        'import_running': False,
    }
    cache.set(_session_key(session_id), session, timeout=3600)
    return session


def get_session(session_id):
    data = cache.get(_session_key(session_id))
    if data:
        return data
    return None


def save_session(session):
    cache.set(_session_key(session['id']), session, timeout=3600)


def step1_upload(session, uploaded_file):
    session['file_name'] = uploaded_file.name
    session['file_size'] = uploaded_file.size

    analysis = analyze_file(uploaded_file)
    session['analysis'] = analysis
    session['file_type'] = analysis['file_type']

    detected = OrderedDict()
    for module in MIGRATION_MODULES:
        if module in analysis.get('modules', {}):
            detected[module] = analysis['modules'][module]

    session['modules'] = detected
    session['step'] = 2
    save_session(session)
    return session


def step2_analyze(session):
    analysis = session.get('analysis', {})
    if not analysis:
        return session

    tables = analysis.get('tables', [])
    all_columns = []
    for table in tables:
        for col in table.get('columns', []):
            all_columns.append(col['name'])

    module_data = {}
    for module in MIGRATION_MODULES:
        if module in session.get('modules', {}):
            fields = MODULE_FIELDS.get(module, [])
            mapping = detect_fields(all_columns, fields)
            module_data[module] = {
                'mapping': mapping,
                'unmapped_fields': [f for f in fields if f not in mapping],
                'field_count': len(fields),
                'mapped_count': len(mapping),
                'sample_rows': [],
                'all_data': [],
            }

    if tables:
        for table in tables:
            for module, data in module_data.items():
                if not data['all_data']:
                    data['sample_rows'] = table.get('sample_rows', [])[:5]
                    data['all_data'] = table.get('sample_rows', [])

    session['module_data'] = module_data
    for module in list(session['modules'].keys()):
        if module in module_data:
            session['modules'][module]['estimated_count'] = module_data[module]['field_count']
            session['modules'][module]['field_count'] = module_data[module]['field_count']
            session['modules'][module]['mapped_count'] = module_data[module]['mapped_count']
            if module_data[module]['mapped_count'] == 0:
                session['modules'][module]['warnings'].append(f'No fields could be auto-mapped for {module}')

    session['step'] = 3
    save_session(session)
    return session


def step3_get_summary(session):
    return session


def step4_get_preview(session, module):
    module_data = session.get('module_data', {})
    return module_data.get(module, {})


def step5_detect_duplicates(session):
    detector = DuplicateDetector()
    dup_results = {}
    for module in session.get('selected_modules', []):
        data = session.get('module_data', {}).get(module, {})
        rows = data.get('all_data', [])
        field_map = data.get('mapping', {})
        reverse_map = {v: k for k, v in field_map.items()}
        mapped_rows = []
        for row in rows:
            mapped_row = {}
            for src_key, val in row.items():
                mapped_key = reverse_map.get(src_key, src_key)
                mapped_row[mapped_key] = val
            mapped_rows.append(mapped_row)
        dup_results[module] = detector.detect_all(module, mapped_rows)
    session['duplicate_results'] = dup_results
    session['step'] = 5
    save_session(session)
    return session


def step6_validate(session):
    validator = DataValidator()
    validation = {}
    for module in session.get('selected_modules', []):
        data = session.get('module_data', {}).get(module, {})
        rows = data.get('all_data', [])
        field_map = data.get('mapping', {})
        validation[module] = validator.validate_rows(module, rows, field_map)
    session['validation'] = validation
    session['step'] = 6
    save_session(session)
    return session


def step7_prepare_import(session, dup_actions=None):
    if dup_actions:
        session['dup_actions'] = dup_actions

    plan = {}
    selected = session.get('selected_modules', [])
    sorted_modules = sorted(selected, key=lambda m: IMPORT_ORDER.index(m) if m in IMPORT_ORDER else len(IMPORT_ORDER))
    for module in sorted_modules:
        data = session.get('module_data', {}).get(module, {})
        rows = data.get('all_data', [])
        field_map = data.get('mapping', {})
        dup_action = (dup_actions or {}).get(module, 'create_new')
        plan[module] = {
            'rows': rows,
            'field_map': field_map,
            'dup_action': dup_action,
        }

    total = sum(len(p['rows']) for p in plan.values())
    session['import_plan'] = plan
    session['step'] = 7
    save_session(session)
    return session, total


def step8_execute_import(session, user=None):
    plan = session.get('import_plan', {})
    if not plan:
        return session, None

    engine = ImportEngine(user=user)
    session['import_running'] = True
    save_session(session)

    results = engine.run_import(plan)
    session['import_results'] = results
    session['import_running'] = False
    session['step'] = 8
    save_session(session)
    return session, results


def get_module_fields():
    return MODULE_FIELDS


def get_migration_modules():
    return MIGRATION_MODULES


def clear_session(session_id):
    cache.delete(_session_key(session_id))
