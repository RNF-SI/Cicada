"""Contrat entre l'API de suivi et le paquet cicada (installateur, heartbeat).

Les appels reproduisent exactement ceux de
packaging/debian/usr/share/cicada/install/install_service.py (register) et
packaging/debian/usr/bin/cicada-heartbeat (heartbeat).
"""
import re
import uuid
from datetime import timedelta
from unittest import mock

import requests
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core import mail
from django.core.cache import cache
from django.test import RequestFactory, TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from . import views
from .adhesion import ALPHABET_CODE, empreinte, empreinte_code, normaliser_code, tirer_code
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


def reponse_hub(code, corps=None):
    reponse = mock.Mock(status_code=code)
    reponse.json.return_value = corps or {}
    return reponse


class CodeTest(TestCase):
    def test_format_et_alphabet(self):
        for _ in range(50):
            code = tirer_code()
            self.assertRegex(code, r'^[A-Z2-9]{4}-[A-Z2-9]{4}$')
            self.assertFalse(set(code.replace('-', '')) - set(ALPHABET_CODE))
        self.assertGreater(len({tirer_code() for _ in range(50)}), 45)  # tiré au hasard

    def test_normalisation(self):
        self.assertEqual(normaliser_code(' abcd-efgh '), 'ABCDEFGH')
        self.assertEqual(normaliser_code('ab cd\tef-gh'), 'ABCDEFGH')
        self.assertEqual(empreinte_code('abcd efgh'), empreinte_code('ABCD-EFGH'))


