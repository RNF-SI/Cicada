"""Comptes et sessions : désactiver coupe, se déconnecter révoque, les essais
de mot de passe sont limités, l'impersonation ne fait que regarder."""
import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.authentication.providers import usershub
from tests.factories.users import (
    AdminOrganismeFactory, OrganismeFactory, RoleFactory, SuperAdminFactory,
)

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

MOT_DE_PASSE = 'Correct-cheval-42'


def _porteur(jeton):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {jeton}')
    return client


@pytest.fixture
def compte():
    user = RoleFactory(email='agent@test.fr', identifiant='agent')
    user.set_password(MOT_DE_PASSE)
    user.save()
    return user


class TestDesactivation:
    def test_un_compte_desactive_perd_l_acces_des_la_requete_suivante(self, compte):
        acces = str(RefreshToken.for_user(compte).access_token)
        client = _porteur(acces)
        assert client.get('/api/auth/me/').status_code == 200
        compte.active = False
        compte.save()
        assert client.get('/api/auth/me/').status_code == 401
        assert client.get('/api/plans/plans/').status_code == 401

    def test_un_compte_desactive_ne_rafraichit_plus(self, compte):
        rafraichissement = str(RefreshToken.for_user(compte))
        compte.active = False
        compte.save()
        reponse = APIClient().post('/api/auth/refresh/', {'refresh': rafraichissement}, format='json')
        assert reponse.status_code == 401


class TestSessions:
    def test_la_deconnexion_revoque_le_jeton_de_rafraichissement(self, compte):
        jetons = RefreshToken.for_user(compte)
        client = _porteur(str(jetons.access_token))
        assert client.post('/api/auth/logout/', {'refresh': str(jetons)}, format='json').status_code == 200
        reponse = APIClient().post('/api/auth/refresh/', {'refresh': str(jetons)}, format='json')
        assert reponse.status_code == 401

    def test_on_ne_revoque_pas_le_jeton_d_un_autre(self, compte):
        from apps.authentication.sessions import ouvrir
        autre = ouvrir(RefreshToken.for_user(RoleFactory()))
        client = _porteur(str(RefreshToken.for_user(compte).access_token))
        assert client.post('/api/auth/logout/', {'refresh': str(autre)}, format='json').status_code == 400
        assert APIClient().post('/api/auth/refresh/', {'refresh': str(autre)}, format='json').status_code == 200

    def test_changer_son_mot_de_passe_ferme_les_autres_sessions(self, compte):
        acces = str(RefreshToken.for_user(compte).access_token)
        compte.set_password('Un-autre-mot-de-passe-7')
        compte.save()
        assert _porteur(acces).get('/api/auth/me/').status_code == 401

    def test_le_jeton_d_acces_est_court_en_production(self):
        # Le développement l'allonge (config/settings/development.py) ; la base,
        # celle de la production, le garde court.
        from config.settings import base
        assert base.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds() <= 3600
        assert base.SIMPLE_JWT['CHECK_REVOKE_TOKEN'] is True
        assert 'rest_framework_simplejwt.token_blacklist' in base.INSTALLED_APPS


def _connexion(identifiant, mot_de_passe, client_ip):
    # Apache d'entrée puis Apache du conteneur : « <forgé>, <client>, <proxy> ».
    return APIClient().post(
        '/api/auth/login/', {'username': identifiant, 'password': mot_de_passe}, format='json',
        HTTP_X_FORWARDED_FOR=f'6.6.6.{client_ip}, {client_ip_reel(client_ip)}, 10.0.0.2',
    )


def client_ip_reel(i):
    return f'203.0.113.{i}'


@pytest.fixture
def cache_vide():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def sans_limite_par_adresse(monkeypatch, cache_vide):
    """La limite par adresse (5/min) masquerait celle par compte, testée ici."""
    from apps.authentication.throttles import AuthRateThrottle
    monkeypatch.setattr(AuthRateThrottle, 'allow_request', lambda self, request, view: True)


