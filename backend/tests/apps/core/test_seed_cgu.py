"""
Jeu d'essai : les comptes de test ont accepté la version en vigueur des CGU (#746).

Sur une base neuve (CI), la configuration de l'instance n'existe pas encore au
moment du seed. Créée ensuite par la première requête, elle datait ses CGU
d'après les comptes : chacun devait les accepter, et la fenêtre d'acceptation
couvrait chaque page des tests E2E.
"""
import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.core.models import SiteConfiguration
from apps.users.models import Role

pytestmark = [pytest.mark.django_db]


def test_base_neuve_seuls_les_comptes_prevus_doivent_accepter_les_cgu():
    SiteConfiguration.objects.all().delete()

    call_command('seed_testdata', only='users', verbosity=0)

    a_accepter = {u.email for u in Role.objects.filter(email__endswith='@test.fr')
                  if u.doit_accepter_cgu()}
    assert a_accepter == set()
    assert Role.objects.get(email='test@example.com').doit_accepter_cgu()

    client = APIClient()
    client.force_authenticate(Role.objects.get(email='admin@test.fr'))
    assert client.get('/api/auth/me/').json()['cgu_a_accepter'] is False


def test_un_nouveau_texte_redemande_l_acceptation():
    call_command('seed_testdata', only='users', verbosity=0)
    config = SiteConfiguration.get_instance()

    admin = Role.objects.get(email='admin@test.fr')
    config.cgu_version = admin.cgu_acceptees_le.replace(year=admin.cgu_acceptees_le.year + 1)
    config.save()

    admin.refresh_from_db()
    assert admin.doit_accepter_cgu()


def test_le_seed_indexe_les_plans_valides_pour_l_exploration():
    """Signaux coupés pendant le seed : sans réindexation, l'exploration d'une
    base neuve ne trouvait aucun contenu."""
    from apps.plans.models import PlanGestion
    from apps.search.indexing import INDEXED_STATUSES
    from apps.search.models import ContenuIndexe

    call_command('import_nomenclatures', verbosity=0)
    call_command('seed_testdata', only='ventilation_plans', verbosity=0)

    indexables = PlanGestion.objects.filter(statut__in=INDEXED_STATUSES)
    assert indexables.exists()
    assert ContenuIndexe.objects.exists()
    assert set(ContenuIndexe.objects.values_list('id_pg', flat=True).distinct()) <= set(
        indexables.values_list('pk', flat=True))
