"""Filet « perte de données » — famille E : le canari de confidentialité.

Promesse faite aux structures : budget, financement, RH, mesures, réalisations
et personnes ne sortent jamais vers le hub, ni vers un lecteur d'exploration
d'un autre organisme. Les tests par **nom de clé** ont laissé passer une clé
nouvelle (``operation_annee_globale``, #735). Ici, chaque champ sensible du plan
complet reçoit une **valeur repère**, et l'on cherche ces valeurs n'importe où
dans ce qui sort : une clé nouvelle qui transporte une donnée sensible est
attrapée sans que personne ait pensé à la nommer.
"""
import json
from decimal import Decimal

import pytest
from rest_framework.renderers import JSONRenderer
from rest_framework.test import APIClient

from apps.plans.models_operations import (
    FinanceOperation, OperationAnnee, OperationAnneeOrganisme, OperationAnneeRH,
    RealisationFinanceur, RealisationOperationAnnee, RealisationOperationAnneeOrganisme,
    RealisationOperationAnneeRH,
)
from tests.factories.users import RoleFactory
from tests.integrite.socle import construire_plan_complet

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

MONTANT = Decimal('987654.32')
JOURS = Decimal('7777.00')
# Assez distinctifs pour ne jamais apparaître par hasard (coordonnées, identifiants).
REPERES = ('987654.32', '7777.00', 'canari')


def _semer(pc):
    """Valeurs repères dans chaque champ sensible du plan complet."""
    OperationAnnee.tous.filter(id_operation__in=[pc.action, pc.action_globale]).update(
        budget=MONTANT, etp=JOURS, budget_fonctionnement=MONTANT,
        autre_cout_commentaire='Canari commentaire budget')
    OperationAnneeOrganisme.objects.filter(
        id_operation_annee__id_operation__in=[pc.action, pc.action_globale]).update(
        cout_stage=MONTANT, cout_prestataire=MONTANT, etp=JOURS,
        autre_cout_commentaire='Canari commentaire organisme')
    OperationAnneeRH.objects.update(jours=JOURS)
    FinanceOperation.objects.update(montant=MONTANT)
    RealisationOperationAnnee.objects.update(
        budget_realise=MONTANT, etp_realise=JOURS, commentaires='Canari commentaire de suivi')
    RealisationOperationAnneeOrganisme.objects.update(
        budget_fonctionnement_realise=MONTANT, etp_realise=JOURS)
    RealisationOperationAnneeRH.objects.update(jours=JOURS)
    RealisationFinanceur.objects.update(montant=MONTANT)
    pc.poste.nom_local, pc.poste.cout_jour = 'Canari poste', MONTANT
    pc.poste.save()
    pc.financeur.nom = 'Canari financeur'
    pc.financeur.save()
    pc.metrique.mesures.update(valeur='987654.32', commentaire='Canari mesure')
    pc.suivi.protocoles.update(nb_etp_cycle=JOURS)
    pc.referent.nom_role, pc.referent.email = 'Canari-Personne', 'canari@personne.fr'
    pc.referent.save()


@pytest.fixture
def pc():
    pc = construire_plan_complet(statut='valide')
    _semer(pc)
    return pc


def _chemins(noeud, chemin=''):
    if isinstance(noeud, dict):
        for cle, valeur in noeud.items():
            yield from _chemins(valeur, f'{chemin}.{cle}')
    elif isinstance(noeud, list):
        for valeur in noeud:
            yield from _chemins(valeur, f'{chemin}[]')
    elif any(repere in str(noeud).lower() for repere in REPERES):
        yield f'{chemin} = {str(noeud)[:40]}'


def _fuites(donnees):
    """Chemins JSON où une valeur repère apparaît (vide si rien ne sort)."""
    return sorted(set(_chemins(json.loads(JSONRenderer().render(donnees)))))


def _etranger():
    client = APIClient()
    client.force_authenticate(RoleFactory())
    return client


def test_les_reperes_sont_bien_poses(pc):
    """Sans ce garde-fou, un canari qui ne serait écrit nulle part rendrait le test muet."""
    from apps.plans.serializers_operations import OperationSerializer
    assert _fuites(OperationSerializer(pc.action_globale).data)


@pytest.mark.parametrize('url', [
    '/api/plans/plans/by-slug/{slug}/',
    '/api/plans/plans/{plan}/',
    '/api/plans/enjeux/by-plan/{plan}/',
    '/api/plans/operations/by-plan/{plan}/',
    '/api/plans/operations/{action}/',
    '/api/plans/operations/{globale}/',
    '/api/plans/indicateurs/{indicateur}/',
])
def test_rien_ne_sort_vers_un_lecteur_d_exploration(pc, url):
    url = url.format(slug=pc.plan.slug, plan=pc.plan.pk, action=pc.action.pk,
                     globale=pc.action_globale.pk, indicateur=pc.metrique.id_indicateur_id)
    reponse = _etranger().get(url)
    assert reponse.status_code == 200, (url, reponse.status_code)
    assert reponse.data.get('acces_exploration') is True, url
    assert not _fuites(reponse.data), f'{url} laisse sortir {_fuites(reponse.data)}'


def test_rien_ne_sort_dans_les_ecrans_publies_au_hub(pc):
    from apps.search.ecrans import ecrans_du_plan
    assert not _fuites(ecrans_du_plan(pc.plan))


def _plan_publie(pc):
    """Le plan tel que ``push_federation`` le charge."""
    from apps.search.push import plans_a_publier
    from apps.search.serializers import prefetch_sites
    return plans_a_publier().prefetch_related(prefetch_sites()).get(pk=pc.plan.pk)


def test_rien_ne_sort_dans_la_fiche_publique(pc):
    from apps.search.fiche import construire_fiche
    from apps.search.serializers_fiche import FichePubliqueSerializer
    assert not _fuites(FichePubliqueSerializer(construire_fiche(_plan_publie(pc))).data)


def test_rien_ne_sort_dans_la_charge_publiee(pc):
    """Tout ce qui part vers le hub : bandeau, index, fiche, écrans."""
    from apps.search.indexing import index_plan
    from apps.search.push import charge_utile
    index_plan(pc.plan)
    charge = charge_utile(_plan_publie(pc))
    assert charge['contenus'], "l'index du plan est vide : le test ne verrait rien"
    assert not _fuites(charge)