class TestLimiteDesEssais:
    def test_changer_l_en_tete_forge_ne_contourne_plus_la_limite(self, compte, cache_vide, settings):
        """Le développement coupe les limites ; on remet celles de la production."""
        from config.settings import base
        from rest_framework.settings import api_settings
        from apps.authentication.throttles import AuthRateThrottle
        settings.REST_FRAMEWORK = {**base.REST_FRAMEWORK, 'NUM_PROXIES': 2}
        api_settings.reload()
        AuthRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES
        try:
            codes = []
            for essai in range(7):
                reponse = APIClient().post(
                    '/api/auth/login/', {'username': 'inconnu', 'password': 'faux'}, format='json',
                    HTTP_X_FORWARDED_FOR=f'6.6.6.{essai}, 203.0.113.7, 10.0.0.2')
                codes.append(reponse.status_code)
            assert codes[-1] == 429, codes
        finally:
            settings.REST_FRAMEWORK = __import__('django.conf', fromlist=['settings']).settings.REST_FRAMEWORK
            api_settings.reload()
            AuthRateThrottle.THROTTLE_RATES = api_settings.DEFAULT_THROTTLE_RATES

    def test_dix_echecs_d_une_adresse_la_ferment_pour_ce_compte(self, compte, sans_limite_par_adresse):
        for _ in range(10):
            assert _connexion('agent', 'faux', 7).status_code in (401, 429)
        reponse = _connexion('agent', MOT_DE_PASSE, 7)
        assert reponse.status_code == 429
        assert 'tentatives' in reponse.json()['detail']

    def test_des_echecs_d_ailleurs_n_enferment_pas_le_titulaire(self, compte, sans_limite_par_adresse):
        """Le verrou par compte servait de déni de service : dix requêtes de
        n'importe où tenaient un super admin dehors, bon mot de passe compris."""
        for essai in range(40):
            _connexion('agent', 'faux', essai)
        assert _connexion('agent', MOT_DE_PASSE, 99).status_code == 200

    def test_au_dela_de_trente_echecs_repartis_les_adresses_fautives_sont_refusees(self, compte, sans_limite_par_adresse):
        for essai in range(30):
            _connexion('agent', 'faux', essai)
        assert _connexion('agent', MOT_DE_PASSE, 3).status_code == 429
        assert _connexion('agent', MOT_DE_PASSE, 98).status_code == 200

    def test_email_et_identifiant_partagent_le_compteur(self, compte, sans_limite_par_adresse):
        for _ in range(5):
            _connexion('agent', 'faux', 8)
            _connexion('agent@test.fr', 'faux', 8)
        assert _connexion('agent@test.fr', MOT_DE_PASSE, 8).status_code == 429

    def test_la_reinitialisation_debloque(self, compte, sans_limite_par_adresse):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode
        for _ in range(10):
            _connexion('agent', 'faux', 9)
        assert _connexion('agent', MOT_DE_PASSE, 9).status_code == 429
        reponse = APIClient().post('/api/auth/password-reset/confirm/', {
            'uid': urlsafe_base64_encode(force_bytes(compte.pk)),
            'token': default_token_generator.make_token(compte),
            'new_password': 'Un-autre-mot-de-passe-7',
        }, format='json')
        assert reponse.status_code == 200
        assert _connexion('agent', 'Un-autre-mot-de-passe-7', 9).status_code == 200

    def test_un_succes_remet_le_compteur_a_zero(self, compte, sans_limite_par_adresse):
        for _ in range(3):
            _connexion('agent', 'faux', 10)
        assert _connexion('agent', MOT_DE_PASSE, 10).status_code == 200
        from apps.authentication import echecs
        from django.core.cache import cache as c
        cle_compte, cle_adresse = echecs._cles(f'role:{compte.pk}', client_ip_reel(10))
        assert not c.get(cle_adresse)


class TestFuitesDInformation:
    def test_une_demande_en_attente_ne_se_devoile_pas_sans_son_mot_de_passe(self, db, cache_vide):
        from django.contrib.auth.hashers import make_password
        from tests.factories.notifications import PendingUserFactory
        organisme = OrganismeFactory(nom_organisme='Organisme Secret')
        PendingUserFactory(
            email='demandeur@test.fr', password_hash=make_password(MOT_DE_PASSE),
            requested_organisme=organisme)
        reponse = APIClient().post(
            '/api/auth/login/', {'username': 'demandeur@test.fr', 'password': 'faux'}, format='json')
        assert reponse.status_code == 401
        assert 'Organisme Secret' not in reponse.content.decode()
        assert 'attente' not in reponse.content.decode()

    def test_le_dernier_editeur_des_parametres_n_est_pas_public(self, db):
        reponse = APIClient().get('/api/settings/')
        if reponse.status_code == 200:
            assert reponse.json().get('updated_by_name') in (None, '')


