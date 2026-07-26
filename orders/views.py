from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from menu.models import Food
from .models import Order


@staff_member_required
def admin_dashboard(request):

    context = {
        "foods": Food.objects.count(),
        "orders": Order.objects.count(),
        "pending": Order.objects.filter(
            status="Pending"
        ).count(),
    }

    return render(
        request,
        "admin/dashboard.html",
        context
    )


from reportlab.pdfgen import canvas
from django.http import HttpResponse

def invoice_pdf(request, order_id):

    response = HttpResponse(
        content_type='application/pdf'
    )

    response[
        'Content-Disposition'
    ] = f'attachment; filename=invoice_{order_id}.pdf'

    p = canvas.Canvas(response)

    p.drawString(
        100,
        800,
        f"Invoice #{order_id}"
    )

    p.drawString(
        100,
        770,
        f"Customer: {request.user.email}"
    )

    p.save()

    return response