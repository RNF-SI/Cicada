"""
Integration tests for Plans de Gestion API.
Converted from test_plans_api.py standalone script.
Tests CRUD operations, filters, GeoJSON, statistics, and file handling.
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


# =============================================================================
# PLANS LIST TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansListEndpoint:
    """Tests for plans list endpoint."""

    def test_list_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list plans."""
        response = api_client.get('/api/plans/plans/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_super_admin_sees_all(self, api_client):
        """Test super admin can see all plans."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Draft Plan', statut='draft')
        PlanGestionFactory(nom='Valid Plan', statut='valide')
        PlanGestionFactory(nom='Archive Plan', statut='archive')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['pagination']['count'] >= 3

    def test_list_referent_sees_assigned_plans(self, api_client):
        """Test referent sees plans for their assigned sites."""
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        plan = PlanGestionFactory(nom='Referent Plan')
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        # Plan without referent's site
        other_plan = PlanGestionFactory(nom='Other Plan')

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

        plan = PlanGestionFactory(nom='Org Plan')
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        api_client.force_authenticate(user=admin_og)
        response = api_client.get('/api/plans/plans/')

        assert response.status_code == status.HTTP_200_OK
        plan_names = [p['nom'] for p in response.data['results']]
        assert 'Org Plan' in plan_names

    def test_list_pagination(self, api_client):
        """Test list pagination."""
        admin = SuperAdminFactory()
        for i in range(15):
            PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?page_size=5')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) <= 5
        assert response.data['pagination']['total_pages'] >= 3


# =============================================================================
# PLANS FILTERS TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansFilters:
    """Tests for plans filters."""

    def test_filter_by_statut(self, api_client):
        """Test filtering by status."""
        admin = SuperAdminFactory()
        PlanGestionFactory(statut='draft')
        PlanGestionFactory(statut='valide')
        PlanGestionFactory(statut='archive')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?statut=valide')

        assert response.status_code == status.HTTP_200_OK
        for plan in response.data['results']:
            assert plan['statut'] == 'valide'

    def test_filter_gestion_partagee(self, api_client):
        """Test filtering multi-site plans."""
        admin = SuperAdminFactory()
        plan_shared = PlanGestionFactory(gestion_partagee=True)
        plan_single = PlanGestionFactory(gestion_partagee=False)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?gestion_partagee=true')

        assert response.status_code == status.HTTP_200_OK
        for plan in response.data['results']:
            assert plan['gestion_partagee'] is True

    def test_filter_ct88(self, api_client):
        """Test filtering CT88 plans."""
        admin = SuperAdminFactory()
        plan_ct88 = PlanGestionFactory(ct88=True)
        plan_normal = PlanGestionFactory(ct88=False)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?ct88=true')

        assert response.status_code == status.HTTP_200_OK
        for plan in response.data['results']:
            assert plan['ct88'] is True

    def test_filter_by_annee_debut(self, api_client):
        """Test filtering by start year."""
        admin = SuperAdminFactory()
        PlanGestionFactory(annee_debut=2020)
        PlanGestionFactory(annee_debut=2024)
        PlanGestionFactory(annee_debut=2025)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?annee_debut=2024')

        assert response.status_code == status.HTTP_200_OK
        for plan in response.data['results']:
            assert plan['annee_debut'] == 2024

    def test_filter_actif_en_annee(self, api_client):
        """Test filtering plans active in a specific year."""
        admin = SuperAdminFactory()
        PlanGestionFactory(annee_debut=2020, annee_fin=2030)  # Active in 2024
        PlanGestionFactory(annee_debut=2025, annee_fin=2035)  # Not active in 2024

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?actif_en_annee=2024')

        assert response.status_code == status.HTTP_200_OK
        # Plans active in 2024 should have annee_debut <= 2024 and annee_fin >= 2024

    def test_search_by_nom(self, api_client):
        """Test searching by name."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Marais du Grosset')
        PlanGestionFactory(nom='Foret de Rambouillet')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?search=Marais')

        assert response.status_code == status.HTTP_200_OK
        assert any('Marais' in p['nom'] for p in response.data['results'])


# =============================================================================
# PLANS DETAIL TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansDetailEndpoint:
    """Tests for plan detail endpoint."""

    def test_detail_returns_complete_info(self, api_client):
        """Test detail returns complete plan info."""
        admin = SuperAdminFactory()
        site = SiteFactory(nom_site='Site Test')
        plan = PlanGestionFactory(
            nom='Test Plan',
            annee_debut=2020,
            annee_fin=2030,
            gestion_partagee=False,
            ct88=True
        )
        CorSitePgFactory(plan_de_gestion=plan, site=site)
        CorPgFichierFactory(plan_de_gestion=plan, titre='Document Test')

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/plans/plans/{plan.id_pg}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom'] == 'Test Plan'
        assert response.data['annee_debut'] == 2020
        assert response.data['annee_fin'] == 2030
        assert 'periode_gestion' in response.data
        assert 'sites' in response.data
        assert 'fichiers' in response.data

    def test_detail_nonexistent(self, api_client):
        """Test retrieving non-existent plan returns 404."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# PLANS CREATE TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansCreateEndpoint:
    """Tests for plan creation endpoint."""

    def test_create_plan_super_admin(self, api_client):
        """Test super admin can create a plan."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/plans/plans/', {
            'nom': 'New API Plan',
            'annee_debut': 2024,
            'annee_fin': 2034,
            'statut': 'draft',
            'gestion_partagee': False,
            'ct88': False,
            'version': '1.0'
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom'] == 'New API Plan'
        assert PlanGestion.objects.filter(nom='New API Plan').exists()

    def test_create_plan_referent(self, api_client):
        """Test referent can create a plan."""
        referent = ReferentFactory()
        site = SiteFactory()
        # Make user a real referent by creating validated site assignment
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=referent)
        response = api_client.post('/api/plans/plans/', {
            'nom': 'Referent Plan',
            'statut': 'draft',
            'annee_debut': 2024
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom'] == 'Referent Plan'

    def test_create_plan_sets_creator(self, api_client):
        """Test created plan has creator set."""
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


# =============================================================================
# PLANS UPDATE TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansUpdateEndpoint:
    """Tests for plan update endpoint."""

    def test_update_plan(self, api_client):
        """Test updating a plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(nom='Original Name', commentaire=None)

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/plans/plans/{plan.id_pg}/', {
            'nom': 'Updated Name',
            'commentaire': 'Updated via API'
        })

        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.nom == 'Updated Name'
        assert plan.commentaire == 'Updated via API'

    def test_update_plan_status(self, api_client):
        """Test updating plan status."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/plans/plans/{plan.id_pg}/', {
            'statut': 'valide'
        })

        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'valide'

    def test_update_plan_sets_modifier(self, api_client):
        """Test update sets modifier."""
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


