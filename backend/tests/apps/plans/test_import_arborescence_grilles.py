"""
#787 — Export / import de l'arborescence : le paramétrage des métriques
(format, grille de scores, blocs complémentaires, pondération, état de
référence) fait l'aller-retour. Les mesures saisies n'en font pas partie
(décision Q3 de l'issue).
"""

import io
from decimal import Decimal

import pytest
from openpyxl import load_workbook

from apps.plans.models_indicateurs import Metrique, MetriqueScoreBlock
from apps.plans.services_import import (
    build_arborescence_workbook,
    build_example_workbook,
    execute_import,
    parse_workbook,
    validate_import,
)
from tests.factories.enjeux import (
    EnjeuFactory,
    IndicateurFactory,
    MesureFactory,
    MetriqueFactory,
    NiveauExigenceFactory,
    NomenclatureFormatMetriqueFactory,
    NomenclatureTypeIndicateurFactory,
    NomenclatureTypeMetriqueFactory,
    ObjectifLongTermeFactory,
    ObjectifOperationnelFactory,
    ResultatAttenduFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import SuperAdminFactory

pytestmark = [pytest.mark.django_db, pytest.mark.integration]

# Champs de paramétrage comparés après l'aller-retour (tout sauf identifiants,
# rattachement, ordre, dates et auteurs).
_EXCLUS_METRIQUE = {
    "id_metrique", "id_indicateur", "ordre", "date_ajout", "date_maj",
    "id_utilisateur_ajout", "id_utilisateur_maj",
}
_EXCLUS_BLOC = {"id_score_block", "id_metrique"}


def _params(obj, exclus):
    # Nomenclatures comparées par mnémonique : l'import les retrouve par libellé.
    def val(f):
        v = getattr(obj, f.name)
        return getattr(v, "mnemonique", v) if f.is_relation else v
    return {f.name: val(f) for f in obj._meta.concrete_fields if f.name not in exclus}


def _d(v):
    return Decimal(str(v))


@pytest.fixture
def source():
    user = SuperAdminFactory()
    etat = NomenclatureTypeIndicateurFactory(mnemonique="ETAT", cd_nomenclature="ETAT", label="État")
    reponse = NomenclatureTypeIndicateurFactory(mnemonique="REPONSE", cd_nomenclature="REPONSE", label="Réponse")
    numerique = NomenclatureTypeMetriqueFactory(mnemonique="NUMERIQUE", cd_nomenclature="NUMERIQUE",
                                                label="Intervalle numérique")
    texte = NomenclatureTypeMetriqueFactory(mnemonique="TEXTE", cd_nomenclature="TEXTE", label="Texte")
    grille = NomenclatureFormatMetriqueFactory(mnemonique="GRILLE", cd_nomenclature="GRILLE", label="Grille")

    plan = PlanGestionFactory(id_utilisateur_ajout=user)
    enjeu = EnjeuFactory(id_pg=plan, id_utilisateur_ajout=user)
    ne = NiveauExigenceFactory(id_olt=ObjectifLongTermeFactory(id_enjeu=enjeu))
    ind_etat = IndicateurFactory(id_ne=ne, type_indicateur=etat)
    # Métrique numérique : grille croissante, palier 1 non utilisé, bornes
    # extrêmes, pondération, état de référence, bloc principal nommé et un bloc
    # complémentaire décroissant combiné en ET.
    m1 = MetriqueFactory(
        id_indicateur=ind_etat, nom_metrique="Surface en bon état", type_metrique=numerique,
        unite="ha", bloc_intitule="surface", ponderation=_d("0.75"),
        etat_reference="120 ha en 2010", sens_variation="CROISSANT",
        score_2_inf=_d(80), score_2_sup=_d(100), score_3_inf=_d(100), score_3_sup=_d(115),
        score_4_inf=_d(115), score_4_sup=_d(120), score_5_inf=_d(120), score_5_sup=_d(200),
        score_3_sup_inclusive=False, has_borne_score5=True, inactive_levels=[1],
        group_open=1, group_close=0,
    )
    MetriqueScoreBlock.objects.create(
        id_metrique=m1, position=1, intitule="recouvrement", unite="%", logical_op="AND",
        group_open=0, group_close=1, sens_variation="DECROISSANT",
        score_1_inf=_d(80), score_1_sup=_d(100), score_2_inf=_d(60), score_2_sup=_d(80),
        score_3_inf=_d(40), score_3_sup=_d(60), score_4_inf=_d(20), score_4_sup=_d(40),
        score_5_inf=_d(0), score_5_sup=_d(20), score_2_sup_inclusive=False,
        has_borne_score1=True, inactive_levels=[],
    )
    # Mesure saisie : ne fait pas l'aller-retour (Q3).
    MesureFactory(id_metrique=m1, valeur="116")

    # Indicateur de réponse avec grille de lecture (Q2), métrique « texte ».
    oo = ObjectifOperationnelFactory(id_enjeu=enjeu)
    ind_rep = IndicateurFactory(id_ne=None, id_resultat_attendu=ResultatAttenduFactory(id_oo=oo),
                                type_indicateur=reponse)
    MetriqueFactory(
        id_indicateur=ind_rep, nom_metrique="Comité local", type_metrique=texte,
        format_metrique=grille, unite=None,
        score_1_label="Aucune réunion", score_2_label="1 réunion", score_3_label="2 réunions",
        score_4_label="3 réunions", score_5_label="4 réunions ou plus",
    )
    return plan, user


def _aller_retour(plan, user):
    parsed = parse_workbook(build_arborescence_workbook(plan=plan))
    cible = PlanGestionFactory(id_utilisateur_ajout=user)
    report = validate_import(cible, parsed)
    assert report.can_import, report.errors
    execute_import(cible, parsed, user)
    return cible


def test_aller_retour_metriques_blocs_et_grilles_identiques(source):
    plan, user = source
    cible = _aller_retour(plan, user)
    avant = {m.nom_metrique: m for m in Metrique.objects.filter(
        nom_metrique__in=["Surface en bon état", "Comité local"], id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan)}
    avant["Comité local"] = Metrique.objects.get(
        nom_metrique="Comité local",
        id_indicateur__id_resultat_attendu__id_oo__id_enjeu__id_pg=plan)
    apres = {
        "Surface en bon état": Metrique.objects.get(
            nom_metrique="Surface en bon état", id_indicateur__id_ne__id_olt__id_enjeu__id_pg=cible),
        "Comité local": Metrique.objects.get(
            nom_metrique="Comité local", id_indicateur__id_resultat_attendu__id_oo__id_enjeu__id_pg=cible),
    }
    for nom in avant:
        assert _params(apres[nom], _EXCLUS_METRIQUE) == _params(avant[nom], _EXCLUS_METRIQUE), nom
    blocs_avant = [_params(b, _EXCLUS_BLOC) for b in avant["Surface en bon état"].score_blocks.all()]
    blocs_apres = [_params(b, _EXCLUS_BLOC) for b in apres["Surface en bon état"].score_blocks.all()]
    assert blocs_apres == blocs_avant and len(blocs_apres) == 1
    # Les mesures ne sont pas reprises (Q3 : paramétrage seul).
    assert not apres["Surface en bon état"].mesures.exists()


def test_classeur_porte_les_onglets_blocs_et_grilles(source):
    plan, _user = source
    wb = load_workbook(io.BytesIO(build_arborescence_workbook(plan=plan)))
    assert "Grilles" in wb.sheetnames and "Blocs" in wb.sheetnames
    lisez_moi = " ".join(str(c.value) for row in wb["Lisez-moi"].iter_rows() for c in row if c.value)
    assert "Format version 1.1" in lisez_moi


def test_classeur_1_0_sans_grilles_reste_importable(source):
    """Un classeur exporté avant #787 (sans onglets Blocs / Grilles) s'importe."""
    plan, user = source
    wb = load_workbook(io.BytesIO(build_arborescence_workbook(plan=plan)))
    del wb["Grilles"]
    del wb["Blocs"]
    buf = io.BytesIO()
    wb.save(buf)
    parsed = parse_workbook(buf.getvalue())
    assert parsed["grilles"] == [] and parsed["blocs"] == []
    cible = PlanGestionFactory(id_utilisateur_ajout=user)
    assert validate_import(cible, parsed).can_import


def _parsed_avec_grille(plan, user, **palier):
    parsed = parse_workbook(build_arborescence_workbook(plan=plan))
    ligne = next(r for r in parsed["grilles"] if str(r["bloc"]) == "0" and str(r["palier"]) == "3")
    ligne.update(palier)
    return parsed


def _erreurs(plan, user, parsed, niveau="errors"):
    cible = PlanGestionFactory(id_utilisateur_ajout=user)
    report = validate_import(cible, parsed)
    return [e["message"] for e in getattr(report, niveau)]


def test_seuils_incoherents_signales_sans_bloquer(source):
    """Les règles de la saisie s'appliquent, en avertissement : une grille
    enregistrée avant ces contrôles ne doit pas empêcher de réimporter le plan."""
    plan, user = source
    # Borne sup ≤ borne inf.
    parsed = _parsed_avec_grille(plan, user, borne_sup=90)
    assert any("strictement supérieure" in m for m in _erreurs(plan, user, parsed, "warnings"))
    assert not _erreurs(plan, user, parsed)
    # Discontinuité avec le palier 4 (115).
    parsed = _parsed_avec_grille(plan, user, borne_sup=113)
    assert any("continuité" in m for m in _erreurs(plan, user, parsed, "warnings"))


def test_palier_et_bloc_inconnus_refuses(source):
    plan, user = source
    parsed = _parsed_avec_grille(plan, user, palier=7)
    assert any("palier" in m.lower() for m in _erreurs(plan, user, parsed))
    parsed = _parsed_avec_grille(plan, user, bloc=4)
    assert any("bloc" in m.lower() for m in _erreurs(plan, user, parsed))
    parsed = parse_workbook(build_arborescence_workbook(plan=plan))
    parsed["blocs"][0]["sens"] = "En biais"
    assert any("sens" in m.lower() for m in _erreurs(plan, user, parsed))


def test_modele_exemple_construit():
    wb = load_workbook(io.BytesIO(build_example_workbook()))
    assert "Grilles" in wb.sheetnames


def test_metrique_indeterminee_sans_nom_importable(source):
    """#339 : l'écran accepte une métrique « Indéterminé » sans intitulé ;
    l'import d'un plan exporté ne doit pas la refuser."""
    plan, user = source
    indet = NomenclatureTypeMetriqueFactory(mnemonique="INDETERMINE", cd_nomenclature="INDETERMINE",
                                            label="Indéterminé")
    Metrique.objects.filter(nom_metrique="Comité local").update(nom_metrique="", type_metrique=indet,
                                                                format_metrique=None)
    parsed = parse_workbook(build_arborescence_workbook(plan=plan))
    assert not _erreurs(plan, user, parsed)
