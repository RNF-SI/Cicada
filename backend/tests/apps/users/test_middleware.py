"""
Unit tests for custom middleware.
Tests PermissionMiddleware, SecurityHeadersMiddleware, AuditMiddleware.
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from django.http import HttpResponse, HttpRequest
from django.test import RequestFactory

from apps.users.middleware import (
    PermissionMiddleware, SecurityHeadersMiddleware, AuditMiddleware
)
from tests.factories.users import SuperAdminFactory, AdminOrganismeFactory, RoleFactory


@pytest.fixture
def request_factory():
    """Return a Django request factory."""
    return RequestFactory()


@pytest.fixture
def get_response():
    """Mock get_response callable for middleware."""
    return Mock(return_value=HttpResponse())


@pytest.mark.django_db
@pytest.mark.unit
class TestPermissionMiddleware:
    """Tests for PermissionMiddleware."""

    def test_exempt_urls_skip_processing_admin(self, request_factory, get_response):
        """Test that /admin/ is exempt from processing."""
        middleware = PermissionMiddleware(get_response)
        request = request_factory.get('/admin/')

        result = middleware.process_request(request)
        assert result is None  # None means continue processing

    def test_exempt_urls_skip_processing_login(self, request_factory, get_response):
        """Test that /api/auth/login/ is exempt from processing."""
        middleware = PermissionMiddleware(get_response)
        request = request_factory.get('/api/auth/login/')

        result = middleware.process_request(request)
        assert result is None

    def test_exempt_urls_skip_processing_health(self, request_factory, get_response):
        """Test that /api/auth/health/ is exempt from processing."""
        middleware = PermissionMiddleware(get_response)
        request = request_factory.get('/api/auth/health/')

        result = middleware.process_request(request)
        assert result is None

    def test_non_exempt_url_continues(self, request_factory, get_response):
        """Test that non-exempt URLs continue processing."""
        middleware = PermissionMiddleware(get_response)
        request = request_factory.get('/api/users/')

        result = middleware.process_request(request)
        assert result is None  # None means continue (DRF handles auth)

    def test_adds_user_role_header(self, request_factory, get_response):
        """Test that X-User-Role header is added for authenticated users."""
        user = SuperAdminFactory()
        middleware = PermissionMiddleware(get_response)

        request = request_factory.get('/api/users/')
        request.user = user

        response = HttpResponse()
        result = middleware.process_response(request, response)

        assert 'X-User-Role' in result
        assert result['X-User-Role'] == 'super_admin'

    def test_adds_user_organisme_header(self, request_factory, get_response):
        """Test that X-User-Organisme header is added."""
        user = AdminOrganismeFactory()
        middleware = PermissionMiddleware(get_response)

        request = request_factory.get('/api/users/')
        request.user = user

        response = HttpResponse()
        result = middleware.process_response(request, response)

        assert 'X-User-Organisme' in result
        assert result['X-User-Organisme'] == str(user.id_organisme.id_organisme)

    def test_adds_user_organisme_none_when_no_organisme(self, request_factory, get_response):
        """Test that X-User-Organisme is 'None' when user has no organisme."""
        user = SuperAdminFactory(id_organisme=None)
        middleware = PermissionMiddleware(get_response)

        request = request_factory.get('/api/users/')
        request.user = user

        response = HttpResponse()
        result = middleware.process_response(request, response)

        assert result['X-User-Organisme'] == 'None'

    def test_adds_user_permissions_header(self, request_factory, get_response):
        """Test that X-User-Permissions header is added with correct values."""
        user = SuperAdminFactory()
        middleware = PermissionMiddleware(get_response)

        request = request_factory.get('/api/users/')
        request.user = user

        response = HttpResponse()
        result = middleware.process_response(request, response)

        assert 'X-User-Permissions' in result
        permissions = json.loads(result['X-User-Permissions'])
        assert permissions['is_super_admin'] is True
        assert permissions['is_admin_organisme'] is True
        assert permissions['is_referent'] is True

    def test_no_headers_for_unauthenticated(self, request_factory, get_response):
        """Test that no headers are added for unauthenticated users."""
        middleware = PermissionMiddleware(get_response)

        request = request_factory.get('/api/users/')
        request.user = Mock()
        request.user.is_authenticated = False

        response = HttpResponse()
        result = middleware.process_response(request, response)

        assert 'X-User-Role' not in result

    def test_no_headers_for_non_api_path(self, request_factory, get_response):
        """Test that headers are not added for non-API paths."""
        user = SuperAdminFactory()
        middleware = PermissionMiddleware(get_response)

        request = request_factory.get('/static/file.js')
        request.user = user

        response = HttpResponse()
        result = middleware.process_response(request, response)

        assert 'X-User-Role' not in result


@pytest.mark.django_db
@pytest.mark.unit
class TestSecurityHeadersMiddleware:
    """Tests for SecurityHeadersMiddleware."""

    def test_adds_x_content_type_options(self, request_factory, get_response):
        """Test that X-Content-Type-Options header is added."""
        middleware = SecurityHeadersMiddleware(get_response)
        request = request_factory.get('/any/path/')

        response = HttpResponse()
        result = middleware.process_response(request, response)

        assert result['X-Content-Type-Options'] == 'nosniff'

    def test_adds_x_frame_options(self, request_factory, get_response):
        """Test that X-Frame-Options header is added."""
        middleware = SecurityHeadersMiddleware(get_response)
        request = request_factory.get('/any/path/')

        response = HttpResponse()
        result = middleware.process_response(request, response)

        assert result['X-Frame-Options'] == 'DENY'

    def test_adds_x_xss_protection(self, request_factory, get_response):
        """Test that X-XSS-Protection header is added."""
        middleware = SecurityHeadersMiddleware(get_response)
        request = request_factory.get('/any/path/')

        response = HttpResponse()
        result = middleware.process_response(request, response)

        assert result['X-XSS-Protection'] == '1; mode=block'

    def test_adds_cors_headers_for_api(self, request_factory, get_response):
        """Test that CORS headers are added for API endpoints."""
        middleware = SecurityHeadersMiddleware(get_response)
        request = request_factory.get('/api/users/')

        response = HttpResponse()
        result = middleware.process_response(request, response)

        assert result['Access-Control-Allow-Credentials'] == 'true'
        assert 'GET' in result['Access-Control-Allow-Methods']
        assert 'POST' in result['Access-Control-Allow-Methods']
        assert 'Authorization' in result['Access-Control-Allow-Headers']

    def test_no_cors_headers_for_non_api(self, request_factory, get_response):
        """Test that CORS headers are not added for non-API paths."""
        middleware = SecurityHeadersMiddleware(get_response)
        request = request_factory.get('/static/file.js')

        response = HttpResponse()
        result = middleware.process_response(request, response)

        # Security headers should still be present
        assert result['X-Content-Type-Options'] == 'nosniff'
        # But CORS headers should not be present
        assert 'Access-Control-Allow-Credentials' not in result

    def test_security_headers_on_all_paths(self, request_factory, get_response):
        """Test that security headers are added to all paths."""
        middleware = SecurityHeadersMiddleware(get_response)

        paths = ['/api/users/', '/admin/', '/static/file.js', '/']
        for path in paths:
            request = request_factory.get(path)
            response = HttpResponse()
            result = middleware.process_response(request, response)

            assert result['X-Content-Type-Options'] == 'nosniff'
            assert result['X-Frame-Options'] == 'DENY'
            assert result['X-XSS-Protection'] == '1; mode=block'


@pytest.mark.django_db
@pytest.mark.unit
class TestAuditMiddleware:
    """Tests for AuditMiddleware."""

    def test_audit_info_stored_for_post(self, request_factory, get_response):
        """Test that audit info is stored for POST requests on audit paths."""
        user = RoleFactory()
        middleware = AuditMiddleware(get_response)

        request = request_factory.post('/api/users/')
        request.user = user

        middleware.process_request(request)

        assert hasattr(request, 'audit_info')
        assert request.audit_info['action'] == 'POST'
        assert request.audit_info['user_email'] == user.email
        assert request.audit_info['path'] == '/api/users/'

    def test_audit_info_stored_for_put(self, request_factory, get_response):
        """Test that audit info is stored for PUT requests."""
        user = RoleFactory()
        middleware = AuditMiddleware(get_response)

        request = request_factory.put('/api/users/1/')
        request.user = user

        middleware.process_request(request)

        assert hasattr(request, 'audit_info')
        assert request.audit_info['action'] == 'PUT'

    def test_audit_info_stored_for_patch(self, request_factory, get_response):
        """Test that audit info is stored for PATCH requests."""
        user = RoleFactory()
        middleware = AuditMiddleware(get_response)

        request = request_factory.patch('/api/plans/1/')
        request.user = user

        middleware.process_request(request)

        assert hasattr(request, 'audit_info')
        assert request.audit_info['action'] == 'PATCH'

    def test_audit_info_stored_for_delete(self, request_factory, get_response):
        """Test that audit info is stored for DELETE requests."""
        user = RoleFactory()
        middleware = AuditMiddleware(get_response)

        request = request_factory.delete('/api/sites/1/')
        request.user = user

        middleware.process_request(request)

        assert hasattr(request, 'audit_info')
        assert request.audit_info['action'] == 'DELETE'

    def test_no_audit_for_get_requests(self, request_factory, get_response):
        """Test that GET requests are not audited."""
        user = RoleFactory()
        middleware = AuditMiddleware(get_response)

        request = request_factory.get('/api/users/')
        request.user = user

        middleware.process_request(request)

        assert not hasattr(request, 'audit_info')

    def test_no_audit_for_non_audit_paths(self, request_factory, get_response):
        """Test that non-audit paths are not audited."""
        user = RoleFactory()
        middleware = AuditMiddleware(get_response)

        request = request_factory.post('/api/auth/login/')
        request.user = user

        middleware.process_request(request)

        assert not hasattr(request, 'audit_info')

    def test_no_audit_for_unauthenticated(self, request_factory, get_response):
        """Test that unauthenticated requests are not audited."""
        middleware = AuditMiddleware(get_response)

        request = request_factory.post('/api/users/')
        request.user = Mock()
        request.user.is_authenticated = False

        middleware.process_request(request)

        assert not hasattr(request, 'audit_info')

    def test_process_response_adds_timestamp(self, request_factory, get_response):
        """Test that process_response adds timestamp to audit info."""
        user = RoleFactory()
        middleware = AuditMiddleware(get_response)

        request = request_factory.post('/api/users/')
        request.user = user

        middleware.process_request(request)

        response = HttpResponse(status=201)
        middleware.process_response(request, response)

        assert request.audit_info['timestamp'] is not None
        assert request.audit_info['status_code'] == 201

    def test_audit_paths_include_organismes(self, request_factory, get_response):
        """Test that /api/organismes/ is included in audit paths."""
        user = RoleFactory()
        middleware = AuditMiddleware(get_response)

        request = request_factory.post('/api/organismes/')
        request.user = user

        middleware.process_request(request)

        assert hasattr(request, 'audit_info')
