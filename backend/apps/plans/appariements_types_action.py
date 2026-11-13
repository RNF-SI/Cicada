"""
#770 — appariement du référentiel des types d'action d'une structure vers
Gestref, à l'import des actions.

Décisions (Sophie et mainteneur, 13/11) :

- le type de la structure arrive par une **colonne du classeur**
  (« type d'action (référentiel de la structure) ») ;
- l'appariement **se saisit à l'import** (étape « Correspondance avec
  Gestref ») ;
- il est **gardé par organisme** — l'organisme gestionnaire du plan — et
  proposé aux imports suivants ;
- la colonne Gestref (« type d'action ») **l'emporte** quand elle est remplie :
  le type de la structure ne sert que si elle est vide.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from apps.core.models import Nomenclature

from .referentiel_actions import TYPE_ACTION, _cle, libelle_type_action

COLONNE = "type_action_structure"


def organisme_d_appariement(plan, user=None):
    """L'organisme dont on lit et enregistre les appariements : le
    gestionnaire du site principal du plan, à défaut celui de l'utilisateur."""
    from .redacteurs import organisme_gestionnaire_principal

    org = organisme_gestionnaire_principal(plan) if plan is not None else None
    if org is None and user is not None:
        org = getattr(user, "id_organisme", None)
    return org


@dataclass
class _Valeur:
    valeur: str
    lignes: list = field(default_factory=list)
    type: Nomenclature | None = None
    origine: str = ""   # "saisi" (cet import) | "enregistre" (import précédent) | ""


class Appariements:
    """Les types de la structure rencontrés dans un classeur, et leur type
    Gestref : celui choisi à cet import (``recus``, {valeur: id}) sinon celui
    enregistré pour l'organisme."""

    def __init__(self, plan, user=None, recus: dict | None = None):
        from .models_referentiel import AppariementTypeAction

        self.organisme = organisme_d_appariement(plan, user)
        self.user = user
        ids = {v for v in (recus or {}).values() if v}
        types = {n.pk: n for n in Nomenclature.objects.filter(
            pk__in=ids, id_type__mnemonique=TYPE_ACTION)}
        self._recus = {_cle(k): types.get(_entier(v)) for k, v in (recus or {}).items()}
        self._enregistres = {}
        if self.organisme is not None:
            self._enregistres = {
                a.cle: a.id_type_action for a in AppariementTypeAction.objects.filter(
                    organisme=self.organisme).select_related('id_type_action')}
        self._valeurs: dict[str, _Valeur] = {}

    def type_pour(self, valeur, ligne=None) -> Nomenclature | None:
        """Type Gestref d'une valeur de la structure (et note la ligne)."""
        valeur = (valeur or "").strip()
        if not valeur:
            return None
        cle = _cle(valeur)
        v = self._valeurs.get(cle)
        if v is None:
            v = self._valeurs[cle] = _Valeur(valeur)
            if self._recus.get(cle) is not None:
                v.type, v.origine = self._recus[cle], "saisi"
            elif self._enregistres.get(cle) is not None:
                v.type, v.origine = self._enregistres[cle], "enregistre"
        if ligne is not None and ligne not in v.lignes:
            v.lignes.append(ligne)
        return v.type

    def resume(self) -> list[dict]:
        """Pour l'étape « Correspondance » : une ligne par valeur rencontrée."""
        return [{
            "valeur": v.valeur,
            "lignes": v.lignes,
            "id_type_action": v.type.pk if v.type else None,
            "type_action": libelle_type_action(v.type) if v.type else "",
            "origine": v.origine,
        } for v in sorted(self._valeurs.values(), key=lambda x: x.valeur.lower())]

    def organisme_dict(self) -> dict | None:
        if self.organisme is None:
            return None
        return {"id": self.organisme.pk, "nom": getattr(self.organisme, "nom_organisme", "")
                or str(self.organisme)}

    def enregistrer(self) -> int:
        """Garde pour l'organisme les appariements utilisés par cet import."""
        from .models_referentiel import AppariementTypeAction

        if self.organisme is None:
            return 0
        n = 0
        for cle, v in self._valeurs.items():
            if v.type is None:
                continue
            AppariementTypeAction.objects.update_or_create(
                organisme=self.organisme, cle=cle,
                defaults={"valeur": v.valeur, "id_type_action": v.type,
                          "id_utilisateur_maj": self.user if getattr(self.user, "pk", None) else None})
            n += 1
        return n


def _entier(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None
