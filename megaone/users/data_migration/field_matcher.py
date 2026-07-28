import re


FIELD_ALIASES = {
    'name': ['product name', 'item name', 'name', 'product', 'item', 'service name',
             'description of goods', 'inventory item', 'item description', 'title',
             'product title', 'food name', 'product description', 'category name'],
    'price': ['price', 'selling price', 'unit price', 'sale price', 'retail price',
              'mrp', 'list price', 'rate', 'sales price', 'regular price', 'standard price',
              'unit selling price', 'sp', 'sell price', 'product price', 'item price'],
    'wholesale_price': ['wholesale price', 'trade price', 'dealer price', 'bulk price',
                        'ws price', 'wholesale', 'wholesale rate', 'distributor price'],
    'cost_price': ['cost price', 'purchase price', 'cost', 'buying price', 'unit cost',
                   'landed cost', 'supplier price', 'product cost', 'item cost',
                   'original cost', 'cost per unit', 'unit purchase price', 'purchase cost'],
    'stock': ['stock', 'quantity', 'qty', 'inventory', 'stock qty', 'qoh', 'on hand',
              'available qty', 'current stock', 'balance', 'stock on hand', 'quantity on hand',
              'available stock', 'stock level', 'in stock', 'opening stock', 'stock quantity',
              'stock count', 'current qty'],
    'sku': ['sku', 'code', 'product code', 'item code', 'sku code', 'stock code',
            'part number', 'reference', 'product ref', 'ref code', 'internal code',
            'inventory code', 'product number', 'item number', 'article code'],
    'barcode': ['barcode', 'bar code', 'upc', 'ean', 'isbn', 'gtin', 'barcode number',
                'barcode no', 'bar code number', 'upc code', 'ean code', 'scan code',
                'barcode/ean', 'upc/ean'],
    'category': ['category', 'department', 'group', 'product group', 'section', 'type',
                 'class', 'category name', 'product category', 'item category', 'commodity',
                 'classification', 'product line', 'category id', 'cat'],
    'description': ['description', 'desc', 'details', 'notes', 'comments', 'product description',
                    'full description', 'specification', 'remarks', 'additional info',
                    'long description', 'short description', 'product details'],
    'discount_type': ['discount type', 'disc type', 'discount method', 'discount category', 'discount mode'],
    'discount_value': ['discount', 'discount value', 'disc %', 'discount %', 'discount amount',
                       'discount percent', 'offer discount', 'discount rate', 'discount percentage'],
    'reward_points': ['reward points', 'points', 'loyalty points', 'reward point', 'point',
                      'cashback points', 'loyalty point', 'member points', 'bonus points'],
    'available': ['available', 'active', 'status', 'enabled', 'is active', 'is available',
                  'is enabled', 'published', 'visibility', 'is visible', 'in stock status'],
    'company_name': ['company name', 'company', 'business name', 'customer', 'customer name',
                     'client', 'organization', 'firm', 'business', 'account name', 'trading name',
                     'company', 'supplier name', 'vendor name'],
    'contact_person': ['contact person', 'contact', 'contact name', 'person', 'representative',
                       'contact person name', 'primary contact', 'account manager', 'contact person'],
    'card_number': ['card number', 'card no', 'card#', 'card id', 'loyalty card', 'member id',
                    'member card', 'card #', 'loyalty id', 'membership id', 'loyalty number',
                    'membership number', 'loyalty card number', 'member number'],
    'title': ['title', 'expense title', 'name', 'expense name', 'particulars',
              'expense description', 'narration', 'item', 'expense item'],
    'amount': ['amount', 'total', 'value', 'expense amount', 'cost', 'sum', 'net amount',
               'gross amount', 'taxable amount', 'total amount', 'paid amount', 'transaction amount'],
    'payment_method': ['payment method', 'payment', 'pay mode', 'payment type', 'mode', 'method',
                       'payment mode', 'payment term', 'payment option', 'transaction type'],
    'expense_date': ['expense date', 'date', 'transaction date', 'date of expense', 'posted date',
                     'entry date', 'payment date', 'voucher date', 'bill date', 'expense date'],
    'quantity_change': ['quantity change', 'qty change', 'adjustment', 'change', 'difference',
                        'delta', 'qty adjustment', 'stock change', 'quantity adjustment', 'adjustment qty'],
    'product_name': ['product name', 'product', 'item', 'name', 'item name', 'inventory item',
                     'product description', 'product title', 'food name'],
    'notes': ['notes', 'note', 'remarks', 'comments', 'memo', 'description', 'additional notes'],
    'total_points': ['total points', 'total points earned', 'points earned', 'earned points',
                     'lifetime points', 'total pts'],
    'used_points': ['used points', 'points used', 'redeemed points', 'points redeemed'],
    'remaining_points': ['remaining points', 'points remaining', 'balance points', 'available points',
                         'points balance', 'remaining balance'],
    'email': ['email', 'email address', 'e-mail', 'user email', 'customer email', 'email id',
              'electronic mail', 'mail'],
    'phone': ['phone', 'telephone', 'mobile', 'phone number', 'contact no', 'mobile no',
              'cell', 'tel', 'telephone number', 'mobile number', 'cell phone'],
    'address': ['address', 'address line 1', 'street', 'location', 'postal address',
                'shipping address', 'billing address', 'street address', 'physical address'],
    'city': ['city', 'town', 'municipality', 'city/town'],
    'state': ['state', 'province', 'region', 'territory'],
    'zip_code': ['zip code', 'postal code', 'zip', 'postcode', 'pin code', 'pin'],
    'country': ['country', 'nation'],
    'is_active': ['is active', 'active', 'enabled', 'status', 'state', 'active status'],
    'credit_limit': ['credit limit', 'credit line', 'credit amount', 'limit', 'max credit'],
    'account_status': ['account status', 'status', 'account type', 'customer status'],
    'reference_number': ['reference number', 'reference', 'ref no', 'ref number', 'transaction ref'],
    'invoice_number': ['invoice number', 'invoice no', 'invoice#', 'invoice #', 'bill number',
                       'bill no', 'receipt number', 'receipt no'],
    'due_date': ['due date', 'payment due', 'due on', 'net due', 'credit term end'],
    'payment_status': ['payment status', 'paid status', 'status', 'invoice status', 'settlement status'],
    'employee_id': ['employee id', 'employee', 'emp id', 'emp code', 'staff id', 'operator id'],
    'employee_name': ['employee name', 'staff name', 'employee', 'operator name', 'full name'],
    'supplier_code': ['supplier code', 'vendor code', 'supplier id', 'vendor id'],
    'customer_code': ['customer code', 'customer id', 'client code', 'client id'],
    'unit': ['unit', 'uom', 'unit of measure', 'measure', 'measurement unit', 'uom code'],
    'tax_rate': ['tax rate', 'tax %', 'vat', 'gst', 'sales tax', 'tax percentage'],
    'tax_amount': ['tax amount', 'tax', 'vat amount', 'gst amount', 'sales tax amount'],
    'discount_amount': ['discount amount', 'discount', 'discount total', 'total discount'],
    'subtotal': ['subtotal', 'sub total', 'sub-total', 'net amount', 'taxable amount'],
    'grand_total': ['grand total', 'total', 'total amount', 'invoice total', 'net total'],
    'created_at': ['created at', 'created date', 'date created', 'created on', 'created', 'created_date'],
    'updated_at': ['updated at', 'updated date', 'last updated', 'modified', 'updated_on'],
    'customer_name': ['customer name', 'customer', 'client name', 'buyer name', 'guest name'],
    'customer_email': ['customer email', 'email', 'customer email address'],
    'customer_phone': ['customer phone', 'phone', 'customer phone number', 'customer mobile'],
    'supplier_name': ['supplier name', 'supplier', 'vendor name', 'vendor'],
    'supplier_email': ['supplier email', 'supplier email address', 'vendor email'],
    'supplier_phone': ['supplier phone', 'supplier telephone', 'vendor phone'],
    'product_code': ['product code', 'product number', 'article code', 'item code'],
    'warehouse': ['warehouse', 'location', 'store', 'branch', 'outlet'],
    'batch_number': ['batch number', 'batch no', 'batch', 'lot number', 'lot'],
    'expiry_date': ['expiry date', 'expiration date', 'expires', 'expiry', 'best before'],
    'unit_price': ['unit price', 'price per unit', 'unit rate', 'rate per unit'],
}

