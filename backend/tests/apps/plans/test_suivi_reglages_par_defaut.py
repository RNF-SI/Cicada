"""
#761 — les réglages du 1er suivi saisi du plan deviennent ceux proposés par
défaut pour les autres actions.

Réglages repris : « Déclinaison par type de coût » (#741) et « Déclinaison
par type de poste » (#760). Référence : le 1er suivi saisi du plan (et non le
dernier). Les règles de la programmation priment, et les suivis déjà
enregistrés ne changent pas.
"""

import pytest
from rest_framework.test import APIClient

from apps.plans.models_operations import (
    OperationAnnee, OperationRealisationGlobale, RealisationOperationAnnee,
)
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, MetriqueFactory, NiveauExigenceFactory,
    ObjectifLongTermeFactory, OperationFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import SuperAdminFactory


@pytest.fixture
def plan(db):
    p = PlanGestionFactory(annee_debut=2026, annee_fin=2028, statut='valide')
    ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=EnjeuFactory(id_pg=p)))
    p._met = MetriqueFactory(id_indicateur=IndicateurFactory(id_ne=ne))
    return p


def _action(plan, code, **kw):
    kw.setdefault('ventilation_mode', 'none')
    kw.setdefault('declinaison_par_type_cout', False)
    op = OperationFactory(metriques=[plan._met], code_operation=code, **kw)
    oa = OperationAnnee.objects.create(id_operation=op, annee=2027, periodicite=True)
    return op, oa


def _suivi(op, oa, **reglages):
    if reglages:
        OperationRealisationGlobale.objects.create(id_operation=op, **reglages)
    return RealisationOperationAnnee.objects.create(id_operation_annee=oa)


def _client():
    client = APIClient()
    client.force_authenticate(SuperAdminFactory())
    return client


def _defaults(plan):
    r = _client().get(f'/api/plans/operations/suivi-defaults/{plan.id_pg}/')
    assert r.status_code == 200, r.content
    return r.json()


@pytest.mark.django_db
class TestSuiviDefaults:
    def test_aucun_suivi_dans_le_plan(self, plan):
        _action(plan, 'A1')
        data = _defaults(plan)
        assert data['source_operation_id'] is None
        assert data['declinaison_par_type_cout_realise'] is None
        assert data['declinaison_par_poste_realise'] is None

    def test_reglages_du_premier_suivi_et_non_du_dernier(self, plan):
        premier, oa1 = _action(plan, 'A1')
        _suivi(premier, oa1, declinaison_par_type_cout_realise=True,
               declinaison_par_poste_realise=True)
        dernier, oa2 = _action(plan, 'A2')
        _suivi(dernier, oa2)  # réglages de la programmation : rien de décliné
        data = _defaults(plan)
        assert data['source_operation_id'] == premier.id_operation
        assert data['declinaison_par_type_cout_realise'] is True
        assert data['declinaison_par_poste_realise'] is True

    def test_reglages_effectifs_du_premier_suivi(self, plan):
        """Le 1er suivi n'a rien réglé : ce sont ceux de sa programmation."""
        premier, oa1 = _action(plan, 'A1', ventilation_mode='by_type_poste',
                               declinaison_par_type_cout=True, declinaison_par_poste=True)
        _suivi(premier, oa1)
        data = _defaults(plan)
        assert data['declinaison_par_type_cout_realise'] is True
        assert data['declinaison_par_poste_realise'] is True


@pytest.mark.django_db
class TestReglagesDefinis:
    """Le client sait si les réglages d'une action ont déjà été posés."""

    def test_exposes_sur_l_action(self, plan):
        op, oa = _action(plan, 'A1')
        url = f'/api/plans/operations/{op.pk}/'
        assert _client().get(url).json()['reglages_suivi_definis'] is False
        OperationRealisationGlobale.objects.create(id_operation=op, declinaison_par_poste_realise=False)
        assert _client().get(url).json()['reglages_suivi_definis'] is True

    def test_surcharge_de_niveau_seule_ne_compte_pas(self, plan):
        op, _oa = _action(plan, 'A1')
        OperationRealisationGlobale.objects.create(id_operation=op, commentaire_override='x')
        assert _client().get(f'/api/plans/operations/{op.pk}/').json()['reglages_suivi_definis'] is False
