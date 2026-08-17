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
    NiveauExigenceFactory, ObjectifLongTermeFactory, OperationFactory,
    PressionFactory,
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
    indicateur = IndicateurFactory(id_ne=niveau, nom_indicateur=f'Indicateur {prefixe}')

    plan.statut = statut
    plan.save()
    # Exposé pour les tests qui ont besoin d'accrocher une action à la branche.
    plan.indicateur_racine = indicateur
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

    def test_la_faute_de_frappe_est_toleree_sur_un_habitat(
        self, client_connecte, jeu_de_donnees
    ):
        """
        Retour de recette #634 : « eutotrophes » ne remontait pas « Lacs
        eutrophes naturels… ».

        L'habitat était bien indexé, mais le rattrapage par similarité ne
        portait que sur le libellé de l'objet. Or un nom d'habitat ou d'espèce
        est long et rarement tapé sans faute : c'est justement là que le plein
        texte, qui ne pardonne aucune lettre en trop, laisse l'utilisateur sans
        résultat ni explication.
        """
        from apps.plans.models_enjeux import Enjeu
        from tests.factories.enjeux import CorEnjeuHabitatFactory

        plan = jeu_de_donnees['plans']['ouest']
        enjeu = Enjeu.objects.get(id_pg=plan)
        CorEnjeuHabitatFactory(
            id_enjeu=enjeu, cd_hab='3150',
            lb_hab_fr='Lacs eutrophes naturels avec végétation du Magnopotamion',
        )
        index_plan(plan)

        reponse = client_connecte.get(URL_CONTENUS, {'q': 'eutotrophes'})

        assert 'Protection des limicoles' in titres(reponse)

    def test_l_habitat_remonte_sans_faute_de_frappe(
        self, client_connecte, jeu_de_donnees
    ):
        """Le rattrapage ne doit pas masquer le cas nominal (plein texte)."""
        from apps.plans.models_enjeux import Enjeu
        from tests.factories.enjeux import CorEnjeuHabitatFactory

        plan = jeu_de_donnees['plans']['ouest']
        CorEnjeuHabitatFactory(
            id_enjeu=Enjeu.objects.get(id_pg=plan), cd_hab='3150',
            lb_hab_fr='Lacs eutrophes naturels avec végétation du Magnopotamion',
        )
        index_plan(plan)

        reponse = client_connecte.get(URL_CONTENUS, {'q': 'eutrophes'})

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


# --------------------------------------------------------------------------- #
# Fiche publique
# --------------------------------------------------------------------------- #

def url_fiche(plan):
    return f'/api/exploration/plans/{plan.slug}/'


def _cles_profondes(donnees, prefixe=''):
    """Toutes les clés d'une charge utile JSON, chemins imbriqués compris."""
    if isinstance(donnees, dict):
        for cle, valeur in donnees.items():
            chemin = f'{prefixe}.{cle}' if prefixe else cle
            yield chemin
            yield from _cles_profondes(valeur, chemin)
    elif isinstance(donnees, list):
        for element in donnees:
            yield from _cles_profondes(element, prefixe)


