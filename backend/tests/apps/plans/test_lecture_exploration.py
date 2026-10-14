"""
Tests de #683 — lecture d'exploration des écrans réels d'un plan.

Un utilisateur **sans aucun lien** avec un plan validé doit pouvoir en ouvrir la
page, l'arborescence et une fiche action — **sans** les données sensibles. Le
même plan en brouillon lui reste fermé, les listes de gestion ne s'élargissent
pas, et les suivis (mesures, réalisations) restent refusés.

Pour un utilisateur lié au plan, rien ne change : la réponse est entière et
`acces_exploration` vaut faux.
"""

import pytest
from rest_framework.test import APIClient

from apps.plans.exploration import CLES_SENSIBLES, elaguer
from tests.factories.enjeux import (
    EnjeuFactory, IndicateurFactory, MesureFactory, MetriqueFactory,
    NiveauExigenceFactory, NomenclatureTypeIndicateurFactory,
    ObjectifLongTermeFactory, OperationAnneeFactory, OperationFactory,
)
from tests.factories.plans import PlanGestionFactory
from tests.factories.users import RoleFactory


@pytest.fixture
def plan_valide(db):
    """Un plan validé portant une branche complète, une mesure et un budget."""
    plan = PlanGestionFactory(statut='valide', annee_debut=2020, annee_fin=2030)
    enjeu = EnjeuFactory(id_pg=plan, libelle='Enjeu public', slug='enjeu-public')
    olt = ObjectifLongTermeFactory(id_enjeu=enjeu, libelle='Objectif public')
    niveau = NiveauExigenceFactory(id_olt=olt)
    # Type fixé : `NomenclatureTypeIndicateurFactory` tourne sur ETAT / PRESSION
    # / RÉPONSE, et un indicateur de réponse n'apparaît pas dans l'arborescence
    # (#477) — le test dépendrait sinon de l'ordre d'exécution.
    etat = NomenclatureTypeIndicateurFactory(
        cd_nomenclature='ETAT', mnemonique='ETAT', label='État',
    )
    indicateur = IndicateurFactory(
        id_ne=niveau, nom_indicateur='Indicateur public', type_indicateur=etat,
    )
    metrique = MetriqueFactory(id_indicateur=indicateur)
    MesureFactory(id_metrique=metrique, valeur='42')
    operation = OperationFactory(libelle='Action publique', id_indicateur=indicateur)
    OperationAnneeFactory(id_operation=operation, annee=2021)
    plan.enjeu_racine = enjeu
    plan.operation_racine = operation
    plan.indicateur_racine = indicateur
    return plan


@pytest.fixture
def etranger(db):
    """Utilisateur d'un autre organisme, sans aucun lien avec le plan."""
    client = APIClient()
    client.force_authenticate(RoleFactory())
    return client


@pytest.fixture
def referent(plan_valide):
    """Référent du plan : il voit tout."""
    user = RoleFactory()
    plan_valide.referents.add(user)
    client = APIClient()
    client.force_authenticate(user)
    return client


def cles(donnees, acc=None):
    """Toutes les clés présentes dans une réponse, à toute profondeur."""
    acc = set() if acc is None else acc
    if isinstance(donnees, dict):
        for cle, valeur in donnees.items():
            acc.add(cle)
            cles(valeur, acc)
    elif isinstance(donnees, list):
        for element in donnees:
            cles(element, acc)
    return acc


