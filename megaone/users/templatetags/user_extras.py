from django import template

register = template.Library()


@register.filter
def get_attr(obj, attr):
    return getattr(obj, attr, False)


@register.filter
def perm_label(field_name):
    return field_name.replace('can_', '').replace('_', ' ').strip().title()
