"""
Integration tests for Authentication API.
Converted from test_auth_api.py standalone script.
Tests JWT authentication endpoints: login, logout, refresh, user info.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.users.models import Role
from tests.factories.users import RoleFactory, SuperAdminFactory, AdminOrganismeFactory


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user_with_password(db):
    """Create a user with a known password."""
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
class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check_public(self, api_client):
        """Test health check endpoint is publicly accessible."""
        response = api_client.get('/api/auth/health/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'ok'

    def test_health_check_returns_json(self, api_client):
        """Test health check returns JSON response."""
        response = api_client.get('/api/auth/health/')

        assert response.status_code == status.HTTP_200_OK
        assert 'status' in response.data


@pytest.mark.django_db
@pytest.mark.integration
class TestLogin:
    """Tests for login endpoint."""

    def test_login_with_email_success(self, api_client, user_with_password):
        """Test successful login with email returns tokens."""
        response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'TestPassword123!'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert 'user' in response.data
        assert response.data['user']['email'] == user_with_password.email

    def test_login_returns_user_info(self, api_client, user_with_password):
        """Test login returns complete user information."""
        response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'TestPassword123!'
        })

        assert response.status_code == status.HTTP_200_OK
        user_data = response.data['user']
        assert 'email' in user_data
        assert 'nom' in user_data or 'nom_role' in user_data
        assert 'prenom' in user_data or 'prenom_role' in user_data

    def test_login_with_organisme_user(self, api_client, db):
        """Test login with user that has an organisme."""
        admin_og = AdminOrganismeFactory()
        admin_og.set_password('OrgPassword123!')
        admin_og.save()

        response = api_client.post('/api/auth/login/', {
            'username': admin_og.email,
            'password': 'OrgPassword123!'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        # Check organisme is included if present
        user_data = response.data['user']
        if 'organisme' in user_data and user_data['organisme']:
            assert 'nom' in user_data['organisme'] or 'nom_organisme' in user_data['organisme']

    def test_login_invalid_password(self, api_client, user_with_password):
        """Test login with wrong password fails."""
        response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'WrongPassword!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent user fails."""
        response = api_client.post('/api/auth/login/', {
            'username': 'nonexistent@test.fr',
            'password': 'AnyPassword!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_missing_password(self, api_client, user_with_password):
        """Test login without password fails."""
        response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email
        })

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED]

    def test_login_missing_email(self, api_client):
        """Test login without email fails."""
        response = api_client.post('/api/auth/login/', {
            'password': 'SomePassword!'
        })

        assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED]

    def test_login_inactive_user(self, api_client, db):
        """Test login with inactive user fails."""
        inactive_user = RoleFactory(active=False)
        inactive_user.set_password('Password123!')
        inactive_user.save()

        response = api_client.post('/api/auth/login/', {
            'username': inactive_user.email,
            'password': 'Password123!'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.integration
class TestUserInfo:
    """Tests for /me/ endpoint."""

    def test_me_authenticated(self, api_client, user_with_password):
        """Test /me endpoint returns user info when authenticated."""
        # Login first
        login_response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'TestPassword123!'
        })
        token = login_response.data['access']

        # Access /me
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = api_client.get('/api/auth/me/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['email'] == user_with_password.email

    def test_me_unauthenticated(self, api_client):
        """Test /me endpoint requires authentication."""
        response = api_client.get('/api/auth/me/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_invalid_token(self, api_client):
        """Test /me endpoint rejects invalid token."""
        api_client.credentials(HTTP_AUTHORIZATION='Bearer invalid-token')
        response = api_client.get('/api/auth/me/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_returns_complete_info(self, api_client, admin_with_password):
        """Test /me returns complete user information."""
        # Login
        login_response = api_client.post('/api/auth/login/', {
            'username': admin_with_password.email,
            'password': 'AdminPassword123!'
        })
        token = login_response.data['access']

        # Access /me
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = api_client.get('/api/auth/me/')

        assert response.status_code == status.HTTP_200_OK
        assert 'id' in response.data  # Uses 'id' not 'id_role'
        assert 'email' in response.data
        assert 'is_staff' in response.data
        # Note: /me/ endpoint uses 'is_active' not 'is_superuser'
        assert 'is_active' in response.data


@pytest.mark.django_db
@pytest.mark.integration
class TestTokenRefresh:
    """Tests for token refresh endpoint."""

    def test_refresh_token_success(self, api_client, user_with_password):
        """Test token refresh returns new access token."""
        # Login to get tokens
        login_response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'TestPassword123!'
        })
        refresh_token = login_response.data['refresh']

        # Refresh token
        response = api_client.post('/api/auth/refresh/', {
            'refresh': refresh_token
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data

    def test_refresh_with_new_token_works(self, api_client, user_with_password):
        """Test new access token from refresh works."""
        # Login
        login_response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'TestPassword123!'
        })
        refresh_token = login_response.data['refresh']

        # Refresh
        refresh_response = api_client.post('/api/auth/refresh/', {
            'refresh': refresh_token
        })
        new_access_token = refresh_response.data['access']

        # Use new token
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access_token}')
        response = api_client.get('/api/auth/me/')

        assert response.status_code == status.HTTP_200_OK

    def test_refresh_invalid_token(self, api_client):
        """Test refresh with invalid token fails."""
        response = api_client.post('/api/auth/refresh/', {
            'refresh': 'invalid-refresh-token'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_missing_token(self, api_client):
        """Test refresh without token fails."""
        response = api_client.post('/api/auth/refresh/', {})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refresh_token_blocked_for_disabled_user(self, api_client, db):
        """Test token refresh is blocked for users disabled after login."""
        # Create active user and login
        user = RoleFactory(active=True)
        user.set_password('Password123!')
        user.save()

        login_response = api_client.post('/api/auth/login/', {
            'username': user.email,
            'password': 'Password123!'
        })
        assert login_response.status_code == status.HTTP_200_OK
        refresh_token = login_response.data['refresh']

        # Deactivate the user
        user.active = False
        user.save()

        # Try to refresh token - should be blocked
        response = api_client.post('/api/auth/refresh/', {
            'refresh': refresh_token
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert 'desactive' in response.data.get('detail', '').lower()


@pytest.mark.django_db
@pytest.mark.integration
class TestLogout:
    """Tests for logout endpoint.

    Note: Full logout with token blacklisting requires the
    'rest_framework_simplejwt.token_blacklist' app to be installed.
    Without it, logout returns 400. These tests verify the endpoint
    behavior with or without blacklist support.
    """

    def test_logout_endpoint_responds(self, api_client, user_with_password):
        """Test logout endpoint accepts authenticated requests."""
        # Login
        login_response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'TestPassword123!'
        })
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']

        # Logout - endpoint should respond (may return 200 or 400 depending on blacklist config)
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        response = api_client.post('/api/auth/logout/', {
            'refresh': refresh_token
        }, format='json')

        # Without token_blacklist app, logout returns 400, with it returns 200
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    @pytest.mark.skip(reason="Requires rest_framework_simplejwt.token_blacklist app")
    def test_logout_invalidates_refresh_token(self, api_client, user_with_password):
        """Test refresh token is invalidated after logout."""
        # Login
        login_response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'TestPassword123!'
        })
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']

        # Logout
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        api_client.post('/api/auth/logout/', {'refresh': refresh_token}, format='json')

        # Try to refresh with blacklisted token
        api_client.credentials()
        refresh_response = api_client.post('/api/auth/refresh/', {
            'refresh': refresh_token
        })

        assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_unauthenticated(self, api_client):
        """Test logout requires authentication."""
        response = api_client.post('/api/auth/logout/', {
            'refresh': 'some-token'
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
@pytest.mark.integration
class TestAuthenticationFlow:
    """Tests for complete authentication flow."""

    def test_complete_auth_flow(self, api_client, user_with_password):
        """Test complete authentication flow: login -> me -> refresh -> logout."""
        # 1. Login
        login_response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'TestPassword123!'
        })
        assert login_response.status_code == status.HTTP_200_OK
        access_token = login_response.data['access']
        refresh_token = login_response.data['refresh']

        # 2. Access protected endpoint
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        me_response = api_client.get('/api/auth/me/')
        assert me_response.status_code == status.HTTP_200_OK

        # 3. Refresh token
        api_client.credentials()
        refresh_response = api_client.post('/api/auth/refresh/', {
            'refresh': refresh_token
        })
        assert refresh_response.status_code == status.HTTP_200_OK
        new_access_token = refresh_response.data['access']

        # 4. Use new token
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {new_access_token}')
        me_response2 = api_client.get('/api/auth/me/')
        assert me_response2.status_code == status.HTTP_200_OK

        # 5. Logout (may return 400 without token_blacklist app)
        logout_response = api_client.post('/api/auth/logout/', {
            'refresh': refresh_token
        }, format='json')
        # Accept either 200 (with blacklist) or 400 (without blacklist)
        assert logout_response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]

    def test_multiple_logins_different_users(self, api_client, db):
        """Test multiple users can login independently."""
        user1 = RoleFactory()
        user1.set_password('Password1!')
        user1.save()

        user2 = RoleFactory()
        user2.set_password('Password2!')
        user2.save()

        # Login user1
        response1 = api_client.post('/api/auth/login/', {
            'username': user1.email,
            'password': 'Password1!'
        })
        assert response1.status_code == status.HTTP_200_OK

        # Login user2
        response2 = api_client.post('/api/auth/login/', {
            'username': user2.email,
            'password': 'Password2!'
        })
        assert response2.status_code == status.HTTP_200_OK

        # Both tokens should work
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response1.data['access']}")
        me1 = api_client.get('/api/auth/me/')
        assert me1.data['email'] == user1.email

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {response2.data['access']}")
        me2 = api_client.get('/api/auth/me/')
        assert me2.data['email'] == user2.email


