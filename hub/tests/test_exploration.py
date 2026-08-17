"""
Tests de la lecture de l'exploration sur l'index agrégé.

Ce qui compte ici, et qui ne se teste nulle part ailleurs : la recherche est
**transverse**. Le tri par pertinence classe dans une même liste des documents
venus d'instances différentes, et les compteurs d'onglets portent sur l'union.
C'est la propriété qui justifie l'index central plutôt qu'une fédération de
requêtes, et c'est donc elle qu'il faut vérifier.
"""

import pytest

from apps.index.models import ContenuIndexe, PlanIndexe

JETON_LECTURE = 'jeton-lecture'

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def lecture_autorisee(settings):
    settings.HUB_READ_TOKEN = JETON_LECTURE


@pytest.fixture
def lire(client):
    """Appelle l'API de lecture avec le jeton, et rend le corps décodé."""
    def appel(url, **params):
        reponse = client.get(
            url, params, HTTP_X_HUB_TOKEN=JETON_LECTURE
        )
        assert reponse.status_code == 200, reponse.content
        return reponse.json()
    return appel


def publier_plan(instance_id='rnf', id_pg=1, nom='Plan', contenus=(), **kwargs):
    """Pose directement un plan indexé, sans passer par le dépôt."""
    defauts = {
        'slug': f'plan-{instance_id}-{id_pg}',
        'statut': 'valide',
        'annee_debut': 2020,
        'annee_fin': 2030,
    }
    defauts.update(kwargs)
    plan = PlanIndexe.objects.create(
        instance_id=instance_id, id_pg=id_pg, nom=nom, **defauts
    )
    for numero, contenu in enumerate(contenus, start=1):
        champs = {
            'type_contenu': ContenuIndexe.TYPE_ENJEU,
            'id_objet': id_pg * 1000 + numero,
            'titre': 'Sans titre',
        }
        champs.update(contenu)
        ContenuIndexe.objects.create(
            instance_id=instance_id, plan=plan,
            statut_pg=plan.statut,
            annee_debut=plan.annee_debut, annee_fin=plan.annee_fin,
            type_site_codes=plan.type_site_codes,
            area_ids=plan.area_ids,
            **champs,
        )
    return plan


class TestAcces:
    def test_la_lecture_exige_un_jeton(self, client):
        assert client.get('/api/exploration/contenus/').status_code == 403

    def test_un_jeton_de_lecture_invalide_est_refuse(self, client):
        reponse = client.get(
            '/api/exploration/contenus/', HTTP_X_HUB_TOKEN='jeton-invente'
        )
        assert reponse.status_code == 403


class TestRechercheTransverse:
    """La propriété qui justifie l'index central."""

    def test_une_recherche_remonte_le_contenu_de_toutes_les_instances(self, lire):
        publier_plan('rnf', 1, contenus=[{'titre': 'Roselières du delta'}])
        publier_plan('cen', 1, contenus=[{'titre': 'Roselières du lac'}])

        corps = lire('/api/exploration/contenus/', q='roselieres')

        assert corps['pagination']['count'] == 2
        assert {r['instance_id'] for r in corps['results']} == {'rnf', 'cen'}

    def test_les_compteurs_d_onglets_portent_sur_l_union(self, lire):
        publier_plan('rnf', 1, contenus=[
            {'titre': 'Enjeu A', 'type_contenu': 'enjeu'},
            {'titre': 'Action A', 'type_contenu': 'action'},
        ])
        publier_plan('cen', 1, contenus=[
            {'titre': 'Action B', 'type_contenu': 'action'},
        ])

        corps = lire('/api/exploration/contenus/')

        assert corps['compteurs']['tout'] == 3
        assert corps['compteurs']['action'] == 2
        assert corps['compteurs']['enjeu'] == 1

    def test_les_compteurs_ignorent_l_onglet_actif(self, lire):
        """
        Sinon sélectionner « Actions » ferait tomber à zéro tous les autres
        onglets, et l'utilisateur ne pourrait plus en sortir.
        """
        publier_plan('rnf', 1, contenus=[
            {'titre': 'Enjeu A', 'type_contenu': 'enjeu'},
            {'titre': 'Action A', 'type_contenu': 'action'},
        ])

        corps = lire('/api/exploration/contenus/', onglet='action')

        assert corps['pagination']['count'] == 1
        assert corps['compteurs']['enjeu'] == 1

    def test_le_bandeau_du_plan_accompagne_chaque_resultat(self, lire):
        """
        Le plan est joint depuis sa table, pas recopié sur chaque ligne : c'est
        ce que la table `t_plan_indexe` achète.
        """
        publier_plan(
            'cen', 7, nom='Plan du Vercors',
            gestionnaire_principal='CEN Auvergne-Rhône-Alpes',
            contenus=[{'titre': 'Pelouses sèches'}],
        )

        resultat = lire('/api/exploration/contenus/')['results'][0]

        assert resultat['plan']['nom'] == 'Plan du Vercors'
        assert resultat['plan']['gestionnaire_principal'] == 'CEN Auvergne-Rhône-Alpes'
        assert resultat['plan']['reference'] == 'cen:plan-cen-7'


