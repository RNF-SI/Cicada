"""Contrat entre l'API de suivi et le paquet cicada (installateur, heartbeat).

Les appels reproduisent exactement ceux de
packaging/debian/usr/share/cicada/install/install_service.py (register) et
packaging/debian/usr/bin/cicada-heartbeat (heartbeat).
"""
import uuid
from unittest import mock

import requests
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from rest_framework.test import APIClient

from . import views
from .adhesion import code_verification, empreinte
from .admin import AdhesionHubAdmin
from .models import AdhesionHub, Instance


class ContratInstanceTest(TestCase):
    def setUp(self):
        cache.clear()  # compteurs de throttling
        self.client = APIClient()
        self.token = str(uuid.uuid4())

    def register(self, version='0.1.49'):
        return self.client.post('/api/instances/register/',
                                {'token': self.token, 'version': version, 'rgpd_consent': False},
                                format='json')

    def heartbeat(self, token=None, version='0.1.49'):
        return self.client.post('/api/instances/heartbeat/', {'version': version}, format='json',
                                HTTP_X_INSTANCE_TOKEN=token or self.token)

    def test_enregistrement_puis_heartbeat(self):
        self.assertEqual(self.register().status_code, 201)
        response = self.heartbeat()
        # Régression #226 : l'instance authentifiée n'avait pas is_authenticated → 500
        self.assertEqual(response.status_code, 200)
        self.assertIn('last_heartbeat', response.json())

    def test_heartbeat_jeton_inconnu_refuse(self):
        self.assertIn(self.heartbeat(token=str(uuid.uuid4())).status_code, (401, 403))

    def test_heartbeat_sans_jeton_refuse(self):
        response = self.client.post('/api/instances/heartbeat/', {'version': '0.1.49'}, format='json')
        self.assertIn(response.status_code, (401, 403))

    def test_instance_me(self):
        self.register()
        response = self.client.get('/api/instances/me/', HTTP_X_INSTANCE_TOKEN=self.token)
        self.assertEqual(response.status_code, 200)

    def test_reenregistrement_met_a_jour(self):
        self.register('0.1.47')
        self.assertEqual(self.register('0.1.49').status_code, 200)


class VersionTest(TestCase):
    def test_pas_de_mise_a_jour_sans_version_publiee(self):
        views.LATEST_VERSION = ''
        self.assertFalse(views.is_update_available('0.1.49'))

    def test_comparaison_numerique(self):
        views.LATEST_VERSION = '0.1.50'
        try:
            self.assertTrue(views.is_update_available('0.1.49'))
            self.assertTrue(views.is_update_available('0.1.9'))   # 9 < 50, pas un tri de chaînes
            self.assertFalse(views.is_update_available('0.1.50'))
            self.assertFalse(views.is_update_available('0.2.0'))  # instance en avance
            self.assertFalse(views.is_update_available('unknown'))
        finally:
            views.LATEST_VERSION = ''


# --- Adhésion au hub (#696) ------------------------------------------------

EMPREINTE_DEPOT = empreinte('jeton-depot')
EMPREINTE_LECTURE = empreinte('jeton-lecture')


class CodeVerificationTest(TestCase):
    """La formule est recalculée côté instance : la moindre divergence fait
    afficher deux codes différents. La valeur est figée pour qu'une modification
    d'un seul côté se voie ici (même entrées, même valeur attendue côté instance)."""

    def test_valeur_figee(self):
        self.assertEqual(
            EMPREINTE_DEPOT, 'c608b951e9af8410d44022b31368434c2ffd5e14d267632ef335068337a15b92')
        self.assertEqual(
            EMPREINTE_LECTURE, '8b9121800784b8fe7c2b05cb6f7aa3f52a77e68e7441ffec5ec88d28efb5f8a0')
        self.assertEqual(
            code_verification('123e4567-e89b-12d3-a456-426614174000', 'cen-aura',
                              EMPREINTE_DEPOT, EMPREINTE_LECTURE),
            'BM5-KKM')

    def test_chaque_entree_change_le_code(self):
        base = ('123e4567-e89b-12d3-a456-426614174000', 'cen-aura', EMPREINTE_DEPOT, EMPREINTE_LECTURE)
        reference = code_verification(*base)
        for i, autre in enumerate(('00000000-0000-0000-0000-000000000000', 'rnf',
                                   EMPREINTE_LECTURE, EMPREINTE_DEPOT)):
            variante = list(base)
            variante[i] = autre
            self.assertNotEqual(code_verification(*variante), reference)