@pytest.mark.integration
class TestFichePublique:

    def test_la_fiche_expose_larborescence_du_plan(
        self, client_connecte, jeu_de_donnees
    ):
        reponse = client_connecte.get(url_fiche(jeu_de_donnees['plans']['ouest']))

        assert reponse.status_code == 200
        assert reponse.data['nom'] == 'Plan Ouest'

        enjeux = reponse.data['enjeux']
        assert [e['libelle'] for e in enjeux] == ['Protection des limicoles']

        enjeu = enjeux[0]
        assert [f['libelle'] for f in enjeu['facteurs']] == ['Facteur Ouest']
        assert [p['libelle'] for p in enjeu['facteurs'][0]['pressions']] == [
            'Pression Ouest'
        ]
        assert [o['libelle'] for o in enjeu['objectifs_long_terme']] == [
            'Objectif Ouest'
        ]

        indicateurs = [
            indicateur['nom_indicateur']
            for objectif in enjeu['objectifs_long_terme']
            for niveau in objectif['niveaux_exigence']
            for indicateur in niveau['indicateurs']
        ]
        assert indicateurs == ['Indicateur Ouest']

    def test_la_fiche_descend_jusquaux_metriques_et_a_leur_grille(
        self, client_connecte, jeu_de_donnees
    ):
        """
        Retour de recette #634 : « il manque les indicateurs et les métriques et
        les grilles de métriques ».

        La grille est le barème qui donne son sens à une mesure : sans elle, un
        lecteur extérieur voit ce qui est suivi, mais pas ce qui compte comme un
        bon résultat. Les mesures, elles, restent internes.
        """
        from tests.factories.enjeux import MetriqueFactory

        plan = jeu_de_donnees['plans']['ouest']
        MetriqueFactory(
            id_indicateur=plan.indicateur_racine,
            nom_metrique='Recouvrement', unite='%',
            type_metrique=None,
            score_1_label='Absent', score_2_label='Rare', score_3_label='Présent',
            score_4_label='Fréquent', score_5_label='Dominant',
        )

        reponse = client_connecte.get(url_fiche(plan))

        indicateur = (
            reponse.data['enjeux'][0]['objectifs_long_terme'][0]
            ['niveaux_exigence'][0]['indicateurs'][0]
        )
        metrique = next(
            m for m in indicateur['metriques'] if m['nom_metrique'] == 'Recouvrement'
        )
        assert metrique['unite'] == '%'
        assert [palier['valeur'] for palier in metrique['grille']] == [
            'Absent', 'Rare', 'Présent', 'Fréquent', 'Dominant',
        ]
        assert [palier['libelle'] for palier in metrique['grille']][0] == 'Très mauvais'

    def test_une_metrique_sans_grille_ne_publie_pas_de_grille(
        self, client_connecte, jeu_de_donnees
    ):
        """Pas de grille vide : cinq cases à « — » n'apprennent rien."""
        from tests.factories.enjeux import MetriqueFactory

        plan = jeu_de_donnees['plans']['ouest']
        MetriqueFactory(
            id_indicateur=plan.indicateur_racine,
            nom_metrique='Effectif', unite='individus', type_metrique=None,
        )

        reponse = client_connecte.get(url_fiche(plan))

        indicateur = (
            reponse.data['enjeux'][0]['objectifs_long_terme'][0]
            ['niveaux_exigence'][0]['indicateurs'][0]
        )
        metrique = next(
            m for m in indicateur['metriques'] if m['nom_metrique'] == 'Effectif'
        )
        assert metrique['grille'] is None

    def test_une_action_porte_son_rattachement_a_larborescence(
        self, client_connecte, jeu_de_donnees
    ):
        """
        L'action est affichée **sous** l'indicateur qu'elle sert (#634) : la
        fiche doit donc dire de quel indicateur et de quelles métriques elle
        dépend, sinon elle ne peut vivre que dans une liste à plat.
        """
        from tests.factories.enjeux import MetriqueFactory

        plan = jeu_de_donnees['plans']['ouest']
        metrique = MetriqueFactory(
            id_indicateur=plan.indicateur_racine, nom_metrique='Recouvrement',
            type_metrique=None,
        )
        OperationFactory(
            libelle='Comptage annuel', id_indicateur=plan.indicateur_racine,
            metriques=[metrique],
        )

        reponse = client_connecte.get(url_fiche(plan))

        action = next(
            a for a in reponse.data['actions'] if a['libelle'] == 'Comptage annuel'
        )
        assert action['id_indicateur'] == plan.indicateur_racine.pk
        assert action['indicateur'] == 'Indicateur Ouest'
        assert [m['nom_metrique'] for m in action['metriques']] == ['Recouvrement']

    def test_un_utilisateur_dun_autre_organisme_peut_consulter(
        self, client_connecte, jeu_de_donnees
    ):
        """C'est la raison d'être de la fiche : partager entre gestionnaires."""
        assert client_connecte.get(
            url_fiche(jeu_de_donnees['plans']['est'])
        ).status_code == 200

    def test_un_brouillon_na_pas_de_fiche(self, client_connecte, jeu_de_donnees):
        assert client_connecte.get(
            url_fiche(jeu_de_donnees['plans']['brouillon'])
        ).status_code == 404

    def test_la_fiche_exige_detre_connecte(self, jeu_de_donnees):
        assert APIClient().get(
            url_fiche(jeu_de_donnees['plans']['ouest'])
        ).status_code in (401, 403)

    def test_un_plan_inconnu_renvoie_404(self, client_connecte, jeu_de_donnees):
        assert client_connecte.get('/api/exploration/plans/inexistant/').status_code == 404


