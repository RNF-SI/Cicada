"""
Jeu d'essai : les plans réalistes portent les fonctionnalités récentes.

``PlansCompletsSeeder`` met Camargue, Aiguilles Rouges, Vercors-Écrins… au
niveau des derniers chantiers — financeurs (#790), types complémentaires
(#792), planification annuelle ajustée (#794), appariements (#770) — et les
seeders de comptes, notifications et journal suivent (#771, #706, #751, #769).
Le seed est relancé deux fois : il doit rester idempotent.
"""
from datetime import date

import pytest
from django.core.management import call_command

from apps.core.models import ActivityLog
from apps.notifications.models import Notification
from apps.plans.financeurs import bilan_financeurs
from apps.plans.models_operations import (
    CorOperationTypeAction, FinanceOperation, Operation, RealisationFinanceur,
    RealisationOperationAnnee,
)
from apps.plans.models_planification import AjustementAnnuel
from apps.plans.models_referentiel import AppariementTypeAction
from apps.users.models import Role

pytestmark = [pytest.mark.django_db]


def _seed():
    call_command('import_nomenclatures', verbosity=0)
    call_command('seed_testdata', verbosity=0)


def _op(code):
    return Operation.objects.get(code_operation=code)


def test_plans_realistes_complets_et_idempotents():
    _seed()
    compte = {
        'ajustements': AjustementAnnuel.objects.count(),
        'complementaires': CorOperationTypeAction.objects.count(),
        'realise_financeurs': RealisationFinanceur.objects.count(),
        'appariements': AppariementTypeAction.objects.count(),
        'journal': ActivityLog.objects.filter(entity_type='instance').count(),
    }
    _seed()
    assert compte == {
        'ajustements': AjustementAnnuel.objects.count(),
        'complementaires': CorOperationTypeAction.objects.count(),
        'realise_financeurs': RealisationFinanceur.objects.count(),
        'appariements': AppariementTypeAction.objects.count(),
        'journal': ActivityLog.objects.filter(entity_type='instance').count(),
    }

    annee = date.today().year

    # #790 — montants prévus et réalisés ; écart au budget ; catégorie libre ;
    # financeur non prévu ; Brouage sans montants (facultatifs).
    assert bilan_financeurs(_op('AR-PR01'))['ecart_budget'] is True
    assert not bilan_financeurs(_op('CAM-SE01'))['ecart_budget']
    assert FinanceOperation.objects.filter(
        id_operation=_op('CAM-SE02'), id_financeur__categorie_libre='Mécénat').exists()
    assert RealisationFinanceur.objects.filter(
        id_realisation_operation_annee__id_operation_annee__id_operation=_op('CAM-IP02'),
        id_financeur__nom__startswith='Commune').exists()
    assert not FinanceOperation.objects.filter(
        id_operation__code_operation__startswith='BRG-', montant__isnull=False).exists()
    assert FinanceOperation.objects.filter(
        id_operation__code_operation__startswith='SCA-', montant__isnull=False).exists()

    # #792 — jamais sur une action CS (un complémentaire CS exigerait un suivi).
    complementaires = CorOperationTypeAction.objects.filter(
        id_operation__code_operation__regex=r'^(CAM|AR|VER|REM|SCA|BRG)-')
    assert complementaires.exists()
    assert not complementaires.filter(id_operation__id_type_action__mnemonique__startswith='CS').exists()

    # #794 — chaque statut de l'année en cours, et des actions encore à revoir.
    def ajust(code, a=annee):
        return AjustementAnnuel.objects.get(id_operation__code_operation=code, annee=a)

    assert ajust('CAM-SE01').statut == 'planifiee' and ajust('CAM-SE01').date_revue
    assert ajust('CAM-SE02').financeurs.exists()
    assert ajust('CAM-GE01').statut == 'non_prevue'
    assert ajust('CAM-IP01').statut == 'reportee' and ajust('CAM-IP01').annee_report == annee + 1
    assert ajust('CAM-IP01', annee + 1).report_de == annee
    assert ajust('AR-CC01').statut == 'planifiee' and ajust('AR-CC01').annee_report == annee + 1
    assert not AjustementAnnuel.objects.filter(id_operation__code_operation='CAM-IP02').exists()
    # Une année reportée ne porte que le niveau « Reporté », une année non
    # prévue aucun réalisé.
    reel = RealisationOperationAnnee.objects.get(
        id_operation_annee__id_operation=_op('CAM-IP01'), id_operation_annee__annee=annee)
    assert reel.id_niveau_realisation.mnemonique == 'REPORTE'
    assert not RealisationOperationAnnee.objects.filter(
        id_operation_annee__id_operation=_op('CAM-GE01'), id_operation_annee__annee=annee).exists()

    # #770, #771, notifications et journal de l'instance.
    assert AppariementTypeAction.objects.filter(organisme__nom_organisme__icontains='CEN').exists()
    assert Role.objects.get(email='admin.rnf@test.fr').derniere_activite is not None
    assert Role.objects.get(email='test@example.com').derniere_activite is None
    for type_ in ('plan_csrpn_transition', 'user_first_login', 'referentiel_actions',
                  'referentiel_actions_suivi'):
        assert Notification.objects.filter(notification_type=type_).exists(), type_
    assert ActivityLog.objects.filter(entity_type='instance', visibility='system').exists()
