import csv
from datetime import datetime, date
from decimal import Decimal
from django.http import HttpResponse


def _resolve_field(obj, accessor):
    parts = accessor.split('.')
    current = obj
    for part in parts:
        if current is None:
            return ''
        if hasattr(current, 'all'):
            try:
                related_qs = current.all()
                current = ', '.join(str(r) for r in related_qs) if related_qs else ''
                continue
            except Exception:
                pass
        if hasattr(current, part):
            current = getattr(current, part)
        elif isinstance(current, dict):
            current = current.get(part, '')
        else:
            try:
                current = current[part]
            except (TypeError, KeyError, IndexError):
                return ''
        if callable(current):
            try:
                current = current()
            except Exception:
                return ''
    if current is None:
        return ''
    if isinstance(current, (datetime, date)):
        return current.strftime('%Y-%m-%d %H:%M')
    if isinstance(current, Decimal):
        return float(current)
    if isinstance(current, bool):
        return 'Yes' if current else 'No'
    return str(current)


def export_to_csv_response(queryset, field_map, filename):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    headers = [label for _, label in field_map]
    writer.writerow(headers)
    for obj in queryset:
        row = []
        for accessor, _ in field_map:
            val = _resolve_field(obj, accessor)
            row.append(val)
        writer.writerow(row)
    return response
