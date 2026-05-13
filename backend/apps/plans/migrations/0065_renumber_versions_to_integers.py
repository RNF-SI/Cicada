# #279 — Numérotation des versions en entiers (1, 2, 3...) au lieu de 1.0, 1.1
#
# Renumérote chaque chaîne `plan_parent` chronologiquement (par `date_ajout`)
# en démarrant à 1 sur la racine. Les valeurs antérieures au format '1.0',
# '1.1', '2.0'... sont remplacées par des entiers.

from django.db import migrations, models


def renumber_versions(apps, schema_editor):
    PlanGestion = apps.get_model("plans", "PlanGestion")

    # 1. Trouver les racines de chaîne (plan_parent IS NULL).
    roots = PlanGestion.objects.filter(plan_parent__isnull=True).order_by("date_ajout")

    def walk(plan, position):
        plan.version = str(position)
        plan.save(update_fields=["version"])
        children = PlanGestion.objects.filter(plan_parent=plan).order_by("date_ajout")
        next_pos = position + 1
        for child in children:
            next_pos = walk(child, next_pos)
        return next_pos

    for root in roots:
        walk(root, 1)

    # 2. Filet de sécurité : les plans orphelins (cycle, parent supprimé...)
    # qui ne sont pas attrapés par la marche depuis les racines.
    orphans = PlanGestion.objects.exclude(version__regex=r"^\d+$").order_by("date_ajout")
    for plan in orphans:
        plan.version = "1"
        plan.save(update_fields=["version"])


def reverse_noop(apps, schema_editor):
    """La conversion vers les versions décimales historiques n'est pas
    reconstructible : on ne fait rien en reverse."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0064_revert_categorie_socio_economique"),
    ]

    operations = [
        migrations.AlterField(
            model_name="plangestion",
            name="version",
            field=models.CharField(
                default="1",
                help_text="Version du plan dans la chaîne (entier : 1, 2, 3...)",
                max_length=20,
                verbose_name="Version",
            ),
        ),
        migrations.RunPython(renumber_versions, reverse_noop),
    ]
