from django import template
from .format_tags import register

from .format_tags import format_currency, format_number, title_case, thousand_separator, currency

__all__ = ['format_currency', 'format_number', 'title_case', 'thousand_separator', 'currency']
