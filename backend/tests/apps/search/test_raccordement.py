"""
Raccordement de l'instance au hub par adhésion (#696) et état du raccordement (#698).

Ni le suivi ni le hub ne sont lancés : leurs réponses sont simulées. Ce qui est
vérifié ici est ce que l'instance **décide** et **expose** — la configuration
effective, le chiffrement des jetons, l'historique des publications, le
diagnostic, et surtout qu'aucun jeton ni empreinte ne sorte jamais.
"""

import hashlib
from datetime import datetime, timezone as dt_timezone
import json
import logging
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from apps.core.models import SiteConfiguration
from apps.search import raccordement as rac
from apps.search.indexing import index_plan
from apps.search.models import PublicationHub, RaccordementHub
from apps.search.relay import relais_actif
from apps.search.tasks import actualiser_adhesion_hub, publier_vers_le_hub
from tests.factories import (
    EnjeuFactory, PlanGestionFactory, SiteFactory, SuperAdminFactory, UserFactory,
)

URL_RACCORDEMENT = '/api/federation/raccordement/'
JETON_SUIVI = '123e4567-e89b-12d3-a456-426614174000'
CONTACT = {
    'contact_nom': 'Camille Martin', 'contact_email': 'camille@cen.example',
    'contact_telephone': '04 00 00 00 00', 'message': 'Bonjour',
}


@pytest.fixture(autouse=True)
def configuration_vierge(db, settings, monkeypatch):
    """
    Une instance identifiée, sans aucun jeton d'environnement.

    L'environnement de développement porte de vrais jetons du banc : sans ce
    décor, la résolution « environnement d'abord » masquerait tout ce que ces
    tests vérifient de l'adhésion.
    """
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
def partage(db):
    return SiteConfiguration.objects.create(federation_partage=True)


@pytest.fixture
def admin_client():
    client = APIClient()
    client.force_authenticate(user=SuperAdminFactory())
    return client


def reponse(status_code=200, corps=None):
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = corps if corps is not None else {}
    r.content = json.dumps(corps or {}).encode()
    r.text = json.dumps(corps or {})
    return r


def adhesion_acceptee(hub='http://hub'):
    ligne = RaccordementHub(
        jeton_depot_chiffre=rac.chiffrer('depot-secret'),
        jeton_lecture_chiffre=rac.chiffrer('lecture-secret'),
        adhesion_statut=RaccordementHub.STATUT_ACCEPTEE,
        adhesion_instance_id='cen-aura', hub_url=hub,
    )
    ligne.save()
    return ligne


# --------------------------------------------------------------------------- #

class TestFormules:
    """Le hub ne stocke que l'empreinte : la formule est un contrat, figé ici."""

    def test_empreinte_est_le_sha256_hexadecimal(self):
        assert rac.empreinte('abc') == hashlib.sha256(b'abc').hexdigest()

    def test_jeton_tire_assez_long(self):
        assert len(rac.nouveau_jeton()) >= 64


@pytest.mark.django_db
class TestChiffrement:
    def test_aller_retour(self):
        assert rac.dechiffrer(rac.chiffrer('secret')) == 'secret'

    def test_le_jeton_n_est_pas_stocke_en_clair(self):
        assert 'secret' not in rac.chiffrer('secret')

    def test_secret_key_changee_jeton_absent_sans_exception(self, settings):
        adhesion_acceptee()
        settings.SECRET_KEY = 'une-autre-cle'
        assert rac.jeton_depot() is None
        assert rac.jeton_lecture() is None

    def test_secret_key_changee_diagnostiquee(self, settings, partage):
        adhesion_acceptee()
        settings.SECRET_KEY = 'une-autre-cle'
        diag = rac.etat()['diagnostic']
        assert diag['cle'] == 'jeton_depot_absent'
        assert diag['parametres'] == {'cause': 'dechiffrement'}


