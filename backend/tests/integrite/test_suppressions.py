"""Filet « perte de données » — famille C : les gestes destructeurs bornés."""
import pytest
from rest_framework.test import APIClient

from apps.plans.models import PlanGestion
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import (
    AdminOrganismeFactory, CorOgSiteFactory, CorRoleSiteFactory, OrganismeFactory, RoleFactory,
    SiteFactory, SuperAdminFactory,
)
from tests.integrite.socle import construire_plan_complet, ecarts, inventaire

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_une_version_validee_ne_se_supprime_pas(db):
    referent = RoleFactory()
    plan = PlanGestionFactory(statut='valide', referents=[referent])
    avant = inventaire()
    reponse = _client(referent).post(f'/api/plans/plans/{plan.pk}/delete-version/', {}, format='json')
    assert reponse.status_code in (403, 409), reponse.content[:300]
    assert PlanGestion.objects.filter(pk=plan.pk).exists()
    assert not ecarts(avant, inventaire())


def test_un_brouillon_se_supprime_toujours(db):
    referent = RoleFactory()
    plan = PlanGestionFactory(statut='draft', referents=[referent])
    PlanGestionFactory(statut='valide')  # la chaîne n'est pas en jeu
    reponse = _client(referent).post(f'/api/plans/plans/{plan.pk}/delete-version/', {}, format='json')
    assert reponse.status_code == 200, reponse.content[:300]


def test_un_financeur_qui_porte_du_suivi_ne_se_supprime_pas():
    pc = construire_plan_complet()
    avant = inventaire()
    reponse = _client(pc.admin).delete(f'/api/plans/financeurs/{pc.financeur.pk}/')
    assert reponse.status_code == 409, reponse.content[:300]
    assert not ecarts(avant, inventaire())


def test_un_poste_qui_porte_du_temps_realise_ne_se_supprime_pas():
    pc = construire_plan_complet()
    avant = inventaire()
    reponse = _client(pc.admin).delete(f'/api/plans/postes/{pc.poste.pk}/')
    assert reponse.status_code == 409, reponse.content[:300]
    assert not ecarts(avant, inventaire())


def test_un_organisme_qui_porte_du_budget_ne_se_supprime_pas():
    pc = construire_plan_complet()
    admin = SuperAdminFactory()
    avant = inventaire()
    reponse = _client(admin).delete(f'/api/users/organismes/{pc.org_a.pk}/')
    assert reponse.status_code == 409, reponse.content[:300]
    assert not ecarts(avant, inventaire())


def test_un_site_lie_a_un_plan_valide_ne_se_supprime_pas(db):
    site = SiteFactory()
    referent_site = RoleFactory()
    CorRoleSiteFactory(id_role=referent_site, id_site=site, referent=True, referent_valid=True)
    PlanGestionFactory(statut='valide', sites=[site])
    reponse = _client(referent_site).delete(f'/api/users/sites/{site.slug}/')
    assert reponse.status_code == 409, reponse.content[:300]


def test_un_site_partage_avec_un_autre_organisme_ne_se_supprime_pas(db):
    site = SiteFactory()
    admin_a = AdminOrganismeFactory()
    CorOgSiteFactory(id_site=site, uuid_og=admin_a.id_organisme)
    CorOgSiteFactory(id_site=site, uuid_og=OrganismeFactory())
    reponse = _client(admin_a).delete(f'/api/users/sites/{site.slug}/')
    assert reponse.status_code == 409, reponse.content[:300]
