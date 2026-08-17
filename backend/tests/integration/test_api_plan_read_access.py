"""
Tests d'intégration — #610 : accès en LECTURE SEULE au contenu d'un plan pour
un utilisateur lié au plan sans être « référent ».

Un membre du plan (`CorRolePlan`, `referent=False`) doit pouvoir consulter le
plan et toute son arborescence (enjeux, indicateurs, opérations, RH),
qu'il soit en brouillon ou validé, sans pouvoir écrire. Les SUIVIS (bilan,
réalisations) restent réservés aux référents/gestionnaires — cf. #610 et
`TestPlanSuiviAccess`.

Vérifie aussi le corollaire : le contenu d'un plan validé n'est PAS visible
d'un utilisateur sans aucun lien avec ce plan.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from tests.factories.enjeux import EnjeuFactory, NomenclatureEnjeuFactory
from tests.factories.plans import (
    PlanGestionFactory, CorRolePlanFactory, CorSitePgFactory,
)
from tests.factories.users import (
    RoleFactory, SiteFactory, OrganismeFactory, CorOgSiteFactory,
)


@pytest.fixture
def plan_read_access_data(db):
    """Plan d'un organisme A, un membre non référent, et un tiers sans lien."""
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan lecture seule', statut='draft')
    CorSitePgFactory(plan_de_gestion=plan, site=site)
    enjeu = EnjeuFactory(id_pg=plan, id_categorie=NomenclatureEnjeuFactory(), rang=1)

    # Membre du plan, d'un AUTRE organisme : seul le lien CorRolePlan le rattache.
    membre = RoleFactory(role_level='utilisateur', id_organisme=OrganismeFactory())
    CorRolePlanFactory(id_role=membre, plan_de_gestion=plan, referent=False)

    # Référent du plan (#610 — voit les suivis).
    referent = RoleFactory(role_level='utilisateur', id_organisme=OrganismeFactory())
    plan.referents.add(referent)

    # Utilisateur sans aucun lien avec le plan.
    etranger = RoleFactory(role_level='utilisateur', id_organisme=OrganismeFactory())

    return {
        'plan': plan, 'site': site, 'enjeu': enjeu,
        'membre': membre, 'referent': referent, 'etranger': etranger,
    }


def _client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


CONTENT_ENDPOINTS = [
    '/api/plans/enjeux/',
    '/api/plans/facteurs-influence/',
    '/api/plans/pressions/',
    '/api/plans/objectifs-long-terme/',
    '/api/plans/niveaux-exigence/',
    '/api/plans/objectifs-operationnels/',
    '/api/plans/resultats-attendus/',
    '/api/plans/indicateurs/',
    '/api/plans/metriques/',
    '/api/plans/mesures/',
    '/api/plans/indicateur-mesures/',
    '/api/plans/operations/',
    '/api/plans/postes/',
    '/api/inventaires/suivis/',
]
# #610 — les SUIVIS (réalisations, bilan) ne sont PAS du contenu ouvert : ils
# sont réservés aux référents/gestionnaires (voir TestPlanSuiviAccess).


