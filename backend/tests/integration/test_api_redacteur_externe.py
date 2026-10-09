"""
Tests d'intégration — #700 : rôle « Rédacteur externe » (bureau d'étude…).

Le rédacteur externe n'a accès à aucun plan par défaut. Il cherche le plan à
rédiger, demande l'accès en saisie à l'organisme gestionnaire, et une fois
rattaché il saisit, gère le cycle de vie et exporte comme un référent — mais
n'accède jamais aux suivis. Son organisme n'ouvre, lui, aucun plan.
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

    def test_son_organisme_n_est_pas_rattache(self, rattache):
        plan, bureau = rattache['plan'], rattache['bureau']
        assert not plan.organismes_redacteurs.filter(uuid_og=bureau).exists()
        assert not rattache['site'].corogsite_set.filter(uuid_og=bureau).exists()

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
