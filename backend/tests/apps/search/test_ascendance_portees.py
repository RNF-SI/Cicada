"""
Tests de #681 / #682 : ascendance, descendance et axes de portée de l'index.

- chaque ligne porte le **chemin** qui mène à l'objet (enjeu → … → parent
  direct) et le slug de l'enjeu de sa branche ;
- la colonne **enfants** fait ressortir un enjeu quand c'est l'un de ses
  objectifs qui porte le mot cherché ;
- les trois axes de portée (`description`, `parents`, `enfants`) se cochent
  indépendamment, et l'API dit **où** chaque résultat a répondu ;
- en repli approximatif, le mot réellement retenu est désigné.
"""

import pytest
from rest_framework.test import APIClient

from apps.search.models import ContenuIndexe
from apps.search.surlignage import extrait_autour, mots_proches, similarite
from tests.factories.enjeux import (
    EnjeuFactory, FacteurInfluenceFactory, IndicateurFactory,
    NiveauExigenceFactory, ObjectifLongTermeFactory, OperationFactory,
    PressionFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import RoleFactory


@pytest.fixture
def plan(db):
    """
    enjeu « Zones humides » (slug connu)
      → facteur « Drainage » → pression « Assèchement des mares »
      → OLT « Restaurer la roselière » → NE « 10 ha » → indicateur « Surface »
          → action « Fauche tardive »
    """
    plan = PlanGestionFactory(statut='draft', annee_debut=2020, annee_fin=2030)
    enjeu = EnjeuFactory(
        id_pg=plan, libelle='Zones humides', slug='zones-humides',
        description='Un enjeu décrit avec le mot tourbière',
    )
    facteur = FacteurInfluenceFactory(libelle='Drainage', id_enjeu=enjeu)
    PressionFactory(id_facteur_influence=facteur, libelle='Assèchement des mares')
    olt = ObjectifLongTermeFactory(id_enjeu=enjeu, libelle='Restaurer la roselière')
    niveau = NiveauExigenceFactory(id_olt=olt, libelle='Au moins 10 ha')
    indicateur = IndicateurFactory(id_ne=niveau, nom_indicateur='Surface en eau libre')
    OperationFactory(libelle='Fauche tardive', id_indicateur=indicateur)
    plan.statut = 'valide'
    plan.save()
    return plan


def ligne(type_contenu, titre):
    return ContenuIndexe.objects.get(type_contenu=type_contenu, titre=titre)


class TestAscendance:

    def test_un_enjeu_na_pas_dascendance_mais_connait_son_slug(self, plan):
        enjeu = ligne('enjeu', 'Zones humides')
        assert enjeu.chemin == []
        assert enjeu.enjeu_slug == 'zones-humides'

    def test_le_chemin_dune_pression_passe_par_le_facteur(self, plan):
        pression = ligne('pression', 'Assèchement des mares')
        assert [m['type'] for m in pression.chemin] == ['enjeu', 'facteur']
        assert [m['libelle'] for m in pression.chemin] == ['Zones humides', 'Drainage']
        assert pression.enjeu_slug == 'zones-humides'

    def test_le_chemin_dun_indicateur_montre_le_niveau_dexigence(self, plan):
        """Le niveau d'exigence n'est pas explorable, mais l'arborescence l'affiche."""
        indicateur = ligne('indicateur', 'Surface en eau libre')
        assert [m['type'] for m in indicateur.chemin] == [
            'enjeu', 'objectif_lt', 'niveau_exigence',
        ]

    def test_le_chemin_dune_action_descend_jusqua_son_indicateur(self, plan):
        action = ligne('action', 'Fauche tardive')
        assert [m['type'] for m in action.chemin] == [
            'enjeu', 'objectif_lt', 'niveau_exigence', 'indicateur',
        ]
        assert action.chemin[-1]['libelle'] == 'Surface en eau libre'

    def test_le_parent_direct_reste_le_dernier_maillon(self, plan):
        """`parent_libelle` est conservé pour les lecteurs du contrat d'échange."""
        action = ligne('action', 'Fauche tardive')
        assert action.parent_libelle == action.chemin[-1]['libelle']


class TestDescendance:

    def test_un_enjeu_porte_les_libelles_de_toute_sa_branche(self, plan):
        enfants = ligne('enjeu', 'Zones humides').enfants
        for libelle in (
            'Drainage', 'Assèchement des mares', 'Restaurer la roselière',
            'Au moins 10 ha', 'Surface en eau libre', 'Fauche tardive',
        ):
            assert libelle in enfants

    def test_un_objectif_ne_porte_que_sa_descendance(self, plan):
        enfants = ligne('objectif_lt', 'Restaurer la roselière').enfants
        assert 'Surface en eau libre' in enfants
        assert 'Fauche tardive' in enfants
        assert 'Drainage' not in enfants

    def test_une_feuille_na_pas_de_descendance(self, plan):
        assert ligne('action', 'Fauche tardive').enfants == ''


@pytest.fixture
def client(db):
    client = APIClient()
    client.force_authenticate(RoleFactory())
    return client


def titres(reponse):
    return {r['titre'] for r in reponse.data['results']}


class TestPortees:

    def test_par_defaut_seul_lobjet_lui_meme_repond(self, client, plan):
        reponse = client.get('/api/exploration/contenus/', {'q': 'roselière'})
        assert titres(reponse) == {'Restaurer la roselière'}

    def test_la_portee_enfants_fait_remonter_lenjeu(self, client, plan):
        """#682 — un enjeu ressort quand un de ses objectifs porte le mot."""
        reponse = client.get(
            '/api/exploration/contenus/', {'q': 'roselière', 'portee': 'enfants'}
        )
        assert 'Zones humides' in titres(reponse)
        enjeu = next(r for r in reponse.data['results'] if r['titre'] == 'Zones humides')
        assert enjeu['correspondances'] == ['enfants']
        assert 'roselière' in enjeu['extraits']['enfants']

    def test_la_portee_parents_fait_descendre_le_mot_de_lenjeu(self, client, plan):
        reponse = client.get(
            '/api/exploration/contenus/', {'q': 'humides', 'portee': 'parents'}
        )
        assert 'Fauche tardive' in titres(reponse)
        action = next(r for r in reponse.data['results'] if r['titre'] == 'Fauche tardive')
        assert action['correspondances'] == ['contexte']
        # L'arborescence rendue permet de surligner le maillon qui a répondu.
        assert action['chemin'][0]['libelle'] == 'Zones humides'

    def test_la_portee_description_ne_touche_pas_aux_parents(self, client, plan):
        reponse = client.get(
            '/api/exploration/contenus/', {'q': 'tourbière', 'portee': 'description'}
        )
        assert titres(reponse) == {'Zones humides'}
        enjeu = reponse.data['results'][0]
        assert enjeu['correspondances'] == ['description']
        assert 'tourbière' in enjeu['extraits']['description']

        sans = client.get('/api/exploration/contenus/', {'q': 'tourbière'})
        assert titres(sans) == set()

    def test_les_portees_se_cumulent(self, client, plan):
        reponse = client.get(
            '/api/exploration/contenus/',
            {'q': 'roselière', 'portee': 'parents,enfants'},
        )
        assert {'Zones humides', 'Restaurer la roselière', 'Surface en eau libre'} <= titres(reponse)

    def test_lancien_parametre_titres_seulement_false_vaut_tout_elargir(self, client, plan):
        """Une URL de recherche partagée avant #681 doit encore marcher."""
        reponse = client.get(
            '/api/exploration/contenus/', {'q': 'tourbière', 'titres_seulement': 'false'}
        )
        assert 'Zones humides' in titres(reponse)

    def test_chaque_tuile_dit_si_ses_ecrans_reels_sont_ouvrables(self, client, plan):
        reponse = client.get('/api/exploration/contenus/', {'q': 'roselière'})
        assert reponse.data['results'][0]['acces_direct'] is True
        assert reponse.data['results'][0]['enjeu_slug'] == 'zones-humides'


class TestApproximation:

    def test_le_mot_retenu_est_designe(self, client, plan):
        reponse = client.get('/api/exploration/contenus/', {'q': 'roseliere'})
        # « roseliere » sans accent est trouvé exactement par unaccent…
        assert reponse.data['approximatif'] is False

        reponse = client.get('/api/exploration/contenus/', {'q': 'rosselière'})
        assert reponse.data['approximatif'] is True
        objectif = next(
            r for r in reponse.data['results'] if r['titre'] == 'Restaurer la roselière'
        )
        assert objectif['termes_surlignes'] == ['roselière']

    def test_similarite_trigramme(self):
        assert similarite('flamand', 'flamant') >= 0.5
        assert similarite('fleur', 'leur') < 0.5

    def test_mots_proches_respecte_lordre_du_texte(self):
        assert mots_proches('Le Flamant rose et le flamant nain', 'flamand') == ['Flamant']

    def test_extrait_autour_borne_la_fenetre(self):
        texte = ' '.join(f'mot{i}' for i in range(30)) + ' cible ' + 'fin ' * 5
        extrait = extrait_autour(texte, ['cible'], fenetre=2)
        assert extrait == '… mot28 mot29 cible fin fin …'
