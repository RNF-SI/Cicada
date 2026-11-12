"""Filet « perte de données » — famille A : l'aller-retour à l'identique.

Relire une ressource puis la renvoyer telle quelle (``GET`` puis ``PATCH`` ou
``PUT`` du même corps) ne doit rien perdre. C'est le geste « enregistrer sans
rien changer » de l'interface ; il effaçait tout le suivi d'une action
(programmation supprimée puis recréée, réalisations parties en cascade).

Une écriture refusée (400) ne perd rien non plus : seul compte l'inventaire.
"""
import pytest

from tests.integrite.socle import construire_plan_complet, ecarts, inventaire

pytestmark = [pytest.mark.django_db, pytest.mark.integration]


@pytest.fixture
def pc():
    return construire_plan_complet()


def _aller_retour(api_client, utilisateur, url, methode):
    api_client.force_authenticate(user=utilisateur)
    lu = api_client.get(url)
    assert lu.status_code == 200, (url, lu.status_code, lu.content[:300])
    avant = inventaire()
    envoi = getattr(api_client, methode)(url, lu.json(), format='json')
    apres = inventaire()
    return envoi, ecarts(avant, apres)


RESSOURCES = {
    'action annuelle': lambda pc: f'/api/plans/operations/{pc.action.pk}/',
    'action globale': lambda pc: f'/api/plans/operations/{pc.action_globale.pk}/',
    'plan': lambda pc: f'/api/plans/plans/{pc.plan.pk}/',
    'enjeu': lambda pc: f'/api/plans/enjeux/{pc.metrique.id_indicateur.id_ne.id_olt.id_enjeu_id}/',
    'indicateur': lambda pc: f'/api/plans/indicateurs/{pc.metrique.id_indicateur_id}/',
    'métrique': lambda pc: f'/api/plans/metriques/{pc.metrique.pk}/',
    'poste': lambda pc: f'/api/plans/postes/{pc.poste.pk}/',
    'financeur': lambda pc: f'/api/plans/financeurs/{pc.financeur.pk}/',
    'suivi-inventaire': lambda pc: f'/api/inventaires/suivis/{pc.suivi.pk}/',
}


@pytest.mark.parametrize('methode', ['patch', 'put'])
@pytest.mark.parametrize('ressource', list(RESSOURCES))
def test_enregistrer_sans_rien_changer_ne_perd_rien(api_client, pc, ressource, methode):
    envoi, differences = _aller_retour(api_client, pc.admin, RESSOURCES[ressource](pc), methode)
    assert envoi.status_code in (200, 400, 405), (envoi.status_code, envoi.content[:500])
    assert not differences, f"{ressource} ({methode}, {envoi.status_code}) : " + " | ".join(differences)


def test_enregistrer_l_action_garde_son_suivi(api_client, pc):
    """Le cas observé : 4 années de suivi saisies, 0 après un enregistrement."""
    from apps.plans.models_operations import RealisationOperationAnnee
    suivis = RealisationOperationAnnee.objects.filter(
        id_operation_annee__id_operation=pc.action).count()
    assert suivis == 2
    envoi, differences = _aller_retour(
        api_client, pc.admin, f'/api/plans/operations/{pc.action.pk}/', 'patch')
    assert envoi.status_code == 200, envoi.content[:500]
    assert RealisationOperationAnnee.objects.filter(
        id_operation_annee__id_operation=pc.action).count() == suivis
    assert not differences, differences