@pytest.mark.django_db
class TestResolution:
    def test_rien_de_configure(self):
        assert rac.hub_url() == ''
        assert rac.jeton_depot() is None
        assert rac.source_jetons() is None

    def test_environnement_d_abord(self, settings):
        adhesion_acceptee(hub='http://hub-adhesion')
        settings.CICADA_HUB_URL = 'http://hub-env/'
        settings.CICADA_HUB_PUSH_TOKEN = 'depot-env'
        assert rac.hub_url() == 'http://hub-env'
        assert rac.jeton_depot() == 'depot-env'
        assert rac.jeton_lecture() == 'lecture-secret'
        assert rac.source_jetons() == 'environnement'

    def test_adhesion_acceptee(self):
        adhesion_acceptee()
        assert rac.hub_url() == 'http://hub'
        assert rac.jeton_depot() == 'depot-secret'
        assert rac.jeton_lecture() == 'lecture-secret'
        assert rac.source_jetons() == 'adhesion'

    @pytest.mark.parametrize('statut', ['en_attente', 'refusee'])
    def test_adhesion_non_acceptee_ne_fournit_aucun_jeton(self, statut):
        ligne = adhesion_acceptee()
        ligne.adhesion_statut = statut
        ligne.save()
        assert rac.jeton_depot() is None
        assert rac.jeton_lecture() is None
        assert rac.source_jetons() is None

    def test_relais_exige_un_jeton_de_lecture(self, settings, partage):
        settings.CICADA_EXPLORATION_SOURCE = 'hub'
        settings.CICADA_HUB_URL = 'http://hub'
        assert relais_actif() is False
        adhesion_acceptee()
        assert relais_actif() is True

    def test_le_relais_utilise_le_jeton_de_l_adhesion(self, settings, partage):
        settings.CICADA_EXPLORATION_SOURCE = 'hub'
        adhesion_acceptee()
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        with patch('apps.search.relay.requests.get', return_value=reponse(200, {'results': []})) as appel:
            client.get('/api/exploration/contenus/')
        assert appel.call_args[0][0] == 'http://hub/api/exploration/contenus/'
        assert appel.call_args[1]['headers'] == {'X-Hub-Token': 'lecture-secret'}

    @pytest.mark.parametrize('identifiant,libelle,valide', [
        ('cen-aura', 'CEN', True),
        ('local', 'CEN', False),
        ('', 'CEN', False),
        ('CEN AURA', 'CEN', False),
        ('cen-aura', '  ', False),
    ])
    def test_identite(self, settings, identifiant, libelle, valide):
        settings.CICADA_INSTANCE_ID = identifiant
        settings.CICADA_INSTANCE_LABEL = libelle
        assert rac.identite_valide() is valide


# --------------------------------------------------------------------------- #

@pytest.mark.django_db
class TestPermissions:
    @pytest.mark.parametrize('methode,chemin', [
        ('get', ''), ('post', 'verifier/'), ('post', 'adhesion/'),
        ('post', 'confirmation/'), ('post', 'contact/'),
    ])
    def test_anonyme_refuse(self, methode, chemin):
        assert getattr(APIClient(), methode)(URL_RACCORDEMENT + chemin).status_code == 401

    @pytest.mark.parametrize('methode,chemin', [
        ('get', ''), ('post', 'verifier/'), ('post', 'adhesion/'),
        ('post', 'confirmation/'), ('post', 'contact/'),
    ])
    def test_utilisateur_ordinaire_refuse(self, methode, chemin):
        client = APIClient()
        client.force_authenticate(user=UserFactory())
        assert getattr(client, methode)(URL_RACCORDEMENT + chemin).status_code == 403


def suivi_qui_accepte():
    """Simule `POST /instances/adhesion-hub/` : le suivi enregistre la demande."""
    recu = {}

    def poster(url, headers=None, json=None, timeout=None):
        recu.update(url=url, headers=headers, corps=json)
        return reponse(201, {'statut': 'en_attente', 'demandee_le': 'x'})

    return poster, recu