class TestImpersonation:
    @staticmethod
    def _demarrer(admin, cible, **corps):
        client = APIClient()
        client.force_authenticate(admin)
        return client.post(f'/api/auth/impersonate/{cible.pk}/', {'reason': 'test', **corps}, format='json').json()

    @override_settings(IMPERSONATION_ECRITURE=False)
    def test_un_jeton_d_impersonation_ne_peut_pas_ecrire(self, db):
        admin = SuperAdminFactory()
        cible = RoleFactory()
        jetons = self._demarrer(admin, cible)
        imp = _porteur(jetons['access'])
        assert imp.get('/api/auth/me/').status_code == 200
        reponse = imp.post('/api/plans/plans/', {'nom': 'Écrit en se faisant passer'}, format='json')
        assert reponse.status_code == 403
        assert imp.post('/api/auth/stop-impersonation/', {}, format='json').status_code != 403

    def test_l_arret_ferme_la_session_empruntee(self, db):
        admin, cible = SuperAdminFactory(), RoleFactory()
        jetons = self._demarrer(admin, cible)
        imp = _porteur(jetons['access'])
        assert imp.post('/api/auth/stop-impersonation/', {}, format='json').status_code == 200
        assert imp.get('/api/auth/me/').status_code == 401
        assert APIClient().post('/api/auth/refresh/', {'refresh': jetons['refresh']}, format='json').status_code == 401

    def test_un_auteur_desactive_perd_la_session_empruntee(self, db):
        admin, cible = SuperAdminFactory(), RoleFactory()
        jetons = self._demarrer(admin, cible)
        admin.active = False
        admin.save()
        assert _porteur(jetons['access']).get('/api/auth/me/').status_code == 401
        assert APIClient().post('/api/auth/refresh/', {'refresh': jetons['refresh']}, format='json').status_code == 401

    def test_une_impersonation_dure_une_heure_au_plus(self, db):
        import time
        from apps.authentication.sessions import CLAIM_DEBUT
        admin, cible = SuperAdminFactory(), RoleFactory()
        jetons = self._demarrer(admin, cible)
        ancien = RefreshToken(jetons['refresh'])
        ancien[CLAIM_DEBUT] = int(time.time()) - 2 * 3600
        assert APIClient().post('/api/auth/refresh/', {'refresh': str(ancien)}, format='json').status_code == 401

    def test_les_jetons_du_super_admin_sont_revoques_au_depart(self, db):
        from apps.authentication.sessions import ouvrir
        admin, cible = SuperAdminFactory(), RoleFactory()
        siens = ouvrir(RefreshToken.for_user(admin))
        self._demarrer(admin, cible, refresh=str(siens))
        assert APIClient().post('/api/auth/refresh/', {'refresh': str(siens)}, format='json').status_code == 401


class TestDureeDesSessions:
    def test_un_rafraichissement_apres_changement_de_mot_de_passe_est_refuse(self, compte):
        from apps.authentication.sessions import ouvrir
        jeton = ouvrir(RefreshToken.for_user(compte))
        compte.set_password('Un-autre-mot-de-passe-7')
        compte.save()
        assert APIClient().post('/api/auth/refresh/', {'refresh': str(jeton)}, format='json').status_code == 401

    def test_une_session_a_une_duree_absolue(self, compte, settings):
        import time
        from apps.authentication.sessions import ouvrir
        jeton = ouvrir(RefreshToken.for_user(compte), debut=time.time() - 8 * 86400)
        assert APIClient().post('/api/auth/refresh/', {'refresh': str(jeton)}, format='json').status_code == 401
        frais = ouvrir(RefreshToken.for_user(compte))
        assert APIClient().post('/api/auth/refresh/', {'refresh': str(frais)}, format='json').status_code == 200

    def test_la_rotation_garde_le_debut_de_session(self, compte):
        from apps.authentication.sessions import CLAIM_DEBUT, ouvrir
        jeton = ouvrir(RefreshToken.for_user(compte), debut=1_900_000_000 - 1)
        jeton[CLAIM_DEBUT] = int(__import__('time').time()) - 3600
        reponse = APIClient().post('/api/auth/refresh/', {'refresh': str(jeton)}, format='json')
        assert reponse.status_code == 200
        assert RefreshToken(reponse.json()['refresh'])[CLAIM_DEBUT] == jeton[CLAIM_DEBUT]

    def test_la_connexion_ouvre_une_session(self, compte, cache_vide):
        from apps.authentication.sessions import CLAIM_DEBUT
        reponse = _connexion('agent', MOT_DE_PASSE, 11)
        assert reponse.status_code == 200
        assert CLAIM_DEBUT in RefreshToken(reponse.json()['refresh'])


