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

    def test_login_with_identifiant_success(self, api_client, db):
        """User can login using their identifiant instead of email."""
        user = RoleFactory(
            email='ident.user@test.fr',
            identifiant='myident',
        )
        user.set_password('IdentPass123!')
        user.save()

        response = api_client.post('/api/auth/login/', {
            'username': 'myident',
            'password': 'IdentPass123!',
        })

        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
        assert response.data['user']['email'] == 'ident.user@test.fr'

    def test_login_with_identifiant_case_insensitive(self, api_client, db):
        """Identifiant lookup is case-insensitive."""
        user = RoleFactory(
            email='case.user@test.fr',
            identifiant='CaseSensitive',
        )
        user.set_password('CasePass123!')
        user.save()

        response = api_client.post('/api/auth/login/', {
            'username': 'casesensitive',
            'password': 'CasePass123!',
        })

        assert response.status_code == status.HTTP_200_OK

    def test_login_with_unknown_identifiant_fails(self, api_client, db):
        """Login with an identifiant that doesn't match any user fails."""
        response = api_client.post('/api/auth/login/', {
            'username': 'nonexistent_ident',
            'password': 'AnyPass123!',
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_login_updates_last_login(self, api_client, user_with_password):
        """Successful login must update the user's last_login timestamp."""
        from django.utils import timezone

        # Initially last_login should be None (factory doesn't set it)
        assert user_with_password.last_login is None

        before = timezone.now()
        response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'TestPassword123!',
        })

        assert response.status_code == status.HTTP_200_OK
        user_with_password.refresh_from_db()
        assert user_with_password.last_login is not None
        assert user_with_password.last_login >= before

    def test_login_with_identifiant_updates_last_login(self, api_client, db):
        """Login via identifiant (not email) must also update last_login."""
        from django.utils import timezone

        user = RoleFactory(email='ll.user@test.fr', identifiant='llident')
        user.set_password('LLPass123!')
        user.save()
        assert user.last_login is None

        before = timezone.now()
        response = api_client.post('/api/auth/login/', {
            'username': 'llident',
            'password': 'LLPass123!',
        })

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.last_login is not None
        assert user.last_login >= before

    def test_failed_login_does_not_update_last_login(self, api_client, user_with_password):
        """A failed login attempt must not touch last_login."""
        assert user_with_password.last_login is None

        response = api_client.post('/api/auth/login/', {
            'username': user_with_password.email,
            'password': 'WrongPassword!',
        })

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        user_with_password.refresh_from_db()
        assert user_with_password.last_login is None


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

    def test_stop_impersonation_returns_admin_tokens(self, api_client, db):
        """Test stop impersonation returns tokens for original admin."""
        super_admin = SuperAdminFactory()
        super_admin.set_password('AdminPass123!')
        super_admin.save()

        target_user = RoleFactory()

        # Start impersonation
        api_client.force_authenticate(user=super_admin)
        start_response = api_client.post(
            f'/api/auth/impersonate/{target_user.id_role}/',
            {'reason': 'Test stop'}
        )
        assert start_response.status_code == status.HTTP_200_OK

        impersonation_token = start_response.data['access']

        # Use the impersonation token to stop
        api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {impersonation_token}')
        stop_response = api_client.post('/api/auth/stop-impersonation/')

        assert stop_response.status_code == status.HTTP_200_OK
        assert 'access' in stop_response.data
        assert 'refresh' in stop_response.data

    def test_stop_impersonation_without_session(self, api_client, db):
        """Test stop impersonation fails when not in impersonation session."""
        super_admin = SuperAdminFactory()

        api_client.force_authenticate(user=super_admin)
        response = api_client.post('/api/auth/stop-impersonation/')

        # Should fail because no impersonation claims in token
        # 401 is returned when force_authenticate is used (no JWT token with claims)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_403_FORBIDDEN
        ]

    def test_impersonate_nonexistent_user(self, api_client, db):
        """Test impersonating a nonexistent user returns 404."""
        super_admin = SuperAdminFactory()

        api_client.force_authenticate(user=super_admin)
        response = api_client.post('/api/auth/impersonate/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_impersonation_creates_log_entry(self, api_client, db):
        """Test starting impersonation creates a log entry."""
        from apps.authentication.models import ImpersonationLog

        super_admin = SuperAdminFactory()
        target_user = RoleFactory()

        initial_count = ImpersonationLog.objects.count()

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f'/api/auth/impersonate/{target_user.id_role}/',
            {'reason': 'Audit log test'}
        )
        assert response.status_code == status.HTTP_200_OK

        assert ImpersonationLog.objects.count() == initial_count + 1
        log = ImpersonationLog.objects.latest('started_at')
        assert log.impersonator == super_admin
        assert log.impersonated_user == target_user
        assert log.reason == 'Audit log test'
        assert log.ended_at is None  # Still active

    def test_impersonation_token_contains_claims(self, api_client, db):
        """Test impersonation JWT token contains proper claims."""
        import jwt
        from django.conf import settings

        super_admin = SuperAdminFactory()
        target_user = RoleFactory()

        api_client.force_authenticate(user=super_admin)
        response = api_client.post(
            f'/api/auth/impersonate/{target_user.id_role}/'
        )
        assert response.status_code == status.HTTP_200_OK

        token = response.data['access']
        # Decode without verification to inspect claims
        decoded = jwt.decode(token, options={"verify_signature": False})

        assert decoded.get('is_impersonating') is True
        assert decoded.get('impersonator_id') == super_admin.id_role

    def test_impersonation_logs_filter_by_impersonator(self, api_client, db):
        """Test filtering impersonation logs by impersonator_id."""
        super_admin = SuperAdminFactory()
        target_user = RoleFactory()

        # Create an impersonation session
        api_client.force_authenticate(user=super_admin)
        api_client.post(f'/api/auth/impersonate/{target_user.id_role}/')

        response = api_client.get(
            '/api/auth/impersonation-logs/',
            {'impersonator_id': super_admin.id_role}
        )
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['impersonator']['id'] == super_admin.id_role


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