@pytest.mark.django_db
class TestDemandeAdhesion:
    def test_etat_initial(self, admin_client):
        corps = admin_client.get(URL_RACCORDEMENT).json()
        assert set(corps) == {'configuration', 'adhesion', 'publications', 'diagnostic'}
        assert set(corps['configuration']) == {
            'instance_id', 'instance_libelle', 'identite_valide', 'hub_url',
            'source_jetons', 'jeton_depot_defini', 'jeton_lecture_defini',
            'exploration_source', 'relais_actif', 'publication_auto', 'partage',
            'suivi_disponible',
        }
        assert set(corps['adhesion']) == {
            'statut', 'demandee_le', 'motif', 'possible', 'erreur_suivi',
            'code_expire_le', 'contact_email',
        }
        assert corps['adhesion']['possible'] is True
        assert corps['adhesion']['statut'] == ''
        assert corps['diagnostic'] == {'niveau': 'info', 'cle': 'non_raccorde', 'parametres': {}}

    def test_demande_reussie(self, admin_client):
        poster, recu = suivi_qui_accepte()
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_RACCORDEMENT + 'adhesion/', CONTACT, format='json')
        assert rep.status_code == 200
        corps = rep.json()
        assert corps['adhesion']['statut'] == 'en_attente'
        assert corps['adhesion']['possible'] is False
        assert corps['diagnostic']['cle'] == 'adhesion_en_attente'
        assert corps['diagnostic']['parametres'] == {}

        assert recu['url'] == 'http://suivi/api/instances/adhesion-hub/'
        assert recu['headers'] == {'X-Instance-Token': JETON_SUIVI}
        assert recu['corps']['instance_id'] == 'cen-aura'
        assert recu['corps']['libelle'] == 'CEN Auvergne-Rhône-Alpes'
        for champ, valeur in CONTACT.items():
            assert recu['corps'][champ] == valeur
        assert corps['adhesion']['contact_email'] == 'camille@cen.example'

        ligne = RaccordementHub.objects.get()
        depot = rac.dechiffrer(ligne.jeton_depot_chiffre)
        lecture = rac.dechiffrer(ligne.jeton_lecture_chiffre)
        # Seules les empreintes ont voyagé.
        assert recu['corps']['empreinte_depot'] == rac.empreinte(depot)
        assert recu['corps']['empreinte_lecture'] == rac.empreinte(lecture)
        assert depot not in json.dumps(recu['corps'])
        assert ligne.adhesion_instance_id == 'cen-aura'

    def test_redemande_apres_refus(self, admin_client):
        ligne = adhesion_acceptee()
        ligne.adhesion_statut = 'refusee'
        ligne.adhesion_motif = 'Inconnu'
        ligne.save()
        poster, _ = suivi_qui_accepte()
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_RACCORDEMENT + 'adhesion/', CONTACT, format='json')
        assert rep.status_code == 200
        ligne.refresh_from_db()
        assert ligne.adhesion_statut == 'en_attente'
        assert ligne.adhesion_motif == ''
        assert rac.dechiffrer(ligne.jeton_depot_chiffre) != 'depot-secret'

    def test_deja_acceptee(self, admin_client):
        adhesion_acceptee()
        with patch('apps.search.raccordement.requests.post') as appel:
            rep = admin_client.post(URL_RACCORDEMENT + 'adhesion/', CONTACT, format='json')
        assert rep.status_code == 409
        assert rep.json()['erreur'] == 'deja_acceptee'
        appel.assert_not_called()

    def test_jetons_d_environnement(self, admin_client, settings):
        settings.CICADA_HUB_PUSH_TOKEN = 'depot-env'
        rep = admin_client.post(URL_RACCORDEMENT + 'adhesion/', CONTACT, format='json')
        assert rep.status_code == 409
        assert rep.json()['erreur'] == 'jetons_environnement'

    def test_identite_locale_refusee(self, admin_client, settings):
        settings.CICADA_INSTANCE_ID = 'local'
        rep = admin_client.post(URL_RACCORDEMENT + 'adhesion/', CONTACT, format='json')
        assert rep.status_code == 400
        assert rep.json()['erreur'] == 'identite_manquante'
        assert 'rebuild_search_index' in rep.json()['detail']

    def test_sans_jeton_de_suivi(self, admin_client, monkeypatch):
        monkeypatch.delenv('CICADA_TRACKING_TOKEN')
        with patch('apps.system.tracking.TOKEN_FILE') as fichier:
            fichier.read_text.side_effect = FileNotFoundError
            rep = admin_client.post(URL_RACCORDEMENT + 'adhesion/', CONTACT, format='json')
            etat = admin_client.get(URL_RACCORDEMENT).json()
        assert rep.status_code == 400
        assert rep.json()['erreur'] == 'jeton_suivi_absent'
        assert etat['configuration']['suivi_disponible'] is False
        assert etat['adhesion']['possible'] is False

    def test_suivi_injoignable(self, admin_client):
        import requests

        with patch('apps.search.raccordement.requests.post',
                   side_effect=requests.ConnectionError('non')):
            rep = admin_client.post(URL_RACCORDEMENT + 'adhesion/', CONTACT, format='json')
        assert rep.status_code == 400
        assert rep.json()['erreur'] == 'suivi_indisponible'


@pytest.mark.django_db
class TestActualisation:
    def _en_attente(self):
        ligne = adhesion_acceptee(hub='')
        ligne.adhesion_statut = 'en_attente'
        ligne.save()
        return ligne

    def test_acceptation_lue_a_l_affichage(self, admin_client, partage):
        self._en_attente()
        suivi = reponse(200, {
            'statut': 'acceptee', 'instance_id': 'cen-aura',
            'hub_url': 'https://hub.rnf/', 'motif_refus': '',
        })
        with patch('apps.search.raccordement.requests.get', return_value=suivi) as appel:
            corps = admin_client.get(URL_RACCORDEMENT).json()
        assert appel.call_args[0][0] == 'http://suivi/api/instances/adhesion-hub/'
        assert appel.call_args[1]['timeout'] == 5
        assert corps['adhesion']['statut'] == 'acceptee'
        assert corps['configuration']['hub_url'] == 'https://hub.rnf'
        assert corps['configuration']['source_jetons'] == 'adhesion'
        assert corps['configuration']['jeton_depot_defini'] is True
        assert corps['diagnostic']['cle'] == 'aucune_publication'

    def test_refus_lu_avec_motif(self, admin_client):
        self._en_attente()
        suivi = reponse(200, {'statut': 'refusee', 'motif_refus': 'Structure inconnue'})
        with patch('apps.search.raccordement.requests.get', return_value=suivi):
            corps = admin_client.get(URL_RACCORDEMENT).json()
        assert corps['adhesion']['statut'] == 'refusee'
        assert corps['adhesion']['motif'] == 'Structure inconnue'
        assert corps['adhesion']['possible'] is True
        assert corps['diagnostic'] == {
            'niveau': 'erreur', 'cle': 'adhesion_refusee',
            'parametres': {'motif': 'Structure inconnue'},
        }

    def test_suivi_injoignable_tolere_et_signale(self, admin_client):
        import requests

        self._en_attente()
        with patch('apps.search.raccordement.requests.get',
                   side_effect=requests.Timeout('lent')):
            rep = admin_client.get(URL_RACCORDEMENT)
        assert rep.status_code == 200
        assert rep.json()['adhesion']['erreur_suivi'] == 'suivi_indisponible'
        assert rep.json()['adhesion']['statut'] == 'en_attente'

    def test_hors_attente_aucun_appel(self, admin_client):
        with patch('apps.search.raccordement.requests.get') as appel:
            admin_client.get(URL_RACCORDEMENT)
            assert actualiser_adhesion_hub() == 'rien à actualiser'
        appel.assert_not_called()

    def test_tache_planifiee(self):
        self._en_attente()
        suivi = reponse(200, {'statut': 'acceptee', 'hub_url': 'https://hub.rnf'})
        with patch('apps.search.raccordement.requests.get', return_value=suivi):
            assert actualiser_adhesion_hub() == 'acceptee'
        assert RaccordementHub.objects.get().hub_url == 'https://hub.rnf'

    def test_tache_dans_le_planning(self, settings):
        taches = {e['task'] for e in settings.CELERY_BEAT_SCHEDULE.values()}
        assert 'apps.search.tasks.actualiser_adhesion_hub' in taches


