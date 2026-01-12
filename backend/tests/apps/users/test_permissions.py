"""
Unit tests for custom DRF permissions.
Tests IsSuperAdmin, IsAdminOrganisme, IsReferent, CanManageOrganisme,
CanManageSite, IsOwnerOrReadOnly, IsOrganismeMember, HasPlanGestionAccess.
"""
import pytest
from unittest.mock import Mock, MagicMock
from rest_framework.test import APIRequestFactory

from apps.users.permissions import (
    IsSuperAdmin, IsAdminOrganisme, IsReferent,
    CanManageOrganisme, CanManageSite, IsOwnerOrReadOnly,
    IsOrganismeMember, HasPlanGestionAccess
)
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, OrganismeFactory, SiteFactory, CorOgSiteFactory,
    CorRoleSiteFactory
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory


@pytest.fixture
def request_factory():
    """Return an API request factory."""
    return APIRequestFactory()


@pytest.fixture
def mock_view():
    """Return a mock view."""
    return Mock()


def create_mock_request(user, method='GET'):
    """Create a mock request with a user."""
    request = Mock()
    request.user = user
    request.method = method
    return request


@pytest.mark.django_db
@pytest.mark.unit
class TestIsSuperAdminPermission:
    """Tests for IsSuperAdmin permission class."""

    def test_super_admin_has_permission(self, mock_view):
        """Test super admin passes permission check."""
        permission = IsSuperAdmin()
        admin = SuperAdminFactory()
        request = create_mock_request(admin)

        assert permission.has_permission(request, mock_view) is True

    def test_admin_og_denied(self, mock_view):
        """Test admin organisme fails permission check."""
        permission = IsSuperAdmin()
        admin_og = AdminOrganismeFactory()
        request = create_mock_request(admin_og)

        assert permission.has_permission(request, mock_view) is False

    def test_referent_denied(self, mock_view):
        """Test referent fails permission check."""
        permission = IsSuperAdmin()
        referent = ReferentFactory()
        request = create_mock_request(referent)

        assert permission.has_permission(request, mock_view) is False

    def test_regular_user_denied(self, mock_view):
        """Test regular user fails permission check."""
        permission = IsSuperAdmin()
        user = RoleFactory()
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is False

    def test_unauthenticated_denied(self, mock_view):
        """Test unauthenticated user fails permission check."""
        permission = IsSuperAdmin()
        user = Mock()
        user.is_authenticated = False
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is False

    def test_none_user_denied(self, mock_view):
        """Test None user fails permission check."""
        permission = IsSuperAdmin()
        request = Mock()
        request.user = None

        # When user is None, the short-circuit evaluation returns None (falsy)
        result = permission.has_permission(request, mock_view)
        assert not result  # None is falsy


