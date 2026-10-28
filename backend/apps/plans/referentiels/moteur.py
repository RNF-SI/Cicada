"""
Moteur commun des passages de version de référentiel (#779) — PressRef, TaxRef,
HabRef. Mêmes règles que les types d'action (#751, #776) :

- correspondance **sûre** ou **probable** → le nouveau code est posé (listé,
  modifiable par les référents) ;
- **à arbitrer** → **cohabitation** : l'ancien code reste jusqu'au choix du
  référent, parmi les équivalents (`options`) ou ailleurs dans le référentiel ;
- un code repris tel quel par la nouvelle version n'est pas touché ;
- une notification par référent et par passage ; journal par objet
  (`PassageReferentielObjet`), qui permet l'annulation.

Une version est un dossier de `nomenclatures_data/referentiels_versions/<ref>/` :
`version.json` (code, libellé, `depuis`), `correspondance.csv`
(`ancien_code,nouveau_code,confiance,options,note`) et, pour un référentiel tenu
en nomenclature (PressRef), `referentiel.csv` (`code,libelle`). Pour TaxRef et
HabRef, la nouvelle version s'importe d'abord (`import_taxref`, `import_habref`) ;
le passage remappe ensuite les codes portés par les plans.
"""
from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from ..models_referentiel import (
    PassageReferentielActions, PassageReferentielObjet, VersionReferentielActions,
)
from .cibles import CIBLES

DOSSIER_VERSIONS = (
    Path(__file__).resolve().parents[3] / 'nomenclatures_data' / 'referentiels_versions'
)
URL_A_ACTUALISER = '/actions-a-actualiser'
CONFIANCES = ('sure', 'probable', 'a_arbitrer')
APPLIQUEES = ('sure', 'probable')


class ReferentielErreur(Exception):
    """Version ou table de correspondance inutilisable (message lisible)."""


@dataclass
class Correspondance:
    nouveau_code: str
    confiance: str
    note: str = ''
    options: list = field(default_factory=list)


@dataclass
class Definition:
    code: str
    libelle: str
    depuis: str
    lignes: list = field(default_factory=list)          # [(code, libelle)]
    correspondance: dict = field(default_factory=dict)

    @property
    def codes(self) -> set:
        return {c for c, _l in self.lignes}


# ---------------------------------------------------------------------------
# Référentiels
# ---------------------------------------------------------------------------

class Referentiel:
    """Un référentiel versionné : ses cibles, sa version de départ, ses libellés."""

    code = ''
    libelle = ''
    dossier = ''
    cibles: tuple = ()
    nomenclature: str | None = None    # type de nomenclature tenu par versions

    # -- version de départ, relevée en base au premier passage --------------
    def version_initiale(self) -> tuple[str, str]:  # pragma: no cover - interface
        raise NotImplementedError

    def lignes_initiales(self) -> list[dict]:
        if not self.nomenclature:
            return []
        from apps.core.models import Nomenclature
        return [{'id': n.pk, 'code': n.cd_nomenclature or n.mnemonique or '',
                 'libelle': n.label or '', 'hierarchy': n.hierarchy or '',
                 'definition': n.definition or ''}
                for n in Nomenclature.objects.filter(id_type__mnemonique=self.nomenclature,
                                                      actif=True)]

    # -- libellés en base (options, recherche) -------------------------------
    def libelles(self, codes) -> dict[str, str]:  # pragma: no cover - interface
        raise NotImplementedError

    def existe(self, code: str) -> bool:
        return code in self.libelles([code])


class PressRef(Referentiel):
    code = 'PRESSREF'
    libelle = "Types de pression (PressRef)"
    dossier = 'pressref'
    cibles = ('pression',)
    nomenclature = 'TYPE_PRESSION'

    def version_initiale(self):
        return 'PRESSREF_CARET_V1', 'PressRef CARET V1'

    def libelles(self, codes):
        from apps.core.models import Nomenclature
        return dict(Nomenclature.objects.filter(
            id_type__mnemonique=self.nomenclature, cd_nomenclature__in=list(codes))
            .order_by('actif').values_list('cd_nomenclature', 'label'))