@pytest.mark.django_db
class TestVerifier:
    def _hub(self, instances_status=200, instances=None):
        def get(url, headers=None, timeout=None):
            assert timeout == 5
            if url.endswith('/api/health/'):
                return reponse(200, {'status': 'ok'})
            return reponse(instances_status, {'instances': instances or []})
        return get

    def test_instance_reconnue(self, admin_client):
        adhesion_acceptee()
        hub = self._hub(instances=[
            {'instance_id': 'autre', 'active': True},
            {'instance_id': 'cen-aura', 'active': True, 'derniere_publication': '2026-10-07T02:30:00Z',
             'plans_publies': 12, 'contenus_publies': 340},
        ])
        with patch('apps.search.raccordement.requests.get', side_effect=hub):
            corps = admin_client.post(URL_RACCORDEMENT + 'verifier/').json()
        assert corps == {
            'hub_joignable': True, 'instance_reconnue': True, 'active': True,
            'derniere_publication': '2026-10-07T02:30:00Z', 'plans': 12,
            'contenus': 340, 'erreur': None,
        }

    def test_jeton_refuse(self, admin_client):
        adhesion_acceptee()
        with patch('apps.search.raccordement.requests.get', side_effect=self._hub(403)):
            corps = admin_client.post(URL_RACCORDEMENT + 'verifier/').json()
        assert corps['instance_reconnue'] is False
        assert corps['erreur'] == 'jeton_refuse'

    def test_hub_injoignable(self, admin_client):
        import requests

        adhesion_acceptee()
        with patch('apps.search.raccordement.requests.get',
                   side_effect=requests.ConnectionError('non')):
            corps = admin_client.post(URL_RACCORDEMENT + 'verifier/').json()
        assert corps['hub_joignable'] is False
        assert corps['erreur'] == 'hub_injoignable'

    def test_sans_jeton_rien_a_verifier(self, admin_client, settings):
        settings.CICADA_HUB_URL = 'http://hub'
        with patch('apps.search.raccordement.requests.get', side_effect=self._hub()) as appel:
            corps = admin_client.post(URL_RACCORDEMENT + 'verifier/').json()
        assert corps['hub_joignable'] is True
        assert corps['instance_reconnue'] is None
        assert corps['erreur'] is None
        assert appel.call_count == 1


# --------------------------------------------------------------------------- #

@pytest.fixture
def plan_indexe(db):
    site = SiteFactory(nom_site='Camargue', id_inpn='FR3600001')
    plan = PlanGestionFactory(statut='valide', nom='Plan', sites=[site])
    EnjeuFactory(id_pg=plan, libelle='Forêt alluviale')
    index_plan(plan)
    return plan


def hub_de_depot(echec=False):
    def repondre(methode, url, **kwargs):
        r = type('R', (), {})()
        r.content = b'{}'
        r.text = 'boom'
        if url.endswith('/lots/'):
            r.status_code, corps = 201, {'lot_id': 'lot-1'}
        elif url.endswith('/plans/'):
            r.status_code, corps = (500 if echec else 200), {'plans_recus': 1, 'contenus_recus': 3}
        elif url.endswith('/bascule/'):
            r.status_code, corps = 200, {'plans_recus': 1, 'contenus_recus': 3, 'plans_purges': 2}
        else:
            r.status_code, corps = 204, {}
        r.json = lambda: corps
        return r
    return repondre