@pytest.mark.django_db
@pytest.mark.integration
class TestImpersonation:
    """Tests for user impersonation feature."""

    def test_start_impersonation_super_admin_can_impersonate(self, api_client, db):
        """Test super admin can start impersonation session."""
        super_admin = SuperAdminFactory()
        super_admin.set_password('AdminPass123!')
        super_admin.save()

        target_user = RoleFactory()

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f'/api/auth/impersonate/{target_user.id_role}/', {
            'reason': 'Support technique'
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert 'refresh' in response.data
        assert response.data['impersonation']['isImpersonating'] is True
        assert response.data['user']['id'] == target_user.id_role

    def test_start_impersonation_regular_user_denied(self, api_client, db):
        """Test regular user cannot start impersonation."""
        regular_user = RoleFactory()
        target_user = RoleFactory()

        api_client.force_authenticate(user=regular_user)
        response = api_client.post(f'/api/auth/impersonate/{target_user.id_role}/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_start_impersonation_admin_og_denied(self, api_client, db):
        """Test admin organisme cannot start impersonation."""
        admin_og = AdminOrganismeFactory()
        target_user = RoleFactory()

        api_client.force_authenticate(user=admin_og)
        response = api_client.post(f'/api/auth/impersonate/{target_user.id_role}/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cannot_impersonate_self(self, api_client, db):
        """Test super admin cannot impersonate themselves."""
        super_admin = SuperAdminFactory()

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(f'/api/auth/impersonate/{super_admin.id_role}/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'vous-meme' in response.data['detail'].lower()

    def test_cannot_impersonate_another_super_admin(self, api_client, db):
        """Test super admin cannot impersonate another super admin."""
        super_admin1 = SuperAdminFactory()
        super_admin2 = SuperAdminFactory()

        api_client.force_authenticate(user=super_admin1)
        response = api_client.post(f'/api/auth/impersonate/{super_admin2.id_role}/')

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'super administrateur' in response.data['detail'].lower()

    def test_impersonation_logs_super_admin_only(self, api_client, db):
        """Test only super admin can view impersonation logs."""
        super_admin = SuperAdminFactory()
        regular_user = RoleFactory()

        # Super admin can access
        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/auth/impersonation-logs/')
        assert response.status_code == status.HTTP_200_OK

        # Regular user cannot
        api_client.force_authenticate(user=regular_user)
        response = api_client.get('/api/auth/impersonation-logs/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_impersonation_logs_returns_list(self, api_client, db):
        """Test impersonation logs endpoint returns proper structure."""
        super_admin = SuperAdminFactory()

        api_client.force_authenticate(user=super_admin)
        response = api_client.get('/api/auth/impersonation-logs/')

        assert response.status_code == status.HTTP_200_OK
        assert 'count' in response.data
        assert 'results' in response.data
        assert isinstance(response.data['results'], list)


@pytest.mark.django_db
@pytest.mark.integration
class TestPublicStats:
    """Tests for public statistics endpoint."""

    def test_public_stats_accessible_without_auth(self, api_client, db):
        """Test public stats endpoint is accessible without authentication."""
        response = api_client.get('/api/auth/stats/')

        assert response.status_code == status.HTTP_200_OK

    def test_public_stats_returns_counts(self, api_client, db):
        """Test public stats returns expected count fields."""
        response = api_client.get('/api/auth/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert 'sites_count' in response.data
        assert 'plans_count' in response.data
        assert 'organismes_count' in response.data
        assert isinstance(response.data['sites_count'], int)
        assert isinstance(response.data['plans_count'], int)
        assert isinstance(response.data['organismes_count'], int)

    def test_public_stats_reflects_data(self, api_client, db):
        """Test public stats counts reflect actual database data."""
        from tests.factories.users import SiteFactory, OrganismeFactory
        from tests.factories.plans import PlanGestionFactory, PlanGestionValideFactory

        # Create some test data
        SiteFactory.create_batch(3)  # 3 active sites
        OrganismeFactory.create_batch(2)  # 2 organismes
        PlanGestionValideFactory.create_batch(2)  # 2 valid plans
        PlanGestionFactory(statut='draft')  # 1 draft plan (should not be counted)

        response = api_client.get('/api/auth/stats/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['sites_count'] >= 3
        assert response.data['organismes_count'] >= 2
        # Only valid plans should be counted, not drafts
        assert response.data['plans_count'] >= 2
