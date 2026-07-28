"""
Tests de l'index de recherche du contenu des plans de gestion (apps.search).

Trois familles :

- **cycle de vie** : l'index suit le statut du plan, jamais autre chose ;
- **extraction** : chaque type d'objet produit la bonne ligne, avec son parent
  et son sous-type ;
- **recherche** : radicalisation, insensibilité aux accents, et surtout la
  différence entre le mode « titres uniquement » et le mode élargi.
"""

import pytest
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from django.contrib.postgres.search import SearchQuery
from django.core.management import call_command
from django.db.models import Count

from apps.geo.models import AreaType, LArea
from apps.search.indexing import index_plan
from apps.search.models import SEARCH_CONFIG, ContenuIndexe
from tests.factories.core import NomenclatureFactory, TypeNomenclatureFactory
from tests.factories.enjeux import (
    CorEnjeuGeologieFactory, CorEnjeuHabitatFactory, CorEnjeuTaxonFactory,
    EnjeuFactory, FacteurInfluenceFactory, IndicateurFactory,
    NiveauExigenceFactory, ObjectifLongTermeFactory,
    ObjectifOperationnelFactory, OperationFactory, PressionFactory,
    ProtocoleFactory, SuiviInventaireFactory,
)
from tests.factories.plans import CorSitePgFactory, PlanGestionFactory
from tests.factories.users import SiteFactory


# --------------------------------------------------------------------------- #
# Fixtures
# --------------------------------------------------------------------------- #

@pytest.fixture
def plan_brouillon(db):
    """Un plan en brouillon, donc hors de l'index."""
    return PlanGestionFactory(statut='draft', annee_debut=2020, annee_fin=2030)


@pytest.fixture
def arborescence(plan_brouillon):
    """
    Une branche complète sous un enjeu rattaché à un taxon.

    enjeu « Protection des limicoles » (taxon : Calidris alpina / Bécasseau
    variable) → facteur → pression, et enjeu → OLT → NE → indicateur → action.
    """
    enjeu = EnjeuFactory(
        id_pg=plan_brouillon,
        libelle='Protection des limicoles',
        description='Enjeu majeur du site',
        categorie_ecologique=True,
    )
    CorEnjeuTaxonFactory(
        id_enjeu=enjeu, nom_complet='Calidris alpina',
        nom_vern='Bécasseau variable',
    )
    facteur = FacteurInfluenceFactory(
        libelle='Fréquentation touristique', id_enjeu=enjeu,
    )
    pression = PressionFactory(
        id_facteur_influence=facteur, libelle='Dérangement en période de nidification',
    )
    olt = ObjectifLongTermeFactory(id_enjeu=enjeu, libelle='Maintenir la population nicheuse')
    oo = ObjectifOperationnelFactory(id_enjeu=enjeu, libelle='Canaliser la fréquentation')
    oo.pressions.set([pression])
    niveau = NiveauExigenceFactory(id_olt=olt, libelle='Au moins 50 couples')
    indicateur = IndicateurFactory(id_ne=niveau, nom_indicateur='Nombre de couples nicheurs')
    action = OperationFactory(libelle='Comptage annuel', id_indicateur=indicateur)

    return {
        'plan': plan_brouillon, 'enjeu': enjeu, 'facteur': facteur,
        'pression': pression, 'olt': olt, 'oo': oo, 'indicateur': indicateur,
        'action': action,
    }


@pytest.fixture
def plan_indexe(arborescence):
    """L'arborescence ci-dessus, sur un plan passé à l'état validé."""
    plan = arborescence['plan']
    plan.statut = 'valide'
    plan.save()
    return arborescence


def titres(type_contenu=None):
    qs = ContenuIndexe.objects.all()
    if type_contenu:
        qs = qs.filter(type_contenu=type_contenu)
    return set(qs.values_list('titre', flat=True))


def cherche(terme, champ='search_full'):
    """Résultats d'une recherche, par libellé."""
    requete = SearchQuery(terme, config=SEARCH_CONFIG, search_type='websearch')
    return set(
        ContenuIndexe.objects.filter(**{champ: requete})
        .values_list('titre', flat=True)
    )


# --------------------------------------------------------------------------- #
# Cycle de vie
# --------------------------------------------------------------------------- #

