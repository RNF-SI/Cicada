"""
Tests d'intégration des endpoints de copie profonde (#552) :
POST .../facteurs-influence/{id}/copy/, .../objectifs-operationnels/{id}/copy/,
.../operations/{id}/copy/.

La logique de copie est couverte en unitaire (test_element_copy.py) ; ici on
valide le câblage : authentification, 201, garde « même plan », verrou brouillon.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.plans.models_enjeux import FacteurInfluence, ObjectifOperationnel
from apps.plans.models_operations import Operation, CorOperationMetrique
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory
from tests.factories.users import (
    ReferentFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)
from tests.factories.enjeux import (
    EnjeuFactory, NomenclatureEnjeuFactory, FacteurInfluenceFactory,
    PressionFactory, ObjectifOperationnelFactory, ResultatAttenduFactory,
    IndicateurPressionFactory, MetriqueFactory, OperationFactory,
    NomenclatureTypeIndicateurFactory, NomenclatureTypeMetriqueFactory,
)


@pytest.fixture
def data(db):
    org = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=org)
    referent = ReferentFactory(id_organisme=org)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    cat = NomenclatureEnjeuFactory()

    plan = PlanGestionFactory(statut='draft', id_utilisateur_ajout=referent)
    CorSitePgFactory(plan_de_gestion=plan, site=site)
    plan.referents.add(referent)

    type_ind = NomenclatureTypeIndicateurFactory()
    type_met = NomenclatureTypeMetriqueFactory()

    enjeu = EnjeuFactory(id_pg=plan, id_categorie=cat, libelle='E1', id_utilisateur_ajout=referent)
    target = EnjeuFactory(id_pg=plan, id_categorie=cat, libelle='E2', id_utilisateur_ajout=referent)
    fi = FacteurInfluenceFactory(id_enjeu=enjeu, id_utilisateur_ajout=referent)
    pr = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=referent)
    pr_target = PressionFactory(id_facteur_influence=fi, id_utilisateur_ajout=referent)
    oo = ObjectifOperationnelFactory(id_utilisateur_ajout=referent, pressions=[pr])
    ra = ResultatAttenduFactory(id_oo=oo, id_utilisateur_ajout=referent)
    ind = IndicateurPressionFactory(id_resultat_attendu=ra, type_indicateur=type_ind, id_utilisateur_ajout=referent)
    met = MetriqueFactory(id_indicateur=ind, type_metrique=type_met, id_utilisateur_ajout=referent)
    met_target = MetriqueFactory(id_indicateur=ind, type_metrique=type_met, id_utilisateur_ajout=referent)
    op = OperationFactory(libelle='OP', id_priorite=None, id_utilisateur_ajout=referent)
    CorOperationMetrique.objects.create(id_operation=op, id_metrique=met)

    client = APIClient()
    client.force_authenticate(user=referent)
    return {
        'client': client, 'referent': referent, 'plan': plan,
        'enjeu': enjeu, 'target': target, 'fi': fi, 'pr_target': pr_target,
        'oo': oo, 'op': op, 'met_target': met_target,
    }


@pytest.mark.django_db
@pytest.mark.integration
class TestCopyEndpoints:
    def test_copy_facteur_creates_independent_copy(self, data):
        resp = data['client'].post(
            f"/api/plans/facteurs-influence/{data['fi'].id_facteur_influence}/copy/",
            {'enjeu_id': data['target'].id_enjeu}, format='json',
        )
        assert resp.status_code == status.HTTP_201_CREATED
        new_id = resp.data['id_facteur_influence']
        assert new_id != data['fi'].id_facteur_influence
        new_fi = FacteurInfluence.objects.get(pk=new_id)
        assert list(new_fi.enjeux.values_list('id_enjeu', flat=True)) == [data['target'].id_enjeu]

    def test_copy_oo_to_pression(self, data):
        resp = data['client'].post(
            f"/api/plans/objectifs-operationnels/{data['oo'].id_oo}/copy/",
            {'pression_id': data['pr_target'].id_pression}, format='json',
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['id_oo'] != data['oo'].id_oo

    def test_copy_operation_to_metrique(self, data):
        resp = data['client'].post(
            f"/api/plans/operations/{data['op'].id_operation}/copy/",
            {'metrique_id': data['met_target'].id_metrique}, format='json',
        )
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['id_operation'] != data['op'].id_operation

    def test_copy_oo_requires_exactly_one_target(self, data):
        resp = data['client'].post(
            f"/api/plans/objectifs-operationnels/{data['oo'].id_oo}/copy/",
            {}, format='json',
        )
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_copy_facteur_blocked_on_validated_plan(self, data):
        data['plan'].statut = 'valide'
        data['plan'].save(update_fields=['statut'])
        resp = data['client'].post(
            f"/api/plans/facteurs-influence/{data['fi'].id_facteur_influence}/copy/",
            {'enjeu_id': data['target'].id_enjeu}, format='json',
        )
        assert resp.status_code == status.HTTP_403_FORBIDDEN