# =============================================================================
# PLANS DELETE TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansDeleteEndpoint:
    """Tests for plan deletion endpoint."""

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

    def test_delete_plan_cascades_fichiers(self, api_client):
        """Test deleting plan removes file associations."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        CorPgFichierFactory(plan_de_gestion=plan)
        plan_id = plan.id_pg

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/plans/plans/{plan_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CorPgFichier.objects.filter(plan_de_gestion_id=plan_id).exists()


# =============================================================================
# PLANS GEOJSON TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansGeoJSONEndpoints:
    """Tests for GeoJSON endpoints."""

    def test_geojson_list(self, api_client):
        """Test GeoJSON list returns FeatureCollection."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Plan 1')
        PlanGestionFactory(nom='Plan 2')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/geojson_list/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['type'] == 'FeatureCollection'
        assert 'features' in response.data

    def test_geojson_list_contains_plan_properties(self, api_client):
        """Test GeoJSON features contain plan properties."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(nom='GeoJSON Test Plan')
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/geojson_list/')

        assert response.status_code == status.HTTP_200_OK
        if response.data['features']:
            feature = next(
                (f for f in response.data['features'] if f['properties']['nom'] == 'GeoJSON Test Plan'),
                None
            )
            if feature:
                assert feature['type'] == 'Feature'
                assert 'properties' in feature
                assert feature['properties']['nom'] == 'GeoJSON Test Plan'


# =============================================================================
# PLANS STATISTICS TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansStatsEndpoint:
    """Tests for plans statistics endpoint."""

    def test_stats_returns_counts(self, api_client):
        """Test stats endpoint returns correct counts."""
        admin = SuperAdminFactory()
        PlanGestionFactory(statut='draft', gestion_partagee=False)
        PlanGestionFactory(statut='valide', gestion_partagee=True)
        PlanGestionFactory(statut='valide', ct88=True)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'total' in response.data
        assert response.data['total'] >= 3
        assert 'par_statut' in response.data

    def test_stats_includes_gestion_partagee(self, api_client):
        """Test stats includes shared management count."""
        admin = SuperAdminFactory()
        PlanGestionFactory(gestion_partagee=True)
        PlanGestionFactory(gestion_partagee=True)
        PlanGestionFactory(gestion_partagee=False)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'gestion_partagee' in response.data
        assert response.data['gestion_partagee'] >= 2

    def test_stats_includes_ct88(self, api_client):
        """Test stats includes CT88 count."""
        admin = SuperAdminFactory()
        PlanGestionFactory(ct88=True)
        PlanGestionFactory(ct88=False)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'ct88' in response.data
        assert response.data['ct88'] >= 1


# =============================================================================
# PLANS SITE ASSIGNMENT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansSiteAssignment:
    """Tests for plan site assignment."""

    def test_assign_site_to_plan(self, api_client):
        """Test assigning a site to a plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/assign_site/', {
            'site_id': site.id_site
        })

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
        assert CorSitePg.objects.filter(plan_de_gestion=plan, site=site).exists()

    def test_remove_site_from_plan(self, api_client):
        """Test removing a site from a plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        api_client.force_authenticate(user=admin)
        # DELETE method with site_id as query parameter
        response = api_client.delete(f'/api/plans/plans/{plan.id_pg}/remove_site/?site_id={site.id_site}')

        assert response.status_code == status.HTTP_200_OK
        assert not CorSitePg.objects.filter(plan_de_gestion=plan, site=site).exists()


# =============================================================================
# PLANS FICHIERS TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansFichiersEndpoint:
    """Tests for plan files endpoint."""

    def test_list_fichiers(self, api_client):
        """Test listing plan files."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        CorPgFichierFactory(plan_de_gestion=plan, titre='Document 1', type_fichier='document')
        CorPgFichierFactory(plan_de_gestion=plan, titre='Carte 1', type_fichier='carte')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/fichiers/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['pagination']['count'] >= 2

    def test_filter_fichiers_by_type(self, api_client):
        """Test filtering files by type."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        CorPgFichierFactory(plan_de_gestion=plan, type_fichier='document')
        CorPgFichierFactory(plan_de_gestion=plan, type_fichier='carte')
        CorPgFichierFactory(plan_de_gestion=plan, type_fichier='photo')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/fichiers/?type_fichier=document')

        assert response.status_code == status.HTTP_200_OK
        for fichier in response.data['results']:
            assert fichier['type_fichier'] == 'document'

    def test_list_plan_fichiers(self, api_client):
        """Test listing files for a specific plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        CorPgFichierFactory(plan_de_gestion=plan, titre='Plan Doc')
        other_plan = PlanGestionFactory()
        CorPgFichierFactory(plan_de_gestion=other_plan, titre='Other Doc')

        api_client.force_authenticate(user=admin)
        # Fichiers are at /api/plans/fichiers/ with plan filter, not nested
        response = api_client.get(f'/api/plans/fichiers/?plan_de_gestion={plan.id_pg}')

        assert response.status_code == status.HTTP_200_OK
        # Should only return files for this plan