class TaxRef(Referentiel):
    code = 'TAXREF'
    libelle = "Taxons (TaxRef)"
    dossier = 'taxref'
    cibles = ('enjeu_taxon', 'responsabilite_taxon')

    def version_initiale(self):
        from apps.taxonomy.models import TMetaTaxref
        meta = TMetaTaxref.objects.order_by('-update_date').first()
        version = meta.version if meta else '?'
        return f'TAXREF_V{version}', f'TaxRef v{version}'

    def libelles(self, codes):
        from apps.taxonomy.models import Taxref
        ints = [int(c) for c in codes if str(c).isdigit()]
        return {str(k): v for k, v in Taxref.objects.filter(cd_nom__in=ints)
                .values_list('cd_nom', 'nom_complet')}


class HabRef(Referentiel):
    code = 'HABREF'
    libelle = "Habitats (HabRef)"
    dossier = 'habref'
    cibles = ('enjeu_habitat', 'responsabilite_habitat', 'suivi_habitat')

    def version_initiale(self):
        from apps.habitats.management.commands.import_habref import HABREF_URL
        m = re.search(r'HABREF_(\d)(\d+)', HABREF_URL)
        version = f'{m.group(1)}.{m.group(2)}' if m else '?'
        return f'HABREF_V{version}', f'HabRef {version}'

    def libelles(self, codes):
        from apps.habitats.models import Habref
        ints = [int(c) for c in codes if str(c).isdigit()]
        return {str(k): v for k, v in Habref.objects.filter(cd_hab__in=ints)
                .values_list('cd_hab', 'lb_hab_fr')}


REFERENTIELS = {r.code: r for r in (PressRef(), TaxRef(), HabRef())}


def referentiel(code: str) -> Referentiel:
    try:
        return REFERENTIELS[code.upper()]
    except KeyError as e:
        raise ReferentielErreur(f"Référentiel inconnu : {code}") from e


# ---------------------------------------------------------------------------
# Lecture d'une version
# ---------------------------------------------------------------------------

def versions_disponibles(ref: Referentiel) -> list[str]:
    dossier = DOSSIER_VERSIONS / ref.dossier
    return sorted(p.name for p in dossier.iterdir() if (p / 'version.json').exists()) \
        if dossier.is_dir() else []


def charger(ref: Referentiel, nom: str) -> Definition:
    dossier = DOSSIER_VERSIONS / ref.dossier / nom
    if not dossier.is_dir():
        raise ReferentielErreur(f"Version introuvable : {dossier}")
    try:
        meta = json.loads((dossier / 'version.json').read_text(encoding='utf-8'))
    except (OSError, ValueError) as e:
        raise ReferentielErreur(f"version.json illisible : {e}") from e
    for cle in ('code', 'libelle', 'depuis'):
        if not meta.get(cle):
            raise ReferentielErreur(f"version.json : « {cle} » manquant")
    d = Definition(code=meta['code'], libelle=meta['libelle'], depuis=meta['depuis'])
    if (dossier / 'referentiel.csv').exists():
        with open(dossier / 'referentiel.csv', encoding='utf-8', newline='') as f:
            for row in csv.DictReader(f):
                code = (row.get('code') or '').strip()
                if code:
                    d.lignes.append((code, ' '.join((row.get('libelle') or '').split())))
    elif ref.nomenclature:
        raise ReferentielErreur("referentiel.csv requis pour un référentiel en nomenclature")

    def connu(code):
        return code in d.codes if d.lignes else ref.existe(code)

    with open(dossier / 'correspondance.csv', encoding='utf-8', newline='') as f:
        for row in csv.DictReader(f):
            ancien = (row.get('ancien_code') or '').strip()
            if not ancien:
                continue
            nouveau = (row.get('nouveau_code') or '').strip()
            confiance = (row.get('confiance') or '').strip()
            if confiance not in CONFIANCES:
                raise ReferentielErreur(f"correspondance.csv : confiance « {confiance} » inconnue ({ancien})")
            if confiance in APPLIQUEES and not nouveau:
                raise ReferentielErreur(f"correspondance.csv : « {ancien} » est {confiance} sans nouveau code")
            options = [nouveau] if nouveau else []
            options += [c.strip() for c in (row.get('options') or '').split('|')
                        if c.strip() and c.strip() not in options]
            for code in options:
                if not connu(code):
                    raise ReferentielErreur(
                        f"correspondance.csv : « {code} » ({ancien}) absent de la nouvelle version")
            d.correspondance[ancien] = Correspondance(nouveau, confiance,
                                                      (row.get('note') or '').strip(), options)
    return d


