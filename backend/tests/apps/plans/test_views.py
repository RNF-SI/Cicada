"""
Unit tests for Plans ViewSet.
Tests CRUD operations, permissions, filtering, and custom actions.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.plans.models import PlanGestion, CorSitePg, CorPgFichier
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, OrganismeFactory, SiteFactory, CorRoleSiteFactory,
    CorOgSiteFactory
)
from tests.factories.plans import (
    PlanGestionFactory, PlanGestionValideFactory, PlanGestionArchiveFactory,
    CorSitePgFactory, CorPgFichierFactory
)


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetList:
    """Tests for PlanGestionViewSet list action."""

    def test_list_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list plans."""
        response = api_client.get('/api/plans/plans/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_super_admin_sees_all(self, api_client):
        """Test super admin can see all plans regardless of status."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Draft Plan', statut='draft')
        PlanGestionFactory(nom='Valid Plan', statut='valide')
        PlanGestionFactory(nom='Archive Plan', statut='archive')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/')

        assert response.status_code == status.HTTP_200_OK
        # Super admin sees all 3 plans
        assert response.data['pagination']['count'] >= 3

    def test_list_regular_user_denied(self, api_client):
        """Test regular users cannot access plans list (requires IsReferent)."""
        user = RoleFactory()  # Regular utilisateur
        PlanGestionFactory(nom='Draft Plan', statut='draft')
        PlanGestionFactory(nom='Valid Plan', statut='valide')

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/plans/plans/')

        # Regular users are denied - ViewSet requires IsReferent permission
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_referent_sees_assigned_sites_plans(self, api_client):
        """Test referent sees plans for their assigned sites."""
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        plan = PlanGestionFactory(nom='Referent Plan', statut='draft')
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        api_client.force_authenticate(user=referent)
        response = api_client.get('/api/plans/plans/')

        assert response.status_code == status.HTTP_200_OK
        plan_names = [p['nom'] for p in response.data['results']]
        assert 'Referent Plan' in plan_names

    def test_list_admin_og_sees_organisme_plans(self, api_client):
        """Test admin organisme sees plans for their organisation's sites."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)

        plan = PlanGestionFactory(nom='Org Plan', statut='draft')
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        api_client.force_authenticate(user=admin_og)
        response = api_client.get('/api/plans/plans/')

        assert response.status_code == status.HTTP_200_OK
        plan_names = [p['nom'] for p in response.data['results']]
        assert 'Org Plan' in plan_names


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetCreate:
    """Tests for PlanGestionViewSet create action."""

    def test_create_plan_referent(self, api_client):
        """Test referent can create a plan."""
        referent = ReferentFactory()
        site = SiteFactory()
        # Make user a real referent by creating validated site assignment
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=referent)
        response = api_client.post('/api/plans/plans/', {
            'nom': 'New Test Plan',
            'statut': 'draft',
            'annee_debut': 2024,
            'annee_fin': 2034
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom'] == 'New Test Plan'
        assert response.data['statut'] == 'draft'

    def test_create_plan_sets_creator(self, api_client):
        """Test that plan creator is automatically set."""
        referent = ReferentFactory()
        site = SiteFactory()
        # Make user a real referent by creating validated site assignment
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=referent)
        response = api_client.post('/api/plans/plans/', {
            'nom': 'Creator Test Plan',
            'statut': 'draft'
        })

        assert response.status_code == status.HTTP_201_CREATED
        # Get the plan by name since we just created it
        plan = PlanGestion.objects.get(nom='Creator Test Plan')
        assert plan.id_utilisateur_ajout == referent

    def test_create_plan_regular_user_denied(self, api_client):
        """Test regular users cannot create plans."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/plans/plans/', {
            'nom': 'Unauthorized Plan',
            'statut': 'draft'
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_plan_with_years(self, api_client):
        """Test creating plan with year range."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/plans/plans/', {
            'nom': 'Year Range Plan',
            'statut': 'draft',
            'annee_debut': 2024,
            'annee_fin': 2034,
            'version': '1.0'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['annee_debut'] == 2024
        assert response.data['annee_fin'] == 2034


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetRetrieve:
    """Tests for PlanGestionViewSet retrieve action."""

    def test_retrieve_plan(self, api_client):
        """Test retrieving a single plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(nom='Detail Test Plan')

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/plans/plans/{plan.id_pg}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom'] == 'Detail Test Plan'

    def test_retrieve_nonexistent_plan(self, api_client):
        """Test retrieving a non-existent plan."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetUpdate:
    """Tests for PlanGestionViewSet update action."""

    def test_update_plan(self, api_client):
        """Test updating a plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(nom='Original Name')

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/plans/plans/{plan.id_pg}/', {
            'nom': 'Updated Name'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom'] == 'Updated Name'

    def test_update_plan_sets_modifier(self, api_client):
        """Test that plan modifier is automatically set."""
        admin = SuperAdminFactory()
        other_admin = SuperAdminFactory()
        plan = PlanGestionFactory(id_utilisateur_ajout=other_admin)

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/plans/plans/{plan.id_pg}/', {
            'nom': 'Modifier Test'
        })

        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.id_utilisateur_maj == admin

    def test_update_plan_status(self, api_client):
        """Test updating plan status."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/plans/plans/{plan.id_pg}/', {
            'statut': 'valide'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['statut'] == 'valide'


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetDelete:
    """Tests for PlanGestionViewSet delete action."""

    def test_delete_plan(self, api_client):
        """Test deleting a plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        plan_id = plan.id_pg

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/plans/plans/{plan_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not PlanGestion.objects.filter(id_pg=plan_id).exists()

    def test_delete_plan_cascades_sites(self, api_client):
        """Test deleting plan removes site associations."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site)
        plan_id = plan.id_pg

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/plans/plans/{plan_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CorSitePg.objects.filter(plan_de_gestion_id=plan_id).exists()


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetFilters:
    """Tests for PlanGestionViewSet filters."""

    def test_filter_by_statut(self, api_client):
        """Test filtering plans by status."""
        admin = SuperAdminFactory()
        PlanGestionFactory(statut='draft')
        PlanGestionFactory(statut='valide')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?statut=valide')

        assert response.status_code == status.HTTP_200_OK
        for plan in response.data['results']:
            assert plan['statut'] == 'valide'

    def test_filter_by_annee_debut(self, api_client):
        """Test filtering plans by start year."""
        admin = SuperAdminFactory()
        PlanGestionFactory(annee_debut=2020)
        PlanGestionFactory(annee_debut=2025)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?annee_debut=2025')

        assert response.status_code == status.HTTP_200_OK
        for plan in response.data['results']:
            assert plan['annee_debut'] == 2025

    def test_search_by_nom(self, api_client):
        """Test searching plans by name."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Marais du Grosset')
        PlanGestionFactory(nom='Foret de Rambouillet')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?search=Marais')

        assert response.status_code == status.HTTP_200_OK
        assert any('Marais' in p['nom'] for p in response.data['results'])


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetGeoJSON:
    """Tests for PlanGestionViewSet GeoJSON actions."""

    def test_geojson_list(self, api_client):
        """Test GeoJSON list endpoint returns FeatureCollection."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/geojson_list/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['type'] == 'FeatureCollection'
        assert 'features' in response.data


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetOrdering:
    """Tests for PlanGestionViewSet ordering."""

    def test_ordering_by_date_maj(self, api_client):
        """Test ordering by modification date (default)."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Plan A')
        PlanGestionFactory(nom='Plan B')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/')

        assert response.status_code == status.HTTP_200_OK
        # Default ordering is -date_maj (most recent first)

    def test_ordering_by_nom(self, api_client):
        """Test ordering by name."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Zebra Plan')
        PlanGestionFactory(nom='Alpha Plan')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?ordering=nom')

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        if len(results) >= 2:
            assert results[0]['nom'] <= results[1]['nom']
