"""
Restructuration ObjectifOperationnel – étape 2 : schéma.

- Rendre id_facteur_influence non-nullable et CASCADE
- Supprimer id_enjeu
"""
from django.db import migrations, models
import django.db.models.deletion


def migrate_data_backward(apps, schema_editor):
    """Reverse: restore id_enjeu from facteur_influence's enjeu."""
    ObjectifOperationnel = apps.get_model('plans', 'ObjectifOperationnel')

    for oo in ObjectifOperationnel.objects.select_related('id_facteur_influence').all():
        if oo.id_facteur_influence_id:
            oo.id_enjeu_id = oo.id_facteur_influence.id_enjeu_id
            oo.save(update_fields=['id_enjeu_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0030_oo_under_facteur_influence'),
    ]

    operations = [
        # Step 1: Make id_facteur_influence non-nullable and CASCADE
        migrations.AlterField(
            model_name='objectifoperationnel',
            name='id_facteur_influence',
            field=models.ForeignKey(
                db_column='id_facteur_influence',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='objectifs_operationnels',
                to='plans.facteurinfluence',
                verbose_name="Facteur d'influence",
                help_text="Facteur d'influence parent de cet objectif opérationnel",
            ),
        ),

        # Step 2: Remove id_enjeu from OO
        migrations.RemoveField(
            model_name='objectifoperationnel',
            name='id_enjeu',
        ),
    ]