# ---------------------------------------------------------------------------
# Versions en base
# ---------------------------------------------------------------------------

def version_courante(ref: Referentiel) -> VersionReferentielActions | None:
    return VersionReferentielActions.objects.filter(referentiel=ref.code, courante=True).first()


def version_en_service(ref: Referentiel) -> tuple[str, str]:
    """(code, libellé) de la version en service, relevée ou non."""
    v = version_courante(ref)
    return (v.code, v.libelle) if v else ref.version_initiale()


def _releve_initiale(ref: Referentiel) -> VersionReferentielActions:
    code, libelle = ref.version_initiale()
    v, _ = VersionReferentielActions.objects.update_or_create(
        code=code, defaults={'referentiel': ref.code, 'libelle': libelle,
                             'lignes': ref.lignes_initiales(), 'courante': True})
    return v


def _depart(ref: Referentiel, d: Definition) -> VersionReferentielActions | None:
    code = version_en_service(ref)[0]
    if code != d.depuis:
        raise ReferentielErreur(f"{d.code} part de {d.depuis}, or la version en service est {code}.")
    return version_courante(ref)


def _lignes_nomenclature(ref: Referentiel, d: Definition) -> list[dict]:
    """Crée (inactives) ou retrouve les nomenclatures de la version."""
    from apps.core.models import Nomenclature, TypeNomenclature

    from ..referentiel_actions import REFERENTIEL_ID_BASE

    type_nom = TypeNomenclature.objects.filter(mnemonique=ref.nomenclature).first()
    if type_nom is None:
        raise ReferentielErreur(f"Nomenclature absente : {ref.nomenclature}")
    prochain = (Nomenclature.objects.filter(id_nomenclature__gte=REFERENTIEL_ID_BASE)
                .aggregate(m=Max('id_nomenclature'))['m'] or REFERENTIEL_ID_BASE - 1) + 1
    lignes = []
    for code, libelle in d.lignes:
        # Clé de tri numérique (1.10 après 1.9), posée aussi sur les lignes reprises.
        hierarchie = '.'.join(f'{int(n):03d}' for n in re.findall(r'\d+', code)) or code
        nom = (Nomenclature.objects.filter(id_type=type_nom, cd_nomenclature=code)
               .order_by('-actif', 'id_nomenclature').first())
        if nom is None:
            nom = Nomenclature.objects.create(
                id_nomenclature=prochain, id_type=type_nom, cd_nomenclature=code,
                mnemonique=code.replace('.', '_'), label=libelle, definition=libelle,
                source=d.code, statut='Validé', hierarchy=hierarchie, actif=False,
                date_ajout=timezone.now(), date_maj=timezone.now())
            prochain += 1
        lignes.append({'id': nom.pk, 'code': code, 'libelle': libelle,
                       'hierarchy': hierarchie, 'definition': libelle})
    return lignes


