"""
#676 — Un plan prolongé (#250) reste « en cours » pendant ses années
d'extension, sur le hub comme sur une instance.

`annees_extension` voyage avec le plan. Il est **optionnel** : une instance
antérieure à ce champ ne l'envoie pas, et sa publication ne doit pas échouer
pour autant — le plan est alors considéré comme non prolongé.
"""

import datetime

import pytest

from apps.index.models import ContenuIndexe, PlanIndexe

from test_exploration import lecture_autorisee, lire  # noqa: F401
from test_federation import Publication, jetons_configures, plan_charge  # noqa: F401

pytestmark = pytest.mark.django_db

Y = datetime.date.today().year


def _publier(client, *plans):
    reponse = Publication(client).publier(*plans)
    assert reponse.status_code == 200, reponse.content


class TestDepot:

    def test_la_prolongation_est_stockee_sur_le_plan_et_son_contenu(self, client):
        _publier(client, plan_charge(annees_extension=2))

        assert PlanIndexe.objects.get().annees_extension == 2
        assert ContenuIndexe.objects.get().annees_extension == 2

    def test_une_instance_qui_n_envoie_pas_le_champ_publie_quand_meme(self, client):
        charge = plan_charge()
        charge.pop('annees_extension', None)
        _publier(client, charge)

        assert PlanIndexe.objects.get().annees_extension == 0
        assert ContenuIndexe.objects.get().annees_extension == 0

    def test_une_valeur_nulle_vaut_zero(self, client):
        _publier(client, plan_charge(annees_extension=None))
        assert PlanIndexe.objects.get().annees_extension == 0

    def test_une_valeur_hors_bornes_est_refusee(self, client):
        publication = Publication(client)
        publication.ouvrir()
        reponse = publication.deposer(plan_charge(annees_extension=5))
        assert reponse.status_code == 400


class TestFiltreEnCours:

    @pytest.fixture
    def plans_publies(self, client):
        _publier(
            client,
            # terminé l'an dernier, prolongé de 2 ans → en cours jusqu'en Y+1
            plan_charge(1, 'Prolongé', annee_debut=Y - 10, annee_fin=Y - 1, annees_extension=2),
            # prolongation d'un an écoulée → terminé
            plan_charge(2, 'Écoulé', annee_debut=Y - 12, annee_fin=Y - 2, annees_extension=1),
            # non prolongé, terminé
            plan_charge(3, 'Terminé', annee_debut=Y - 10, annee_fin=Y - 1),
            # non prolongé, en cours
            plan_charge(4, 'En cours', annee_debut=Y - 2, annee_fin=Y + 3),
        )

    def test_mode_plans(self, lire, plans_publies):
        corps = lire('/api/exploration/plans/', statuts='en_cours')
        assert {p['nom'] for p in corps['results']} == {'Prolongé', 'En cours'}

    def test_mode_contenus(self, lire, plans_publies):
        corps = lire('/api/exploration/contenus/', statuts='en_cours')
        ids = {r['id_objet'] for r in corps['results']}
        # un enjeu par plan (id_objet = id_pg * 100 + 1)
        assert ids == {101, 401}
