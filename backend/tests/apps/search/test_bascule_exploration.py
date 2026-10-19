"""
#703 — Bascule de l'exploration entre l'index local et le hub.

Depuis #695, un super administrateur bascule le relais depuis
Administration > Paramètres, sans redémarrage : la bascule devient fréquente et
faite par des non-exploitants. Chaque mode était testé seul ; ces tests
vérifient le passage de l'un à l'autre, dans les deux sens, et les traces
qu'un mode pourrait laisser dans l'autre.
"""
from unittest.mock import patch

import pytest
import requests
from rest_framework.test import APIClient

from apps.core.models import SiteConfiguration
from apps.search.indexing import index_plan
from apps.search.models import PublicationHub, RaccordementHub
from tests.factories import EnjeuFactory, PlanGestionFactory, SiteFactory, UserFactory

pytestmark = pytest.mark.django_db

REPONSE_HUB = {
    'pagination': {'count': 1, 'current_page': 1, 'total_pages': 1, 'page_size': 20},
    'results': [{'nom': 'Plan du hub', 'instance_id': 'cen'}],
}


@pytest.fixture
def instance(settings):
    settings.CICADA_INSTANCE_ID = 'rnf'
    settings.CICADA_INSTANCE_LABEL = 'Réserves Naturelles de France'
    settings.CICADA_EXPLORATION_SOURCE = ''
    settings.CICADA_HUB_URL = 'http://hub:8000'
    settings.CICADA_HUB_READ_TOKEN = 'jeton-lecture'
    SiteConfiguration.objects.create(federation_partage=True)


@pytest.fixture
def client():
    client = APIClient()
    client.force_authenticate(user=UserFactory())
    return client


@pytest.fixture
def plan_local(instance):
    """Un plan « camargue » de cette instance — l'homonyme à ne jamais servir à tort."""
    site = SiteFactory(nom_site='Camargue', id_inpn='FR3600001')
    plan = PlanGestionFactory(statut='valide', nom='Plan de la Camargue', slug='camargue', sites=[site])
    EnjeuFactory(id_pg=plan, libelle='Forêt alluviale')
    index_plan(plan)
    return plan


def basculer(source):
    """Comme le réglage de l'interface (#695) : en base, lu à chaque appel."""
    ligne, _ = RaccordementHub.objects.get_or_create(pk=1)
    ligne.exploration_source = source
    ligne.save()


def hub_repond(corps=REPONSE_HUB):
    mock = patch('apps.search.relay.requests.get')
    appel = mock.start()
    appel.return_value.status_code = 200
    appel.return_value.json.return_value = corps
    return mock, appel


class TestBasculeDansLesDeuxSens:

    def test_local_puis_hub_puis_local(self, client, plan_local):
        mock, appel = hub_repond()
        try:
            basculer('local')
            noms = [p['nom'] for p in client.get('/api/exploration/plans/').json()['results']]
            assert noms == ['Plan de la Camargue']
            appel.assert_not_called()

            basculer('hub')
            noms = [p['nom'] for p in client.get('/api/exploration/plans/').json()['results']]
            assert noms == ['Plan du hub']

            basculer('local')
            appel.reset_mock()
            noms = [p['nom'] for p in client.get('/api/exploration/plans/').json()['results']]
            # Aucun résultat de l'ancien mode servi après la bascule.
            assert noms == ['Plan de la Camargue']
            appel.assert_not_called()
        finally:
            mock.stop()

    def test_la_liste_des_structures_suit_le_mode(self, client, plan_local):
        mock, _ = hub_repond({'count': 2, 'instances': [
            {'instance_id': 'rnf', 'libelle': 'RNF'}, {'instance_id': 'cen', 'libelle': 'CEN'},
        ]})
        try:
            basculer('hub')
            assert client.get('/api/exploration/instances/').json()['count'] == 2
            basculer('local')
            corps = client.get('/api/exploration/instances/').json()
            assert corps['count'] == 1
            assert corps['instances'][0]['instance_id'] == 'rnf'
        finally:
            mock.stop()

    def test_hub_injoignable_502_puis_le_local_retablit_la_recherche(self, client, plan_local):
        basculer('hub')
        with patch('apps.search.relay.requests.get', side_effect=requests.ConnectionError('coupé')):
            assert client.get('/api/exploration/plans/').status_code == 502
        basculer('local')
        assert client.get('/api/exploration/plans/').status_code == 200

    def test_la_bascule_ne_touche_pas_au_consentement_ni_a_la_publication(self, client, plan_local):
        """Passer en local n'est pas retirer ses plans du hub, et inversement."""
        avant = PublicationHub.objects.count()
        with patch('apps.search.raccordement.retirer_du_hub') as retrait, \
             patch('apps.search.tasks.publier_apres_consentement.delay') as publication:
            for source in ('hub', 'local', 'hub', 'local'):
                basculer(source)
        assert SiteConfiguration.objects.get().federation_partage is True
        retrait.assert_not_called()
        publication.assert_not_called()
        assert PublicationHub.objects.count() == avant


class TestUrlPartageeOuverteEnLocal:

    def test_filtre_sur_une_autre_structure(self, client, plan_local):
        """`?instances=cen` venu de l'exploration nationale : pas les plans d'ici."""
        basculer('local')
        assert client.get('/api/exploration/plans/', {'instances': 'cen'}).json()['results'] == []
        assert client.get('/api/exploration/contenus/', {'instances': 'cen'}).json()['results'] == []
        assert client.get('/api/exploration/plans/', {'instances': 'cen,rnf'}).json()['results']

    def test_fiche_d_une_autre_structure_jamais_l_homonyme_local(self, client, plan_local):
        basculer('local')
        reponse = client.get('/api/exploration/plans/cen:camargue/')
        assert reponse.status_code == 404
        assert reponse.json()['erreur'] == 'autre_structure'
        assert reponse.json()['instance_id'] == 'cen'
        assert 'Plan de la Camargue' not in reponse.content.decode()

    def test_fiche_de_cette_structure_par_sa_reference(self, client, plan_local):
        """`rnf:camargue` ouvert sur l'instance rnf elle-même : son propre plan."""
        basculer('local')
        reponse = client.get('/api/exploration/plans/rnf:camargue/')
        assert reponse.status_code == 200
        assert reponse.json()['nom'] == 'Plan de la Camargue'