@pytest.mark.django_db
@pytest.mark.unit
class TestIsAdminOrganismePermission:
    """Tests for IsAdminOrganisme permission class."""

    def test_admin_og_has_permission(self, mock_view):
        """Test admin organisme passes permission check."""
        permission = IsAdminOrganisme()
        admin_og = AdminOrganismeFactory()
        request = create_mock_request(admin_og)

        assert permission.has_permission(request, mock_view) is True

    def test_super_admin_has_permission(self, mock_view):
        """Test super admin passes admin organisme check (hierarchy)."""
        permission = IsAdminOrganisme()
        admin = SuperAdminFactory()
        request = create_mock_request(admin)

        assert permission.has_permission(request, mock_view) is True

    def test_referent_denied(self, mock_view):
        """Test referent fails admin organisme check."""
        permission = IsAdminOrganisme()
        referent = ReferentFactory()
        request = create_mock_request(referent)

        assert permission.has_permission(request, mock_view) is False

    def test_regular_user_denied(self, mock_view):
        """Test regular user fails permission check."""
        permission = IsAdminOrganisme()
        user = RoleFactory()
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is False

    def test_unauthenticated_denied(self, mock_view):
        """Test unauthenticated user fails permission check."""
        permission = IsAdminOrganisme()
        user = Mock()
        user.is_authenticated = False
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestIsReferentPermission:
    """Tests for IsReferent permission class."""

    def test_site_referent_has_permission(self, mock_view):
        """Test site referent passes permission check."""
        permission = IsReferent()
        user = RoleFactory()
        site = SiteFactory()
        # Create validated site referent assignment
        CorRoleSiteFactory(id_role=user, id_site=site, referent=True, referent_valid=True)
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is True

    def test_admin_og_has_permission(self, mock_view):
        """Test admin organisme passes referent check (hierarchy)."""
        permission = IsReferent()
        admin_og = AdminOrganismeFactory()
        request = create_mock_request(admin_og)

        assert permission.has_permission(request, mock_view) is True

    def test_super_admin_has_permission(self, mock_view):
        """Test super admin passes referent check (hierarchy)."""
        permission = IsReferent()
        admin = SuperAdminFactory()
        request = create_mock_request(admin)

        assert permission.has_permission(request, mock_view) is True

    def test_regular_user_denied(self, mock_view):
        """Test regular user fails referent check."""
        permission = IsReferent()
        user = RoleFactory()
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is False

    def test_unauthenticated_denied(self, mock_view):
        """Test unauthenticated user fails permission check."""
        permission = IsReferent()
        user = Mock()
        user.is_authenticated = False
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestCanManageOrganismePermission:
    """Tests for CanManageOrganisme object-level permission."""

    def test_super_admin_has_permission(self, mock_view):
        """Test super admin has base permission."""
        permission = CanManageOrganisme()
        admin = SuperAdminFactory()
        request = create_mock_request(admin)

        assert permission.has_permission(request, mock_view) is True

    def test_super_admin_can_manage_any_organisme(self, mock_view):
        """Test super admin can manage any organisme."""
        permission = CanManageOrganisme()
        admin = SuperAdminFactory()
        organisme = OrganismeFactory()
        request = create_mock_request(admin)

        assert permission.has_object_permission(request, mock_view, organisme) is True

    def test_admin_og_can_manage_own_organisme(self, mock_view):
        """Test admin_og can manage their organisme."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)

        permission = CanManageOrganisme()
        request = create_mock_request(admin_og)

        assert permission.has_object_permission(request, mock_view, organisme) is True

    def test_admin_og_cannot_manage_other_organisme(self, mock_view):
        """Test admin_og cannot manage other organisme."""
        organisme1 = OrganismeFactory()
        organisme2 = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme1)

        permission = CanManageOrganisme()
        request = create_mock_request(admin_og)

        assert permission.has_object_permission(request, mock_view, organisme2) is False

    def test_unauthenticated_denied(self, mock_view):
        """Test unauthenticated user fails permission check."""
        permission = CanManageOrganisme()
        user = Mock()
        user.is_authenticated = False
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestCanManageSitePermission:
    """Tests for CanManageSite object-level permission."""

    def test_super_admin_has_permission(self, mock_view):
        """Test super admin has base permission."""
        permission = CanManageSite()
        admin = SuperAdminFactory()
        request = create_mock_request(admin)

        assert permission.has_permission(request, mock_view) is True

    def test_super_admin_can_manage_any_site(self, mock_view):
        """Test super admin can manage any site."""
        permission = CanManageSite()
        admin = SuperAdminFactory()
        site = SiteFactory()
        request = create_mock_request(admin)

        assert permission.has_object_permission(request, mock_view, site) is True

    def test_referent_can_manage_assigned_site(self, mock_view):
        """Test referent can manage their assigned site."""
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(
            id_role=referent,
            id_site=site,
            referent=True,
            referent_valid=True
        )

        permission = CanManageSite()
        request = create_mock_request(referent)

        assert permission.has_object_permission(request, mock_view, site) is True

    def test_referent_cannot_manage_unassigned_site(self, mock_view):
        """Test referent cannot manage unassigned site."""
        referent = ReferentFactory()
        site = SiteFactory()
        # No CorRoleSite link

        permission = CanManageSite()
        request = create_mock_request(referent)

        assert permission.has_object_permission(request, mock_view, site) is False

    def test_admin_og_can_manage_organisme_site(self, mock_view):
        """Test admin_og can manage site linked to their organisme."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)

        permission = CanManageSite()
        request = create_mock_request(admin_og)

        assert permission.has_object_permission(request, mock_view, site) is True

    def test_unauthenticated_denied(self, mock_view):
        """Test unauthenticated user fails permission check."""
        permission = CanManageSite()
        user = Mock()
        user.is_authenticated = False
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestIsOwnerOrReadOnlyPermission:
    """Tests for IsOwnerOrReadOnly permission class."""

    def test_read_allowed_for_authenticated(self, mock_view):
        """Test read operations allowed for authenticated users."""
        permission = IsOwnerOrReadOnly()
        user = RoleFactory()

        for method in ['GET', 'HEAD', 'OPTIONS']:
            request = create_mock_request(user, method=method)
            assert permission.has_object_permission(request, mock_view, Mock()) is True

    def test_read_denied_for_unauthenticated(self, mock_view):
        """Test read operations denied for unauthenticated users."""
        permission = IsOwnerOrReadOnly()
        user = Mock()
        user.is_authenticated = False
        request = create_mock_request(user, method='GET')

        assert permission.has_object_permission(request, mock_view, Mock()) is False

    def test_write_allowed_for_owner(self, mock_view):
        """Test write operations allowed for object owner."""
        permission = IsOwnerOrReadOnly()
        user = RoleFactory()
        obj = Mock()
        obj.id_role = user
        request = create_mock_request(user, method='PUT')

        assert permission.has_object_permission(request, mock_view, obj) is True

    def test_write_denied_for_non_owner(self, mock_view):
        """Test write operations denied for non-owner regular user."""
        permission = IsOwnerOrReadOnly()
        user1 = RoleFactory()
        user2 = RoleFactory()
        obj = Mock()
        obj.id_role = user1
        request = create_mock_request(user2, method='PUT')

        assert permission.has_object_permission(request, mock_view, obj) is False

    def test_write_allowed_for_admin(self, mock_view):
        """Test write operations allowed for admin organisme."""
        permission = IsOwnerOrReadOnly()
        owner = RoleFactory()
        admin = AdminOrganismeFactory()
        obj = Mock()
        obj.id_role = owner
        request = create_mock_request(admin, method='PUT')

        assert permission.has_object_permission(request, mock_view, obj) is True


