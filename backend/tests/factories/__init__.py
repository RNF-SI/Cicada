"""
Factory Boy factories for test data generation.
"""
from tests.factories.users import (
    OrganismeFactory,
    RoleFactory,
    UserFactory,
    SuperAdminFactory,
    AdminOrganismeFactory,
    ReferentFactory,
    SiteFactory,
    CorRoleSiteFactory,
    CorOgSiteFactory,
)
from tests.factories.plans import (
    PlanGestionFactory,
    CorSitePgFactory,
    CorPgFichierFactory,
)
from tests.factories.core import (
    TypeNomenclatureFactory,
    NomenclatureFactory,
)
from tests.factories.notifications import (
    NotificationFactory,
    ValidationRequestFactory,
    ReferentValidationRequestFactory,
    SiteAccessRequestFactory,
    UserRegistrationRequestFactory,
    PendingUserFactory,
)

__all__ = [
    # Users factories
    'OrganismeFactory',
    'RoleFactory',
    'UserFactory',
    'SuperAdminFactory',
    'AdminOrganismeFactory',
    'ReferentFactory',
    'SiteFactory',
    'CorRoleSiteFactory',
    'CorOgSiteFactory',
    # Plans factories
    'PlanGestionFactory',
    'CorSitePgFactory',
    'CorPgFichierFactory',
    # Core factories
    'TypeNomenclatureFactory',
    'NomenclatureFactory',
    # Notifications factories
    'NotificationFactory',
    'ValidationRequestFactory',
    'ReferentValidationRequestFactory',
    'SiteAccessRequestFactory',
    'UserRegistrationRequestFactory',
    'PendingUserFactory',
]
