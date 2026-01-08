"""
Root conftest.py - Shared fixtures across all test modules.
Configuration pytest pour le projet Outil Plan de Gestion.
"""
import pytest
from django.test import Client
from rest_framework.test import APIClient

# Import all factories
pytest_plugins = ['tests.factories']


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear Django cache before each test to ensure test isolation."""
    from django.core.cache import cache
    cache.clear()
    yield
    # Clear again after test for good measure
    cache.clear()


@pytest.fixture
def api_client():
    """Return an unauthenticated DRF API client."""
    return APIClient()


@pytest.fixture
def django_client():
    """Return a standard Django test client."""
    return Client()


@pytest.fixture
def authenticated_client(api_client, db):
    """
    Return an authenticated API client with a basic user.
    Returns tuple (client, user) for access to both.
    """
    from tests.factories.users import UserFactory

    user = UserFactory()
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.fixture
def super_admin_client(api_client, db):
    """
    Return an authenticated API client with a super admin user.
    Returns tuple (client, user) for access to both.
    """
    from tests.factories.users import SuperAdminFactory

    admin = SuperAdminFactory()
    api_client.force_authenticate(user=admin)
    return api_client, admin


@pytest.fixture
def admin_og_client(api_client, db):
    """
    Return an authenticated API client with an organisme admin user.
    Returns tuple (client, user) for access to both.
    """
    from tests.factories.users import AdminOrganismeFactory

    admin_og = AdminOrganismeFactory()
    api_client.force_authenticate(user=admin_og)
    return api_client, admin_og


@pytest.fixture
def referent_client(api_client, db):
    """
    Return an authenticated API client with a referent user.
    Returns tuple (client, user) for access to both.
    """
    from tests.factories.users import ReferentFactory

    referent = ReferentFactory()
    api_client.force_authenticate(user=referent)
    return api_client, referent


# Convenience fixtures for creating model instances
@pytest.fixture
def user_factory(db):
    """Return the UserFactory for creating users in tests."""
    from tests.factories.users import UserFactory
    return UserFactory


@pytest.fixture
def super_admin_factory(db):
    """Return the SuperAdminFactory for creating super admins in tests."""
    from tests.factories.users import SuperAdminFactory
    return SuperAdminFactory


@pytest.fixture
def admin_organisme_factory(db):
    """Return the AdminOrganismeFactory for creating org admins in tests."""
    from tests.factories.users import AdminOrganismeFactory
    return AdminOrganismeFactory


@pytest.fixture
def referent_factory(db):
    """Return the ReferentFactory for creating referents in tests."""
    from tests.factories.users import ReferentFactory
    return ReferentFactory


@pytest.fixture
def organisme_factory(db):
    """Return the OrganismeFactory for creating organismes in tests."""
    from tests.factories.users import OrganismeFactory
    return OrganismeFactory


@pytest.fixture
def site_factory(db):
    """Return the SiteFactory for creating sites in tests."""
    from tests.factories.users import SiteFactory
    return SiteFactory


@pytest.fixture
def plan_factory(db):
    """Return the PlanGestionFactory for creating plans in tests."""
    from tests.factories.plans import PlanGestionFactory
    return PlanGestionFactory


@pytest.fixture
def nomenclature_factory(db):
    """Return the NomenclatureFactory for creating nomenclatures in tests."""
    from tests.factories.core import NomenclatureFactory
    return NomenclatureFactory
