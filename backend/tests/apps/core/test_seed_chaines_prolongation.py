"""
Jeu d'essai : les chaînes de prolongation (#250) restent recettables chaque année.

Avec des années fixes, la recette de la prolongation se périmait : à partir de
2028, plus aucun plan prolongé n'était « en cours » (#675, #676) et plus aucun
n'était prolongeable. `periodes_extension()` ancre ces plans sur l'année
courante ; ce test vérifie, année par année, que chaque chaîne garde son rôle.
"""

import datetime

import pytest

from apps.core.management.commands.seeders.plans_seeder import periodes_extension
from apps.plans.models import PlanGestion
from apps.plans.serializers import PlanGestionDetailSerializer
from tests.factories.plans import PlanGestionFactory

ANNEES = range(2026, 2041)


def test_en_2026_le_jeu_d_essai_est_inchange():
    """Les écarts reproduisent exactement les années fixes d'avant."""
    assert periodes_extension(2026) == {
        'scandola': (2016, 2025),
        'grand_voyeux': (2015, 2024),
        'brouage': (2014, 2023),
    }


@pytest.mark.django_db
@pytest.mark.parametrize('annee', ANNEES)
def test_chaque_chaine_garde_son_role(annee, monkeypatch):
    periodes = periodes_extension(annee)
    plans = {
        cle: PlanGestionFactory(
            nom=cle, statut='modifie', annees_extension=extension,
            annee_debut=periodes[cle][0], annee_fin=periodes[cle][1],
        )
        for cle, extension in (('scandola', 2), ('grand_voyeux', 1), ('brouage', 2))
    }

    # Plan « en cours » / « actif » cette année : Scandola seul (#675, #676).
    actifs = set(
        PlanGestion.objects.filter(PlanGestion.actif_en_q(annee))
        .values_list('nom', flat=True)
    )
    assert actifs == {'scandola'}

    # Bouton « Prolonger » : Grand-Voyeux seul (reconduction d'un an, cumul ≤ 2).
    class DateFigee(datetime.date):
        @classmethod
        def today(cls):
            return cls(annee, 6, 15)

    monkeypatch.setattr(datetime, 'date', DateFigee)
    prolongeables = {
        cle for cle, plan in plans.items()
        if PlanGestionDetailSerializer(plan).data['peut_etre_etendu']
    }
    assert prolongeables == {'grand_voyeux'}
