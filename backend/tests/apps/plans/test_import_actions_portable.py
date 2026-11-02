"""
#786 — Les actions d'un plan s'exportent dans un classeur réimportable sur une
**autre instance** : aucun identifiant local ne survit, tout se retrouve par
son nom (indicateurs, organismes, sites, métriques) ou se recrée (postes,
suivis, protocoles). Seule la programmation voyage (décision Q3).

Le test simule l'autre instance : après l'export, le plan d'origine, son site
et son organisme sont supprimés, puis recréés à l'identique (mêmes noms, même
code INPN, nouveaux identifiants) avant l'import de l'arborescence, puis des
actions.
"""

import re
from decimal import Decimal

import pytest
from django.contrib.gis.geos import GEOSGeometry

from apps.core.models import Nomenclature
from apps.plans.models import CorSitePg, PlanGestion
from apps.plans.models_operations import (
    Fonction,
    Operation,
    OperationAnnee,
    Poste,
    PosteFonction,
    Protocole,
    SuiviInventaire,
)
from apps.plans.services_import import (
    build_arborescence_workbook,
    execute_import,
    parse_workbook,
)
from apps.plans.services_import_actions import (
    _MODE_LABELS,
    _plan_operations,
    build_actions_workbook,
    execute_actions_import,
    parse_actions_workbook,
    validate_actions_import,
)
from apps.plans.services_import_actions_fiche import (
    CHAMPS_PROTOCOLE,
    CHAMPS_SUIVI,
    annees_operation,
    ligne_objet,
)
from apps.users.models import BibOrganismes, CorOgSite, Site
from tests.factories.core import NomenclatureFactory
from tests.factories.enjeux import (
    EnjeuFactory,
    IndicateurFactory,
    MetriqueFactory,
    NiveauExigenceFactory,
    ObjectifLongTermeFactory,
    TypeNomenclatureFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import OrganismeFactory, SiteFactory, SuperAdminFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

POLY = '{"type": "Polygon", "coordinates": [[[4.5, 43.5], [4.6, 43.5], [4.6, 43.6], [4.5, 43.5]]]}'
POLY_2024 = '{"type": "Polygon", "coordinates": [[[4.52, 43.52], [4.55, 43.52], [4.55, 43.55], [4.52, 43.52]]]}'


def _nom(type_mnemo, cd, label):
    type_nom = TypeNomenclatureFactory(mnemonique=type_mnemo)
    return NomenclatureFactory(id_type=type_nom, mnemonique=cd, cd_nomenclature=cd, label=label)


def _site_et_organisme(nom_org):
    site = SiteFactory(nom_site="Marais du test", id_inpn="FR9999786")
    org = OrganismeFactory(nom_organisme=nom_org)
    CorOgSite.objects.create(id_site=site, uuid_og=org)
    return site, org


def _plan(user, site):
    plan = PlanGestionFactory(id_utilisateur_ajout=user)
    CorSitePg.objects.create(plan_de_gestion=plan, site=site)
    return plan


def _row(n, action, annee, **values):
    return {"action": action, "annee": annee, "_row": n, **values}


@pytest.fixture
def source():
    user = SuperAdminFactory()
    noms = {
        "type": _nom("TYPE_ACTION", "CS1", "Suivi des habitats"),
        "prio": _nom("PRIORITE_OPERATION", "P1", "Priorité 1"),
        "cat": _nom("CATEGORIE_ACTION_RESERVE", "CS", "Connaissance et suivi"),
        "statut": _nom("STATUT_SUIVI", "EN_COURS", "En cours"),
        "type_poste": _nom("TYPE_POSTE", "SALARIE", "Salarié"),
    }
    site, org = _site_et_organisme("CEN du test #786")
    plan = _plan(user, site)
    enjeu = EnjeuFactory(id_pg=plan, libelle="Prairies humides")
    ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=enjeu))
    ind = IndicateurFactory(id_ne=ne, nom_indicateur="Surface de prairies")
    met = MetriqueFactory(id_indicateur=ind, nom_metrique="Surface fauchée (ha)")

    fonction = Fonction.objects.create(libelle="Garde technicien #786", id_pg=plan,
                                       id_type_poste=noms["type_poste"], finance_par_defaut=True)
    poste = Poste.objects.create(id_pg=plan, id_organisme=org, nombre=2, cout_jour=Decimal("300"),
                                 nom_local="Garde", commentaire="Temps plein")
    PosteFonction.objects.create(id_poste=poste, id_fonction=fonction, pourcentage=Decimal("100"))

    # Budget et temps : posés par l'import (même chemin que la fiche).
    parsed = {
        "actions": [
            {"code": "A1", "indicateur": "I1", "libelle": "Fauche tardive", "_row": 3,
             "annee_min": 2024, "annee_max": 2025,
             "mode_ventilation": _MODE_LABELS["by_org_type_poste"],
             "declinaison_par_type_cout": "Oui", "cout_salarial_auto": "Non",
             "type_action": "Suivi des habitats", "priorite": "Priorité 1"},
            # #735 — « aucune ventilation » à coûts détaillés, sans poste,
            # programmée globalement sur la période.
            {"code": "A2", "indicateur": "I1", "libelle": "Animation locale", "_row": 4,
             "annee_min": 2024, "annee_max": 2026, "mode_ventilation": _MODE_LABELS["none"],
             "declinaison_par_type_cout": "Oui", "declinaison_par_poste": "Non",
             "programmation_globale": "Oui"},
        ],
        "indicateurs": {"I1": ind.id_indicateur},
        "postes": {"Q1": poste.id_poste},
        "organismes": {"O1": org.id_organisme},
        "budgets": [
            _row(3, "A1", 2024, organisme="O1", cout_salarial="1800", cout_stage="300",
                 autre_cout_invest="70", autre_cout_invest_commentaire="Clôture"),
            _row(4, "A1", 2025, organisme="O1", cout_prestataire="1500"),
            _row(5, "A2", "Période", cout_salarial="900", autre_cout="120",
                 autre_cout_commentaire="Salle"),
        ],
        "rh": [
            _row(3, "A1", 2024, poste="Q1", jours="6"),
            _row(4, "A1", 2025, poste="Q1", jours="4", categorie_depense="Investissement"),
            _row(5, "A2", "Période", jours="12"),
        ],
    }
    report = validate_actions_import(plan, parsed)
    assert report.can_import, report.errors
    execute_actions_import(plan, parsed, user)

    # Reste de la fiche, saisi comme à l'écran.
    a1 = Operation.objects.get(code_operation="A1")
    suivi = SuiviInventaire.objects.create(
        id_pg=plan, id_utilisateur_ajout=user, intitule="Suivi de la fauche",
        id_type_action=noms["type"], id_statut=noms["statut"], objectif_principal="Évaluer",
        cibles_principales="Habitats", habitats=[{"cd_hab": 123, "nom": "Prairie"}],
        transmission_donnee=True, frequence_nombre=1, frequence_unite="an")
    for i, nom in enumerate(("Quadrats", "Transects")):
        proto = Protocole.objects.create(
            id_utilisateur_ajout=user, nom_protocole=nom, protocole_dans_campanule=bool(i),
            cd_protocole_campanule=900101 if i else None, respect_protocole=not i,
            justification_non_respect="" if not i else "Adapté au site",
            nb_etp_cycle=Decimal("0.5"))
        suivi.protocoles.add(proto)
    Operation.objects.filter(pk=a1.pk).update(
        id_suivi=suivi, est_suivi_existant=False, id_categorie_action_reserve=noms["cat"],
        partenaires="Commune", action_restauration=True, numero_manuel=7,
        frequence_nombre=2, frequence_unite="an", operateurs="Garde",
        financeurs="Agence de l'eau", description="Fauche après le 15 juillet",
        programmation_mensuelle_defaut={str(m): m in (7, 8) for m in range(1, 13)},
        geom=GEOSGeometry(POLY, srid=4326), emprise_suit_sites=False)
    a1.sites.add(site)
    a1.metriques.add(met)
    # #790 — financeurs du plan et montant prévu global.
    from apps.plans.models_operations import FinanceOperation, Financeur
    cat_fin = _nom("CATEGORIE_FINANCE", "AGENCE", "Agence de l'eau")
    for nom, cat, libre, montant in (("Agence RMC", cat_fin, "", Decimal("1500")),
                                     ("Mécène local", None, "Mécénat", None)):
        f = Financeur.pour(plan, nom, cat, libre)
        FinanceOperation.objects.create(id_operation=a1, id_financeur=f, libelle=nom,
                                        id_categorie=cat, montant=montant)
    oa = OperationAnnee.objects.get(id_operation=a1, annee=2024)
    oa.periodicite_mensuelle = {str(m): m == 7 for m in range(1, 13)}
    oa.geom = GEOSGeometry(POLY_2024, srid=4326)
    oa.save()
    return user, plan


