# Revert de #260 : on revient à un choix binaire pour la catégorie d'enjeu
# (conservation du patrimoine naturel OU socio-économique, pas les deux).

from django.db import migrations, models


def collapse_to_single_category(apps, schema_editor):
    """
    Avant suppression du champ `categorie_socio_economique`, on consolide :
    - eco=False, socio=True (socio-éco pur)   → eco=False (inchangé)
    - eco=True, socio=False (eco pur)          → eco=True (inchangé)
    - eco=True, socio=True (transversal)       → eco=True (on retombe sur eco)
    - eco=False, socio=False (théoriquement impossible post-#260) → eco=False
    """
    Enjeu = apps.get_model("plans", "Enjeu")
    # Les transversaux retombent côté conservation du patrimoine naturel.
    Enjeu.objects.filter(
        categorie_ecologique=True, categorie_socio_economique=True
    ).update(categorie_socio_economique=False)


def reverse_noop(apps, schema_editor):
    """L'ajout du champ se fera côté schéma ; on ne sait pas reconstruire le
    flag transversal, donc rien à faire ici."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0063_add_categorie_action_reserve"),
    ]

    operations = [
        migrations.RunPython(collapse_to_single_category, reverse_noop),
        migrations.RemoveField(
            model_name="enjeu",
            name="categorie_socio_economique",
        ),
        migrations.AlterField(
            model_name="enjeu",
            name="categorie_ecologique",
            field=models.BooleanField(
                default=True,
                help_text="True=Conservation du patrimoine naturel, False=Socio-économique",
                null=True,
                verbose_name="Catégorie conservation du patrimoine naturel",
            ),
        ),
    ]
