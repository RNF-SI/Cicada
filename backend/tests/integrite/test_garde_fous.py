"""Filet « perte de données » — garde-fous de la programmation, atomicité (famille D)
et commandes dangereuses (famille H)."""
import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.plans.models_operations import Financeur, OperationAnnee, RealisationOperationAnnee
from tests.factories.plans import PlanGestionFactory
from tests.integrite.socle import construire_plan_complet, ecarts, inventaire

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture
def pc():
    return construire_plan_complet()


def _corps(api_client, pc, action=None):
    action = action or pc.action
    api_client.force_authenticate(user=pc.admin)
    url = f'/api/plans/operations/{action.pk}/'
    return url, api_client.get(url).json()


class TestProgrammationEtSuivi:
    def test_retirer_une_annee_suivie_est_refuse(self, api_client, pc):
        url, corps = _corps(api_client, pc)
        corps['operation_annees'] = [
            a for a in corps['operation_annees'] if a['annee'] != pc.annee - 1]
        avant = inventaire()
        reponse = api_client.patch(url, corps, format='json')
        assert reponse.status_code == 400, reponse.content[:300]
        assert 'suivi' in str(reponse.json()).lower()
        assert not ecarts(avant, inventaire())

    def test_retirer_une_annee_sans_suivi_est_permis(self, api_client, pc):
        url, corps = _corps(api_client, pc)
        corps['operation_annees'] = [
            a for a in corps['operation_annees'] if a['annee'] != pc.annee + 1]
        reponse = api_client.patch(url, corps, format='json')
        assert reponse.status_code == 200, reponse.content[:300]
        annees = set(OperationAnnee.objects.filter(
            id_operation=pc.action).values_list('annee', flat=True))
        assert annees == {pc.annee - 1, pc.annee}
        assert RealisationOperationAnnee.objects.filter(
            id_operation_annee__id_operation=pc.action).count() == 2

    def test_retirer_un_organisme_suivi_est_refuse(self, api_client, pc):
        url, corps = _corps(api_client, pc)
        for annee in corps['operation_annees']:
            annee['organismes'] = [
                o for o in annee['organismes'] if o['id_organisme'] != pc.org_b.pk]
        avant = inventaire()
        reponse = api_client.patch(url, corps, format='json')
        assert reponse.status_code == 400, reponse.content[:300]
        assert not ecarts(avant, inventaire())

    def test_modifier_un_montant_prevu_garde_le_suivi(self, api_client, pc):
        url, corps = _corps(api_client, pc)
        for annee in corps['operation_annees']:
            for org in annee['organismes']:
                org['cout_stage'] = '4321.00'
        reponse = api_client.patch(url, corps, format='json')
        assert reponse.status_code == 200, reponse.content[:300]
        assert RealisationOperationAnnee.objects.filter(
            id_operation_annee__id_operation=pc.action).count() == 2
        assert {str(o.cout_stage) for oa in OperationAnnee.objects.filter(
            id_operation=pc.action) for o in oa.organismes.all()} == {'4321.00'}


class TestAtomicite:
    def test_une_erreur_en_fin_d_enregistrement_ne_laisse_rien_a_moitie(self, api_client, pc):
        """La programmation est réécrite, puis les financements échouent : rien ne change."""
        url, corps = _corps(api_client, pc)
        for annee in corps['operation_annees']:
            annee['budget'] = '1.00'
        etranger = Financeur.objects.create(id_pg=PlanGestionFactory(), nom='Autre plan')
        corps['finances'] = [{'id_financeur': etranger.pk, 'montant': '10.00'}]
        avant = inventaire()
        reponse = api_client.patch(url, corps, format='json')
        assert reponse.status_code == 400, reponse.content[:300]
        assert not ecarts(avant, inventaire())


class TestCommandesDangereuses:
    @override_settings(SETTINGS_MODULE='config.settings.production')
    def test_seed_testdata_refuse_en_production(self):
        with pytest.raises(CommandError, match='production'):
            call_command('seed_testdata', '--reset', verbosity=0)

    @override_settings(SETTINGS_MODULE='config.settings.production')
    def test_seed_testdata_simulation_permise_en_production(self):
        call_command('seed_testdata', '--reset', '--dry-run', verbosity=0)


class TestJeuDEssai:
    def test_le_jeu_d_essai_se_supprime_puis_se_recree(self):
        """`--reset` (lancé par l'E2E avant chaque série) doit passer les
        protections de suppression : organismes protégés tant qu'ils portent du
        budget (PROTECT), donc supprimés après les plans."""
        from apps.plans.models import PlanGestion
        from apps.users.models import BibOrganismes
        call_command('import_nomenclatures', verbosity=0)
        call_command('seed_testdata', '--only=ventilation_plans', verbosity=0)
        assert PlanGestion.objects.exists()
        call_command('seed_testdata', '--reset', verbosity=0)
        assert not PlanGestion.objects.exists()
        assert not BibOrganismes.objects.filter(nom_organisme='Réserves Naturelles de France').exists()
        call_command('seed_testdata', '--only=ventilation_plans', verbosity=0)
        assert PlanGestion.objects.exists()
