import json
from decimal import Decimal
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction as db_transaction
from django.db.models import Sum, Q
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator

from megaone.users.permissions import operator_permission_required, has_permission, module_access_required
from megaone.users.models import AuditLog
from .models import CashDrawerSession, CashTransaction, DenominationCount, CashApproval, NoSaleTransaction
from .services import CashDrawerService, CashDrawerError


def _is_cash_handling_enabled():
    try:
        from megaone.users.models import SystemSetting
        s = SystemSetting.objects.filter(pk=1).first()
        if s:
            return 'cash_handling' in (s.enabled_modules or [])
    except Exception:
        pass
    return False


def cash_handling_enabled_required(view_func):
    from functools import wraps
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not _is_cash_handling_enabled():
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"error": "Cash Handling module is disabled"}, status=403)
            messages.error(request, "Cash Handling module is disabled.")
            return redirect('users:admin_dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped


def _get_session_context(session):
    if not session:
        return None
    return {
        'id': session.id,
        'opened_at': session.opened_at,
        'closed_at': session.closed_at,
        'status': session.status,
        'opening_balance': float(session.opening_balance),
        'current_balance': float(CashDrawerService.get_session_balance(session)),
        'expected_closing': float(session.expected_closing) if session.expected_closing else 0,
        'closing_balance': float(session.closing_balance) if session.closing_balance else 0,
        'cash_sales': float(CashDrawerService.get_session_cash_sales(session)),
        'cash_refunds': float(CashDrawerService.get_session_cash_refunds(session)),
        'cash_drops': float(CashDrawerService.get_session_drops(session)),
        'cash_in': float(CashDrawerService.get_session_cash_in(session)),
        'cash_out': float(CashDrawerService.get_session_cash_out(session)),
    }


# =========================
# DASHBOARD
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_dashboard_view')
@cash_handling_enabled_required
def dashboard(request):
    session = CashDrawerService.get_active_session(request.user)
    session_data = _get_session_context(session)
    recent_txns = CashTransaction.objects.none()
    if session:
        recent_txns = CashTransaction.objects.filter(session=session).order_by('-created_at')[:10]
    open_sessions_count = CashDrawerSession.objects.filter(status='open').count()
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_cash_sales = CashTransaction.objects.filter(
        transaction_type='sale', created_at__gte=today_start
    ).aggregate(total=Sum('amount'))['total'] or 0
    pending_approvals = CashApproval.objects.filter(status='pending').count()

    context = {
        'active_page': 'cash_dashboard',
        'session': session,
        'session_data': session_data,
        'recent_txns': recent_txns,
        'open_sessions_count': open_sessions_count,
        'today_cash_sales': float(today_cash_sales),
        'pending_approvals': pending_approvals,
    }
    return render(request, 'cash_handling/dashboard.html', context)


# =========================
# CASH DRAWERS
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_drawer_view')
@cash_handling_enabled_required
def cash_drawers(request):
    sessions = CashDrawerSession.objects.select_related('user', 'closed_by').all().order_by('-opened_at')[:50]
    can_force_close = has_permission(request.user, 'cash_session_force_close')
    can_reopen = has_permission(request.user, 'cash_session_reopen')
    context = {
        'active_page': 'cash_drawers',
        'sessions': sessions,
        'can_force_close': can_force_close,
        'can_reopen': can_reopen,
    }
    return render(request, 'cash_handling/cash_drawers.html', context)


# =========================
# SESSION MANAGEMENT (API + Pages)
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_session_open')
@cash_handling_enabled_required
def session_open_page(request):
    return render(request, 'cash_handling/session_open.html', {
        'active_page': 'cash_sessions',
        'existing_session': CashDrawerService.get_active_session(request.user),
    })


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_session_close')
@cash_handling_enabled_required
def session_close_page(request):
    session = CashDrawerService.get_active_session(request.user)
    if not session:
        messages.error(request, "No open session found.")
        return redirect('cash_handling:session_open_page')
    context = {
        'active_page': 'cash_sessions',
        'session': session,
        'session_data': _get_session_context(session),
    }
    return render(request, 'cash_handling/session_close.html', context)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_session_open')
@cash_handling_enabled_required
@require_POST
def session_open(request):
    try:
        data = json.loads(request.body)
        opening_balance = Decimal(str(data.get('opening_balance', 0)))
        notes = data.get('notes', '')
        session = CashDrawerService.open_session(
            user=request.user,
            opening_balance=opening_balance,
            notes=notes,
        )
        AuditLog.objects.create(
            user=request.user,
            action='session_open',
            description=f"Opened cash session #{session.id} with opening balance {opening_balance}",
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'message': 'Session opened successfully',
        })
    except CashDrawerError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_session_close')
