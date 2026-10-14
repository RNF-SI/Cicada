"""
Tests de #683 / #693 — écrans réels d'un plan distant.

- ce qu'une instance **publie** pour ses écrans (`ecrans_du_plan`) ne contient
  aucune donnée de gestion, à aucune profondeur ;
- ce que l'instance lectrice **ressert** (`/api/exploration/distant/…`) répond
  sous les chemins de l'API des plans, avec la référence comme slug et la
  provenance, et refuse tout le reste.
"""

from unittest import mock

import pytest
from rest_framework.test import APIClient

from apps.search.distant import repondre
from apps.search.ecrans import ecrans_du_plan
# Import du module et non de la classe : pytest collecterait sinon ses tests
# une seconde fois ici, sans leurs fixtures.
from tests.apps.plans import test_lecture_exploration as lecture
from tests.apps.plans.test_lecture_exploration import cles, plan_valide  # noqa: F401 (fixture)
from tests.factories.users import RoleFactory


class TestEcransPubliesCloisonnement:
    """Même garde-fou que pour la lecture d'exploration locale, sur ce qui part vers le hub."""

    INTERDITS = lecture.TestCloisonnementParFragments.INTERDITS
    TOLERES = lecture.TestCloisonnementParFragments.TOLERES

    def test_les_ecrans_publies_ne_portent_aucune_donnee_de_gestion(self, plan_valide):
        ecrans = ecrans_du_plan(plan_valide)
        fautifs = sorted(
            cle for cle in cles(ecrans)
            if cle not in self.TOLERES
            and any(fragment in cle.lower() for fragment in self.INTERDITS)
        )
        assert fautifs == []

    def test_les_ecrans_ont_la_forme_de_lapi_locale(self, plan_valide):
        ecrans = ecrans_du_plan(plan_valide)
        assert ecrans['plan']['slug'] == plan_valide.slug
        assert ecrans['plan']['acces_exploration'] is True
        assert [e['libelle'] for e in ecrans['enjeux']['enjeux']] == ['Enjeu public']
        assert ecrans['enjeux']['acces_exploration'] is True
        assert ecrans['operations_par_type']['total'] == 1
        operation = ecrans['operations'][str(plan_valide.operation_racine.pk)]
        assert operation['libelle'] == 'Action publique'
        assert operation['acces_exploration'] is True
        assert 'operation_annees' not in operation


ECRANS = {
    'plan': {'id_pg': 42, 'slug': 'camargue', 'nom': 'Camargue'},
    'enjeux': {'plan_id': 42, 'plan_slug': 'camargue', 'enjeux': []},
    'operations_par_type': {'plan_id': 42, 'groups': []},
    'operations': {'7': {'id_operation': 7, 'libelle': 'Comptage'}},
    'reference': 'rnf:camargue',
    'instance_id': 'rnf',
    'instance_libelle': 'RNF',
    'url_instance': 'https://rnf.example',
    'date_publication': '2026-10-06T00:00:00Z',
}


class TestRepondre:

    def test_la_page_du_plan_porte_la_reference_comme_slug(self):
        donnees = repondre(ECRANS, 'plans/by-slug/camargue/', 'rnf:camargue')
        assert donnees['slug'] == 'rnf:camargue'
        assert donnees['nom'] == 'Camargue'
        assert donnees['instance_libelle'] == 'RNF'
        assert donnees['date_publication'] == '2026-10-06T00:00:00Z'

    def test_le_detail_par_identifiant_repond_aussi(self):
        assert repondre(ECRANS, 'plans/42/', 'rnf:camargue')['slug'] == 'rnf:camargue'

    def test_larborescence(self):
        donnees = repondre(ECRANS, 'enjeux/by-plan/42/', 'rnf:camargue')
        assert donnees['plan_slug'] == 'rnf:camargue'
        assert donnees['enjeux'] == []

    def test_les_actions_du_plan(self):
        assert repondre(ECRANS, 'operations/by-plan/42/', 'rnf:camargue')['groups'] == []

    def test_une_action(self):
        donnees = repondre(ECRANS, 'operations/7/', 'rnf:camargue')
        assert donnees['libelle'] == 'Comptage'
        assert donnees['instance_id'] == 'rnf'

    def test_tout_le_reste_est_refuse(self):
        for chemin in (
            'operations/8/', 'realisations/by-plan/42/', 'plans/42/export-plan-docx/',
            'postes/by-plan/42/', 'plans/', 'enjeux/',
        ):
            assert repondre(ECRANS, chemin, 'rnf:camargue') is None, chemin


@pytest.fixture
def client(db):
    client = APIClient()
    client.force_authenticate(RoleFactory())
    return client


class TestVueDistante:

    def test_sans_hub_configure_404(self, client, settings):
        settings.CICADA_HUB_URL = ''
        reponse = client.get('/api/exploration/distant/rnf:camargue/plans/by-slug/camargue/')
        assert reponse.status_code == 404

    def test_sert_linstantane_lu_sur_le_hub(self, client, settings):
        settings.CICADA_HUB_URL = 'http://hub'
        settings.CICADA_HUB_READ_TOKEN = 'lecture'
        settings.CICADA_EXPLORATION_SOURCE = 'hub'
        with mock.patch('apps.search.distant.relais_actif', return_value=True), \
             mock.patch('apps.search.distant.lire_ecrans', return_value=ECRANS) as lecture:
            reponse = client.get('/api/exploration/distant/rnf:camargue/plans/by-slug/camargue/')
            assert reponse.status_code == 200
            assert reponse.data['slug'] == 'rnf:camargue'
            lecture.assert_called_once_with('rnf:camargue')

            assert client.get(
                '/api/exploration/distant/rnf:camargue/operations/7/'
            ).data['libelle'] == 'Comptage'
            assert client.get(
                '/api/exploration/distant/rnf:camargue/realisations/by-plan/42/'
            ).status_code == 404

    def test_un_plan_inconnu_du_hub_404(self, client):
        with mock.patch('apps.search.distant.relais_actif', return_value=True), \
             mock.patch('apps.search.distant.lire_ecrans', return_value=None):
            reponse = client.get('/api/exploration/distant/cen:inconnu/plans/by-slug/inconnu/')
            assert reponse.status_code == 404

    def test_anonyme_refuse(self, db):
        reponse = APIClient().get('/api/exploration/distant/rnf:camargue/plans/by-slug/camargue/')
        assert reponse.status_code in (401, 403)