@pytest.mark.integration
class TestFichePubliqueCloisonnement:
    """
    La fiche est le seul endroit où le contenu d'un plan sort de son périmètre
    de lecture (#610). Ces tests verrouillent ce qui en sort.
    """

    #: Fragments de noms de champs qui n'ont rien à faire dans une fiche
    #: publique : budget, RH, données empiriques et traçabilité interne.
    INTERDITS = [
        'budget', 'cout', 'etp', 'montant', 'financ',
        'poste', 'fonction', 'salaire', 'jours',
        'mesure', 'realisation', 'realise',
        'utilisateur', 'date_ajout', 'date_maj',
    ]

    def test_aucun_champ_de_gestion_nest_expose(
        self, client_connecte, jeu_de_donnees
    ):
        reponse = client_connecte.get(url_fiche(jeu_de_donnees['plans']['ouest']))

        fautifs = [
            cle for cle in _cles_profondes(reponse.data)
            if any(interdit in cle.lower() for interdit in self.INTERDITS)
        ]
        assert fautifs == [], f'Champs interdits exposés : {fautifs}'

    def test_les_actions_nexposent_pas_leurs_financeurs(
        self, client_connecte, jeu_de_donnees
    ):
        """
        `operateurs` et `partenaires` disent qui agit — c'est de la structure.
        `financeurs` dit qui paie : c'est du budget, donc hors périmètre.
        """
        plan = jeu_de_donnees['plans']['ouest']
        OperationFactory(
            libelle='Action financée',
            id_indicateur=plan.indicateur_racine,
            operateurs='Équipe technique',
            partenaires='CEN voisin',
            financeurs='Agence de l\'eau',
        )
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Action financée'
        )

        assert action['operateurs'] == 'Équipe technique'
        assert 'financeurs' not in action


# --------------------------------------------------------------------------- #
# Fiche action : suivi, protocoles et indicateurs de réponse
# --------------------------------------------------------------------------- #

def _nomenclature(type_mnemonique, mnemonique, label):
    from tests.factories.core import NomenclatureFactory, TypeNomenclatureFactory

    return NomenclatureFactory(
        id_type=TypeNomenclatureFactory(mnemonique=type_mnemonique),
        mnemonique=mnemonique, cd_nomenclature=mnemonique, label=label,
    )


def _action_avec_suivi(plan, **champs_suivi):
    """Une action de connaissance portant un suivi et deux protocoles."""
    from tests.factories.enjeux import (
        ProtocoleFactory, SuiviInventaireFactory,
    )

    standardise = ProtocoleFactory(
        protocole_dans_campanule=True,
        protocole_campanule_nom='STOC-EPS',
        description_protocole='Points d\'écoute de 5 minutes.',
        objectif_protocole='Suivre la tendance des populations.',
        respect_protocole=True,
        periode_echantillonnage='Avril à juin',
        documentation_disponible=True,
        url_documentation='https://exemple.fr/stoc',
    )
    libre = ProtocoleFactory(
        protocole_dans_campanule=False,
        nom_protocole='Comptage maison',
        respect_protocole=False,
        justification_non_respect='Effectifs trop faibles pour le protocole.',
        differences_protocole='Deux passages au lieu de quatre.',
    )
    defauts = {
        'id_pg': plan,
        'intitule': 'Suivi des limicoles nicheurs',
        'objectif_principal': 'OBJ_ETAT_CONSERVATION',
        'cibles_principales': 'ESPECES',
        'taxon_taxref': 'Calidris alpina',
        'habitats': [{'cd_hab': '1150', 'lb_hab_fr': 'Lagunes côtières'}],
        'frequence_nombre': 2,
        'frequence_unite': 'an',
        'outil_saisie': 'GEONATURE',
        'protocoles': [standardise, libre],
    }
    suivi = SuiviInventaireFactory(**{**defauts, **champs_suivi})
    return OperationFactory(
        libelle='Comptage des limicoles',
        id_indicateur=plan.indicateur_racine,
        id_suivi=suivi,
    ), suivi