@pytest.mark.django_db
@pytest.mark.integration
class TestPasswordReset:
    """Tests for the forgotten-password flow (#329)."""

    REQUEST_URL = '/api/auth/password-reset/'
    CONFIRM_URL = '/api/auth/password-reset/confirm/'

    def _uid_token(self, user):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        return (
            urlsafe_base64_encode(force_bytes(user.pk)),
            default_token_generator.make_token(user),
        )

    def test_request_existing_email_enqueues_email(self, api_client, user_with_password):
        """Une adresse connue déclenche l'envoi du mail de réinitialisation."""
        from unittest.mock import patch
        with patch('apps.notifications.tasks.send_password_reset_email.delay') as mock_delay:
            response = api_client.post(
                self.REQUEST_URL, {'email': user_with_password.email}, format='json'
            )
        assert response.status_code == status.HTTP_200_OK
        mock_delay.assert_called_once()
        # Le lien transmis pointe vers la page frontend de réinitialisation.
        sent_url = mock_delay.call_args[0][1]
        assert '/auth/reset-password?uid=' in sent_url and 'token=' in sent_url

    def test_request_unknown_email_no_email_same_response(self, api_client):
        """Une adresse inconnue renvoie la même réponse, sans envoyer d'email."""
        from unittest.mock import patch
        with patch('apps.notifications.tasks.send_password_reset_email.delay') as mock_delay:
            response = api_client.post(
                self.REQUEST_URL, {'email': 'inconnu@test.fr'}, format='json'
            )
        assert response.status_code == status.HTTP_200_OK
        mock_delay.assert_not_called()

    def test_request_inactive_user_no_email(self, api_client, user_with_password):
        """Un compte désactivé ne reçoit pas d'email de réinitialisation."""
        from unittest.mock import patch
        user_with_password.active = False
        user_with_password.save(update_fields=['active'])
        with patch('apps.notifications.tasks.send_password_reset_email.delay') as mock_delay:
            response = api_client.post(
                self.REQUEST_URL, {'email': user_with_password.email}, format='json'
            )
        assert response.status_code == status.HTTP_200_OK
        mock_delay.assert_not_called()

    def test_confirm_valid_token_sets_password(self, api_client, user_with_password):
        """Un jeton valide applique le nouveau mot de passe."""
        uid, token = self._uid_token(user_with_password)
        response = api_client.post(
            self.CONFIRM_URL,
            {'uid': uid, 'token': token, 'new_password': 'NouveauPass123!'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        user_with_password.refresh_from_db()
        assert user_with_password.check_password('NouveauPass123!')

    def test_confirm_invalid_token_rejected(self, api_client, user_with_password):
        """Un jeton invalide est rejeté (400) et le mot de passe est inchangé."""
        uid, _token = self._uid_token(user_with_password)
        response = api_client.post(
            self.CONFIRM_URL,
            {'uid': uid, 'token': 'invalide-xxxx', 'new_password': 'NouveauPass123!'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        user_with_password.refresh_from_db()
        assert user_with_password.check_password('TestPassword123!')

    def test_confirm_token_single_use(self, api_client, user_with_password):
        """Le jeton n'est plus valide après une réinitialisation réussie."""
        uid, token = self._uid_token(user_with_password)
        first = api_client.post(
            self.CONFIRM_URL,
            {'uid': uid, 'token': token, 'new_password': 'NouveauPass123!'},
            format='json',
        )
        assert first.status_code == status.HTTP_200_OK
        second = api_client.post(
            self.CONFIRM_URL,
            {'uid': uid, 'token': token, 'new_password': 'EncoreAutre123!'},
            format='json',
        )
        assert second.status_code == status.HTTP_400_BAD_REQUEST

    def test_confirm_short_password_rejected(self, api_client, user_with_password):
        """Un mot de passe trop court (<8) est rejeté."""
        uid, token = self._uid_token(user_with_password)
        response = api_client.post(
            self.CONFIRM_URL,
            {'uid': uid, 'token': token, 'new_password': 'court'},
            format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
