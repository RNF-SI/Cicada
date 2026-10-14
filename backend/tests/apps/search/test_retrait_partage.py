"""
Retirer son consentement au partage retire ses plans — et son accès (#636).

Décision produit du 09/10/2026 : « Si quelqu'un ne veut plus partager, alors il
ne doit plus avoir accès aux plans des autres instances. » Couper le relais côté
instance ne suffit pas : quiconque administre l'instance peut le rallumer. La
règle est donc tenue par le hub, qui ne sert que les instances ayant des plans
publiés — et décocher le partage les retire immédiatement.

Le hub n'est pas lancé ici : ses réponses sont simulées. Le refus effectif de
la lecture après un retrait est vérifié par la suite du hub
(`TestReciprocite`) et, de bout en bout, par le banc de la fédération.
"""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.core.models import SiteConfiguration
from apps.search import raccordement as rac
from apps.search.models import PublicationHub, RaccordementHub
from apps.search.tasks import publier_apres_consentement, relancer_retrait_hub
from tests.factories import SuperAdminFactory

JETON_SUIVI = '123e4567-e89b-12d3-a456-426614174000'
CONTACT = {'contact_nom': 'Camille Martin', 'contact_email': 'camille@cen.example'}


@pytest.fixture(autouse=True)
def configuration_vierge(db, settings, monkeypatch):
    """Instance identifiée, sans jeton d'environnement (cf. `test_raccordement`)."""
    settings.CICADA_INSTANCE_ID = 'cen-aura'
    settings.CICADA_INSTANCE_LABEL = 'CEN Auvergne-Rhône-Alpes'
    settings.CICADA_PUBLIC_URL = 'https://cen.example'
    settings.CICADA_HUB_URL = ''
    settings.CICADA_HUB_PUSH_TOKEN = ''
    settings.CICADA_HUB_READ_TOKEN = ''
    settings.CICADA_EXPLORATION_SOURCE = 'local'
    settings.CICADA_HUB_PUSH_AUTO = True
    monkeypatch.setenv('CICADA_TRACKING_TOKEN', JETON_SUIVI)
    monkeypatch.setenv('TRACKING_API_URL', 'http://suivi/api')


@pytest.fixture
def admin_client():
    client = APIClient()
    client.force_authenticate(user=SuperAdminFactory())
    return client


@pytest.fixture
def raccordee():
    """Adhésion acceptée et partage consenti : l'instance publie et lit."""
    RaccordementHub(
        jeton_depot_chiffre=rac.chiffrer('depot-secret'),
        jeton_lecture_chiffre=rac.chiffrer('lecture-secret'),
        adhesion_statut=RaccordementHub.STATUT_ACCEPTEE,
        adhesion_instance_id='cen-aura', hub_url='http://hub',
    ).save()
    return SiteConfiguration.objects.create(federation_partage=True)


def hub_qui_purge(purges=4, appels=None):
    """Simule le hub : ouverture d'un lot, puis bascule qui purge `purges` plans."""
    appels = appels if appels is not None else []

    def repondre(methode, url, headers=None, data=None, timeout=None):
        appels.append({'methode': methode, 'url': url, 'headers': headers,
                       'corps': json.loads(data) if data else None})
        r = MagicMock()
        r.status_code = 201 if url.endswith('/lots/') else 200
        corps = {'lot_id': 'lot-9'} if url.endswith('/lots/') else {
            'plans_recus': 0, 'contenus_recus': 0, 'plans_purges': purges,
        }
        r.json.return_value = corps
        r.content = json.dumps(corps).encode()
        r.text = json.dumps(corps)
        return r

    return repondre, appels


def decocher(client):
    return client.patch('/api/settings/', {'federation_partage': False}, format='json')


def cocher(client):
    return client.patch('/api/settings/', {'federation_partage': True}, format='json')


@pytest.mark.django_db
class TestDecocherRetire:
    def test_decocher_retire_les_plans_du_hub(self, admin_client, raccordee):
        """Lot vide ouvert puis basculé, avec le jeton de dépôt de l'adhésion."""
        repondre, appels = hub_qui_purge(purges=4)
        with patch('apps.search.raccordement.requests.request', side_effect=repondre):
            rep = decocher(admin_client)

        assert rep.status_code == 200
        assert rep.json()['federation_partage'] is False
        assert [(a['methode'], a['url']) for a in appels] == [
            ('POST', 'http://hub/api/federation/lots/'),
            ('POST', 'http://hub/api/federation/lots/lot-9/bascule/'),
        ]
        assert all(a['headers']['X-Federation-Token'] == 'depot-secret' for a in appels)
        # Aucune page de plans : c'est précisément ce qui vide l'index distant.
        assert not any(a['url'].endswith('/plans/') for a in appels)
        assert RaccordementHub.objects.get().retrait_en_attente is False

    def test_le_retrait_est_journalise(self, admin_client, raccordee):
        repondre, _ = hub_qui_purge(purges=4)
        with patch('apps.search.raccordement.requests.request', side_effect=repondre):
            decocher(admin_client)

        entree = PublicationHub.objects.get()
        assert (entree.origine, entree.resultat, entree.depublies) == ('manuelle', 'retrait', 4)
        publication = rac.etat(actualiser=False)['publications'][0]
        assert publication['resultat'] == 'retrait'

    def test_decocher_sans_raccordement_n_appelle_rien(self, admin_client):
        """Jamais raccordée : rien n'a pu être publié, rien à retirer."""
        SiteConfiguration.objects.create(federation_partage=True)
        with patch('apps.search.raccordement.requests.request') as appel:
            rep = decocher(admin_client)
        assert rep.status_code == 200
        appel.assert_not_called()
        assert not PublicationHub.objects.exists()

    def test_un_autre_reglage_ne_declenche_rien(self, admin_client, raccordee):
        with patch('apps.search.raccordement.requests.request') as appel:
            admin_client.patch('/api/settings/', {'export_color': '#025359'}, format='json')
        appel.assert_not_called()


