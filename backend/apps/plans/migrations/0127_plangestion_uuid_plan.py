"""
#645 — Identifiant stable du plan, exposé aux applications tierces (DOCenCEN).

En trois temps, et non un simple `AddField` : `default=uuid.uuid4` est évalué
**une seule fois** par Django pour remplir les lignes existantes, qui
recevraient donc toutes le même UUID — et la contrainte d'unicité tomberait.
On ajoute donc la colonne sans contrainte, on tire un UUID par plan, puis on
pose l'unicité. Le tirage réécrit **toutes** les lignes, et pas seulement les
NULL : après l'`AddField`, elles portent déjà toutes la même valeur.
"""
import uuid

from django.db import migrations, models


def attribuer_uuid(apps, schema_editor):
    PlanGestion = apps.get_model('plans', 'PlanGestion')
    for plan in PlanGestion.objects.all().only('pk'):
        PlanGestion.objects.filter(pk=plan.pk).update(uuid_plan=uuid.uuid4())


def retirer_uuid(apps, schema_editor):
    """Rien à défaire : la colonne disparaît avec le `RemoveField` inverse."""


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0126_indicateur_partage_parents'),
    ]

    operations = [
        migrations.AddField(
            model_name='plangestion',
            name='uuid_plan',
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                null=True,
                help_text="Identifiant stable du plan, exposé aux applications tierces.",
                verbose_name='Identifiant unique',
            ),
        ),
        migrations.RunPython(attribuer_uuid, retirer_uuid),
        migrations.AlterField(
            model_name='plangestion',
            name='uuid_plan',
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
                help_text="Identifiant stable du plan, exposé aux applications tierces.",
                verbose_name='Identifiant unique',
            ),
        ),
    ]
