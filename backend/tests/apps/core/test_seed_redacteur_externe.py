"""
Jeu d'essai : un rédacteur externe recettable sans manipulation (#718).

Le jeu d'essai doit fournir un bureau d'étude, son rédacteur externe (#700),
un plan déjà rattaché (son organisme y est rédacteur, #714) et une demande
d'accès en saisie en attente sur un plan d'un autre organisme.
"""
import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.core.management.commands.seeders.organismes_seeder import BUREAU_ETUDE_NOM
from apps.core.management.commands.seeders.plans_seeder import NOM_PLAN_REDACTION_EXTERNE
from apps.core.management.commands.seeders.users_seeder import REDACTEUR_EXTERNE_EMAIL
from apps.notifications.models import ValidationRequest
from apps.plans.access import accessible_plan_ids, user_can_access_suivi
from apps.plans.models import PlanGestion
from apps.users.models import BibOrganismes, Role

pytestmark = [pytest.mark.django_db]


def _seed():
    call_command('seed_testdata', only='users,plans,validation_requests', verbosity=0)


def test_redacteur_externe_et_son_plan():
    _seed()

    bureau = BibOrganismes.objects.get(nom_organisme=BUREAU_ETUDE_NOM)
    assert not bureau.corogsite_set.exists()  # organisme indépendant, sans site

    redacteur = Role.objects.get(email=REDACTEUR_EXTERNE_EMAIL)
    assert redacteur.role_level == 'redacteur'
    assert redacteur.id_organisme == bureau
    assert redacteur.check_password('Test123!')

    plan = PlanGestion.objects.get(nom=NOM_PLAN_REDACTION_EXTERNE)
    assert plan.statut == 'draft'
    assert plan.referents.filter(pk=redacteur.pk).exists()
    assert plan.organismes_redacteurs.filter(uuid_og=bureau).exists()

    # « Mes plans » : le seul plan rattaché, sans les suivis.
    assert list(accessible_plan_ids(redacteur).values_list('id_pg', flat=True)) == [plan.pk]
    assert not user_can_access_suivi(redacteur, plan)

    demande = ValidationRequest.objects.get(
        requester=redacteur, request_type='plan_access', status='pending')
    assert demande.request_as_referent is True
    assert demande.target_plan.nom == 'Plan de gestion 2022-2032 - Grand-Voyeux'

    # L'admin de l'OG du plan visé (CEN AURA) la voit parmi ses validations.
    client = APIClient()
    client.force_authenticate(Role.objects.get(email='admin.cen@test.fr'))
    response = client.get('/api/validations/', {'status': 'pending', 'page_size': 200})
    assert response.status_code == 200
    resultats = response.data['results'] if 'results' in response.data else response.data
    assert demande.pk in [d['id'] for d in resultats]


def test_idempotent_et_reset():
    _seed()
    _seed()
    assert Role.objects.filter(email=REDACTEUR_EXTERNE_EMAIL).count() == 1
    assert PlanGestion.objects.filter(nom=NOM_PLAN_REDACTION_EXTERNE).count() == 1
    assert ValidationRequest.objects.filter(requester__email=REDACTEUR_EXTERNE_EMAIL).count() == 1

    call_command('seed_testdata', reset=True, verbosity=0)
    assert not Role.objects.filter(email=REDACTEUR_EXTERNE_EMAIL).exists()
    assert not PlanGestion.objects.filter(nom=NOM_PLAN_REDACTION_EXTERNE).exists()
    assert not BibOrganismes.objects.filter(nom_organisme=BUREAU_ETUDE_NOM).exists()
