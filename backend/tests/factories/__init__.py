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
    CorRolePlanFactory,
    CorPgFichierFactory,
)
from tests.factories.core import (
    TypeNomenclatureFactory,
    NomenclatureFactory,
    ActivityLogFactory,
)
from tests.factories.notifications import (
    NotificationFactory,
    ValidationRequestFactory,
    ReferentValidationRequestFactory,
    SiteAccessRequestFactory,
    UserRegistrationRequestFactory,
    PendingUserFactory,
)
from tests.factories.enjeux import (
    CategorieEnjeuTypeFactory,
    NomenclatureEnjeuFactory,
    NomenclatureFcrFactory,
    CategorieFcrTypeFactory,
    NomenclatureCategorieFcrFactory,
    EnjeuFactory,
    FcrFactory,
    FacteurInfluenceFactory,
    PressionFactory,
    ObjectifLongTermeFactory,
    NiveauExigenceFactory,
    CorEnjeuTaxonFactory,
    CorEnjeuHabitatFactory,
    CorEnjeuGeologieFactory,
    # Indicateur / Metrique / Mesure factories
    TypeIndicateurTypeFactory,
    NomenclatureTypeIndicateurFactory,
    TypeMetriqueTypeFactory,
    NomenclatureTypeMetriqueFactory,
    IndicateurFactory,
    MetriqueFactory,
    MesureFactory,
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
    'CorRolePlanFactory',
    'CorPgFichierFactory',
    # Core factories
    'TypeNomenclatureFactory',
    'NomenclatureFactory',
    'ActivityLogFactory',
    # Notifications factories
    'NotificationFactory',
    'ValidationRequestFactory',
    'ReferentValidationRequestFactory',
    'SiteAccessRequestFactory',
    'UserRegistrationRequestFactory',
    'PendingUserFactory',
    # Enjeux factories
    'CategorieEnjeuTypeFactory',
    'NomenclatureEnjeuFactory',
    'NomenclatureFcrFactory',
    'CategorieFcrTypeFactory',
    'NomenclatureCategorieFcrFactory',
    'EnjeuFactory',
    'FcrFactory',
    'FacteurInfluenceFactory',
    'PressionFactory',
    'ObjectifLongTermeFactory',
    'NiveauExigenceFactory',
    'CorEnjeuTaxonFactory',
    'CorEnjeuHabitatFactory',
    'CorEnjeuGeologieFactory',
    # Indicateur / Metrique / Mesure factories
    'TypeIndicateurTypeFactory',
    'NomenclatureTypeIndicateurFactory',
    'TypeMetriqueTypeFactory',
    'NomenclatureTypeMetriqueFactory',
    'IndicateurFactory',
    'MetriqueFactory',
    'MesureFactory',
]
