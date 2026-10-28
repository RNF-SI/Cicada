"""
Passage d'une version du référentiel des types d'action à une autre (#751).

Le passage est **générique** : codification Eden 62 → Gestref V1 aujourd'hui,
Gestref V1 → V2 demain. Une version est décrite par un dossier de
`nomenclatures_data/referentiels_types_action/` (voir son README) ; la version
de départ des instances existantes, `EDEN62`, est relevée en base au premier
passage.

Rien ne se passe au démarrage d'une instance : seul `manage.py
passage_types_action` applique un passage, et il commence par une simulation.

Règles :

- correspondance **sûre** ou **probable** → l'action (ou le suivi) prend le
  nouveau type ; la catégorie suit le préfixe du nouveau code (CS.1.1 → CS) ;
- correspondance **à arbitrer** (ou code absent de la table) → **cohabitation**
  (#776) : l'objet garde son ancien type et sa catégorie, devient « à
  actualiser », et le référent choisit parmi les équivalents proposés (ou
  ailleurs dans le référentiel) ; les changements automatiques restent
  modifiables, même dans un plan validé ou archivé ;
- une action qui devient CS sans suivi en reçoit un (nouveau ou existant) ;
- les types et catégories de l'ancienne version sont désactivés (pas
  supprimés : l'historique et l'annulation en ont besoin) ;
- chaque référent d'un plan touché reçoit **une** notification par passage —
  jamais une par action — qui renvoie à la page « Actions à actualiser » ; quand
  un autre référent actualise une action, les autres reçoivent une
  notification de suivi regroupée (mise à jour tant qu'elle n'est pas lue) ;
- un passage s'annule : les anciens types et catégories sont restaurés à
  partir du journal (`PassageReferentielObjet`).
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from apps.core.models import Nomenclature, TypeNomenclature

from .models_referentiel import (
    REFERENTIEL_TYPES_ACTION, PassageReferentielActions, PassageReferentielObjet,
    VersionReferentielActions,
)

TYPE_ACTION = 'TYPE_ACTION'
CATEGORIE = 'CATEGORIE_ACTION_RESERVE'
VERSION_INITIALE = 'EDEN62'
LIBELLE_INITIAL = 'Codification unique Eden 62'

DOSSIER_REFERENTIELS = (
    Path(__file__).resolve().parents[2] / 'nomenclatures_data' / 'referentiels_types_action'
)

# Les nomenclatures créées par un passage prennent leur identifiant à partir
# d'ici : `import_nomenclatures` pose des identifiants explicites et fait un
# upsert sur la clé primaire — une ligne tirée de la séquence pourrait être
# écrasée par la prochaine ligne ajoutée au fichier SQL. `--prune` ignore aussi
# cette plage.
REFERENTIEL_ID_BASE = 500_000

CONFIANCES_APPLIQUEES = (
    PassageReferentielObjet.CONFIANCE_SURE,
    PassageReferentielObjet.CONFIANCE_PROBABLE,
)

URL_A_ACTUALISER = '/actions-a-actualiser'


class ReferentielErreur(Exception):
    """Version ou table de correspondance inutilisable (message lisible)."""


# ---------------------------------------------------------------------------
# Lecture d'une version
# ---------------------------------------------------------------------------

@dataclass
class Correspondance:
    nouveau_code: str
    confiance: str
    note: str = ''
    # #776 — équivalents possibles ; le premier est le code proposé.
    options: list = field(default_factory=list)


@dataclass
class DefinitionVersion:
    code: str
    libelle: str
    depuis: str
    categories: list = field(default_factory=list)     # [(code, libelle)]
    types: list = field(default_factory=list)          # [(code, libelle)]
    correspondance: dict = field(default_factory=dict)  # ancien_code → Correspondance
    exclues: list = field(default_factory=list)

    @property
    def codes_types(self) -> set:
        return {c for c, _l in self.types}

    @property
    def codes_categories(self) -> set:
        return {c for c, _l in self.categories}


def categorie_du_code(code: str) -> str:
    """Catégorie d'un code de type : CS.1.1 → CS, IP1.2 → IP."""
    m = re.match(r'[A-Za-z]+', code or '')
    return m.group(0).upper() if m else ''


def _hierarchie(rang_categorie: int, code: str) -> str:
    """Clé de tri : la catégorie dans l'ordre du fichier, puis les numéros
    (CS.1.10 après CS.1.9, ce que l'ordre alphabétique ne donne pas)."""
    nums = [int(n) for n in re.findall(r'\d+', code)]
    return '.'.join([f'{rang_categorie:02d}'] + [f'{n:03d}' for n in nums])


