"""
#788 — Catégories d'action réserve (CT88) remises en état après un passage
Gestref appliqué avant la correction.

Avant #788, un passage de version traitait `CATEGORIE_ACTION_RESERVE` comme
les catégories du référentiel : il désactivait MS, EI, CI, PR, PA, CC, donnait
leur libellé Gestref à CS, IP, SP, créait des catégories à partir de l'id
500 000 et changeait la catégorie des actions. `reparer()` défait cela :

- les 9 catégories CT88 reprennent leur libellé d'origine (fichier SQL des
  nomenclatures) et sont réactivées ; celles créées par un passage sont
  désactivées (jamais supprimées : le journal y renvoie) ;
- chaque action du journal reprend sa catégorie d'avant le passage
  (`ancienne_categorie`), sauf si elle a été changée depuis à la main ;
- les lignes de la version en service ne désignent plus de catégorie.

Ce qui n'a laissé aucune trace est listé, pas deviné : actions portant une
catégorie de passage hors journal, et actions sans type dont la catégorie a pu
être effacée (la boucle d'avant #788 ne journalisait pas). Simulation par défaut.
"""
import re
from collections import Counter
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.core.models import Nomenclature

from . import referentiel_actions as ref
from .models_referentiel import PassageReferentielObjet, VersionReferentielActions

FICHIER_NOMENCLATURES = (
    Path(__file__).resolve().parents[2] / 'nomenclatures_data' / 'nomenclatures_inserts.sql'
)
SOURCE_CT88 = 'CICADA/CT88'

_VALEUR = r"'((?:[^']|'')*)'"
_LIGNE = re.compile(
    rf"VALUES \((\d+), \d+, {_VALEUR}, {_VALEUR}, {_VALEUR}, {_VALEUR}, '{SOURCE_CT88}', "
    rf"{_VALEUR}, {_VALEUR},")


def categories_ct88() -> list[dict]:
    """Les 9 catégories des réserves, telles que livrées par le fichier SQL."""
    out = []
    for ligne in FICHIER_NOMENCLATURES.read_text(encoding='utf-8').splitlines():
        m = _LIGNE.search(ligne)
        if m:
            pk, code, _mnemo, label, definition, _statut, hierarchy = m.groups()
            out.append({'id': int(pk), 'code': code, 'label': label.replace("''", "'"),
                        'definition': definition.replace("''", "'"), 'hierarchy': hierarchy})
    return out


def _est_de_passage(categorie) -> bool:
    return categorie is not None and categorie.pk >= ref.REFERENTIEL_ID_BASE


def _a_restaurer(op, obj) -> bool:
    """La catégorie de l'action est celle qu'un passage (ou l'actualisation
    d'avant #788) lui a donnée, pas un choix fait depuis."""
    actuelle = op.id_categorie_action_reserve
    if actuelle == obj.ancienne_categorie:
        return False
    if actuelle is None or _est_de_passage(actuelle) or actuelle == obj.nouvelle_categorie:
        return True
    # Actualisation par le référent : catégorie déduite du nouveau type.
    code_type = (op.id_type_action.cd_nomenclature or '') if op.id_type_action else ''
    return actuelle.cd_nomenclature == ref.categorie_du_code(code_type)


def reparer(*, appliquer=False) -> dict:
    from .models_operations import Operation

    ct88 = categories_ct88()
    par_id = Nomenclature.objects.in_bulk([c['id'] for c in ct88])
    categories = [c for c in ct88 if c['id'] in par_id and (
        not par_id[c['id']].actif or par_id[c['id']].label != c['label'])]
    absentes = [c['code'] for c in ct88 if c['id'] not in par_id]
    de_passage = list(Nomenclature.objects.filter(
        id_type__mnemonique=ref.CATEGORIE, actif=True,
        id_nomenclature__gte=ref.REFERENTIEL_ID_BASE).order_by('pk'))

    objets = (PassageReferentielObjet.objects
              .filter(operation__isnull=False,
                      passage__cible__referentiel=ref.REFERENTIEL_TYPES_ACTION)
              .select_related('operation__id_categorie_action_reserve',
                              'operation__id_type_action', 'ancienne_categorie',
                              'nouvelle_categorie', 'plan')
              .order_by('operation_id', 'passage_id'))
    # Le premier passage de chaque action donne sa catégorie d'origine.
    premier = {}
    for obj in objets:
        premier.setdefault(obj.operation_id, obj)
    corrections, modifiees = [], 0
    for obj in premier.values():
        if _a_restaurer(obj.operation, obj):
            corrections.append(obj)
        elif obj.operation.id_categorie_action_reserve != obj.ancienne_categorie:
            modifiees += 1

    sans_trace = list(Operation.objects
                      .filter(id_categorie_action_reserve__id_nomenclature__gte=ref.REFERENTIEL_ID_BASE)
                      .exclude(pk__in=premier.keys())
                      .select_related('id_categorie_action_reserve'))
    a_verifier = (Operation.objects.filter(id_type_action__isnull=True,
                                           id_categorie_action_reserve__isnull=True)
                  .exclude(pk__in=premier.keys()).count())

    rapport = {
        'categories_restaurees': [c['code'] for c in categories],
        'categories_absentes': absentes,
        'categories_desactivees': [n.cd_nomenclature for n in de_passage],
        'actions_corrigees': len(corrections),
        'actions_corrigees_par_categorie': dict(Counter(
            (o.ancienne_categorie.cd_nomenclature if o.ancienne_categorie else '(aucune)')
            for o in corrections)),
        'actions_modifiees_depuis': modifiees,
        'actions_sans_trace': [
            {'id': op.pk, 'libelle': op.libelle,
             'categorie': op.id_categorie_action_reserve.cd_nomenclature}
            for op in sans_trace],
        'actions_sans_type_ni_categorie': a_verifier,
    }
    if appliquer:
        _appliquer(ct88, par_id, de_passage, corrections)
    return rapport


@transaction.atomic
def _appliquer(ct88, par_id, de_passage, corrections) -> None:
    for c in ct88:
        if c['id'] in par_id:
            Nomenclature.objects.filter(pk=c['id']).update(
                actif=True, label=c['label'], definition=c['definition'],
                hierarchy=c['hierarchy'], date_maj=timezone.now())
    Nomenclature.objects.filter(pk__in=[n.pk for n in de_passage]).update(
        actif=False, date_maj=timezone.now())
    for obj in corrections:
        # save() : la recherche réindexe l'action.
        obj.operation.id_categorie_action_reserve = obj.ancienne_categorie
        obj.operation.save(update_fields=['id_categorie_action_reserve'])
    # Les versions ne désignent plus de catégorie : leurs catégories deviennent
    # des titres de groupe, et une activation ne touche plus aux CT88.
    for version in VersionReferentielActions.objects.filter(
            referentiel=ref.REFERENTIEL_TYPES_ACTION):
        lignes = []
        for l in version.lignes:
            if l.get('nomenclature') == ref.CATEGORIE:
                if version.code == ref.VERSION_INITIALE:
                    continue
                l = {k: v for k, v in l.items() if k != 'id'} | {'nomenclature': ref.GROUPE}
            lignes.append(l)
        if lignes != version.lignes:
            version.lignes = lignes
            version.save(update_fields=['lignes'])