def _geom(g):
    """Emprise comparée à 1e-9 degré près : le GeoJSON arrondit le 15e chiffre."""
    if g is None:
        return None
    return re.sub(r"-?\d+(?:\.\d+)?", lambda m: f"{float(m.group()):.9f}", g.wkt)


def _mois(d):
    """Mois cochés (un dictionnaire partiel ou complet dit la même chose)."""
    return sorted(int(k) for k, v in (d or {}).items() if v)


def _snapshot(plan):
    """Ce qui doit survivre au voyage, sans aucun identifiant."""
    def org(o):
        return o.nom_organisme if o else None

    def montants(src):
        return tuple(getattr(src, f) for f in (
            "budget", "budget_fonctionnement", "budget_investissement", "cout_salarial",
            "cout_salarial_invest", "cout_stage", "cout_prestataire", "autre_cout",
            "autre_cout_commentaire", "cout_prestataire_invest", "autre_cout_invest",
            "autre_cout_invest_commentaire", "etp") if hasattr(src, f))

    snap = {}
    for op in _plan_operations(plan):
        annees = []
        for oa in annees_operation(op):
            annees.append((
                oa.annee, oa.periodicite, _mois(oa.periodicite_mensuelle),
                _geom(oa.geom), montants(oa),
                sorted((org(o.id_organisme), montants(o)) for o in oa.organismes.all()),
                sorted((r.id_poste.libelle if r.id_poste else None, org(r.id_organisme),
                        r.jours, r.categorie_depense, r.finance) for r in oa.rh_lignes.all()),
            ))
        suivi = None
        if op.id_suivi:
            suivi = (ligne_objet(op.id_suivi, CHAMPS_SUIVI),
                     [ligne_objet(p, CHAMPS_PROTOCOLE) for p in op.id_suivi.protocoles.all()])
        snap[op.code_operation] = dict(
            # Rattachement direct, ou par une métrique (actions d'avant #398).
            libelle=op.libelle, indicateur=(
                op.id_indicateur or op.metriques.first().id_indicateur).nom_indicateur,
            type=getattr(op.id_type_action, "label", None),
            priorite=getattr(op.id_priorite, "label", None),
            categorie=getattr(op.id_categorie_action_reserve, "label", None),
            champs=(op.numero_manuel, op.action_restauration, op.partenaires, op.operateurs,
                    op.financeurs, op.description, op.frequence_nombre, op.frequence_unite,
                    _mois(op.programmation_mensuelle_defaut), op.emprise_suit_sites,
                    op.est_suivi_existant, op.annee_min, op.annee_max),
            reglages=(op.ventilation_mode, op.declinaison_par_type_cout,
                      op.declinaison_par_poste, op.cout_salarial_auto, op.programmation_globale),
            geom=_geom(op.geom),
            sites=sorted(s.id_inpn for s in op.sites.all()),
            metriques=sorted(m.nom_metrique for m in op.metriques.all()),
            suivi=suivi, annees=annees,
            financements=sorted(
                (f.id_financeur.nom, f.id_financeur.categorie_affichage, f.montant)
                for f in op.finances.all()),
        )
    postes = sorted(
        (p.libelle, p.nom_local, p.commentaire, p.nombre, p.cout_jour, org(p.id_organisme),
         sorted((pf.id_fonction.libelle, pf.id_fonction.id_type_poste.cd_nomenclature,
                 pf.pourcentage) for pf in p.fonctions.all()))
        for p in plan.postes.all())
    return snap, postes


