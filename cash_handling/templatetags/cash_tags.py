from django import template

register = template.Library()


@register.filter
def split(value, delimiter):
    return value.split(delimiter)


@register.filter
def get_count(existing_counts, value):
    if existing_counts:
        for c in existing_counts:
            if str(c.denomination_value) == str(value):
                return c.count
    return 0
