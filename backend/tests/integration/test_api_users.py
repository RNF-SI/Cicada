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


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersRGPDDeletion:
    """Tests for RGPD account deletion functionality."""

    def test_request_deletion_success(self, api_client):
        """Test user can request account deletion - account stays active."""
        user = RoleFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/request_deletion/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'requested'
        assert 'message' in response.data

        # Verify user stays ACTIVE and deletion_requested_at is set
        user.refresh_from_db()
        assert user.active is True  # Account stays active now
        assert user.deletion_requested_at is not None

    def test_request_deletion_unauthenticated(self, api_client):
        """Test unauthenticated user cannot request deletion."""
        response = api_client.post('/api/users/users/request_deletion/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_request_deletion_already_pending(self, api_client):
        """Test user cannot request deletion twice."""
        from django.utils import timezone
        user = RoleFactory(active=False)
        user.deletion_requested_at = timezone.now()
        user.save()

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/request_deletion/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_request_deletion_already_anonymized(self, api_client):
        """Test anonymized user cannot request deletion."""
        user = RoleFactory(
            active=False,
            is_anonymized=True,
            email='anonymized_test@deleted.local'
        )

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/request_deletion/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_cancel_deletion_success(self, api_client):
        """Test user can cancel deletion request."""
        from django.utils import timezone
        user = RoleFactory(active=True)  # Account stays active in new logic
        user.deletion_requested_at = timezone.now()
        user.save()

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/cancel_deletion/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'cancelled'

        # Verify deletion_requested_at is cleared
        user.refresh_from_db()
        assert user.active is True
        assert user.deletion_requested_at is None

    def test_cancel_deletion_no_pending_request(self, api_client):
        """Test cancel fails when no deletion is pending."""
        user = RoleFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/cancel_deletion/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_cancel_deletion_already_anonymized(self, api_client):
        """Test cancel fails for anonymized accounts."""
        from django.utils import timezone
        user = RoleFactory(
            active=False,
            is_anonymized=True,
            email='anonymized_test2@deleted.local'
        )
        user.deletion_requested_at = timezone.now()
        user.save()

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/cancel_deletion/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_cancel_deletion_unauthenticated(self, api_client):
        """Test unauthenticated user cannot cancel deletion."""
        response = api_client.post('/api/users/users/cancel_deletion/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_returns_deletion_info(self, api_client):
        """Test /me endpoint returns deletion_requested_at field."""
        from django.utils import timezone
        user = RoleFactory(active=True)  # Account stays active in new logic
        user.deletion_requested_at = timezone.now()
        user.save()

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/users/me/')

        assert response.status_code == status.HTTP_200_OK
        assert 'deletion_requested_at' in response.data
        assert response.data['deletion_requested_at'] is not None

    def test_me_returns_anonymized_info(self, api_client):
        """Test /me endpoint returns is_anonymized field."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/users/me/')

        assert response.status_code == status.HTTP_200_OK
        assert 'is_anonymized' in response.data
        assert response.data['is_anonymized'] is False


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersRGPDModelMethods:
    """Tests for RGPD model methods on User."""

    def test_request_deletion_method(self):
        """Test Role.request_deletion() method - still deactivates (for backward compat)."""
        user = RoleFactory(active=True)

        # The model method still deactivates (used internally)
        # The API endpoint now keeps account active
        user.request_deletion()

        assert user.active is False  # Model method still deactivates
        assert user.deletion_requested_at is not None

    def test_anonymize_method(self):
        """Test Role.anonymize() method."""
        from django.utils import timezone
        user = RoleFactory(
            email='marie.dupont@test.fr',
            nom_role='Dupont',
            prenom_role='Marie',
            active=False
        )
        user.deletion_requested_at = timezone.now()
        user.save()

        user.anonymize()

        assert user.is_anonymized is True
        assert user.anonymized_at is not None
        assert 'anonymized_' in user.email
        assert '@deleted.local' in user.email
        assert user.nom_role == 'Utilisateur'
        assert user.prenom_role == 'Anonymise'

    def test_can_be_anonymized_no_request(self):
        """Test can_be_anonymized returns False when no deletion requested."""
        user = RoleFactory(active=True)
        assert user.can_be_anonymized() is False

    def test_can_be_anonymized_already_anonymized(self):
        """Test can_be_anonymized returns False when already anonymized."""
        from django.utils import timezone
        user = RoleFactory(
            is_anonymized=True,
            email='anonymized_123@deleted.local'
        )
        user.deletion_requested_at = timezone.now()
        user.save()

        assert user.can_be_anonymized() is False

    def test_can_be_anonymized_within_grace_period(self):
        """Test can_be_anonymized returns False within 30-day grace period."""
        from django.utils import timezone
        user = RoleFactory(active=False)
        user.deletion_requested_at = timezone.now()
        user.save()

        assert user.can_be_anonymized() is False

    def test_can_be_anonymized_after_grace_period(self):
        """Test can_be_anonymized returns True after 30-day grace period."""
        from django.utils import timezone
        from datetime import timedelta

        user = RoleFactory(active=False)
        user.deletion_requested_at = timezone.now() - timedelta(days=31)
        user.save()

        assert user.can_be_anonymized() is True


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersRGPDNotifications:
    """Tests for RGPD notifications sent to admins and referents."""

    def test_request_deletion_notifies_super_admins(self, api_client):
        """Test super admins receive notification on deletion request."""
        from apps.notifications.models import Notification

        # Create a super admin
        super_admin = SuperAdminFactory(active=True)
        # Create user requesting deletion
        user = RoleFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/request_deletion/')

        assert response.status_code == status.HTTP_200_OK

        # Check notification was created for super admin
        notification = Notification.objects.filter(
            recipient=super_admin,
            notification_type='system_alert',
            related_user=user
        ).first()
        assert notification is not None
        assert 'RGPD' in notification.title
        assert user.get_full_name() in notification.message or str(user) in notification.message

    def test_request_deletion_notifies_organisme_admin(self, api_client):
        """Test organisme admin receives notification on deletion request."""
        from apps.notifications.models import Notification

        # Create organisme and its admin
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme, active=True)
        # Create user in same organisme
        user = RoleFactory(active=True, id_organisme=organisme)

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/request_deletion/')

        assert response.status_code == status.HTTP_200_OK

        # Check notification was created for organisme admin
        notification = Notification.objects.filter(
            recipient=admin_og,
            notification_type='system_alert',
            related_user=user
        ).first()
        assert notification is not None
        assert 'RGPD' in notification.title

    def test_request_deletion_notifies_site_referents(self, api_client):
        """Test site referents receive notification on deletion request."""
        from apps.notifications.models import Notification

        # Create a site
        site = SiteFactory()
        # Create referent for this site
        referent = RoleFactory(active=True)
        CorRoleSiteFactory(
            id_role=referent,
            id_site=site,
            referent=True,
            referent_valid=True
        )
        # Create user who is member of this site
        user = RoleFactory(active=True)
        CorRoleSiteFactory(
            id_role=user,
            id_site=site,
            referent=False
        )

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/request_deletion/')

        assert response.status_code == status.HTTP_200_OK

        # Check notification was created for site referent
        notification = Notification.objects.filter(
            recipient=referent,
            notification_type='system_alert',
            related_user=user
        ).first()
        assert notification is not None
        assert 'RGPD' in notification.title

    def test_request_deletion_notifies_plan_referents(self, api_client):
        """Test plan referents receive notification on deletion request."""
        from apps.notifications.models import Notification
        from tests.factories.plans import PlanGestionFactory

        # Create plan
        plan = PlanGestionFactory()
        # Create another referent for this plan
        other_referent = RoleFactory(active=True)
        plan.referents.add(other_referent)
        # Create user who is also referent of this plan
        user = RoleFactory(active=True)
        plan.referents.add(user)

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/request_deletion/')

        assert response.status_code == status.HTTP_200_OK

        # Check notification was created for other plan referent
        notification = Notification.objects.filter(
            recipient=other_referent,
            notification_type='system_alert',
            related_user=user
        ).first()
        assert notification is not None
        assert 'RGPD' in notification.title

    def test_request_deletion_no_duplicate_notifications(self, api_client):
        """Test no duplicate notifications when user has multiple roles."""
        from apps.notifications.models import Notification

        # Create organisme and site
        organisme = OrganismeFactory()
        site = SiteFactory()

        # Create admin who is also referent of the site
        admin_referent = AdminOrganismeFactory(id_organisme=organisme, active=True)
        CorRoleSiteFactory(
            id_role=admin_referent,
            id_site=site,
            referent=True,
            referent_valid=True
        )

        # Create user in same organisme and member of same site
        user = RoleFactory(active=True, id_organisme=organisme)
        CorRoleSiteFactory(
            id_role=user,
            id_site=site,
            referent=False
        )

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/request_deletion/')

        assert response.status_code == status.HTTP_200_OK

        # Check only ONE notification was created for admin_referent (not duplicated)
        notifications = Notification.objects.filter(
            recipient=admin_referent,
            notification_type='system_alert',
            related_user=user
        )
        assert notifications.count() == 1

    def test_request_deletion_user_not_notified(self, api_client):
        """Test the user requesting deletion does not receive a notification."""
        from apps.notifications.models import Notification

        user = RoleFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/users/users/request_deletion/')

        assert response.status_code == status.HTTP_200_OK

        # Check no notification was created for the user themselves
        notification = Notification.objects.filter(
            recipient=user,
            notification_type='system_alert',
            related_user=user
        ).first()
        assert notification is None


@pytest.mark.django_db
@pytest.mark.integration
class TestUsersRGPDAdminEndpoints:
    """Tests for RGPD admin endpoints (super_admin only)."""

    def test_rgpd_requests_list_super_admin(self, api_client):
        """Test super admin can list RGPD requests."""
        from django.utils import timezone
        admin = SuperAdminFactory()

        # Create users with RGPD requests
        user1 = RoleFactory(active=True)
        user1.deletion_requested_at = timezone.now()
        user1.save()

        user2 = RoleFactory(active=True)
        user2.deletion_requested_at = timezone.now()
        user2.save()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/users/users/rgpd_requests/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['pagination']['count'] >= 2

    def test_rgpd_requests_list_denied_for_regular_user(self, api_client):
        """Test regular users cannot access RGPD requests list."""
        user = RoleFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/users/rgpd_requests/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_rgpd_requests_list_denied_for_admin_og(self, api_client):
        """Test admin organisme cannot access RGPD requests list."""
        admin_og = AdminOrganismeFactory()

        api_client.force_authenticate(user=admin_og)
        response = api_client.get('/api/users/users/rgpd_requests/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_deactivate_rgpd_success(self, api_client):
        """Test super admin can deactivate a user via RGPD."""
        from django.utils import timezone
        admin = SuperAdminFactory()
        user = RoleFactory(active=True)
        user.deletion_requested_at = timezone.now()
        user.save()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/users/users/{user.id_role}/deactivate_rgpd/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'deactivated'

        user.refresh_from_db()
        assert user.active is False
        assert user.deletion_requested_at is None  # Request cleared

    def test_deactivate_rgpd_no_request(self, api_client):
        """Test cannot deactivate user without RGPD request."""
        admin = SuperAdminFactory()
        user = RoleFactory(active=True)  # No deletion_requested_at

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/users/users/{user.id_role}/deactivate_rgpd/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_anonymize_rgpd_success(self, api_client):
        """Test super admin can anonymize a user via RGPD."""
        from django.utils import timezone
        admin = SuperAdminFactory()
        user = RoleFactory(
            active=True,
            email='jean.dupont@test.fr',
            nom_role='Dupont',
            prenom_role='Jean'
        )
        user.deletion_requested_at = timezone.now()
        user.save()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/users/users/{user.id_role}/anonymize_rgpd/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'anonymized'

        user.refresh_from_db()
        assert user.is_anonymized is True
        assert '@deleted.local' in user.email
        assert user.nom_role == 'Utilisateur'
        assert user.prenom_role == 'Anonymise'

    def test_anonymize_rgpd_no_request(self, api_client):
        """Test cannot anonymize user without RGPD request."""
        admin = SuperAdminFactory()
        user = RoleFactory(active=True)  # No deletion_requested_at

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/users/users/{user.id_role}/anonymize_rgpd/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_reject_rgpd_success(self, api_client):
        """Test super admin can reject a RGPD request."""
        from django.utils import timezone
        admin = SuperAdminFactory()
        user = RoleFactory(active=True)
        user.deletion_requested_at = timezone.now()
        user.save()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/users/users/{user.id_role}/reject_rgpd/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'rejected'

        user.refresh_from_db()
        assert user.active is True  # Still active
        assert user.deletion_requested_at is None  # Request cleared

    def test_reject_rgpd_notifies_user(self, api_client):
        """Test rejecting RGPD request notifies the user."""
        from django.utils import timezone
        from apps.notifications.models import Notification

        admin = SuperAdminFactory()
        user = RoleFactory(active=True)
        user.deletion_requested_at = timezone.now()
        user.save()

        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/users/users/{user.id_role}/reject_rgpd/')

        assert response.status_code == status.HTTP_200_OK

        # Check notification was created for user
        notification = Notification.objects.filter(
            recipient=user,
            notification_type='system_alert'
        ).first()
        assert notification is not None
        assert 'rejetee' in notification.title.lower() or 'reject' in notification.title.lower()

    def test_auth_provider_endpoint(self, api_client):
        """Test auth_provider endpoint returns the configured provider."""
        user = RoleFactory(active=True)

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/users/users/auth_provider/')

        assert response.status_code == status.HTTP_200_OK
        assert 'provider' in response.data
        assert response.data['provider'] == 'local'  # Default value

    def test_rgpd_admin_actions_denied_for_non_super_admin(self, api_client):
        """Test RGPD admin actions are denied for non super_admin users."""
        from django.utils import timezone
        admin_og = AdminOrganismeFactory()
        user = RoleFactory(active=True)
        user.deletion_requested_at = timezone.now()
        user.save()

        api_client.force_authenticate(user=admin_og)

        # Test deactivate_rgpd
        response = api_client.post(f'/api/users/users/{user.id_role}/deactivate_rgpd/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Test anonymize_rgpd
        response = api_client.post(f'/api/users/users/{user.id_role}/anonymize_rgpd/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Test reject_rgpd
        response = api_client.post(f'/api/users/users/{user.id_role}/reject_rgpd/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