class TestEcransReelsOuverts:

    def test_la_page_du_plan_souvre_sans_les_personnes(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/plans/by-slug/{plan_valide.slug}/')
        assert reponse.status_code == 200
        assert reponse.data['acces_exploration'] is True
        assert reponse.data['nom'] == plan_valide.nom
        assert not cles(reponse.data) & CLES_SENSIBLES

    def test_le_detail_du_plan_souvre_aussi(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/plans/{plan_valide.pk}/')
        assert reponse.status_code == 200
        assert reponse.data['acces_exploration'] is True

    def test_larborescence_souvre_sans_les_mesures_ni_le_budget(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/enjeux/by-plan/{plan_valide.pk}/')
        assert reponse.status_code == 200
        assert reponse.data['acces_exploration'] is True
        assert [e['libelle'] for e in reponse.data['enjeux']] == ['Enjeu public']
        presentes = cles(reponse.data)
        assert 'nom_indicateur' in presentes  # la structure est là…
        assert not presentes & CLES_SENSIBLES  # …pas les mesures ni le budget

    def test_la_fiche_action_souvre_sans_programmation(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/operations/{plan_valide.operation_racine.pk}/')
        assert reponse.status_code == 200
        assert reponse.data['acces_exploration'] is True
        assert reponse.data['libelle'] == 'Action publique'
        assert 'operation_annees' not in reponse.data
        assert 'financeurs' not in reponse.data
        assert 'createur_nom' not in reponse.data

    def test_les_actions_du_plan_souvrent(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/operations/by-plan/{plan_valide.pk}/')
        assert reponse.status_code == 200
        assert not cles(reponse.data) & CLES_SENSIBLES

    def test_un_indicateur_souvre_sans_ses_mesures(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/indicateurs/{plan_valide.indicateur_racine.pk}/')
        assert reponse.status_code == 200
        assert 'mesures' not in cles(reponse.data)


class TestCeQuiResteFerme:

    def test_un_brouillon_etranger_reste_ferme(self, etranger, db):
        plan = PlanGestionFactory(statut='draft')
        assert etranger.get(f'/api/plans/plans/by-slug/{plan.slug}/').status_code == 403
        assert etranger.get(f'/api/plans/plans/{plan.pk}/').status_code == 404
        assert etranger.get(f'/api/plans/enjeux/by-plan/{plan.pk}/').status_code == 403

    def test_la_liste_des_plans_ne_selargit_pas(self, etranger, plan_valide):
        """« Mes plans » reste mes plans : l'exploration a sa propre page."""
        reponse = etranger.get('/api/plans/plans/')
        assert reponse.status_code == 200
        assert plan_valide.pk not in {p['id_pg'] for p in reponse.data['results']}

    def test_la_liste_des_enjeux_ne_selargit_pas(self, etranger, plan_valide):
        reponse = etranger.get('/api/plans/enjeux/')
        assert reponse.status_code == 200
        assert reponse.data['pagination']['count'] == 0

    def test_les_suivis_restent_refuses(self, etranger, plan_valide):
        assert etranger.get(
            f'/api/plans/realisations/by-plan/{plan_valide.pk}/'
        ).status_code == 403
        assert etranger.get(
            f'/api/plans/indicateurs/{plan_valide.indicateur_racine.pk}/global/'
        ).status_code == 404

    def test_les_exports_restent_refuses(self, etranger, plan_valide):
        reponse = etranger.get(
            f'/api/plans/operations/{plan_valide.operation_racine.pk}/export-fiche-xlsx/'
        )
        assert reponse.status_code in (403, 404)

    def test_lecriture_reste_refusee(self, etranger, plan_valide):
        reponse = etranger.patch(
            f'/api/plans/enjeux/{plan_valide.enjeu_racine.pk}/',
            {'libelle': 'Vandalisme'}, format='json',
        )
        assert reponse.status_code in (403, 404)


class TestLecteurLie:

    def test_le_referent_voit_tout(self, referent, plan_valide):
        reponse = referent.get(f'/api/plans/plans/by-slug/{plan_valide.slug}/')
        assert reponse.status_code == 200
        assert reponse.data['acces_exploration'] is False
        assert 'referents' in reponse.data

        arbo = referent.get(f'/api/plans/enjeux/by-plan/{plan_valide.pk}/')
        assert arbo.data['acces_exploration'] is False
        assert 'mesures' in cles(arbo.data)


class TestElagage:

    def test_elaguer_retire_les_cles_a_toute_profondeur(self):
        donnees = {
            'libelle': 'ok',
            'createur_nom': 'secret',
            'metriques': [{'nom': 'm', 'mesures': [{'valeur': 1}]}],
            'operations': [{'operation_annees': [{'budget': 1}], 'code': 'A'}],
        }
        assert elaguer(donnees) == {
            'libelle': 'ok',
            'metriques': [{'nom': 'm'}],
            'operations': [{'code': 'A'}],
        }


class TestCloisonnementParFragments:
    """
    Même garde-fou que `TestFichePubliqueCloisonnement` côté exploration
    (#683) : on ne vérifie pas une liste de clés, mais que **aucun nom de
    champ** de ce qui est servi à un lecteur d'exploration ne contienne un
    fragment de gestion. Un champ `cout_total` ou `nb_jours_rh` ajouté plus
    tard à un sérialiseur sans être inscrit dans `CLES_SENSIBLES` fait donc
    échouer ce test, à n'importe quelle profondeur.
    """

    INTERDITS = [
        'budget', 'cout', 'etp', 'montant', 'financ',
        'poste', 'salaire', 'jours', 'ventilation',
        'mesure', 'realisation', 'realise',
        'utilisateur', 'createur', 'referent', 'membre',
        'fichier', 'document',
    ]

    #: Faux positifs connus : ces noms contiennent un fragment mais ne portent
    #: aucune donnée de gestion. Chaque entrée dit pourquoi.
    TOLERES = {
        'geo_documents',   # booléen : « patrimoine géologique — documents » (catégorie d'enjeu)
        'type_document', 'type_document_display', 'type_document_mnemonique',
        # ↑ nomenclature du plan (plan initial / évaluation), pas un fichier
        'id_referentiel_operations',  # référentiel des codes d'action, pas une réalisation
        'est_suivi_existant',  # booléen de structure d'une action
        'frequence_nombre',    # fréquence de l'action, pas du temps de travail
    }

    def _fautifs(self, donnees):
        return sorted(
            cle for cle in cles(donnees)
            if cle not in self.TOLERES
            and any(fragment in cle.lower() for fragment in self.INTERDITS)
        )

    def test_la_page_du_plan(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/plans/by-slug/{plan_valide.slug}/')
        assert self._fautifs(reponse.data) == []

    def test_larborescence(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/enjeux/by-plan/{plan_valide.pk}/')
        assert self._fautifs(reponse.data) == []

    def test_la_fiche_action(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/operations/{plan_valide.operation_racine.pk}/')
        assert self._fautifs(reponse.data) == []

    def test_les_actions_du_plan(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/operations/by-plan/{plan_valide.pk}/')
        assert self._fautifs(reponse.data) == []

    def test_un_indicateur(self, etranger, plan_valide):
        reponse = etranger.get(f'/api/plans/indicateurs/{plan_valide.indicateur_racine.pk}/')
        assert self._fautifs(reponse.data) == []
