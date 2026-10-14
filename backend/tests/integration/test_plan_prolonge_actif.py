"""
#675 — Un plan prolongé (#250) reste « actif » pendant ses années d'extension.

Les filtres `actif` / `actif_en_annee`, le filtre rapide `actifs_cette_annee`
et les statistiques par période se basaient sur `annee_fin` seule : pendant
sa prolongation, le plan était traité comme terminé.

Les années sont exprimées relativement à l'année courante (Y), puisque les
filtres « actif » en dépendent.
"""

from datetime import datetime

import pytest
from rest_framework.test import APIClient

from apps.plans.filters import PlanGestionQuickFilter
from apps.plans.models import PlanGestion
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import SuperAdminFactory

Y = datetime.now().year


@pytest.fixture
def plans():
    """Un plan par cas, nommé d'après son état attendu l'année Y."""
    return {
        # terminé l'an dernier mais prolongé de 2 ans → actif jusqu'en Y+1
        'prolonge_en_cours': PlanGestionFactory(
            nom='prolonge_en_cours', annee_debut=Y - 10, annee_fin=Y - 1, annees_extension=2),
        # prolongation d'1 an déjà écoulée → terminé
        'prolonge_termine': PlanGestionFactory(
            nom='prolonge_termine', annee_debut=Y - 12, annee_fin=Y - 2, annees_extension=1),
        # non prolongé, terminé l'an dernier
        'termine': PlanGestionFactory(
            nom='termine', annee_debut=Y - 10, annee_fin=Y - 1, annees_extension=0),
        # non prolongé, en cours
        'en_cours': PlanGestionFactory(
            nom='en_cours', annee_debut=Y - 2, annee_fin=Y + 3, annees_extension=0),
        # pas encore commencé (même prolongé)
        'futur': PlanGestionFactory(
            nom='futur', annee_debut=Y + 1, annee_fin=Y + 10, annees_extension=2),
    }


def _q_names(q):
    return set(PlanGestion.objects.filter(q).values_list('nom', flat=True))


@pytest.mark.django_db
class TestCriterePlanActif:

    def test_actif_cette_annee(self, plans):
        assert _q_names(PlanGestion.actif_en_q(Y)) == {'prolonge_en_cours', 'en_cours'}

    def test_inactif_cette_annee(self, plans):
        assert _q_names(PlanGestion.inactif_en_q(Y)) == {
            'prolonge_termine', 'termine', 'futur'}

    def test_actif_et_inactif_sont_complementaires(self, plans):
        for annee in range(Y - 13, Y + 12):
            actifs = _q_names(PlanGestion.actif_en_q(annee))
            inactifs = _q_names(PlanGestion.inactif_en_q(annee))
            assert actifs.isdisjoint(inactifs), annee
            assert actifs | inactifs == set(plans), annee

    def test_bornes_de_la_prolongation(self, plans):
        # dernière année d'extension : encore actif ; l'année suivante : terminé
        assert 'prolonge_en_cours' in _q_names(PlanGestion.actif_en_q(Y + 1))
        assert 'prolonge_en_cours' not in _q_names(PlanGestion.actif_en_q(Y + 2))

    def test_filtre_rapide(self, plans):
        assert _q_names(PlanGestionQuickFilter.actifs_cette_annee()) == {
            'prolonge_en_cours', 'en_cours'}


@pytest.mark.django_db
class TestApiPlanActif:

    @pytest.fixture
    def client(self):
        client = APIClient()
        client.force_authenticate(user=SuperAdminFactory())
        return client

    @staticmethod
    def _noms(client, params):
        resp = client.get('/api/plans/plans/', {**params, 'page_size': 100})
        assert resp.status_code == 200
        return {p['nom'] for p in resp.data['results']}

    def test_filtre_actif_true(self, client, plans):
        assert self._noms(client, {'actif': 'true'}) == {'prolonge_en_cours', 'en_cours'}

    def test_filtre_actif_false(self, client, plans):
        assert self._noms(client, {'actif': 'false'}) == {
            'prolonge_termine', 'termine', 'futur'}

    def test_filtre_actif_en_annee_pendant_la_prolongation(self, client, plans):
        assert self._noms(client, {'actif_en_annee': Y + 1}) == {
            'prolonge_en_cours', 'en_cours', 'futur'}

    def test_statistiques_par_periode(self, client, plans):
        resp = client.get('/api/plans/plans/stats/')
        assert resp.status_code == 200
        par_periode = {int(k): v for k, v in resp.data['par_periode'].items()}
        # Y : prolonge_en_cours + en_cours (avant #675 : en_cours seul)
        assert par_periode[Y] == 2