def activer(ref: Referentiel, version: VersionReferentielActions) -> None:
    if ref.nomenclature:
        from apps.core.models import Nomenclature
        ids = set()
        for l in version.lignes:
            ids.add(l['id'])
            Nomenclature.objects.filter(pk=l['id']).update(
                actif=True, label=l['libelle'], hierarchy=l.get('hierarchy') or None,
                date_maj=timezone.now())
        (Nomenclature.objects.filter(id_type__mnemonique=ref.nomenclature, actif=True)
         .exclude(pk__in=ids).update(actif=False, date_maj=timezone.now()))
    VersionReferentielActions.objects.filter(referentiel=ref.code).exclude(
        pk=version.pk).update(courante=False)
    if not version.courante:
        version.courante = True
        version.save(update_fields=['courante'])


def reappliquer_versions_courantes() -> list[str]:
    """Après `import_nomenclatures --force` : rétablit les référentiels tenus en
    nomenclature (PressRef) dans leur version en service."""
    faits = []
    for ref in REFERENTIELS.values():
        v = version_courante(ref)
        if ref.nomenclature and v and v.code != ref.version_initiale()[0]:
            activer(ref, v)
            faits.append(ref.code)
    return faits


# ---------------------------------------------------------------------------
# Simulation / application / annulation
# ---------------------------------------------------------------------------

def _correspondance(d: Definition, ref: Referentiel, code: str) -> Correspondance | None:
    """Ce qui arrive à un code : None = inchangé."""
    if code in d.correspondance:
        return d.correspondance[code]
    if d.lignes and code not in d.codes and ref.nomenclature:
        return Correspondance('', 'a_arbitrer', "Code absent de la table de correspondance")
    return None


def _prevus(ref: Referentiel, d: Definition):
    for nom in ref.cibles:
        for o in CIBLES[nom].objets():
            corr = _correspondance(d, ref, o.code)
            if corr is not None:
                yield o, corr


def simuler(ref: Referentiel, d: Definition) -> dict:
    _depart(ref, d)
    from ..referentiel_actions import destinataires

    prevus = list(_prevus(ref, d))
    par_cible = defaultdict(Counter)
    par_plan = defaultdict(Counter)
    for o, corr in prevus:
        par_cible[o.cible.libelle][corr.confiance] += 1
        par_plan[o.plan][corr.confiance] += 1
    return {
        'referentiel': ref.code,
        'depuis': d.depuis, 'vers': d.code, 'libelle': d.libelle,
        'objets': dict(Counter(c.confiance for _o, c in prevus)),
        'par_cible': {k: dict(v) for k, v in par_cible.items()},
        'a_arbitrer_par_code': Counter(o.code for o, c in prevus if c.confiance == 'a_arbitrer').most_common(),
        'plans': sorted(({'plan': pl.nom if pl else None, 'statut': pl.statut if pl else None, **dict(c)}
                         for pl, c in par_plan.items()),
                        key=lambda x: (x['plan'] is None, x['plan'] or '')),
        'plans_sans_destinataire': [pl.nom for pl in par_plan if pl is not None and not destinataires(pl)],
    }


@transaction.atomic
def appliquer(ref: Referentiel, d: Definition, *, envoyer_email=True) -> PassageReferentielActions:
    source = _depart(ref, d) or _releve_initiale(ref)
    lignes = _lignes_nomenclature(ref, d) if ref.nomenclature else [
        {'code': c, 'libelle': l} for c, l in d.lignes]
    cible_v, _ = VersionReferentielActions.objects.update_or_create(
        code=d.code, defaults={'referentiel': ref.code, 'libelle': d.libelle,
                               'lignes': lignes, 'courante': False})
    passage = PassageReferentielActions.objects.create(source=source, cible=cible_v)
    libelles_ref = dict(d.lignes) or {}
    libelles_base = ref.libelles({c for corr in d.correspondance.values() for c in corr.options})
    journal = []
    for o, corr in _prevus(ref, d):
        applique = corr.confiance in APPLIQUEES
        nouveau_libelle = (libelles_ref.get(corr.nouveau_code)
                           or libelles_base.get(corr.nouveau_code, '')) if corr.nouveau_code else ''
        if applique:
            o.cible.poser(o.objet_id, corr.nouveau_code, nouveau_libelle, o.code)
        journal.append(PassageReferentielObjet(
            passage=passage, cible=o.cible.nom, objet_id=o.objet_id, plan=o.plan,
            ancien_code=o.code, ancien_libelle=o.libelle[:500],
            nouveau_code=corr.nouveau_code if applique else '',
            nouveau_libelle=nouveau_libelle[:500] if applique else '',
            suggestion_code=corr.nouveau_code, options=corr.options, note=corr.note,
            confiance=corr.confiance,
            statut=(PassageReferentielObjet.STATUT_APPLIQUE if applique
                    else PassageReferentielObjet.STATUT_A_ACTUALISER),
        ))
    PassageReferentielObjet.objects.bulk_create(journal)
    activer(ref, cible_v)
    passage.resume = dict(Counter(o.confiance for o in journal))
    passage.save(update_fields=['resume'])
    transaction.on_commit(lambda: notifier(ref, passage, envoyer_email=envoyer_email))
    return passage