@pytest.mark.django_db
class TestHistorique:
    def test_publication_reussie_par_l_adhesion(self, partage, plan_indexe):
        adhesion_acceptee()
        with patch('requests.request', side_effect=hub_de_depot()) as appel:
            call_command('push_federation')
        assert appel.call_args_list[0][1]['headers']['X-Federation-Token'] == 'depot-secret'
        entree = PublicationHub.objects.get()
        assert (entree.origine, entree.resultat) == ('manuelle', 'reussie')
        assert (entree.plans, entree.documents, entree.depublies) == (1, 3, 2)

    def test_echec_consigne(self, partage, plan_indexe):
        adhesion_acceptee()
        with patch('requests.request', side_effect=hub_de_depot(echec=True)):
            with pytest.raises(CommandError):
                call_command('push_federation', origine='nuit')
        entree = PublicationHub.objects.get()
        assert (entree.origine, entree.resultat) == ('nuit', 'echec')
        assert 'Dépôt interrompu' in entree.message

    def test_rien_a_publier_ignoree(self, partage):
        adhesion_acceptee()
        with patch('requests.request') as appel:
            call_command('push_federation')
        appel.assert_not_called()
        assert PublicationHub.objects.get().resultat == 'ignoree'

    def test_dry_run_n_enregistre_rien(self, partage, plan_indexe):
        call_command('push_federation', '--dry-run')
        assert not PublicationHub.objects.exists()

    def test_tache_non_configuree_ignoree(self):
        assert publier_vers_le_hub() == 'non configurée'
        entree = PublicationHub.objects.get()
        assert (entree.origine, entree.resultat) == ('nuit', 'ignoree')

    def test_tache_partage_desactive_ignoree(self):
        adhesion_acceptee()
        assert publier_vers_le_hub() == 'partage désactivé'
        assert PublicationHub.objects.get().resultat == 'ignoree'

    def test_tache_passe_l_origine_nuit(self, partage):
        adhesion_acceptee()
        with patch('apps.search.tasks.call_command') as commande:
            publier_vers_le_hub()
        assert commande.call_args[1]['origine'] == 'nuit'

    def test_conservation_bornee(self):
        for _ in range(PublicationHub.CONSERVATION + 5):
            PublicationHub.enregistrer('nuit', 'ignoree')
        assert PublicationHub.objects.count() == PublicationHub.CONSERVATION

    def test_message_tronque(self):
        assert len(PublicationHub.enregistrer('nuit', 'echec', message='x' * 900).message) == 500


@pytest.mark.django_db
class TestDiagnostic:
    def _cle(self):
        return rac.etat(actualiser=False)['diagnostic']

    def test_identite_manquante_prime(self, settings):
        settings.CICADA_INSTANCE_ID = 'local'
        adhesion_acceptee()
        assert self._cle()['cle'] == 'identite_manquante'
        assert self._cle()['niveau'] == 'erreur'

    def test_jeton_depot_absent(self, settings):
        settings.CICADA_HUB_READ_TOKEN = 'lecture-env'
        assert self._cle() == {
            'niveau': 'attention', 'cle': 'jeton_depot_absent', 'parametres': {'cause': 'absent'},
        }

    def test_partage_inactif(self):
        adhesion_acceptee()
        assert self._cle()['cle'] == 'partage_inactif'

    def test_derniere_publication_echec(self, partage):
        adhesion_acceptee()
        PublicationHub.enregistrer('nuit', 'reussie', plans=3)
        PublicationHub.enregistrer('nuit', 'echec', message='Hub muet')
        PublicationHub.enregistrer('nuit', 'ignoree')
        assert self._cle() == {
            'niveau': 'erreur', 'cle': 'derniere_publication_echec',
            'parametres': {'message': 'Hub muet'},
        }

    def test_ok(self, partage):
        adhesion_acceptee()
        PublicationHub.enregistrer('nuit', 'echec', message='Hub muet')
        PublicationHub.enregistrer('manuelle', 'reussie', plans=3)
        assert self._cle() == {'niveau': 'ok', 'cle': 'ok', 'parametres': {}}

    def test_publications_exposees(self, partage):
        PublicationHub.enregistrer('nuit', 'reussie', plans=12, documents=340)
        publication, = rac.etat(actualiser=False)['publications']
        assert set(publication) == {
            'date', 'origine', 'resultat', 'plans', 'documents', 'depublies', 'message',
        }
        assert publication['plans'] == 12