def charger_version(nom: str) -> DefinitionVersion:
    """Lit `<nom>/version.json`, `referentiel.csv` et `correspondance.csv`."""
    dossier = DOSSIER_REFERENTIELS / nom
    if not dossier.is_dir():
        raise ReferentielErreur(f"Version introuvable : {dossier}")
    try:
        meta = json.loads((dossier / 'version.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise ReferentielErreur(f"version.json illisible : {e}") from e
    for cle in ('code', 'libelle', 'depuis'):
        if not meta.get(cle):
            raise ReferentielErreur(f"version.json : « {cle} » manquant")

    exclues = [c.upper() for c in meta.get('exclure_categories', [])]
    definition = DefinitionVersion(code=meta['code'], libelle=meta['libelle'],
                                   depuis=meta['depuis'], exclues=exclues)
    with open(dossier / 'referentiel.csv', encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            code = (row.get('code') or '').strip()
            libelle = ' '.join((row.get('libelle') or '').split())
            if not code:
                continue
            if categorie_du_code(code) in exclues:
                continue
            if '.' in code:
                definition.types.append((code, libelle))
            else:
                definition.categories.append((code.upper(), libelle))
    if not definition.types:
        raise ReferentielErreur("referentiel.csv : aucun type d'action")
    sans_categorie = sorted({categorie_du_code(c) for c in definition.codes_types}
                            - definition.codes_categories)
    if sans_categorie:
        raise ReferentielErreur(
            f"referentiel.csv : catégorie absente pour {', '.join(sans_categorie)}")

    confiances = {c for c, _l in PassageReferentielObjet.CONFIANCES}
    with open(dossier / 'correspondance.csv', encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            ancien = (row.get('ancien_code') or '').strip()
            if not ancien:
                continue
            nouveau = (row.get('nouveau_code') or '').strip()
            confiance = (row.get('confiance') or '').strip()
            note = (row.get('note') or '').strip()
            if confiance not in confiances:
                raise ReferentielErreur(
                    f"correspondance.csv : confiance « {confiance} » inconnue ({ancien})")
            if nouveau and categorie_du_code(nouveau) in exclues:
                # Une catégorie écartée n'existe pas dans cette version : on ne
                # peut que proposer, pas poser.
                confiance = PassageReferentielObjet.CONFIANCE_A_ARBITRER
                note = (note + ' — ' if note else '') + "catégorie écartée de cette version"
                nouveau = ''
            elif nouveau and nouveau not in definition.codes_types:
                raise ReferentielErreur(
                    f"correspondance.csv : « {nouveau} » ({ancien}) absent du référentiel")
            if confiance in CONFIANCES_APPLIQUEES and not nouveau:
                raise ReferentielErreur(
                    f"correspondance.csv : « {ancien} » est {confiance} sans nouveau code")
            options = [nouveau] if nouveau else []
            for code in (row.get('options') or '').split('|'):
                code = code.strip()
                if not code or code in options or categorie_du_code(code) in exclues:
                    continue
                if code not in definition.codes_types:
                    raise ReferentielErreur(
                        f"correspondance.csv : option « {code} » ({ancien}) absente du référentiel")
                options.append(code)
            definition.correspondance[ancien] = Correspondance(nouveau, confiance, note, options)
    return definition


# ---------------------------------------------------------------------------
# Versions en base
# ---------------------------------------------------------------------------

def _ligne(nom: Nomenclature, nomenclature: str) -> dict:
    return {'id': nom.id_nomenclature, 'nomenclature': nomenclature,
            'code': nom.cd_nomenclature or nom.mnemonique or '',
            'libelle': nom.label or '', 'hierarchy': nom.hierarchy or '',
            'definition': nom.definition or ''}


def version_courante() -> VersionReferentielActions | None:
    return VersionReferentielActions.objects.filter(
        referentiel=REFERENTIEL_TYPES_ACTION, courante=True).first()


def _releve_version_initiale() -> VersionReferentielActions:
    """La version en service avant tout passage : types et catégories actifs."""
    lignes = []
    for mnemo in (TYPE_ACTION, CATEGORIE):
        for nom in Nomenclature.objects.filter(id_type__mnemonique=mnemo, actif=True):
            lignes.append(_ligne(nom, mnemo))
    version, _ = VersionReferentielActions.objects.update_or_create(
        code=VERSION_INITIALE,
        defaults={'libelle': LIBELLE_INITIAL, 'lignes': lignes, 'courante': True,
                  'referentiel': REFERENTIEL_TYPES_ACTION},
    )
    return version


def version_de_depart(definition: DefinitionVersion) -> VersionReferentielActions:
    courante = version_courante()
    code_courant = courante.code if courante else VERSION_INITIALE
    if code_courant != definition.depuis:
        raise ReferentielErreur(
            f"{definition.code} part de {definition.depuis}, or la version en service est "
            f"{code_courant}.")
    return courante


def _types_nomenclature():
    types = {t.mnemonique: t for t in TypeNomenclature.objects.filter(
        mnemonique__in=(TYPE_ACTION, CATEGORIE))}
    manquants = {TYPE_ACTION, CATEGORIE} - set(types)
    if manquants:
        raise ReferentielErreur(f"Nomenclatures absentes : {', '.join(sorted(manquants))}")
    return types


def _creer_lignes_version(definition: DefinitionVersion) -> list[dict]:
    """Crée (inactives) ou retrouve les nomenclatures de la version.

    Une ligne de même code est réutilisée — catégorie partagée (CS, IP, SP) ou
    type repris d'une version à la suivante : les actions qui la portent n'ont
    alors rien à changer. Elles ne deviennent actives qu'à l'activation.
    """
    types = _types_nomenclature()
    prochain = max(
        Nomenclature.objects.filter(id_nomenclature__gte=REFERENTIEL_ID_BASE)
        .aggregate(m=Max('id_nomenclature'))['m'] or REFERENTIEL_ID_BASE - 1,
        REFERENTIEL_ID_BASE - 1,
    ) + 1
    rang = {code: i + 1 for i, (code, _l) in enumerate(definition.categories)}
    lignes = []
    entrees = ([(CATEGORIE, c, l) for c, l in definition.categories]
               + [(TYPE_ACTION, c, l) for c, l in definition.types])
    for mnemo, code, libelle in entrees:
        hierarchie = (f'{rang[code]:02d}' if mnemo == CATEGORIE
                      else _hierarchie(rang[categorie_du_code(code)], code))
        nom = (Nomenclature.objects.filter(id_type=types[mnemo], cd_nomenclature=code)
               .order_by('-actif', 'id_nomenclature').first())
        if nom is None:
            nom = Nomenclature.objects.create(
                id_nomenclature=prochain, id_type=types[mnemo], cd_nomenclature=code,
                mnemonique=code, label=libelle, definition=libelle,
                source=definition.code, statut='Validé', hierarchy=hierarchie,
                actif=False, date_ajout=timezone.now(), date_maj=timezone.now(),
            )
            prochain += 1
        lignes.append({'id': nom.id_nomenclature, 'nomenclature': mnemo, 'code': code,
                       'libelle': libelle, 'hierarchy': hierarchie, 'definition': libelle})
    return lignes


def activer(version: VersionReferentielActions) -> None:
    """Rend actives les nomenclatures de la version (avec ses libellés), et
    elles seules, dans TYPE_ACTION et CATEGORIE_ACTION_RESERVE."""
    ids = set()
    for ligne in version.lignes:
        ids.add(ligne['id'])
        Nomenclature.objects.filter(pk=ligne['id']).update(
            actif=True, label=ligne['libelle'], hierarchy=ligne['hierarchy'] or None,
            definition=ligne['definition'] or None, date_maj=timezone.now(),
        )
    (Nomenclature.objects.filter(id_type__mnemonique__in=(TYPE_ACTION, CATEGORIE), actif=True)
     .exclude(pk__in=ids).update(actif=False, date_maj=timezone.now()))
    (VersionReferentielActions.objects.filter(referentiel=REFERENTIEL_TYPES_ACTION)
     .exclude(pk=version.pk).update(courante=False))
    if not version.courante:
        version.courante = True
        version.save(update_fields=['courante'])


def reappliquer_version_courante() -> bool:
    """À appeler après `import_nomenclatures --force` : l'upsert du fichier SQL
    réactive les types Eden 62 et remet leurs libellés aux catégories
    partagées. Sans passage appliqué, rien à faire."""
    courante = version_courante()
    if courante is None or courante.code == VERSION_INITIALE:
        return False
    activer(courante)
    return True


# ---------------------------------------------------------------------------
# Plans et destinataires
# ---------------------------------------------------------------------------

def _plan_par_operation() -> dict[int, object]:
    """{id_operation: plan}, par tous les chemins de l'arborescence."""
    from .access import OPERATION_TO_PG_PATHS
    from .models import PlanGestion
    from .models_operations import Operation

    out = {}
    for path in OPERATION_TO_PG_PATHS:
        rows = Operation.objects.filter(**{f'{path}__isnull': False}).values_list('pk', path)
        for op_id, plan_id in rows:
            out.setdefault(op_id, plan_id)
    plans = PlanGestion.objects.in_bulk(set(out.values()))
    return {op_id: plans.get(plan_id) for op_id, plan_id in out.items()}


def destinataires(plan) -> list:
    """Référents actifs du plan ; à défaut, administrateurs de ses organismes
    gestionnaires."""
    from apps.users.models import Role

    referents = list(plan.referents.filter(active=True))
    if referents:
        return referents
    organismes = [o.pk for o in plan.get_organismes_gestionnaires()]
    return list(Role.objects.filter(role_level='admin_og', active=True,
                                    id_organisme__in=organismes))


def plans_q_pour(user) -> Q | None:
    """Plans dont `user` actualise les types (référent, admin de l'organisme
    gestionnaire d'un plan sans référent, accès global). None = tous."""
    from .access import has_global_plan_access

    if has_global_plan_access(user):
        return None
    q = Q(referents=user)
    if user.role_level == 'admin_og' and user.id_organisme_id:
        q |= Q(referents__isnull=True,
               sites__site__corogsite__uuid_og_id=user.id_organisme_id)
    return q


def peut_actualiser(user, plan) -> bool:
    from .models import PlanGestion

    if plan is None:
        return bool(user.is_super_admin())
    q = plans_q_pour(user)
    return q is None or PlanGestion.objects.filter(q, pk=plan.pk).exists()


# ---------------------------------------------------------------------------
# Simulation / application
# ---------------------------------------------------------------------------

@dataclass
class ObjetPrevu:
    objet: object                 # Operation | SuiviInventaire
    est_operation: bool
    plan: object | None
    ancien_type: Nomenclature
    ancienne_categorie: Nomenclature | None
    corr: Correspondance


def _correspondance(definition, ancien_type) -> Correspondance:
    code = ancien_type.cd_nomenclature or ancien_type.mnemonique or ''
    if code in definition.codes_types:
        # Type repris tel quel par la nouvelle version (V1 → V2).
        return Correspondance(code, PassageReferentielObjet.CONFIANCE_SURE, options=[code])
    return definition.correspondance.get(code) or Correspondance(
        '', PassageReferentielObjet.CONFIANCE_A_ARBITRER, "Code absent de la table de correspondance")


def _objets_prevus(definition) -> list[ObjetPrevu]:
    from .models_operations import Operation, SuiviInventaire

    plans = _plan_par_operation()
    out = []
    for op in (Operation.objects.filter(id_type_action__isnull=False)
               .select_related('id_type_action', 'id_categorie_action_reserve')
               .order_by('pk')):
        out.append(ObjetPrevu(op, True, plans.get(op.pk), op.id_type_action,
                              op.id_categorie_action_reserve,
                              _correspondance(definition, op.id_type_action)))
    for suivi in (SuiviInventaire.objects.filter(id_type_action__isnull=False)
                  .select_related('id_type_action', 'id_pg').order_by('pk')):
        out.append(ObjetPrevu(suivi, False, suivi.id_pg, suivi.id_type_action, None,
                              _correspondance(definition, suivi.id_type_action)))
    return out


def simuler(definition: DefinitionVersion) -> dict:
    """Ce que ferait le passage, sans rien écrire."""
    version_de_depart(definition)
    prevus = _objets_prevus(definition)
    ops = [p for p in prevus if p.est_operation]
    suivis = [p for p in prevus if not p.est_operation]
    from .models_operations import Operation

    par_plan = defaultdict(Counter)
    for p in ops:
        par_plan[p.plan][p.corr.confiance] += 1
    devient_cs = [p for p in ops
                  if p.corr.nouveau_code and categorie_du_code(p.corr.nouveau_code) == 'CS'
                  and categorie_du_code(p.ancien_type.cd_nomenclature or '') != 'CS']
    a_arbitrer = Counter((p.ancien_type.cd_nomenclature or '') for p in ops
                         if p.corr.confiance == PassageReferentielObjet.CONFIANCE_A_ARBITRER)
    plans_sans_destinataire = [pl for pl in par_plan if pl is not None and not destinataires(pl)]
    return {
        'depuis': definition.depuis,
        'vers': definition.code,
        'types': len(definition.types),
        'categories': [c for c, _l in definition.categories],
        'exclues': definition.exclues,
        'actions': {
            'total': Operation.objects.count(),
            'sans_type': Operation.objects.filter(id_type_action__isnull=True).count(),
            **Counter(p.corr.confiance for p in ops),
        },
        'suivis': dict(Counter(p.corr.confiance for p in suivis)),
        'devient_cs': {'total': len(devient_cs),
                       'sans_suivi': sum(1 for p in devient_cs if not p.objet.id_suivi_id)},
        'a_arbitrer_par_code': a_arbitrer.most_common(),
        'plans': sorted(
            ({'plan': pl.nom if pl else None, 'statut': pl.statut if pl else None,
              **dict(c)} for pl, c in par_plan.items()),
            key=lambda d: (d['plan'] is None, d['plan'] or ''),
        ),
        'plans_sans_destinataire': [pl.nom for pl in plans_sans_destinataire],
        'sans_plan': sum(1 for p in ops if p.plan is None),
    }


def _type_par_code(version) -> dict[str, Nomenclature]:
    ids = [l['id'] for l in version.lignes]
    return {(n.cd_nomenclature or ''): n for n in Nomenclature.objects.filter(
        pk__in=ids).select_related('id_type')}


@transaction.atomic
def appliquer(definition: DefinitionVersion, *, envoyer_email=True) -> PassageReferentielActions:
    source = version_de_depart(definition) or _releve_version_initiale()
    cible, _ = VersionReferentielActions.objects.update_or_create(
        code=definition.code,
        defaults={'libelle': definition.libelle, 'lignes': _creer_lignes_version(definition),
                  'courante': False, 'referentiel': REFERENTIEL_TYPES_ACTION},
    )
    nouveaux = _type_par_code(cible)
    types_cible = {c: n for c, n in nouveaux.items() if n.id_type.mnemonique == TYPE_ACTION}
    categories_cible = {c: n for c, n in nouveaux.items() if n.id_type.mnemonique == CATEGORIE}

    prevus = _objets_prevus(definition)
    passage = PassageReferentielActions.objects.create(source=source, cible=cible)
    journal = []
    for p in prevus:
        corr = p.corr
        applique = corr.confiance in CONFIANCES_APPLIQUEES
        nouveau_type = types_cible.get(corr.nouveau_code) if applique else None
        nouvelle_categorie = (categories_cible.get(categorie_du_code(corr.nouveau_code))
                              if applique else None)
        # À arbitrer : cohabitation, l'objet garde son ancien type et sa
        # catégorie jusqu'au choix du référent (#776).
        if applique and p.est_operation:
            p.objet.id_type_action = nouveau_type
            # La catégorie d'une action la suit ; une action qui n'en avait pas
            # n'en reçoit pas (son code d'affichage découle déjà du type).
            if p.ancienne_categorie is not None or nouvelle_categorie is None:
                p.objet.id_categorie_action_reserve = nouvelle_categorie
            p.objet.save(update_fields=['id_type_action', 'id_categorie_action_reserve'])
        elif applique:
            p.objet.id_type_action = nouveau_type
            p.objet.save(update_fields=['id_type_action'])
        journal.append(PassageReferentielObjet(
            passage=passage,
            operation=p.objet if p.est_operation else None,
            suivi=None if p.est_operation else p.objet,
            plan=p.plan,
            ancien_type=p.ancien_type,
            ancien_code=p.ancien_type.cd_nomenclature or p.ancien_type.mnemonique or '',
            ancien_libelle=p.ancien_type.label or '',
            ancienne_categorie=p.ancienne_categorie,
            nouveau_type=nouveau_type,
            nouvelle_categorie=nouvelle_categorie if p.est_operation else None,
            suggestion_code=corr.nouveau_code,
            options=corr.options,
            confiance=corr.confiance,
            note=corr.note,
            statut=(PassageReferentielObjet.STATUT_APPLIQUE if applique
                    else PassageReferentielObjet.STATUT_A_ACTUALISER),
        ))
    PassageReferentielObjet.objects.bulk_create(journal)

    # Catégories sans correspondance de type (action sans type mais catégorisée).
    from .models_operations import Operation
    for op in (Operation.objects.filter(id_type_action__isnull=True,
                                        id_categorie_action_reserve__isnull=False)
               .exclude(passages_referentiel__passage=passage)
               .exclude(id_categorie_action_reserve__in=categories_cible.values())
               .select_related('id_categorie_action_reserve')):
        op.id_categorie_action_reserve = categories_cible.get(
            op.id_categorie_action_reserve.cd_nomenclature or '')
        op.save(update_fields=['id_categorie_action_reserve'])

    activer(cible)
    passage.resume = dict(Counter(o.confiance for o in journal if o.operation_id))
    passage.save(update_fields=['resume'])
    _journaliser(passage)
    transaction.on_commit(lambda: notifier_passage(passage, envoyer_email=envoyer_email))
    return passage


@transaction.atomic
def annuler(definition: DefinitionVersion) -> PassageReferentielActions:
    """Revient à la version de départ du dernier passage vers `definition`."""
    passage = (PassageReferentielActions.objects
               .filter(cible__code=definition.code, cible__referentiel=REFERENTIEL_TYPES_ACTION,
                       statut=PassageReferentielActions.STATUT_APPLIQUE)
               .select_related('source', 'cible').first())
    if passage is None:
        raise ReferentielErreur(f"Aucun passage vers {definition.code} à annuler.")
    if version_courante() != passage.cible:
        raise ReferentielErreur(
            f"La version en service n'est plus {definition.code} : annuler d'abord les passages suivants.")
    for obj in passage.objets.select_related('operation', 'suivi'):
        if obj.operation_id:
            obj.operation.id_type_action = obj.ancien_type
            obj.operation.id_categorie_action_reserve = obj.ancienne_categorie
            obj.operation.save(update_fields=['id_type_action', 'id_categorie_action_reserve'])
        elif obj.suivi_id:
            obj.suivi.id_type_action = obj.ancien_type
            obj.suivi.save(update_fields=['id_type_action'])
    activer(passage.source)
    passage.statut = PassageReferentielActions.STATUT_ANNULE
    passage.date_annulation = timezone.now()
    passage.save(update_fields=['statut', 'date_annulation'])
    _retirer_notifications(passage)
    return passage


def _journaliser(passage) -> None:
    from apps.core.services import ActivityService

    ActivityService.log_activity(
        entity_type='instance', entity_id=passage.pk,
        entity_name=f"Référentiel des types d'action : {passage.cible.libelle}",
        action='update', actor=None,
        description=(f"Passage du référentiel des types d'action de « {passage.source.libelle} » "
                     f"à « {passage.cible.libelle} »."),
        metadata={'passage': passage.pk, **passage.resume}, visibility='system',
    )


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def notifier_passage(passage, *, envoyer_email=True) -> int:
    """Une notification par destinataire, tous plans confondus."""
    from apps.notifications.services import NotificationService

    par_dest = defaultdict(lambda: {'plans': Counter(), 'auto': 0})
    objets = passage.objets.filter(operation__isnull=False, plan__isnull=False).select_related('plan')
    par_plan = {}
    for obj in objets:
        if obj.plan_id not in par_plan:
            par_plan[obj.plan_id] = destinataires(obj.plan)
        for dest in par_plan[obj.plan_id]:
            entree = par_dest[dest]
            if obj.statut == PassageReferentielObjet.STATUT_A_ACTUALISER:
                entree['plans'][obj.plan.nom] += 1
            else:
                entree['auto'] += 1
    envoyees = 0
    for dest, e in par_dest.items():
        a_faire = sum(e['plans'].values())
        detail = ', '.join(f"« {nom} » : {n}" for nom, n in e['plans'].most_common())
        message = (f"Le référentiel des types d'action passe de « {passage.source.libelle} » "
                   f"à « {passage.cible.libelle} ». ")
        if e['auto']:
            message += f"{e['auto']} action(s) de vos plans ont reçu leur nouveau type automatiquement. "
        if a_faire:
            message += (f"{a_faire} action(s) n'ont pas d'équivalent certain : elles gardent leur "
                        f"ancien type en attendant que vous choisissiez le nouveau ({detail}).")
        NotificationService.create_notification(
            recipient=dest, notification_type='referentiel_actions',
            title=("Types d'action à actualiser" if a_faire
                   else "Types d'action mis à jour automatiquement"),
            message=message.strip(), priority='medium',
            action_url=URL_A_ACTUALISER, send_email=envoyer_email and bool(a_faire),
        )
        envoyees += 1
    return envoyees


def _retirer_notifications(passage) -> None:
    from apps.notifications.models import Notification

    Notification.objects.filter(
        notification_type__in=('referentiel_actions', 'referentiel_actions_suivi'),
        created_at__gte=passage.date_application,
    ).delete()


def _notifier_suivi(obj, auteur) -> None:
    """Prévient les autres destinataires du plan qu'une action a été actualisée.

    Une seule notification non lue par personne, par passage et par plan : on
    la complète au lieu d'en empiler une par action.
    """
    from apps.notifications.models import Notification
    from apps.notifications.services import NotificationService

    if obj.plan is None:
        return
    # Types d'action : on compte les actions ; autres référentiels (#779) : les
    # objets de la même cible (taxons d'enjeu, pressions…).
    meme_nature = (obj.passage.objets.filter(plan=obj.plan, cible=obj.cible) if obj.cible
                   else obj.passage.objets.filter(plan=obj.plan, operation__isnull=False))
    restantes = meme_nature.filter(statut=PassageReferentielObjet.STATUT_A_ACTUALISER).count()
    for dest in destinataires(obj.plan):
        if dest.pk == getattr(auteur, 'pk', None):
            continue
        notif = Notification.objects.filter(
            recipient=dest, notification_type='referentiel_actions_suivi',
            related_plan=obj.plan, read=False,
            created_at__gte=obj.passage.date_application).first()
        faites = meme_nature.filter(statut=PassageReferentielObjet.STATUT_ACTUALISE).exclude(
            actualise_par=dest).count()
        quoi = "élément(s)" if obj.cible else "action(s)"
        message = (f"{faites} {quoi} du plan « {obj.plan.nom} » ont reçu leur nouveau "
                   f"{'code' if obj.cible else 'type'} par un autre référent (dernière : "
                   f"{auteur.get_full_name() if auteur else '—'}). Il en reste {restantes} à actualiser.")
        if notif:
            notif.message = message
            notif.created_at = timezone.now()
            notif.save(update_fields=['message', 'created_at'])
        else:
            NotificationService.create_notification(
                recipient=dest, notification_type='referentiel_actions_suivi',
                title="Types d'action actualisés", message=message, priority='low',
                related_plan=obj.plan, related_user=auteur, action_url=URL_A_ACTUALISER,
            )


# ---------------------------------------------------------------------------
# Actualisation par un utilisateur
# ---------------------------------------------------------------------------

def passage_en_service() -> PassageReferentielActions | None:
    """Dernier passage appliqué vers la version des types d'action en service."""
    return (PassageReferentielActions.objects
            .filter(statut=PassageReferentielActions.STATUT_APPLIQUE, cible__courante=True,
                    cible__referentiel=REFERENTIEL_TYPES_ACTION)
            .select_related('source', 'cible').first())


def _objets_courants():
    return PassageReferentielObjet.objects.filter(
        passage__statut=PassageReferentielActions.STATUT_APPLIQUE, passage__cible__courante=True,
        passage__cible__referentiel=REFERENTIEL_TYPES_ACTION)


def objet_du_passage(operation) -> PassageReferentielObjet | None:
    """Ligne d'une action pour le passage en service, quel que soit son statut."""
    return (_objets_courants().filter(operation=operation)
            .select_related('passage__cible', 'plan').first())


def objet_en_attente(operation) -> PassageReferentielObjet | None:
    """Ligne « à actualiser » d'une action pour le passage en service."""
    return (_objets_courants()
            .filter(operation=operation, statut=PassageReferentielObjet.STATUT_A_ACTUALISER)
            .select_related('passage__cible', 'plan').first())


def _type_pose_par_le_passage(obj) -> int | None:
    if obj.statut == PassageReferentielObjet.STATUT_ACTUALISE:
        return obj.type_choisi_id
    if obj.statut == PassageReferentielObjet.STATUT_APPLIQUE:
        return obj.nouveau_type_id
    return obj.ancien_type_id


def noter_actualisation(operation, user) -> PassageReferentielObjet | None:
    """Le type de l'action a changé depuis le passage : sa ligne passe à
    « actualisé » (choix fait, ou changement automatique corrigé). Les autres
    référents du plan sont prévenus quand c'était un choix attendu."""
    if operation.id_type_action_id is None:
        return None
    obj = objet_du_passage(operation)
    if obj is None or operation.id_type_action_id == _type_pose_par_le_passage(obj):
        return None
    attendu = obj.statut == PassageReferentielObjet.STATUT_A_ACTUALISER
    obj.statut = PassageReferentielObjet.STATUT_ACTUALISE
    obj.actualise_par = user if getattr(user, 'pk', None) else None
    obj.actualise_le = timezone.now()
    obj.type_choisi_id = operation.id_type_action_id
    obj.save(update_fields=['statut', 'actualise_par', 'actualise_le', 'type_choisi'])
    if attendu:
        transaction.on_commit(lambda: _notifier_suivi(obj, obj.actualise_par))
    return obj


def dernier_objet(operation) -> PassageReferentielObjet | None:
    return (PassageReferentielObjet.objects.filter(operation=operation)
            .select_related('actualise_par').order_by('-pk').first())


class TypeDejaModifie(Exception):
    """Le type a changé depuis que l'utilisateur a ouvert l'action."""

    def __init__(self, operation, obj):
        super().__init__("type déjà modifié")
        self.operation = operation
        self.obj = obj


class SuiviRequis(Exception):
    """L'action devient CS sans suivi : il faut en créer ou en rattacher un."""


def est_cs(type_action) -> bool:
    return bool(type_action) and (type_action.cd_nomenclature or '').startswith('CS')


def devient_cs(op, nouveau_type) -> bool:
    """L'action passe d'un type hors CS à un type CS sans avoir de suivi : il
    faut alors poser les questions du suivi (#776). Une action déjà CS garde
    son état, avec ou sans suivi."""
    return est_cs(nouveau_type) and not est_cs(op.id_type_action) and not op.id_suivi_id


def _rattacher_suivi(op, nouveau_type, suivi, user) -> None:
    """Suivi d'une action qui devient CS : existant (`id_suivi`) ou nouveau
    (intitulé, objectif, cible, protocoles), dans le plan de l'action."""
    from .models_operations import SuiviInventaire
    from .serializers_operations import pop_protocoles_data, sync_suivi_protocoles

    if suivi.get('id_suivi'):
        op.id_suivi = SuiviInventaire.objects.get(pk=suivi['id_suivi'])
        op.est_suivi_existant = True
        return
    donnees = {k: v for k, v in suivi.items() if k != 'id_suivi'}
    protocoles = pop_protocoles_data(donnees)
    nouveau = SuiviInventaire.objects.create(
        **donnees, id_type_action=nouveau_type, id_pg=op.get_plan_de_gestion(),
        id_utilisateur_ajout=user if getattr(user, 'pk', None) else None,
    )
    sync_suivi_protocoles(nouveau, protocoles, user)
    op.id_suivi = nouveau
    op.est_suivi_existant = False


def actualiser_type(operation, nouveau_type, user, *, type_attendu_id,
                    suivi=None) -> PassageReferentielObjet | None:
    """Pose le type choisi, même dans un plan validé ou archivé (#248 : seule
    exception, le type et ce qui en découle).

    `type_attendu_id` = le type affiché quand l'utilisateur a choisi ; s'il ne
    correspond plus, un autre référent est passé avant lui. Une action qui
    devient CS sans suivi exige `suivi` (`{'id_suivi': …}` ou les champs d'un
    nouveau suivi) — sinon `SuiviRequis`.
    """
    from .models_operations import Operation

    with transaction.atomic():
        op = Operation.objects.select_for_update().get(pk=operation.pk)
        if op.id_type_action_id != type_attendu_id:
            raise TypeDejaModifie(op, dernier_objet(op))
        champs = ['id_type_action', 'id_categorie_action_reserve']
        if devient_cs(op, nouveau_type):
            if not suivi:
                raise SuiviRequis()
            _rattacher_suivi(op, nouveau_type, suivi, user)
            champs += ['id_suivi', 'est_suivi_existant']
        elif not est_cs(nouveau_type) and op.id_suivi_id:
            # #715 — une action qui n'est plus CS se détache de son suivi.
            op.id_suivi = None
            op.est_suivi_existant = False
            champs += ['id_suivi', 'est_suivi_existant']
        op.id_type_action = nouveau_type
        categorie = Nomenclature.objects.filter(
            id_type__mnemonique=CATEGORIE, actif=True,
            cd_nomenclature=categorie_du_code(nouveau_type.cd_nomenclature or '')).first()
        if categorie is not None:
            op.id_categorie_action_reserve = categorie
        op.save(update_fields=champs)
        # Le suivi rattaché prend le type de son action (#715).
        if op.id_suivi_id and est_cs(nouveau_type) and op.id_suivi.id_type_action_id != nouveau_type.pk:
            op.id_suivi.id_type_action = nouveau_type
            op.id_suivi.save(update_fields=['id_type_action'])
        return noter_actualisation(op, user)


def options_de(obj) -> list[Nomenclature]:
    """Équivalents proposés (types actifs), dans l'ordre de la table."""
    codes = obj.options or ([obj.suggestion_code] if obj.suggestion_code else [])
    par_code = {n.cd_nomenclature: n for n in Nomenclature.objects.filter(
        id_type__mnemonique=TYPE_ACTION, actif=True, cd_nomenclature__in=codes)}
    return [par_code[c] for c in codes if c in par_code]


def _option(n) -> dict:
    return {'id': n.pk, 'code': n.cd_nomenclature, 'libelle': n.label}


def accepter_propositions(user, plan_id=None) -> dict:
    """« Accepter toutes les propositions » : pose l'équivalent des actions à
    actualiser qui n'en ont qu'un ; les autres attendent un choix (plusieurs
    équivalents, ou action qui deviendrait CS sans suivi)."""
    from .models import PlanGestion

    objets = (_objets_courants()
              .filter(operation__isnull=False, statut=PassageReferentielObjet.STATUT_A_ACTUALISER)
              .select_related('operation'))
    q = plans_q_pour(user)
    if q is not None:
        objets = objets.filter(plan__in=PlanGestion.objects.filter(q))
    if plan_id:
        objets = objets.filter(plan_id=plan_id)
    bilan = {'acceptees': 0, 'plusieurs_options': 0, 'suivi_requis': 0}
    for obj in objets:
        options = options_de(obj)
        if len(options) != 1:
            bilan['plusieurs_options'] += 1
            continue
        op = obj.operation
        if devient_cs(op, options[0]):
            bilan['suivi_requis'] += 1
            continue
        try:
            actualiser_type(op, options[0], user, type_attendu_id=op.id_type_action_id)
        except TypeDejaModifie:
            continue
        bilan['acceptees'] += 1
    return bilan


def resume_attente(operation) -> dict | None:
    """Ce que la fiche action affiche d'une action à actualiser."""
    obj = objet_en_attente(operation)
    if obj is None:
        return None
    options = options_de(obj)
    suggestion = options[0] if options else None
    return {
        'passage': obj.passage_id,
        'version': obj.passage.cible.libelle,
        'ancien_code': obj.ancien_code,
        'ancien_libelle': obj.ancien_libelle,
        'suggestion_id': suggestion.pk if suggestion else None,
        'suggestion_code': suggestion.cd_nomenclature if suggestion else '',
        'suggestion_libelle': suggestion.label if suggestion else '',
        'options': [_option(n) for n in options],
        'note': obj.note,
    }
