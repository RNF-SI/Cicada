"""
Factories for notifications app models.
Uses Factory Boy for test data generation.
"""
import factory
from factory.django import DjangoModelFactory
from django.utils import timezone

from apps.notifications.models import Notification, ValidationRequest, PendingUser
from tests.factories.users import RoleFactory, SiteFactory, OrganismeFactory


class NotificationFactory(DjangoModelFactory):
    """Factory for Notification model."""

    class Meta:
        model = Notification

    recipient = factory.SubFactory(RoleFactory)
    notification_type = 'info'
    title = factory.Sequence(lambda n: f'Notification Test {n}')
    message = factory.Faker('paragraph', locale='fr_FR')
    priority = 'medium'
    read = False


class ValidationRequestFactory(DjangoModelFactory):
    """Factory for ValidationRequest model."""

    class Meta:
        model = ValidationRequest

    request_type = 'site_access'
    status = 'pending'
    requester = factory.SubFactory(RoleFactory)
    justification = factory.Faker('paragraph', locale='fr_FR')


class ReferentValidationRequestFactory(ValidationRequestFactory):
    """Factory for referent validation requests."""

    request_type = 'referent_validation'
    target_site = factory.SubFactory(SiteFactory)


class SiteAccessRequestFactory(ValidationRequestFactory):
    """Factory for site access requests."""

    request_type = 'site_access'
    target_site = factory.SubFactory(SiteFactory)


class UserRegistrationRequestFactory(ValidationRequestFactory):
    """Factory for user registration requests."""

    request_type = 'user_registration'
    requester = None  # Registration requests don't have a requester yet
    requested_organisme = factory.SubFactory(OrganismeFactory)


class PendingUserFactory(DjangoModelFactory):
    """Factory for PendingUser model."""

    class Meta:
        model = PendingUser

    email = factory.Sequence(lambda n: f'pending{n}@test.fr')
    password_hash = factory.LazyFunction(
        lambda: 'pbkdf2_sha256$600000$test$hashvalue=='
    )
    nom_role = factory.Faker('last_name', locale='fr_FR')
    prenom_role = factory.Faker('first_name', locale='fr_FR')
    requested_organisme = factory.SubFactory(OrganismeFactory)
    validation_request = factory.SubFactory(
        UserRegistrationRequestFactory,
        requester=None
    )
    justification = factory.Faker('paragraph', locale='fr_FR')