@pytest.mark.django_db
class TestHubInjoignable:
    """Le consentement retiré est honoré même si le réseau ne suit pas."""

    def _decocher_hub_muet(self, admin_client):
        with patch('apps.search.raccordement.requests.request',
                   side_effect=requests.ConnectionError('non')):
            return decocher(admin_client)

    def test_la_case_reste_decochee(self, admin_client, raccordee):
        rep = self._decocher_hub_muet(admin_client)
        assert rep.status_code == 200
        assert rep.json()['federation_partage'] is False
        assert SiteConfiguration.get_instance().federation_partage is False

    def test_le_retrait_est_mis_en_attente_et_diagnostique(self, admin_client, raccordee):
        self._decocher_hub_muet(admin_client)
        assert RaccordementHub.objects.get().retrait_en_attente is True
        assert rac.etat(actualiser=False)['diagnostic'] == {
            'niveau': 'attention', 'cle': 'retrait_en_attente', 'parametres': {},
        }
        entree = PublicationHub.objects.get()
        assert entree.resultat == 'echec'
        assert entree.message.startswith('Retrait')

    def test_un_hub_qui_refuse_met_aussi_en_attente(self, admin_client, raccordee):
        refus = MagicMock(status_code=503, content=b'x', text='indisponible')
        with patch('apps.search.raccordement.requests.request', return_value=refus):
            decocher(admin_client)
        assert RaccordementHub.objects.get().retrait_en_attente is True

    def test_la_tache_relance_et_leve_le_drapeau(self, admin_client, raccordee):
        self._decocher_hub_muet(admin_client)

        # Toujours injoignable : le drapeau reste, et l'historique n'est pas
        # noyé sous une ligne par heure.
        with patch('apps.search.raccordement.requests.request',
                   side_effect=requests.ConnectionError('non')):
            assert relancer_retrait_hub() == 'en attente : hub_injoignable'
        assert RaccordementHub.objects.get().retrait_en_attente is True
        assert PublicationHub.objects.count() == 1

        repondre, appels = hub_qui_purge(purges=7)
        with patch('apps.search.raccordement.requests.request', side_effect=repondre):
            assert relancer_retrait_hub() == '7 plan(s) retiré(s)'
        assert len(appels) == 2
        assert RaccordementHub.objects.get().retrait_en_attente is False
        derniere = PublicationHub.objects.first()
        assert (derniere.origine, derniere.resultat, derniere.depublies) == ('relance', 'retrait', 7)
        assert rac.etat(actualiser=False)['diagnostic']['cle'] == 'partage_inactif'

    def test_la_tache_ne_fait_rien_sans_retrait_en_attente(self, raccordee):
        with patch('apps.search.raccordement.requests.request') as appel:
            assert relancer_retrait_hub() == 'rien à retirer'
        appel.assert_not_called()

    def test_la_tache_abandonne_si_le_partage_est_recoche(self, raccordee):
        ligne = RaccordementHub.objects.get()
        ligne.retrait_en_attente = True
        ligne.save()
        with patch('apps.search.raccordement.requests.request') as appel:
            assert relancer_retrait_hub() == 'partage réactivé'
        appel.assert_not_called()
        assert RaccordementHub.objects.get().retrait_en_attente is False

    def test_tache_dans_le_planning(self, settings):
        taches = {e['task'] for e in settings.CELERY_BEAT_SCHEDULE.values()}
        assert 'apps.search.tasks.relancer_retrait_hub' in taches


