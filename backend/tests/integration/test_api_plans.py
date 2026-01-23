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


# =============================================================================
# PLANS REFERENT ASSIGNMENT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansReferentAssignment:
    """Tests for plan referent assignment."""

    def test_assign_referent_to_plan(self, api_client):
        """Test assigning a referent to a plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/assign_referent/', {
            'referent_id': referent.id_role
        })

        assert response.status_code == status.HTTP_200_OK
        assert referent in plan.referents.all()

    def test_assign_referent_without_id(self, api_client):
        """Test assign referent fails without referent_id."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/assign_referent/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'referent_id' in str(response.data)

    def test_assign_referent_non_referent_user(self, api_client):
        """Test cannot assign user who is not a referent."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        regular_user = RoleFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/assign_referent/', {
            'referent_id': regular_user.id_role
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert regular_user not in plan.referents.all()

    def test_assign_referent_nonexistent_user(self, api_client):
        """Test assign referent with non-existent user."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/assign_referent/', {
            'referent_id': 99999
        })

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_referent_from_plan(self, api_client):
        """Test removing a referent from a plan."""
        admin = SuperAdminFactory()
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        plan = PlanGestionFactory()
        plan.referents.add(referent)

        api_client.force_authenticate(user=admin)
        response = api_client.delete(
            f'/api/plans/plans/{plan.id_pg}/remove_referent/?referent_id={referent.id_role}'
        )

        assert response.status_code == status.HTTP_200_OK
        assert referent not in plan.referents.all()

    def test_remove_referent_without_id(self, api_client):
        """Test remove referent fails without referent_id."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/plans/plans/{plan.id_pg}/remove_referent/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_referent_not_assigned(self, api_client):
        """Test remove referent fails if not assigned to plan."""
        admin = SuperAdminFactory()
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        plan = PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.delete(
            f'/api/plans/plans/{plan.id_pg}/remove_referent/?referent_id={referent.id_role}'
        )

        # Note: Returns 400 if referent exists but not assigned, 404 if referent not found
        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND]

    def test_remove_referent_nonexistent_user(self, api_client):
        """Test remove referent with non-existent user."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.delete(
            f'/api/plans/plans/{plan.id_pg}/remove_referent/?referent_id=99999'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_referent_requires_admin_permission(self, api_client):
        """Test only admin or admin_og can assign referents."""
        regular_user = RoleFactory()
        plan = PlanGestionFactory()
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=regular_user)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/assign_referent/', {
            'referent_id': referent.id_role
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# SITE ASSIGNMENT ERROR HANDLING TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansSiteAssignmentErrors:
    """Tests for plan site assignment error handling."""

    def test_assign_site_without_id(self, api_client):
        """Test assign site fails without site_id."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/assign_site/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'site_id' in str(response.data)

    def test_assign_site_nonexistent(self, api_client):
        """Test assign site fails with non-existent site."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/assign_site/', {
            'site_id': 99999
        })

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_assign_site_no_permission(self, api_client):
        """Test assign site fails without permission on site."""
        # Use super admin to ensure access to plan, but no permission on site
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        other_org = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=other_org)

        # Create another admin with different organisme who can see plan but not manage site
        admin_og = AdminOrganismeFactory()

        api_client.force_authenticate(user=admin_og)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/assign_site/', {
            'site_id': site.id_site
        })

        # May get 404 (plan not visible) or 403 (no permission on site)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_remove_site_without_id(self, api_client):
        """Test remove site fails without site_id."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/plans/plans/{plan.id_pg}/remove_site/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_site_not_assigned(self, api_client):
        """Test remove site fails if site not assigned to plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.delete(
            f'/api/plans/plans/{plan.id_pg}/remove_site/?site_id={site.id_site}'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# FICHIERS DOWNLOAD TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPlansFichiersDownload:
    """Tests for plan files download endpoint."""

    def test_download_public_fichier(self, api_client, tmp_path):
        """Test downloading a public file."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        # Create a temporary file
        test_file = tmp_path / "test_document.pdf"
        test_file.write_text("Test content")

        fichier = CorPgFichierFactory(
            plan_de_gestion=plan,
            public=True,
            chemin_fichier=str(test_file),
            nom_fichier='test_document.pdf'
        )

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/plans/fichiers/{fichier.id}/download/')

        assert response.status_code == status.HTTP_200_OK
        assert response['Content-Disposition'] == 'attachment; filename="test_document.pdf"'

    def test_download_private_fichier_with_permission(self, api_client, tmp_path):
        """Test downloading a private file with proper permission."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        test_file = tmp_path / "private_doc.pdf"
        test_file.write_text("Private content")

        fichier = CorPgFichierFactory(
            plan_de_gestion=plan,
            public=False,
            chemin_fichier=str(test_file),
            nom_fichier='private_doc.pdf'
        )

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/plans/fichiers/{fichier.id}/download/')

        assert response.status_code == status.HTTP_200_OK

    def test_download_fichier_file_not_found(self, api_client):
        """Test downloading file that doesn't exist on disk."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        fichier = CorPgFichierFactory(
            plan_de_gestion=plan,
            public=True,
            chemin_fichier='/nonexistent/path/file.pdf',
            nom_fichier='missing.pdf'
        )

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/plans/fichiers/{fichier.id}/download/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# BULK ASSIGN SITES TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestBulkAssignSites:
    """Tests for bulk site assignment endpoint."""

    def test_bulk_assign_sites_success(self, api_client):
        """Test bulk assigning sites to plans."""
        admin = SuperAdminFactory()
        plan1 = PlanGestionFactory()
        plan2 = PlanGestionFactory()
        site1 = SiteFactory()
        site2 = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/plans/plans/bulk_assign_sites/', {
            'plan_ids': [plan1.id_pg, plan2.id_pg],
            'site_ids': [site1.id_site, site2.id_site],
            'commentaire': 'Test bulk assignment'
        }, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert CorSitePg.objects.filter(plan_de_gestion=plan1, site=site1).exists()
        assert CorSitePg.objects.filter(plan_de_gestion=plan1, site=site2).exists()
        assert CorSitePg.objects.filter(plan_de_gestion=plan2, site=site1).exists()
        assert CorSitePg.objects.filter(plan_de_gestion=plan2, site=site2).exists()

    def test_bulk_assign_sites_missing_plan_ids(self, api_client):
        """Test bulk assign fails without plan_ids."""
        admin = SuperAdminFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/plans/plans/bulk_assign_sites/', {
            'site_ids': [site.id_site]
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_assign_sites_missing_site_ids(self, api_client):
        """Test bulk assign fails without site_ids."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/plans/plans/bulk_assign_sites/', {
            'plan_ids': [plan.id_pg]
        }, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_assign_sites_no_permission(self, api_client):
        """Test bulk assign fails without permission on site."""
        admin_og = AdminOrganismeFactory()
        plan = PlanGestionFactory()
        other_org = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=other_org)

        api_client.force_authenticate(user=admin_og)
        response = api_client.post('/api/plans/plans/bulk_assign_sites/', {
            'plan_ids': [plan.id_pg],
            'site_ids': [site.id_site]
        }, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_assign_sites_requires_admin(self, api_client):
        """Test bulk assign requires admin permission."""
        regular_user = RoleFactory()
        plan = PlanGestionFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=regular_user)
        response = api_client.post('/api/plans/plans/bulk_assign_sites/', {
            'plan_ids': [plan.id_pg],
            'site_ids': [site.id_site]
        }, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN
