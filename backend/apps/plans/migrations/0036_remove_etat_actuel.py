"""
Migration: Supprimer le modèle EtatActuel et rattacher OLT directement à Enjeu.

L'état de l'enjeu est désormais décrit par le champ texte Enjeu.etat_enjeu.
La hiérarchie passe de Enjeu → EtatActuel → OLT → NE
                         à Enjeu → OLT → NE.
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_olt_to_enjeu(apps, schema_editor):
    """Copy id_enjeu from EtatActuel to ObjectifLongTerme."""
    ObjectifLongTerme = apps.get_model('plans', 'ObjectifLongTerme')
    for olt in ObjectifLongTerme.objects.select_related('id_etat_actuel').all():
        olt.id_enjeu_id = olt.id_etat_actuel.id_enjeu_id
        olt.save(update_fields=['id_enjeu_id'])


def reverse_migrate(apps, schema_editor):
    """Reverse is not possible - data loss."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0035_add_operation_annee_organisme'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Add nullable id_enjeu FK to ObjectifLongTerme
        migrations.AddField(
            model_name='objectiflongterme',
            name='id_enjeu',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='objectifs_long_terme',
                db_column='id_enjeu',
                to='plans.enjeu',
                verbose_name='Enjeu',
            ),
        ),

        # Step 2: Data migration - copy id_enjeu from EtatActuel
        migrations.RunPython(migrate_olt_to_enjeu, reverse_migrate),

        # Step 3: Make id_enjeu non-nullable
        migrations.AlterField(
            model_name='objectiflongterme',
            name='id_enjeu',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='objectifs_long_terme',
                db_column='id_enjeu',
                to='plans.enjeu',
                verbose_name='Enjeu',
            ),
        ),

        # Step 4: Remove id_etat_actuel FK from ObjectifLongTerme
        migrations.RemoveField(
            model_name='objectiflongterme',
            name='id_etat_actuel',
        ),

        # Step 5: Delete EtatActuel model
        migrations.DeleteModel(
            name='EtatActuel',
        ),
    ]