@cash_handling_enabled_required
@require_POST
def session_close(request):
    try:
        data = json.loads(request.body)
        session = CashDrawerService.get_active_session(request.user)
        if not session:
            return JsonResponse({'error': 'No open session found'}, status=400)
        closing_balance = data.get('closing_balance')
        if closing_balance is not None:
            closing_balance = Decimal(str(closing_balance))
        notes = data.get('notes', '')
        session = CashDrawerService.close_session(
            session=session,
            user=request.user,
            closing_balance=closing_balance,
            notes=notes,
        )
        AuditLog.objects.create(
            user=request.user,
            action='session_close',
            description=f"Closed cash session #{session.id}. Expected: {session.expected_closing}, Actual: {session.closing_balance}, Variance: {session.closing_balance - session.expected_closing if session.closing_balance is not None and session.expected_closing is not None else 0}",
            ip_address=request.META.get('REMOTE_ADDR'),
        )
        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'expected_closing': float(session.expected_closing),
            'closing_balance': float(session.closing_balance),
            'variance': float(session.closing_balance - session.expected_closing) if session.closing_balance is not None and session.expected_closing is not None else 0,
            'message': 'Session closed successfully',
        })
    except CashDrawerError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@module_access_required('cash_handling')
@cash_handling_enabled_required
def session_status(request):
    session = CashDrawerService.get_active_session(request.user)
    if not session:
        return JsonResponse({'has_active_session': False})
    balance = float(CashDrawerService.get_session_balance(session))
    return JsonResponse({
        'has_active_session': True,
        'session_id': session.id,
        'opened_at': session.opened_at.isoformat(),
        'opening_balance': float(session.opening_balance),
        'current_balance': balance,
    })


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_session_view')
@cash_handling_enabled_required
def session_detail(request, session_id):
    session = get_object_or_404(CashDrawerSession, id=session_id)
    if session.user != request.user and not has_permission(request.user, 'cash_session_view_all'):
        return JsonResponse({'error': 'Access denied'}, status=403)
    balance = float(CashDrawerService.get_session_balance(session))
    return JsonResponse({
        'id': session.id,
        'user_email': session.user.email,
        'user_name': session.user.name or session.user.email,
        'opened_at': session.opened_at.isoformat(),
        'closed_at': session.closed_at.isoformat() if session.closed_at else None,
        'status': session.status,
        'opening_balance': float(session.opening_balance),
        'current_balance': balance,
        'expected_closing': float(session.expected_closing) if session.expected_closing else None,
        'closing_balance': float(session.closing_balance) if session.closing_balance else None,
    })


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_session_force_close')
@cash_handling_enabled_required
@require_POST
def session_force_close(request, session_id):
    try:
        session = get_object_or_404(CashDrawerSession, id=session_id, status='open')
        data = json.loads(request.body) if request.body else {}
        notes = data.get('notes', '')

        session = CashDrawerService.close_session(
            session=session,
            user=request.user,
            closing_balance=data.get('closing_balance'),
            notes=notes,
        )

        AuditLog.objects.create(
            user=request.user,
            action='session_force_close',
            description=f"Force closed session #{session.id} (user: {session.user.email})",
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'message': f'Session #{session.id} force closed successfully',
        })
    except CashDrawerError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_session_reopen')