class TestModesDeRecherche:
    def test_le_mode_titres_ignore_la_description(self, lire):
        publier_plan('rnf', 1, contenus=[
            {'titre': 'Enjeu', 'description': 'restauration hydraulique'},
        ])

        assert lire(
            '/api/exploration/contenus/', q='hydraulique'
        )['pagination']['count'] == 0
        assert lire(
            '/api/exploration/contenus/', q='hydraulique', titres_seulement='false'
        )['pagination']['count'] == 1

    def test_les_rattachements_sont_trouves_dans_les_deux_modes(self, lire):
        """Chercher une espèce ne doit pas obliger à élargir la recherche."""
        publier_plan('rnf', 1, contenus=[
            {'titre': 'Enjeu', 'rattachements': 'Alnus glutinosa'},
        ])

        assert lire(
            '/api/exploration/contenus/', q='glutinosa'
        )['pagination']['count'] == 1

    def test_la_recherche_pardonne_une_faute_de_frappe(self, lire):
        """La radicalisation ne pardonne aucune lettre en trop : le trigramme si."""
        publier_plan('rnf', 1, contenus=[
            {'titre': 'Lacs eutrophes naturels'},
        ])

        assert lire(
            '/api/exploration/contenus/', q='eutotrophes'
        )['pagination']['count'] == 1


class TestFacettes:
    def test_le_filtre_par_instance(self, lire):
        """Facette propre au hub : un index local n'a qu'une seule provenance."""
        publier_plan('rnf', 1, contenus=[{'titre': 'A'}])
        publier_plan('cen', 1, contenus=[{'titre': 'B'}])

        corps = lire('/api/exploration/contenus/', instances='cen')

        assert corps['pagination']['count'] == 1
        assert corps['results'][0]['instance_id'] == 'cen'

    def test_le_filtre_par_type_d_aire_protegee(self, lire):
        publier_plan('rnf', 1, type_site_codes=['RNN'], contenus=[{'titre': 'A'}])
        publier_plan('rnf', 2, type_site_codes=['RNR'], contenus=[{'titre': 'B'}])

        corps = lire('/api/exploration/contenus/', types_site='RNN')
        assert [r['titre'] for r in corps['results']] == ['A']

    def test_le_filtre_par_organisme_ne_rend_rien(self, lire):
        """
        Comportement voulu, pas un oubli : faute d'identité nationale des
        organismes, la colonne est vide. Une absence visible vaut mieux qu'un
        appariement faux sur un identifiant local.
        """
        publier_plan('rnf', 1, contenus=[{'titre': 'A'}])

        assert lire(
            '/api/exploration/contenus/', organismes='42'
        )['pagination']['count'] == 0

    def test_un_groupe_de_sous_types_ne_masque_pas_les_autres_types(self, lire):
        """
        Cocher « Indicateur d'état » raffine les indicateurs et laisse les
        enjeux intacts.
        """
        publier_plan('rnf', 1, contenus=[
            {'titre': 'Enjeu', 'type_contenu': 'enjeu'},
            {'titre': 'Ind. état', 'type_contenu': 'indicateur', 'sous_type': 'ETAT'},
            {'titre': 'Ind. pression', 'type_contenu': 'indicateur',
             'sous_type': 'PRESSION'},
        ])

        corps = lire('/api/exploration/contenus/', types_indicateur='ETAT')

        assert sorted(r['titre'] for r in corps['results']) == ['Enjeu', 'Ind. état']