class TestRoles:
    def test_un_admin_d_organisme_ne_donne_pas_l_acces_a_l_admin_django(self, db):
        admin = AdminOrganismeFactory()
        collegue = RoleFactory(id_organisme=admin.id_organisme)
        client = APIClient()
        client.force_authenticate(admin)
        client.patch(f'/api/users/users/{collegue.pk}/', {'is_staff': True}, format='json')
        collegue.refresh_from_db()
        assert collegue.is_staff is False

    def test_usershub_ne_relie_pas_un_super_admin_par_son_email(self, db):
        SuperAdminFactory(email='chef@rnf.fr')
        identite = usershub.IdentiteUsersHub(id_role=4242, email='chef@rnf.fr', identifiant='chef')
        with pytest.raises(usershub.UsersHubErreur) as erreur:
            usershub.compte_pour(identite)
        assert erreur.value.status_code == 409

    def test_usershub_relie_un_admin_d_organisme_d_un_autre_organisme_non(self, db):
        AdminOrganismeFactory(email='admin@cen.fr')
        identite = usershub.IdentiteUsersHub(id_role=4243, email='admin@cen.fr', identifiant='admin')
        with pytest.raises(usershub.UsersHubErreur):
            usershub.compte_pour(identite)


class TestAdministrationDesComptes:
    """Matrice profil × cible × champ de ``/api/users/users/`` : un compte ne
    s'administre que depuis un rang supérieur, dans son organisme (super admin
    excepté) ; le rôle ne passe jamais par cette route ; le mot de passe d'autrui
    reste au super admin."""

    @pytest.fixture
    def monde(self, db):
        rnf, cen = OrganismeFactory(), OrganismeFactory()
        return {
            'super': SuperAdminFactory(id_organisme=rnf),
            'rp': RoleFactory(role_level='redacteur_principal', id_organisme=rnf),
            'admin_rnf': AdminOrganismeFactory(id_organisme=rnf),
            'admin_rnf_2': AdminOrganismeFactory(id_organisme=rnf),
            'admin_cen': AdminOrganismeFactory(id_organisme=cen),
            'user_rnf': RoleFactory(id_organisme=rnf),
            'user_cen': RoleFactory(id_organisme=cen),
            'cen': cen,
        }

    @staticmethod
    def _client(user):
        client = APIClient()
        client.force_authenticate(user)
        return client

    @pytest.mark.parametrize('acteur', ['admin_rnf', 'rp'])
    @pytest.mark.parametrize('cible', ['super', 'rp', 'admin_rnf_2'])
    def test_on_ne_touche_pas_un_compte_de_rang_egal_ou_superieur(self, monde, acteur, cible):
        if acteur == cible:
            pytest.skip('son propre compte : autre règle')
        client, compte = self._client(monde[acteur]), monde[cible]
        if monde[acteur].rang() > compte.rang():
            pytest.skip('rang inférieur')
        assert client.patch(f'/api/users/users/{compte.pk}/', {'active': False}, format='json').status_code in (403, 404)
        assert client.post(f'/api/users/users/{compte.pk}/change_password/',
                           {'password': 'Nouveau-mot-2-passe', 'password_confirm': 'Nouveau-mot-2-passe'},
                           format='json').status_code in (403, 404)
        assert client.delete(f'/api/users/users/{compte.pk}/').status_code in (403, 404)
        compte.refresh_from_db()
        assert compte.active is True
        assert compte.check_password('TestPassword123!')

    @pytest.mark.parametrize('acteur', ['admin_rnf', 'rp'])
    def test_le_mot_de_passe_d_autrui_reste_au_super_admin(self, monde, acteur):
        cible = monde['user_rnf']
        reponse = self._client(monde[acteur]).post(
            f'/api/users/users/{cible.pk}/change_password/',
            {'password': 'Nouveau-mot-2-passe', 'password_confirm': 'Nouveau-mot-2-passe'}, format='json')
        assert reponse.status_code == 403
        cible.refresh_from_db()
        assert cible.check_password('TestPassword123!')

    def test_le_super_admin_change_le_mot_de_passe_d_autrui(self, monde):
        cible = monde['admin_cen']
        reponse = self._client(monde['super']).post(
            f'/api/users/users/{cible.pk}/change_password/',
            {'password': 'Nouveau-mot-2-passe', 'password_confirm': 'Nouveau-mot-2-passe'}, format='json')
        assert reponse.status_code == 200
        cible.refresh_from_db()
        assert cible.check_password('Nouveau-mot-2-passe')

    def test_son_propre_mot_de_passe_exige_l_ancien(self, monde):
        moi = monde['user_rnf']
        client = self._client(moi)
        nouveau = {'password': 'Nouveau-mot-2-passe', 'password_confirm': 'Nouveau-mot-2-passe'}
        assert client.post(f'/api/users/users/{moi.pk}/change_password/', nouveau, format='json').status_code == 400
        reponse = client.post(f'/api/users/users/{moi.pk}/change_password/',
                              {**nouveau, 'old_password': 'TestPassword123!'}, format='json')
        assert reponse.status_code == 200
        moi.refresh_from_db()
        assert moi.check_password('Nouveau-mot-2-passe')

    def test_un_admin_ne_promeut_pas_par_la_fiche(self, monde):
        cible = monde['user_rnf']
        reponse = self._client(monde['admin_rnf']).patch(
            f'/api/users/users/{cible.pk}/', {'role_level': 'admin_og'}, format='json')
        assert reponse.status_code == 403
        cible.refresh_from_db()
        assert cible.role_level == 'utilisateur'

    def test_un_admin_ne_deplace_pas_un_compte_dans_un_autre_organisme(self, monde):
        cible = monde['user_rnf']
        reponse = self._client(monde['admin_rnf']).patch(
            f'/api/users/users/{cible.pk}/', {'uuid_organisme': str(monde['cen'].uuid_organisme)}, format='json')
        assert reponse.status_code == 403
        cible.refresh_from_db()
        assert cible.id_organisme_id == monde['admin_rnf'].id_organisme_id

    def test_un_admin_detache_et_desactive_un_compte_de_son_organisme(self, monde):
        """Le geste « retirer de l'organisme » de l'écran des utilisateurs."""
        cible = monde['user_rnf']
        client = self._client(monde['admin_rnf'])
        assert client.patch(f'/api/users/users/{cible.pk}/', {'uuid_organisme': None}, format='json').status_code == 200
        cible.refresh_from_db()
        assert cible.id_organisme_id is None

    def test_un_admin_desactive_un_compte_de_son_organisme(self, monde):
        cible = monde['user_rnf']
        assert self._client(monde['admin_rnf']).patch(
            f'/api/users/users/{cible.pk}/', {'active': False}, format='json').status_code == 200
        cible.refresh_from_db()
        assert cible.active is False

    def test_un_admin_ne_touche_pas_un_autre_organisme(self, monde):
        cible = monde['user_cen']
        assert self._client(monde['admin_rnf']).patch(
            f'/api/users/users/{cible.pk}/', {'active': False}, format='json').status_code in (403, 404)
        cible.refresh_from_db()
        assert cible.active is True

    def test_son_profil_sans_son_role_ni_son_organisme(self, monde):
        moi = monde['user_rnf']
        reponse = self._client(moi).patch(
            f'/api/users/users/{moi.pk}/',
            {'nom_role': 'Nouveau', 'role_level': 'super_admin', 'active': False,
             'uuid_organisme': str(monde['cen'].uuid_organisme)}, format='json')
        assert reponse.status_code == 200
        moi.refresh_from_db()
        assert (moi.nom_role, moi.role_level, moi.active) == ('Nouveau', 'utilisateur', True)
        assert moi.id_organisme_id != monde['cen'].pk


