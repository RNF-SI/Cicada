"""
Integration tests for Site duplicate detection feature.
Tests INPN uniqueness constraint and check_duplicates endpoint.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import Site, CorOgSite, CorRoleSite
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, RoleFactory,
    OrganismeFactory, SiteFactory, SiteWithoutGeomFactory,
    CorOgSiteFactory, CorRoleSiteFactory
)


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


# =============================================================================
# INPN UNIQUENESS CONSTRAINT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestInpnUniqueness:
    """Tests for INPN code uniqueness constraint."""

    def test_create_site_with_unique_inpn(self, api_client):
        """Test that creating a site with a unique INPN code succeeds."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        payload = {
            'nom_site': 'Site Test Unique INPN',
            'id_inpn': 'FR1234567'
        }

        response = api_client.post('/api/users/sites/', payload)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['id_inpn'] == 'FR1234567'

    def test_create_site_with_duplicate_inpn_fails(self, api_client):
        """Test that creating a site with a duplicate INPN code fails."""
        admin = SuperAdminFactory()
        existing_site = SiteWithoutGeomFactory(id_inpn='FR0000001', nom_site='Site Existant')

        api_client.force_authenticate(user=admin)

        payload = {
            'nom_site': 'Site Test Doublon',
            'id_inpn': 'FR0000001'
        }

        response = api_client.post('/api/users/sites/', payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'id_inpn' in response.data
        # Error can come from serializer validation or DB unique constraint
        error_msg = str(response.data['id_inpn'][0]).lower()
        assert 'inpn' in error_msg or 'unique' in error_msg or 'existant' in error_msg

    def test_null_inpn_allowed_multiple(self, api_client):
        """Test that multiple sites can have NULL INPN codes."""
        admin = SuperAdminFactory()
        # Create sites without INPN codes
        SiteWithoutGeomFactory(id_inpn=None, nom_site='Site Sans INPN 1')
        SiteWithoutGeomFactory(id_inpn=None, nom_site='Site Sans INPN 2')

        api_client.force_authenticate(user=admin)

        # Create another site without INPN
        payload = {
            'nom_site': 'Site Sans INPN 3',
            'id_inpn': None
        }

        response = api_client.post('/api/users/sites/', payload)

        # Should succeed - NULL is allowed multiple times
        assert response.status_code == status.HTTP_201_CREATED

    def test_empty_string_inpn_converted_to_null(self, api_client):
        """Test that empty string INPN is converted to NULL."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        payload = {
            'nom_site': 'Site INPN Vide',
            'id_inpn': ''
        }

        response = api_client.post('/api/users/sites/', payload)

        assert response.status_code == status.HTTP_201_CREATED
        # Check in database that it's NULL
        site = Site.objects.get(id_site=response.data['id_site'])
        assert site.id_inpn is None

    def test_update_site_with_own_inpn_succeeds(self, api_client):
        """Test that updating a site keeps its own INPN code without error."""
        admin = SuperAdminFactory()
        site = SiteWithoutGeomFactory(id_inpn='FR9999999', nom_site='Site Original')

        api_client.force_authenticate(user=admin)

        payload = {
            'nom_site': 'Site Modifie',
            'id_inpn': 'FR9999999'  # Same INPN as existing
        }

        response = api_client.patch(f'/api/users/sites/{site.id_site}/', payload)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom_site'] == 'Site Modifie'

    def test_update_site_with_other_site_inpn_fails(self, api_client):
        """Test that updating a site with another site's INPN fails."""
        admin = SuperAdminFactory()
        existing_site = SiteWithoutGeomFactory(id_inpn='FR1111111', nom_site='Site Existant')
        site_to_update = SiteWithoutGeomFactory(id_inpn='FR2222222', nom_site='Site A Modifier')

        api_client.force_authenticate(user=admin)

        payload = {
            'id_inpn': 'FR1111111'  # INPN of existing_site
        }

        response = api_client.patch(f'/api/users/sites/{site_to_update.id_site}/', payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'id_inpn' in response.data


# =============================================================================
# CHECK DUPLICATES ENDPOINT TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestCheckDuplicatesEndpoint:
    """Tests for check_duplicates endpoint."""

    def test_check_duplicates_by_inpn(self, api_client):
        """Test that check_duplicates finds exact INPN match."""
        admin = SuperAdminFactory()
        organisme = OrganismeFactory(nom_organisme='RNF Test')
        site = SiteWithoutGeomFactory(
            id_inpn='FR0000001',
            nom_site='Reserve de Camargue'
        )
        CorOgSiteFactory(id_site=site, uuid_og=organisme, principal=True)

        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/users/sites/check_duplicates/', {
            'id_inpn': 'FR0000001'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['exact_inpn_match'] is not None
        assert response.data['exact_inpn_match']['id_site'] == site.id_site
        assert response.data['exact_inpn_match']['nom_site'] == 'Reserve de Camargue'
        assert len(response.data['exact_inpn_match']['organismes']) == 1
        assert response.data['exact_inpn_match']['organismes'][0]['nom_organisme'] == 'RNF Test'

    def test_check_duplicates_by_name(self, api_client):
        """Test that check_duplicates finds similar names."""
        admin = SuperAdminFactory()
        site1 = SiteWithoutGeomFactory(nom_site='Reserve Naturelle de Camargue')
        site2 = SiteWithoutGeomFactory(nom_site='Camargue Petite')

        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/users/sites/check_duplicates/', {
            'nom_site': 'Camargue'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['exact_inpn_match'] is None
        assert len(response.data['similar_names']) == 2

        site_ids = [s['id_site'] for s in response.data['similar_names']]
        assert site1.id_site in site_ids
        assert site2.id_site in site_ids

    def test_check_duplicates_no_match(self, api_client):
        """Test that check_duplicates returns empty when no match."""
        admin = SuperAdminFactory()
        SiteWithoutGeomFactory(nom_site='Autre Site', id_inpn='FR9999999')

        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/users/sites/check_duplicates/', {
            'nom_site': 'Reserve Inexistante',
            'id_inpn': 'FR0000000'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['exact_inpn_match'] is None
        assert len(response.data['similar_names']) == 0

    def test_check_duplicates_exclude_current_site(self, api_client):
        """Test that check_duplicates excludes current site in edit mode."""
        admin = SuperAdminFactory()
        site = SiteWithoutGeomFactory(id_inpn='FR1234567', nom_site='Mon Site')

        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/users/sites/check_duplicates/', {
            'id_inpn': 'FR1234567',
            'exclude_id': str(site.id_site)
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['exact_inpn_match'] is None

    def test_check_duplicates_requires_authentication(self, api_client):
        """Test that check_duplicates requires authentication."""
        response = api_client.get('/api/users/sites/check_duplicates/', {
            'id_inpn': 'FR0000001'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_check_duplicates_shows_user_access(self, api_client):
        """Test that check_duplicates shows if user has access to site."""
        user = RoleFactory()
        site_with_access = SiteWithoutGeomFactory(nom_site='Site Avec Acces')
        site_without_access = SiteWithoutGeomFactory(nom_site='Site Sans Acces')
        CorRoleSiteFactory(id_role=user, id_site=site_with_access, referent=True)

        api_client.force_authenticate(user=user)

        response = api_client.get('/api/users/sites/check_duplicates/', {
            'nom_site': 'Site'
        })

        assert response.status_code == status.HTTP_200_OK
        sites = {s['id_site']: s for s in response.data['similar_names']}

        assert sites[site_with_access.id_site]['has_access'] is True
        assert sites[site_without_access.id_site]['has_access'] is False

    def test_check_duplicates_shows_user_org_link(self, api_client):
        """Test that check_duplicates shows if site belongs to user's org."""
        organisme = OrganismeFactory()
        admin = AdminOrganismeFactory(id_organisme=organisme)

        site_linked = SiteWithoutGeomFactory(nom_site='Site Lie a Mon Org')
        site_other = SiteWithoutGeomFactory(nom_site='Site Autre Org')

        CorOgSiteFactory(id_site=site_linked, uuid_og=organisme)
        CorOgSiteFactory(id_site=site_other, uuid_og=OrganismeFactory())

        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/users/sites/check_duplicates/', {
            'nom_site': 'Site'
        })

        assert response.status_code == status.HTTP_200_OK
        sites = {s['id_site']: s for s in response.data['similar_names']}

        assert sites[site_linked.id_site]['is_user_org'] is True
        assert sites[site_other.id_site]['is_user_org'] is False

    def test_check_duplicates_name_too_short(self, api_client):
        """Test that check_duplicates ignores names shorter than 3 chars."""
        admin = SuperAdminFactory()
        SiteWithoutGeomFactory(nom_site='AB')

        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/users/sites/check_duplicates/', {
            'nom_site': 'AB'
        })

        assert response.status_code == status.HTTP_200_OK
        # Name is too short, should not search
        assert len(response.data['similar_names']) == 0

    def test_check_duplicates_inpn_and_name_combined(self, api_client):
        """Test check_duplicates with both INPN and name search."""
        admin = SuperAdminFactory()
        site_inpn = SiteWithoutGeomFactory(
            id_inpn='FR0000001',
            nom_site='Reserve Specifique'
        )
        site_similar = SiteWithoutGeomFactory(
            id_inpn=None,
            nom_site='Reserve Generale'
        )

        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/users/sites/check_duplicates/', {
            'id_inpn': 'FR0000001',
            'nom_site': 'Reserve'
        })

        assert response.status_code == status.HTTP_200_OK
        # INPN match should be separate from name matches
        assert response.data['exact_inpn_match']['id_site'] == site_inpn.id_site
        # Similar names should not include the INPN match
        similar_ids = [s['id_site'] for s in response.data['similar_names']]
        assert site_inpn.id_site not in similar_ids
        assert site_similar.id_site in similar_ids

    def test_check_duplicates_inactive_sites_excluded(self, api_client):
        """Test that inactive sites are excluded from duplicate check."""
        admin = SuperAdminFactory()
        inactive_site = SiteWithoutGeomFactory(
            id_inpn='FR0000001',
            nom_site='Site Inactif',
            active=False
        )

        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/users/sites/check_duplicates/', {
            'id_inpn': 'FR0000001'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['exact_inpn_match'] is None
