from decimal import Decimal, ROUND_HALF_UP


def get_currency_config():
    try:
        from .models import SystemSetting
        settings = SystemSetting.objects.filter(pk=1).first()
        if settings:
            return {
                'symbol': settings.currency_symbol,
                'code': settings.currency_code,
            }
    except Exception:
        pass
    return {'symbol': 'Rs', 'code': 'PKR'}


def format_currency(value, decimals=2):
    config = get_currency_config()
    try:
        if isinstance(value, str):
            value = value.replace(',', '')
        v = Decimal(str(value)).quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)
        formatted = f"{v:,.{decimals}f}"
        return f"{config['symbol']}{formatted}"
    except (ValueError, TypeError, InvalidOperation):
        return str(value) if value else '0'


def format_number(value, decimals=2):
    try:
        if isinstance(value, str):
            value = value.replace(',', '')
        v = Decimal(str(value)).quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)
        return f"{v:,.{decimals}f}"
    except (ValueError, TypeError, InvalidOperation):
        return str(value) if value else '0'


def title_case(value):
    if not value or not isinstance(value, str):
        return value
    exceptions = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'by', 'with'}
    words = value.split()
    result = []
    for i, word in enumerate(words):
        if not word:
            continue
        if i > 0 and word.lower() in exceptions:
            result.append(word.lower())
        else:
            result.append(word[0].upper() + word[1:].lower())
    return ' '.join(result)