@pytest.mark.django_db
@pytest.mark.integration
class TestPlanMemberReadAccess:
    """#610 — un membre non référent lit le plan et son contenu."""

    def test_membre_peut_voir_le_plan(self, plan_read_access_data):
        plan = plan_read_access_data['plan']
        response = _client(plan_read_access_data['membre']).get(
            f'/api/plans/plans/by-slug/{plan.slug}/'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id_pg'] == plan.id_pg

    @pytest.mark.parametrize('url', CONTENT_ENDPOINTS)
    def test_membre_non_referent_lit_le_contenu(self, plan_read_access_data, url):
        """Avant #610, IsReferent renvoyait 403 sur toutes ces routes."""
        response = _client(plan_read_access_data['membre']).get(url)
        assert response.status_code == status.HTTP_200_OK, url

    def test_membre_voit_les_enjeux_du_plan(self, plan_read_access_data):
        plan = plan_read_access_data['plan']
        response = _client(plan_read_access_data['membre']).get(
            f'/api/plans/enjeux/?id_pg={plan.id_pg}'
        )
        assert response.status_code == status.HTTP_200_OK
        ids = [e['id_enjeu'] for e in response.data['results']]
        assert plan_read_access_data['enjeu'].id_enjeu in ids

    def test_membre_lit_un_plan_valide(self, plan_read_access_data):
        """Le verrouillage #248 ne doit pas empêcher la lecture."""
        plan = plan_read_access_data['plan']
        plan.statut = 'valide'
        plan.save(update_fields=['statut'])

        response = _client(plan_read_access_data['membre']).get(
            f'/api/plans/enjeux/?id_pg={plan.id_pg}'
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 1

    def test_membre_non_referent_ne_peut_pas_ecrire(self, plan_read_access_data):
        """La lecture est ouverte, l'écriture reste réservée aux référents."""
        plan = plan_read_access_data['plan']
        response = _client(plan_read_access_data['membre']).post(
            '/api/plans/enjeux/',
            {'id_pg': plan.id_pg, 'libelle': 'Tentative', 'rang': 2},
            format='json',
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.integration
class TestPlanContentIsolation:
    """#610 — le contenu reste cloisonné aux plans auxquels on est lié."""

    def test_utilisateur_sans_lien_ne_voit_pas_le_contenu_dun_plan_valide(
        self, plan_read_access_data
    ):
        """
        Le scoping historique ouvrait tout plan `statut='valide'` à quiconque
        passait le filtre `IsReferent` — y compris hors organisme.
        """
        plan = plan_read_access_data['plan']
        plan.statut = 'valide'
        plan.save(update_fields=['statut'])

        response = _client(plan_read_access_data['etranger']).get(
            f'/api/plans/enjeux/?id_pg={plan.id_pg}'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'] == []

    def test_utilisateur_sans_lien_ne_voit_pas_le_plan(self, plan_read_access_data):
        plan = plan_read_access_data['plan']
        plan.statut = 'valide'
        plan.save(update_fields=['statut'])

        response = _client(plan_read_access_data['etranger']).get(
            f'/api/plans/plans/by-slug/{plan.slug}/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
@pytest.mark.integration
class TestPlanSuiviAccess:
    """#610 — les suivis (bilan, réalisations) sont réservés aux référents et
    gestionnaires ; un simple membre lié au plan n'y accède pas."""

    def test_membre_non_referent_ne_voit_pas_les_realisations(self, plan_read_access_data):
        plan = plan_read_access_data['plan']
        response = _client(plan_read_access_data['membre']).get(
            f'/api/plans/realisations/by-plan/{plan.id_pg}/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_membre_non_referent_ne_voit_pas_le_bilan(self, plan_read_access_data):
        plan = plan_read_access_data['plan']
        response = _client(plan_read_access_data['membre']).get(
            f'/api/plans/realisations/bilan/{plan.id_pg}/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_liste_realisations_scopee_hors_suivi_est_vide_pour_le_membre(
        self, plan_read_access_data
    ):
        """La liste reste 200 mais ne fuit aucune réalisation (queryset scopé)."""
        response = _client(plan_read_access_data['membre']).get('/api/plans/realisations/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['results'] == []

    def test_membre_non_referent_ne_voit_pas_les_series_du_bilan(self, plan_read_access_data):
        plan = plan_read_access_data['plan']
        response = _client(plan_read_access_data['membre']).get(
            f'/api/plans/realisations/bilan-series/{plan.id_pg}/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_referent_voit_les_realisations_et_le_bilan(self, plan_read_access_data):
        plan = plan_read_access_data['plan']
        client = _client(plan_read_access_data['referent'])
        assert client.get(
            f'/api/plans/realisations/by-plan/{plan.id_pg}/'
        ).status_code == status.HTTP_200_OK
        assert client.get(
            f'/api/plans/realisations/bilan/{plan.id_pg}/'
        ).status_code == status.HTTP_200_OK
        assert client.get(
            f'/api/plans/realisations/bilan-series/{plan.id_pg}/'
        ).status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
class TestPlanSuiviQueryShape:
    """
    Garde-fou de performance sur les agrégations bornées à UN plan.

    Ces vues valident l'accès au plan avec `assert_suivi_access()` puis
    restreignent les lignes à ce plan : re-filtrer chaque ligne par le périmètre
    de `get_queryset()` (7 chemins ORM OR-és, > 60 jointures) ne retire rien et
    coûte cher. Sur une base sans statistiques — c'est le cas en CI juste après
    `seed_testdata` — le planificateur bascule en GEQO et la réponse passait de
    ~100 ms à plus de 5 s, faisant échouer les tests E2E de la page Bilan.
    """

    # Les trois vues tournent aujourd'hui entre 10 et 12 jointures ; le budget
    # laisse de la marge tout en rattrapant la requête à ~63 jointures que
    # produisait le périmètre par ligne.
    JOIN_BUDGET = 25

    @pytest.mark.parametrize('endpoint', ['bilan', 'bilan-series', 'by-plan'])
    def test_agregations_du_plan_sans_requete_a_rallonge(
        self, plan_read_access_data, endpoint
    ):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        plan = plan_read_access_data['plan']
        client = _client(plan_read_access_data['referent'])

        with CaptureQueriesContext(connection) as captured:
            response = client.get(f'/api/plans/realisations/{endpoint}/{plan.id_pg}/')

        assert response.status_code == status.HTTP_200_OK
        pire = max(q['sql'].count('JOIN') for q in captured.captured_queries)
        assert pire <= self.JOIN_BUDGET, (
            f"/{endpoint}/ produit une requête à {pire} jointures : le périmètre "
            f"par ligne a probablement été réappliqué après assert_suivi_access()."
        )