@pytest.mark.django_db
class TestAucuneFuite:
    """Jamais de jeton ni d'empreinte dans une réponse d'API ou un journal."""

    def test_ni_reponse_ni_journal(self, admin_client, partage, caplog):
        caplog.set_level(logging.DEBUG)
        poster, recu = suivi_qui_accepte()
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            reponses = [admin_client.post(URL_RACCORDEMENT + 'adhesion/', CONTACT, format='json').content]

        ligne = RaccordementHub.objects.get()
        depot = rac.dechiffrer(ligne.jeton_depot_chiffre)
        lecture = rac.dechiffrer(ligne.jeton_lecture_chiffre)

        suivi = reponse(200, {'statut': 'acceptee', 'hub_url': 'http://hub'})
        hub = TestVerifier()._hub(instances=[{'instance_id': 'cen-aura', 'active': True}])
        with patch('apps.search.raccordement.requests.get', side_effect=[suivi]):
            reponses.append(admin_client.get(URL_RACCORDEMENT).content)
        with patch('apps.search.raccordement.requests.get', side_effect=hub):
            reponses.append(admin_client.post(URL_RACCORDEMENT + 'verifier/').content)

        secrets_ = [
            depot, lecture, rac.empreinte(depot), rac.empreinte(lecture), JETON_SUIVI,
            ligne.jeton_depot_chiffre, ligne.jeton_lecture_chiffre,
        ]
        texte = b''.join(reponses).decode() + caplog.text
        for secret in secrets_:
            assert secret not in texte


# --------------------------------------------------------------------------- #
# V2 — confirmation par code envoyé par e-mail
# --------------------------------------------------------------------------- #

URL_CONFIRMATION = URL_RACCORDEMENT + 'confirmation/'
URL_CONTACT = URL_RACCORDEMENT + 'contact/'
CODE = 'K7FM-29QA'


def adhesion_code_envoye():
    ligne = adhesion_acceptee(hub='')
    ligne.adhesion_statut = RaccordementHub.STATUT_CODE_ENVOYE
    ligne.adhesion_contact_email = 'camille@cen.example'
    ligne.save()
    return ligne


@pytest.mark.django_db
class TestContactDeLaDemande:
    @pytest.mark.parametrize('modif', [
        {'contact_nom': ''}, {'contact_nom': '   '}, {'contact_email': ''},
        {'contact_email': 'pas-une-adresse'}, {'contact_nom': None},
        {'contact_email': 42}, {'message': 'x' * 5001},
    ])
    def test_contact_invalide(self, admin_client, modif):
        with patch('apps.search.raccordement.requests.post') as appel:
            rep = admin_client.post(
                URL_RACCORDEMENT + 'adhesion/', {**CONTACT, **modif}, format='json',
            )
        assert rep.status_code == 400
        assert rep.json()['erreur'] == 'contact_invalide'
        appel.assert_not_called()
        assert not RaccordementHub.objects.exists()

    def test_sans_corps(self, admin_client):
        rep = admin_client.post(URL_RACCORDEMENT + 'adhesion/')
        assert rep.json()['erreur'] == 'contact_invalide'

    def test_telephone_et_message_facultatifs(self, admin_client):
        poster, recu = suivi_qui_accepte()
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(
                URL_RACCORDEMENT + 'adhesion/',
                {'contact_nom': 'Camille', 'contact_email': 'c@cen.example'}, format='json',
            )
        assert rep.status_code == 200
        assert recu['corps']['contact_telephone'] == ''
        ligne = RaccordementHub.objects.get()
        assert (ligne.adhesion_contact_nom, ligne.adhesion_contact_email) == ('Camille', 'c@cen.example')

    def test_redemande_possible_pendant_code_envoye(self, admin_client):
        adhesion_code_envoye()
        poster, _ = suivi_qui_accepte()
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_RACCORDEMENT + 'adhesion/', CONTACT, format='json')
        assert rep.status_code == 200
        assert rep.json()['adhesion']['statut'] == 'en_attente'


def suivi_confirmation(status_code, corps):
    recu = {}

    def poster(url, headers=None, json=None, timeout=None):
        recu.update(url=url, headers=headers, corps=json, timeout=timeout)
        return reponse(status_code, corps)

    return poster, recu


