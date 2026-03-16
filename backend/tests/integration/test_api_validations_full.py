"""
Integration tests for Validations API - full coverage for missing validation types.

Covers:
1. plan_site_link: request endpoint, direct link, approve service
2. plan_access: approve flow
3. module_access: request, grant, revoke
4. admin_deactivation, admin_promotion, admin_demotion: request endpoints
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.notifications.models import Notification, ValidationRequest
from apps.plans.models import CorSitePg, CorRolePlan
from apps.users.models import CorRoleSite, CorOgSite
from apps.core.models import Module
from tests.factories.users import (
    RoleFactory, SuperAdminFactory, AdminOrganismeFactory, OrganismeFactory,
    SiteFactory, CorRoleSiteFactory, CorOgSiteFactory
)
from tests.factories.plans import PlanGestionFactory


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def authenticated_client(db):
    """Return an authenticated API client with a regular user."""
    user = RoleFactory()
    client = APIClient()
    client.force_authenticate(user=user)
    return client, user


@pytest.fixture
def admin_client(db):
    """Return an authenticated API client with a super admin user."""
    admin = SuperAdminFactory()
    client = APIClient()
    client.force_authenticate(user=admin)
    return client, admin


@pytest.fixture
def admin_og_client(db):
    """Return an authenticated API client with an admin organisme."""
    organisme = OrganismeFactory()
    admin_og = AdminOrganismeFactory(id_organisme=organisme)
    client = APIClient()
    client.force_authenticate(user=admin_og)
    return client, admin_og


@pytest.fixture
def module_with_access(db):
    """Create a module that requires access."""
    module, _ = Module.objects.get_or_create(
        code='test_zonages_access',
        defaults={
            'name': 'Zonages Test',
            'description': 'Module de zonages pour tests',
            'requires_access': True,
            'is_active': True,
        }
    )
    # Ensure the flags are correct in case it already existed
    module.requires_access = True
    module.is_active = True
    module.save(update_fields=['requires_access', 'is_active'])
    return module


@pytest.fixture
def module_no_access(db):
    """Create a module that does not require access."""
    module, _ = Module.objects.get_or_create(
        code='test_plans_noaccess',
        defaults={
            'name': 'Plans Test No Access',
            'description': 'Module plans sans acces pour tests',
            'requires_access': False,
            'is_active': True,
        }
    )
    module.requires_access = False
    module.is_active = True
    module.save(update_fields=['requires_access', 'is_active'])
    return module


# =============================================================================
# 1. PLAN_SITE_LINK - REQUEST ENDPOINT
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlanSiteLinkRequest:
    """Tests for POST /api/validations/request_plan_site_link/ endpoint."""

    def test_request_plan_site_link_success_as_plan_member(self):
        """Test successful plan-site link request by a plan member."""
        organisme = OrganismeFactory()
        user = RoleFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=user)

        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site])

        # Make user a member of the plan (not referent)
        CorRolePlan.objects.create(id_role=user, plan_de_gestion=plan, referent=False)

        new_site = SiteFactory()

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': new_site.id_site,
            'justification': 'Need to add this site',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['direct'] is False
        assert 'id' in response.data

    def test_request_plan_site_link_success_as_site_member(self):
        """Test successful plan-site link request by a site member."""
        user = RoleFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide')

        # Make user a member of the site (not referent)
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False)

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': site.id_site,
            'justification': 'Site should be linked',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['direct'] is False

    def test_request_plan_site_link_missing_fields(self, authenticated_client):
        """Test error when plan_id or site_id is missing."""
        client, user = authenticated_client

        # Missing both
        response = client.post('/api/validations/request_plan_site_link/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Missing site_id
        plan = PlanGestionFactory(statut='valide')
        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_plan_site_link_already_linked(self):
        """Test error when site is already linked to plan."""
        user = RoleFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site], referents=[user])

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': site.id_site,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'deja lie' in response.data['error'].lower() or 'déjà' in response.data['error'].lower()

    def test_request_plan_site_link_plan_not_found(self, authenticated_client):
        """Test error when plan does not exist."""
        client, user = authenticated_client
        site = SiteFactory()

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': 99999,
            'site_id': site.id_site,
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_request_plan_site_link_site_not_found(self, authenticated_client):
        """Test error when site does not exist."""
        client, user = authenticated_client
        plan = PlanGestionFactory(statut='valide', referents=[user])

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': 99999,
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_request_plan_site_link_as_plan_referent_creates_validation(self):
        """Test that plan referent who is NOT site referent creates a validation request."""
        user = RoleFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', referents=[user])
        new_site = SiteFactory()

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': new_site.id_site,
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['direct'] is False

    def test_request_plan_site_link_forbidden_for_non_member(self, authenticated_client):
        """Test 403 for user who is not related to plan or site."""
        client, user = authenticated_client
        plan = PlanGestionFactory(statut='valide')
        site = SiteFactory()

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': site.id_site,
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_request_plan_site_link_duplicate_pending(self):
        """Test error when a pending request already exists for same plan-site."""
        user = RoleFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', referents=[user])
        new_site = SiteFactory()

        # First request
        response1 = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': new_site.id_site,
        })
        assert response1.status_code == status.HTTP_201_CREATED

        # Duplicate request
        response2 = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': new_site.id_site,
        })
        assert response2.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# 1b. PLAN_SITE_LINK - DIRECT LINK (NO VALIDATION)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlanSiteLinkDirect:
    """Tests for direct plan-site linking (no validation needed)."""

    def test_direct_link_super_admin(self, admin_client):
        """Test super_admin can link directly without validation."""
        client, admin = admin_client
        plan = PlanGestionFactory(statut='valide')
        site = SiteFactory()

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': site.id_site,
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['direct'] is True
        assert CorSitePg.objects.filter(plan_de_gestion=plan, site=site).exists()

    def test_direct_link_admin_og_and_site_referent(self):
        """Test admin_og who is also site referent can link directly."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        site = SiteFactory()
        # Make admin_og a validated referent of the site
        CorRoleSiteFactory(id_role=admin_og, id_site=site, referent=True, referent_valid=True)
        plan = PlanGestionFactory(statut='valide')

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': site.id_site,
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['direct'] is True
        assert CorSitePg.objects.filter(plan_de_gestion=plan, site=site).exists()

    def test_direct_link_plan_referent_and_site_referent(self):
        """Test user who is referent of both plan and site can link directly."""
        user = RoleFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site, referent=True, referent_valid=True)
        plan = PlanGestionFactory(statut='valide', referents=[user])

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': site.id_site,
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['direct'] is True
        assert CorSitePg.objects.filter(plan_de_gestion=plan, site=site).exists()

    def test_direct_link_notifies_plan_referents(self):
        """Test that direct link notifies other plan referents."""
        user = RoleFactory()
        other_referent = RoleFactory()
        client = APIClient()
        client.force_authenticate(user=user)

        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site, referent=True, referent_valid=True)
        plan = PlanGestionFactory(statut='valide', referents=[user, other_referent])

        Notification.objects.all().delete()

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': site.id_site,
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['direct'] is True

        # other_referent should be notified
        notifs = Notification.objects.filter(recipient=other_referent)
        assert notifs.exists()

    def test_admin_og_without_site_referent_creates_validation(self):
        """Test admin_og who is NOT site referent creates a validation request."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        site = SiteFactory()
        # admin_og is admin_organisme but NOT referent of this site
        plan = PlanGestionFactory(statut='valide')

        response = client.post('/api/validations/request_plan_site_link/', {
            'plan_id': plan.id_pg,
            'site_id': site.id_site,
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['direct'] is False


# =============================================================================
# 1c. PLAN_SITE_LINK - APPROVE SERVICE
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlanSiteLinkApprove:
    """Tests for approving plan_site_link validation requests."""

    def test_approve_plan_site_link_creates_cor_site_pg(self, admin_client):
        """Test approving plan_site_link creates the CorSitePg record."""
        client, admin = admin_client
        requester = RoleFactory()
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide')

        vr = ValidationRequest.objects.create(
            request_type='plan_site_link',
            status='pending',
            requester=requester,
            target_plan=plan,
            target_site=site,
        )

        response = client.post(f'/api/validations/{vr.id}/approve/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'approved'

        assert CorSitePg.objects.filter(plan_de_gestion=plan, site=site).exists()

    def test_approve_plan_site_link_notifies_requester(self, admin_client):
        """Test approving plan_site_link notifies the requester."""
        client, admin = admin_client
        requester = RoleFactory()
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide')

        vr = ValidationRequest.objects.create(
            request_type='plan_site_link',
            status='pending',
            requester=requester,
            target_plan=plan,
            target_site=site,
        )

        Notification.objects.all().delete()
        client.post(f'/api/validations/{vr.id}/approve/')

        # Requester should receive a notification about the approval
        notifs = Notification.objects.filter(
            recipient=requester,
            notification_type='validation_approved',
        )
        assert notifs.exists()

    def test_approve_plan_site_link_notifies_plan_referents(self, admin_client):
        """Test approving plan_site_link notifies plan referents."""
        client, admin = admin_client
        requester = RoleFactory()
        plan_referent = RoleFactory()
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', referents=[plan_referent])

        vr = ValidationRequest.objects.create(
            request_type='plan_site_link',
            status='pending',
            requester=requester,
            target_plan=plan,
            target_site=site,
        )

        Notification.objects.all().delete()
        client.post(f'/api/validations/{vr.id}/approve/')

        # Plan referent should get an info notification about the new link
        notifs = Notification.objects.filter(
            recipient=plan_referent,
            notification_type='info',
        )
        assert notifs.exists()

    def test_approve_plan_site_link_sets_validator(self, admin_client):
        """Test approving sets the validator on the request."""
        client, admin = admin_client
        requester = RoleFactory()
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide')

        vr = ValidationRequest.objects.create(
            request_type='plan_site_link',
            status='pending',
            requester=requester,
            target_plan=plan,
            target_site=site,
        )

        client.post(f'/api/validations/{vr.id}/approve/')
        vr.refresh_from_db()
        assert vr.status == 'approved'
        assert vr.validator == admin
        assert vr.validated_at is not None


# =============================================================================
# 2. PLAN_ACCESS APPROVE FLOW
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlanAccessApprove:
    """Tests for approve flow of plan_access validation requests."""

    def test_approve_plan_access_creates_member(self, admin_client):
        """Test approving plan_access creates CorRolePlan for the requester."""
        client, admin = admin_client
        requester = RoleFactory()
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site])

        vr = ValidationRequest.objects.create(
            request_type='plan_access',
            status='pending',
            requester=requester,
            target_plan=plan,
        )

        response = client.post(f'/api/validations/{vr.id}/approve/')
        assert response.status_code == status.HTTP_200_OK
        assert CorRolePlan.objects.filter(id_role=requester, plan_de_gestion=plan).exists()

    def test_approve_plan_access_as_referent(self, admin_client):
        """Test approving plan_access with request_as_referent creates referent."""
        client, admin = admin_client
        requester = RoleFactory()
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site])

        vr = ValidationRequest.objects.create(
            request_type='plan_access',
            status='pending',
            requester=requester,
            target_plan=plan,
            request_as_referent=True,
        )

        client.post(f'/api/validations/{vr.id}/approve/')

        cor = CorRolePlan.objects.get(id_role=requester, plan_de_gestion=plan)
        assert cor.referent is True
        assert plan.referents.filter(pk=requester.pk).exists()

    def test_approve_plan_access_notifies_requester(self, admin_client):
        """Test approving plan_access notifies the requester."""
        client, admin = admin_client
        requester = RoleFactory()
        site = SiteFactory()
        plan = PlanGestionFactory(statut='valide', sites=[site])

        vr = ValidationRequest.objects.create(
            request_type='plan_access',
            status='pending',
            requester=requester,
            target_plan=plan,
        )

        Notification.objects.all().delete()
        client.post(f'/api/validations/{vr.id}/approve/')

        notifs = Notification.objects.filter(
            recipient=requester,
            notification_type='validation_approved',
        )
        assert notifs.exists()

    def test_approve_plan_access_sets_approved_status(self, admin_client):
        """Test approving plan_access sets the correct status."""
        client, admin = admin_client
        requester = RoleFactory()
        plan = PlanGestionFactory(statut='valide')

        vr = ValidationRequest.objects.create(
            request_type='plan_access',
            status='pending',
            requester=requester,
            target_plan=plan,
        )

        client.post(f'/api/validations/{vr.id}/approve/')
        vr.refresh_from_db()
        assert vr.status == 'approved'
        assert vr.validator == admin


# =============================================================================
# 3. MODULE_ACCESS - REQUEST
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestModuleAccessRequest:
    """Tests for POST /api/validations/request_module_access/ endpoint."""

    def test_request_module_access_success(self, authenticated_client, module_with_access):
        """Test successful module access request."""
        client, user = authenticated_client

        response = client.post('/api/validations/request_module_access/', {
            'module_code': module_with_access.code,
            'justification': 'I need access to zonages',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data

        vr = ValidationRequest.objects.get(id=response.data['id'])
        assert vr.request_type == 'module_access'
        assert vr.target_module == module_with_access.code
        assert vr.requester == user
        assert vr.status == 'pending'

    def test_request_module_access_missing_module_code(self, authenticated_client):
        """Test error when module_code is missing."""
        client, user = authenticated_client

        response = client.post('/api/validations/request_module_access/', {})
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_module_access_invalid_module_code(self, authenticated_client, module_with_access):
        """Test error when module_code is invalid."""
        client, user = authenticated_client

        response = client.post('/api/validations/request_module_access/', {
            'module_code': 'nonexistent_module',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_module_access_already_approved(self, authenticated_client, module_with_access):
        """Test error when user already has approved access."""
        client, user = authenticated_client

        # Create an already-approved request
        ValidationRequest.objects.create(
            request_type='module_access',
            status='approved',
            requester=user,
            target_module=module_with_access.code,
        )

        response = client.post('/api/validations/request_module_access/', {
            'module_code': module_with_access.code,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'deja acces' in response.data['error'].lower() or 'déjà' in response.data['error'].lower()

    def test_request_module_access_duplicate_pending(self, authenticated_client, module_with_access):
        """Test error when a pending request already exists."""
        client, user = authenticated_client

        # First request
        client.post('/api/validations/request_module_access/', {
            'module_code': module_with_access.code,
        })

        # Duplicate request
        response = client.post('/api/validations/request_module_access/', {
            'module_code': module_with_access.code,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_module_access_no_access_required(self, authenticated_client, module_no_access):
        """Test error when module does not require access."""
        client, user = authenticated_client

        response = client.post('/api/validations/request_module_access/', {
            'module_code': module_no_access.code,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# 3b. MODULE_ACCESS - GRANT
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestGrantModuleAccess:
    """Tests for POST /api/validations/grant_module_access/ endpoint."""

    def test_grant_module_access_success(self, admin_client, module_with_access):
        """Test super_admin can grant module access."""
        client, admin = admin_client
        target_user = RoleFactory()

        response = client.post('/api/validations/grant_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'granted'

        # Verify an approved request was created
        vr = ValidationRequest.objects.get(
            requester=target_user,
            request_type='module_access',
            target_module=module_with_access.code,
            status='approved',
        )
        assert vr.validator == admin

    def test_grant_module_access_forbidden_for_non_super_admin(self, admin_og_client, module_with_access):
        """Test admin_og cannot grant module access."""
        client, admin_og = admin_og_client
        target_user = RoleFactory()

        response = client.post('/api/validations/grant_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_grant_module_access_forbidden_for_regular_user(self, authenticated_client, module_with_access):
        """Test regular user cannot grant module access."""
        client, user = authenticated_client
        target_user = RoleFactory()

        response = client.post('/api/validations/grant_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_grant_module_access_already_has_access(self, admin_client, module_with_access):
        """Test error when user already has access."""
        client, admin = admin_client
        target_user = RoleFactory()

        # Create existing approved request
        ValidationRequest.objects.create(
            request_type='module_access',
            status='approved',
            requester=target_user,
            target_module=module_with_access.code,
            validator=admin,
        )

        response = client.post('/api/validations/grant_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_grant_module_access_cancels_pending_request(self, admin_client, module_with_access):
        """Test granting access cancels any pending request."""
        client, admin = admin_client
        target_user = RoleFactory()

        # Create a pending request
        pending_vr = ValidationRequest.objects.create(
            request_type='module_access',
            status='pending',
            requester=target_user,
            target_module=module_with_access.code,
        )

        client.post('/api/validations/grant_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })

        pending_vr.refresh_from_db()
        assert pending_vr.status == 'cancelled'

    def test_grant_module_access_notifies_user(self, admin_client, module_with_access):
        """Test granting access creates a notification for the user."""
        client, admin = admin_client
        target_user = RoleFactory()

        Notification.objects.all().delete()
        client.post('/api/validations/grant_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })

        notifs = Notification.objects.filter(
            recipient=target_user,
            notification_type='validation_approved',
        )
        assert notifs.exists()


# =============================================================================
# 3c. MODULE_ACCESS - REVOKE
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestRevokeModuleAccess:
    """Tests for POST /api/validations/revoke_module_access/ endpoint."""

    def test_revoke_module_access_success(self, admin_client, module_with_access):
        """Test super_admin can revoke module access."""
        client, admin = admin_client
        target_user = RoleFactory()

        # Grant access first
        ValidationRequest.objects.create(
            request_type='module_access',
            status='approved',
            requester=target_user,
            target_module=module_with_access.code,
            validator=admin,
        )

        response = client.post('/api/validations/revoke_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'revoked'

        # Verify the approved request was changed to rejected
        assert not ValidationRequest.objects.filter(
            requester=target_user,
            request_type='module_access',
            target_module=module_with_access.code,
            status='approved',
        ).exists()

    def test_revoke_module_access_forbidden_for_non_super_admin(self, admin_og_client, module_with_access):
        """Test admin_og cannot revoke module access."""
        client, admin_og = admin_og_client
        target_user = RoleFactory()

        response = client.post('/api/validations/revoke_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_revoke_module_access_forbidden_for_regular_user(self, authenticated_client, module_with_access):
        """Test regular user cannot revoke module access."""
        client, user = authenticated_client
        target_user = RoleFactory()

        response = client.post('/api/validations/revoke_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_revoke_module_access_no_access_to_revoke(self, admin_client, module_with_access):
        """Test error when user does not have access."""
        client, admin = admin_client
        target_user = RoleFactory()

        response = client.post('/api/validations/revoke_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_revoke_module_access_notifies_user(self, admin_client, module_with_access):
        """Test revoking access creates a notification for the user."""
        client, admin = admin_client
        target_user = RoleFactory()

        # Grant access first
        ValidationRequest.objects.create(
            request_type='module_access',
            status='approved',
            requester=target_user,
            target_module=module_with_access.code,
            validator=admin,
        )

        Notification.objects.all().delete()
        client.post('/api/validations/revoke_module_access/', {
            'user_id': target_user.id_role,
            'module_code': module_with_access.code,
        })

        notifs = Notification.objects.filter(
            recipient=target_user,
            notification_type='validation_rejected',
        )
        assert notifs.exists()


# =============================================================================
# 4a. ADMIN_DEACTIVATION REQUEST
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestAdminDeactivationRequest:
    """Tests for POST /api/validations/request_admin_deactivation/ endpoint."""

    def test_request_admin_deactivation_success_by_admin_og(self):
        """Test admin_og can request deactivation of another admin_og in same org."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        target_admin = AdminOrganismeFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': target_admin.id_role,
            'justification': 'No longer active',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data

    def test_request_admin_deactivation_success_by_super_admin(self, admin_client):
        """Test super_admin can request deactivation of any admin_og."""
        client, admin = admin_client
        organisme = OrganismeFactory()
        target_admin = AdminOrganismeFactory(id_organisme=organisme)

        response = client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': target_admin.id_role,
            'justification': 'Security concern',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_request_admin_deactivation_forbidden_for_regular_user(self, authenticated_client):
        """Test regular user cannot request admin deactivation."""
        client, user = authenticated_client
        organisme = OrganismeFactory()
        target_admin = AdminOrganismeFactory(id_organisme=organisme)

        response = client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': target_admin.id_role,
            'justification': 'Some reason',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_request_admin_deactivation_target_not_admin(self):
        """Test error when target is not an admin_og."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        regular_user = RoleFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': regular_user.id_role,
            'justification': 'Not admin',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_admin_deactivation_different_org_forbidden(self):
        """Test admin_og cannot deactivate admin of different organisation."""
        org1 = OrganismeFactory()
        org2 = OrganismeFactory()
        admin_og1 = AdminOrganismeFactory(id_organisme=org1)
        admin_og2 = AdminOrganismeFactory(id_organisme=org2)
        client = APIClient()
        client.force_authenticate(user=admin_og1)

        response = client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': admin_og2.id_role,
            'justification': 'Cross-org attempt',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_request_admin_deactivation_missing_justification(self):
        """Test error when justification is missing."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        target_admin = AdminOrganismeFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': target_admin.id_role,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_admin_deactivation_target_not_found(self):
        """Test error when target user does not exist."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': 99999,
            'justification': 'Some reason',
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_request_admin_deactivation_duplicate_pending(self):
        """Test error when pending request already exists."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        target_admin = AdminOrganismeFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        # First request
        client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': target_admin.id_role,
            'justification': 'First request',
        })

        # Duplicate
        response = client.post('/api/validations/request_admin_deactivation/', {
            'target_user_id': target_admin.id_role,
            'justification': 'Duplicate request',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# 4b. ADMIN_PROMOTION REQUEST
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestAdminPromotionRequest:
    """Tests for POST /api/validations/request_admin_promotion/ endpoint."""

    def test_request_admin_promotion_success(self):
        """Test admin_og can request promotion of user in same org."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        target_user = RoleFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_promotion/', {
            'target_user_id': target_user.id_role,
            'justification': 'Deserves promotion',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data

    def test_request_admin_promotion_success_by_super_admin(self, admin_client):
        """Test super_admin can request promotion of any user."""
        client, admin = admin_client
        target_user = RoleFactory()

        response = client.post('/api/validations/request_admin_promotion/', {
            'target_user_id': target_user.id_role,
            'justification': 'Needs admin rights',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_request_admin_promotion_forbidden_for_regular_user(self, authenticated_client):
        """Test regular user cannot request promotion."""
        client, user = authenticated_client
        target_user = RoleFactory()

        response = client.post('/api/validations/request_admin_promotion/', {
            'target_user_id': target_user.id_role,
            'justification': 'Some reason',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_request_admin_promotion_target_already_admin(self):
        """Test error when target is already an admin."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        target_admin = AdminOrganismeFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_promotion/', {
            'target_user_id': target_admin.id_role,
            'justification': 'Already admin',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_admin_promotion_different_org_forbidden(self):
        """Test admin_og cannot promote user from different org."""
        org1 = OrganismeFactory()
        org2 = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=org1)
        target_user = RoleFactory(id_organisme=org2)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_promotion/', {
            'target_user_id': target_user.id_role,
            'justification': 'Cross-org attempt',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_request_admin_promotion_missing_justification(self):
        """Test error when justification is missing."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        target_user = RoleFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_promotion/', {
            'target_user_id': target_user.id_role,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_admin_promotion_duplicate_pending(self):
        """Test error when pending request already exists."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        target_user = RoleFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        client.post('/api/validations/request_admin_promotion/', {
            'target_user_id': target_user.id_role,
            'justification': 'First request',
        })

        response = client.post('/api/validations/request_admin_promotion/', {
            'target_user_id': target_user.id_role,
            'justification': 'Duplicate',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# 4c. ADMIN_DEMOTION REQUEST
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestAdminDemotionRequest:
    """Tests for POST /api/validations/request_admin_demotion/ endpoint."""

    def test_request_admin_demotion_success(self):
        """Test admin_og can request demotion of another admin_og in same org."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        target_admin = AdminOrganismeFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_demotion/', {
            'target_user_id': target_admin.id_role,
            'justification': 'Should be demoted',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data

    def test_request_admin_demotion_success_by_super_admin(self, admin_client):
        """Test super_admin can request demotion of any admin_og."""
        client, admin = admin_client
        organisme = OrganismeFactory()
        target_admin = AdminOrganismeFactory(id_organisme=organisme)

        response = client.post('/api/validations/request_admin_demotion/', {
            'target_user_id': target_admin.id_role,
            'justification': 'Needs to be demoted',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_request_admin_demotion_forbidden_for_regular_user(self, authenticated_client):
        """Test regular user cannot request demotion."""
        client, user = authenticated_client
        organisme = OrganismeFactory()
        target_admin = AdminOrganismeFactory(id_organisme=organisme)

        response = client.post('/api/validations/request_admin_demotion/', {
            'target_user_id': target_admin.id_role,
            'justification': 'Some reason',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_request_admin_demotion_target_not_admin(self):
        """Test error when target is not an admin_og."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        regular_user = RoleFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_demotion/', {
            'target_user_id': regular_user.id_role,
            'justification': 'Not an admin',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_admin_demotion_different_org_forbidden(self):
        """Test admin_og cannot demote admin of different org."""
        org1 = OrganismeFactory()
        org2 = OrganismeFactory()
        admin_og1 = AdminOrganismeFactory(id_organisme=org1)
        admin_og2 = AdminOrganismeFactory(id_organisme=org2)
        client = APIClient()
        client.force_authenticate(user=admin_og1)

        response = client.post('/api/validations/request_admin_demotion/', {
            'target_user_id': admin_og2.id_role,
            'justification': 'Cross-org attempt',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_request_admin_demotion_missing_justification(self):
        """Test error when justification is missing."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        target_admin = AdminOrganismeFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        response = client.post('/api/validations/request_admin_demotion/', {
            'target_user_id': target_admin.id_role,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_admin_demotion_duplicate_pending(self):
        """Test error when pending request already exists."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        target_admin = AdminOrganismeFactory(id_organisme=organisme)
        client = APIClient()
        client.force_authenticate(user=admin_og)

        client.post('/api/validations/request_admin_demotion/', {
            'target_user_id': target_admin.id_role,
            'justification': 'First request',
        })

        response = client.post('/api/validations/request_admin_demotion/', {
            'target_user_id': target_admin.id_role,
            'justification': 'Duplicate',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST
