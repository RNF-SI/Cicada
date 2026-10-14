"""
#676 — Un plan prolongé (#250) reste « en cours » dans l'exploration pendant
ses années d'extension.

Le statut `en_cours` retenait `annee_debut <= année <= annee_fin` : un plan
terminé l'an dernier mais prolongé de deux ans disparaissait du filtre. L'index
porte désormais `annees_extension`, comme le plan, et le transmet au hub.
"""

import datetime

import pytest

from apps.search.federation import contenu_depuis_document
from apps.search.indexing import facettes_du_plan
from apps.search.models import ContenuIndexe
from apps.search.push import charge_utile

from .test_api_exploration import (
    URL_CONTENUS, URL_PLANS, _plan_avec_contenu, client_connecte, noms,  # noqa: F401
)

Y = datetime.date.today().year


def _plan(nom, annee_debut, annee_fin, annees_extension):
    plan = _plan_avec_contenu(nom, f'Enjeu {nom}', nom)
    plan.annee_debut = annee_debut
    plan.annee_fin = annee_fin
    plan.annees_extension = annees_extension
    plan.save()
    return plan


@pytest.fixture
def plans(db):
    return {
        # terminé l'an dernier, prolongé de 2 ans → en cours jusqu'en Y+1
        'prolonge': _plan('Prolongé', Y - 10, Y - 1, 2),
        # prolongation d'un an écoulée → terminé
        'prolongation_ecoulee': _plan('Écoulé', Y - 12, Y - 2, 1),
        # non prolongé, terminé
        'termine': _plan('Terminé', Y - 10, Y - 1, 0),
        # non prolongé, en cours
        'en_cours': _plan('En cours', Y - 2, Y + 3, 0),
    }


@pytest.mark.integration
class TestIndexPortLaProlongation:

    def test_facettes_du_plan(self, plans):
        assert facettes_du_plan(plans['prolonge'])['annees_extension'] == 2

    def test_lignes_d_index_rafraichies_a_la_prolongation(self, plans):
        """Prolonger un plan déjà indexé met à jour ses lignes (signal)."""
        lignes = ContenuIndexe.objects.filter(id_pg=plans['prolonge'])
        assert lignes.exists()
        assert set(lignes.values_list('annees_extension', flat=True)) == {2}

        plan = plans['prolonge']
        plan.annees_extension = 0
        plan.save()
        assert set(lignes.values_list('annees_extension', flat=True)) == {0}


@pytest.mark.integration
class TestFiltreEnCours:

    def test_mode_contenus(self, client_connecte, plans):
        reponse = client_connecte.get(URL_CONTENUS, {'statuts': 'en_cours', 'types': 'enjeu'})
        titres = {r['titre'] for r in reponse.data['results']}
        assert titres == {'Enjeu Prolongé', 'Enjeu En cours'}

    def test_mode_plans(self, client_connecte, plans):
        reponse = client_connecte.get(URL_PLANS, {'statuts': 'en_cours'})
        assert set(noms(reponse)) == {'Prolongé', 'En cours'}

    def test_statut_valide_inchange(self, client_connecte, plans):
        reponse = client_connecte.get(URL_PLANS, {'statuts': 'valide'})
        assert set(noms(reponse)) == {'Prolongé', 'Écoulé', 'Terminé', 'En cours'}


@pytest.mark.integration
class TestTransmission:

    def test_charge_publiee_vers_le_hub(self, plans):
        assert charge_utile(plans['prolonge'], avec_fiche=False)['annees_extension'] == 2
        assert charge_utile(plans['en_cours'], avec_fiche=False)['annees_extension'] == 0

    def test_document_recu_sans_le_champ(self, db):
        """Un document émis avant #676 n'a pas `annees_extension` : 0."""
        ligne = contenu_depuis_document(
            {'type_contenu': 'enjeu', 'id_objet': 1, 'titre': 'Ancien',
             'statut_pg': 'valide', 'annee_debut': 2020, 'annee_fin': 2030},
            'autre',
        )
        assert ligne.annees_extension == 0