@pytest.mark.django_db
class TestConfirmation:
    def test_code_juste_adhesion_acceptee(self, admin_client, partage):
        adhesion_code_envoye()
        poster, recu = suivi_confirmation(200, {'statut': 'acceptee', 'hub_url': 'https://hub.rnf/'})
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_CONFIRMATION, {'code': f' {CODE} '}, format='json')
        assert rep.status_code == 200
        assert recu['url'] == 'http://suivi/api/instances/adhesion-hub/confirmation/'
        assert recu['headers'] == {'X-Instance-Token': JETON_SUIVI}
        assert recu['corps'] == {'code': CODE}
        assert recu['timeout'] == 5
        corps = rep.json()
        assert corps['adhesion']['statut'] == 'acceptee'
        assert corps['configuration']['hub_url'] == 'https://hub.rnf'
        assert corps['configuration']['source_jetons'] == 'adhesion'
        assert corps['diagnostic']['cle'] == 'aucune_publication'
        ligne = RaccordementHub.objects.get()
        assert ligne.adhesion_statut == 'acceptee'
        assert rac.jeton_depot() == 'depot-secret'

    def test_code_invalide_relaye_avec_essais_restants(self, admin_client):
        adhesion_code_envoye()
        poster, _ = suivi_confirmation(400, {'erreur': 'code_invalide', 'essais_restants': 3})
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_CONFIRMATION, {'code': 'FAUX-CODE'}, format='json')
        assert rep.status_code == 400
        assert rep.json()['erreur'] == 'code_invalide'
        assert rep.json()['essais_restants'] == 3
        assert RaccordementHub.objects.get().adhesion_statut == 'code_envoye'

    @pytest.mark.parametrize('status_code,cle', [
        (400, 'code_expire'), (409, 'pas_de_code'), (502, 'hub_injoignable'),
    ])
    def test_erreurs_relayees(self, admin_client, status_code, cle):
        adhesion_code_envoye()
        poster, _ = suivi_confirmation(status_code, {'erreur': cle})
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_CONFIRMATION, {'code': CODE}, format='json')
        assert rep.status_code == status_code
        assert rep.json()['erreur'] == cle
        assert 'essais_restants' not in rep.json()
        assert RaccordementHub.objects.get().adhesion_statut == 'code_envoye'

    def test_trop_d_essais_repasse_en_attente(self, admin_client):
        adhesion_code_envoye()
        poster, _ = suivi_confirmation(400, {'erreur': 'trop_d_essais'})
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_CONFIRMATION, {'code': CODE}, format='json')
        assert rep.status_code == 400
        assert rep.json()['erreur'] == 'trop_d_essais'
        assert RaccordementHub.objects.get().adhesion_statut == 'en_attente'

    def test_demande_inconnue_du_suivi(self, admin_client):
        adhesion_code_envoye()
        poster, _ = suivi_confirmation(404, {'detail': 'Not found.'})
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_CONFIRMATION, {'code': CODE}, format='json')
        assert (rep.status_code, rep.json()['erreur']) == (409, 'pas_de_code')

    def test_reponse_inattendue_du_suivi(self, admin_client):
        adhesion_code_envoye()
        poster, _ = suivi_confirmation(500, {'erreur': 'autre_chose'})
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_CONFIRMATION, {'code': CODE}, format='json')
        assert rep.json()['erreur'] == 'suivi_indisponible'

    def test_suivi_injoignable(self, admin_client):
        import requests

        adhesion_code_envoye()
        with patch('apps.search.raccordement.requests.post',
                   side_effect=requests.ConnectionError('non')):
            rep = admin_client.post(URL_CONFIRMATION, {'code': CODE}, format='json')
        assert rep.json()['erreur'] == 'suivi_indisponible'

    def test_sans_jeton_de_suivi(self, admin_client, monkeypatch):
        adhesion_code_envoye()
        monkeypatch.delenv('CICADA_TRACKING_TOKEN')
        with patch('apps.system.tracking.TOKEN_FILE') as fichier:
            fichier.read_text.side_effect = FileNotFoundError
            rep = admin_client.post(URL_CONFIRMATION, {'code': CODE}, format='json')
        assert rep.json()['erreur'] == 'jeton_suivi_absent'

    @pytest.mark.parametrize('corps', [{}, {'code': ''}, {'code': '   '}, {'code': 12}])
    def test_code_vide_non_transmis(self, admin_client, corps):
        adhesion_code_envoye()
        with patch('apps.search.raccordement.requests.post') as appel:
            rep = admin_client.post(URL_CONFIRMATION, corps, format='json')
        assert (rep.status_code, rep.json()['erreur']) == (400, 'code_invalide')
        appel.assert_not_called()

    @pytest.mark.parametrize('statut,cle', [('', 'pas_de_code'), ('refusee', 'pas_de_code'),
                                            ('acceptee', 'deja_acceptee')])
    def test_hors_demande_en_cours(self, admin_client, statut, cle):
        ligne = adhesion_acceptee()
        ligne.adhesion_statut = statut
        ligne.save()
        with patch('apps.search.raccordement.requests.post') as appel:
            rep = admin_client.post(URL_CONFIRMATION, {'code': CODE}, format='json')
        assert (rep.status_code, rep.json()['erreur']) == (409, cle)
        appel.assert_not_called()

    def test_en_attente_locale_relayee(self, admin_client):
        """Statut local périmé : le code a pu arriver avant l'actualisation."""
        ligne = adhesion_code_envoye()
        ligne.adhesion_statut = 'en_attente'
        ligne.save()
        poster, _ = suivi_confirmation(200, {'statut': 'acceptee', 'hub_url': 'http://hub'})
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_CONFIRMATION, {'code': CODE}, format='json')
        assert rep.json()['adhesion']['statut'] == 'acceptee'


