"""
Tests de l'API d'exploration des données.

Couvre les deux modes de la maquette (contenu / plan de gestion), les familles
de filtres de la barre latérale, les compteurs d'onglets, et deux invariants
faciles à casser : le périmètre transverse (on voit les plans des autres
organismes, mais jamais un brouillon) et l'absence de N+1 sur les tuiles.
"""

import pytest
from django.contrib.gis.geos import MultiPolygon, Point, Polygon
from rest_framework.test import APIClient

from apps.geo.models import AreaType, LArea
from apps.search.indexing import index_plan
from tests.factories.core import SiteTypeNomenclatureFactory
from tests.factories.enjeux import (
    EnjeuFactory, FacteurInfluenceFactory, IndicateurFactory,
    NiveauExigenceFactory, ObjectifLongTermeFactory, PressionFactory,
)
from tests.factories.plans import CorSitePgFactory, PlanGestionFactory
from tests.factories.users import (
    CorOgSiteFactory, OrganismeFactory, RoleFactory, SiteFactory,
)

URL_CONTENUS = '/api/exploration/contenus/'
URL_PLANS = '/api/exploration/plans/'


def carre(xmin, ymin, xmax, ymax):
    return MultiPolygon(Polygon.from_bbox((xmin, ymin, xmax, ymax)), srid=4326)


@pytest.fixture
def client_connecte(db):
    """Un utilisateur lambda, sans lien avec les plans explorés."""
    client = APIClient()
    client.force_authenticate(RoleFactory())
    return client


@pytest.fixture
def referentiel_geo(db):
    type_dep = AreaType.objects.create(
        type_code=AreaType.DEPARTEMENT, type_name='Département'
    )
    type_reg = AreaType.objects.create(
        type_code=AreaType.REGION, type_name='Région'
    )
    region = LArea.objects.create(
        id_type=type_reg, area_code='R1', area_name='Grande Région',
        geom=carre(0, 0, 10, 10),
    )
    ouest = LArea.objects.create(
        id_type=type_dep, area_code='D1', area_name='Département Ouest',
        geom=carre(0, 0, 5, 10), parent=region,
    )
    est = LArea.objects.create(
        id_type=type_dep, area_code='D2', area_name='Département Est',
        geom=carre(5, 0, 10, 10), parent=region,
    )
    return {'region': region, 'ouest': ouest, 'est': est}


def _plan_avec_contenu(nom, libelle_enjeu, prefixe, site=None, statut='valide'):
    """
    Un plan portant un enjeu, un facteur, une pression, un OLT et un indicateur.

    Seul l'enjeu porte le thème (« limicoles ») : ses descendants sont nommés
    à partir de `prefixe`, sans reprendre ce mot. C'est ce qui permet de
    distinguer une correspondance sur le libellé d'une correspondance héritée
    du contexte de la branche.
    """
    plan = PlanGestionFactory(
        nom=nom, statut='draft', annee_debut=2020, annee_fin=2030,
    )
    if site is not None:
        CorSitePgFactory(site=site, plan_de_gestion=plan, rang=1)

    enjeu = EnjeuFactory(id_pg=plan, libelle=libelle_enjeu)
    facteur = FacteurInfluenceFactory(libelle=f'Facteur {prefixe}', id_enjeu=enjeu)
    PressionFactory(id_facteur_influence=facteur, libelle=f'Pression {prefixe}')
    olt = ObjectifLongTermeFactory(id_enjeu=enjeu, libelle=f'Objectif {prefixe}')
    niveau = NiveauExigenceFactory(id_olt=olt)
    IndicateurFactory(id_ne=niveau, nom_indicateur=f'Indicateur {prefixe}')

    plan.statut = statut
    plan.save()
    return plan


def _descendants(prefixe):
    return {
        f'Facteur {prefixe}', f'Pression {prefixe}',
        f'Objectif {prefixe}', f'Indicateur {prefixe}',
    }


@pytest.fixture
def jeu_de_donnees(referentiel_geo, db):
    """Deux plans validés dans deux départements, plus un brouillon."""
    type_rnn = SiteTypeNomenclatureFactory(mnemonique='RNN', cd_nomenclature='RNN')
    site_ouest = SiteFactory(
        nom_site='Réserve de l\'Ouest', id_type_site=type_rnn,
        geom=carre(1, 1, 2, 2), geom_pt=Point(1.5, 1.5, srid=4326),
    )
    site_est = SiteFactory(
        nom_site='Réserve de l\'Est',
        geom=carre(7, 1, 8, 2), geom_pt=Point(7.5, 1.5, srid=4326),
    )
    plans = {
        'ouest': _plan_avec_contenu(
            'Plan Ouest', 'Protection des limicoles', 'Ouest', site_ouest,
        ),
        'est': _plan_avec_contenu(
            'Plan Est', 'Protection des chiroptères', 'Est', site_est,
        ),
        'brouillon': _plan_avec_contenu(
            'Plan Brouillon', 'Protection des amphibiens', 'Brouillon',
            statut='draft',
        ),
    }
    return {
        'plans': plans, 'site_ouest': site_ouest, 'site_est': site_est,
        'type_rnn': type_rnn,
    }


def titres(reponse):
    return [r['titre'] for r in reponse.data['results']]


def noms(reponse):
    return [r['nom'] for r in reponse.data['results']]


# --------------------------------------------------------------------------- #
# Périmètre
# --------------------------------------------------------------------------- #

@pytest.mark.integration
class TestPerimetre:

    def test_lexploration_exige_detre_connecte(self, jeu_de_donnees):
        assert APIClient().get(URL_CONTENUS).status_code in (401, 403)
        assert APIClient().get(URL_PLANS).status_code in (401, 403)

    def test_un_utilisateur_sans_lien_voit_les_plans_des_autres_organismes(
        self, client_connecte, jeu_de_donnees
    ):
        """
        L'exploration est transverse par décision produit : elle n'applique pas
        le périmètre de lecture d'un plan (#610).
        """
        reponse = client_connecte.get(URL_CONTENUS)

        assert reponse.status_code == 200
        assert 'Protection des limicoles' in titres(reponse)
        assert 'Protection des chiroptères' in titres(reponse)

    def test_les_brouillons_restent_invisibles(self, client_connecte, jeu_de_donnees):
        assert 'Protection des amphibiens' not in titres(
            client_connecte.get(URL_CONTENUS)
        )
        assert 'Plan Brouillon' not in noms(client_connecte.get(URL_PLANS))

    def test_aucune_donnee_de_gestion_nest_exposee(self, client_connecte, jeu_de_donnees):
        """Ni budget, ni RH, ni mesures dans la charge utile d'un résultat."""
        resultat = client_connecte.get(URL_CONTENUS).data['results'][0]
        interdits = {'budget', 'etp', 'cout', 'poste', 'mesure', 'realisation'}

        champs = set(resultat) | set(resultat['plan'])
        assert not any(
            interdit in champ.lower() for champ in champs for interdit in interdits
        )


# --------------------------------------------------------------------------- #
# Recherche par mot-clé
# --------------------------------------------------------------------------- #

@pytest.mark.integration
class TestRechercheContenu:

    def test_sans_mot_cle_tout_le_contenu_indexe_remonte(
        self, client_connecte, jeu_de_donnees
    ):
        reponse = client_connecte.get(URL_CONTENUS)

        # 5 objets par plan validé, 2 plans validés.
        assert reponse.data['pagination']['count'] == 10

    def test_le_mot_cle_filtre_sur_les_libelles(self, client_connecte, jeu_de_donnees):
        reponse = client_connecte.get(URL_CONTENUS, {'q': 'limicole'})

        assert set(titres(reponse)) == {'Protection des limicoles'}

    def test_le_mode_elargi_remonte_la_branche(self, client_connecte, jeu_de_donnees):
        reponse = client_connecte.get(
            URL_CONTENUS, {'q': 'limicole', 'titres_seulement': 'false'}
        )

        # Aucun descendant ne porte « limicole » dans son libellé : ils
        # ressortent par le contexte hérité de leur enjeu.
        assert _descendants('Ouest') <= set(titres(reponse))
        assert not _descendants('Est') & set(titres(reponse))

    def test_la_recherche_tolere_une_faute_de_frappe(
        self, client_connecte, jeu_de_donnees
    ):
        reponse = client_connecte.get(URL_CONTENUS, {'q': 'limicolle'})

        assert 'Protection des limicoles' in titres(reponse)


# --------------------------------------------------------------------------- #
# Onglets et compteurs
# --------------------------------------------------------------------------- #