def test_aller_retour_sur_une_autre_instance(source):
    user, plan = source
    avant = _snapshot(plan)
    arbo = build_arborescence_workbook(plan=plan)
    actions = build_actions_workbook(plan)

    # « Autre instance » : plus rien des identifiants d'origine.
    org_nom = "CEN du test #786"
    for op in _plan_operations(plan):
        op.delete()
    PosteFonction.objects.filter(id_poste__id_pg=plan).delete()
    Poste.objects.filter(id_pg=plan).delete()
    Fonction.objects.filter(id_pg=plan).delete()
    PlanGestion.objects.filter(pk=plan.pk).delete()
    Site.objects.filter(id_inpn="FR9999786").delete()
    BibOrganismes.objects.filter(nom_organisme=org_nom).delete()
    Fonction.objects.filter(libelle="Garde technicien #786").delete()

    site, _org = _site_et_organisme(org_nom)
    cible = _plan(user, site)
    execute_import(cible, parse_workbook(arbo), user)

    parsed = parse_actions_workbook(actions)
    report = validate_actions_import(cible, parsed)
    assert report.can_import, report.errors
    # Le poste absent du plan cible est annoncé comme créé (Q4).
    assert any("sera créé" in w["message"] for w in report.warnings)
    execute_actions_import(cible, parsed, user)

    apres = _snapshot(cible)
    assert apres[1] == avant[1]  # postes et fonctions
    for code in avant[0]:
        for cle, valeur in avant[0][code].items():
            assert apres[0][code][cle] == valeur, (code, cle)


