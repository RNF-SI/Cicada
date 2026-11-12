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
    """Le journal d'audit est écrit **après** la vue : c'est là seulement que
    l'utilisateur d'une requête de l'API (jeton JWT) est connu."""

    @staticmethod
    def _passer(request_factory, methode, chemin, user=None, statut=200):
        from django.contrib.auth.models import AnonymousUser
        middleware = AuditMiddleware(Mock(return_value=HttpResponse(status=statut)))
        request = getattr(request_factory, methode)(chemin)
        request.user = user or AnonymousUser()
        return middleware.process_response(request, HttpResponse(status=statut))

    @pytest.mark.parametrize('methode', ['post', 'put', 'patch', 'delete'])
    def test_une_ecriture_de_l_api_est_journalisee_avec_son_auteur(self, request_factory, methode, caplog):
        user = RoleFactory()
        with caplog.at_level('INFO', logger='audit'):
            self._passer(request_factory, methode, '/api/plans/plans/1/', user)
        enregistrements = [r for r in caplog.records if r.name == 'audit']
        assert len(enregistrements) == 1
        assert enregistrements[0].user_email == user.email
        assert enregistrements[0].action == methode.upper()

    def test_toute_l_api_est_couverte(self, request_factory, caplog):
        with caplog.at_level('INFO', logger='audit'):
            self._passer(request_factory, 'post', '/api/validations/1/approve/', RoleFactory())
        assert [r for r in caplog.records if r.name == 'audit']

    def test_pas_de_journal_pour_une_lecture(self, request_factory, caplog):
        with caplog.at_level('INFO', logger='audit'):
            self._passer(request_factory, 'get', '/api/users/', RoleFactory())
        assert not [r for r in caplog.records if r.name == 'audit']

    def test_pas_de_journal_hors_api(self, request_factory, caplog):
        with caplog.at_level('INFO', logger='audit'):
            self._passer(request_factory, 'post', '/admin/login/', RoleFactory())
        assert not [r for r in caplog.records if r.name == 'audit']

    def test_un_refus_anonyme_est_journalise(self, request_factory, caplog):
        with caplog.at_level('INFO', logger='audit'):
            self._passer(request_factory, 'post', '/api/plans/plans/', None, statut=401)
        enregistrements = [r for r in caplog.records if r.name == 'audit']
        assert len(enregistrements) == 1 and enregistrements[0].success is False

    def test_une_ecriture_anonyme_reussie_n_est_pas_journalisee_ici(self, request_factory, caplog):
        with caplog.at_level('INFO', logger='audit'):
            self._passer(request_factory, 'post', '/api/auth/register/', None, statut=201)
        assert not [r for r in caplog.records if r.name == 'audit']

    def test_par_l_api_reelle_l_auteur_du_jeton_est_journalise(self, caplog):
        """Le cas qui manquait : DRF authentifie après les middlewares."""
        from rest_framework.test import APIClient
        from rest_framework_simplejwt.tokens import RefreshToken
        user = RoleFactory()
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
        with caplog.at_level('INFO', logger='audit'):
            client.post('/api/notifications/read-all/', {}, format='json')
        enregistrements = [r for r in caplog.records if r.name == 'audit']
        assert enregistrements and enregistrements[-1].user_id == user.pk
