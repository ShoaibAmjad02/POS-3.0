from django.urls import path
from . import views

app_name = 'data_migration'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('start/', views.start_migration, name='start'),
    path('<uuid:session_id>/upload/', views.step1_upload, name='step1_upload'),
    path('<uuid:session_id>/analyze/', views.step2_analyze, name='step2_analyze'),
    path('<uuid:session_id>/summary/', views.step3_summary, name='step3_summary'),
    path('<uuid:session_id>/preview/<str:module>/', views.step4_preview, name='step4_preview'),
    path('<uuid:session_id>/duplicates/', views.step5_duplicates, name='step5_duplicates'),
    path('<uuid:session_id>/validate/', views.step6_validate, name='step6_validate'),
    path('<uuid:session_id>/confirm/', views.step7_confirm, name='step7_confirm'),
    path('<uuid:session_id>/import/', views.step8_import, name='step8_import'),
    path('<uuid:session_id>/progress/', views.import_progress, name='import_progress'),
    path('<uuid:session_id>/report/', views.step9_report, name='step9_report'),
    path('<uuid:session_id>/clear/', views.clear_session, name='clear'),
    path('<uuid:session_id>/select-modules/', views.select_modules, name='select_modules'),
    path('<uuid:session_id>/update-mapping/', views.update_mapping, name='update_mapping'),
    path('<uuid:session_id>/download-report/', views.download_report, name='download_report'),
    path('<uuid:session_id>/download-errors/', views.download_errors, name='download_errors'),
]