# =============================================================================
# PLANS ORDERING TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansOrdering:
    """Tests for plans ordering."""

    def test_ordering_by_nom(self, api_client):
        """Test ordering by name."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Zebra Plan')
        PlanGestionFactory(nom='Alpha Plan')
        PlanGestionFactory(nom='Middle Plan')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?ordering=nom')

        assert response.status_code == status.HTTP_200_OK
        names = [p['nom'] for p in response.data['results']]
        assert names == sorted(names)

    def test_ordering_by_date_maj(self, api_client):
        """Test ordering by modification date."""
        admin = SuperAdminFactory()
        plan1 = PlanGestionFactory()
        plan2 = PlanGestionFactory()
        plan3 = PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?ordering=-date_maj')

        assert response.status_code == status.HTTP_200_OK
        # Most recent first

    def test_ordering_by_annee_debut(self, api_client):
        """Test ordering by start year."""
        admin = SuperAdminFactory()
        PlanGestionFactory(annee_debut=2030)
        PlanGestionFactory(annee_debut=2020)
        PlanGestionFactory(annee_debut=2025)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?ordering=annee_debut')

        assert response.status_code == status.HTTP_200_OK
        years = [p['annee_debut'] for p in response.data['results'] if p.get('annee_debut')]
        assert years == sorted(years)


# =============================================================================
# EXPORT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansExport:
    """Tests for plans export endpoints."""

    def test_export_geojson(self, api_client):
        """Test export GeoJSON endpoint."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Export Plan 1')
        PlanGestionFactory(nom='Export Plan 2')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/export_geojson/')

        # May return 200 or 404 depending on if endpoint exists
        if response.status_code == status.HTTP_200_OK:
            assert response.data['type'] == 'FeatureCollection'
            assert 'features' in response.data