class TestModePlan:
    def test_recherche_par_nom_de_plan(self, lire):
        publier_plan('rnf', 1, nom='Plan de la Camargue')
        publier_plan('cen', 1, nom='Plan du Vercors')

        corps = lire('/api/exploration/plans/', q='camargue')
        assert [p['nom'] for p in corps['results']] == ['Plan de la Camargue']

    def test_recherche_par_nom_de_site(self, lire):
        publier_plan(
            'rnf', 1, nom='Plan sans rapport',
            sites=[{'nom_site': 'Marais de Brouage', 'slug': 'brouage'}],
            sites_noms='Marais de Brouage',
        )

        corps = lire('/api/exploration/plans/', q='brouage')
        assert corps['pagination']['count'] == 1

    def test_recherche_par_nom_de_zone(self, lire):
        """
        Les zones sont stockées par identifiant : la recherche par nom passe par
        le référentiel, qui est petit et local au hub.
        """
        from django.contrib.gis.geos import MultiPolygon, Polygon

        from apps.geo.models import AreaType, LArea

        carre = MultiPolygon(
            Polygon(((0, 0), (0, 1), (1, 1), (1, 0), (0, 0))), srid=4326
        )
        type_dep = AreaType.objects.create(
            type_code=AreaType.DEPARTEMENT, type_name='Département'
        )
        dep = LArea.objects.create(
            id_type=type_dep, area_code='13', area_name='Bouches-du-Rhône', geom=carre
        )
        publier_plan('rnf', 1, nom='Plan sans rapport', area_ids=[dep.id_area])

        corps = lire('/api/exploration/plans/', q='bouches')
        assert corps['pagination']['count'] == 1

    def test_le_filtre_par_statut_en_cours(self, lire):
        """`en_cours` n'est pas un statut en base : c'est une période courante."""
        publier_plan('rnf', 1, nom='Terminé', annee_debut=2000, annee_fin=2010)
        publier_plan('rnf', 2, nom='En cours', annee_debut=2020, annee_fin=2090)

        corps = lire('/api/exploration/plans/', statuts='en_cours')
        assert [p['nom'] for p in corps['results']] == ['En cours']


class TestFiche:
    def test_la_fiche_est_resservie_a_plat_comme_par_une_instance(self, lire):
        """
        Même forme que la fiche d'une instance, métadonnées en plus.

        Envelopper la fiche dans un objet obligerait le frontend à distinguer
        les deux sources — ce que la bascule vers le hub doit précisément lui
        épargner. Cette exigence a été apprise par l'échec : la première version
        enveloppait, et la page de fiche s'affichait avec un titre vide.
        """
        arbre = {'nom': 'Camargue', 'enjeux': [{'titre': 'Roselières'}]}
        publier_plan('rnf', 42, nom='Camargue', fiche=arbre)

        corps = lire('/api/exploration/plans/rnf:plan-rnf-42/')

        assert corps['nom'] == 'Camargue'
        assert corps['enjeux'] == [{'titre': 'Roselières'}]
        assert corps['instance_id'] == 'rnf'
        assert 'fiche' not in corps

    def test_la_fiche_annonce_sa_date_de_publication(self, lire):
        """
        Un instantané sans date ne se distingue pas d'une donnée jointe à la
        volée — or c'est précisément la différence qu'il faut pouvoir voir.
        """
        publier_plan('rnf', 42, fiche={'nom': 'X'})

        corps = lire('/api/exploration/plans/rnf:plan-rnf-42/')
        assert corps['date_publication'] is not None

    def test_deux_instances_peuvent_avoir_le_meme_slug(self, lire):
        """
        C'est pour ça que la référence porte l'instance : ni l'identifiant du
        plan ni son slug ne sont uniques entre déploiements.
        """
        publier_plan('rnf', 1, nom='Plan RNF', slug='camargue', fiche={'nom': 'RNF'})
        publier_plan('cen', 1, nom='Plan CEN', slug='camargue', fiche={'nom': 'CEN'})

        assert lire('/api/exploration/plans/rnf:camargue/')['nom'] == 'RNF'
        assert lire('/api/exploration/plans/cen:camargue/')['nom'] == 'CEN'

    def test_une_reference_inconnue_rend_404(self, client):
        reponse = client.get(
            '/api/exploration/plans/rnf:inexistant/', HTTP_X_HUB_TOKEN=JETON_LECTURE
        )
        assert reponse.status_code == 404
