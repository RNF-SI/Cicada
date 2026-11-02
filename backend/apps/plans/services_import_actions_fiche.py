"""
#786 — Classeur des actions réimportable sur une autre instance.

Complète ``services_import_actions.py`` (budget / RH) avec le reste de la fiche
action et ce qui doit voyager avec elle :

- colonnes supplémentaires de l'onglet « Actions » (catégorie réserve,
  partenaires, fréquence, mois par défaut, sites, métriques, suivi…) ;
- onglets ``Annees`` (années programmées et mois), ``Emprises`` (GeoJSON,
  découpé en parties : une cellule Excel est limitée à 32 767 caractères),
  ``Fonctions`` (fonctions des postes, par libellé et code de type de poste),
  ``Suivis`` et ``Protocoles`` (suivi des actions CS, #642 / #715) ;
- résolution des références **sans identifiant local** : un indicateur se
  retrouve par son nom (et son enjeu), un organisme par son nom parmi les
  gestionnaires des sites du plan, un poste par son libellé et son organisme —
  et il est créé s'il manque (décision Q4 de l'issue).

Seule la programmation voyage : le réalisé (suivi des réalisations) n'est pas
exporté (Q3). L'import reste une création (Q2) : un plan qui a déjà des actions
est refusé.

Les colonnes d'un modèle sont décrites par ``Champ`` et converties par un codec
commun (``vers_cellule`` / ``depuis_cellule``) : ajouter un champ au suivi ou
au protocole revient à l'ajouter à une liste.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

# Une cellule Excel contient au plus 32 767 caractères.
TAILLE_PARTIE_GEOJSON = 30000
ANNEE_GLOBALE = "Période"


@dataclass(frozen=True)
class Champ:
    """Une colonne de classeur liée à un champ de modèle.

    ``genre`` : ``texte``, ``bool`` (Oui / Non / vide = inconnu), ``entier``,
    ``decimal``, ``json``, ``date``, ``mois`` (« 1,4,5 » ↔ {"1": true…}) ou
    ``nom:<TYPE>`` (nomenclature désignée par son libellé).
    """

    cle: str
    entete: str
    genre: str = "texte"
    largeur: int = 18
    aide: str = ""


# --- Codec cellule ↔ valeur -------------------------------------------------


def _str(value) -> str:
    from .services_import import _cell_str
    return _cell_str(value)


def vers_cellule(value, genre):
    if value is None:
        return ""
    if genre == "bool":
        return "Oui" if value else "Non"
    if genre.startswith("nom:"):
        return value.label or ""
    if genre == "json":
        return json.dumps(value, ensure_ascii=False) if value not in ({}, []) else ""
    if genre == "date":
        return value.isoformat()
    if genre == "mois":
        return ",".join(str(m) for m in range(1, 13) if (value or {}).get(str(m)))
    if genre == "decimal":
        d = Decimal(value)
        return int(d) if d == d.to_integral_value() else float(d)
    return value


def depuis_cellule(raw, genre, resolver=None):
    """Renvoie ``(valeur, erreur)`` ; ``erreur`` est un message lisible."""
    from .services_import import _as_int, _parse_bool

    text = _str(raw)
    if genre == "mois":
        if not text:
            return {}, None
        try:
            mois = {int(float(t)) for t in text.replace(";", ",").split(",") if t.strip()}
        except ValueError:
            return None, "liste de mois attendue (ex : 3,4,5)"
        if any(m < 1 or m > 12 for m in mois):
            return None, "les mois vont de 1 à 12"
        return {str(m): m in mois for m in range(1, 13)}, None
    if not text:
        return (None, None)
    if genre == "bool":
        v = _parse_bool(text)
        return (v, None) if v is not None else (None, "Oui ou Non attendu")
    if genre == "entier":
        v = _as_int(text)
        return (v, None) if v is not None else (None, "nombre entier attendu")
    if genre == "decimal":
        try:
            return Decimal(text.replace(",", ".").replace(" ", "")), None
        except InvalidOperation:
            return None, "nombre attendu"
    if genre == "json":
        try:
            return json.loads(text), None
        except ValueError:
            return None, "contenu JSON illisible"
    if genre == "date":
        if isinstance(raw, datetime):
            return raw.date(), None
        if isinstance(raw, date):
            return raw, None
        try:
            return date.fromisoformat(text[:10]), None
        except ValueError:
            return None, "date attendue (AAAA-MM-JJ)"
    if genre.startswith("nom:"):
        nom = resolver.resolve(genre[4:], text) if resolver else None
        return (nom, None) if nom is not None else (None, f"valeur « {text} » non reconnue")
    return text, None


def ligne_objet(obj, champs) -> dict:
    return {c.cle: vers_cellule(getattr(obj, c.cle), c.genre) for c in champs}


# --- Colonnes ---------------------------------------------------------------

# Colonnes ajoutées à l'onglet « Actions » (champs simples de la fiche).
CHAMPS_ACTION = [
    Champ("id_categorie_action_reserve", "catégorie réserve",
          "nom:CATEGORIE_ACTION_RESERVE", 24, "Catégorie d'action réserve (CT88)."),
    Champ("numero_manuel", "numéro fixé", "entier", 10,
          "Numéro fixé à la main dans le code de l'action (vide = automatique)."),
    Champ("action_restauration", "action de restauration", "bool", 14),
    Champ("partenaires", "partenaires", "texte", 30),
    Champ("frequence_nombre", "fréquence (nombre)", "entier", 12),
    Champ("frequence_unite", "fréquence (unité)", "texte", 12,
          "jour, semaine, mois ou an."),
    Champ("programmation_mensuelle_defaut", "mois par défaut", "mois", 16,
          "Mois programmés par défaut, séparés par des virgules (ex : 4,5,6)."),
    Champ("emprise_suit_sites", "emprise = sites", "bool", 12,
          "Oui : l'emprise de l'action reprend celle de ses sites."),
    Champ("est_suivi_existant", "suivi existant", "bool", 12,
          "Action CS : le suivi existait-il déjà ?"),
]
# Colonnes « techniques » de l'onglet Actions, gérées hors du codec.
COLONNES_ACTION_REFS = [
    ("declinaison_par_poste", "déclinaison par type de poste", False,
     "Oui : temps de travail saisi par poste (toujours le cas dans les modes "
     "« + type de poste »). Laissé vide : déduit de l'onglet « RH ».", None, 18),
    ("programmation_globale", "programmation globale", False,
     "Oui : budget et temps saisis une fois pour la période de l'action, sur "
     f"les lignes dont l'année vaut « {ANNEE_GLOBALE} » (onglets Budgets et RH).",
     None, 16),
    ("sites", "sites", False,
     "Sites de l'action : codes INPN (ou noms) séparés par des virgules, "
     "parmi les sites du plan.", None, 24),
    ("metriques", "métriques", False,
     "Métriques liées, par leur nom, séparées par « ; ».", None, 30),
    ("suivi", "suivi", False, "Code du suivi (onglet « Suivis »).", None, 10),
]

CHAMPS_SUIVI = [
    Champ("intitule", "intitulé", "texte", 30),
    Champ("id_type_action", "type d'action", "nom:TYPE_ACTION", 22),
    Champ("id_statut", "statut", "nom:STATUT_SUIVI", 16),
    Champ("objectif_principal", "objectif principal", "texte", 24),
    Champ("objectif_secondaire", "objectif secondaire", "texte", 24),
    Champ("cibles_principales", "cible principale", "texte", 24),
    Champ("cible_secondaire", "cible secondaire", "texte", 24),
    Champ("taxon_taxref", "taxon (TaxRef)", "texte", 16),
    Champ("habitat_ref", "référentiel habitat", "texte", 16),
    Champ("habitats", "habitats (JSON)", "json", 30),
    Champ("suit_indicateur", "suit un indicateur", "bool", 12),
    Champ("type_indicateur", "type d'indicateur", "texte", 14),
    Champ("frequence_nombre", "fréquence (nombre)", "entier", 12),
    Champ("frequence_unite", "fréquence (unité)", "texte", 12),
    Champ("frequence_unite_precision", "précision fréquence", "texte", 16),
    Champ("annee_fin_suivi", "année de fin", "entier", 10),
    Champ("date_lancement_suivi", "date de lancement", "date", 14),
    Champ("prix_indicatif", "prix indicatif (€/an)", "decimal", 12),
    Champ("outil_saisie", "outil de saisie", "texte", 18),
    Champ("outil_bancarisation", "outil de bancarisation", "texte", 18),
    Champ("transmission_donnee", "transmission de la donnée", "bool", 12),
    Champ("integre_plan_gestion", "intégré au plan de gestion", "bool", 12),
    Champ("actif", "actif", "bool", 10),
    Champ("commentaires", "commentaires", "texte", 30),
]

CHAMPS_PROTOCOLE = [
    Champ("protocole_dans_campanule", "protocole standardisé", "bool", 12),
    Champ("cd_protocole_campanule", "code protocole standardisé", "entier", 14),
    Champ("protocole_campanule_nom", "protocole standardisé (nom)", "texte", 30),
    Champ("nom_protocole", "nom du protocole", "texte", 30),
    Champ("respect_protocole", "respect strict", "bool", 12),
    Champ("justification_non_respect", "justification du non-respect", "texte", 30),
    Champ("differences_protocole", "différences avec le protocole", "texte", 30),
    Champ("description_protocole", "description", "texte", 30),
    Champ("objectif_protocole", "objectif", "texte", 24),
    Champ("mode_validation", "mode de validation", "texte", 20),
    Champ("periode_echantillonnage", "période d'échantillonnage", "texte", 18),
    Champ("periode_suivi", "période de suivi", "texte", 18),
    Champ("nb_etp_cycle", "ETP par cycle", "decimal", 10),
    Champ("documentation_disponible", "documentation disponible", "bool", 12),
    Champ("url_documentation", "URL de la documentation", "texte", 30),
]

CHAMPS_POSTE = [
    Champ("nom_local", "nom local", "texte", 24),
    Champ("organisme_libre", "organisme (saisi)", "texte", 22),
    Champ("nombre", "nombre de postes", "decimal", 10),
    Champ("etp", "ETP total", "decimal", 10),
    Champ("commentaire", "commentaire", "texte", 24),
]


def _colonnes(champs, prefixe=()):
    """Champs → colonnes de ``_write_simple_sheet`` (key, header, req, help, width)."""
    return list(prefixe) + [(c.cle, c.entete, False, c.aide, c.largeur) for c in champs]


COLONNES_ANNEES = [
    ("action", "action", True, "Code de l'action (onglet « Actions »).", 12),
    ("annee", "année", True,
     f"Année, ou « {ANNEE_GLOBALE} » pour la ligne de la programmation globale.", 10),
    ("programmee", "programmée", False, "Oui : l'action est programmée cette année.", 12),
    ("mois", "mois", False, "Mois programmés, séparés par des virgules (ex : 4,5,6).", 16),
    ("organismes", "organismes", False,
     "Codes des organismes de l'année (onglet « Organismes »), même sans "
     "montant : le réalisé par organisme s'y rattache. « O1:12 » = 12 jours "
     "enregistrés pour cet organisme sans ligne de temps (données anciennes).", 16),
    ("budget_enregistre", "budget enregistré (€)", False,
     "Budget total enregistré pour l'année. Repris seulement si l'onglet "
     "« Budgets » n'a aucune ligne pour cette action et cette année (données "
     "saisies avant le détail par organisme ou par type de coût).", 14),
    ("jours_enregistres", "jours enregistrés", False,
     "Temps total enregistré pour l'année. Repris seulement si l'onglet « RH » "
     "n'a aucune ligne pour cette action et cette année (données antérieures "
     "aux postes, #560).", 12),
]
COLONNES_EMPRISES = [
    ("action", "action", True, "Code de l'action (onglet « Actions »).", 12),
    ("annee", "année", False, "Vide : emprise de l'action ; sinon emprise de l'année.", 10),
    ("partie", "partie", True,
     "Numéro de la partie : un GeoJSON long est découpé sur plusieurs lignes.", 8),
    ("geojson", "GeoJSON (WGS 84)", True, "Géométrie GeoJSON, ou sa partie.", 80),
]
COLONNES_FONCTIONS = [
    ("poste", "poste", True, "Code du poste (onglet « Postes »).", 10),
    ("fonction", "fonction", True, "Libellé de la fonction.", 30),
    ("type_poste", "type de poste", False, "Code du type de poste (nomenclature).", 16),
    ("finance_par_defaut", "financée par défaut", False, "Oui / Non.", 12),
    ("pourcentage", "pourcentage", False, "Part du poste consacrée à la fonction.", 12),
]
COLONNES_FINANCEMENTS = [
    ("action", "action", True, "Code de l'action (onglet « Actions »).", 12),
    ("financeur", "financeur", True, "Nom du financeur.", 30),
    ("categorie", "catégorie", False,
     "Catégorie de financement (liste) ; vide si « autre catégorie ».", 22),
    ("categorie_libre", "autre catégorie", False,
     "Catégorie hors liste, propre au plan.", 22),
    ("montant", "montant prévu (€)", False,
     "Montant global sur l'action, facultatif (#790).", 14),
]
COLONNES_SUIVIS = _colonnes(CHAMPS_SUIVI, prefixe=[
    ("code", "code", True, "Code du suivi (ex : S1), repris dans l'onglet « Actions ».", 10),
])
COLONNES_PROTOCOLES = _colonnes(CHAMPS_PROTOCOLE, prefixe=[
    ("suivi", "suivi", True, "Code du suivi (onglet « Suivis »).", 10),
])

ONGLETS_FICHE = {
    # clé : (nom de l'onglet, colonnes, description)
    "annees": ("Annees", COLONNES_ANNEES,
               "Années programmées de chaque action et leurs mois."),
    "emprises": ("Emprises", COLONNES_EMPRISES,
                 "Emprises prévues (GeoJSON en WGS 84), de l'action ou d'une année."),
    "fonctions": ("Fonctions", COLONNES_FONCTIONS,
                  "Fonctions de chaque poste. Un poste absent du plan cible y est "
                  "créé avec ses fonctions."),
    "financements": ("Financements", COLONNES_FINANCEMENTS,
                     "Financeurs de chaque action et montant prévu (facultatif). "
                     "Même nom + même catégorie = un seul financeur du plan."),
    "suivis": ("Suivis", COLONNES_SUIVIS,
               "Suivis / inventaires des actions CS (créés à l'import)."),
    "protocoles": ("Protocoles", COLONNES_PROTOCOLES,
                   "Protocoles de chaque suivi, dans leur ordre de saisie."),
}


def entetes(colonnes) -> dict:
    from .services_import import _norm
    return {_norm(c[1]): c[0] for c in colonnes}


# --- Années (programmation globale) ------------------------------------------


def lire_annee(raw):
    """``(annee, ok)`` : un entier, ``None`` pour la période (programmation
    globale) ; ``ok`` faux si la cellule est illisible."""
    from .services_import import _as_int, _norm

    text = _str(raw)
    if not text:
        return None, False
    if _norm(text) in (_norm(ANNEE_GLOBALE), "global", "periode (global)"):
        return None, True
    value = _as_int(text)
    return value, value is not None


def cellule_annee(annee):
    return ANNEE_GLOBALE if annee is None else annee


def annees_operation(op):
    """Toutes les lignes de programmation de l'action, période globale en tête
    (le gestionnaire par défaut l'exclut, #735)."""
    from django.db.models import F

    from .models_operations import OperationAnnee

    return (OperationAnnee.tous.filter(id_operation=op)
            .order_by(F("annee").asc(nulls_first=True)))


# --- Extraction (export) -----------------------------------------------------


def _geojson(geom):
    return geom.json if geom is not None else ""


def _a_du_temps(oa):
    return oa.rh_lignes.exists()


def _parties(texte):
    return [texte[i:i + TAILLE_PARTIE_GEOJSON]
            for i in range(0, len(texte), TAILLE_PARTIE_GEOJSON)] or [""]


def extraire_fiche(ops, op_code, poste_code_by_id, postes, org_code_by_id=None):
    """Lignes des onglets de la fiche, et valeurs des colonnes ajoutées à
    « Actions » (``{code action: {clé: valeur}}``)."""
    rows = {k: [] for k in ONGLETS_FICHE}
    colonnes_action: dict[str, dict] = {}
    suivi_codes: dict[int, str] = {}

    for op in ops:
        code = op_code(op)
        extra = ligne_objet(op, CHAMPS_ACTION)
        extra["declinaison_par_poste"] = "Oui" if op.temps_par_poste() else "Non"
        extra["programmation_globale"] = "Oui" if op.programmation_globale else "Non"
        extra["sites"] = ", ".join(
            (s.id_inpn or s.nom_site or "") for s in op.sites.all().order_by("id_site"))
        extra["metriques"] = " ; ".join(
            m.nom_metrique for m in op.metriques.all().order_by("ordre", "id_metrique"))
        if op.id_suivi_id:
            if op.id_suivi_id not in suivi_codes:
                s_code = f"S{len(suivi_codes) + 1}"
                suivi_codes[op.id_suivi_id] = s_code
                suivi = op.id_suivi
                rows["suivis"].append({"code": s_code, **ligne_objet(suivi, CHAMPS_SUIVI)})
                for proto in suivi.protocoles.all():
                    rows["protocoles"].append(
                        {"suivi": s_code, **ligne_objet(proto, CHAMPS_PROTOCOLE)})
            extra["suivi"] = suivi_codes[op.id_suivi_id]
        colonnes_action[code] = extra
        for fin in op.finances.select_related("id_financeur", "id_categorie").order_by(
                "id_finance_operation"):
            f = fin.id_financeur
            rows["financements"].append({
                "action": code,
                "financeur": f.nom if f else fin.libelle,
                "categorie": (f.id_categorie.label if f and f.id_categorie_id else
                              (fin.id_categorie.label if fin.id_categorie_id else "")),
                "categorie_libre": f.categorie_libre if f else "",
                "montant": vers_cellule(fin.montant, "decimal"),
            })

        for i, partie in enumerate(_parties(_geojson(op.geom)), start=1):
            if partie:
                rows["emprises"].append(
                    {"action": code, "annee": "", "partie": i, "geojson": partie})
        for oa in annees_operation(op):
            rows["annees"].append({
                "action": code,
                "annee": cellule_annee(oa.annee),
                "programmee": "Oui" if oa.periodicite else "Non",
                "mois": vers_cellule(oa.periodicite_mensuelle, "mois"),
                "organismes": ",".join(
                    (org_code_by_id or {})[o.id_organisme_id]
                    + (f":{vers_cellule(o.etp, 'decimal')}"
                       if o.etp is not None and not _a_du_temps(oa) else "")
                    for o in oa.organismes.all().order_by("id_operation_annee_organisme")
                    if (org_code_by_id or {}).get(o.id_organisme_id)),
                "budget_enregistre": vers_cellule(oa.budget, "decimal"),
                "jours_enregistres": vers_cellule(oa.etp, "decimal") if not _a_du_temps(oa) else "",
            })
            for i, partie in enumerate(_parties(_geojson(oa.geom)), start=1):
                if partie:
                    rows["emprises"].append({
                        "action": code, "annee": cellule_annee(oa.annee),
                        "partie": i, "geojson": partie})

    for poste in postes:
        for pf in poste.fonctions.all():
            f = pf.id_fonction
            rows["fonctions"].append({
                "poste": poste_code_by_id[poste.id_poste],
                "fonction": f.libelle,
                "type_poste": f.id_type_poste.cd_nomenclature if f.id_type_poste else "",
                "finance_par_defaut": "Oui" if f.finance_par_defaut else "Non",
                "pourcentage": vers_cellule(pf.pourcentage, "decimal"),
            })
    return rows, colonnes_action


# --- Résolution des références (import, autre instance) ----------------------


def resoudre_references(plan, parsed, report):
    """Rattache les codes du classeur aux objets du plan cible, sans se fier
    aux identifiants (ceux d'une autre instance n'y ont aucun sens).

    Renvoie une copie de ``parsed`` où ``indicateurs`` / ``organismes`` /
    ``postes`` donnent des identifiants **du plan cible** (ou ``None``), et
    ``postes_a_creer`` les postes absents (créés à l'import, Q4)."""
    from .services_import import WARNING, _norm
    from .services_import_actions import _plan_indicateurs, _plan_organismes, _plan_postes

    out = dict(parsed)
    if parsed.get("_resolu"):
        return out
    out["_resolu"] = True

    # Indicateurs : identifiant du plan, sinon nom (+ enjeu) unique.
    indicateurs = _plan_indicateurs(plan)
    ids = {ind.id_indicateur for ind, _ in indicateurs}
    noms = parsed.get("indicateurs_noms", {})
    resolu = {}
    for code, ident in parsed.get("indicateurs", {}).items():
        if ident in ids:
            resolu[code] = ident
            continue
        nom, enjeu = noms.get(code, ("", ""))
        candidats = [i for i, e in indicateurs if _norm(i.nom_indicateur) == _norm(nom)]
        if len(candidats) > 1 and enjeu:
            candidats = [i for i, e in indicateurs
                         if _norm(i.nom_indicateur) == _norm(nom) and _norm(e) == _norm(enjeu)]
        # Introuvable : l'identifiant d'origine reste, la validation le signale
        # (avec le nom, cf. ``nom_reference``).
        resolu[code] = candidats[0].id_indicateur if len(candidats) == 1 else ident
    out["indicateurs"] = resolu

    # Organismes : identifiant, sinon nom, parmi les gestionnaires des sites.
    plan_orgs = [org for org, _s in _plan_organismes(plan)]
    org_ids = {o.id_organisme for o in plan_orgs}
    org_noms = parsed.get("organismes_noms", {})
    orgs, hors = {}, set()
    for code, ident in parsed.get("organismes", {}).items():
        if ident in org_ids:
            orgs[code] = ident
            continue
        nom = org_noms.get(code, "")
        match = [o for o in plan_orgs if nom and _norm(o.nom_organisme) == _norm(nom)]
        if not match and nom:
            # Organisme utilisé par les actions sans gérer les sites du plan :
            # retrouvé dans l'instance par son nom (#786).
            from apps.users.models import BibOrganismes
            autre = [o for o in BibOrganismes.objects.filter(nom_organisme__iexact=nom)
                     if _norm(o.nom_organisme) == _norm(nom)]
            if autre:
                hors.add(autre[0].id_organisme)
                report.add("Organismes", None, "organisme", WARNING,
                           f"Organisme « {code} » (« {nom} ») : il ne gère aucun site "
                           "de ce plan, ses montants lui sont tout de même rattachés.")
                match = autre
        orgs[code] = match[0].id_organisme if match else ident
    out["organismes"] = orgs
    out["organismes_hors_gestionnaires"] = hors

    # Postes : identifiant du plan, sinon libellé + organisme, sinon à créer.
    postes = _plan_postes(plan)
    poste_ids = {p.id_poste for p in postes}
    details = parsed.get("postes_details", {})
    resolus, a_creer = {}, {}
    for code, ident in parsed.get("postes", {}).items():
        if ident in poste_ids:
            resolus[code] = ident
            continue
        d = details.get(code)
        if not d:  # pas de quoi le retrouver ni le créer
            resolus[code] = ident
            continue
        libelle = _norm(d.get("nom_local") or d.get("poste"))
        org = _norm(d.get("organisme"))
        match = [p for p in postes if libelle and _norm(p.libelle) == libelle
                 and _norm(p.organisme_affichage) == org]
        if match:
            resolus[code] = match[0].id_poste
            continue
        resolus[code] = None
        a_creer[code] = d
        report.add("Postes", d.get("_row"), "poste", WARNING,
                   f"Poste « {code} » (« {d.get('poste') or code} ») absent de ce "
                   "plan : il sera créé, avec ses fonctions.")
        if d.get("organisme") and not any(
                _norm(o.nom_organisme) == org for o in plan_orgs):
            report.add("Postes", d.get("_row"), "organisme", WARNING,
                       f"Organisme « {d.get('organisme')} » du poste « {code} » "
                       "absent des gestionnaires des sites du plan : il sera "
                       "repris comme organisme saisi.")
    out["postes"] = resolus
    out["postes_a_creer"] = a_creer
    return out


# --- Validation des onglets de la fiche --------------------------------------


def valider_fiche(plan, parsed, report, resolver, action_codes, globales):
    from .services_import import ERROR, WARNING, _norm

    for row in parsed.get("actions", []):
        for c in CHAMPS_ACTION:
            _v, err = depuis_cellule(row.get(c.cle), c.genre, resolver)
            if err:
                report.add("Actions", row["_row"], c.cle, ERROR, f"« {c.entete} » : {err}.")
        suivi = _str(row.get("suivi"))
        if suivi and suivi not in {_str(s.get("code")) for s in parsed.get("suivis", [])}:
            report.add("Actions", row["_row"], "suivi", ERROR,
                       f"Suivi « {suivi} » introuvable dans l'onglet « Suivis ».")

    def _action_annee(sheet, row, annee_requise=True):
        ac = _str(row.get("action"))
        if ac not in action_codes:
            report.add(sheet, row["_row"], "action", ERROR,
                       f"Action « {ac} » introuvable dans l'onglet « Actions ».")
        if not annee_requise and not _str(row.get("annee")):
            return
        annee, ok = lire_annee(row.get("annee"))
        if not ok:
            report.add(sheet, row["_row"], "annee", ERROR,
                       f"Année attendue (un nombre, ou « {ANNEE_GLOBALE} »).")
        elif annee is None and ac not in globales:
            report.add(sheet, row["_row"], "annee", ERROR,
                       f"« {ANNEE_GLOBALE} » réservé aux actions en programmation globale.")

    org_ids = _org_ids_acceptes(plan, parsed)
    for row in parsed.get("annees", []):
        _action_annee("Annees", row)
        for entree in _liste(row.get("organismes"), ","):
            org_code = entree.partition(":")[0].strip()
            if parsed.get("organismes", {}).get(org_code) not in org_ids:
                report.add("Annees", row["_row"], "organismes", ERROR,
                           f"Organisme « {org_code} » introuvable parmi les "
                           "gestionnaires des sites de ce plan.")
        for col, genre in (("programmee", "bool"), ("mois", "mois")):
            _v, err = depuis_cellule(row.get(col), genre)
            if err:
                report.add("Annees", row["_row"], col, ERROR, f"« {col} » : {err}.")

    for (ac, annee), texte in assembler_emprises(parsed).items():
        row = texte["_row"]
        try:
            _geometrie(texte["geojson"])
        except ValueError as exc:
            report.add("Emprises", row, "geojson", ERROR,
                       f"Emprise de l'action « {ac} » illisible : {exc}")
    for row in parsed.get("emprises", []):
        _action_annee("Emprises", row, annee_requise=False)

    postes = set(parsed.get("postes", {}))
    for row in parsed.get("fonctions", []):
        if _str(row.get("poste")) not in postes:
            report.add("Fonctions", row["_row"], "poste", ERROR,
                       f"Poste « {_str(row.get('poste'))} » introuvable dans l'onglet « Postes ».")
        if not _str(row.get("fonction")):
            report.add("Fonctions", row["_row"], "fonction", ERROR, "Libellé obligatoire.")
        tp = _str(row.get("type_poste"))
        if tp and _type_poste(tp) is None:
            report.add("Fonctions", row["_row"], "type_poste", WARNING,
                       f"Type de poste « {tp} » inconnu : la fonction sera créée sans type.")

    for row in parsed.get("financements", []):
        if _str(row.get("action")) not in action_codes:
            report.add("Financements", row["_row"], "action", ERROR,
                       f"Action « {_str(row.get('action'))} » introuvable dans l'onglet « Actions ».")
        if not _str(row.get("financeur")):
            report.add("Financements", row["_row"], "financeur", ERROR, "Nom obligatoire.")
        for col, genre in (("categorie", "nom:CATEGORIE_FINANCE"), ("montant", "decimal")):
            _v, err = depuis_cellule(row.get(col), genre, resolver)
            if err:
                report.add("Financements", row["_row"], col, ERROR, f"« {col} » : {err}.")

    codes_suivis = set()
    for row in parsed.get("suivis", []):
        code = _str(row.get("code"))
        if not code or code in codes_suivis:
            report.add("Suivis", row["_row"], "code", ERROR, "Code manquant ou en double.")
        codes_suivis.add(code)
        for c in CHAMPS_SUIVI:
            _v, err = depuis_cellule(row.get(c.cle), c.genre, resolver)
            if err:
                report.add("Suivis", row["_row"], c.cle, ERROR, f"« {c.entete} » : {err}.")
    for row in parsed.get("protocoles", []):
        if _str(row.get("suivi")) not in codes_suivis:
            report.add("Protocoles", row["_row"], "suivi", ERROR,
                       f"Suivi « {_str(row.get('suivi'))} » introuvable dans l'onglet « Suivis ».")
        for c in CHAMPS_PROTOCOLE:
            _v, err = depuis_cellule(row.get(c.cle), c.genre, resolver)
            if err:
                report.add("Protocoles", row["_row"], c.cle, ERROR, f"« {c.entete} » : {err}.")

    # Sites et métriques : retrouvés par leur nom ; un absent est ignoré.
    sites = _sites_du_plan(plan)
    for row in parsed.get("actions", []):
        for token in _liste(row.get("sites"), ","):
            if _site(sites, token) is None:
                report.add("Actions", row["_row"], "sites", WARNING,
                           f"Site « {token} » absent de ce plan : ignoré.")
        for token in _liste(row.get("metriques"), ";"):
            if not _metriques_nommees(plan, token):
                report.add("Actions", row["_row"], "metriques", WARNING,
                           f"Métrique « {token} » absente de ce plan : ignorée.")


# --- Exécution ----------------------------------------------------------------


def _liste(raw, sep):
    return [t.strip() for t in _str(raw).split(sep) if t.strip()]


def _organismes_du_plan(plan):
    from .services_import_actions import _plan_organismes
    return [org for org, _s in _plan_organismes(plan)]


def _org_ids_acceptes(plan, parsed):
    return ({o.id_organisme for o in _organismes_du_plan(plan)}
            | set(parsed.get("organismes_hors_gestionnaires", ())))


def _sites_du_plan(plan):
    from apps.users.models import Site
    return list(Site.objects.filter(
        id_site__in=plan.sites.values_list("site_id", flat=True)).order_by("id_site"))


def _site(sites, token):
    from .services_import import _norm
    for s in sites:
        if s.id_inpn and _norm(s.id_inpn) == _norm(token):
            return s
    for s in sites:
        if _norm(s.nom_site) == _norm(token):
            return s
    return None


def _metriques_nommees(plan, nom):
    from .models_indicateurs import Metrique
    from .services_import import _norm
    from .services_import_actions import _plan_indicateurs

    ids = [ind.id_indicateur for ind, _ in _plan_indicateurs(plan)]
    return [m for m in Metrique.objects.filter(id_indicateur_id__in=ids)
            if _norm(m.nom_metrique) == _norm(nom)]


def _type_poste(code):
    from apps.core.models import Nomenclature
    return (Nomenclature.objects.filter(id_type__mnemonique="TYPE_POSTE")
            .filter(cd_nomenclature=code).first()
            or Nomenclature.objects.filter(id_type__mnemonique="TYPE_POSTE",
                                           mnemonique=code).first())


def _geometrie(texte):
    from django.contrib.gis.geos import GEOSGeometry
    try:
        geom = GEOSGeometry(texte, srid=4326)
    except Exception as exc:  # noqa: BLE001
        raise ValueError("GeoJSON attendu") from exc
    return geom


def assembler_emprises(parsed):
    """GeoJSON de chaque (action, année), parties remises bout à bout."""
    parties: dict = {}
    for row in parsed.get("emprises", []):
        annee, _ok = lire_annee(row.get("annee")) if _str(row.get("annee")) else ("action", True)
        cle = (_str(row.get("action")), annee)
        from .services_import import _as_int
        parties.setdefault(cle, []).append((_as_int(row.get("partie")) or 1, row))
    out = {}
    for cle, morceaux in parties.items():
        morceaux.sort(key=lambda m: m[0])
        out[cle] = {"geojson": "".join(_str(r.get("geojson")) for _n, r in morceaux),
                    "_row": morceaux[0][1]["_row"]}
    return out


def _vide(model, champ, valeur):
    """Texte vide : ``None`` si la colonne l'accepte, ``""`` sinon."""
    if valeur:
        return valeur
    return None if model._meta.get_field(champ).null else ""


def creer_postes(plan, parsed):
    """Crée les postes absents du plan (Q4) avec leurs fonctions ; renvoie
    ``{code: id_poste}``."""
    from .models_operations import Fonction, Poste, PosteFonction
    from .services_import import _norm
    from .services_import_actions import _plan_organismes

    orgs = {_norm(o.nom_organisme): o for o, _s in _plan_organismes(plan)}
    fonctions = [r for r in parsed.get("fonctions", [])]
    crees = {}
    for code, d in parsed.get("postes_a_creer", {}).items():
        org = orgs.get(_norm(d.get("organisme")))
        cout, _e = depuis_cellule(d.get("cout_jour"), "decimal")
        poste = Poste.objects.create(
            id_pg=plan, id_organisme=org,
            organisme_libre=_vide(Poste, "organisme_libre", _str(d.get("organisme_libre"))
                                  or ("" if org else _str(d.get("organisme")))),
            nom_local=_vide(Poste, "nom_local", _str(d.get("nom_local"))),
            commentaire=_vide(Poste, "commentaire", _str(d.get("commentaire"))),
            nombre=depuis_cellule(d.get("nombre"), "decimal")[0] or 1,
            etp=depuis_cellule(d.get("etp"), "decimal")[0],
            cout_jour=cout,
        )
        for row in fonctions:
            if _str(row.get("poste")) != code:
                continue
            libelle = _str(row.get("fonction"))
            fonction = (Fonction.objects.filter(libelle=libelle, id_pg=plan).first()
                        or Fonction.objects.filter(libelle=libelle, id_pg__isnull=True).first())
            if fonction is None:
                finance = depuis_cellule(row.get("finance_par_defaut"), "bool")[0]
                fonction = Fonction.objects.create(
                    libelle=libelle, id_pg=plan,
                    id_type_poste=_type_poste(_str(row.get("type_poste"))),
                    finance_par_defaut=True if finance is None else finance,
                )
            PosteFonction.objects.create(
                id_poste=poste, id_fonction=fonction,
                pourcentage=depuis_cellule(row.get("pourcentage"), "decimal")[0])
        crees[code] = poste.id_poste
    return crees


def appliquer_fiche(plan, parsed, user, op_by_code, get_annee, resolver):
    """Écrit le reste de la fiche sur les actions créées."""
    from .models_operations import OperationAnneeOrganisme, Protocole, SuiviInventaire

    # Suivis et protocoles (créés dans le plan cible).
    suivis = {}
    for row in parsed.get("suivis", []):
        valeurs = {c.cle: depuis_cellule(row.get(c.cle), c.genre, resolver)[0]
                   for c in CHAMPS_SUIVI}
        valeurs = {k: v for k, v in valeurs.items() if v is not None}
        suivis[_str(row.get("code"))] = SuiviInventaire.objects.create(
            id_pg=plan, id_utilisateur_ajout=user, **valeurs)
    for row in parsed.get("protocoles", []):
        suivi = suivis.get(_str(row.get("suivi")))
        if suivi is None:
            continue
        valeurs = {c.cle: depuis_cellule(row.get(c.cle), c.genre, resolver)[0]
                   for c in CHAMPS_PROTOCOLE}
        proto = Protocole.objects.create(
            id_utilisateur_ajout=user, **{k: v for k, v in valeurs.items() if v is not None})
        suivi.protocoles.add(proto)

    # Financements (#790) : financeur du plan retrouvé ou créé.
    from .models_operations import FinanceOperation, Financeur
    for row in parsed.get("financements", []):
        op = op_by_code.get(_str(row.get("action")))
        if op is None or not _str(row.get("financeur")):
            continue
        cat = depuis_cellule(row.get("categorie"), "nom:CATEGORIE_FINANCE", resolver)[0]
        financeur = Financeur.pour(plan, _str(row.get("financeur")), cat,
                                   _str(row.get("categorie_libre")))
        FinanceOperation.objects.create(
            id_operation=op, id_financeur=financeur, libelle=financeur.nom,
            id_categorie=financeur.id_categorie,
            montant=depuis_cellule(row.get("montant"), "decimal")[0])

    sites = _sites_du_plan(plan)
    for row in parsed.get("actions", []):
        op = op_by_code.get(_str(row.get("code")))
        if op is None:
            continue
        for c in CHAMPS_ACTION:
            value = depuis_cellule(row.get(c.cle), c.genre, resolver)[0]
            if c.genre == "mois" or value is not None:
                setattr(op, c.cle, value)
        op.id_suivi = suivis.get(_str(row.get("suivi")))
        op.save()
        site_ids = [s.id_site for s in (_site(sites, t) for t in _liste(row.get("sites"), ","))
                    if s is not None]
        if site_ids:
            from .models_operations import CorOperationSite
            CorOperationSite.objects.bulk_create(
                [CorOperationSite(id_operation=op, id_site_id=sid) for sid in site_ids],
                ignore_conflicts=True)
        metriques = []
        for nom in _liste(row.get("metriques"), ";"):
            candidats = _metriques_nommees(plan, nom)
            preferees = [m for m in candidats if m.id_indicateur_id == op.id_indicateur_id]
            if preferees or candidats:
                metriques.append((preferees or candidats)[0])
        if metriques:
            op.metriques.add(*metriques)

    # Années : programmée et mois, tels que saisis (après les totaux).
    def _cles(rows):
        return {(_str(r.get("action")), lire_annee(r.get("annee"))[0]) for r in rows}
    avec_budget, avec_temps = _cles(parsed.get("budgets", [])), _cles(parsed.get("rh", []))
    for row in parsed.get("annees", []):
        code = _str(row.get("action"))
        if code not in op_by_code:
            continue
        annee, ok = lire_annee(row.get("annee"))
        if not ok:
            continue
        oa = get_annee(code, annee)
        programmee = depuis_cellule(row.get("programmee"), "bool")[0]
        if programmee is not None:
            oa.periodicite = programmee
        oa.periodicite_mensuelle = depuis_cellule(row.get("mois"), "mois")[0] or {}
        # Totaux enregistrés (données anciennes) : seulement là où les onglets
        # Budgets / RH ne disent rien, pour ne jamais écraser une saisie.
        cle = (code, annee)
        if cle not in avec_budget:
            budget = depuis_cellule(row.get("budget_enregistre"), "decimal")[0]
            if budget is not None:
                oa.budget = budget
        if cle not in avec_temps:
            jours = depuis_cellule(row.get("jours_enregistres"), "decimal")[0]
            if jours is not None:
                oa.etp = jours
        oa.save()
        for entree in _liste(row.get("organismes"), ","):
            org_code, _sep, jours = entree.partition(":")
            org_id = parsed.get("organismes", {}).get(org_code.strip())
            if org_id is None:
                continue
            ligne, _c = OperationAnneeOrganisme.objects.get_or_create(
                id_operation_annee=oa, id_organisme_id=org_id)
            jours = depuis_cellule(jours, "decimal")[0]
            if jours is not None and cle not in avec_temps:
                ligne.etp = jours
                ligne.save(update_fields=["etp"])

    # Emprises.
    for (code, annee), texte in assembler_emprises(parsed).items():
        if code not in op_by_code or not texte["geojson"]:
            continue
        geom = _geometrie(texte["geojson"])
        if annee == "action":
            op = op_by_code[code]
            op.geom = geom
            op.save(update_fields=["geom"])
        else:
            oa = get_annee(code, annee)
            oa.geom = geom
            oa.save(update_fields=["geom"])


def nom_reference(parsed, cle, code) -> str:
    """« (« nom ») » d'un indicateur / organisme / poste du classeur, pour
    les messages de la validation (vide si le classeur ne le donne pas)."""
    if cle == "indicateurs":
        nom = parsed.get("indicateurs_noms", {}).get(code, ("", ""))[0]
    elif cle == "organismes":
        nom = parsed.get("organismes_noms", {}).get(code, "")
    else:
        nom = (parsed.get("postes_details", {}).get(code) or {}).get("poste") or ""
    return f" (« {nom} »)" if nom else ""