@pytest.mark.integration
class TestCompteurs:

    def test_les_compteurs_couvrent_tous_les_types(self, client_connecte, jeu_de_donnees):
        compteurs = client_connecte.get(URL_CONTENUS).data['compteurs']

        assert compteurs['tout'] == 10
        assert compteurs['enjeu'] == 2
        assert compteurs['pression'] == 2
        assert compteurs['objectif_op'] == 0

    def test_longlet_filtre_la_liste_sans_toucher_aux_compteurs(
        self, client_connecte, jeu_de_donnees
    ):
        reponse = client_connecte.get(URL_CONTENUS, {'onglet': 'pression'})

        assert reponse.data['pagination']['count'] == 2
        assert reponse.data['compteurs']['tout'] == 10
        assert reponse.data['compteurs']['enjeu'] == 2

    def test_un_onglet_peut_couvrir_plusieurs_types(
        self, client_connecte, jeu_de_donnees
    ):
        """
        La maquette n'affiche qu'un onglet « Objectifs » : il doit couvrir les
        objectifs à long terme et les objectifs opérationnels d'un seul tenant.
        """
        reponse = client_connecte.get(
            URL_CONTENUS, {'onglet': 'objectif_lt,objectif_op'}
        )

        assert set(titres(reponse)) == {'Objectif Ouest', 'Objectif Est'}
        assert reponse.data['compteurs']['tout'] == 10

    def test_les_compteurs_suivent_les_filtres(self, client_connecte, jeu_de_donnees):
        reponse = client_connecte.get(URL_CONTENUS, {'q': 'limicole'})

        assert reponse.data['compteurs']['tout'] == 1
        assert reponse.data['compteurs']['enjeu'] == 1


# --------------------------------------------------------------------------- #
# Filtres de la barre latérale
# --------------------------------------------------------------------------- #

@pytest.mark.integration
class TestFiltres:

    def test_filtrer_par_departement(
        self, client_connecte, jeu_de_donnees, referentiel_geo
    ):
        reponse = client_connecte.get(
            URL_CONTENUS, {'zones': referentiel_geo['ouest'].pk}
        )

        assert 'Protection des limicoles' in titres(reponse)
        assert 'Protection des chiroptères' not in titres(reponse)

    def test_filtrer_par_region_couvre_ses_departements(
        self, client_connecte, jeu_de_donnees, referentiel_geo
    ):
        reponse = client_connecte.get(
            URL_CONTENUS, {'zones': referentiel_geo['region'].pk}
        )

        assert reponse.data['pagination']['count'] == 10

    def test_filtrer_par_type_daire_protegee(
        self, client_connecte, jeu_de_donnees
    ):
        reponse = client_connecte.get(URL_CONTENUS, {'types_site': 'RNN'})

        # Seul le site Ouest est une RNN.
        assert set(titres(reponse)) == {'Protection des limicoles'} | _descendants('Ouest')

    def test_filtrer_par_organisme_gestionnaire(
        self, client_connecte, jeu_de_donnees
    ):
        organisme = OrganismeFactory(nom_organisme='CEN Test')
        CorOgSiteFactory(
            id_site=jeu_de_donnees['site_ouest'], uuid_og=organisme, principal=True,
        )
        index_plan(jeu_de_donnees['plans']['ouest'])

        reponse = client_connecte.get(
            URL_CONTENUS, {'organismes': organisme.pk}
        )

        assert set(titres(reponse)) == {'Protection des limicoles'} | _descendants('Ouest')

    def test_un_groupe_de_facettes_ne_raffine_que_son_type(
        self, client_connecte, jeu_de_donnees
    ):
        """
        Cocher « Indicateur d'état » restreint les indicateurs mais ne fait pas
        disparaître les enjeux ou les pressions de la liste.
        """
        reponse = client_connecte.get(URL_CONTENUS, {'types_indicateur': 'INEXISTANT'})

        compteurs = reponse.data['compteurs']
        assert compteurs['indicateur'] == 0
        assert compteurs['enjeu'] == 2
        assert compteurs['pression'] == 2

    def test_filtrer_par_categorie_denjeu(self, client_connecte, jeu_de_donnees):
        reponse = client_connecte.get(URL_CONTENUS, {'categories_enjeu': 'socioeco'})

        assert reponse.data['compteurs']['enjeu'] == 0
        assert reponse.data['compteurs']['pression'] == 2

    def test_filtrer_par_type_de_donnees(self, client_connecte, jeu_de_donnees):
        reponse = client_connecte.get(URL_CONTENUS, {'types': 'enjeu,pression'})

        assert reponse.data['compteurs']['tout'] == 4
        assert reponse.data['compteurs']['indicateur'] == 0

    def test_filtrer_par_statut_archive(self, client_connecte, jeu_de_donnees):
        plan = jeu_de_donnees['plans']['est']
        plan.statut = 'archive'
        plan.save()

        reponse = client_connecte.get(URL_CONTENUS, {'statuts': 'archive'})

        assert set(titres(reponse)) == {'Protection des chiroptères'} | _descendants('Est')