class TestCloisonnementDesComptes:
    def test_inviter_un_organisme_ne_livre_pas_ses_comptes(self, db):
        from tests.factories.users import SiteFactory
        cen = OrganismeFactory()
        RoleFactory(id_organisme=cen, email='secret@cen.fr')
        referent = AdminOrganismeFactory()  # référent de quelque chose, d'un autre organisme
        client = APIClient()
        client.force_authenticate(referent)
        reponse = client.get(f'/api/users/organismes/{cen.pk}/?for_invite=true')
        assert reponse.status_code == 200
        assert reponse.json().get('users') == []
        assert 'secret@cen.fr' not in reponse.content.decode()

    def test_l_admin_de_l_organisme_voit_ses_comptes(self, db):
        admin = AdminOrganismeFactory()
        RoleFactory(id_organisme=admin.id_organisme, email='collegue@org.fr')
        client = APIClient()
        client.force_authenticate(admin)
        reponse = client.get(f'/api/users/organismes/{admin.id_organisme.pk}/')
        assert 'collegue@org.fr' in reponse.content.decode()

    def test_un_identifiant_ne_peut_pas_etre_l_email_d_un_autre(self, db):
        org = OrganismeFactory()
        reponse = APIClient().post('/api/auth/register/', {
            'email': 'moi@example.fr', 'identifiant': 'chef@rnf.fr',
            'password': 'Inscr-Audit-2026x', 'password_confirm': 'Inscr-Audit-2026x',
            'prenom_role': 'A', 'nom_role': 'B', 'requested_organisme_id': org.pk,
        }, format='json')
        assert reponse.status_code == 400
        assert 'identifiant' in reponse.json().get('errors', reponse.json())

    def test_la_connexion_resout_d_abord_par_email(self, db):
        victime = RoleFactory(email='victime@rnf.fr', identifiant='victime')
        squat = RoleFactory(email='squat@ailleurs.fr', identifiant='squat')
        # Identifiant posé avant la règle (ou en base) : l'e-mail l'emporte.
        type(squat).objects.filter(pk=squat.pk).update(identifiant='victime@rnf.fr')
        reponse = APIClient().post('/api/auth/login/', {'username': 'victime@rnf.fr',
                                                         'password': 'TestPassword123!'}, format='json')
        assert reponse.status_code == 200
        assert reponse.json()['user']['id'] == victime.pk


