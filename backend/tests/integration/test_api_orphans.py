"""
Integration tests for the orphans admin endpoint (/api/admin/orphans/).

Couvre la page Administration > Orphelins qui remplace l'ancien audit
hebdomadaire par email : liste des sites sans utilisateur et des plans sans site,
avec scope par role.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, RoleFactory,
    SiteFactory, CorRoleSiteFactory, CorOgSiteFactory,
)
from tests.factories.plans import PlanGestionFactory


ORPHANS_URL = '/api/admin/orphans/'
COUNTS_URL = '/api/admin/orphans/counts/'


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
@pytest.mark.integration
class TestAdminOrphansEndpoint:
    """Tests for /api/admin/orphans/."""

    def test_unauthenticated_denied(self, api_client):
        """Un utilisateur non authentifie ne peut pas acceder aux orphelins."""
        response = api_client.get(ORPHANS_URL)
        assert response.status_code in (
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN,
        )

    def test_regular_user_forbidden(self, api_client):
        """Un simple utilisateur (non admin) recoit 403."""
        api_client.force_authenticate(user=RoleFactory())
        assert api_client.get(ORPHANS_URL).status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_sees_orphaned_sites_only(self, api_client):
        """Super admin : sites actifs sans utilisateur, hors sites peuples/inactifs."""
        admin = SuperAdminFactory()
        orphan = SiteFactory(active=True)

        # Site avec un utilisateur -> pas orphelin
        linked = SiteFactory(active=True)
        CorRoleSiteFactory(id_site=linked, id_role=RoleFactory())

        # Site inactif sans utilisateur -> ignore
        inactive = SiteFactory(active=False)

        api_client.force_authenticate(user=admin)
        response = api_client.get(ORPHANS_URL)

        assert response.status_code == status.HTTP_200_OK
        site_ids = {s['id_site'] for s in response.data['sites']}
        assert orphan.id_site in site_ids
        assert linked.id_site not in site_ids
        assert inactive.id_site not in site_ids

    def test_super_admin_sees_orphaned_plans(self, api_client):
        """Super admin : plans sans aucun site, hors plans avec site."""
        admin = SuperAdminFactory()
        orphan_plan = PlanGestionFactory()  # aucun site
        plan_with_site = PlanGestionFactory(sites=[SiteFactory()])

        api_client.force_authenticate(user=admin)
        response = api_client.get(ORPHANS_URL)

        plan_ids = {p['id_pg'] for p in response.data['plans']}
        assert orphan_plan.id_pg in plan_ids
        assert plan_with_site.id_pg not in plan_ids

    def test_admin_og_scoped_to_org_and_no_plans(self, api_client):
        """Admin_og : uniquement les sites orphelins de son organisme, aucun plan."""
        admin = AdminOrganismeFactory()

        # Site orphelin rattache a l'organisme de l'admin -> visible
        my_site = SiteFactory(active=True)
        CorOgSiteFactory(id_site=my_site, uuid_og=admin.id_organisme)

        # Site orphelin non rattache a son organisme -> invisible
        other_site = SiteFactory(active=True)

        # Plan orphelin -> reserve a l'acces global, invisible pour admin_og
        PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get(ORPHANS_URL)

        assert response.status_code == status.HTTP_200_OK
        site_ids = {s['id_site'] for s in response.data['sites']}
        assert my_site.id_site in site_ids
        assert other_site.id_site not in site_ids
        assert response.data['plans'] == []
        assert response.data['plans_count'] == 0

    def test_counts_endpoint_matches_list(self, api_client):
        """Le compteur (badge) doit refleter la liste complete."""
        admin = SuperAdminFactory()
        SiteFactory(active=True)
        SiteFactory(active=True)
        PlanGestionFactory()  # plan orphelin

        api_client.force_authenticate(user=admin)
        counts = api_client.get(COUNTS_URL)
        full = api_client.get(ORPHANS_URL)

        assert counts.status_code == status.HTTP_200_OK
        assert counts.data['sites_count'] == full.data['sites_count']
        assert counts.data['plans_count'] == full.data['plans_count']
        assert counts.data['total'] == counts.data['sites_count'] + counts.data['plans_count']