@override_settings(RNF_CONTACT_EMAIL='si@rnf.test', ADMIN_BASE_URL='https://suivi.test/',
                   DEFAULT_FROM_EMAIL='noreply@cicada.test')
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
                 'empreinte_lecture': EMPREINTE_LECTURE, 'contact_nom': 'Marie Dupont',
                 'contact_email': 'marie@cen-aura.fr', 'contact_telephone': '04 00 00 00 00',
                 'message': 'Nous souhaitons partager nos plans.'}
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
        for url in (self.URL + 'confirmation/', '/api/instances/contact/'):
            self.assertIn(self.client.post(url, {}, format='json').status_code, (401, 403))
        self.assertFalse(AdhesionHub.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_creation(self):
        reponse = self.demander()
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(set(reponse.json()), {'statut', 'demandee_le'})
        self.assertEqual(reponse.json()['statut'], 'en_attente')
        adhesion = AdhesionHub.objects.get(instance=self.instance)
        self.assertEqual(adhesion.empreinte_depot, EMPREINTE_DEPOT)
        self.assertEqual(adhesion.libelle, 'CEN Auvergne-Rhône-Alpes')
        self.assertEqual(adhesion.contact_nom, 'Marie Dupont')
        self.assertEqual(adhesion.contact_telephone, '04 00 00 00 00')
        self.assertEqual(adhesion.email_confirmation, 'marie@cen-aura.fr')  # pré-remplie

    def test_contact_facultatifs(self):
        corps = self.corps()
        del corps['contact_telephone'], corps['message']
        reponse = self.client.post(self.URL, corps, format='json', HTTP_X_INSTANCE_TOKEN=self.token)
        self.assertEqual(reponse.status_code, 201)

    def test_deux_emails_a_la_demande(self):
        self.demander()
        self.assertEqual(len(mail.outbox), 2)
        a_rnf, accuse = mail.outbox
        adhesion = AdhesionHub.objects.get()
        self.assertEqual(a_rnf.to, ['si@rnf.test'])
        self.assertEqual(a_rnf.subject,
                         "[CICADA] Nouvelle demande d'adhésion au hub — CEN Auvergne-Rhône-Alpes")
        self.assertEqual(a_rnf.reply_to, ['marie@cen-aura.fr'])
        for attendu in ('cen-aura', 'https://cicada.cen-aura.fr', 'Marie Dupont', 'marie@cen-aura.fr',
                        '04 00 00 00 00', 'Nous souhaitons partager nos plans.',
                        f'https://suivi.test/admin/instances/adhesionhub/{adhesion.pk}/change/',
                        'prenez contact'):
            self.assertIn(attendu, a_rnf.body)
        self.assertEqual(accuse.to, ['marie@cen-aura.fr'])
        self.assertIn('code de confirmation', accuse.body)
        for message in mail.outbox:
            self.assertEqual(message.from_email, 'noreply@cicada.test')
            self.assertNotIn(EMPREINTE_DEPOT, message.body)

    def test_echec_email_n_echoue_pas_la_demande(self):
        with mock.patch('instances.adhesion.EmailMessage.send', side_effect=OSError('smtp')), \
                self.assertLogs('instances.adhesion', level='ERROR'):
            reponse = self.demander()
        self.assertEqual(reponse.status_code, 201)
        self.assertTrue(AdhesionHub.objects.exists())

    def test_validations(self):
        for surcharge in ({'instance_id': 'CEN'}, {'instance_id': '-cen'}, {'instance_id': 'a' * 51},
                          {'libelle': ''}, {'empreinte_depot': 'abc'},
                          {'empreinte_lecture': EMPREINTE_LECTURE.upper()},
                          {'empreinte_lecture': EMPREINTE_DEPOT},
                          {'contact_nom': ''}, {'contact_email': ''}, {'contact_email': 'pas-une-adresse'}):
            with self.subTest(surcharge=surcharge):
                self.assertEqual(self.demander(**surcharge).status_code, 400)
        self.assertFalse(AdhesionHub.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_remplace_demande_en_attente(self):
        self.demander()
        autre = empreinte('autre-depot')
        reponse = self.demander(empreinte_depot=autre, contact_email='paul@cen-aura.fr')
        self.assertEqual(reponse.status_code, 201)
        self.assertEqual(AdhesionHub.objects.count(), 1)
        adhesion = AdhesionHub.objects.get()
        self.assertEqual(adhesion.empreinte_depot, autre)
        self.assertEqual(adhesion.email_confirmation, 'paul@cen-aura.fr')

    def test_remplace_demande_code_envoye(self):
        """Un code envoyé portait sur d'autres empreintes : il ne doit plus valoir."""
        self.demander()
        AdhesionHub.objects.update(statut=AdhesionHub.CODE_ENVOYE, code_empreinte=empreinte_code('AAAA-BBBB'),
                                   code_expire_le=timezone.now() + timedelta(days=7), code_essais=2)
        self.assertEqual(self.demander().status_code, 201)
        adhesion = AdhesionHub.objects.get()
        self.assertEqual(adhesion.statut, AdhesionHub.EN_ATTENTE)
        self.assertEqual(adhesion.code_empreinte, '')
        self.assertIsNone(adhesion.code_expire_le)
        self.assertEqual(adhesion.code_essais, 0)

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
        self.demander()
        donnees = self.lire().json()
        self.assertEqual(donnees['statut'], 'en_attente')
        self.assertEqual(donnees['instance_id'], 'cen-aura')
        self.assertEqual(donnees['hub_url'], '')
        self.assertIsNone(donnees['traitee_le'])
        self.assertIsNone(donnees['code_expire_le'])
        # Aucune empreinte ne repart vers l'instance : elle les a déjà.
        self.assertNotIn(EMPREINTE_DEPOT, str(donnees))

    def test_lecture_code_envoye(self):
        self.demander()
        expire = timezone.now() + timedelta(days=7)
        empreinte_du_code = empreinte_code('AAAA-BBBB')
        AdhesionHub.objects.update(statut=AdhesionHub.CODE_ENVOYE, code_empreinte=empreinte_du_code,
                                   code_expire_le=expire)
        donnees = self.lire().json()
        self.assertEqual(donnees['statut'], 'code_envoye')
        self.assertEqual(donnees['code_expire_le'], expire.isoformat())
        self.assertNotIn(empreinte_du_code, str(donnees))
        self.assertNotIn('AAAA', str(donnees))

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


CODE = 'K7FM-29QX'


@override_settings(HUB_URL='https://hub.example.org/', HUB_ADMIN_TOKEN='secret-admin-hub')
class ConfirmationTest(TestCase):
    URL = '/api/instances/adhesion-hub/confirmation/'

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.instance = Instance.objects.create(version='0.1.52')
        self.adhesion = AdhesionHub.objects.create(
            instance=self.instance, instance_id_demande='cen-aura', libelle='CEN AURA',
            url_publique='https://cicada.cen-aura.fr', empreinte_depot=EMPREINTE_DEPOT,
            empreinte_lecture=EMPREINTE_LECTURE, contact_nom='Marie', contact_email='marie@cen-aura.fr',
            email_confirmation='marie@cen-aura.fr', statut=AdhesionHub.CODE_ENVOYE,
            code_empreinte=empreinte_code(CODE), code_expire_le=timezone.now() + timedelta(days=7))

    def confirmer(self, code, reponse=None, effet=None, token=None):
        if reponse is None and effet is None:
            reponse = reponse_hub(201, {'instance_id': 'cen-aura', 'active': True, 'cree': True})
        with mock.patch('instances.adhesion.requests.post', return_value=reponse, side_effect=effet) as post:
            resultat = self.client.post(self.URL, {'code': code}, format='json',
                                        HTTP_X_INSTANCE_TOKEN=token or str(self.instance.token))
        self.adhesion.refresh_from_db()
        return resultat, post

    def test_succes(self):
        reponse, post = self.confirmer(CODE)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.json(), {'statut': 'acceptee', 'hub_url': 'https://hub.example.org'})
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
        self.assertEqual(self.adhesion.traitee_par, 'code')
        self.assertIsNotNone(self.adhesion.traitee_le)
        self.assertEqual(self.adhesion.code_empreinte, '')  # consommé

    def test_code_normalise(self):
        reponse, _ = self.confirmer(' k7fm 29qx ')
        self.assertEqual(reponse.status_code, 200)

    def test_idempotence_hub_200(self):
        reponse, _ = self.confirmer(CODE, reponse_hub(200, {'cree': False}))
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(self.adhesion.statut, AdhesionHub.ACCEPTEE)

    def test_sans_demande(self):
        autre = Instance.objects.create(version='0.1.52')
        reponse, post = self.confirmer(CODE, token=str(autre.token))
        self.assertEqual(reponse.status_code, 404)
        post.assert_not_called()

    def test_pas_de_code(self):
        for statut in (AdhesionHub.EN_ATTENTE, AdhesionHub.REFUSEE, AdhesionHub.ACCEPTEE):
            with self.subTest(statut=statut):
                AdhesionHub.objects.update(statut=statut)
                reponse, post = self.confirmer(CODE)
                self.assertEqual(reponse.status_code, 409)
                self.assertEqual(reponse.json(), {'erreur': 'pas_de_code'})
                post.assert_not_called()

    def test_code_expire(self):
        AdhesionHub.objects.update(code_expire_le=timezone.now() - timedelta(seconds=1))
        reponse, post = self.confirmer(CODE)
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.json(), {'erreur': 'code_expire'})
        post.assert_not_called()
        self.assertEqual(self.adhesion.statut, AdhesionHub.CODE_ENVOYE)

    def test_code_invalide_puis_trop_d_essais(self):
        for restants in (4, 3, 2, 1):
            reponse, post = self.confirmer('AAAA-AAAA')
            self.assertEqual(reponse.status_code, 400)
            self.assertEqual(reponse.json(), {'erreur': 'code_invalide', 'essais_restants': restants})
            post.assert_not_called()
        self.assertEqual(self.adhesion.code_essais, 4)
        reponse, _ = self.confirmer('AAAA-AAAA')
        self.assertEqual(reponse.status_code, 400)
        self.assertEqual(reponse.json(), {'erreur': 'trop_d_essais'})
        self.assertEqual(self.adhesion.statut, AdhesionHub.EN_ATTENTE)
        self.assertEqual(self.adhesion.code_empreinte, '')
        # Le bon code ne vaut plus : RNF doit en renvoyer un.
        reponse, post = self.confirmer(CODE)
        self.assertEqual(reponse.json(), {'erreur': 'pas_de_code'})
        post.assert_not_called()

    def test_code_vide_ne_compte_pas(self):
        reponse, _ = self.confirmer('  ')
        self.assertEqual(reponse.json(), {'erreur': 'code_invalide', 'essais_restants': 5})
        self.assertEqual(self.adhesion.code_essais, 0)

    def test_echec_hub_conserve_le_code(self):
        for reponse, effet in ((reponse_hub(409, {'detail': 'déjà enrôlée'}), None),
                               (reponse_hub(403), None),
                               (None, requests.ConnectionError('refusé'))):
            with self.subTest(reponse=reponse, effet=effet):
                with self.assertLogs('instances.views', level='ERROR') as journal:
                    resultat, _ = self.confirmer(CODE, reponse, effet)
                self.assertEqual(resultat.status_code, 502)
                self.assertEqual(resultat.json(), {'erreur': 'hub_injoignable'})
                self.assertEqual(self.adhesion.statut, AdhesionHub.CODE_ENVOYE)
                self.assertEqual(self.adhesion.code_empreinte, empreinte_code(CODE))
                self.assertEqual(self.adhesion.code_essais, 0)
                texte = ' '.join(journal.output)
                self.assertNotIn('secret-admin-hub', texte)
                self.assertNotIn(CODE, texte)
        resultat, _ = self.confirmer(CODE)  # l'administrateur réessaie plus tard
        self.assertEqual(resultat.status_code, 200)

    @override_settings(HUB_URL='', HUB_ADMIN_TOKEN='')
    def test_hub_non_configure(self):
        with self.assertLogs('instances.views', level='ERROR'):
            reponse, post = self.confirmer(CODE)
        self.assertEqual(reponse.status_code, 502)
        post.assert_not_called()

    def test_verrou_sur_la_demande(self):
        """La lecture de la demande se fait sous select_for_update."""
        with mock.patch('instances.views.AdhesionHub.objects.select_for_update',
                        wraps=AdhesionHub.objects.select_for_update) as verrou:
            self.confirmer('AAAA-AAAA')
        verrou.assert_called_once()


