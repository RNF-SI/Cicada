"""
Consentement au partage avec l'exploration nationale (#636).

Publier le contenu de ses plans est un **engagement de la structure**, pas un
réglage technique. Ces tests verrouillent les trois conséquences de ce principe :

1. rien ne sort tant que personne n'a choisi — y compris après une mise à jour ;
2. la décision ne peut pas être contournée par une automatisation ;
3. retirer ses données reste possible, et se distingue d'un accident.

Ce que le partage fait sortir — la structure des plans, jamais le budget ni les
RH — est verrouillé ailleurs, par `TestFichePubliqueCloisonnement`.
"""

from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from apps.core.models import SiteConfiguration
from apps.search.indexing import index_plan
from apps.search.push import partage_active
from apps.search.relay import relais_actif
from tests.factories import EnjeuFactory, PlanGestionFactory, SiteFactory, UserFactory


@pytest.fixture
def configuration(db):
    """La configuration d'instance, telle qu'elle existe après installation."""
    return SiteConfiguration.objects.create()


@pytest.fixture
def plan_publiable(db):
    site = SiteFactory(nom_site='Camargue', id_inpn='FR3600001')
    plan = PlanGestionFactory(statut='valide', nom='Plan test', sites=[site])
    EnjeuFactory(id_pg=plan, libelle='Forêt alluviale')
    index_plan(plan)
    return plan


@pytest.mark.django_db
class TestDefaut:
    def test_sans_configuration_le_partage_est_inactif(self):
        """
        Une instance fraîchement installée ne publie rien.

        C'est le comportement sûr : l'absence de décision ne vaut pas
        consentement.
        """
        assert partage_active() is False

    def test_le_partage_est_desactive_par_defaut(self, configuration):
        """
        Une mise à jour ne doit pas décider à la place de la structure.

        Si le défaut était « partagé », une montée de version ferait sortir le
        contenu des plans sans que personne ne l'ait voulu — et la structure
        l'apprendrait après coup, ou jamais.
        """
        assert configuration.federation_partage is False
        assert partage_active() is False

    def test_activer_le_partage_suffit(self, configuration):
        configuration.federation_partage = True
        configuration.save()
        assert partage_active() is True


@pytest.mark.django_db
class TestPublication:
    def test_sans_consentement_rien_n_est_publie(
        self, configuration, plan_publiable, settings
    ):
        """
        Refus franc, et non dépôt silencieux d'un lot vide.

        La commande peut être appelée par une tâche planifiée : si elle publiait
        malgré un partage désactivé, la décision de la structure serait
        contournée par une automatisation que personne ne relit.
        """
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'

        with patch('requests.request') as appel:
            with pytest.raises(CommandError, match='partage'):
                call_command('push_federation')

        appel.assert_not_called()

    def test_le_message_indique_la_marche_a_suivre(self, configuration, plan_publiable):
        """
        Un refus qui n'explique pas se lit comme une panne.

        L'exploitant qui voit échouer la tâche doit comprendre que c'est un
        choix de la structure, et savoir qui peut le changer.
        """
        with pytest.raises(CommandError) as echec:
            call_command('push_federation')

        message = str(echec.value)
        assert 'partage' in message
        assert 'paramètres' in message
        assert 'retrait_federation' in message

    def test_avec_consentement_la_publication_reprend(
        self, configuration, plan_publiable, settings
    ):
        configuration.federation_partage = True
        configuration.save()
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'

        with patch('requests.request') as appel:
            appel.return_value.status_code = 201
            appel.return_value.content = b'{}'
            appel.return_value.json.return_value = {
                'lot_id': 'lot-1', 'plans_recus': 1, 'contenus_recus': 1,
                'plans_purges': 0,
            }
            call_command('push_federation')

        assert appel.called


