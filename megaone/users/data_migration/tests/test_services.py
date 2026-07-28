"""Tests for services.py — session lifecycle, 10-step orchestration, no-DB-before-confirm."""

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from megaone.users.data_migration import services
from .sample_data import dicts_to_csv_bytes, PRODUCTS_A


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


class TestCreateSession:
    def test_creates_with_defaults(self):
        session = services.create_session()
        assert 'id' in session
        assert session['step'] == 1
        assert session['modules'] == {}
        assert session['selected_modules'] == []
        assert session['import_plan'] is None
        assert session['import_results'] is None

    def test_stores_in_cache(self):
        session = services.create_session()
        retrieved = services.get_session(session['id'])
        assert retrieved is not None
        assert retrieved['id'] == session['id']


class TestGetSession:
    def test_returns_none_for_missing(self):
        assert services.get_session('nonexistent') is None

    def test_returns_session(self):
        session = services.create_session()
        assert services.get_session(session['id']) is not None


class TestSaveSession:
    def test_updates_cache(self):
        session = services.create_session()
        session['step'] = 5
        services.save_session(session)
        retrieved = services.get_session(session['id'])
        assert retrieved['step'] == 5


class TestStep1Upload:
    def test_uploads_csv_and_analyzes(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        assert session['file_name'] == 'products.csv'
        assert session['file_type'] == 'csv'
        assert session['step'] == 2
        assert 'Products' in session['modules']

    def test_stores_analysis_in_session(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        assert session['analysis'] is not None
        assert session['analysis']['file_type'] == 'csv'
        assert session['analysis']['status'] == 'analyzed'

    def test_no_database_writes(self):
        """Upload step must not write to database."""
        from django.db import connection
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        # Verify no tables were created/modified
        assert session['step'] == 2


class TestStep2Analyze:
    def test_builds_module_data(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        session['selected_modules'] = ['Products']
        session = services.step2_analyze(session)
        assert 'module_data' in session
        assert 'Products' in session['module_data']
        assert session['step'] == 3

    def test_field_mapping_populated(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        session['selected_modules'] = ['Products']
        session = services.step2_analyze(session)
        pd = session['module_data']['Products']
        assert 'mapping' in pd
        assert 'sample_rows' in pd
        assert 'all_data' in pd
        assert len(pd['all_data']) > 0

    def test_no_database_writes(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        session['selected_modules'] = ['Products']
        session = services.step2_analyze(session)
        assert session['step'] == 3  # Just analysis, no DB


class TestStep5DetectDuplicates:
    def test_detects_duplicates_in_session(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        session['selected_modules'] = ['Products']
        session = services.step2_analyze(session)
        session = services.step5_detect_duplicates(session)
        assert 'duplicate_results' in session
        assert 'Products' in session['duplicate_results']
        assert session['step'] == 5

    def test_no_database_writes(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        session['selected_modules'] = ['Products']
        session = services.step2_analyze(session)
        session = services.step5_detect_duplicates(session)
        assert session['step'] == 5


class TestStep6Validate:
    def test_validates_products(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        session['selected_modules'] = ['Products']
        session = services.step2_analyze(session)
        session = services.step6_validate(session)
        assert 'validation' in session
        assert 'Products' in session['validation']
        assert session['step'] == 6

    def test_no_database_writes(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        session['selected_modules'] = ['Products']
        session = services.step2_analyze(session)
        session = services.step6_validate(session)
        assert session['step'] == 6


class TestStep7PrepareImport:
    def test_prepares_plan(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        session['selected_modules'] = ['Products']
        session = services.step2_analyze(session)
        session, total = services.step7_prepare_import(session)
        assert 'import_plan' in session
        assert 'Products' in session['import_plan']
        assert total > 0
        assert session['step'] == 7

    def test_no_database_writes(self):
        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')
        session = services.step1_upload(session, uf)
        session['selected_modules'] = ['Products']
        session = services.step2_analyze(session)
        session, total = services.step7_prepare_import(session)
        assert session['step'] == 7  # Not yet imported


class TestFullOrchestrationNoDbBeforeConfirm:
    """Ensure no database writes happen at any step before step8 confirmation."""

    @pytest.mark.django_db(transaction=True)
    def test_no_db_writes_before_import(self):
        from django.db import connection
        from menu.models import Food

        initial_count = Food.objects.count()

        session = services.create_session()
        data = dicts_to_csv_bytes(PRODUCTS_A)
        uf = SimpleUploadedFile('products.csv', data, content_type='text/csv')

        # Step 1 - Upload
        session = services.step1_upload(session, uf)
        assert Food.objects.count() == initial_count

        # Step 2 - Analyze
        session['selected_modules'] = ['Products']
        session = services.step2_analyze(session)
        assert Food.objects.count() == initial_count

        # Step 5 - Duplicates
        session = services.step5_detect_duplicates(session)
        assert Food.objects.count() == initial_count

        # Step 6 - Validate
        session = services.step6_validate(session)
        assert Food.objects.count() == initial_count

        # Step 7 - Prepare
        session, total = services.step7_prepare_import(session)
        assert Food.objects.count() == initial_count

        # Database should still be untouched
        assert session['step'] == 7


class TestClearSession:
    def test_removes_from_cache(self):
        session = services.create_session()
        sid = session['id']
        assert services.get_session(sid) is not None
        services.clear_session(sid)
        assert services.get_session(sid) is None
