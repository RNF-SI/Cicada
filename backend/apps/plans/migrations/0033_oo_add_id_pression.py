"""
Migration: Add id_pression FK to ObjectifOperationnel and populate it.

Step 1 of 2: Add nullable id_pression column, populate it from
id_facteur_influence via Pression, then make it non-null.

For each OO, find (or create) a Pression under its FacteurInfluence.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def populate_id_pression(apps, schema_editor):
    """
    For each ObjectifOperationnel, find or create a Pression under
    its FacteurInfluence, and set id_pression.
    """
    ObjectifOperationnel = apps.get_model('plans', 'ObjectifOperationnel')
    Pression = apps.get_model('plans', 'Pression')

    for oo in ObjectifOperationnel.objects.select_related('id_facteur_influence').all():
        fi = oo.id_facteur_influence
        # Try to find an existing Pression under this FI
        pression = Pression.objects.filter(id_facteur_influence=fi).first()
        if not pression:
            # Create a default Pression
            pression = Pression.objects.create(
                id_facteur_influence=fi,
                libelle=f"Pression de {fi.libelle}",
                description="Pression créée automatiquement lors de la migration",
                id_utilisateur_ajout=oo.id_utilisateur_ajout,
            )
        oo.id_pression = pression
        oo.save(update_fields=['id_pression'])


def reverse_populate(apps, schema_editor):
    """Reverse: copy id_facteur_influence from the pression back to OO."""
    # Nothing needed: the next migration (0034) will handle the reverse
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0032_operation_fk_metrique'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # 1. Add nullable id_pression column
        migrations.AddField(
            model_name='objectifoperationnel',
            name='id_pression',
            field=models.ForeignKey(
                blank=True,
                null=True,
                db_column='id_pression',
                help_text="Pression parente de cet objectif opérationnel",
                on_delete=django.db.models.deletion.CASCADE,
                related_name='objectifs_operationnels',
                to='plans.pression',
                verbose_name='Pression',
            ),
        ),
        # 2. Populate id_pression from id_facteur_influence
        migrations.RunPython(populate_id_pression, reverse_populate),
    ]