@override_settings(RNF_CONTACT_EMAIL='si@rnf.test')
class ContactTest(TestCase):
    URL = '/api/instances/contact/'

    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.instance = Instance.objects.create(version='0.1.52', structure_name='CEN AURA (suivi)')

    def envoyer(self, **surcharges):
        corps = {'nom': 'Marie Dupont', 'email': 'marie@cen-aura.fr', 'sujet': 'Question\nsur le hub',
                 'message': 'Bonjour, une question.'}
        corps.update(surcharges)
        return self.client.post(self.URL, corps, format='json', HTTP_X_INSTANCE_TOKEN=str(self.instance.token))

    def test_envoi_sans_adhesion(self):
        reponse = self.envoyer()
        self.assertEqual(reponse.status_code, 202)
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['si@rnf.test'])
        self.assertEqual(message.reply_to, ['marie@cen-aura.fr'])
        self.assertEqual(message.subject, '[CICADA] Message de CEN AURA (suivi) — Question sur le hub')
        self.assertIn('Bonjour, une question.', message.body)

    def test_envoi_avec_adhesion(self):
        AdhesionHub.objects.create(instance=self.instance, instance_id_demande='cen-aura', libelle='CEN AURA',
                                   url_publique='https://cicada.cen-aura.fr', empreinte_depot=EMPREINTE_DEPOT,
                                   empreinte_lecture=EMPREINTE_LECTURE, contact_nom='M', contact_email='m@x.fr')
        self.envoyer()
        message = mail.outbox[0]
        self.assertTrue(message.subject.startswith('[CICADA] Message de CEN AURA — '))
        self.assertIn('cen-aura', message.body)
        self.assertIn('https://cicada.cen-aura.fr', message.body)
        self.assertNotIn(EMPREINTE_DEPOT, message.body)

    def test_champs_requis(self):
        for champ in ('nom', 'email', 'sujet', 'message'):
            with self.subTest(champ=champ):
                self.assertEqual(self.envoyer(**{champ: ''}).status_code, 400)
        self.assertEqual(self.envoyer(email='pas-une-adresse').status_code, 400)
        self.assertEqual(len(mail.outbox), 0)

    def test_echec_envoi_signale(self):
        with mock.patch('instances.adhesion.EmailMessage.send', side_effect=OSError('smtp')), \
                self.assertLogs('instances.views', level='ERROR'):
            reponse = self.envoyer()
        self.assertEqual(reponse.status_code, 502)
        self.assertEqual(reponse.json(), {'erreur': 'envoi_impossible'})

    def test_limite(self):
        for _ in range(10):
            self.assertEqual(self.envoyer().status_code, 202)
        self.assertEqual(self.envoyer().status_code, 429)


