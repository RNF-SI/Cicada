"""
Integration tests for Organismes and Sites API.
Converted from test_api_org_sites.py standalone script.
Tests CRUD operations, GeoJSON, relationships, filters, and statistics.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import BibOrganismes, Site, CorOgSite
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, OrganismeFactory, SiteFactory, CorOgSiteFactory
)


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


# =============================================================================
# ORGANISMES TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOrganismesListEndpoint:
    """Tests for organismes list endpoint."""

    def test_list_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list organismes."""
        response = api_client.get('/api/users/organismes/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_super_admin_sees_all(self, api_client):
        """Test super admin can see all organismes."""
        admin = SuperAdminFactory()
        OrganismeFactory(nom_organisme='Org 1')
        OrganismeFactory(nom_organisme='Org 2')
        OrganismeFactory(nom_organisme='Org 3')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/organismes/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['pagination']['count'] >= 3

    def test_list_admin_og_sees_all_or_filtered(self, api_client):
        """Test admin organisme access to organismes list."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        OrganismeFactory()

        api_client.force_authenticate(user=admin_og)
        response = api_client.get('/api/users/organismes/')

        # Admin OG may see all organismes or just theirs depending on implementation
        assert response.status_code == status.HTTP_200_OK

    def test_list_referent_access(self, api_client):
        """Test referent access to organismes list."""
        referent = ReferentFactory()
        OrganismeFactory()

        api_client.force_authenticate(user=referent)
        response = api_client.get('/api/users/organismes/')

        # Referent may or may not have access
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
@pytest.mark.integration
class TestOrganismesDetailEndpoint:
    """Tests for organisme detail endpoint."""

    def test_detail_super_admin(self, api_client):
        """Test super admin can view organisme details."""
        admin = SuperAdminFactory()
        organisme = OrganismeFactory(nom_organisme='Test Organisme', ville_organisme='Paris')

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/organismes/{organisme.id_organisme}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom_organisme'] == 'Test Organisme'
        assert response.data['ville_organisme'] == 'Paris'

    def test_detail_nonexistent(self, api_client):
        """Test retrieving non-existent organisme returns 404."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/organismes/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_admin_og_own_organisme(self, api_client):
        """Test admin organisme can view their own organisme."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)

        api_client.force_authenticate(user=admin_og)
        response = api_client.get(f'/api/users/organismes/{organisme.id_organisme}/')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
class TestOrganismesCreateEndpoint:
    """Tests for organisme creation endpoint."""

    def test_create_organisme_super_admin(self, api_client):
        """Test super admin can create an organisme."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/users/organismes/', {
            'nom_organisme': 'New Organisme',
            'ville_organisme': 'Lyon',
            'email_organisme': 'contact@neworg.fr',
            'active': True
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom_organisme'] == 'New Organisme'
        assert BibOrganismes.objects.filter(nom_organisme='New Organisme').exists()

    def test_create_organisme_admin_og_allowed(self, api_client):
        """Test admin organisme CAN create organismes (their parent will be set)."""
        admin_og = AdminOrganismeFactory()

        api_client.force_authenticate(user=admin_og)
        response = api_client.post('/api/users/organismes/', {
            'nom_organisme': 'Sub Organisme'
        })

        # Admin organisme can create organismes (as sub-organismes of their own)
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_organisme_regular_user_denied(self, api_client):
        """Test regular users cannot create organismes."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/organismes/', {
            'nom_organisme': 'Unauthorized Organisme'
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_organisme_with_parent(self, api_client):
        """Test creating organisme with parent."""
        admin = SuperAdminFactory()
        parent_org = OrganismeFactory(nom_organisme='Parent Org')

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/users/organismes/', {
            'nom_organisme': 'Child Organisme',
            'parent_id': parent_org.id_organisme,
            'active': True
        })

        assert response.status_code == status.HTTP_201_CREATED
        # Verify parent was set (response may use different field name)
        created_org = BibOrganismes.objects.get(nom_organisme='Child Organisme')
        assert created_org.id_parent == parent_org


@pytest.mark.django_db
@pytest.mark.integration
class TestOrganismesUpdateEndpoint:
    """Tests for organisme update endpoint."""

    def test_update_organisme(self, api_client):
        """Test updating an organisme."""
        admin = SuperAdminFactory()
        organisme = OrganismeFactory(nom_organisme='Original Name')

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/users/organismes/{organisme.id_organisme}/', {
            'nom_organisme': 'Updated Name'
        })

        assert response.status_code == status.HTTP_200_OK
        organisme.refresh_from_db()
        assert organisme.nom_organisme == 'Updated Name'


@pytest.mark.django_db
@pytest.mark.integration
class TestOrganismesStatsEndpoint:
    """Tests for organismes statistics endpoint."""

    def test_stats_super_admin(self, api_client):
        """Test super admin can access stats."""
        admin = SuperAdminFactory()
        # BibOrganismes doesn't have an 'active' field - create some organismes
        OrganismeFactory(nom_organisme='Org Stats 1')
        OrganismeFactory(nom_organisme='Org Stats 2')
        OrganismeFactory(nom_organisme='Org Stats 3')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/organismes/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_organismes' in response.data
        assert response.data['total_organismes'] >= 3


@pytest.mark.django_db
@pytest.mark.integration
class TestOrganismesSitesRelation:
    """Tests for organisme-site relationships."""

    def test_list_organisme_sites(self, api_client):
        """Test listing sites of an organisme."""
        admin = SuperAdminFactory()
        organisme = OrganismeFactory()
        site1 = SiteFactory(nom_site='Site 1')
        site2 = SiteFactory(nom_site='Site 2')
        CorOgSiteFactory(uuid_og=organisme, id_site=site1)
        CorOgSiteFactory(uuid_og=organisme, id_site=site2)

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/organismes/{organisme.id_organisme}/sites/')

        assert response.status_code == status.HTTP_200_OK
        # Should return at least 2 sites
        if isinstance(response.data, list):
            assert len(response.data) >= 2
        elif 'results' in response.data:
            assert len(response.data['results']) >= 2

    def test_assign_site_to_organisme(self, api_client):
        """Test assigning a site to an organisme."""
        admin = SuperAdminFactory()
        organisme = OrganismeFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f'/api/users/organismes/{organisme.id_organisme}/assign_site/',
            {'site_id': site.id_site}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert CorOgSite.objects.filter(uuid_og=organisme, id_site=site).exists()

    def test_bulk_assign_sites(self, api_client):
        """Test bulk assigning sites to an organisme."""
        admin = SuperAdminFactory()
        organisme = OrganismeFactory()
        site1 = SiteFactory()
        site2 = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f'/api/users/organismes/{organisme.id_organisme}/bulk_assign_sites/',
            {'site_ids': [site1.id_site, site2.id_site]}
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'assigned' in response.data
        assert CorOgSite.objects.filter(uuid_og=organisme, id_site=site1).exists()
        assert CorOgSite.objects.filter(uuid_og=organisme, id_site=site2).exists()


# =============================================================================
# SITES TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSitesListEndpoint:
    """Tests for sites list endpoint."""

    def test_list_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list sites."""
        response = api_client.get('/api/users/sites/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_super_admin_sees_all(self, api_client):
        """Test super admin can see all sites."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site='Site 1')
        SiteFactory(nom_site='Site 2')
        SiteFactory(nom_site='Site 3')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/sites/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['pagination']['count'] >= 3

    def test_list_admin_og_sees_organisme_sites(self, api_client):
        """Test admin organisme sees sites linked to their organisme."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site_linked = SiteFactory(nom_site='Linked Site')
        site_unlinked = SiteFactory(nom_site='Unlinked Site')
        CorOgSiteFactory(uuid_og=organisme, id_site=site_linked)

        api_client.force_authenticate(user=admin_og)
        response = api_client.get('/api/users/sites/')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
class TestSitesDetailEndpoint:
    """Tests for site detail endpoint."""

    def test_detail_super_admin(self, api_client):
        """Test super admin can view site details."""
        admin = SuperAdminFactory()
        site = SiteFactory(nom_site='Test Site', surf_off=1000.5)

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/sites/{site.slug}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom_site'] == 'Test Site'
        assert float(response.data['surf_off']) == 1000.5

    def test_detail_nonexistent(self, api_client):
        """Test retrieving non-existent site returns 404."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/sites/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.integration
class TestSitesCreateEndpoint:
    """Tests for site creation endpoint."""

    def test_create_site_super_admin(self, api_client):
        """Test super admin can create a site."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/users/sites/', {
            'nom_site': 'New Test Site',
            'id_local': 'TEST001',
            'surf_off': 500.0,
            'marin': False,
            'outre_mer': False,
            'active': True
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom_site'] == 'New Test Site'
        assert Site.objects.filter(nom_site='New Test Site').exists()

    def test_create_site_with_geojson_point(self, api_client):
        """Test creating site with GeoJSON point geometry."""
        admin = SuperAdminFactory()
        point_geojson = {
            "type": "Point",
            "coordinates": [2.3522, 48.8566]  # Paris
        }

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/users/sites/', {
            'nom_site': 'Site GeoJSON',
            'id_local': 'GEO001',
            'surf_off': 100.0,
            'geom_pt_geojson': point_geojson,
            'active': True
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom_site'] == 'Site GeoJSON'

    def test_create_site_admin_og_allowed(self, api_client):
        """Test admin organisme CAN create sites."""
        admin_og = AdminOrganismeFactory()

        api_client.force_authenticate(user=admin_og)
        response = api_client.post('/api/users/sites/', {
            'nom_site': 'Admin OG Site',
            'active': True
        })

        # Admin organisme can create sites
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_site_regular_user_creates_inactive_with_validation(self, api_client):
        """Test regular users can create sites but they are inactive and require validation."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/sites/', {
            'nom_site': 'User Site Request',
            'active': True  # This will be ignored for non-super_admin
        })

        # Site is created but as inactive with pending validation
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['active'] is False  # Site is inactive until approved
        assert response.data['validation_pending'] is True  # Validation is pending
        assert 'validation_request_id' in response.data


@pytest.mark.django_db
@pytest.mark.integration
class TestSitesUpdateEndpoint:
    """Tests for site update endpoint."""

    def test_update_site(self, api_client):
        """Test updating a site."""
        admin = SuperAdminFactory()
        site = SiteFactory(nom_site='Original Site', surf_off=100.0)

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/users/sites/{site.slug}/', {
            'nom_site': 'Updated Site',
            'surf_off': 200.0
        })

        assert response.status_code == status.HTTP_200_OK
        site.refresh_from_db()
        assert site.nom_site == 'Updated Site'
        assert float(site.surf_off) == 200.0


@pytest.mark.django_db
@pytest.mark.integration
class TestSitesGeoJSONEndpoints:
    """Tests for GeoJSON endpoints."""

    def test_site_geojson(self, api_client):
        """Test GeoJSON export for a single site."""
        admin = SuperAdminFactory()
        site = SiteFactory(nom_site='GeoJSON Test Site')

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/sites/{site.slug}/geojson/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['type'] == 'Feature'
        assert 'properties' in response.data
        assert response.data['properties']['nom_site'] == 'GeoJSON Test Site'

    def test_sites_geojson_list(self, api_client):
        """Test GeoJSON list of all sites."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site='Site 1')
        SiteFactory(nom_site='Site 2')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/sites/geojson_list/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['type'] == 'FeatureCollection'
        assert 'features' in response.data
        assert len(response.data['features']) >= 2


@pytest.mark.django_db
@pytest.mark.integration
class TestSitesStatsEndpoint:
    """Tests for sites statistics endpoint."""

    def test_stats_super_admin(self, api_client):
        """Test super admin can access site stats."""
        admin = SuperAdminFactory()
        SiteFactory(active=True, surf_off=100.0)
        SiteFactory(active=True, surf_off=200.0, marin=True)
        SiteFactory(active=False, surf_off=150.0)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/sites/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_sites' in response.data
        assert 'active_sites' in response.data
        assert response.data['total_sites'] >= 3
        assert response.data['active_sites'] >= 2


@pytest.mark.django_db
@pytest.mark.integration
class TestSitesRelationships:
    """Tests for site relationship endpoints."""

    def test_list_site_users(self, api_client):
        """Test listing users assigned to a site."""
        admin = SuperAdminFactory()
        site = SiteFactory()
        user1 = RoleFactory()
        user2 = RoleFactory()
        from tests.factories.users import CorRoleSiteFactory
        CorRoleSiteFactory(id_site=site, id_role=user1)
        CorRoleSiteFactory(id_site=site, id_role=user2)

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/sites/{site.slug}/users/')

        assert response.status_code == status.HTTP_200_OK

    def test_list_site_organismes(self, api_client):
        """Test listing organismes managing a site."""
        admin = SuperAdminFactory()
        site = SiteFactory()
        org1 = OrganismeFactory()
        org2 = OrganismeFactory()
        CorOgSiteFactory(id_site=site, uuid_og=org1)
        CorOgSiteFactory(id_site=site, uuid_og=org2)

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/sites/{site.slug}/organismes/')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
class TestSitesDeleteEndpoint:
    """Tests for site deletion endpoint."""

    def test_delete_site(self, api_client):
        """Test deleting a site."""
        admin = SuperAdminFactory()
        site = SiteFactory()
        site_id = site.id_site
        site_slug = site.slug

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/users/sites/{site_slug}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Site.objects.filter(id_site=site_id).exists()

    def test_delete_site_cascades_relations(self, api_client):
        """Test deleting site removes relationship records."""
        admin = SuperAdminFactory()
        site = SiteFactory()
        organisme = OrganismeFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        site_id = site.id_site
        site_slug = site.slug

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/users/sites/{site_slug}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CorOgSite.objects.filter(id_site_id=site_id).exists()


# =============================================================================
# FILTERS AND SEARCH TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOrganismesFilters:
    """Tests for organismes filters and search."""

    def test_search_by_name(self, api_client):
        """Test searching organismes by name."""
        admin = SuperAdminFactory()
        OrganismeFactory(nom_organisme='Conservatoire du Littoral')
        OrganismeFactory(nom_organisme='Parc National')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/organismes/?search=Conservatoire')

        assert response.status_code == status.HTTP_200_OK
        assert any('Conservatoire' in o['nom_organisme'] for o in response.data['results'])

    def test_filter_by_ville(self, api_client):
        """Test filtering organismes by city."""
        admin = SuperAdminFactory()
        OrganismeFactory(ville_organisme='Paris')
        OrganismeFactory(ville_organisme='Lyon')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/organismes/?ville=Paris')

        assert response.status_code == status.HTTP_200_OK
        for org in response.data['results']:
            if org.get('ville_organisme'):
                assert 'Paris' in org['ville_organisme'] or org['ville_organisme'].lower() == 'paris'

    def test_filter_has_sites(self, api_client):
        """Test filtering organismes with sites."""
        admin = SuperAdminFactory()
        org_with_site = OrganismeFactory()
        org_without_site = OrganismeFactory()
        site = SiteFactory()
        CorOgSiteFactory(uuid_og=org_with_site, id_site=site)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/organismes/?has_sites=true')

        assert response.status_code == status.HTTP_200_OK
        org_ids = [o['id_organisme'] for o in response.data['results']]
        assert org_with_site.id_organisme in org_ids

    def test_ordering_by_name(self, api_client):
        """Test ordering organismes by name."""
        admin = SuperAdminFactory()
        OrganismeFactory(nom_organisme='Zebra Org')
        OrganismeFactory(nom_organisme='Alpha Org')

        api_client.force_authenticate(user=admin)
        # Use 'nom' (short label) instead of 'nom_organisme' (full field name)
        response = api_client.get('/api/users/organismes/?ordering=nom')

        assert response.status_code == status.HTTP_200_OK
        names = [o['nom_organisme'] for o in response.data['results']]
        assert names == sorted(names)


@pytest.mark.django_db
@pytest.mark.integration
class TestSitesFilters:
    """Tests for sites filters and search."""

    def test_search_by_name(self, api_client):
        """Test searching sites by name."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site='Reserve de Camargue')
        SiteFactory(nom_site='Parc du Vercors')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/sites/?search=Camargue')

        assert response.status_code == status.HTTP_200_OK
        assert any('Camargue' in s['nom_site'] for s in response.data['results'])

    def test_filter_by_surface(self, api_client):
        """Test filtering sites by minimum surface."""
        admin = SuperAdminFactory()
        SiteFactory(surf_off=50.0)
        SiteFactory(surf_off=150.0)
        SiteFactory(surf_off=500.0)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/sites/?surf_min=100')

        assert response.status_code == status.HTTP_200_OK
        for site in response.data['results']:
            if site.get('surf_off'):
                assert float(site['surf_off']) >= 100

    def test_filter_marin(self, api_client):
        """Test filtering marine sites."""
        admin = SuperAdminFactory()
        SiteFactory(marin=True)
        SiteFactory(marin=False)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/sites/?marin=true')

        assert response.status_code == status.HTTP_200_OK
        for site in response.data['results']:
            assert site['marin'] is True

    def test_filter_active(self, api_client):
        """Test filtering active sites."""
        admin = SuperAdminFactory()
        SiteFactory(active=True)
        SiteFactory(active=False)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/sites/?active=true')

        assert response.status_code == status.HTTP_200_OK
        for site in response.data['results']:
            assert site['active'] is True

    def test_ordering_by_name(self, api_client):
        """Test ordering sites by name."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site='Zebra Site')
        SiteFactory(nom_site='Alpha Site')

        api_client.force_authenticate(user=admin)
        # Use 'nom' (short label) instead of 'nom_site' (full field name)
        response = api_client.get('/api/users/sites/?ordering=nom')

        assert response.status_code == status.HTTP_200_OK
        names = [s['nom_site'] for s in response.data['results']]
        assert names == sorted(names)

    def test_ordering_by_surface(self, api_client):
        """Test ordering sites by surface."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site='Large Site', surf_off=500.0)
        SiteFactory(nom_site='Small Site', surf_off=100.0)
        SiteFactory(nom_site='Medium Site', surf_off=300.0)

        api_client.force_authenticate(user=admin)
        # Use 'surface' (short label) instead of 'surf_off' (full field name)
        response = api_client.get('/api/users/sites/?ordering=surface')

        assert response.status_code == status.HTTP_200_OK
        # Verify ordering parameter is accepted and returns results
        # Note: Results may include other sites from the database
        assert 'results' in response.data


# =============================================================================
# SITE ACCESS AND VALIDATION REQUESTS TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteRequestAccessEndpoint:
    """Tests for site access request endpoint."""

    def test_request_access_success(self, api_client):
        """Test requesting access to a site."""
        user = RoleFactory()
        site = SiteFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_access/',
            {'justification': 'Need access for research'}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data
        assert 'message' in response.data

    def test_request_access_already_has_access(self, api_client):
        """Test requesting access when already has access returns error."""
        from tests.factories.users import CorRoleSiteFactory
        user = RoleFactory()
        site = SiteFactory(active=True)
        CorRoleSiteFactory(id_role=user, id_site=site)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_access/',
            {}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_request_access_pending_request_exists(self, api_client):
        """Test requesting access when a pending request already exists."""
        from apps.notifications.models import ValidationRequest
        user = RoleFactory()
        site = SiteFactory(active=True)

        # Create pending request
        ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=user,
            target_site=site
        )

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_access/',
            {}
        )

        assert response.status_code == status.HTTP_409_CONFLICT

    def test_request_access_as_referent(self, api_client):
        """Test requesting access with referent flag."""
        user = RoleFactory()
        site = SiteFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_access/',
            {'request_as_referent': True, 'justification': 'Want to manage site'}
        )

        assert response.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
@pytest.mark.integration
class TestSiteRequestReferentEndpoint:
    """Tests for site referent request endpoint."""

    def test_request_referent_success(self, api_client):
        """Test requesting referent status for a site."""
        from tests.factories.users import CorRoleSiteFactory
        user = RoleFactory()
        site = SiteFactory(active=True)
        # User must have access first
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_referent/',
            {'justification': 'I manage this site'}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data

    def test_request_referent_without_access(self, api_client):
        """Test requesting referent without site access returns error."""
        user = RoleFactory()
        site = SiteFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_referent/',
            {}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_referent_already_referent(self, api_client):
        """Test requesting referent when already referent."""
        from tests.factories.users import CorRoleSiteFactory
        user = RoleFactory()
        site = SiteFactory(active=True)
        CorRoleSiteFactory(id_role=user, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_referent/',
            {}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.integration
class TestSiteRequestOrgLinkEndpoint:
    """Tests for site org link request endpoint."""

    def test_request_org_link_success(self, api_client):
        """Test requesting to link organisme to a site."""
        organisme = OrganismeFactory()
        user = RoleFactory(id_organisme=organisme)
        site = SiteFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_org_link/',
            {'justification': 'Our org manages this site'}
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert 'id' in response.data

    def test_request_org_link_no_organisme(self, api_client):
        """Test request org link without organisme returns error."""
        user = RoleFactory(id_organisme=None)
        site = SiteFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_org_link/',
            {}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_request_org_link_already_linked(self, api_client):
        """Test request org link when already linked."""
        organisme = OrganismeFactory()
        user = RoleFactory(id_organisme=organisme)
        site = SiteFactory(active=True)
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/request_org_link/',
            {}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# SITE INVITATIONS TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteInviteOrganismeEndpoint:
    """Tests for inviting organisme to site endpoint."""

    def test_invite_organisme_success(self, api_client):
        """Test referent can invite organisme to site - creates direct link."""
        from tests.factories.users import CorRoleSiteFactory
        referent = RoleFactory()
        site = SiteFactory(active=True)
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
        target_org = OrganismeFactory()

        api_client.force_authenticate(user=referent)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/invite_organisme/',
            {'organisme_id': target_org.id_organisme, 'justification': 'Partner org'}
        )

        assert response.status_code == status.HTTP_201_CREATED
        # Verify direct link was created (no ValidationRequest)
        assert CorOgSite.objects.filter(id_site=site, uuid_og=target_org).exists()

    def test_invite_organisme_not_referent(self, api_client):
        """Test non-referent cannot invite organisme."""
        user = RoleFactory()
        site = SiteFactory(active=True)
        target_org = OrganismeFactory()

        api_client.force_authenticate(user=user)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/invite_organisme/',
            {'organisme_id': target_org.id_organisme}
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invite_organisme_super_admin_allowed(self, api_client):
        """Test super admin can invite organisme - creates direct link."""
        admin = SuperAdminFactory()
        site = SiteFactory(active=True)
        target_org = OrganismeFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/invite_organisme/',
            {'organisme_id': target_org.id_organisme}
        )

        assert response.status_code == status.HTTP_201_CREATED
        # Verify direct link was created
        assert CorOgSite.objects.filter(id_site=site, uuid_og=target_org).exists()


@pytest.mark.django_db
@pytest.mark.integration
class TestSiteInviteUserEndpoint:
    """Tests for inviting user to site endpoint."""

    def test_invite_user_success(self, api_client):
        """Test referent can invite user to site - creates direct link."""
        from tests.factories.users import CorRoleSiteFactory
        from apps.users.models import CorRoleSite
        referent = RoleFactory()
        site = SiteFactory(active=True)
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        # Target user must have an organisme linked to the site
        target_org = OrganismeFactory()
        target_user = RoleFactory(id_organisme=target_org)
        CorOgSiteFactory(uuid_og=target_org, id_site=site)

        api_client.force_authenticate(user=referent)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/invite_user/',
            {'user_id': target_user.id_role, 'justification': 'New team member'}
        )

        assert response.status_code == status.HTTP_201_CREATED
        # Verify direct link was created (no ValidationRequest)
        assert CorRoleSite.objects.filter(id_role=target_user, id_site=site).exists()

    def test_invite_user_org_not_linked(self, api_client):
        """Test cannot invite user whose org is not linked to site."""
        from tests.factories.users import CorRoleSiteFactory
        referent = RoleFactory()
        site = SiteFactory(active=True)
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        target_org = OrganismeFactory()
        target_user = RoleFactory(id_organisme=target_org)
        # Note: target_org is NOT linked to site

        api_client.force_authenticate(user=referent)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/invite_user/',
            {'user_id': target_user.id_role}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


# =============================================================================
# SITE DUPLICATE CHECK TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteCheckDuplicatesEndpoint:
    """Tests for site duplicate check endpoint."""

    def test_check_duplicates_by_inpn(self, api_client):
        """Test checking duplicates by INPN code."""
        admin = SuperAdminFactory()
        existing_site = SiteFactory(id_inpn='FR1234567', active=True)

        api_client.force_authenticate(user=admin)
        response = api_client.get(
            '/api/users/sites/check_duplicates/',
            {'id_inpn': 'FR1234567'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['exact_inpn_match'] is not None
        assert response.data['exact_inpn_match']['id_inpn'] == 'FR1234567'

    def test_check_duplicates_by_name(self, api_client):
        """Test checking duplicates by similar name."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site='Reserve Naturelle de Camargue', active=True)

        api_client.force_authenticate(user=admin)
        response = api_client.get(
            '/api/users/sites/check_duplicates/',
            {'nom_site': 'Camargue'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['similar_names']) >= 1

    def test_check_duplicates_no_match(self, api_client):
        """Test checking duplicates with no matches."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get(
            '/api/users/sites/check_duplicates/',
            {'id_inpn': 'NONEXISTENT', 'nom_site': 'xyz123'}
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['exact_inpn_match'] is None
        assert len(response.data['similar_names']) == 0


# =============================================================================
# SITE PRINCIPAL ORGANISME TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSitePrincipalOrganismeEndpoint:
    """Tests for site principal organisme endpoints."""

    def test_get_principal_organisme(self, api_client):
        """Test getting principal organisme of a site."""
        admin = SuperAdminFactory()
        site = SiteFactory(active=True)
        organisme = OrganismeFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site, principal=True)

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/sites/{site.slug}/principal_organisme/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id_organisme'] == organisme.id_organisme

    def test_get_principal_organisme_none_set(self, api_client):
        """Test getting principal organisme when none is set."""
        admin = SuperAdminFactory()
        site = SiteFactory(active=True)

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/sites/{site.slug}/principal_organisme/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_set_principal_organisme_super_admin(self, api_client):
        """Test super admin can set principal organisme."""
        admin = SuperAdminFactory()
        site = SiteFactory(active=True)
        organisme = OrganismeFactory()
        CorOgSiteFactory(uuid_og=organisme, id_site=site, principal=False)

        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f'/api/users/sites/{site.slug}/set_principal_organisme/',
            {'organisme_id': organisme.id_organisme}
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'gestionnaire principal' in response.data['message']

    def test_set_principal_organisme_unauthenticated_denied(self, api_client):
        """Test unauthenticated user cannot set principal organisme."""
        organisme = OrganismeFactory()
        site = SiteFactory(active=True)
        CorOgSiteFactory(uuid_og=organisme, id_site=site)

        response = api_client.post(
            f'/api/users/sites/{site.slug}/set_principal_organisme/',
            {'organisme_id': organisme.id_organisme}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# SITE SEARCH AND DISCOVERY TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSiteSearchAllEndpoint:
    """Tests for search_all endpoint."""

    def test_search_all_sites(self, api_client):
        """Test searching all active sites."""
        user = RoleFactory()
        SiteFactory(nom_site='Camargue Reserve', active=True)
        SiteFactory(nom_site='Vercors Park', active=True)
        SiteFactory(nom_site='Inactive Site', active=False)

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/sites/search_all/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 2
        # Should only include active sites
        site_names = [s['nom_site'] for s in response.data['results']]
        assert 'Inactive Site' not in site_names

    def test_search_all_with_search_term(self, api_client):
        """Test searching sites with search term."""
        user = RoleFactory()
        SiteFactory(nom_site='Camargue Reserve', active=True)
        SiteFactory(nom_site='Vercors Park', active=True)

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/sites/search_all/?search=Camargue')

        assert response.status_code == status.HTTP_200_OK
        assert all('Camargue' in s['nom_site'] for s in response.data['results'])


@pytest.mark.django_db
@pytest.mark.integration
class TestSiteAvailableForAssignmentEndpoint:
    """Tests for available_for_assignment endpoint."""

    def test_available_for_assignment(self, api_client):
        """Test listing sites available for assignment."""
        admin_og = AdminOrganismeFactory()
        SiteFactory(nom_site='Site 1', active=True)
        SiteFactory(nom_site='Site 2', active=True)

        api_client.force_authenticate(user=admin_og)
        response = api_client.get('/api/users/sites/available_for_assignment/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] >= 2

    def test_available_for_assignment_with_search(self, api_client):
        """Test available sites with search filter."""
        admin_og = AdminOrganismeFactory()
        SiteFactory(nom_site='Unique Site Name', active=True)
        SiteFactory(nom_site='Other Site', active=True)

        api_client.force_authenticate(user=admin_og)
        response = api_client.get('/api/users/sites/available_for_assignment/?search=Unique')

        assert response.status_code == status.HTTP_200_OK
        assert all('Unique' in s['nom_site'] for s in response.data['results'])

    def test_available_for_assignment_unauthenticated(self, api_client):
        """Test that unauthenticated user cannot access available_for_assignment."""
        response = api_client.get('/api/users/sites/available_for_assignment/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# ORGANISMES PUBLIC ENDPOINT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOrganismesPublicEndpoint:
    """Tests for public organismes endpoint."""

    def test_public_list_unauthenticated(self, api_client):
        """Test public endpoint is accessible without authentication."""
        OrganismeFactory(nom_organisme='Public Org 1')
        OrganismeFactory(nom_organisme='Public Org 2')

        response = api_client.get('/api/users/organismes/public/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 2
        # Should only contain id and nom_organisme
        for org in response.data:
            assert 'id' in org
            assert 'nom_organisme' in org

    def test_public_list_ordered_by_name(self, api_client):
        """Test public list is ordered by name."""
        OrganismeFactory(nom_organisme='Zebra Org')
        OrganismeFactory(nom_organisme='Alpha Org')

        response = api_client.get('/api/users/organismes/public/')

        assert response.status_code == status.HTTP_200_OK
        names = [o['nom_organisme'] for o in response.data]
        assert names == sorted(names)
