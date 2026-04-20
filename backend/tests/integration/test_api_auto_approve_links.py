"""
Integration tests for the privileged-role auto-approval of link request endpoints.

Covers the 5 link types:
- site_access (POST /api/users/sites/{slug}/request_access/)
- referent_validation (POST /api/users/sites/{slug}/request_referent/)
- site_org_link (POST /api/users/sites/{slug}/request_org_link/)
- site_org_unlink (DELETE/POST /api/users/organismes/{org}/sites/{site}/)
- plan_site_link (POST /api/validations/request_plan_site_link/)

Privileged roles that auto-approve their own request:
- super_admin: always
- redacteur_principal: always
- admin_og: only if the link concerns their organisme
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.notifications.models import ValidationRequest
from apps.users.models import CorRoleSite, CorOgSite
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, RoleFactory,
    OrganismeFactory, SiteFactory, CorRoleSiteFactory, CorOgSiteFactory,
)
from tests.factories.plans import PlanGestionFactory


@pytest.fixture
def api_client():
    return APIClient()


def _redacteur_principal():
    """Build a Rédacteur Principal user (no dedicated factory)."""
    rp = RoleFactory(role_level='redacteur_principal', is_staff=True)
    return rp


# =============================================================================
# site_access
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteAccessAutoApprove:
    URL = '/api/users/sites/{slug}/request_access/'

    def test_super_admin_auto_approved(self, api_client):
        admin = SuperAdminFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL.format(slug=site.slug))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True
        vr = ValidationRequest.objects.get(id=response.data['id'])
        assert vr.status == 'approved'
        assert vr.validator == admin
        assert CorRoleSite.objects.filter(id_role=admin, id_site=site).exists()

    def test_redacteur_principal_auto_approved(self, api_client):
        rp = _redacteur_principal()
        site = SiteFactory()

        api_client.force_authenticate(user=rp)
        response = api_client.post(self.URL.format(slug=site.slug))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True

    def test_admin_og_in_scope_auto_approved(self, api_client):
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)
        admin = AdminOrganismeFactory(id_organisme=organisme)

        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL.format(slug=site.slug))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True

    def test_admin_og_out_of_scope_stays_pending(self, api_client):
        admin_org = OrganismeFactory()
        other_site = SiteFactory()  # not linked to admin_org
        admin = AdminOrganismeFactory(id_organisme=admin_org)

        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL.format(slug=other_site.slug))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is False
        vr = ValidationRequest.objects.get(id=response.data['id'])
        assert vr.status == 'pending'

    def test_regular_user_stays_pending(self, api_client):
        user = RoleFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=user)
        response = api_client.post(self.URL.format(slug=site.slug))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is False
        vr = ValidationRequest.objects.get(id=response.data['id'])
        assert vr.status == 'pending'


# =============================================================================
# referent_validation
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestReferentValidationAutoApprove:
    URL = '/api/users/sites/{slug}/request_referent/'

    def test_super_admin_auto_approved(self, api_client):
        admin = SuperAdminFactory()
        site = SiteFactory()
        # Need existing CorRoleSite for the request to be valid
        CorRoleSiteFactory(id_role=admin, id_site=site, referent=False)

        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL.format(slug=site.slug))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True
        cors = CorRoleSite.objects.get(id_role=admin, id_site=site)
        assert cors.referent is True
        assert cors.referent_valid is True

    def test_regular_user_stays_pending(self, api_client):
        user = RoleFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False)

        api_client.force_authenticate(user=user)
        response = api_client.post(self.URL.format(slug=site.slug))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is False


# =============================================================================
# site_org_link
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteOrgLinkAutoApprove:
    URL = '/api/users/sites/{slug}/request_org_link/'

    def test_super_admin_auto_approved(self, api_client):
        organisme = OrganismeFactory()
        admin = SuperAdminFactory(id_organisme=organisme)
        site = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL.format(slug=site.slug))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True
        assert CorOgSite.objects.filter(uuid_og=organisme, id_site=site).exists()

    def test_admin_og_for_own_org_auto_approved(self, api_client):
        organisme = OrganismeFactory()
        admin = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL.format(slug=site.slug))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True

    def test_regular_user_stays_pending(self, api_client):
        organisme = OrganismeFactory()
        user = RoleFactory(id_organisme=organisme)
        site = SiteFactory()

        api_client.force_authenticate(user=user)
        response = api_client.post(self.URL.format(slug=site.slug))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is False


# =============================================================================
# site_org_unlink
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteOrgUnlinkAutoApprove:
    """DELETE /api/users/organismes/{org_id}/sites/{site_id}/"""

    def _url(self, organisme, site):
        return f'/api/users/organismes/{organisme.id_organisme}/sites/{site.id_site}/'

    def test_super_admin_auto_approved(self, api_client):
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.delete(self._url(organisme, site))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True
        assert response.data['status'] == 'approved'
        assert not CorOgSite.objects.filter(uuid_og=organisme, id_site=site).exists()

    def test_admin_og_for_own_org_auto_approved(self, api_client):
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)
        admin = AdminOrganismeFactory(id_organisme=organisme)

        api_client.force_authenticate(user=admin)
        response = api_client.delete(self._url(organisme, site))

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True


# =============================================================================
# plan_site_link
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlanSiteLinkAutoApprove:
    URL = '/api/validations/request_plan_site_link/'

    def test_super_admin_auto_approved(self, api_client):
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL,
            {'plan_id': plan.id_pg, 'site_id': site.id_site},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True
        assert response.data['direct'] is True  # backward-compat field

    def test_admin_og_in_scope_auto_approved(self, api_client):
        organisme = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site)
        admin = AdminOrganismeFactory(id_organisme=organisme)
        plan = PlanGestionFactory()
        # Need plan/site link permission - admin must be a member or referent of plan/site
        # Use site_referent path: admin org has the site
        CorRoleSiteFactory(id_role=admin, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL,
            {'plan_id': plan.id_pg, 'site_id': site.id_site},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True

    def test_plan_referent_and_site_referent_auto_approved(self, api_client):
        """Plan referent + site referent has historical direct-link path; preserved."""
        user = RoleFactory()
        plan = PlanGestionFactory()
        site = SiteFactory()
        plan.referents.add(user)
        CorRoleSiteFactory(id_role=user, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            self.URL,
            {'plan_id': plan.id_pg, 'site_id': site.id_site},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is True

    def test_regular_user_member_stays_pending(self, api_client):
        """Plain plan member (no referent role) → request stays pending."""
        from apps.plans.models import CorRolePlan

        user = RoleFactory()
        plan = PlanGestionFactory()
        site = SiteFactory()
        CorRolePlan.objects.create(id_role=user, plan_de_gestion=plan)
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            self.URL,
            {'plan_id': plan.id_pg, 'site_id': site.id_site},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['auto_approved'] is False