@override_settings(HUB_URL='https://hub.example.org/', HUB_ADMIN_TOKEN='secret-admin-hub',
                   RNF_CONTACT_EMAIL='si@rnf.test')
class AdhesionHubAdminTest(TestCase):
    def setUp(self):
        self.admin = AdhesionHubAdmin(AdhesionHub, AdminSite())
        self.utilisateur = User.objects.create_superuser('rnf', 'rnf@example.org', 'x')
        instance = Instance.objects.create(version='0.1.52')
        self.adhesion = AdhesionHub.objects.create(
            instance=instance, instance_id_demande='cen-aura', libelle='CEN AURA',
            url_publique='https://cicada.cen-aura.fr', empreinte_depot=EMPREINTE_DEPOT,
            empreinte_lecture=EMPREINTE_LECTURE, contact_nom='Marie', contact_email='marie@cen-aura.fr',
            email_confirmation='direction@cen-aura.fr')

    def requete(self):
        requete = RequestFactory().post('/admin/')
        requete.user = self.utilisateur
        requete.session = {}
        requete._messages = FallbackStorage(requete)
        return requete

    def messages(self, requete):
        return [str(m) for m in requete._messages]

    def envoyer_code(self):
        requete = self.requete()
        self.admin.envoyer_code_confirmation(requete, AdhesionHub.objects.all())
        self.adhesion.refresh_from_db()
        return requete

    def code_de_l_email(self, message):
        return re.search(r'[A-Z2-9]{4}-[A-Z2-9]{4}', message.body).group(0)

    def test_pas_d_action_accepter(self):
        self.assertNotIn('accepter', self.admin.actions)

    def test_envoi_du_code(self):
        requete = self.envoyer_code()
        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['direction@cen-aura.fr'])  # l'adresse corrigée par RNF
        self.assertEqual(message.subject, "[CICADA] Votre code de confirmation pour l'exploration nationale")
        self.assertIn('7 jours', message.body)
        self.assertIn('Administration > Paramètres', message.body)
        code = self.code_de_l_email(message)
        self.assertEqual(self.adhesion.statut, AdhesionHub.CODE_ENVOYE)
        self.assertEqual(self.adhesion.code_empreinte, empreinte_code(code))
        self.assertEqual(self.adhesion.code_envoye_par, 'rnf')
        self.assertIsNotNone(self.adhesion.code_envoye_le)
        delai = self.adhesion.code_expire_le - timezone.now()
        self.assertTrue(timedelta(days=6, hours=23) < delai <= timedelta(days=7))
        texte = ' '.join(self.messages(requete))
        self.assertIn('code de confirmation envoyé', texte)
        self.assertNotIn(code, texte)  # le code n'existe que dans l'e-mail

    def test_renvoi_invalide_le_precedent(self):
        self.envoyer_code()
        premier = self.code_de_l_email(mail.outbox[0])
        AdhesionHub.objects.update(code_essais=3)
        self.envoyer_code()
        second = self.code_de_l_email(mail.outbox[1])
        self.assertEqual(self.adhesion.code_essais, 0)
        self.assertEqual(self.adhesion.code_empreinte, empreinte_code(second))
        if premier != second:
            self.assertNotEqual(self.adhesion.code_empreinte, empreinte_code(premier))

    def test_echec_envoi_ne_change_rien(self):
        with mock.patch('instances.adhesion.EmailMessage.send', side_effect=OSError('smtp')), \
                self.assertLogs('instances.admin', level='ERROR'):
            requete = self.envoyer_code()
        self.assertEqual(self.adhesion.statut, AdhesionHub.EN_ATTENTE)
        self.assertEqual(self.adhesion.code_empreinte, '')
        self.assertIn("n'a pas pu être envoyé", ' '.join(self.messages(requete)))

    @override_settings(HUB_URL='', HUB_ADMIN_TOKEN='')
    def test_envoi_refuse_si_hub_non_configure(self):
        requete = self.envoyer_code()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.adhesion.statut, AdhesionHub.EN_ATTENTE)
        self.assertIn('HUB_URL', ' '.join(self.messages(requete)))

    def test_envoi_refuse_hors_attente(self):
        for statut in (AdhesionHub.REFUSEE, AdhesionHub.ACCEPTEE):
            with self.subTest(statut=statut):
                AdhesionHub.objects.update(statut=statut)
                self.envoyer_code()
                self.assertEqual(self.adhesion.statut, statut)
        self.assertEqual(len(mail.outbox), 0)

    def test_envoi_refuse_sans_adresse(self):
        AdhesionHub.objects.update(email_confirmation='')
        self.envoyer_code()
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.adhesion.statut, AdhesionHub.EN_ATTENTE)

    def test_code_envoye_puis_confirme_par_l_api(self):
        """Bout à bout : le code de l'e-mail, saisi sur l'instance, enrôle."""
        self.envoyer_code()
        code = self.code_de_l_email(mail.outbox[0])
        cache.clear()
        with mock.patch('instances.adhesion.requests.post', return_value=reponse_hub(201)):
            reponse = APIClient().post('/api/instances/adhesion-hub/confirmation/', {'code': code.lower()},
                                       format='json', HTTP_X_INSTANCE_TOKEN=str(self.adhesion.instance.token))
        self.assertEqual(reponse.status_code, 200)

    def test_refus(self):
        AdhesionHub.objects.update(motif_refus='Structure inconnue')
        self.admin.refuser(self.requete(), AdhesionHub.objects.all())
        self.adhesion.refresh_from_db()
        self.assertEqual(self.adhesion.statut, AdhesionHub.REFUSEE)
        self.assertEqual(self.adhesion.motif_refus, 'Structure inconnue')
        self.assertEqual(self.adhesion.traitee_par, 'rnf')

    def test_refus_apres_envoi_du_code_l_invalide(self):
        self.envoyer_code()
        self.admin.refuser(self.requete(), AdhesionHub.objects.all())
        self.adhesion.refresh_from_db()
        self.assertEqual(self.adhesion.statut, AdhesionHub.REFUSEE)
        self.assertEqual(self.adhesion.code_empreinte, '')

    def test_refus_impossible_si_acceptee(self):
        AdhesionHub.objects.update(statut=AdhesionHub.ACCEPTEE)
        self.admin.refuser(self.requete(), AdhesionHub.objects.all())
        self.adhesion.refresh_from_db()
        self.assertEqual(self.adhesion.statut, AdhesionHub.ACCEPTEE)

    def test_pages_admin(self):
        """Liste et fiche se rendent, avec le rappel de vérification ; l'adresse d'envoi est éditable."""
        client = self.client
        client.force_login(self.utilisateur)
        liste = client.get('/admin/instances/adhesionhub/')
        self.assertContains(liste, 'CEN AURA')
        self.assertContains(liste, 'prenez contact avec l')
        self.assertContains(liste, 'Envoyer le code de confirmation')
        fiche = client.get(f'/admin/instances/adhesionhub/{self.adhesion.pk}/change/')
        self.assertContains(fiche, 'cen-aura')
        self.assertContains(fiche, 'prenez contact avec l')
        self.assertContains(fiche, 'name="email_confirmation"')
        self.assertContains(fiche, 'name="motif_refus"')
        self.assertNotContains(fiche, 'name="contact_email"')
