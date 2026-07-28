"""Tests for views.py — HTTP flow, URL resolution, decorators."""

import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def software_owner(db):
    """Create a software owner user for testing."""
    user = User.objects.create_user(
        email='admin@test.com',
        name='Admin',
        password='testpass123',
        is_staff=True,
        is_superuser=True,
    )
    user.is_software_owner = True
    user.save()
    return user


@pytest.fixture
def regular_user(db):
    """Create a regular (non-software-owner) user."""
    user = User.objects.create_user(
        email='user@test.com',
        name='User',
        password='testpass123',
        is_staff=True,
    )
    user.is_software_owner = False
    user.save()
    return user


@pytest.fixture
def client():
    return Client()


class TestDashboard:
    @pytest.mark.django_db
    def test_dashboard_requires_login(self, client):
        url = reverse('users:data_migration:dashboard')
        response = client.get(url)
        assert response.status_code == 302

    def test_dashboard_allows_software_owner(self, client, software_owner):
        client.force_login(software_owner)
        url = reverse('users:data_migration:dashboard')
        response = client.get(url)
        assert response.status_code == 200
        assert 'Data Migration' in str(response.content)

    def test_dashboard_blocks_regular_user(self, client, regular_user):
        client.force_login(regular_user)
        url = reverse('users:data_migration:dashboard')
        response = client.get(url)
        assert response.status_code in (302, 403)

    def test_dashboard_lists_modules(self, client, software_owner):
        client.force_login(software_owner)
        url = reverse('users:data_migration:dashboard')
        response = client.get(url)
        content = str(response.content)
        assert 'Products' in content
        assert 'Customers' in content


class TestStartMigration:
    def test_start_creates_session_and_redirects(self, client, software_owner):
        client.force_login(software_owner)
        url = reverse('users:data_migration:start')
        response = client.post(url, follow=False)
        assert response.status_code == 302
        # Should redirect to step1_upload with a UUID
        assert '/upload/' in response.url or '/data-migration/' in response.url


class TestStep1Upload:
    def test_get_returns_form(self, client, software_owner):
        from megaone.users.data_migration import services
        session = services.create_session()
        client.force_login(software_owner)
        url = reverse('users:data_migration:step1_upload', args=[session['id']])
        response = client.get(url)
        assert response.status_code == 200

    def test_post_without_file_returns_error(self, client, software_owner):
        from megaone.users.data_migration import services
        session = services.create_session()
        client.force_login(software_owner)
        url = reverse('users:data_migration:step1_upload', args=[session['id']])
        response = client.post(url, {})
        assert response.status_code == 200
        assert 'Please select a file' in str(response.content)

    def test_post_with_csv_redirects_to_analyze(self, client, software_owner):
        from megaone.users.data_migration import services
        import io, csv
        session = services.create_session()
        client.force_login(software_owner)
        url = reverse('users:data_migration:step1_upload', args=[session['id']])

        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(['Product Name', 'SKU', 'Price'])
        w.writerow(['Widget', 'SKU-001', '29.99'])
        csv_bytes = buf.getvalue().encode('utf-8')

        response = client.post(url, {'file': SimpleUploadedFile('test.csv', csv_bytes)})
        assert response.status_code == 302
        assert 'analyze' in response.url


class TestStep2Analyze:
    def test_get_after_upload_shows_modules(self, client, software_owner):
        from megaone.users.data_migration import services
        import io, csv
        session = services.create_session()
        data = io.StringIO()
        w = csv.writer(data)
        w.writerow(['Product Name', 'SKU', 'Price', 'Stock'])
        w.writerow(['Widget', 'SKU-001', '29.99', '100'])

        # Simulate upload
        from django.core.files.uploadedfile import SimpleUploadedFile
        uf = SimpleUploadedFile('test.csv', data.getvalue().encode('utf-8'))
        session = services.step1_upload(session, uf)

        client.force_login(software_owner)
        url = reverse('users:data_migration:step2_analyze', args=[session['id']])
        response = client.get(url)
        assert response.status_code == 200
        assert 'Products' in str(response.content)


class TestStep3Summary:
    def test_get_returns_summary(self, client, software_owner):
        from megaone.users.data_migration import services
        import io, csv
        session = services.create_session()
        data = io.StringIO()
        w = csv.writer(data)
        w.writerow(['Product Name', 'SKU', 'Price', 'Stock'])
        w.writerow(['Widget', 'SKU-001', '29.99', '100'])

        from django.core.files.uploadedfile import SimpleUploadedFile
        uf = SimpleUploadedFile('test.csv', data.getvalue().encode('utf-8'))
        session = services.step1_upload(session, uf)
        session['selected_modules'] = ['Products']
        services.save_session(session)
        session = services.step2_analyze(session)

        client.force_login(software_owner)
        url = reverse('users:data_migration:step3_summary', args=[session['id']])
        response = client.get(url)
        assert response.status_code == 200


from django.core.files.uploadedfile import SimpleUploadedFile