def test_organisme_introuvable_signale(source):
    """Un organisme du classeur absent des gestionnaires du plan cible est
    une erreur claire, avec son nom."""
    user, plan = source
    actions = build_actions_workbook(plan)
    arbo = build_arborescence_workbook(plan=plan)
    autre_site = SiteFactory(nom_site="Autre site")
    CorOgSite.objects.create(id_site=autre_site, uuid_og=OrganismeFactory(nom_organisme="Autre CEN"))
    cible = _plan(user, autre_site)
    execute_import(cible, parse_workbook(arbo), user)
    parsed = parse_actions_workbook(actions)
    # Un organisme qu'aucune structure de l'instance ne porte.
    parsed["organismes_noms"]["O1"] = "Organisme inconnu #786"
    report = validate_actions_import(cible, parsed)
    assert any("Organisme inconnu #786" in e["message"] and "n'appartient pas" in e["message"]
               for e in report.errors)


def test_organisme_hors_gestionnaires_retrouve_par_son_nom(source):
    """Un organisme qui ne gère aucun site du plan cible mais existe dans
    l'instance : retrouvé par son nom, avec un avertissement (ses montants
    ne sont pas perdus)."""
    user, plan = source
    actions = build_actions_workbook(plan)
    arbo = build_arborescence_workbook(plan=plan)
    autre_site = SiteFactory(nom_site="Autre site")
    CorOgSite.objects.create(id_site=autre_site, uuid_og=OrganismeFactory(nom_organisme="Autre CEN"))
    cible = _plan(user, autre_site)
    execute_import(cible, parse_workbook(arbo), user)
    report = validate_actions_import(cible, parse_actions_workbook(actions))
    assert report.can_import, report.errors
    assert any("ne gère aucun site" in w["message"] for w in report.warnings)


def test_plan_avec_actions_refuse(source):
    """Q2 : création seule — un plan qui a déjà des actions est refusé."""
    _user, plan = source
    report = validate_actions_import(plan, parse_actions_workbook(build_actions_workbook(plan)))
    assert any("déjà des actions" in e["message"] for e in report.errors)


def test_ligne_periode_reservee_a_la_programmation_globale(source):
    user, plan = source
    parsed = parse_actions_workbook(build_actions_workbook(plan))
    for a in parsed["actions"]:
        a["programmation_globale"] = "Non"
    cible = _plan(user, SiteFactory())
    report = validate_actions_import(cible, parsed)
    assert any("réservé aux actions en programmation globale" in e["message"]
               for e in report.errors)
