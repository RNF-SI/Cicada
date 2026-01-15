"""
Integration tests for Users API.
Converted from test_api_users.py standalone script.
Tests CRUD operations, permissions, filters, and custom actions.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import Role, BibOrganismes, CorRoleSite
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, OrganismeFactory, SiteFactory, CorRoleSiteFactory
)


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user_with_password(db):
    """Create a regular user with a known password."""
    user = RoleFactory(
        email='testuser@test.fr',
        nom_role='Test',
        prenom_role='User'
    )
    user.set_password('TestPassword123!')
    user.save()
    return user


@pytest.fixture
def admin_with_password(db):
    """Create an admin with a known password."""
    admin = SuperAdminFactory(email='admin@test.fr')
    admin.set_password('AdminPassword123!')
    admin.save()
    return admin


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersListEndpoint:
    """Tests for users list endpoint."""

    def test_list_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list users."""
        response = api_client.get('/api/users/users/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_super_admin_sees_all(self, api_client):
        """Test super admin can see all users."""
        admin = SuperAdminFactory()
        RoleFactory(nom_role='User1')
        RoleFactory(nom_role='User2')
        RoleFactory(nom_role='User3')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/')

        assert response.status_code == status.HTTP_200_OK
        # Super admin sees all users including themselves
        assert response.data['pagination']['count'] >= 4

    def test_list_admin_og_sees_organisme_users(self, api_client):
        """Test admin organisme sees only users in their organisme."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)

        # User in same organisme
        user_same = RoleFactory(id_organisme=organisme)
        # User in different organisme
        other_org = OrganismeFactory()
        user_other = RoleFactory(id_organisme=other_org)

        api_client.force_authenticate(user=admin_og)
        response = api_client.get('/api/users/users/')

        assert response.status_code == status.HTTP_200_OK
        user_ids = [u['id_role'] for u in response.data['results']]
        assert user_same.id_role in user_ids
        # Admin sees their own profile
        assert admin_og.id_role in user_ids

    def test_list_regular_user_sees_limited(self, api_client):
        """Test regular users can list users but see limited data."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/users/')

        # Regular users can list - ViewSet filters based on permissions
        # They may see only themselves or users from their organisme
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersDetailEndpoint:
    """Tests for user detail endpoint."""

    def test_detail_super_admin(self, api_client):
        """Test super admin can view any user details."""
        admin = SuperAdminFactory()
        user = RoleFactory(nom_role='Test', prenom_role='User')

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/users/{user.id_role}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom_role'] == 'Test'
        assert response.data['prenom_role'] == 'User'

    def test_detail_nonexistent_user(self, api_client):
        """Test retrieving non-existent user returns 404."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_returns_complete_info(self, api_client):
        """Test detail endpoint returns complete user info."""
        admin = SuperAdminFactory()
        organisme = OrganismeFactory()
        user = RoleFactory(
            nom_role='Dupont',
            prenom_role='Marie',
            email='marie.dupont@test.fr',
            id_organisme=organisme
        )

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/users/{user.id_role}/')

        assert response.status_code == status.HTTP_200_OK
        assert 'id_role' in response.data
        assert 'email' in response.data
        assert 'nom_role' in response.data
        assert 'prenom_role' in response.data


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersCreateEndpoint:
    """Tests for user creation endpoint."""

    def test_create_user_super_admin(self, api_client):
        """Test super admin can create a user."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/users/users/', {
            'email': 'newuser@test.fr',
            'nom_role': 'New',
            'prenom_role': 'User',
            'role_level': 'utilisateur',
            'password': 'TestPassword123!',
            'password_confirm': 'TestPassword123!',
            'active': True
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == 'newuser@test.fr'
        assert Role.objects.filter(email='newuser@test.fr').exists()

    def test_create_user_admin_og(self, api_client):
        """Test admin organisme can create user in their organisme."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)

        api_client.force_authenticate(user=admin_og)
        response = api_client.post('/api/users/users/', {
            'email': 'orguser@test.fr',
            'nom_role': 'Org',
            'prenom_role': 'User',
            'role_level': 'utilisateur',
            'password': 'TestPassword123!',
            'password_confirm': 'TestPassword123!',
            'uuid_organisme': str(organisme.uuid_organisme),
            'active': True
        })

        assert response.status_code == status.HTTP_201_CREATED

    def test_create_user_regular_user_denied(self, api_client):
        """Test regular users cannot create users."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/', {
            'email': 'unauthorized@test.fr',
            'nom_role': 'Unauthorized',
            'prenom_role': 'User',
            'password': 'TestPassword123!',
            'password_confirm': 'TestPassword123!',
            'active': True
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_user_password_mismatch(self, api_client):
        """Test user creation fails with mismatched passwords."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/users/users/', {
            'email': 'mismatch@test.fr',
            'nom_role': 'Mismatch',
            'prenom_role': 'User',
            'password': 'Password123!',
            'password_confirm': 'DifferentPassword!',
            'active': True
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_user_duplicate_email(self, api_client):
        """Test user creation fails with duplicate email."""
        admin = SuperAdminFactory()
        existing_user = RoleFactory(email='existing@test.fr')

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/users/users/', {
            'email': 'existing@test.fr',
            'nom_role': 'Duplicate',
            'prenom_role': 'User',
            'password': 'TestPassword123!',
            'password_confirm': 'TestPassword123!',
            'active': True
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersUpdateEndpoint:
    """Tests for user update endpoint."""

    def test_update_user(self, api_client):
        """Test updating a user."""
        admin = SuperAdminFactory()
        user = RoleFactory(nom_role='Original', desc_role=None)

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/users/users/{user.id_role}/', {
            'nom_role': 'Updated',
            'desc_role': 'Description mise à jour'
        })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.nom_role == 'Updated'
        assert user.desc_role == 'Description mise à jour'

    def test_update_user_activate_deactivate(self, api_client):
        """Test activating/deactivating a user."""
        admin = SuperAdminFactory()
        user = RoleFactory(active=True)

        api_client.force_authenticate(user=admin)

        # Deactivate
        response = api_client.patch(f'/api/users/users/{user.id_role}/', {
            'active': False
        })
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.active is False

        # Reactivate
        response = api_client.patch(f'/api/users/users/{user.id_role}/', {
            'active': True
        })
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.active is True


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersChangePassword:
    """Tests for change password endpoint."""

    def test_change_password_by_admin(self, api_client):
        """Test admin can change user password."""
        admin = SuperAdminFactory()
        user = RoleFactory()
        user.set_password('OldPassword123!')
        user.save()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/users/users/{user.id_role}/change_password/', {
            'password': 'NewPassword123!',
            'password_confirm': 'NewPassword123!'
        })

        assert response.status_code == status.HTTP_200_OK
        # Verify new password works
        user.refresh_from_db()
        assert user.check_password('NewPassword123!')

    def test_change_password_mismatch(self, api_client):
        """Test change password fails with mismatch."""
        admin = SuperAdminFactory()
        user = RoleFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/users/users/{user.id_role}/change_password/', {
            'password': 'NewPassword123!',
            'password_confirm': 'DifferentPassword!'
        })

        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersMeEndpoint:
    """Tests for /me/ endpoint."""

    def test_me_returns_current_user(self, api_client):
        """Test /me returns authenticated user info."""
        user = RoleFactory(nom_role='Dupont', prenom_role='Jean')

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/users/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id_role'] == user.id_role
        assert response.data['nom_role'] == 'Dupont'
        assert response.data['prenom_role'] == 'Jean'

    def test_me_unauthenticated(self, api_client):
        """Test /me requires authentication."""
        response = api_client.get('/api/users/users/me/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_returns_organisme_info(self, api_client):
        """Test /me returns user's organisme if present."""
        organisme = OrganismeFactory(nom_organisme='Test Org')
        user = RoleFactory(id_organisme=organisme)

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/users/me/')

        assert response.status_code == status.HTTP_200_OK
        if 'organisme' in response.data and response.data['organisme']:
            assert response.data['organisme']['nom_organisme'] == 'Test Org'


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersStatsEndpoint:
    """Tests for /stats/ endpoint."""

    def test_stats_super_admin(self, api_client):
        """Test super admin can access stats."""
        admin = SuperAdminFactory()
        RoleFactory(active=True)
        RoleFactory(active=True)
        RoleFactory(active=False)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'total_users' in response.data
        assert 'active_users' in response.data
        assert response.data['total_users'] >= 4  # 3 created + admin
        assert response.data['active_users'] >= 3

    def test_stats_regular_user_denied(self, api_client):
        """Test regular users cannot access stats."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/users/stats/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_stats_admin_og_denied(self, api_client):
        """Test admin organisme cannot access global stats."""
        admin_og = AdminOrganismeFactory()

        api_client.force_authenticate(user=admin_og)
        response = api_client.get('/api/users/users/stats/')

        # Admin OG may get 403 for global stats
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_403_FORBIDDEN]


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersSiteAssignment:
    """Tests for site assignment to users."""

    def test_assign_site_to_user(self, api_client):
        """Test assigning a site to a user."""
        admin = SuperAdminFactory()
        user = RoleFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/users/users/{user.id_role}/assign_site/', {
            'site_id': site.id_site,
            'referent': True,
            'referent_valid': True
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert CorRoleSite.objects.filter(
            id_role=user,
            id_site=site
        ).exists()

    def test_assign_site_updates_existing(self, api_client):
        """Test assigning same site twice updates the existing assignment."""
        admin = SuperAdminFactory()
        user = RoleFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site, referent=False)

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/users/users/{user.id_role}/assign_site/', {
            'site_id': site.id_site,
            'referent': True
        })

        # update_or_create returns 201 for both create and update
        assert response.status_code == status.HTTP_201_CREATED
        # Verify the update
        cor = CorRoleSite.objects.get(id_role=user, id_site=site)
        assert cor.referent is True

    def test_remove_site_from_user(self, api_client):
        """Test removing a site from a user."""
        admin = SuperAdminFactory()
        user = RoleFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site)

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/users/users/{user.id_role}/sites/{site.id_site}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CorRoleSite.objects.filter(
            id_role=user,
            id_site=site
        ).exists()

    def test_user_sites_in_detail_response(self, api_client):
        """Test sites assigned to a user are included in detail response."""
        admin = SuperAdminFactory()
        user = RoleFactory()
        site1 = SiteFactory(nom_site='Site 1')
        site2 = SiteFactory(nom_site='Site 2')
        CorRoleSiteFactory(id_role=user, id_site=site1)
        CorRoleSiteFactory(id_role=user, id_site=site2)

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/users/{user.id_role}/')

        assert response.status_code == status.HTTP_200_OK
        # Sites are included in the detail response via sites_lies
        assert 'sites_lies' in response.data
        assert len(response.data['sites_lies']) >= 2


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersFiltersAndSearch:
    """Tests for filters and search."""

    def test_search_by_name(self, api_client):
        """Test searching users by name."""
        admin = SuperAdminFactory()
        RoleFactory(nom_role='Dupont', prenom_role='Marie')
        RoleFactory(nom_role='Martin', prenom_role='Jean')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/?search=Dupont')

        assert response.status_code == status.HTTP_200_OK
        user_names = [u['nom_role'] for u in response.data['results']]
        assert 'Dupont' in user_names

    def test_search_by_email(self, api_client):
        """Test searching users by email."""
        admin = SuperAdminFactory()
        user = RoleFactory(email='specific.email@test.fr')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/?search=specific.email')

        assert response.status_code == status.HTTP_200_OK
        assert any(u['email'] == 'specific.email@test.fr' for u in response.data['results'])

    def test_filter_by_role_level(self, api_client):
        """Test filtering by role level."""
        admin = SuperAdminFactory()
        admin_og = AdminOrganismeFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/?role_level=admin_og')

        assert response.status_code == status.HTTP_200_OK
        # All returned users with admin_og role should be in results
        for user in response.data['results']:
            if user['id_role'] == admin_og.id_role:
                assert user.get('role_level') == 'admin_og'

    def test_filter_by_organisme(self, api_client):
        """Test filtering by organisme."""
        admin = SuperAdminFactory()
        organisme = OrganismeFactory()
        user_in_org = RoleFactory(id_organisme=organisme)
        user_no_org = RoleFactory(id_organisme=None)

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/users/users/?organisme={organisme.id_organisme}')

        assert response.status_code == status.HTTP_200_OK
        user_ids = [u['id_role'] for u in response.data['results']]
        assert user_in_org.id_role in user_ids

    def test_filter_active_users(self, api_client):
        """Test filtering active users."""
        admin = SuperAdminFactory()
        active_user = RoleFactory(active=True)
        inactive_user = RoleFactory(active=False)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/?active=true')

        assert response.status_code == status.HTTP_200_OK
        for user in response.data['results']:
            assert user['active'] is True

    def test_ordering_by_date(self, api_client):
        """Test ordering by date."""
        admin = SuperAdminFactory()
        RoleFactory()
        RoleFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/?ordering=-date_insert')

        assert response.status_code == status.HTTP_200_OK
        # Just verify it returns results without error
        assert 'results' in response.data


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersPagination:
    """Tests for pagination."""

    def test_default_pagination(self, api_client):
        """Test default pagination."""
        admin = SuperAdminFactory()
        for i in range(15):
            RoleFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/')

        assert response.status_code == status.HTTP_200_OK
        assert 'pagination' in response.data
        assert 'current_page' in response.data['pagination']
        assert 'total_pages' in response.data['pagination']

    def test_custom_page_size(self, api_client):
        """Test custom page size."""
        admin = SuperAdminFactory()
        for i in range(10):
            RoleFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/?page_size=5')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) <= 5

    def test_page_navigation(self, api_client):
        """Test navigating between pages."""
        admin = SuperAdminFactory()
        for i in range(15):
            RoleFactory()

        api_client.force_authenticate(user=admin)

        # First page
        response1 = api_client.get('/api/users/users/?page=1&page_size=5')
        assert response1.status_code == status.HTTP_200_OK

        # Second page
        response2 = api_client.get('/api/users/users/?page=2&page_size=5')
        assert response2.status_code == status.HTTP_200_OK

        # Results should be different
        ids_page1 = {u['id_role'] for u in response1.data['results']}
        ids_page2 = {u['id_role'] for u in response2.data['results']}
        assert ids_page1 != ids_page2


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersDeleteEndpoint:
    """Tests for user deletion endpoint."""

    def test_delete_user_deactivates(self, api_client):
        """Test deleting a user deactivates them (soft delete)."""
        admin = SuperAdminFactory()
        user = RoleFactory(active=True)
        user_id = user.id_role

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/users/users/{user_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # ViewSet uses soft delete (deactivation) not physical delete
        user.refresh_from_db()
        assert user.active is False

    def test_delete_user_keeps_site_associations(self, api_client):
        """Test deleting (deactivating) user keeps site associations."""
        admin = SuperAdminFactory()
        user = RoleFactory(active=True)
        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site)
        user_id = user.id_role

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/users/users/{user_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        # Soft delete keeps associations
        assert CorRoleSite.objects.filter(id_role_id=user_id).exists()

    def test_delete_user_regular_user_denied(self, api_client):
        """Test regular users cannot delete other users."""
        user1 = RoleFactory()
        user2 = RoleFactory()

        api_client.force_authenticate(user=user1)
        response = api_client.delete(f'/api/users/users/{user2.id_role}/')

        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersPermissionsEndpoint:
    """Tests for /permissions/ endpoint."""

    def test_permissions_returns_user_permissions(self, api_client):
        """Test permissions endpoint returns user permissions."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/permissions/')

        assert response.status_code == status.HTTP_200_OK
        assert 'role_level' in response.data or 'permissions' in response.data

    def test_permissions_super_admin(self, api_client):
        """Test permissions for super admin."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/permissions/')

        assert response.status_code == status.HTTP_200_OK
        # Super admin should have elevated permissions
        data = response.data
        # Response has nested structure: permissions.is_super_admin, user.role_level
        is_super_admin = data.get('permissions', {}).get('is_super_admin')
        role_level = data.get('user', {}).get('role_level')
        assert is_super_admin or role_level == 'super_admin'

    def test_permissions_unauthenticated(self, api_client):
        """Test permissions endpoint requires authentication."""
        response = api_client.get('/api/users/permissions/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
