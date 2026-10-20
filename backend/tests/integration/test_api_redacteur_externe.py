"""
Tests d'intégration — #700 : rôle « Rédacteur externe » (bureau d'étude…).

Le rédacteur externe n'a accès à aucun plan par défaut. Il cherche le plan à
rédiger, demande l'accès en saisie à l'organisme gestionnaire, et une fois
rattaché il saisit, gère le cycle de vie et exporte comme un référent — mais
n'accède jamais aux suivis. Son organisme n'ouvre, lui, aucun plan.

#714 — Rattaché, il rend son organisme « organisme rédacteur » du plan, sans
que ce lien n'ouvre le plan à ses collègues.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.notifications.models import ValidationRequest
from apps.notifications.services import ValidationService
from apps.plans.access import user_can_access_plan, user_can_access_suivi
from tests.factories.enjeux import EnjeuFactory, NomenclatureEnjeuFactory
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory
from tests.factories.users import (
    RoleFactory, SiteFactory, OrganismeFactory, CorOgSiteFactory,
)


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def redacteur_data(db):
    og = OrganismeFactory()
    site = SiteFactory(nom_site='Marais du Bureau')
    CorOgSiteFactory(id_site=site, uuid_og=og)

    plan = PlanGestionFactory(nom='Plan à rédiger', statut='draft')
    CorSitePgFactory(plan_de_gestion=plan, site=site)
    EnjeuFactory(id_pg=plan, id_categorie=NomenclatureEnjeuFactory(), rang=1)

    bureau = OrganismeFactory()
    redacteur = RoleFactory(role_level='redacteur', id_organisme=bureau)
    admin_og = RoleFactory(role_level='admin_og', id_organisme=og)
    return {'plan': plan, 'site': site, 'og': og, 'bureau': bureau,
            'redacteur': redacteur, 'admin_og': admin_og}


@pytest.mark.django_db
@pytest.mark.integration
class TestRedacteurSansAcces:

    def test_aucun_plan_par_defaut(self, redacteur_data):
        response = _client(redacteur_data['redacteur']).get('/api/plans/plans/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'] == []

    def test_son_organisme_n_ouvre_aucun_plan(self, redacteur_data):
        """Même si son bureau d'étude était rattaché au site, il ne verrait rien."""
        CorOgSiteFactory(id_site=redacteur_data['site'], uuid_og=redacteur_data['bureau'])
        plan = redacteur_data['plan']
        plan.organismes_redacteurs.create(uuid_og=redacteur_data['bureau'])
        redacteur = redacteur_data['redacteur']

        assert not user_can_access_plan(redacteur, plan)
        response = _client(redacteur).get('/api/plans/plans/')
        assert response.data['results'] == []


