"""
Migration: Add M2M relationship between ObjectifOperationnel and Pression.

Step 1 of 2: Create the junction table cor_oo_pression and populate it
from the existing FK id_pression on ObjectifOperationnel.
"""
from django.db import migrations, models
import django.db.models.deletion


def populate_cor_oo_pression(apps, schema_editor):
    """
    For each ObjectifOperationnel that has an id_pression FK,
    create a row in cor_oo_pression to preserve the relationship.
    """
    CorOoPression = apps.get_model('plans', 'CorOoPression')
    ObjectifOperationnel = apps.get_model('plans', 'ObjectifOperationnel')

    links = []
    for oo in ObjectifOperationnel.objects.filter(id_pression__isnull=False).iterator():
        links.append(CorOoPression(id_oo_id=oo.id_oo, id_pression_id=oo.id_pression_id))

    if links:
        CorOoPression.objects.bulk_create(links, ignore_conflicts=True)


def reverse_populate(apps, schema_editor):
    """
    Reverse: populate the FK id_pression from the M2M junction table.
    Takes the first pression linked to each OO.
    """
    CorOoPression = apps.get_model('plans', 'CorOoPression')
    ObjectifOperationnel = apps.get_model('plans', 'ObjectifOperationnel')

    for link in CorOoPression.objects.order_by('id_oo_id', 'id_pression_id').iterator():
        ObjectifOperationnel.objects.filter(
            id_oo=link.id_oo_id, id_pression__isnull=True
        ).update(id_pression=link.id_pression_id)


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0049_add_has_borne_score1_score5'),
    ]

    operations = [
        # 1. Create the junction table
        migrations.CreateModel(
            name='CorOoPression',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_oo', models.ForeignKey(
                    db_column='id_oo',
                    on_delete=django.db.models.deletion.CASCADE,
                    to='plans.objectifoperationnel',
                    verbose_name='Objectif opérationnel',
                )),
                ('id_pression', models.ForeignKey(
                    db_column='id_pression',
                    on_delete=django.db.models.deletion.CASCADE,
                    to='plans.pression',
                    verbose_name='Pression',
                )),
            ],
            options={
                'db_table': '"general"."cor_oo_pression"',
                'verbose_name': 'Lien OO-Pression',
                'verbose_name_plural': 'Liens OO-Pression',
                'unique_together': {('id_oo', 'id_pression')},
            },
        ),

        # 2. Populate junction table from existing FK data
        migrations.RunPython(populate_cor_oo_pression, reverse_populate),
    ]