@pytest.mark.django_db
class TestRetrait:
    """
    Retirer ses données est un droit, et doit rester simple à exercer.

    D'où une commande distincte de la publication : celle-ci refuse de déposer
    un lot vide, parce qu'un index momentanément vide effacerait tout sans que
    personne ne l'ait demandé. La distinction n'est pas entre autorisé et
    interdit, mais entre **accidentel** et **voulu**.
    """

    def test_le_retrait_exige_une_confirmation(self, configuration, settings):
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'

        with patch('requests.request') as appel:
            call_command('retrait_federation')

        appel.assert_not_called()

    def test_le_retrait_confirme_bascule_un_lot_vide(self, configuration, settings):
        """
        Aucun endpoint de suppression n'est nécessaire : le hub purge ce qui
        n'a pas été revu, et un lot sans plan n'en revoit aucun.
        """
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'

        appels = []

        def repondre(methode, url, **kwargs):
            appels.append((methode, url))
            reponse = type('R', (), {})()
            reponse.status_code = 200
            reponse.content = b'{}'
            reponse.text = ''
            reponse.json = lambda: {'lot_id': 'lot-1', 'plans_purges': 22}
            return reponse

        with patch('requests.request', side_effect=repondre):
            call_command('retrait_federation', '--confirmer')

        chemins = [url for _, url in appels]
        assert any(url.endswith('/api/federation/lots/') for url in chemins)
        assert any('bascule' in url for url in chemins)
        # Aucune page de plans : c'est précisément ce qui vide l'index.
        assert not any(url.endswith('/plans/') for url in chemins)

    def test_le_retrait_reste_possible_sans_consentement(self, configuration, settings):
        """
        Le cas qui compte : on vient de désactiver le partage, et il faut
        pouvoir retirer ce qui a déjà été publié. Si le retrait exigeait un
        consentement actif, la donnée resterait sur le hub sans moyen de la
        reprendre.
        """
        assert configuration.federation_partage is False
        settings.CICADA_HUB_URL = 'http://hub:8000'
        settings.CICADA_HUB_PUSH_TOKEN = 'jeton'

        with patch('requests.request') as appel:
            appel.return_value.status_code = 200
            appel.return_value.content = b'{}'
            appel.return_value.json.return_value = {
                'lot_id': 'lot-1', 'plans_purges': 3,
            }
            call_command('retrait_federation', '--confirmer')

        assert appel.called


@pytest.mark.django_db
class TestExploration:
    def test_sans_consentement_l_exploration_reste_locale(
        self, configuration, settings
    ):
        """
        Une instance qui ne publie pas n'explore que ses propres plans.

        Ce n'est pas une punition : l'exploration nationale n'existe que par ce
        que chacun y verse.
        """
        settings.CICADA_EXPLORATION_SOURCE = 'hub'
        settings.CICADA_HUB_URL = 'http://hub:8000'

        assert relais_actif() is False

    def test_avec_consentement_le_relais_s_active(self, configuration, settings):
        configuration.federation_partage = True
        configuration.save()
        settings.CICADA_EXPLORATION_SOURCE = 'hub'
        settings.CICADA_HUB_URL = 'http://hub:8000'

        assert relais_actif() is True

    def test_l_exploration_locale_repond_toujours(
        self, configuration, plan_publiable, settings
    ):
        """Refuser de partager ne prive pas de l'exploration de ses propres plans."""
        settings.CICADA_EXPLORATION_SOURCE = 'hub'
        settings.CICADA_HUB_URL = 'http://hub:8000'

        client = APIClient()
        client.force_authenticate(user=UserFactory())
        reponse = client.get('/api/exploration/contenus/')

        assert reponse.status_code == 200
        assert reponse.json()['pagination']['count'] >= 1


@pytest.mark.django_db
class TestReglage:
    """Le consentement se change depuis l'interface, sans redéploiement."""

    def test_le_reglage_est_expose_par_l_api(self, configuration):
        client = APIClient()
        client.force_authenticate(user=UserFactory(is_superuser=True, is_staff=True))

        reponse = client.get('/api/settings/')
        assert reponse.status_code == 200
        assert reponse.json()['federation_partage'] is False