@pytest.mark.django_db
@pytest.mark.integration
class TestRechercheAcces:

    def test_trouve_un_plan_par_le_nom_du_site(self, redacteur_data):
        response = _client(redacteur_data['redacteur']).get(
            '/api/plans/plans/recherche-acces/', {'q': 'marais du'}
        )
        assert response.status_code == status.HTTP_200_OK
        [resultat] = response.data['results']
        assert resultat['id_pg'] == redacteur_data['plan'].id_pg
        assert resultat['sites'] == ['Marais du Bureau']
        assert resultat['organismes_gestionnaires'] == [redacteur_data['og'].nom_organisme]
        assert resultat['acces'] is False
        assert resultat['demande_en_attente'] is False
        # Métadonnées seulement : jamais le contenu du plan.
        assert 'enjeux' not in resultat

    def test_terme_trop_court(self, redacteur_data):
        response = _client(redacteur_data['redacteur']).get(
            '/api/plans/plans/recherche-acces/', {'q': 'ma'}
        )
        assert response.data['results'] == []

    def test_reservee_au_redacteur(self, redacteur_data):
        utilisateur = RoleFactory(role_level='utilisateur')
        response = _client(utilisateur).get(
            '/api/plans/plans/recherche-acces/', {'q': 'marais'}
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.integration
class TestRedacteurRattache:

    @pytest.fixture
    def rattache(self, redacteur_data):
        """Demande d'accès en saisie, approuvée par l'admin de l'OG."""
        redacteur = redacteur_data['redacteur']
        plan = redacteur_data['plan']
        response = _client(redacteur).post('/api/validations/request_plan_access/', {
            'plan_id': plan.id_pg,
            'request_as_referent': True,
            'justification': 'Mission de rédaction',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        demande = ValidationRequest.objects.get(pk=response.data['id'])
        ValidationService.approve_plan_access(demande, redacteur_data['admin_og'])
        return redacteur_data

    def test_voit_et_saisit_le_plan(self, rattache):
        redacteur, plan = rattache['redacteur'], rattache['plan']
        client = _client(redacteur)
        response = client.get('/api/plans/plans/')
        assert [p['id_pg'] for p in response.data['results']] == [plan.id_pg]
        assert client.get(f'/api/plans/enjeux/by-plan/{plan.id_pg}/').status_code == 200

    def test_son_organisme_devient_redacteur(self, rattache):
        """#714 — rédacteur, pas gestionnaire."""
        plan, bureau = rattache['plan'], rattache['bureau']
        assert plan.organismes_redacteurs.filter(uuid_og=bureau).exists()
        assert not rattache['site'].corogsite_set.filter(uuid_og=bureau).exists()

    def test_ses_collegues_n_accedent_pas_au_plan(self, rattache):
        """#714 — l'organisme rédacteur n'ouvre le plan à personne d'autre."""
        plan, bureau = rattache['plan'], rattache['bureau']
        for role in ('utilisateur', 'admin_og'):
            collegue = RoleFactory(role_level=role, id_organisme=bureau)
            assert not user_can_access_plan(collegue, plan)
            response = _client(collegue).get('/api/plans/plans/')
            assert response.data['results'] == []
            assert _client(collegue).get(f'/api/plans/plans/{plan.id_pg}/').status_code == 404

    def test_le_gestionnaire_reste_redacteur_principal(self, rattache):
        """#739 — l'organisme du bureau d'étude s'ajoute EN DESSOUS du rédacteur
        principal, qui reste l'organisme gestionnaire du site."""
        plan, bureau, og = rattache['plan'], rattache['bureau'], rattache['og']
        response = _client(rattache['admin_og']).get(f'/api/plans/plans/{plan.id_pg}/')
        assert [(o['id_organisme'], o['principal'], o['externe'])
                for o in response.data['organismes_redacteurs_list']] == [
            (og.id_organisme, True, False),
            (bureau.id_organisme, False, True),
        ]

    def test_un_principal_deja_choisi_le_reste(self, redacteur_data):
        """#739 — le rattachement ne remplace pas le principal saisi à la création."""
        from apps.plans.models import CorRedacteurPlan
        autre = OrganismeFactory()
        plan = redacteur_data['plan']
        CorRedacteurPlan.objects.create(plan_de_gestion=plan, uuid_og=autre, principal=True)
        _client(redacteur_data['admin_og']).post(
            f'/api/plans/plans/{plan.id_pg}/assign-redacteur-externe/',
            {'user_id': redacteur_data['redacteur'].pk}, format='json')
        assert list(plan.organismes_redacteurs.values_list('uuid_og', 'principal')) == [
            (autre.uuid_organisme, True), (redacteur_data['bureau'].uuid_organisme, False)]

    def _patch(self, rattache, payload):
        plan = rattache['plan']
        response = _client(rattache['admin_og']).patch(
            f'/api/plans/plans/{plan.id_pg}/', payload, format='json')
        assert response.status_code == status.HTTP_200_OK, response.data
        return list(plan.organismes_redacteurs.values_list('uuid_og', 'principal'))

    def test_le_formulaire_peut_retirer_l_organisme_du_bureau(self, rattache):
        """#739 — l'organisme rédacteur se modifie : retiré, il ne revient pas
        (avant : réinscrit d'office à chaque enregistrement)."""
        og = rattache['og']
        assert self._patch(rattache, {
            'organismes_redacteurs_ids': [og.id_organisme],
            'organisme_redacteur_principal_id': og.id_organisme,
        }) == [(og.uuid_organisme, True)]
        # retirer l'organisme n'ôte pas l'accès du rédacteur
        assert rattache['plan'].referents.filter(pk=rattache['redacteur'].pk).exists()

    def test_le_formulaire_garde_le_bureau_en_secondaire(self, rattache):
        og, bureau = rattache['og'], rattache['bureau']
        assert self._patch(rattache, {
            'organismes_redacteurs_ids': [og.id_organisme, bureau.id_organisme],
            'organisme_redacteur_principal_id': og.id_organisme,
        }) == [(og.uuid_organisme, True), (bureau.uuid_organisme, False)]

    def test_le_formulaire_peut_designer_le_bureau_principal(self, rattache):
        og, bureau = rattache['og'], rattache['bureau']
        assert self._patch(rattache, {
            'organismes_redacteurs_ids': [og.id_organisme, bureau.id_organisme],
            'organisme_redacteur_principal_id': bureau.id_organisme,
        }) == [(bureau.uuid_organisme, True), (og.uuid_organisme, False)]

    def test_sans_principal_explicite_le_premier_l_est(self, rattache):
        """Compatibilité (création) : le premier de la liste est le principal."""
        og, bureau = rattache['og'], rattache['bureau']
        assert self._patch(rattache, {
            'organismes_redacteurs_ids': [bureau.id_organisme, og.id_organisme],
        }) == [(bureau.uuid_organisme, True), (og.uuid_organisme, False)]

    def test_membre_du_plan_marque_redacteur_externe(self, rattache):
        plan, redacteur = rattache['plan'], rattache['redacteur']
        response = _client(rattache['admin_og']).get(f'/api/plans/plans/{plan.id_pg}/')
        [membre] = [m for m in response.data['membres'] if m['id_role'] == redacteur.pk]
        assert membre['is_redacteur_externe'] is True

    def test_peut_exporter(self, rattache):
        plan = rattache['plan']
        response = _client(rattache['redacteur']).get(
            f'/api/plans/plans/{plan.id_pg}/export-arborescence-xlsx/'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_peut_gerer_le_cycle_de_vie(self, rattache):
        plan = rattache['plan']
        response = _client(rattache['redacteur']).post(
            f'/api/plans/plans/{plan.id_pg}/change-status/',
            {'new_status': 'valide'}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data

    def test_n_accede_pas_aux_suivis(self, rattache):
        redacteur, plan = rattache['redacteur'], rattache['plan']
        assert not user_can_access_suivi(redacteur, plan)
        client = _client(redacteur)
        for url in (
            f'/api/plans/realisations/by-plan/{plan.id_pg}/',
            f'/api/plans/realisations/bilan/{plan.id_pg}/',
            f'/api/plans/realisations/bilan-series/{plan.id_pg}/',
        ):
            assert client.get(url).status_code == status.HTTP_403_FORBIDDEN, url


@pytest.mark.django_db
@pytest.mark.integration
class TestAttributionDuRole:

    def test_super_admin_attribue_et_retire_le_role(self, db):
        super_admin = RoleFactory(role_level='super_admin')
        cible = RoleFactory(role_level='utilisateur')
        client = _client(super_admin)

        response = client.post(f'/api/users/users/{cible.pk}/set-redacteur/')
        assert response.status_code == status.HTTP_200_OK
        cible.refresh_from_db()
        assert cible.role_level == 'redacteur'

        response = client.post(f'/api/users/users/{cible.pk}/remove-redacteur/')
        assert response.status_code == status.HTTP_200_OK
        cible.refresh_from_db()
        assert cible.role_level == 'utilisateur'

    def test_refuse_depuis_un_autre_role(self, db):
        super_admin = RoleFactory(role_level='super_admin')
        cible = RoleFactory(role_level='admin_og')
        response = _client(super_admin).post(f'/api/users/users/{cible.pk}/set-redacteur/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reserve_au_super_admin(self, db):
        org = OrganismeFactory()
        admin_og = RoleFactory(role_level='admin_og', id_organisme=org)
        cible = RoleFactory(role_level='utilisateur', id_organisme=org)
        response = _client(admin_og).post(f'/api/users/users/{cible.pk}/set-redacteur/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.integration
class TestValidationAccesPlanReferent:
    """
    Le validateur d'une demande d'accès au plan « en tant que référent » peut
    l'accorder telle quelle ou n'accorder qu'un accès en consultation, comme
    pour une demande d'accès à un site.
    """

    def _demande(self, redacteur_data):
        response = _client(redacteur_data['redacteur']).post('/api/validations/request_plan_access/', {
            'plan_id': redacteur_data['plan'].id_pg,
            'request_as_referent': True,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        return response.data['id']

    def _approuver(self, redacteur_data, demande_id, **corps):
        return _client(redacteur_data['admin_og']).post(
            f'/api/validations/{demande_id}/approve/', corps, format='json')

    def test_approbation_simple_donne_le_role_de_referent(self, redacteur_data):
        demande_id = self._demande(redacteur_data)
        assert self._approuver(redacteur_data, demande_id).status_code == status.HTTP_200_OK
        plan = redacteur_data['plan']
        assert plan.referents.filter(pk=redacteur_data['redacteur'].pk).exists()

    def test_approbation_en_consultation_seulement(self, redacteur_data):
        from apps.plans.models import CorRolePlan

        demande_id = self._demande(redacteur_data)
        response = self._approuver(redacteur_data, demande_id, approve_as_referent=False)
        assert response.status_code == status.HTTP_200_OK
        plan, redacteur = redacteur_data['plan'], redacteur_data['redacteur']
        assert not plan.referents.filter(pk=redacteur.pk).exists()
        assert CorRolePlan.objects.get(plan_de_gestion=plan, id_role=redacteur).referent is False


@pytest.mark.django_db
@pytest.mark.integration
class TestRattacherRedacteurExterneDepuisLePlan:
    """#714 — un référent du plan rattache un utilisateur comme rédacteur externe."""

    def _url(self, plan):
        return f'/api/plans/plans/{plan.id_pg}/assign-redacteur-externe/'

    def test_referent_rattache_et_attribue_le_role(self, redacteur_data):
        plan = redacteur_data['plan']
        referent = RoleFactory(role_level='utilisateur', id_organisme=redacteur_data['og'])
        plan.referents.add(referent)
        bureau = OrganismeFactory()
        cible = RoleFactory(role_level='utilisateur', id_organisme=bureau)

        response = _client(referent).post(self._url(plan), {'user_id': cible.pk}, format='json')

        assert response.status_code == status.HTTP_200_OK, response.data
        cible.refresh_from_db()
        assert cible.role_level == 'redacteur'
        assert plan.referents.filter(pk=cible.pk).exists()
        assert plan.organismes_redacteurs.filter(uuid_og=bureau).exists()

    def test_refuse_un_gestionnaire(self, redacteur_data):
        plan = redacteur_data['plan']
        cible = RoleFactory(role_level='admin_og')
        response = _client(redacteur_data['admin_og']).post(
            self._url(plan), {'user_id': cible.pk}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_refuse_un_simple_membre(self, redacteur_data):
        plan = redacteur_data['plan']
        membre = RoleFactory(role_level='utilisateur')
        from apps.plans.models import CorRolePlan
        CorRolePlan.objects.create(id_role=membre, plan_de_gestion=plan, referent=False)
        cible = RoleFactory(role_level='utilisateur')
        response = _client(membre).post(self._url(plan), {'user_id': cible.pk}, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrait_du_plan_revoque_l_acces(self, redacteur_data):
        plan, redacteur = redacteur_data['plan'], redacteur_data['redacteur']
        client = _client(redacteur_data['admin_og'])
        assert client.post(self._url(plan), {'user_id': redacteur.pk}, format='json').status_code == 200
        assert user_can_access_plan(redacteur, plan)

        response = client.delete(f'/api/plans/plans/{plan.id_pg}/remove_member/?user_id={redacteur.pk}')
        assert response.status_code == status.HTTP_200_OK
        assert not user_can_access_plan(redacteur, plan)


@pytest.mark.django_db
@pytest.mark.integration
class TestRedacteursExternesDisponibles:
    """#737 — « Gérer les utilisateurs du plan » propose les rédacteurs externes
    de toute l'instance, quel que soit leur organisme."""

    URL = '/api/plans/plans/{}/redacteurs-externes/'

    def test_admin_og_voit_les_redacteurs_des_autres_organismes(self, redacteur_data):
        RoleFactory(role_level='redacteur', active=False, id_organisme=redacteur_data['bureau'])
        RoleFactory(role_level='utilisateur', id_organisme=redacteur_data['bureau'])
        plan = redacteur_data['plan']

        response = _client(redacteur_data['admin_og']).get(self.URL.format(plan.id_pg))

        assert response.status_code == status.HTTP_200_OK
        assert [u['id_role'] for u in response.data] == [redacteur_data['redacteur'].id_role]
        [redacteur] = response.data
        assert redacteur['email'] == redacteur_data['redacteur'].email
        assert redacteur['nom_organisme'] == redacteur_data['bureau'].nom_organisme

    def test_referent_du_plan(self, redacteur_data):
        referent = RoleFactory(role_level='utilisateur')
        redacteur_data['plan'].referents.add(referent)
        response = _client(referent).get(self.URL.format(redacteur_data['plan'].id_pg))
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_refuse_a_qui_ne_gere_pas_le_plan(self, redacteur_data):
        membre = RoleFactory(role_level='utilisateur')
        from apps.plans.models import CorRolePlan
        CorRolePlan.objects.create(id_role=membre, plan_de_gestion=redacteur_data['plan'], referent=False)
        response = _client(membre).get(self.URL.format(redacteur_data['plan'].id_pg))
        assert response.status_code == status.HTTP_403_FORBIDDEN
