"""
D'où viennent les données servies par le hub (#636).

Une recherche transverse mélange, dans une même liste triée par pertinence, des
plans venus de plusieurs structures. Tant que rien ne le dit, la liste se lit
comme un résultat local : un gestionnaire du CEN qui tombe sur un plan de RNF
croit consulter le sien, et deux plans homonymes de deux structures deviennent
indiscernables. C'est le seul point de la fédération où une donnée juste peut
être comprise de travers sans qu'aucune erreur ne soit visible.

Ce qui est vérifié ici :

- chaque résultat porte l'instance d'origine **et son nom** ;
- ce nom est résolu même pour une instance qui n'est pas au registre — sinon la
  provenance ne s'affiche que pour les instances déjà enrôlées, c'est-à-dire
  pas pendant la migration, précisément quand elle est la plus utile ;
- l'inventaire des structures qui alimentent la recherche est consultable.
"""

import pytest

from apps.index.identites import identites
from apps.index.models import ContenuIndexe, Instance, LotPublication, PlanIndexe

pytestmark = pytest.mark.django_db

JETONS = {'rnf': 'jeton-rnf-lecture', 'cen': 'jeton-cen-lecture'}


@pytest.fixture(autouse=True)
def lecture_autorisee(settings):
    settings.HUB_READ_TOKENS = dict(JETONS)


@pytest.fixture
def lire(client):
    def appel(url, comme='rnf', **params):
        reponse = client.get(url, params, HTTP_X_HUB_TOKEN=JETONS[comme])
        assert reponse.status_code == 200, reponse.content
        return reponse.json()
    return appel


def publier(instance_id, id_pg=1, nom='Plan', **kwargs):
    plan = PlanIndexe.objects.create(
        instance_id=instance_id, id_pg=id_pg, nom=nom,
        slug=kwargs.pop('slug', f'plan-{id_pg}'),
        statut='valide', annee_debut=2020, annee_fin=2030,
        **kwargs,
    )
    ContenuIndexe.objects.create(
        instance_id=instance_id, plan=plan,
        type_contenu=ContenuIndexe.TYPE_ENJEU, id_objet=id_pg * 10,
        titre='Roselières', statut_pg=plan.statut,
        annee_debut=plan.annee_debut, annee_fin=plan.annee_fin,
    )
    return plan


def declarer(instance_id, libelle, url=''):
    """Ce qu'une instance dit d'elle-même en ouvrant un lot."""
    return LotPublication.objects.create(
        instance_id=instance_id, format_version=1,
        libelle_declare=libelle, url_publique_declaree=url,
    )


class TestResolutionDuNom:
    def test_le_registre_fait_foi(self):
        Instance.objects.create(instance_id='rnf', libelle='RNF (registre)')
        declarer('rnf', 'RNF (déclaré)')
        assert identites()['rnf']['libelle'] == 'RNF (registre)'

    def test_une_instance_non_enrolee_est_nommee_par_ce_qu_elle_declare(self):
        """
        Le cas de la migration : l'instance publie encore par jeton
        d'environnement, donc sans ligne au registre. Sans ce repli, sa
        provenance s'afficherait « rnf » — un identifiant technique, dans une
        interface destinée à des gestionnaires.
        """
        declarer('rnf', 'Réserves Naturelles de France')
        assert identites()['rnf']['libelle'] == 'Réserves Naturelles de France'

    def test_la_derniere_declaration_gagne(self):
        """Une structure qui se renomme n'a rien à faire de plus que publier."""
        declarer('rnf', 'Ancien nom')
        declarer('rnf', 'Nouveau nom')
        assert identites()['rnf']['libelle'] == 'Nouveau nom'

    def test_faute_de_tout_le_reste_l_identifiant_sert_de_nom(self):
        """
        Jamais de provenance vide : une tuile sans provenance se lit comme une
        donnée locale, c'est-à-dire faux.
        """
        publier('inconnue')
        assert identites()['inconnue']['libelle'] == 'inconnue'


class TestProvenanceDesResultats:
    def test_chaque_contenu_dit_de_quelle_structure_il_vient(self, lire):
        Instance.objects.create(instance_id='cen', libelle='CEN Auvergne')
        publier('rnf', 1)
        publier('cen', 2)
        declarer('rnf', 'Réserves Naturelles de France')

        par_instance = {
            r['instance_id']: r for r in lire('/api/exploration/contenus/')['results']
        }
        assert par_instance['rnf']['instance_libelle'] == (
            'Réserves Naturelles de France'
        )
        assert par_instance['cen']['instance_libelle'] == 'CEN Auvergne'
        # Le bandeau du plan la porte aussi : c'est lui qu'affiche la tuile.
        assert par_instance['cen']['plan']['instance_libelle'] == 'CEN Auvergne'

    def test_chaque_plan_dit_de_quelle_structure_il_vient(self, lire):
        declarer('rnf', 'Réserves Naturelles de France')
        publier('rnf', 1)

        resultat = lire('/api/exploration/plans/')['results'][0]
        assert resultat['instance_id'] == 'rnf'
        assert resultat['instance_libelle'] == 'Réserves Naturelles de France'

    def test_la_fiche_dit_qui_l_a_publiee_et_quand(self, lire):
        declarer('rnf', 'Réserves Naturelles de France', 'https://rnf.example')
        publier('rnf', 1, slug='camargue', fiche={'nom': 'Camargue', 'enjeux': []})

        fiche = lire('/api/exploration/plans/rnf:camargue/')
        assert fiche['instance_libelle'] == 'Réserves Naturelles de France'
        assert fiche['url_instance'] == 'https://rnf.example'
        assert fiche['date_publication']
        # La fiche reste servie à plat : la provenance s'ajoute à côté, elle ne
        # l'enveloppe pas.
        assert fiche['nom'] == 'Camargue'

    def test_le_nom_est_resolu_une_fois_par_page(self, lire, django_assert_max_num_queries):
        """
        Vingt tuiles venues de deux structures ne doivent pas coûter vingt
        résolutions : la provenance est un affichage, pas une requête par ligne.
        """
        declarer('rnf', 'RNF')
        declarer('cen', 'CEN')
        for numero in range(1, 11):
            publier('rnf', numero)
            publier('cen', 100 + numero)

        # Recherche + compteurs + provenance : la marge couvre la pagination.
        with django_assert_max_num_queries(10):
            lire('/api/exploration/contenus/')