class TestJournalDActivite:
    def test_un_admin_ne_lit_pas_l_activite_d_un_autre_organisme(self, db):
        from apps.core.models import ActivityLog
        rnf, cen = OrganismeFactory(), OrganismeFactory()
        ActivityLog.objects.create(entity_type='user', entity_id=1, entity_name='Agent RNF',
                                   action='create', description='Compte créé', visibility='public',
                                   related_organisme=rnf)
        admin_cen = AdminOrganismeFactory(id_organisme=cen)
        client = APIClient()
        client.force_authenticate(admin_cen)
        reponse = client.get('/api/activity/')
        assert 'Agent RNF' not in reponse.content.decode()

    def test_le_redacteur_principal_ne_lit_ni_systeme_ni_rgpd(self, db):
        from apps.core.models import ActivityLog
        ActivityLog.objects.create(entity_type='instance', entity_id=1, entity_name='Réglage secret',
                                   action='update', description='x', visibility='system')
        ActivityLog.objects.create(entity_type='user', entity_id=2, entity_name='Demande RGPD',
                                   action='rgpd_request', description='x', visibility='admin')
        rp = RoleFactory(role_level='redacteur_principal')
        client = APIClient()
        client.force_authenticate(rp)
        contenu = client.get('/api/activity/').content.decode()
        assert 'Réglage secret' not in contenu and 'Demande RGPD' not in contenu


class TestAnonymisation:
    def test_le_nom_disparait_du_journal_et_des_notifications(self, db):
        from apps.core.models import ActivityLog
        from apps.notifications.models import Notification
        z = RoleFactory(email='zorglub@example.fr', prenom_role='Zorglub', nom_role='Testanon')
        ActivityLog.objects.create(entity_type='user', entity_id=z.pk, entity_name='Zorglub Testanon',
                                   action='create', description='Compte de Zorglub Testanon créé',
                                   visibility='admin')
        autre = RoleFactory()
        Notification.objects.create(recipient=autre, notification_type='info', title='Info',
                                    message='zorglub@example.fr a rejoint le site')
        z.anonymize()
        assert not ActivityLog.objects.filter(description__icontains='zorglub').exists()
        assert not ActivityLog.objects.filter(entity_name__icontains='zorglub').exists()
        assert not Notification.objects.filter(message__icontains='zorglub').exists()
