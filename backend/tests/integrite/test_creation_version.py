"""Créer une version (prolongation, rang suivant, évaluation) est tout ou rien (#830).

La copie du contenu écrit des centaines de lignes. Interrompue au milieu, elle
laissait un brouillon enfant à moitié copié, sans rien qui le signale — et
`has_draft_child()` refusait ensuite tout nouvel essai.
"""
import pytest
from rest_framework.test import APIClient

from apps.core.models import Nomenclature, TypeNomenclature
from apps.plans.models import PlanGestion
from apps.plans.services import PlanDuplicationService
from tests.integrite.socle import construire_plan_complet, ecarts, inventaire

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture
def types_de_document(db):
    ntype, _ = TypeNomenclature.objects.get_or_create(
        mnemonique='TYPE_DOCUMENT_PLAN', defaults={'label': 'Type de document plan'})
    for mnemonique, code in (('EVAL_MI_PARCOURS', 'EVAL'), ('PLAN_REVISE', 'REVISE')):
        Nomenclature.objects.get_or_create(
            mnemonique=mnemonique,
            defaults={'id_type': ntype, 'label': mnemonique, 'cd_nomenclature': code})


@pytest.fixture
def pc(types_de_document):
    pc = construire_plan_complet(statut='valide')
    # Échéance dans la fenêtre de prolongation ([échéance − 1, + 2]).
    PlanGestion.objects.filter(pk=pc.plan.pk).update(annee_fin=pc.annee)
    pc.plan.refresh_from_db()
    return pc


GESTES = {
    'prolongation': ('extend-duration', {'years': 1}),
    'rang suivant': ('create-next-rang', {}),
    'évaluation': ('create-evaluation', {}),
}


def _creer(pc, geste):
    chemin, corps = GESTES[geste]
    client = APIClient(raise_request_exception=False)
    client.force_authenticate(pc.admin)
    return client.post(f'/api/plans/plans/{pc.plan.pk}/{chemin}/', corps, format='json')


@pytest.mark.parametrize('geste', GESTES)
def test_une_copie_interrompue_ne_laisse_rien(pc, geste, monkeypatch):
    def panne(*args, **kwargs):
        raise RuntimeError('panne au milieu de la copie')

    # Les enjeux sont déjà copiés quand les actions échouent.
    monkeypatch.setattr(PlanDuplicationService, '_copy_suivis_and_operations', panne)
    avant = inventaire()

    reponse = _creer(pc, geste)

    assert reponse.status_code == 500
    assert ecarts(avant, inventaire()) == []
    assert not pc.plan.has_draft_child()


@pytest.mark.parametrize('geste', GESTES)
def test_apres_l_echec_un_nouvel_essai_aboutit(pc, geste, monkeypatch):
    with monkeypatch.context() as m:
        m.setattr(PlanDuplicationService, '_copy_suivis_and_operations',
                  lambda *a, **k: (_ for _ in ()).throw(RuntimeError('panne')))
        assert _creer(pc, geste).status_code == 500

    reponse = _creer(pc, geste)

    assert reponse.status_code == 201, reponse.content
    copie = PlanGestion.objects.get(pk=reponse.json()['id_pg'])
    assert copie.plan_parent_id == pc.plan.pk
    assert copie.enjeux.exists()


def test_creer_version_est_atomique_meme_hors_d_une_vue(pc, monkeypatch):
    monkeypatch.setattr(PlanDuplicationService, '_copy_postes',
                        lambda *a, **k: (_ for _ in ()).throw(RuntimeError('panne')))
    avant = PlanGestion.objects.count()
    with pytest.raises(RuntimeError):
        PlanDuplicationService.creer_version(
            pc.plan, pc.admin, nom='Copie', version=pc.plan.get_next_version())
    assert PlanGestion.objects.count() == avant