@pytest.mark.unit
class TestCycleDeVie:

    def test_un_brouillon_nest_pas_indexe(self, arborescence):
        assert ContenuIndexe.objects.count() == 0

    def test_la_validation_declenche_lindexation(self, arborescence):
        plan = arborescence['plan']
        plan.statut = 'valide'
        plan.save()

        assert ContenuIndexe.objects.filter(id_pg=plan).count() == 7

    def test_le_retour_en_brouillon_desindexe(self, plan_indexe):
        plan = plan_indexe['plan']
        plan.statut = 'draft'
        plan.save()

        assert ContenuIndexe.objects.filter(id_pg=plan).count() == 0

    def test_un_plan_archive_reste_explorable(self, plan_indexe):
        plan = plan_indexe['plan']
        plan.statut = 'archive'
        plan.save()

        assert ContenuIndexe.objects.filter(id_pg=plan).exists()

    def test_le_workflow_csrpn_nest_pas_indexe(self, arborescence):
        """Un plan en cours de validation CSRPN reste un brouillon."""
        plan = arborescence['plan']
        plan.validation_step = 'avis_csrpn'
        plan.save()

        assert ContenuIndexe.objects.count() == 0

    def test_reindexer_ne_duplique_pas(self, plan_indexe):
        avant = ContenuIndexe.objects.count()

        index_plan(plan_indexe['plan'])

        assert ContenuIndexe.objects.count() == avant

    def test_supprimer_le_plan_vide_son_index(self, plan_indexe):
        plan_indexe['plan'].delete()

        assert ContenuIndexe.objects.count() == 0


# --------------------------------------------------------------------------- #
# Extraction
# --------------------------------------------------------------------------- #

@pytest.mark.unit
class TestExtraction:

    def test_les_sept_types_dobjets_sont_indexes(self, plan_indexe):
        assert dict(
            ContenuIndexe.objects.values_list('type_contenu')
            .annotate(n=Count('id'))
        ) == {
            'enjeu': 1, 'facteur': 1, 'pression': 1, 'objectif_lt': 1,
            'objectif_op': 1, 'indicateur': 1, 'action': 1,
        }

    def test_le_libelle_devient_le_titre(self, plan_indexe):
        assert titres('enjeu') == {'Protection des limicoles'}
        assert titres('indicateur') == {'Nombre de couples nicheurs'}
        assert titres('action') == {'Comptage annuel'}

    def test_le_parent_dune_pression_est_son_facteur(self, plan_indexe):
        ligne = ContenuIndexe.objects.get(type_contenu='pression')

        assert ligne.parent_type == 'facteur'
        assert ligne.parent_libelle == 'Fréquentation touristique'

    def test_le_parent_dun_indicateur_est_son_objectif(self, plan_indexe):
        ligne = ContenuIndexe.objects.get(type_contenu='indicateur')

        assert ligne.parent_type == 'objectif_lt'
        assert ligne.parent_libelle == 'Maintenir la population nicheuse'

    def test_le_sous_type_distingue_ecologique_et_socioeconomique(self, plan_indexe):
        assert ContenuIndexe.objects.get(type_contenu='enjeu').sous_type == 'ecologique'

        socio = EnjeuFactory(
            id_pg=plan_indexe['plan'], libelle='Maintien des usages',
            categorie_ecologique=False,
        )
        index_plan(plan_indexe['plan'])

        assert ContenuIndexe.objects.get(id_objet=socio.pk, type_contenu='enjeu') \
            .sous_type == 'socioeco'

    def test_la_description_est_indexee_a_part_du_titre(self, plan_indexe):
        ligne = ContenuIndexe.objects.get(type_contenu='enjeu')

        assert ligne.description == 'Enjeu majeur du site'


# --------------------------------------------------------------------------- #
# Recherche
# --------------------------------------------------------------------------- #

@pytest.mark.unit
class TestRecherche:

    def test_la_recherche_est_insensible_au_pluriel(self, plan_indexe):
        assert 'Protection des limicoles' in cherche('limicole', 'search_titre')

    def test_la_recherche_est_insensible_aux_accents(self, plan_indexe):
        assert 'Fréquentation touristique' in cherche('frequentation', 'search_titre')

    def test_le_mode_titres_ignore_les_descriptions(self, plan_indexe):
        assert cherche('majeur', 'search_titre') == set()
        assert 'Protection des limicoles' in cherche('majeur', 'search_full')

    def test_le_mode_elargi_remonte_toute_la_branche_dun_enjeu(self, plan_indexe):
        """
        Cas décrit dans l'aide de la maquette : « les indicateurs pour lesquels
        il y a un enjeu autour des limicoles ».
        """
        assert cherche('limicole', 'search_titre') == {'Protection des limicoles'}

        elargi = cherche('limicole', 'search_full')
        assert 'Nombre de couples nicheurs' in elargi
        assert 'Dérangement en période de nidification' in elargi
        assert 'Maintenir la population nicheuse' in elargi

    def test_le_nom_scientifique_du_taxon_est_cherchable_dans_les_deux_modes(
        self, plan_indexe
    ):
        """
        #634 a déplacé les rattachements du `contexte` vers les `rattachements`,
        interrogés dans les deux modes : chercher une espèce ne demande plus
        d'élargir la recherche. Le détail est couvert par `TestRattachements`.
        """
        for champ in ('search_titre', 'search_full'):
            resultats = cherche('Calidris', champ)
            assert 'Protection des limicoles' in resultats, champ
            assert 'Nombre de couples nicheurs' in resultats, champ

    def test_le_nom_vernaculaire_du_taxon_est_cherchable(self, plan_indexe):
        assert 'Protection des limicoles' in cherche('bécasseau', 'search_full')