@cash_handling_enabled_required
@require_POST
def session_reopen(request, session_id):
    try:
        session = get_object_or_404(CashDrawerSession, id=session_id, status='closed')
        data = json.loads(request.body) if request.body else {}
        notes = data.get('notes', '')

        session.status = 'open'
        session.closed_at = None
        session.closed_by = None
        session.closing_balance = None
        session.expected_closing = None
        session.notes = (session.notes + '\n' + notes).strip() if notes else session.notes
        session.save()

        AuditLog.objects.create(
            user=request.user,
            action='session_reopen',
            description=f"Reopened session #{session.id} (user: {session.user.email})",
            ip_address=request.META.get('REMOTE_ADDR'),
        )

        return JsonResponse({
            'success': True,
            'session_id': session.id,
            'message': f'Session #{session.id} reopened successfully',
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@module_access_required('pos')
def pos_session_status(request):
    session = CashDrawerService.get_active_session(request.user)
    if not session:
        return JsonResponse({'has_active_session': False})
    balance = float(CashDrawerService.get_session_balance(session))
    return JsonResponse({
        'has_active_session': True,
        'session_id': session.id,
        'opened_at': session.opened_at.isoformat(),
        'opening_balance': float(session.opening_balance),
        'current_balance': balance,
        'operator_name': session.user.get_full_name() or session.user.email,
    })


# =========================
# CASH IN / OUT / DROP (Pages + API)
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_in')
@cash_handling_enabled_required
def cash_in_page(request):
    session = CashDrawerService.get_active_session(request.user)
    context = {
        'active_page': 'cash_in',
        'session': session,
        'session_data': _get_session_context(session),
    }
    return render(request, 'cash_handling/cash_in.html', context)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_out')
@cash_handling_enabled_required
def cash_out_page(request):
    session = CashDrawerService.get_active_session(request.user)
    context = {
        'active_page': 'cash_out',
        'session': session,
        'session_data': _get_session_context(session),
    }
    return render(request, 'cash_handling/cash_out.html', context)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_drop')
@cash_handling_enabled_required
def cash_drop_page(request):
    session = CashDrawerService.get_active_session(request.user)
    context = {
        'active_page': 'cash_drop',
        'session': session,
        'session_data': _get_session_context(session),
    }
    return render(request, 'cash_handling/cash_drop.html', context)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_in')
@cash_handling_enabled_required
@require_POST
def cash_in(request):
    try:
        data = json.loads(request.body)
        amount = Decimal(str(data.get('amount', 0)))
        reason = data.get('reason', '')
        if amount <= 0:
            return JsonResponse({'error': 'Amount must be positive'}, status=400)
        session = CashDrawerService.get_active_session(request.user)
        if not session:
            return JsonResponse({'error': 'No open session. Please open a drawer session first.'}, status=400)
        txn = CashDrawerService.record_cash_in(
            session=session, user=request.user, amount=amount, reason=reason,
        )
        return JsonResponse({
            'success': True, 'transaction_id': txn.id,
            'balance_before': float(txn.balance_before), 'balance_after': float(txn.balance_after),
            'message': 'Cash added successfully',
        })
    except CashDrawerError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_out')
@cash_handling_enabled_required
@require_POST
def cash_out(request):
    try:
        data = json.loads(request.body)
        amount = Decimal(str(data.get('amount', 0)))
        reason = data.get('reason', '')
        if amount <= 0:
            return JsonResponse({'error': 'Amount must be positive'}, status=400)
        session = CashDrawerService.get_active_session(request.user)
        if not session:
            return JsonResponse({'error': 'No open session. Please open a drawer session first.'}, status=400)
        txn = CashDrawerService.record_cash_out(
            session=session, user=request.user, amount=amount, reason=reason,
        )
        return JsonResponse({
            'success': True, 'transaction_id': txn.id,
            'balance_before': float(txn.balance_before), 'balance_after': float(txn.balance_after),
            'message': 'Cash removed successfully',
        })
    except CashDrawerError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_drop')
@cash_handling_enabled_required
@require_POST
def cash_drop(request):
    try:
        data = json.loads(request.body)
        amount = Decimal(str(data.get('amount', 0)))
        reason = data.get('reason', '')
        if amount <= 0:
            return JsonResponse({'error': 'Amount must be positive'}, status=400)
        session = CashDrawerService.get_active_session(request.user)
        if not session:
            return JsonResponse({'error': 'No open session. Please open a drawer session first.'}, status=400)
        txn = CashDrawerService.record_drop(
            session=session, user=request.user, amount=amount, reason=reason,
        )
        return JsonResponse({
            'success': True, 'transaction_id': txn.id,
            'balance_before': float(txn.balance_before), 'balance_after': float(txn.balance_after),
            'message': 'Cash drop recorded successfully',
        })
    except CashDrawerError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =========================
# NO SALE
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_no_sale')
@cash_handling_enabled_required
def no_sale_page(request):
    session = CashDrawerService.get_active_session(request.user)
    context = {
        'active_page': 'cash_no_sale',
        'session': session,
    }
    return render(request, 'cash_handling/no_sale.html', context)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_no_sale')
@cash_handling_enabled_required
@require_POST
def no_sale(request):
    try:
        data = json.loads(request.body)
        reason = data.get('reason', '')
        session = CashDrawerService.get_active_session(request.user)
        if not session:
            return JsonResponse({'error': 'No open session'}, status=400)
        CashDrawerService.record_no_sale(session=session, user=request.user, reason=reason)
        NoSaleTransaction.objects.create(session=session, user=request.user, reason=reason)
        return JsonResponse({'success': True, 'message': 'No sale recorded'})
    except CashDrawerError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =========================
# DENOMINATION COUNT
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_session_close')
@cash_handling_enabled_required
def denomination_count_page(request):
    session = CashDrawerService.get_active_session(request.user)
    if not session:
        messages.error(request, "No open session.")
        return redirect('cash_handling:session_open_page')
    existing_counts = DenominationCount.objects.filter(session=session)
    context = {
        'active_page': 'cash_denomination',
        'session': session,
        'session_data': _get_session_context(session),
        'existing_counts': existing_counts,
    }
    return render(request, 'cash_handling/denomination_count.html', context)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_session_close')
@cash_handling_enabled_required
@require_POST
def denomination_count_save(request):
    try:
        data = json.loads(request.body)
        session = CashDrawerService.get_active_session(request.user)
        if not session:
            return JsonResponse({'error': 'No open session'}, status=400)
        denominations = data.get('denominations', [])
        DenominationCount.objects.filter(session=session).delete()
        total = Decimal('0')
        for d in denominations:
            value = Decimal(str(d.get('value', 0)))
            count = int(d.get('count', 0))
            if count > 0:
                subtotal = value * count
                DenominationCount.objects.create(
                    session=session, denomination_value=value,
                    count=count, subtotal=subtotal, created_by=request.user,
                )
                total += subtotal
        return JsonResponse({'success': True, 'total_counted': float(total), 'message': 'Denominations saved'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =========================
# CLOSING RECONCILIATION
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_session_close')
@cash_handling_enabled_required
def closing_reconciliation_page(request):
    session = CashDrawerService.get_active_session(request.user)
    if not session:
        messages.error(request, "No open session.")
        return redirect('cash_handling:session_open_page')
    denomination_counts = DenominationCount.objects.filter(session=session)
    counted_total = denomination_counts.aggregate(total=Sum('subtotal'))['total'] or Decimal('0')
    context = {
        'active_page': 'cash_reconciliation',
        'session': session,
        'session_data': _get_session_context(session),
        'denomination_counts': denomination_counts,
        'counted_total': float(counted_total),
    }
    return render(request, 'cash_handling/closing_reconciliation.html', context)


# =========================
# REFUNDS
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_refund_approve')
@cash_handling_enabled_required
def refunds(request):
    refund_txns = CashTransaction.objects.filter(transaction_type='refund').order_by('-created_at')
    pending_approvals = CashApproval.objects.filter(approval_type='refund', status='pending')
    context = {
        'active_page': 'cash_refunds',
        'refund_txns': refund_txns,
        'pending_approvals': pending_approvals,
    }
    return render(request, 'cash_handling/refunds.html', context)


# =========================
# VOID SALES
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_void_approve')
@cash_handling_enabled_required
def void_sales(request):
    void_txns = CashTransaction.objects.filter(transaction_type='void_sale').order_by('-created_at')
    pending_approvals = CashApproval.objects.filter(approval_type='void', status='pending')
    context = {
        'active_page': 'cash_voids',
        'void_txns': void_txns,
        'pending_approvals': pending_approvals,
    }
    return render(request, 'cash_handling/void_sales.html', context)


# =========================
# APPROVALS
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_override')
@cash_handling_enabled_required
def approvals(request):
    approvals_list = CashApproval.objects.all().order_by('-created_at')
    context = {
        'active_page': 'cash_approvals',
        'approvals': approvals_list,
    }
    return render(request, 'cash_handling/approvals.html', context)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_override')
@cash_handling_enabled_required
@require_POST
def approval_respond(request):
    try:
        data = json.loads(request.body)
        approval_id = data.get('approval_id')
        action = data.get('action', '')
        reason = data.get('reason', '')
        approval = get_object_or_404(CashApproval, id=approval_id, status='pending')
        if action == 'approve':
            approval.status = 'approved'
            approval.approved_by = request.user
            approval.save()
            session = approval.session
            if approval.approval_type == 'refund':
                CashDrawerService.record_refund(
                    session=session, user=request.user, amount=approval.amount,
                    reference_number=approval.reference_number,
                )
            elif approval.approval_type == 'void':
                CashDrawerService.record_void_sale(
                    session=session, user=request.user, amount=approval.amount,
                    reference_number=approval.reference_number,
                )
            return JsonResponse({'success': True, 'message': 'Approved'})
        elif action == 'reject':
            approval.status = 'rejected'
            approval.approved_by = request.user
            approval.rejection_reason = reason
            approval.save()
            return JsonResponse({'success': True, 'message': 'Rejected'})
        return JsonResponse({'error': 'Invalid action'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_override')
@cash_handling_enabled_required
@require_POST
def approval_request(request):
    try:
        data = json.loads(request.body)
        session = CashDrawerService.get_active_session(request.user)
        if not session:
            return JsonResponse({'error': 'No open session'}, status=400)
        approval = CashApproval.objects.create(
            session=session,
            approval_type=data.get('approval_type', 'override'),
            amount=Decimal(str(data.get('amount', 0))),
            reason=data.get('reason', ''),
            requested_by=request.user,
            reference_number=data.get('reference_number', ''),
        )
        return JsonResponse({'success': True, 'approval_id': approval.id, 'message': 'Approval requested'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# =========================
# TRANSACTION HISTORY
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_transaction_view')
@cash_handling_enabled_required
def transaction_list(request):
    can_view_all = (
        request.user.is_staff or
        request.user.is_software_owner or
        has_permission(request.user, 'cash_session_view_all')
    )
    if can_view_all:
        sessions = CashDrawerSession.objects.all().order_by('-opened_at')
    else:
        sessions = CashDrawerSession.objects.filter(user=request.user).order_by('-opened_at')

    selected_session_id = request.GET.get('session_id')
    if selected_session_id:
        if can_view_all:
            selected_session = get_object_or_404(CashDrawerSession, id=selected_session_id)
        else:
            selected_session = get_object_or_404(CashDrawerSession, id=selected_session_id, user=request.user)
    else:
        selected_session = sessions.first()

    transactions = CashTransaction.objects.none()
    session_data = None
    if selected_session:
        transactions = CashTransaction.objects.filter(session=selected_session).order_by('-created_at')
        session_data = _get_session_context(selected_session)

    context = {
        'active_page': 'cash_transactions',
        'sessions': sessions,
        'selected_session': selected_session,
        'session_data': session_data,
        'transactions': transactions,
        'can_view_all': can_view_all,
    }
    return render(request, 'cash_handling/transactions.html', context)


# =========================
# DASHBOARD DATA (API)
# =========================
@login_required
@module_access_required('cash_handling')
@cash_handling_enabled_required
def dashboard_data(request):
    session = CashDrawerService.get_active_session(request.user)
    if not session:
        return JsonResponse({'has_active_session': False, 'message': 'No active session'})
    balance = float(CashDrawerService.get_session_balance(session))
    return JsonResponse({
        'has_active_session': True,
        'session_id': session.id,
        'opened_at': session.opened_at.isoformat(),
        'opening_balance': float(session.opening_balance),
        'current_balance': balance,
        'expected_closing': balance,
        'cash_sales': float(CashDrawerService.get_session_cash_sales(session)),
        'cash_refunds': float(CashDrawerService.get_session_cash_refunds(session)),
        'cash_drops': float(CashDrawerService.get_session_drops(session)),
        'cash_in': float(CashDrawerService.get_session_cash_in(session)),
        'cash_out': float(CashDrawerService.get_session_cash_out(session)),
    })


# =========================
# SESSION HISTORY
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_report_view')
@cash_handling_enabled_required
def session_history(request):
    sessions_list = CashDrawerSession.objects.filter(user=request.user).order_by('-opened_at')
    paginator = Paginator(sessions_list, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    context = {
        'active_page': 'cash_sessions',
        'page_obj': page_obj, 'sessions': page_obj,
    }
    return render(request, 'cash_handling/session_history.html', context)


# =========================
# REPORTS
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_report_view')
@cash_handling_enabled_required
def reports(request):
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)
    total_sales = CashTransaction.objects.filter(transaction_type='sale').aggregate(total=Sum('amount'))['total'] or 0
    total_refunds = CashTransaction.objects.filter(transaction_type='refund').aggregate(total=Sum('amount'))['total'] or 0
    total_drops = CashTransaction.objects.filter(transaction_type='drop').aggregate(total=Sum('amount'))['total'] or 0
    today_sales = CashTransaction.objects.filter(transaction_type='sale', created_at__gte=today_start).aggregate(total=Sum('amount'))['total'] or 0
    today_refunds = CashTransaction.objects.filter(transaction_type='refund', created_at__gte=today_start).aggregate(total=Sum('amount'))['total'] or 0
    monthly_sales = CashTransaction.objects.filter(transaction_type='sale', created_at__gte=month_start).aggregate(total=Sum('amount'))['total'] or 0
    monthly_refunds = CashTransaction.objects.filter(transaction_type='refund', created_at__gte=month_start).aggregate(total=Sum('amount'))['total'] or 0
    sessions_count = CashDrawerSession.objects.count()
    open_sessions = CashDrawerSession.objects.filter(status='open').count()
    closed_sessions = CashDrawerSession.objects.filter(status='closed').count()

    context = {
        'active_page': 'cash_reports',
        'total_sales': float(total_sales),
        'total_refunds': float(total_refunds),
        'total_drops': float(total_drops),
        'today_sales': float(today_sales),
        'today_refunds': float(today_refunds),
        'monthly_sales': float(monthly_sales),
        'monthly_refunds': float(monthly_refunds),
        'sessions_count': sessions_count,
        'open_sessions': open_sessions,
        'closed_sessions': closed_sessions,
    }
    return render(request, 'cash_handling/reports.html', context)


# =========================
# AUDIT LOGS
# =========================
@login_required
@module_access_required('cash_handling')
@operator_permission_required('cash_report_view')
@cash_handling_enabled_required
def audit_logs(request):
    txns = CashTransaction.objects.all().select_related('user', 'session').order_by('-created_at')[:100]
    context = {
        'active_page': 'cash_audit',
        'transactions': txns,
    }
    return render(request, 'cash_handling/audit_logs.html', context)