@transaction.atomic
def annuler(ref: Referentiel, d: Definition) -> PassageReferentielActions:
    passage = (PassageReferentielActions.objects
               .filter(cible__code=d.code, cible__referentiel=ref.code,
                       statut=PassageReferentielActions.STATUT_APPLIQUE)
               .select_related('source', 'cible').first())
    if passage is None:
        raise ReferentielErreur(f"Aucun passage vers {d.code} à annuler.")
    if version_courante(ref) != passage.cible:
        raise ReferentielErreur(f"La version en service n'est plus {d.code}.")
    for obj in passage.objets.exclude(statut=PassageReferentielObjet.STATUT_A_ACTUALISER):
        CIBLES[obj.cible].poser(obj.objet_id, obj.ancien_code, obj.ancien_libelle, obj.nouveau_code)
    activer(ref, passage.source)
    passage.statut = PassageReferentielActions.STATUT_ANNULE
    passage.date_annulation = timezone.now()
    passage.save(update_fields=['statut', 'date_annulation'])
    from apps.notifications.models import Notification
    Notification.objects.filter(notification_type__in=('referentiel_actions', 'referentiel_actions_suivi'),
                                created_at__gte=passage.date_application,
                                title__startswith=ref.libelle).delete()
    return passage


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

def notifier(ref: Referentiel, passage, *, envoyer_email=True) -> int:
    from apps.notifications.services import NotificationService

    from ..referentiel_actions import destinataires

    par_dest = defaultdict(lambda: {'a_faire': Counter(), 'auto': 0})
    cache = {}
    for obj in passage.objets.filter(plan__isnull=False).select_related('plan'):
        if obj.plan_id not in cache:
            cache[obj.plan_id] = destinataires(obj.plan)
        for dest in cache[obj.plan_id]:
            if obj.statut == PassageReferentielObjet.STATUT_A_ACTUALISER:
                par_dest[dest]['a_faire'][obj.plan.nom] += 1
            else:
                par_dest[dest]['auto'] += 1
    for dest, e in par_dest.items():
        a_faire = sum(e['a_faire'].values())
        message = f"{ref.libelle} : passage de « {passage.source.libelle} » à « {passage.cible.libelle} ». "
        if e['auto']:
            message += f"{e['auto']} élément(s) de vos plans ont reçu leur nouveau code automatiquement. "
        if a_faire:
            detail = ', '.join(f"« {n} » : {c}" for n, c in e['a_faire'].most_common())
            message += (f"{a_faire} élément(s) n'ont pas d'équivalent certain : ils gardent leur ancien "
                        f"code en attendant votre choix ({detail}).")
        NotificationService.create_notification(
            recipient=dest, notification_type='referentiel_actions',
            title=f"{ref.libelle} : " + ("éléments à actualiser" if a_faire else "mise à jour automatique"),
            message=message.strip(), priority='medium', action_url=URL_A_ACTUALISER,
            send_email=envoyer_email and bool(a_faire))
    return len(par_dest)


# ---------------------------------------------------------------------------
# Choix des référents
# ---------------------------------------------------------------------------

