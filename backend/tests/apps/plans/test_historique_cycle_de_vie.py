"""Chaque geste du cycle de vie d'un plan laisse une trace dans l'historique (#837).

Les vues appelaient `ActivityService.log()`, qui n'existe pas : l'erreur était
avalée par un `except Exception: pass`, et les gestes qui ne modifient aucun
champ suivi par le signal (étapes CSRPN, validations administratives,
révision, retrait d'extension) ne laissaient aucune trace.
"""
from datetime import date

import pytest
from rest_framework.test import APIClient

from apps.core.models import ActivityLog, Nomenclature, TypeNomenclature
from apps.plans.models import PlanGestion
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import SiteFactory, SuperAdminFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


def _site_rnn():
    ntype, _ = TypeNomenclature.objects.get_or_create(
        mnemonique='TYPE_SITE', defaults={'label': 'Type de site'})
    rnn, _ = Nomenclature.objects.get_or_create(
        id_type=ntype, mnemonique='RNN', defaults={'label': 'RNN', 'cd_nomenclature': 'RNN'})
    site = SiteFactory()
    site.id_type_site = rnn
    site.save(update_fields=['id_type_site'])
    return site


@pytest.fixture
def client_admin(db):
    ntype, _ = TypeNomenclature.objects.get_or_create(
        mnemonique='TYPE_DOCUMENT_PLAN', defaults={'label': 'Type de document plan'})
    for mnemonique in ('EVAL_MI_PARCOURS', 'PLAN_REVISE'):
        Nomenclature.objects.get_or_create(
            mnemonique=mnemonique,
            defaults={'id_type': ntype, 'label': mnemonique, 'cd_nomenclature': mnemonique[:6]})
    client = APIClient()
    client.force_authenticate(SuperAdminFactory())
    return client


def _plan(**champs):
    annee = date.today().year
    valeurs = dict(statut='valide', rang=1, annee_debut=annee - 5, annee_fin=annee,
                   sites=[_site_rnn()])
    valeurs.update(champs)
    return PlanGestionFactory(**valeurs)


def _journal(plan):
    return list(ActivityLog.objects.filter(entity_type='plan', entity_id=plan.pk)
                .values_list('action', 'description'))


@pytest.mark.parametrize('chemin, corps, champs, attendu', [
    ('csrpn-step', {'step': 'avis_csrpn'}, {'statut': 'draft'}, 'CSRPN'),
    ('admin-validation', {'key': 'comite_consultatif', 'date': '2026-04-10'}, {}, 'Validation administrative'),
    ('start-revision', {}, {}, 'révision'),
    ('end-revision', {}, {'en_revision': True}, 'Révision arrêtée'),
    ('remove-extension', {}, {'annees_extension': 1}, 'Extension'),
], ids=['csrpn', 'validation-administrative', 'debut-revision', 'fin-revision', 'retrait-extension'])
def test_le_geste_est_journalise(client_admin, chemin, corps, champs, attendu):
    plan = _plan(**champs)
    deja = set(ActivityLog.objects.values_list('pk', flat=True))

    reponse = client_admin.post(f'/api/plans/plans/{plan.pk}/{chemin}/', corps, format='json')

    assert reponse.status_code == 200, reponse.content
    nouvelles = (ActivityLog.objects.filter(entity_type='plan', entity_id=plan.pk)
                 .exclude(pk__in=deja).values_list('description', flat=True))
    assert any(attendu.lower() in d.lower() for d in nouvelles), list(nouvelles)


@pytest.mark.parametrize('chemin, corps, attendu', [
    ('extend-duration', {'years': 1}, 'version étendue'),
    ('create-next-rang', {}, 'Brouillon du rang 2'),
    ('create-evaluation', {}, 'Évaluation mi-parcours créée depuis'),
], ids=['prolongation', 'rang-suivant', 'evaluation'])
def test_la_creation_d_une_version_est_journalisee_une_fois(client_admin, chemin, corps, attendu):
    plan = _plan()

    reponse = client_admin.post(f'/api/plans/plans/{plan.pk}/{chemin}/', corps, format='json')

    assert reponse.status_code == 201, reponse.content
    copie = PlanGestion.objects.get(pk=reponse.json()['id_pg'])
    creations = [d for a, d in _journal(copie) if a == 'create']
    assert len(creations) == 1, creations
    assert attendu.lower() in creations[0].lower()
    assert plan.nom in creations[0]


def test_le_changement_de_statut_n_est_journalise_qu_une_fois(client_admin):
    plan = _plan(statut='draft')
    client_admin.post(f'/api/plans/plans/{plan.pk}/change-status/', {'new_status': 'valide'}, format='json')
    assert [a for a, _ in _journal(plan)].count('status_change') == 1