@pytest.mark.django_db
class TestRecocherRepublie:
    def test_recocher_lance_la_publication(
        self, admin_client, raccordee, django_capture_on_commit_callbacks
    ):
        raccordee.federation_partage = False
        raccordee.save()
        with patch('apps.search.tasks.publier_apres_consentement.delay') as publier:
            with django_capture_on_commit_callbacks(execute=True):
                rep = cocher(admin_client)
        assert rep.status_code == 200
        publier.assert_called_once_with()

    def test_recocher_annule_un_retrait_en_attente(
        self, admin_client, raccordee, django_capture_on_commit_callbacks
    ):
        raccordee.federation_partage = False
        raccordee.save()
        ligne = RaccordementHub.objects.get()
        ligne.retrait_en_attente = True
        ligne.save()
        with patch('apps.search.tasks.publier_apres_consentement.delay'):
            with django_capture_on_commit_callbacks(execute=True):
                cocher(admin_client)
        assert RaccordementHub.objects.get().retrait_en_attente is False

    def test_cocher_sans_raccordement_ne_publie_pas(
        self, admin_client, django_capture_on_commit_callbacks
    ):
        SiteConfiguration.objects.create(federation_partage=False)
        with patch('apps.search.tasks.publier_apres_consentement.delay') as publier:
            with django_capture_on_commit_callbacks(execute=True):
                cocher(admin_client)
        publier.assert_not_called()

    def test_broker_indisponible_n_empeche_pas_d_enregistrer(
        self, admin_client, raccordee, django_capture_on_commit_callbacks
    ):
        raccordee.federation_partage = False
        raccordee.save()
        with patch('apps.search.tasks.publier_apres_consentement.delay',
                   side_effect=ConnectionError('redis')):
            with django_capture_on_commit_callbacks(execute=True):
                rep = cocher(admin_client)
        assert rep.status_code == 200
        assert SiteConfiguration.get_instance().federation_partage is True

    def test_la_tache_publie_en_manuelle(self, raccordee, settings):
        """Suite immédiate d'une décision : `CICADA_HUB_PUSH_AUTO` n'y fait rien."""
        settings.CICADA_HUB_PUSH_AUTO = False
        with patch('apps.search.tasks.call_command') as commande:
            publier_apres_consentement()
        assert commande.call_args[0][0] == 'push_federation'
        assert commande.call_args[1]['origine'] == 'manuelle'

    def test_la_tache_relit_le_consentement(self, raccordee):
        raccordee.federation_partage = False
        raccordee.save()
        with patch('apps.search.tasks.call_command') as commande:
            assert publier_apres_consentement() == 'rien à publier'
        commande.assert_not_called()

    def test_diagnostic_apres_recochage_sans_republication(self, raccordee):
        PublicationHub.enregistrer('manuelle', 'reussie', plans=3)
        PublicationHub.enregistrer('manuelle', 'retrait', depublies=3)
        assert rac.etat(actualiser=False)['diagnostic']['cle'] == 'aucune_publication'


@pytest.mark.django_db
class TestAdhesionVautConsentement:
    def _suivi(self, url, headers=None, json=None, timeout=None):
        r = MagicMock(status_code=201)
        r.json.return_value = {'statut': 'en_attente'}
        return r

    def test_demander_l_adhesion_coche_le_partage(self, admin_client):
        SiteConfiguration.objects.create(federation_partage=False)
        with patch('apps.search.raccordement.requests.post', side_effect=self._suivi):
            rep = admin_client.post('/api/federation/raccordement/adhesion/', CONTACT, format='json')
        assert rep.status_code == 200
        assert SiteConfiguration.get_instance().federation_partage is True
        assert rep.json()['configuration']['partage'] is True

    def test_sans_configuration_existante(self, admin_client):
        with patch('apps.search.raccordement.requests.post', side_effect=self._suivi):
            admin_client.post('/api/federation/raccordement/adhesion/', CONTACT, format='json')
        assert SiteConfiguration.get_instance().federation_partage is True

    def test_une_demande_echouee_ne_coche_rien(self, admin_client):
        SiteConfiguration.objects.create(federation_partage=False)
        with patch('apps.search.raccordement.requests.post',
                   side_effect=requests.ConnectionError('non')):
            rep = admin_client.post('/api/federation/raccordement/adhesion/', CONTACT, format='json')
        assert rep.status_code == 400
        assert SiteConfiguration.get_instance().federation_partage is False


@pytest.mark.django_db
class TestCommandeRetrait:
    def test_la_commande_utilise_le_service_et_journalise(self, raccordee):
        repondre, appels = hub_qui_purge(purges=2)
        with patch('apps.search.raccordement.requests.request', side_effect=repondre):
            call_command('retrait_federation', '--confirmer')
        assert [a['url'] for a in appels] == [
            'http://hub/api/federation/lots/', 'http://hub/api/federation/lots/lot-9/bascule/',
        ]
        assert PublicationHub.objects.get().resultat == 'retrait'

    def test_la_commande_satisfait_un_retrait_en_attente(self, raccordee):
        ligne = RaccordementHub.objects.get()
        ligne.retrait_en_attente = True
        ligne.save()
        repondre, _ = hub_qui_purge()
        with patch('apps.search.raccordement.requests.request', side_effect=repondre):
            call_command('retrait_federation', '--confirmer')
        assert RaccordementHub.objects.get().retrait_en_attente is False

    def test_la_commande_echoue_franchement(self, raccordee):
        from django.core.management.base import CommandError

        with patch('apps.search.raccordement.requests.request',
                   side_effect=requests.ConnectionError('non')):
            with pytest.raises(CommandError, match='injoignable'):
                call_command('retrait_federation', '--confirmer')