def objets_courants(ref: Referentiel):
    return PassageReferentielObjet.objects.filter(
        passage__statut=PassageReferentielActions.STATUT_APPLIQUE,
        passage__cible__courante=True, passage__cible__referentiel=ref.code)


def code_courant(obj) -> str:
    """Code que porte l'objet d'après le journal."""
    return obj.ancien_code if obj.statut == PassageReferentielObjet.STATUT_A_ACTUALISER else obj.nouveau_code


class CodeDejaModifie(Exception):
    def __init__(self, obj):
        super().__init__("code déjà modifié")
        self.obj = obj


def options_de(ref: Referentiel, obj) -> list[dict]:
    codes = obj.options or ([obj.suggestion_code] if obj.suggestion_code else [])
    version = obj.passage.cible
    libelles = {l['code']: l['libelle'] for l in version.lignes} or {}
    manquants = [c for c in codes if c not in libelles]
    libelles.update(ref.libelles(manquants) if manquants else {})
    return [{'code': c, 'libelle': libelles.get(c, '')} for c in codes]


def actualiser(ref: Referentiel, obj, code: str, user, *, attendu: str) -> PassageReferentielObjet:
    """Pose le code choisi (ou corrige un changement automatique), même dans
    un plan validé ou archivé — seul ce code change."""
    with transaction.atomic():
        obj = PassageReferentielObjet.objects.select_for_update().select_related('passage__cible').get(pk=obj.pk)
        courant = code_courant(obj)
        if attendu != courant or CIBLES[obj.cible].valeur(obj.objet_id, courant) != courant:
            raise CodeDejaModifie(obj)
        libelle = ({l['code']: l['libelle'] for l in obj.passage.cible.lignes}.get(code)
                   or ref.libelles([code]).get(code, ''))
        if not libelle and not ref.existe(code):
            raise ReferentielErreur(f"Code inconnu dans {obj.passage.cible.libelle} : {code}")
        CIBLES[obj.cible].poser(obj.objet_id, code, libelle, courant)
        attendu_choix = obj.statut == PassageReferentielObjet.STATUT_A_ACTUALISER
        obj.statut = PassageReferentielObjet.STATUT_ACTUALISE
        obj.nouveau_code, obj.nouveau_libelle = code, libelle[:500]
        obj.actualise_par = user if getattr(user, 'pk', None) else None
        obj.actualise_le = timezone.now()
        obj.save(update_fields=['statut', 'nouveau_code', 'nouveau_libelle',
                                'actualise_par', 'actualise_le'])
    if attendu_choix:
        from ..referentiel_actions import _notifier_suivi
        transaction.on_commit(lambda: _notifier_suivi(obj, obj.actualise_par))
    return obj


def peut_actualiser(user, obj) -> bool:
    from ..referentiel_actions import peut_actualiser as peut
    if obj.plan_id is None:
        # Responsabilités de site : pas de référent de plan.
        return bool(user.is_super_admin() or user.is_admin_organisme())
    return peut(user, obj.plan)


def accepter_propositions(ref: Referentiel, user, plan_id=None) -> dict:
    from ..models import PlanGestion
    from ..referentiel_actions import plans_q_pour

    objets = objets_courants(ref).filter(statut=PassageReferentielObjet.STATUT_A_ACTUALISER).select_related('passage__cible')
    q = plans_q_pour(user)
    if q is not None:
        objets = objets.filter(plan__in=PlanGestion.objects.filter(q))
    if plan_id:
        objets = objets.filter(plan_id=plan_id)
    bilan = {'acceptees': 0, 'plusieurs_options': 0, 'suivi_requis': 0}
    for obj in objets:
        options = options_de(ref, obj)
        if len(options) != 1:
            bilan['plusieurs_options'] += 1
            continue
        try:
            actualiser(ref, obj, options[0]['code'], user, attendu=code_courant(obj))
        except (CodeDejaModifie, ReferentielErreur):
            continue
        bilan['acceptees'] += 1
    return bilan
