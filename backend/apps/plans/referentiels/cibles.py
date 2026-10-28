"""
Objets qu'un passage de référentiel touche (#779).

Une **cible** sait lister les objets qui portent un code du référentiel, lire et
poser ce code, et dire à quel plan l'objet appartient (pour ses référents).
Les types d'action ont leur module dédié (`apps/plans/referentiel_actions.py`) ;
ici : PressRef, TaxRef, HabRef.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ObjetCible:
    cible: 'Cible'
    objet_id: int
    plan: object | None
    code: str
    libelle: str
    contexte: str          # ce que l'utilisateur reconnaît (« Enjeu Prairies »)


class Cible:
    nom = ''
    libelle = ''

    def objets(self):  # pragma: no cover - interface
        raise NotImplementedError

    def valeur(self, objet_id, ancien_code=None) -> str | None:  # pragma: no cover
        raise NotImplementedError

    def poser(self, objet_id, code: str, libelle: str, ancien_code: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def plan(self, objet_id):  # pragma: no cover
        raise NotImplementedError


# ---------------------------------------------------------------------------
# PressRef : type de pression d'une pression (nomenclature TYPE_PRESSION)
# ---------------------------------------------------------------------------

class PressionType(Cible):
    nom = 'pression'
    libelle = "Type de pression d'une pression"

    def _qs(self):
        from apps.plans.models_enjeux import Pression
        return Pression.objects.select_related('id_type_pression', 'id_facteur_influence')

    def objets(self):
        for p in self._qs().filter(id_type_pression__isnull=False).order_by('pk'):
            t = p.id_type_pression
            yield ObjetCible(self, p.pk, p.get_plan_de_gestion(),
                             t.cd_nomenclature or t.mnemonique or '', t.label or '',
                             p.libelle or f"Pression {p.pk}")

    def valeur(self, objet_id, ancien_code=None):
        p = self._qs().filter(pk=objet_id).first()
        t = p.id_type_pression if p else None
        return (t.cd_nomenclature or t.mnemonique) if t else None

    def poser(self, objet_id, code, libelle, ancien_code):
        from apps.core.models import Nomenclature
        t = (Nomenclature.objects.filter(id_type__mnemonique='TYPE_PRESSION', cd_nomenclature=code)
             .order_by('-actif', 'id_nomenclature').first())
        self._qs().filter(pk=objet_id).update(id_type_pression=t)

    def plan(self, objet_id):
        p = self._qs().filter(pk=objet_id).first()
        return p.get_plan_de_gestion() if p else None


# ---------------------------------------------------------------------------
# TaxRef / HabRef : lignes de liaison qui portent un code et son libellé
# ---------------------------------------------------------------------------

class LiaisonCode(Cible):
    """Ligne `cor_*` portant un code (cd_nom, cd_hab) et son libellé dénormalisé.

    Deux anciens codes peuvent fusionner : si le parent porte déjà le nouveau
    code, la ligne devient un doublon et est supprimée (contrainte d'unicité).
    """
    modele = ''
    parent = ''            # champ FK du parent (id_enjeu, id_responsabilite)
    champ_code = ''
    champ_libelle = ''
    entier = False

    def _modele(self):
        from django.apps import apps
        return apps.get_model('plans', self.modele)

    def _contexte(self, obj) -> str:
        return str(getattr(obj, self.parent))

    def _plan_de(self, obj):
        return None

    def objets(self):
        qs = (self._modele().objects.select_related(self.parent)
              .exclude(**{f'{self.champ_code}__isnull': True}).order_by('pk'))
        for obj in qs:
            code = getattr(obj, self.champ_code)
            if code in (None, ''):
                continue
            yield ObjetCible(self, obj.pk, self._plan_de(obj), str(code),
                             getattr(obj, self.champ_libelle) or '', self._contexte(obj))

    def valeur(self, objet_id, ancien_code=None):
        obj = self._modele().objects.filter(pk=objet_id).first()
        return str(getattr(obj, self.champ_code)) if obj else None

    def poser(self, objet_id, code, libelle, ancien_code):
        M = self._modele()
        obj = M.objects.filter(pk=objet_id).first()
        if obj is None:
            return
        valeur = int(code) if self.entier else code
        doublon = M.objects.filter(**{self.parent: getattr(obj, f'{self.parent}_id'),
                                      self.champ_code: valeur}).exclude(pk=obj.pk)
        if doublon.exists():
            obj.delete()
            return
        setattr(obj, self.champ_code, valeur)
        setattr(obj, self.champ_libelle, libelle)
        obj.save(update_fields=[self.champ_code, self.champ_libelle])

    def plan(self, objet_id):
        obj = self._modele().objects.select_related(self.parent).filter(pk=objet_id).first()
        return self._plan_de(obj) if obj else None


class EnjeuTaxon(LiaisonCode):
    nom = 'enjeu_taxon'
    libelle = "Taxon d'un enjeu"
    modele, parent, champ_code, champ_libelle, entier = (
        'CorEnjeuTaxon', 'id_enjeu', 'cd_nom', 'nom_complet', True)

    def _contexte(self, obj):
        return f"Enjeu « {obj.id_enjeu.libelle or obj.id_enjeu.intitule_court or obj.id_enjeu_id} »"

    def _plan_de(self, obj):
        return obj.id_enjeu.id_pg


class ResponsabiliteTaxon(LiaisonCode):
    nom = 'responsabilite_taxon'
    libelle = "Taxon d'une responsabilité de site"
    modele, parent, champ_code, champ_libelle, entier = (
        'CorResponsabiliteTaxon', 'id_responsabilite', 'cd_nom', 'nom_complet', True)


class EnjeuHabitat(LiaisonCode):
    nom = 'enjeu_habitat'
    libelle = "Habitat d'un enjeu"
    modele, parent, champ_code, champ_libelle = (
        'CorEnjeuHabitat', 'id_enjeu', 'cd_hab', 'lb_hab_fr')

    def _contexte(self, obj):
        return f"Enjeu « {obj.id_enjeu.libelle or obj.id_enjeu.intitule_court or obj.id_enjeu_id} »"

    def _plan_de(self, obj):
        return obj.id_enjeu.id_pg


class ResponsabiliteHabitat(LiaisonCode):
    nom = 'responsabilite_habitat'
    libelle = "Habitat d'une responsabilité de site"
    modele, parent, champ_code, champ_libelle = (
        'CorResponsabiliteHabitat', 'id_responsabilite', 'cd_hab', 'lb_hab_fr')


class SuiviHabitat(Cible):
    """Habitats structurés d'un suivi (`habitats` : [{cd_hab, lb_hab_fr}]).
    L'objet est le suivi ; l'ancien code désigne l'entrée."""
    nom = 'suivi_habitat'
    libelle = "Habitat d'un suivi"

    def _qs(self):
        from apps.plans.models_operations import SuiviInventaire
        return SuiviInventaire.objects.select_related('id_pg')

    def objets(self):
        for s in self._qs().exclude(habitats=[]).order_by('pk'):
            for h in s.habitats or []:
                code = str(h.get('cd_hab') or '')
                if code:
                    yield ObjetCible(self, s.pk, s.id_pg, code, h.get('lb_hab_fr') or '',
                                     f"Suivi « {s.intitule or s.pk} »")

    def valeur(self, objet_id, ancien_code=None):
        s = self._qs().filter(pk=objet_id).first()
        codes = [str(h.get('cd_hab')) for h in (s.habitats or [])] if s else []
        return ancien_code if ancien_code in codes else None

    def poser(self, objet_id, code, libelle, ancien_code):
        s = self._qs().filter(pk=objet_id).first()
        if s is None:
            return
        habitats, deja = [], {str(h.get('cd_hab')) for h in s.habitats or []}
        for h in s.habitats or []:
            if str(h.get('cd_hab')) == str(ancien_code):
                if str(code) in deja:
                    continue
                h = {**h, 'cd_hab': code, 'lb_hab_fr': libelle}
            habitats.append(h)
        s.habitats = habitats
        s.save(update_fields=['habitats'])

    def plan(self, objet_id):
        s = self._qs().filter(pk=objet_id).first()
        return s.id_pg if s else None


CIBLES = {c.nom: c for c in (PressionType(), EnjeuTaxon(), ResponsabiliteTaxon(),
                             EnjeuHabitat(), ResponsabiliteHabitat(), SuiviHabitat())}