class TestFiltreParStructure:
    def test_on_peut_restreindre_la_recherche_a_une_structure(self, lire):
        publier('rnf', 1, nom='Plan RNF')
        publier('cen', 2, nom='Plan CEN')

        resultats = lire('/api/exploration/plans/', instances='cen')['results']
        assert [r['nom'] for r in resultats] == ['Plan CEN']

    def test_le_filtre_vaut_aussi_pour_le_contenu(self, lire):
        publier('rnf', 1)
        publier('cen', 2)

        resultats = lire('/api/exploration/contenus/', instances='rnf')['results']
        assert {r['instance_id'] for r in resultats} == {'rnf'}


class TestInventaireDesStructures:
    def test_la_liste_dit_qui_alimente_la_recherche(self, lire):
        Instance.objects.create(instance_id='cen', libelle='CEN Auvergne')
        declarer('rnf', 'Réserves Naturelles de France')
        publier('rnf', 1)
        publier('cen', 2)
        publier('cen', 3)

        corps = lire('/api/exploration/instances/')
        assert corps['count'] == 2
        par_id = {i['instance_id']: i for i in corps['instances']}
        assert par_id['cen']['libelle'] == 'CEN Auvergne'
        assert par_id['cen']['plans'] == 2
        assert par_id['rnf']['contenus'] == 1
        assert par_id['rnf']['derniere_publication']

    def test_une_instance_enrolee_mais_muette_n_y_figure_pas(self, lire):
        """
        Elle ne filtre rien et ne couvre rien : l'afficher promettrait des
        résultats que la recherche ne rendra jamais.
        """
        Instance.objects.create(instance_id='dreal', libelle='DREAL')
        publier('rnf', 1)

        corps = lire('/api/exploration/instances/')
        assert [i['instance_id'] for i in corps['instances']] == ['rnf']

    def test_l_inventaire_exige_un_jeton(self, client):
        assert client.get('/api/exploration/instances/').status_code == 403


class TestDeclarationALOuvertureDuLot:
    def test_l_instance_se_nomme_en_ouvrant_son_lot(self, client, settings):
        settings.HUB_FEDERATION_TOKENS = {'rnf': 'jeton-depot'}

        reponse = client.post(
            '/api/federation/lots/',
            data={
                'format_version': 1,
                'libelle': 'Réserves Naturelles de France',
                'url_publique': 'https://rnf.example',
            },
            content_type='application/json',
            HTTP_X_FEDERATION_TOKEN='jeton-depot',
        )
        assert reponse.status_code == 201, reponse.content

        lot = LotPublication.objects.get(pk=reponse.json()['lot_id'])
        assert lot.libelle_declare == 'Réserves Naturelles de France'
        assert lot.url_publique_declaree == 'https://rnf.example'

    def test_une_instance_ancienne_publie_toujours(self, client, settings):
        """
        Le libellé est facultatif : une instance non mise à jour ne l'envoie
        pas, et sa publication ne doit pas échouer pour autant.
        """
        settings.HUB_FEDERATION_TOKENS = {'rnf': 'jeton-depot'}

        reponse = client.post(
            '/api/federation/lots/',
            data={'format_version': 1},
            content_type='application/json',
            HTTP_X_FEDERATION_TOKEN='jeton-depot',
        )
        assert reponse.status_code == 201, reponse.content

    def test_declarer_un_nom_n_enrole_pas(self, client, settings):
        """
        Le garde-fou : créer une ligne de registre à la publication ferait
        basculer l'instance du côté « enrôlée », et `identifier_porteur`
        refuserait alors son propre jeton d'environnement — la publication
        suivante échouerait.
        """
        settings.HUB_FEDERATION_TOKENS = {'rnf': 'jeton-depot'}

        for _ in range(2):
            reponse = client.post(
                '/api/federation/lots/',
                data={'format_version': 1, 'libelle': 'RNF'},
                content_type='application/json',
                HTTP_X_FEDERATION_TOKEN='jeton-depot',
            )
            assert reponse.status_code == 201, reponse.content

        assert not Instance.objects.filter(instance_id='rnf').exists()