# --------------------------------------------------------------------------- #
# Facettes
# --------------------------------------------------------------------------- #

@pytest.fixture
def referentiel_geo(db):
    type_dep = AreaType.objects.create(
        type_code=AreaType.DEPARTEMENT, type_name='Département'
    )
    type_reg = AreaType.objects.create(
        type_code=AreaType.REGION, type_name='Région'
    )
    region = LArea.objects.create(
        id_type=type_reg, area_code='R1', area_name='Région Un',
        geom=MultiPolygon(Polygon.from_bbox((0, 0, 10, 10)), srid=4326),
    )
    departement = LArea.objects.create(
        id_type=type_dep, area_code='D1', area_name='Département Un',
        geom=MultiPolygon(Polygon.from_bbox((0, 0, 5, 10)), srid=4326),
        parent=region,
    )
    return {'region': region, 'departement': departement}


@pytest.mark.unit
class TestFacettes:

    def test_les_facettes_du_plan_sont_recopiees_sur_chaque_ligne(self, plan_indexe):
        plan = plan_indexe['plan']

        for ligne in ContenuIndexe.objects.all():
            assert ligne.statut_pg == 'valide'
            assert ligne.annee_debut == plan.annee_debut
            assert ligne.annee_fin == plan.annee_fin

    def test_la_zone_geographique_du_site_est_reportee(
        self, referentiel_geo, plan_indexe
    ):
        site = SiteFactory(
            geom=MultiPolygon(Polygon.from_bbox((1, 1, 2, 2)), srid=4326),
            geom_pt=Point(1.5, 1.5, srid=4326),
        )
        CorSitePgFactory(site=site, plan_de_gestion=plan_indexe['plan'], rang=1)

        attendu = {referentiel_geo['departement'].pk, referentiel_geo['region'].pk}
        for ligne in ContenuIndexe.objects.all():
            assert set(ligne.area_ids) == attendu
            assert ligne.site_ids == [site.pk]

    def test_retirer_un_site_met_les_facettes_a_jour(
        self, referentiel_geo, plan_indexe
    ):
        site = SiteFactory(
            geom=MultiPolygon(Polygon.from_bbox((1, 1, 2, 2)), srid=4326),
            geom_pt=Point(1.5, 1.5, srid=4326),
        )
        lien = CorSitePgFactory(site=site, plan_de_gestion=plan_indexe['plan'], rang=1)

        lien.delete()

        for ligne in ContenuIndexe.objects.all():
            assert ligne.site_ids == []
            assert ligne.area_ids == []

    def test_le_type_daire_protegee_est_reporte(self, plan_indexe):
        site = SiteFactory()
        CorSitePgFactory(site=site, plan_de_gestion=plan_indexe['plan'], rang=1)

        codes = ContenuIndexe.objects.first().type_site_codes
        attendu = (
            [site.id_type_site.mnemonique] if site.id_type_site_id else []
        )
        assert codes == attendu


# --------------------------------------------------------------------------- #
# Commande de reconstruction
# --------------------------------------------------------------------------- #

@pytest.mark.integration
class TestCommandeRebuild:

    def test_la_commande_reconstruit_lindex(self, plan_indexe):
        ContenuIndexe.objects.all().delete()

        call_command('rebuild_search_index', verbosity=0)

        assert ContenuIndexe.objects.filter(id_pg=plan_indexe['plan']).count() == 7

    def test_la_commande_nindexe_pas_les_brouillons(self, arborescence):
        call_command('rebuild_search_index', verbosity=0)

        assert ContenuIndexe.objects.count() == 0

    def test_la_commande_purge_les_lignes_orphelines(self, plan_indexe):
        """Un plan repassé en brouillon sans que le signal ait pu jouer."""
        plan = plan_indexe['plan']
        ContenuIndexe.objects.filter(id_pg=plan).update(statut_pg='draft')
        type(plan).objects.filter(pk=plan.pk).update(statut='draft')

        call_command('rebuild_search_index', '--purge', verbosity=0)

        assert ContenuIndexe.objects.count() == 0


