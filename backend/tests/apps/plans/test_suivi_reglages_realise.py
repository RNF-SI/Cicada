"""
#741 — réglages du tableau budgétaire propres au SUIVI (réalisé).

- « Coût salarial calculé automatiquement » : le coût jour réel diffère souvent
  du prévisionnel ; le suivi peut donc saisir son coût salarial même si la
  programmation le calculait (et inversement).
- « Déclinaison par type de coût » : le réalisé peut être détaillé même si la
  programmation ne l'était pas ; il ne peut pas l'être MOINS (case verrouillée
  quand la programmation est détaillée).

Les deux réglages sont des données de suivi : modifiables plan validé, par
action, et par défaut ceux de la programmation.
"""

from collections import defaultdict
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.plans.models_operations import (
    OperationAnnee, OperationAnneeRH, OperationRealisationGlobale, Poste,
    RealisationOperationAnnee, RealisationOperationAnneeRH,
)
from apps.plans.services_export_finance import build_action_finance, poste_entry_factory
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, MetriqueFactory, NiveauExigenceFactory,
    ObjectifLongTermeFactory, OperationFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import OrganismeFactory, SuperAdminFactory


@pytest.fixture
def action_suivie(db):
    """Action « type de budget + poste », coût salarial calculé, plan VALIDÉ.

    2027 : 10 j prévus à 300 €/j ; 8 j réalisés, et 1 000 € de stage réalisé.
    """
    plan = PlanGestionFactory(annee_debut=2026, annee_fin=2028, statut='valide')
    enjeu = EnjeuFactory(id_pg=plan)
    ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=enjeu))
    met = MetriqueFactory(id_indicateur=IndicateurFactory(id_ne=ne))
    op = OperationFactory(
        metriques=[met], ventilation_mode='by_type_poste', declinaison_par_poste=True,
        declinaison_par_type_cout=True, cout_salarial_auto=True,
    )
    poste = Poste.objects.create(id_pg=plan, id_organisme=OrganismeFactory(), nombre=1, cout_jour=300)
    oa = OperationAnnee.objects.create(id_operation=op, annee=2027, periodicite=True)
    OperationAnneeRH.objects.create(
        id_operation_annee=oa, id_poste=poste, jours=10, categorie_depense='fonctionnement')
    real = RealisationOperationAnnee.objects.create(
        id_operation_annee=oa, periodicite_realisee=True,
        cout_salarial_realise=Decimal('2000'), cout_stage_realise=Decimal('1000'))
    RealisationOperationAnneeRH.objects.create(
        id_realisation_operation_annee=real, id_poste=poste, jours=8,
        categorie_depense='fonctionnement')
    return {'plan': plan, 'op': op}


def _client():
    client = APIClient()
    client.force_authenticate(SuperAdminFactory())
    return client


def _url(op):
    return f'/api/plans/realisations/suivi-reglages/{op.pk}/'


@pytest.mark.django_db
class TestReglagesParDefaut:
    def test_reprennent_ceux_de_la_programmation(self, action_suivie):
        op = action_suivie['op']
        assert op.get_declinaison_par_type_cout_realise() is True
        assert op.get_cout_salarial_auto_realise() is True
        data = _client().get(f'/api/plans/operations/{op.pk}/').json()
        assert data['declinaison_par_type_cout_realise'] is True
        assert data['cout_salarial_auto_realise'] is True


@pytest.mark.django_db
class TestCoutSalarialRealise:
    def test_saisie_au_suivi_malgre_le_calcul_a_la_programmation(self, action_suivie):
        op = action_suivie['op']
        resp = _client().post(_url(op), {'cout_salarial_auto_realise': False}, format='json')
        assert resp.status_code == 200, resp.content
        assert resp.json()['cout_salarial_auto_realise'] is False

        op.refresh_from_db()
        c = build_action_finance(op, {}, defaultdict(poste_entry_factory)).year_total(2027)
        # Prévu : toujours calculé (10 j × 300 €).
        assert c.sal_fonct == Decimal('3000')
        # Réalisé : le montant saisi (2 000 €), pas 8 j × 300 €.
        assert c.rsal_fonct == Decimal('2000')

    def test_calcule_par_defaut(self, action_suivie):
        c = build_action_finance(
            action_suivie['op'], {}, defaultdict(poste_entry_factory)).year_total(2027)
        assert c.rsal_fonct == Decimal('2400')

    def test_modifiable_plan_valide(self, action_suivie):
        assert action_suivie['plan'].statut == 'valide'
        resp = _client().post(_url(action_suivie['op']), {'cout_salarial_auto_realise': False}, format='json')
        assert resp.status_code == 200


@pytest.mark.django_db
class TestDeclinaisonRealise:
    def test_detail_au_suivi_sans_detail_a_la_programmation(self, action_suivie):
        op = action_suivie['op']
        op.ventilation_mode = 'by_type'
        op.declinaison_par_poste = False
        op.declinaison_par_type_cout = False
        op.save()
        assert op.get_declinaison_par_type_cout_realise() is False

        resp = _client().post(_url(op), {'declinaison_par_type_cout_realise': True}, format='json')
        assert resp.status_code == 200, resp.content
        op.refresh_from_db()
        assert op.get_declinaison_par_type_cout_realise() is True
        c = build_action_finance(op, {}, defaultdict(poste_entry_factory)).year_total(2027)
        # Détail réalisé compté (salarial saisi 2 000 + stage 1 000)…
        assert c.rtot == Decimal('3000')
        # …et le prévu reste en enveloppes (rien de saisi ici).
        assert c.tot == Decimal('0')

    def test_ne_peut_pas_etre_retiree_si_la_programmation_est_detaillee(self, action_suivie):
        op = action_suivie['op']
        resp = _client().post(_url(op), {'declinaison_par_type_cout_realise': False}, format='json')
        assert resp.status_code == 400
        assert op.get_declinaison_par_type_cout_realise() is True

    def test_retirer_la_surcharge_de_niveau_garde_les_reglages(self, action_suivie):
        op = action_suivie['op']
        client = _client()
        client.post(_url(op), {'cout_salarial_auto_realise': False}, format='json')
        client.delete(f'/api/plans/realisations/global-realisation/{op.pk}/')
        assert OperationRealisationGlobale.objects.get(id_operation=op).cout_salarial_auto_realise is False
