"""
Unit tests for custom permission decorators.
Tests require_super_admin, require_admin_organisme, require_referent, etc.
"""
import pytest
from django.test import RequestFactory
from django.http import JsonResponse

from apps.users.decorators import (
    require_super_admin,
    require_admin_organisme,
    require_referent,
    require_organisme_access,
    require_site_access,
    require_same_organisme
)
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, OrganismeFactory, SiteFactory, CorRoleSiteFactory
)


@pytest.fixture
def request_factory():
    """Return a Django RequestFactory."""
    return RequestFactory()


# Dummy view for testing decorators
def dummy_view(request, *args, **kwargs):
    """A simple view that returns success."""
    return JsonResponse({'success': True})


class AnonymousUser:
    """Mock anonymous user for testing."""
    is_authenticated = False


@pytest.mark.django_db
@pytest.mark.unit
class TestRequireSuperAdminDecorator:
    """Tests for require_super_admin decorator."""

    def test_allows_super_admin(self, request_factory):
        """Test super admin can access decorated view."""
        super_admin = SuperAdminFactory()
        request = request_factory.get('/test/')
        request.user = super_admin

        decorated_view = require_super_admin(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 200

    def test_denies_admin_organisme(self, request_factory):
        """Test admin organisme cannot access view requiring super_admin."""
        admin_og = AdminOrganismeFactory()
        request = request_factory.get('/test/')
        request.user = admin_og

        decorated_view = require_super_admin(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 403

    def test_denies_regular_user(self, request_factory):
        """Test regular user cannot access view requiring super_admin."""
        user = RoleFactory()
        request = request_factory.get('/test/')
        request.user = user

        decorated_view = require_super_admin(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 403

    def test_denies_unauthenticated(self, request_factory):
        """Test unauthenticated user cannot access decorated view."""
        request = request_factory.get('/test/')
        request.user = AnonymousUser()

        decorated_view = require_super_admin(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.unit
class TestRequireAdminOrganismeDecorator:
    """Tests for require_admin_organisme decorator."""

    def test_allows_super_admin(self, request_factory):
        """Test super admin can access decorated view."""
        super_admin = SuperAdminFactory()
        request = request_factory.get('/test/')
        request.user = super_admin

        decorated_view = require_admin_organisme(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 200

    def test_allows_admin_organisme(self, request_factory):
        """Test admin organisme can access decorated view."""
        admin_og = AdminOrganismeFactory()
        request = request_factory.get('/test/')
        request.user = admin_og

        decorated_view = require_admin_organisme(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 200

    def test_denies_regular_user(self, request_factory):
        """Test regular user cannot access view requiring admin_organisme."""
        user = RoleFactory()
        request = request_factory.get('/test/')
        request.user = user

        decorated_view = require_admin_organisme(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 403

    def test_denies_unauthenticated(self, request_factory):
        """Test unauthenticated user cannot access decorated view."""
        request = request_factory.get('/test/')
        request.user = AnonymousUser()

        decorated_view = require_admin_organisme(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.unit
class TestRequireReferentDecorator:
    """Tests for require_referent decorator."""

    def test_allows_super_admin(self, request_factory):
        """Test super admin can access decorated view (is_referent returns True)."""
        super_admin = SuperAdminFactory()
        request = request_factory.get('/test/')
        request.user = super_admin

        decorated_view = require_referent(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 200

    def test_allows_admin_organisme(self, request_factory):
        """Test admin organisme can access (is_referent returns True for admin)."""
        admin_og = AdminOrganismeFactory()
        request = request_factory.get('/test/')
        request.user = admin_og

        decorated_view = require_referent(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 200

    def test_allows_site_referent(self, request_factory):
        """Test validated site referent can access decorated view."""
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        request = request_factory.get('/test/')
        request.user = referent

        decorated_view = require_referent(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 200

    def test_denies_regular_user(self, request_factory):
        """Test regular user without referent status cannot access."""
        user = RoleFactory()
        request = request_factory.get('/test/')
        request.user = user

        decorated_view = require_referent(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 403

    def test_denies_unauthenticated(self, request_factory):
        """Test unauthenticated user cannot access decorated view."""
        request = request_factory.get('/test/')
        request.user = AnonymousUser()

        decorated_view = require_referent(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.unit
class TestRequireOrganismeAccessDecorator:
    """Tests for require_organisme_access decorator."""

    def test_super_admin_can_access_any_organisme(self, request_factory):
        """Test super admin can access any organisme."""
        super_admin = SuperAdminFactory()
        organisme = OrganismeFactory()

        request = request_factory.get('/test/')
        request.user = super_admin

        decorated_view = require_organisme_access('organisme_id')(dummy_view)
        response = decorated_view(request, organisme_id=organisme.id_organisme)

        assert response.status_code == 200

    def test_admin_can_access_own_organisme(self, request_factory):
        """Test admin can access their own organisme."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)

        request = request_factory.get('/test/')
        request.user = admin_og

        decorated_view = require_organisme_access('organisme_id')(dummy_view)
        response = decorated_view(request, organisme_id=organisme.id_organisme)

        assert response.status_code == 200

    def test_admin_cannot_access_other_organisme(self, request_factory):
        """Test admin cannot access other organisme."""
        organisme1 = OrganismeFactory()
        organisme2 = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme1)

        request = request_factory.get('/test/')
        request.user = admin_og

        decorated_view = require_organisme_access('organisme_id')(dummy_view)
        response = decorated_view(request, organisme_id=organisme2.id_organisme)

        assert response.status_code == 403

    def test_missing_organisme_id_returns_400(self, request_factory):
        """Test missing organisme_id returns 400."""
        super_admin = SuperAdminFactory()

        request = request_factory.get('/test/')
        request.user = super_admin

        decorated_view = require_organisme_access('organisme_id')(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 400

    def test_nonexistent_organisme_returns_404(self, request_factory):
        """Test non-existent organisme returns 404."""
        super_admin = SuperAdminFactory()

        request = request_factory.get('/test/')
        request.user = super_admin

        decorated_view = require_organisme_access('organisme_id')(dummy_view)
        response = decorated_view(request, organisme_id=99999)

        assert response.status_code == 404

    def test_denies_unauthenticated(self, request_factory):
        """Test unauthenticated user cannot access decorated view."""
        organisme = OrganismeFactory()

        request = request_factory.get('/test/')
        request.user = AnonymousUser()

        decorated_view = require_organisme_access('organisme_id')(dummy_view)
        response = decorated_view(request, organisme_id=organisme.id_organisme)

        assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.unit
class TestRequireSiteAccessDecorator:
    """Tests for require_site_access decorator."""

    def test_super_admin_can_access_any_site(self, request_factory):
        """Test super admin can access any site."""
        super_admin = SuperAdminFactory()
        site = SiteFactory()

        request = request_factory.get('/test/')
        request.user = super_admin

        decorated_view = require_site_access('site_id')(dummy_view)
        response = decorated_view(request, site_id=site.id_site)

        assert response.status_code == 200

    def test_referent_can_access_assigned_site(self, request_factory):
        """Test referent can access assigned site."""
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        request = request_factory.get('/test/')
        request.user = referent

        decorated_view = require_site_access('site_id')(dummy_view)
        response = decorated_view(request, site_id=site.id_site)

        assert response.status_code == 200

    def test_referent_cannot_access_unassigned_site(self, request_factory):
        """Test referent cannot access site they are not assigned to."""
        referent = ReferentFactory()
        site1 = SiteFactory()
        site2 = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site1, referent=True, referent_valid=True)

        request = request_factory.get('/test/')
        request.user = referent

        decorated_view = require_site_access('site_id')(dummy_view)
        response = decorated_view(request, site_id=site2.id_site)

        assert response.status_code == 403

    def test_missing_site_id_returns_400(self, request_factory):
        """Test missing site_id returns 400."""
        super_admin = SuperAdminFactory()

        request = request_factory.get('/test/')
        request.user = super_admin

        decorated_view = require_site_access('site_id')(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 400

    def test_nonexistent_site_returns_404(self, request_factory):
        """Test non-existent site returns 404."""
        super_admin = SuperAdminFactory()

        request = request_factory.get('/test/')
        request.user = super_admin

        decorated_view = require_site_access('site_id')(dummy_view)
        response = decorated_view(request, site_id=99999)

        assert response.status_code == 404

    def test_denies_unauthenticated(self, request_factory):
        """Test unauthenticated user cannot access decorated view."""
        site = SiteFactory()

        request = request_factory.get('/test/')
        request.user = AnonymousUser()

        decorated_view = require_site_access('site_id')(dummy_view)
        response = decorated_view(request, site_id=site.id_site)

        assert response.status_code == 401


@pytest.mark.django_db
@pytest.mark.unit
class TestRequireSameOrganismeDecorator:
    """Tests for require_same_organisme decorator."""

    def test_super_admin_always_passes(self, request_factory):
        """Test super admin passes the decorator."""
        super_admin = SuperAdminFactory()

        request = request_factory.get('/test/')
        request.user = super_admin

        decorated_view = require_same_organisme(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 200

    def test_authenticated_user_passes(self, request_factory):
        """Test authenticated user passes the decorator."""
        user = RoleFactory()

        request = request_factory.get('/test/')
        request.user = user

        decorated_view = require_same_organisme(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 200

    def test_denies_unauthenticated(self, request_factory):
        """Test unauthenticated user cannot access decorated view."""
        request = request_factory.get('/test/')
        request.user = AnonymousUser()

        decorated_view = require_same_organisme(dummy_view)
        response = decorated_view(request)

        assert response.status_code == 401
