"""
Tests de symétrie entre serializers de lecture et d'écriture.

Tout champ accepté en écriture doit aussi être renvoyé en lecture, sinon les
données sont écrasées au round-trip create → edit → save (cf. issue #187 où
habitat_ref était accepté en écriture mais absent du serializer de lecture →
champ vide au formulaire d'édition → écrasement à la sauvegarde).

Les champs purement read-only (computed labels, audit timestamps, FK display
helpers) sont autorisés à n'exister qu'en lecture.
"""
import pytest

from apps.plans.serializers_operations import (
    SuiviInventaireSerializer,
    SuiviInventaireWriteSerializer,
)
from apps.plans.serializers_suivis import (
    SuiviInventaireDetailSerializer,
    SuiviInventaireCreateSerializer,
)


def _assert_write_subset_of_read(
    write_cls,
    read_cls,
    read_only_extras: set[str],
):
    """
    Vérifie que tout champ d'écriture est exposé en lecture.

    `read_only_extras` liste les champs qui n'existent que côté lecture
    (labels calculés, audit, FK display, etc.) — c'est attendu et OK.
    """
    write_fields = set(write_cls.Meta.fields)
    read_fields = set(read_cls.Meta.fields)

    missing_in_read = write_fields - read_fields
    assert not missing_in_read, (
        f"Champs acceptés par {write_cls.__name__} mais absents de "
        f"{read_cls.__name__} (round-trip cassé, perte de données potentielle) : "
        f"{sorted(missing_in_read)}"
    )

    # Sanity check: les seuls champs en read-only-only doivent être ceux déclarés.
    extras_in_read = (read_fields - write_fields) - read_only_extras
    assert not extras_in_read, (
        f"{read_cls.__name__} expose des champs absents de {write_cls.__name__} "
        f"qui ne sont pas listés comme read-only-only : {sorted(extras_in_read)}. "
        f"Si c'est intentionnel (label, timestamp...), ajoute-les à "
        f"read_only_extras du test."
    )


@pytest.mark.unit
class TestSuiviInventaireSerializerSymmetry:
    """
    Le SuiviInventaireSerializer (nested dans OperationSerializer) doit exposer
    tous les champs que le SuiviInventaireWriteSerializer accepte. Sinon les
    données saisies à la création disparaissent au formulaire d'édition.
    """

    def test_write_fields_are_subset_of_read_fields(self):
        _assert_write_subset_of_read(
            write_cls=SuiviInventaireWriteSerializer,
            read_cls=SuiviInventaireSerializer,
            read_only_extras={
                # Labels calculés (résolus depuis nomenclature)
                "bancarisation_label",
                "outil_saisie_label",
                # Audit
                "date_ajout",
                "date_maj",
            },
        )


@pytest.mark.unit
class TestSuiviInventaireStandaloneSerializerSymmetry:
    """
    Idem pour le SuiviInventaire standalone (endpoint /api/inventaires/).
    """

    def test_write_fields_are_subset_of_read_fields(self):
        _assert_write_subset_of_read(
            write_cls=SuiviInventaireCreateSerializer,
            read_cls=SuiviInventaireDetailSerializer,
            read_only_extras={
                # Labels calculés
                "bancarisation_label",
                "outil_saisie_label",
                "statut_label",
                "type_action_code",
                "type_action_label",
                "plan_nom",
                # Audit + métadonnées
                "date_ajout",
                "date_maj",
                "createur_nom",
                "nb_operations",
            },
        )