_suggestions_cache = {}


def _normalize(name):
    n = name.strip().lower()
    n = re.sub(r'[_\-\/#]', ' ', n)
    n = re.sub(r'\s+', ' ', n)
    return n.strip()


def _build_reverse_index():
    index = {}
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            norm = _normalize(alias)
            if norm not in index:
                index[norm] = field
        norm_field = _normalize(field)
        if norm_field not in index:
            index[norm_field] = field
    return index


REVERSE_INDEX = _build_reverse_index()


def match_field(column_name):
    norm = _normalize(column_name)
    if norm in REVERSE_INDEX:
        return REVERSE_INDEX[norm]
    compact = re.sub(r'[^a-zA-Z0-9]', '', norm)
    for alias_norm, field in REVERSE_INDEX.items():
        alias_compact = re.sub(r'[^a-zA-Z0-9]', '', alias_norm)
        if compact == alias_compact:
            return field
    return None


def detect_fields(columns, target_fields):
    mapping = {}
    for col in columns:
        matched = match_field(col)
        if matched and matched in target_fields and matched not in mapping:
            mapping[matched] = col
    return mapping


def suggest_mapping(columns, all_possible_fields):
    suggestions = {}
    for col in columns:
        matched = match_field(col)
        if matched:
            suggestions[col] = matched
    return suggestions