# --------------------------------------------------------------------------- #
# Tri
# --------------------------------------------------------------------------- #

@pytest.mark.integration
class TestTri:

    def test_le_tri_alphabetique(self, client_connecte, jeu_de_donnees):
        reponse = client_connecte.get(URL_CONTENUS, {'tri': 'alphabetique'})

        assert titres(reponse) == sorted(titres(reponse))

    def test_le_tri_par_pertinence_place_le_libelle_avant_le_contexte(
        self, client_connecte, jeu_de_donnees
    ):
        reponse = client_connecte.get(
            URL_CONTENUS, {'q': 'limicole', 'titres_seulement': 'false'}
        )

        # L'enjeu porte le mot dans son libellé (poids A), ses descendants ne
        # l'ont que dans leur contexte (poids C).
        assert titres(reponse)[0] == 'Protection des limicoles'


# --------------------------------------------------------------------------- #
# Mode « plan de gestion »
# --------------------------------------------------------------------------- #

@pytest.mark.integration
class TestRecherchePlans:

    def test_rechercher_par_nom_de_plan(self, client_connecte, jeu_de_donnees):
        assert noms(client_connecte.get(URL_PLANS, {'q': 'Plan Ouest'})) == ['Plan Ouest']

    def test_rechercher_par_nom_de_site(self, client_connecte, jeu_de_donnees):
        assert noms(client_connecte.get(URL_PLANS, {'q': "Réserve de l'Est"})) == ['Plan Est']

    def test_rechercher_par_nom_de_departement(self, client_connecte, jeu_de_donnees):
        assert noms(client_connecte.get(URL_PLANS, {'q': 'Département Ouest'})) == ['Plan Ouest']

    def test_rechercher_par_nom_de_region(self, client_connecte, jeu_de_donnees):
        assert set(noms(client_connecte.get(URL_PLANS, {'q': 'Grande Région'}))) == {
            'Plan Ouest', 'Plan Est',
        }

    def test_la_recherche_ignore_les_accents(self, client_connecte, jeu_de_donnees):
        assert noms(client_connecte.get(URL_PLANS, {'q': 'departement ouest'})) == ['Plan Ouest']

    def test_la_tuile_porte_les_sites_du_plan(self, client_connecte, jeu_de_donnees):
        resultat = client_connecte.get(URL_PLANS, {'q': 'Plan Ouest'}).data['results'][0]

        assert [s['nom_site'] for s in resultat['sites']] == ["Réserve de l'Ouest"]

    def test_un_plan_nest_pas_duplique_par_ses_sites(
        self, client_connecte, jeu_de_donnees
    ):
        CorSitePgFactory(
            site=jeu_de_donnees['site_est'],
            plan_de_gestion=jeu_de_donnees['plans']['ouest'], rang=2,
        )

        assert noms(client_connecte.get(URL_PLANS, {'q': 'Grande Région'})).count(
            'Plan Ouest'
        ) == 1


# --------------------------------------------------------------------------- #
# Performance
# --------------------------------------------------------------------------- #

@pytest.mark.integration
class TestRequetes:
    """
    Garde-fou anti N+1 : les libellés de plan, de site et de gestionnaire sont
    joints, pas dénormalisés. Sans prefetch, chaque tuile déclencherait ses
    propres requêtes et le coût croîtrait avec la taille de la page.
    """

    def test_le_nombre_de_requetes_ne_depend_pas_du_nombre_de_resultats(
        self, client_connecte, jeu_de_donnees, django_assert_max_num_queries
    ):
        with django_assert_max_num_queries(12):
            reponse = client_connecte.get(URL_CONTENUS, {'page_size': 100})
        assert reponse.data['pagination']['count'] == 10

        for indice in range(6):
            _plan_avec_contenu(
                f'Plan supplémentaire {indice}', f'Enjeu {indice}', f'Sup{indice}',
            )

        with django_assert_max_num_queries(12):
            reponse = client_connecte.get(URL_CONTENUS, {'page_size': 100})
        assert reponse.data['pagination']['count'] == 40