# --------------------------------------------------------------------------- #
# Objets rattachés (#634)
# --------------------------------------------------------------------------- #

@pytest.mark.unit
class TestRattachements:
    """
    Chercher une espèce, un habitat, un protocole standardisé, un élément
    géologique ou une référence PressRef doit remonter les objets qui les
    portent — **y compris en mode « titres uniquement »**, qui est l'état par
    défaut de l'interface. Ce sont des rattachements explicites à un
    référentiel, pas du texte de contexte (#634).
    """

    def test_le_nom_scientifique_remonte_en_mode_titres(self, plan_indexe):
        assert 'Protection des limicoles' in cherche('Calidris', 'search_titre')

    def test_le_nom_vernaculaire_remonte_en_mode_titres(self, plan_indexe):
        """« Ne doit pas marcher seulement avec les noms latins » (#634)."""
        assert 'Protection des limicoles' in cherche('bécasseau', 'search_titre')

    def test_une_espece_remonte_les_actions_de_son_enjeu(self, plan_indexe):
        """
        Une action hérite des rattachements de l'enjeu dont elle dépend, via son
        indicateur : chercher l'espèce doit la faire ressortir.
        """
        assert 'Comptage annuel' in cherche('Calidris', 'search_titre')
        assert 'Comptage annuel' in cherche('bécasseau', 'search_titre')

    def test_un_habitat_remonte_toute_sa_branche(self, plan_indexe):
        CorEnjeuHabitatFactory(
            id_enjeu=plan_indexe['enjeu'], cd_hab='1150',
            lb_hab_fr='Lagunes côtières',
        )
        index_plan(plan_indexe['plan'])

        resultats = cherche('lagunes', 'search_titre')
        assert 'Protection des limicoles' in resultats
        assert 'Comptage annuel' in resultats

    def test_un_element_geologique_remonte_sa_branche(self, plan_indexe):
        CorEnjeuGeologieFactory(
            id_enjeu=plan_indexe['enjeu'], id_inpg='INPG_0042',
            nom='Falaise calcaire du Jurassique',
        )
        index_plan(plan_indexe['plan'])

        resultats = cherche('jurassique', 'search_titre')
        assert 'Protection des limicoles' in resultats
        assert 'Comptage annuel' in resultats

    def test_un_protocole_standardise_remonte_les_actions_qui_lappliquent(
        self, plan_indexe
    ):
        """
        « On veut que STOC donne la mention STOC classique mais aussi toutes les
        actions CS sur lesquelles il y a ce truc là » (#634).
        """
        protocole = ProtocoleFactory(nom_protocole='STOC EPS')
        suivi = SuiviInventaireFactory(
            id_pg=plan_indexe['plan'], intitule='Suivi avifaune',
            protocoles=[protocole],
        )
        action = OperationFactory(libelle='Points d\'écoute', id_suivi=suivi)
        index_plan(plan_indexe['plan'])

        resultats = cherche('STOC', 'search_titre')
        assert "Points d'écoute" in resultats, (
            "l'action doit ressortir sur le nom du protocole qu'elle applique"
        )
        assert action.pk  # l'action est bien rattachée au plan par son suivi

    def test_la_reference_pressref_est_cherchable(self, plan_indexe):
        pression = plan_indexe['pression']
        pression.id_type_pression = NomenclatureFactory(
            id_type=TypeNomenclatureFactory(mnemonique='TYPE_PRESSION'),
            mnemonique='2_1_1',
            cd_nomenclature='2_1_1',
            label='Modification des conditions hydrodynamiques',
        )
        pression.save()
        index_plan(plan_indexe['plan'])

        assert 'Dérangement en période de nidification' in cherche(
            'hydrodynamiques', 'search_titre'
        )

    def test_le_libelle_des_ancetres_reste_reserve_au_mode_elargi(self, plan_indexe):
        """
        La frontière entre les deux modes n'est pas « titre / reste » mais
        « ce que l'objet porte » / « ce que ses parents disent ».
        """
        assert 'Comptage annuel' not in cherche('limicole', 'search_titre')
        assert 'Comptage annuel' in cherche('limicole', 'search_full')