class AdhesionHubApiTest(TestCase):
    URL = '/api/instances/adhesion-hub/'

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.instance = Instance.objects.create(version='0.1.52')
        self.token = str(self.instance.token)

    def corps(self, **surcharges):
        corps = {'instance_id': 'cen-aura', 'libelle': 'CEN Auvergne-Rhône-Alpes',
                 'url_publique': 'https://cicada.cen-aura.fr', 'empreinte_depot': EMPREINTE_DEPOT,
                 'empreinte_lecture': EMPREINTE_LECTURE}
        corps.update(surcharges)
        return corps

    def demander(self, token=None, **surcharges):
        return self.client.post(self.URL, self.corps(**surcharges), format='json',
                                HTTP_X_INSTANCE_TOKEN=token or self.token)

    def lire(self, token=None):
        return self.client.get(self.URL, HTTP_X_INSTANCE_TOKEN=token or self.token)

    def test_authentification_requise(self):
        self.assertIn(self.client.post(self.URL, self.corps(), format='json').status_code, (401, 403))
        self.assertIn(self.client.get(self.URL).status_code, (401, 403))
        self.assertIn(self.demander(token=str(uuid.uuid4())).status_code, (401, 403))
        self.assertFalse(AdhesionHub.objects.exists())

    def test_creation(self):
        reponse = self.demander()
        self.assertEqual(reponse.status_code, 201)
        attendu = code_verification(self.token, 'cen-aura', EMPREINTE_DEPOT, EMPREINTE_LECTURE)
        self.assertEqual(reponse.json()['statut'], 'en_attente')
        self.assertEqual(reponse.json()['code'], attendu)
        self.assertIn('demandee_le', reponse.json())
        adhesion = AdhesionHub.objects.get(instance=self.instance)
        self.assertEqual(adhesion.code, attendu)
        self.assertEqual(adhesion.libelle, 'CEN Auvergne-Rhône-Alpes')

    def test_validations(self):
        for surcharge in ({'instance_id': 'CEN'}, {'instance_id': '-cen'}, {'instance_id': 'a' * 51},
                          {'libelle': ''}, {'empreinte_depot': 'abc'},
                          {'empreinte_lecture': EMPREINTE_LECTURE.upper()},
                          {'empreinte_lecture': EMPREINTE_DEPOT}):
            with self.subTest(surcharge=surcharge):
                self.assertEqual(self.demander(**surcharge).status_code, 400)
        self.assertFalse(AdhesionHub.objects.exists())

    def test_remplace_demande_en_attente(self):
        premier = self.demander().json()['code']
        autre = empreinte('autre-depot')
        reponse = self.demander(empreinte_depot=autre)
        self.assertEqual(reponse.status_code, 201)
        self.assertNotEqual(reponse.json()['code'], premier)
        self.assertEqual(AdhesionHub.objects.count(), 1)
        self.assertEqual(AdhesionHub.objects.get().empreinte_depot, autre)

    def test_remplace_demande_refusee(self):
        self.demander()
        AdhesionHub.objects.update(statut=AdhesionHub.REFUSEE, motif_refus='Nom incomplet', traitee_par='rnf')
        self.assertEqual(self.demander(libelle='CEN AURA').status_code, 201)
        adhesion = AdhesionHub.objects.get()
        self.assertEqual(adhesion.statut, AdhesionHub.EN_ATTENTE)
        self.assertEqual(adhesion.motif_refus, '')
        self.assertEqual(adhesion.traitee_par, '')
        self.assertIsNone(adhesion.traitee_le)

    def test_conflit_si_deja_acceptee(self):
        self.demander()
        AdhesionHub.objects.update(statut=AdhesionHub.ACCEPTEE)
        self.assertEqual(self.demander(libelle='Autre').status_code, 409)
        self.assertEqual(AdhesionHub.objects.get().libelle, 'CEN Auvergne-Rhône-Alpes')

    def test_conflit_si_identifiant_pris_par_une_autre_instance(self):
        autre = Instance.objects.create(version='0.1.52')
        self.demander(token=str(autre.token))
        AdhesionHub.objects.update(statut=AdhesionHub.ACCEPTEE)
        self.assertEqual(self.demander().status_code, 409)
        # Un identifiant seulement *demandé* ailleurs ne bloque pas : c'est RNF qui tranche.
        AdhesionHub.objects.update(statut=AdhesionHub.EN_ATTENTE)
        self.assertEqual(self.demander().status_code, 201)

    def test_lecture(self):
        self.assertEqual(self.lire().status_code, 404)
        code = self.demander().json()['code']
        donnees = self.lire().json()
        self.assertEqual(donnees['statut'], 'en_attente')
        self.assertEqual(donnees['code'], code)
        self.assertEqual(donnees['instance_id'], 'cen-aura')
        self.assertEqual(donnees['hub_url'], '')
        self.assertIsNone(donnees['traitee_le'])
        # Aucune empreinte ne repart vers l'instance : elle les a déjà.
        self.assertNotIn(EMPREINTE_DEPOT, str(donnees))

    def test_lecture_isolee_par_instance(self):
        self.demander()
        autre = Instance.objects.create(version='0.1.52')
        self.assertEqual(self.lire(token=str(autre.token)).status_code, 404)

    def test_hub_url_seulement_si_acceptee(self):
        self.demander()
        AdhesionHub.objects.update(hub_url='https://hub.example.org', statut=AdhesionHub.REFUSEE)
        self.assertEqual(self.lire().json()['hub_url'], '')
        AdhesionHub.objects.update(statut=AdhesionHub.ACCEPTEE)
        self.assertEqual(self.lire().json()['hub_url'], 'https://hub.example.org')


