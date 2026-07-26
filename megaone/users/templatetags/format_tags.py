from django import template
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

register = template.Library()


@register.simple_tag(takes_context=True)
def format_currency(context, value, decimals=2):
    try:
        symbol = context.get('currency_symbol', 'Rs ')
    except Exception:
        symbol = 'Rs '
    try:
        if value is None:
            value = 0
        if isinstance(value, str):
            value = value.replace(',', '')
        v = Decimal(str(value)).quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)
        formatted = f"{v:,.{decimals}f}"
        return f"{symbol}{formatted}"
    except (ValueError, TypeError, InvalidOperation):
        try:
            return f"{symbol}{float(value or 0):,.{decimals}f}"
        except Exception:
            return str(value) if value else f"{symbol}0"


@register.filter
def format_number(value, decimals=2):
    try:
        if value is None:
            return '0'
        if isinstance(value, str):
            value = value.replace(',', '')
        v = Decimal(str(value)).quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)
        return f"{v:,.{decimals}f}"
    except (ValueError, TypeError, InvalidOperation):
        try:
            return f"{float(value or 0):,.{decimals}f}"
        except Exception:
            return str(value) if value else '0'


@register.filter
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


@register.filter
def thousand_separator(value, decimals=2):
    return format_number(value, decimals)


@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.simple_tag(takes_context=True)
def currency(context, value, decimals=2):
    return format_currency(context, value, decimals)
