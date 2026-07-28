import json
import csv
import io
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.conf import settings

from megaone.users.permissions import software_owner_required
from . import services


@login_required
@software_owner_required
def dashboard(request):
    return render(request, 'users/data_migration/dashboard.html', {
        'title': 'Data Migration',
        'modules': services.get_migration_modules(),
    })


@login_required
@software_owner_required
def start_migration(request):
    session = services.create_session()
    return redirect('users:data_migration:step1_upload', session_id=session['id'])


@login_required
@software_owner_required
def step1_upload(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return redirect('users:data_migration:dashboard')

    if request.method == 'POST':
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return render(request, 'users/data_migration/step1_upload.html', {
                'session': session,
                'error': 'Please select a file to upload.',
            })
        session = services.step1_upload(session, uploaded_file)
        return redirect('users:data_migration:step2_analyze', session_id=session_id)

    return render(request, 'users/data_migration/step1_upload.html', {
        'session': session,
    })


@login_required
@software_owner_required
def step2_analyze(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return redirect('users:data_migration:dashboard')

    if request.method == 'POST':
        selected = request.POST.getlist('modules')
        session['selected_modules'] = selected
        services.save_session(session)
        session = services.step2_analyze(session)
        return redirect('users:data_migration:step3_summary', session_id=session_id)

    analysis = session.get('analysis', {})
    modules = session.get('modules', {})
    return render(request, 'users/data_migration/step2_analyze.html', {
        'session': session,
        'analysis': analysis,
        'detected_modules': modules,
        'all_modules': services.get_migration_modules(),
    })


@login_required
@software_owner_required
def step3_summary(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return redirect('users:data_migration:dashboard')

    if request.method == 'POST':
        return redirect('users:data_migration:select_modules', session_id=session_id)

    modules = session.get('modules', {})
    selected = session.get('selected_modules', list(modules.keys()))
    total_records = session.get('analysis', {}).get('total_records', 0)
    total_modules = len(modules)
    total_warnings = sum(len(m.get('warnings', [])) for m in modules.values())

    return render(request, 'users/data_migration/step3_summary.html', {
        'session': session,
        'modules': modules,
        'selected': selected,
        'total_records': total_records,
        'total_modules': total_modules,
        'total_warnings': total_warnings,
    })


@login_required
@software_owner_required
def select_modules(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return redirect('users:data_migration:dashboard')

    if request.method == 'POST':
        selected = request.POST.getlist('modules')
        session['selected_modules'] = selected
        services.save_session(session)
        return redirect('users:data_migration:step7_confirm', session_id=session_id)

    modules = session.get('modules', {})
    selected = session.get('selected_modules', list(modules.keys()))
    return render(request, 'users/data_migration/select_modules.html', {
        'session': session,
        'modules': modules,
        'selected': selected,
    })


@login_required
@software_owner_required
def step4_preview(request, session_id, module):
    session = services.get_session(session_id)
    if not session:
        return redirect('users:data_migration:dashboard')

    data = services.step4_get_preview(session, module)
    fields = services.MODULE_FIELDS.get(module, [])
    mapping = data.get('mapping', {})
    all_data = data.get('all_data', [])

    display_rows = []
    for row in all_data:
        display_row = {}
        for field in fields:
            source_col = mapping.get(field)
            if source_col and source_col in row:
                display_row[field] = row[source_col]
            else:
                display_row[field] = None
        display_rows.append(display_row)

    page = int(request.GET.get('page', 1))
    per_page = 25
    total_pages = max(1, (len(display_rows) + per_page - 1) // per_page)
    page_data = display_rows[(page - 1) * per_page: page * per_page]

    query = request.GET.get('q', '').strip().lower()
    if query:
        filtered = []
        for r in display_rows:
            if any(query in str(v).lower() for v in r.values()):
                filtered.append(r)
        total_pages = max(1, (len(filtered) + per_page - 1) // per_page)
        page_data = filtered[(page - 1) * per_page: page * per_page]
    else:
        page_data = display_rows[(page - 1) * per_page: page * per_page]

    return render(request, 'users/data_migration/step4_preview.html', {
        'session': session,
        'module': module,
        'fields': fields,
        'mapping': mapping,
        'page_data': page_data,
        'page': page,
        'total_pages': total_pages,
        'total_records': len(display_rows),
        'query': query,
    })


@login_required
@software_owner_required
def update_mapping(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return JsonResponse({'error': 'Session not found'}, status=404)

    if request.method == 'POST':
        data = json.loads(request.body)
        module = data.get('module')
        mapping = data.get('mapping', {})
        if module and module in session.get('module_data', {}):
            session['module_data'][module]['mapping'] = mapping
            services.save_session(session)
            return JsonResponse({'success': True})
    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
@software_owner_required
def step5_duplicates(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return redirect('users:data_migration:dashboard')

    dup_results = session.get('duplicate_results', {})
    if not dup_results:
        session = services.step5_detect_duplicates(session)
        dup_results = session.get('duplicate_results', {})

    if request.method == 'POST':
        dup_actions = {}
        for module in session.get('selected_modules', []):
            action = request.POST.get(f'dup_action_{module}', 'create_new')
            dup_actions[module] = action
        session['dup_actions'] = dup_actions
        services.save_session(session)
        return redirect('users:data_migration:step6_validate', session_id=session_id)

    return render(request, 'users/data_migration/step5_duplicates.html', {
        'session': session,
        'dup_results': dup_results,
        'dup_strategies': ['create_new', 'update_existing', 'skip', 'merge'],
    })


@login_required
@software_owner_required
def step6_validate(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return redirect('users:data_migration:dashboard')

    validation = session.get('validation', {})
    if not validation:
        session = services.step6_validate(session)
        validation = session.get('validation', {})

    if request.method == 'POST':
        return redirect('users:data_migration:step7_confirm', session_id=session_id)

    return render(request, 'users/data_migration/step6_validation.html', {
        'session': session,
        'validation': validation,
    })


@login_required
@software_owner_required
def step7_confirm(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return redirect('users:data_migration:dashboard')

    import logging
    logger = logging.getLogger(__name__)
    logger.info('[MIGRATION] Confirm Import page displayed')

    dup_actions = session.get('dup_actions', {})
    for module in session.get('selected_modules', []):
        if module not in dup_actions:
            dup_actions[module] = 'create_new'
    session['dup_actions'] = dup_actions
    session, total = services.step7_prepare_import(session, dup_actions)

    module_counts = {}
    module_data_list = []
    for module, config in session.get('import_plan', {}).items():
        count = len(config['rows'])
        module_counts[module] = count
        module_data_list.append({
            'module': module,
            'count': count,
            'dup_action': dup_actions.get(module, 'create_new'),
        })

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'import_all':
            return redirect('users:data_migration:step8_import', session_id=session_id)
        elif action == 'select_modules':
            return redirect('users:data_migration:select_modules', session_id=session_id)
        return redirect('users:data_migration:dashboard')

    return render(request, 'users/data_migration/step7_confirm.html', {
        'session': session,
        'module_counts': module_counts,
        'module_data_list': module_data_list,
        'total': total,
    })


@login_required
@software_owner_required
def step8_import(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return redirect('users:data_migration:dashboard')

    return render(request, 'users/data_migration/step8_progress.html', {
        'session': session,
    })


@login_required
@software_owner_required
def import_progress(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return JsonResponse({'error': 'Session not found'}, status=404)

    if request.method == 'POST':
        import logging
        logger = logging.getLogger(__name__)

        results = session.get('import_results')
        if not results:
            logger.info('[MIGRATION] Starting import job')
            modules = list(session.get('import_plan', {}).keys())
            logger.info('[MIGRATION] Selected modules: %s', modules)
            session, results = services.step8_execute_import(session, user=request.user)
            logger.info('[MIGRATION] Import completed: %d imported, %d failed',
                        results.get('imported', 0), results.get('failed', 0))
        else:
            logger.info('[MIGRATION] Import already completed, returning cached results')

        response_data = {
            'completed': True,
            'progress': 100,
            'imported': results.get('imported', 0),
            'updated': results.get('updated', 0),
            'skipped': results.get('skipped', 0),
            'failed': results.get('failed', 0),
            'total': results.get('total', 0),
            'current_module': '',
            'results': results,
        }
        return JsonResponse(response_data)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
@software_owner_required
def step9_report(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return redirect('users:data_migration:dashboard')

    results = session.get('import_results', {})
    return render(request, 'users/data_migration/step9_report.html', {
        'session': session,
        'results': results,
    })


@login_required
@software_owner_required
def clear_session(request, session_id):
    services.clear_session(session_id)
    return redirect('users:data_migration:dashboard')


@login_required
@software_owner_required
def download_report(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return HttpResponse('Session not found', status=404)

    results = session.get('import_results', {})
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="migration_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Module', 'Imported', 'Updated', 'Skipped', 'Merged', 'Failed', 'Total'])
    for module, mod_res in results.get('modules', {}).items():
        writer.writerow([
            module,
            mod_res.get('imported', 0),
            mod_res.get('updated', 0),
            mod_res.get('skipped', 0),
            mod_res.get('merged', 0),
            mod_res.get('failed', 0),
            mod_res.get('total', 0),
        ])
    writer.writerow([])
    writer.writerow(['Total', results.get('imported', 0), results.get('updated', 0),
                     results.get('skipped', 0), results.get('merged', 0),
                     results.get('failed', 0), results.get('total', 0)])
    writer.writerow([])
    writer.writerow(['Elapsed', results.get('elapsed_formatted', '')])
    return response


@login_required
@software_owner_required
def download_errors(request, session_id):
    session = services.get_session(session_id)
    if not session:
        return HttpResponse('Session not found', status=404)

    results = session.get('import_results', {})
    errors = results.get('errors', [])
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="migration_errors.csv"'
    writer = csv.writer(response)
    writer.writerow(['Error'])
    for err in errors:
        writer.writerow([err])
    return response
