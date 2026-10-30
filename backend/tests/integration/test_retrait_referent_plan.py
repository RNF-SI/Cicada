"""
#789 — Un référent du plan doit toujours pouvoir être retiré.

Un utilisateur est référent d'un plan par la relation ``PlanGestion.referents``
ou par une ligne ``CorRolePlan(referent=True)``. Plusieurs chemins n'écrivaient
que la première : le retrait (``remove_member``), qui exigeait la seconde,
répondait « Cet utilisateur n'est pas membre de ce plan ». Les deux sont
désormais tenues ensemble (signaux), et le retrait accepte l'une ou l'autre.
"""
import importlib

import pytest
from django.apps import apps as django_apps
from rest_framework import status
from rest_framework.test import APIClient

from apps.plans.models import CorRolePlan, PlanGestion
from tests.factories.plans import PlanGestionFactory, PlanGestionValideFactory
from tests.factories.users import (
    CorRoleSiteFactory, ReferentFactory, RoleFactory, SiteFactory, SuperAdminFactory,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    client = APIClient()
    client.force_authenticate(user=SuperAdminFactory())
    return client


def _retirer(client, plan, user):
    return client.delete(f'/api/plans/plans/{plan.id_pg}/remove_member/?user_id={user.id_role}')


def _assert_retire(plan, user):
    assert not plan.referents.filter(pk=user.pk).exists()
    assert not CorRolePlan.objects.filter(id_role=user, plan_de_gestion=plan).exists()


class TestRetraitReferent:
    def test_referent_par_la_seule_relation(self, admin_client):
        """Ligne CorRolePlan absente (données antérieures) : le retrait passe quand même."""
        plan = PlanGestionFactory()
        user = RoleFactory()
        # Écriture directe de la table de liaison : aucun signal, comme les
        # données enregistrées avant la correction.
        PlanGestion.referents.through.objects.create(plangestion=plan, role=user)
        assert not CorRolePlan.objects.filter(id_role=user, plan_de_gestion=plan).exists()

        response = _retirer(admin_client, plan, user)

        assert response.status_code == status.HTTP_200_OK, response.data
        _assert_retire(plan, user)

    def test_ni_referent_ni_membre(self, admin_client):
        plan = PlanGestionFactory()
        response = _retirer(admin_client, plan, RoleFactory())
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_createur_du_plan(self):
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
        client = APIClient()
        client.force_authenticate(user=referent)
        response = client.post('/api/plans/plans/', {
            'nom': 'Plan #789', 'statut': 'draft', 'annee_debut': 2026, 'annee_fin': 2036,
            'rang': 1, 'ct88': False, 'sites_ids': [site.id_site],
        })
        assert response.status_code == status.HTTP_201_CREATED, response.data
        plan = PlanGestion.objects.get(nom='Plan #789')
        assert CorRolePlan.objects.get(id_role=referent, plan_de_gestion=plan).referent is True

        admin = APIClient()
        admin.force_authenticate(user=SuperAdminFactory())
        assert _retirer(admin, plan, referent).status_code == status.HTTP_200_OK
        _assert_retire(plan, referent)

    def test_referents_ids_du_formulaire(self, admin_client):
        plan = PlanGestionFactory()
        user = RoleFactory()
        response = admin_client.patch(
            f'/api/plans/plans/{plan.id_pg}/', {'referents_ids': [user.id_role]}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        assert CorRolePlan.objects.get(id_role=user, plan_de_gestion=plan).referent is True

        assert _retirer(admin_client, plan, user).status_code == status.HTTP_200_OK
        _assert_retire(plan, user)

    def test_referent_copie_par_duplication(self, admin_client):
        plan = PlanGestionValideFactory()
        user = RoleFactory()
        plan.referents.add(user)

        response = admin_client.post(f'/api/plans/plans/{plan.id_pg}/duplicate/', {
            'copy_sites': False, 'copy_referents': True,
            'copy_fichiers': False, 'copy_enjeux': False, 'copy_sub_elements': False,
        }, format='json')
        assert response.status_code in (status.HTTP_200_OK, status.HTTP_201_CREATED), response.data
        copie = PlanGestion.objects.exclude(pk=plan.pk).get(plan_parent=plan)
        assert CorRolePlan.objects.get(id_role=user, plan_de_gestion=copie).referent is True

        assert _retirer(admin_client, copie, user).status_code == status.HTTP_200_OK
        _assert_retire(copie, user)


class TestSynchronisation:
    def test_ligne_membre_referent_ajoute_a_la_relation(self):
        plan = PlanGestionFactory()
        user = RoleFactory()
        CorRolePlan.objects.create(id_role=user, plan_de_gestion=plan, referent=True)
        assert plan.referents.filter(pk=user.pk).exists()

    def test_retrait_du_role_garde_le_membre(self, admin_client):
        plan = PlanGestionFactory()
        user = RoleFactory()
        plan.referents.add(user)

        response = admin_client.delete(
            f'/api/plans/plans/{plan.id_pg}/remove_referent/?referent_id={user.id_role}'
        )
        assert response.status_code == status.HTTP_200_OK
        assert not plan.referents.filter(pk=user.pk).exists()
        assert CorRolePlan.objects.get(id_role=user, plan_de_gestion=plan).referent is False

    def test_rattrapage_des_donnees_existantes(self):
        """La migration de données réaligne les deux écritures."""
        plan = PlanGestionFactory()
        seul_m2m, seule_ligne = RoleFactory(), RoleFactory()
        PlanGestion.referents.through.objects.create(plangestion=plan, role=seul_m2m)
        CorRolePlan.objects.bulk_create([
            CorRolePlan(id_role=seule_ligne, plan_de_gestion=plan, referent=True),
        ])

        migration = importlib.import_module('apps.plans.migrations.0144_referents_lignes_membres')
        migration.aligner_referents(django_apps, None)

        assert CorRolePlan.objects.get(id_role=seul_m2m, plan_de_gestion=plan).referent is True
        assert plan.referents.filter(pk=seule_ligne.pk).exists()
