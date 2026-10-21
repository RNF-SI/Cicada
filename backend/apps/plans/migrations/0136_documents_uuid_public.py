"""
#747 — Adresse publique non devinable des documents d'un plan et d'un enjeu.

En trois temps, comme `0127_plangestion_uuid_plan` : `default=uuid.uuid4` n'est
évalué qu'une fois pour les lignes existantes, qui recevraient toutes le même
UUID. On ajoute la colonne sans contrainte, on tire un UUID par document, puis
on pose l'unicité.
"""
import uuid

from django.db import migrations, models

MODELES = ('CorPgFichier', 'CorEnjeuFichier')


def attribuer_uuid(apps, schema_editor):
    for nom in MODELES:
        Modele = apps.get_model('plans', nom)
        for fichier in Modele.objects.all().only('pk'):
            Modele.objects.filter(pk=fichier.pk).update(uuid_public=uuid.uuid4())


def retirer_uuid(apps, schema_editor):
    """Rien à défaire : la colonne disparaît avec le `RemoveField` inverse."""


def _champ(**options):
    return models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        help_text="Identifiant non devinable de l'adresse publique du document.",
        verbose_name='Identifiant public',
        **options,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0135_operation_emprise_suit_sites'),
    ]

    operations = [
        migrations.AddField(
            model_name='corpgfichier', name='uuid_public', field=_champ(null=True),
        ),
        migrations.AddField(
            model_name='corenjeufichier', name='uuid_public', field=_champ(null=True),
        ),
        migrations.RunPython(attribuer_uuid, retirer_uuid),
        migrations.AlterField(
            model_name='corpgfichier', name='uuid_public', field=_champ(unique=True),
        ),
        migrations.AlterField(
            model_name='corenjeufichier', name='uuid_public', field=_champ(unique=True),
        ),
    ]