@pytest.mark.django_db
@pytest.mark.unit
class TestIsOrganismeMemberPermission:
    """Tests for IsOrganismeMember permission class."""

    def test_has_permission_for_authenticated(self, mock_view):
        """Test base permission granted for authenticated users."""
        permission = IsOrganismeMember()
        user = RoleFactory()
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is True

    def test_super_admin_can_access_any_object(self, mock_view):
        """Test super admin can access any object."""
        permission = IsOrganismeMember()
        admin = SuperAdminFactory()
        obj = Mock()
        obj.id_organisme = OrganismeFactory()
        request = create_mock_request(admin)

        assert permission.has_object_permission(request, mock_view, obj) is True

    def test_user_can_access_same_organisme_object(self, mock_view):
        """Test user can access object from same organisme."""
        organisme = OrganismeFactory()
        user = RoleFactory(id_organisme=organisme)
        obj = Mock()
        obj.id_organisme = organisme
        request = create_mock_request(user)

        permission = IsOrganismeMember()
        assert permission.has_object_permission(request, mock_view, obj) is True

    def test_user_cannot_access_other_organisme_object(self, mock_view):
        """Test user cannot access object from different organisme."""
        organisme1 = OrganismeFactory()
        organisme2 = OrganismeFactory()
        user = RoleFactory(id_organisme=organisme1)
        obj = Mock()
        obj.id_organisme = organisme2
        request = create_mock_request(user)

        permission = IsOrganismeMember()
        assert permission.has_object_permission(request, mock_view, obj) is False

    def test_object_without_organisme_denied(self, mock_view):
        """Test access denied for object without organisme attribute."""
        permission = IsOrganismeMember()
        user = RoleFactory()
        obj = Mock(spec=[])  # No id_organisme attribute
        request = create_mock_request(user)

        assert permission.has_object_permission(request, mock_view, obj) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestHasPlanGestionAccessPermission:
    """Tests for HasPlanGestionAccess permission class."""

    def test_has_permission_for_authenticated(self, mock_view):
        """Test base permission granted for authenticated users."""
        permission = HasPlanGestionAccess()
        user = RoleFactory()
        request = create_mock_request(user)

        assert permission.has_permission(request, mock_view) is True

    def test_super_admin_can_access_any_plan(self, mock_view):
        """Test super admin can access any plan."""
        permission = HasPlanGestionAccess()
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        request = create_mock_request(admin)

        assert permission.has_object_permission(request, mock_view, plan) is True

    def test_referent_can_access_plan_with_assigned_site(self, mock_view):
        """Test referent can access plan with their assigned site."""
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(
            id_role=referent,
            id_site=site,
            referent=True,
            referent_valid=True
        )
        plan = PlanGestionFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        permission = HasPlanGestionAccess()
        request = create_mock_request(referent)

        assert permission.has_object_permission(request, mock_view, plan) is True

    def test_referent_cannot_access_plan_without_assigned_site(self, mock_view):
        """Test referent cannot access plan without their assigned site."""
        referent = ReferentFactory()
        site1 = SiteFactory()
        site2 = SiteFactory()
        # Referent is assigned to site1, but plan is linked to site2
        CorRoleSiteFactory(
            id_role=referent,
            id_site=site1,
            referent=True,
            referent_valid=True
        )
        plan = PlanGestionFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site2)

        permission = HasPlanGestionAccess()
        request = create_mock_request(referent)

        assert permission.has_object_permission(request, mock_view, plan) is False

    def test_regular_user_cannot_access_plan(self, mock_view):
        """Test regular user cannot access any plan."""
        user = RoleFactory()
        plan = PlanGestionFactory()

        permission = HasPlanGestionAccess()
        request = create_mock_request(user)

        assert permission.has_object_permission(request, mock_view, plan) is False
