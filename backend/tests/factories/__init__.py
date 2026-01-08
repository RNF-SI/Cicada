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
]