@override_settings(HUB_URL='https://hub.example.org/', HUB_ADMIN_TOKEN='secret-admin-hub')
class AdhesionHubAdminTest(TestCase):
    def setUp(self):
        self.admin = AdhesionHubAdmin(AdhesionHub, AdminSite())
        self.utilisateur = User.objects.create_superuser('rnf', 'rnf@example.org', 'x')
        instance = Instance.objects.create(version='0.1.52')
        self.adhesion = AdhesionHub.objects.create(
            instance=instance, instance_id_demande='cen-aura', libelle='CEN AURA',
            url_publique='https://cicada.cen-aura.fr', empreinte_depot=EMPREINTE_DEPOT,
            empreinte_lecture=EMPREINTE_LECTURE,
            code=code_verification(str(instance.token), 'cen-aura', EMPREINTE_DEPOT, EMPREINTE_LECTURE))

    def requete(self):
        requete = RequestFactory().post('/admin/')
        requete.user = self.utilisateur
        requete.session = {}
        requete._messages = FallbackStorage(requete)
        return requete

    def messages(self, requete):
        return [str(m) for m in requete._messages]

    def reponse_hub(self, code, corps=None):
        reponse = mock.Mock(status_code=code)
        reponse.json.return_value = corps or {}
        return reponse

    def accepter(self, reponse=None, effet=None):
        requete = self.requete()
        with mock.patch('instances.adhesion.requests.post', return_value=reponse, side_effect=effet) as post:
            self.admin.accepter(requete, AdhesionHub.objects.all())
        self.adhesion.refresh_from_db()
        return post, requete

    def test_acceptation(self):
        post, _ = self.accepter(self.reponse_hub(201, {'instance_id': 'cen-aura', 'active': True, 'cree': True}))
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], 'https://hub.example.org/api/federation/enrolements/')
        self.assertEqual(kwargs['headers'], {'X-Hub-Admin-Token': 'secret-admin-hub'})
        self.assertEqual(kwargs['json'], {
            'instance_id': 'cen-aura', 'libelle': 'CEN AURA', 'url_publique': 'https://cicada.cen-aura.fr',
            'empreinte_depot': EMPREINTE_DEPOT, 'empreinte_lecture': EMPREINTE_LECTURE})
        self.assertTrue(kwargs['timeout'])
        self.assertEqual(self.adhesion.statut, AdhesionHub.ACCEPTEE)
        self.assertEqual(self.adhesion.hub_url, 'https://hub.example.org')
        self.assertEqual(self.adhesion.traitee_par, 'rnf')
        self.assertIsNotNone(self.adhesion.traitee_le)

    def test_acceptation_idempotente_200(self):
        self.accepter(self.reponse_hub(200, {'cree': False}))
        self.assertEqual(self.adhesion.statut, AdhesionHub.ACCEPTEE)

    def test_echecs_du_hub_laissent_en_attente(self):
        for reponse, effet in ((self.reponse_hub(409, {'detail': 'déjà enrôlée'}), None),
                               (self.reponse_hub(403), None),
                               (self.reponse_hub(400, {'detail': 'invalide'}), None),
                               (None, requests.ConnectionError('refusé'))):
            with self.subTest(reponse=reponse, effet=effet):
                _, requete = self.accepter(reponse, effet)
                self.assertEqual(self.adhesion.statut, AdhesionHub.EN_ATTENTE)
                self.assertIsNone(self.adhesion.traitee_le)
                texte = ' '.join(self.messages(requete))
                self.assertIn('enrôlement impossible', texte)
                self.assertNotIn('secret-admin-hub', texte)

    @override_settings(HUB_URL='', HUB_ADMIN_TOKEN='')
    def test_hub_non_configure(self):
        post, requete = self.accepter(self.reponse_hub(201))
        post.assert_not_called()
        self.assertEqual(self.adhesion.statut, AdhesionHub.EN_ATTENTE)
        self.assertIn('HUB_URL', ' '.join(self.messages(requete)))

    def test_seule_une_demande_en_attente_est_acceptee(self):
        AdhesionHub.objects.update(statut=AdhesionHub.REFUSEE)
        post, _ = self.accepter(self.reponse_hub(201))
        post.assert_not_called()
        self.assertEqual(self.adhesion.statut, AdhesionHub.REFUSEE)

    def test_refus(self):
        AdhesionHub.objects.update(motif_refus='Structure inconnue')
        with mock.patch('instances.adhesion.requests.post') as post:
            self.admin.refuser(self.requete(), AdhesionHub.objects.all())
        post.assert_not_called()
        self.adhesion.refresh_from_db()
        self.assertEqual(self.adhesion.statut, AdhesionHub.REFUSEE)
        self.assertEqual(self.adhesion.motif_refus, 'Structure inconnue')
        self.assertEqual(self.adhesion.traitee_par, 'rnf')

    def test_refus_impossible_si_acceptee(self):
        AdhesionHub.objects.update(statut=AdhesionHub.ACCEPTEE)
        self.admin.refuser(self.requete(), AdhesionHub.objects.all())
        self.adhesion.refresh_from_db()
        self.assertEqual(self.adhesion.statut, AdhesionHub.ACCEPTEE)

    def test_pages_admin(self):
        """Liste et fiche se rendent, avec le code et le rappel de comparaison."""
        client = self.client
        client.force_login(self.utilisateur)
        liste = client.get('/admin/instances/adhesionhub/')
        self.assertContains(liste, self.adhesion.code)
        self.assertContains(liste, 'de vive voix')
        fiche = client.get(f'/admin/instances/adhesionhub/{self.adhesion.pk}/change/')
        self.assertContains(fiche, self.adhesion.code)
        self.assertContains(fiche, 'de vive voix')