@pytest.mark.integration
class TestFicheActionDetaillee:
    """
    Retour de recette #634 : « il faut plus d'informations dans les détails ».

    Une action de connaissance se lisait comme un intitulé et une période. Ce
    qu'elle observe — l'espèce, l'habitat, le protocole — et ce qui mesure son
    effet — l'indicateur de réponse — n'étaient pas publiés.
    """

    def test_laction_publie_son_suivi(self, client_connecte, jeu_de_donnees):
        plan = jeu_de_donnees['plans']['ouest']
        _nomenclature('OBJECTIF_SUIVI', 'OBJ_ETAT_CONSERVATION',
                      'État de conservation')
        _nomenclature('CIBLE_SUIVI', 'ESPECES', 'Espèces')
        _nomenclature('OUTIL_SAISIE', 'GEONATURE', 'GeoNature')
        _action_avec_suivi(plan)
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Comptage des limicoles'
        )
        suivi = action['suivi']

        assert suivi['intitule'] == 'Suivi des limicoles nicheurs'
        assert suivi['taxon'] == 'Calidris alpina'
        assert suivi['habitats'] == [
            {'cd_hab': '1150', 'lb_hab_fr': 'Lagunes côtières'}
        ]
        assert suivi['frequence'] == '2 / an'
        # Les mnémoniques stockés en base sortent en libellés lisibles.
        assert suivi['objectif_principal'] == 'État de conservation'
        assert suivi['cible_principale'] == 'Espèces'
        assert suivi['outil_saisie'] == 'GeoNature'

    def test_un_mnemonique_sans_nomenclature_sort_tel_quel(
        self, client_connecte, jeu_de_donnees
    ):
        """Mieux vaut un mnémonique brut qu'une case vide sur une fiche."""
        plan = jeu_de_donnees['plans']['ouest']
        _action_avec_suivi(plan)
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Comptage des limicoles'
        )
        assert action['suivi']['objectif_principal'] == 'OBJ_ETAT_CONSERVATION'

    def test_laction_publie_ses_protocoles(self, client_connecte, jeu_de_donnees):
        plan = jeu_de_donnees['plans']['ouest']
        _action_avec_suivi(plan)
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Comptage des limicoles'
        )
        protocoles = {p['nom']: p for p in action['suivi']['protocoles']}

        assert set(protocoles) == {'STOC-EPS', 'Comptage maison'}
        standardise = protocoles['STOC-EPS']
        assert standardise['standardise'] is True
        assert standardise['objectif'] == 'Suivre la tendance des populations.'
        assert standardise['periode_echantillonnage'] == 'Avril à juin'
        assert standardise['url_documentation'] == 'https://exemple.fr/stoc'

    def test_un_protocole_non_respecte_publie_sa_justification(
        self, client_connecte, jeu_de_donnees
    ):
        """
        Un protocole appliqué avec des écarts ne se compare pas à un protocole
        appliqué à la lettre : sans la justification, la donnée est trompeuse.
        """
        plan = jeu_de_donnees['plans']['ouest']
        _action_avec_suivi(plan)
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Comptage des limicoles'
        )
        libre = next(
            p for p in action['suivi']['protocoles']
            if p['nom'] == 'Comptage maison'
        )

        assert libre['standardise'] is False
        assert libre['respecte'] is False
        assert libre['justification_non_respect'] == (
            'Effectifs trop faibles pour le protocole.'
        )
        assert libre['differences'] == 'Deux passages au lieu de quatre.'

    def test_les_mois_de_suivi_sortent_en_libelles(
        self, client_connecte, jeu_de_donnees
    ):
        from tests.factories.enjeux import ProtocoleFactory, SuiviInventaireFactory

        plan = jeu_de_donnees['plans']['ouest']
        _nomenclature('PERIODE_SUIVI', 'JANVIER', 'Janvier')
        _nomenclature('PERIODE_SUIVI', 'FEVRIER', 'Février')
        protocole = ProtocoleFactory(
            nom_protocole='Comptage hivernal', periode_suivi='JANVIER,FEVRIER',
        )
        OperationFactory(
            libelle='Comptage hivernal',
            id_indicateur=plan.indicateur_racine,
            id_suivi=SuiviInventaireFactory(id_pg=plan, protocoles=[protocole]),
        )
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Comptage hivernal'
        )
        assert action['suivi']['protocoles'][0]['periode_suivi'] == [
            'Janvier', 'Février',
        ]

    def test_les_habitats_retombent_sur_le_champ_texte_hérité(
        self, client_connecte, jeu_de_donnees
    ):
        """Les suivis d'avant #368 n'ont que `habitat_ref`, en texte libre."""
        plan = jeu_de_donnees['plans']['ouest']
        _action_avec_suivi(plan, habitats=[], habitat_ref='Prés-salés')
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Comptage des limicoles'
        )
        assert action['suivi']['habitats'] == [
            {'cd_hab': None, 'lb_hab_fr': 'Prés-salés'}
        ]

    def test_une_action_sans_suivi_ne_publie_pas_de_bloc_vide(
        self, client_connecte, jeu_de_donnees
    ):
        plan = jeu_de_donnees['plans']['ouest']
        OperationFactory(
            libelle='Fauche tardive', id_indicateur=plan.indicateur_racine,
        )
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Fauche tardive'
        )
        assert action['suivi'] is None

    def test_le_suivi_ne_publie_pas_la_charge_de_travail(
        self, client_connecte, jeu_de_donnees
    ):
        """`nb_etp_cycle` est du temps de travail, donc du RH : hors périmètre."""
        plan = jeu_de_donnees['plans']['ouest']
        _action_avec_suivi(plan)
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Comptage des limicoles'
        )
        for protocole in action['suivi']['protocoles']:
            assert 'nb_etp_cycle' not in protocole

    def test_lindicateur_de_reponse_est_publie_avec_sa_grille(
        self, client_connecte, jeu_de_donnees
    ):
        """
        L'indicateur de réponse dit si l'action a produit son effet. Sans sa
        grille, sa valeur ne se lit pas.
        """
        from tests.factories.enjeux import (
            IndicateurFactory, MetriqueFactory, NomenclatureTypeIndicateurFactory,
        )

        plan = jeu_de_donnees['plans']['ouest']
        reponse = IndicateurFactory(
            id_ne=None, id_resultat_attendu=None,
            nom_indicateur='Effort d\'arrachage',
            type_indicateur=NomenclatureTypeIndicateurFactory(
                mnemonique='REPONSE', cd_nomenclature='REPONSE', label='Réponse',
            ),
        )
        metrique = MetriqueFactory(
            id_indicateur=reponse, nom_metrique='Linéaire arraché', unite='m',
            type_metrique=None,
            score_1_label='Nul', score_2_label='Faible', score_3_label='Moyen',
            score_4_label='Bon', score_5_label='Complet',
        )
        OperationFactory(
            libelle='Arrachage de la renouée',
            id_indicateur=plan.indicateur_racine,
            metriques=[metrique],
        )
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Arrachage de la renouée'
        )

        assert [i['nom_indicateur'] for i in action['indicateurs_reponse']] == [
            'Effort d\'arrachage'
        ]
        publie = action['indicateurs_reponse'][0]
        assert publie['type_indicateur'] == 'Réponse'
        assert [p['valeur'] for p in publie['metriques'][0]['grille']] == [
            'Nul', 'Faible', 'Moyen', 'Bon', 'Complet',
        ]

    def test_lindicateur_de_reponse_ne_pollue_pas_le_cadre(
        self, client_connecte, jeu_de_donnees
    ):
        """
        Même règle que l'export de fiche action (#626) : la ligne « Indicateur »
        est celle de l'état ou de la pression que l'action sert. Deux règles
        différentes pour le même écran finiraient par diverger.
        """
        from tests.factories.enjeux import (
            IndicateurFactory, MetriqueFactory, NomenclatureTypeIndicateurFactory,
        )

        plan = jeu_de_donnees['plans']['ouest']
        # Accroché au même niveau d'exigence que l'indicateur d'état : c'est par
        # cette chaîne que l'action remonte jusqu'au plan.
        reponse = IndicateurFactory(
            id_ne=plan.indicateur_racine.id_ne, id_resultat_attendu=None,
            nom_indicateur='Effort fourni',
            type_indicateur=NomenclatureTypeIndicateurFactory(
                mnemonique='REPONSE', cd_nomenclature='REPONSE', label='Réponse',
            ),
        )
        OperationFactory(
            libelle='Action de réponse pure', id_indicateur=reponse,
            metriques=[MetriqueFactory(id_indicateur=reponse, type_metrique=None)],
        )
        index_plan(plan)

        action = next(
            a for a in client_connecte.get(url_fiche(plan)).data['actions']
            if a['libelle'] == 'Action de réponse pure'
        )

        assert action['indicateur'] is None
        assert action['metriques'] == []
        assert len(action['indicateurs_reponse']) == 1

    def test_le_cout_de_la_fiche_ne_depend_pas_du_nombre_dactions(
        self, client_connecte, jeu_de_donnees, django_assert_max_num_queries
    ):
        """
        Garde-fou anti N+1 : suivi, protocoles, sites et indicateurs de réponse
        sont préchargés. Sans ça, chaque action ajouterait ses propres requêtes.
        """
        plan = jeu_de_donnees['plans']['ouest']
        _action_avec_suivi(plan)
        index_plan(plan)

        with django_assert_max_num_queries(25):
            client_connecte.get(url_fiche(plan))

        for indice in range(5):
            action, _ = _action_avec_suivi(plan)
            action.libelle = f'Comptage {indice}'
            action.save()

        with django_assert_max_num_queries(25):
            reponse = client_connecte.get(url_fiche(plan))
        assert len(reponse.data['actions']) == 6