@pytest.mark.django_db
class TestContactRnf:
    def test_message_envoye_au_nom_du_compte_connecte(self):
        admin = SuperAdminFactory(prenom_role='Camille', nom_role='Martin', email='camille@cen.example')
        client = APIClient()
        client.force_authenticate(user=admin)
        poster, recu = suivi_confirmation(202, {})
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = client.post(URL_CONTACT, {
                'sujet': 'Question', 'message': 'Bonjour RNF',
                # Ignorés : l'expéditeur est le compte connecté.
                'nom': 'Usurpateur', 'email': 'pirate@example.com',
            }, format='json')
        assert rep.status_code == 202
        assert recu['url'] == 'http://suivi/api/instances/contact/'
        assert recu['headers'] == {'X-Instance-Token': JETON_SUIVI}
        assert recu['corps'] == {
            'nom': 'Camille Martin', 'email': 'camille@cen.example',
            'sujet': 'Question', 'message': 'Bonjour RNF',
        }

    @pytest.mark.parametrize('corps', [
        {}, {'sujet': 'Q'}, {'message': 'M'}, {'sujet': ' ', 'message': 'M'},
    ])
    def test_sujet_et_message_requis(self, admin_client, corps):
        with patch('apps.search.raccordement.requests.post') as appel:
            rep = admin_client.post(URL_CONTACT, corps, format='json')
        assert (rep.status_code, rep.json()['erreur']) == (400, 'contact_invalide')
        appel.assert_not_called()

    @pytest.mark.parametrize('status_code,corps', [
        (500, {}), (502, {'erreur': 'envoi_impossible'}),
    ])
    def test_suivi_en_echec(self, admin_client, status_code, corps):
        poster, _ = suivi_confirmation(status_code, corps)
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_CONTACT, {'sujet': 'Q', 'message': 'M'}, format='json')
        assert rep.status_code == 400
        assert rep.json()['erreur'] == 'suivi_indisponible'

    def test_sans_jeton_de_suivi(self, admin_client, monkeypatch):
        monkeypatch.delenv('CICADA_TRACKING_TOKEN')
        with patch('apps.system.tracking.TOKEN_FILE') as fichier:
            fichier.read_text.side_effect = FileNotFoundError
            rep = admin_client.post(URL_CONTACT, {'sujet': 'Q', 'message': 'M'}, format='json')
        assert rep.json()['erreur'] == 'jeton_suivi_absent'


@pytest.mark.django_db
class TestCodeEnvoye:
    def test_actualisation_lit_le_code_envoye(self, admin_client):
        ligne = adhesion_acceptee(hub='')
        ligne.adhesion_statut = 'en_attente'
        ligne.save()
        suivi = reponse(200, {'statut': 'code_envoye', 'code_expire_le': '2026-10-14T12:00:00Z'})
        with patch('apps.search.raccordement.requests.get', return_value=suivi):
            corps = admin_client.get(URL_RACCORDEMENT).json()
        assert corps['adhesion']['statut'] == 'code_envoye'
        expire = datetime.fromisoformat(corps['adhesion']['code_expire_le'])
        assert expire == datetime(2026, 10, 14, 12, tzinfo=dt_timezone.utc)
        assert corps['adhesion']['possible'] is False
        assert corps['diagnostic'] == {
            'niveau': 'info', 'cle': 'adhesion_code_envoye',
            'parametres': {'expire_le': corps['adhesion']['code_expire_le']},
        }

    def test_code_envoye_actualise_par_la_tache(self):
        adhesion_code_envoye()
        suivi = reponse(200, {'statut': 'acceptee', 'hub_url': 'https://hub.rnf'})
        with patch('apps.search.raccordement.requests.get', return_value=suivi):
            assert actualiser_adhesion_hub() == 'acceptee'
        ligne = RaccordementHub.objects.get()
        assert ligne.hub_url == 'https://hub.rnf'
        assert ligne.adhesion_code_expire_le is None

    def test_refus_prime_sur_le_code(self):
        ligne = adhesion_code_envoye()
        ligne.adhesion_statut = 'refusee'
        ligne.save()
        assert rac.etat(actualiser=False)['diagnostic']['cle'] == 'adhesion_refusee'


@pytest.mark.django_db
class TestLeCodeNeFuitPas:
    """Le code ne transite que dans la requête de confirmation."""

    @pytest.mark.parametrize('status_code,corps', [
        (200, {'statut': 'acceptee', 'hub_url': 'http://hub'}),
        (400, {'erreur': 'code_invalide', 'essais_restants': 2}),
        (500, {}),
    ])
    def test_ni_base_ni_reponse_ni_journal(self, admin_client, caplog, status_code, corps):
        caplog.set_level(logging.DEBUG)
        adhesion_code_envoye()
        code = 'ZQ7W-XK3P'
        poster, _ = suivi_confirmation(status_code, corps)
        with patch('apps.search.raccordement.requests.post', side_effect=poster):
            rep = admin_client.post(URL_CONFIRMATION, {'code': code}, format='json')
        with patch('apps.search.raccordement.requests.get', return_value=reponse(200, corps or {})):
            etat = admin_client.get(URL_RACCORDEMENT)
        ligne = RaccordementHub.objects.get()
        stocke = json.dumps({f.name: str(getattr(ligne, f.name)) for f in ligne._meta.fields})
        texte = rep.content.decode() + etat.content.decode() + caplog.text + stocke
        for forme in (code, code.replace('-', ''), code.lower(),
                      hashlib.sha256(code.replace('-', '').encode()).hexdigest()):
            assert forme not in texte
