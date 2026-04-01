"""
Migration: Operation.id_metrique FK → Operation.metriques M2M

Remplace la FK simple (1 opération = 1 métrique) par une relation M2M
via la table de liaison cor_operation_metrique.

Ordre des opérations :
1. Créer la table cor_operation_metrique
2. Copier les données FK existantes vers la table de liaison
3. Supprimer la FK id_metrique (libère related_name='operations')
4. Ajouter le champ M2M metriques (avec related_name='operations')
"""

from django.db import migrations, models
import django.db.models.deletion


def migrate_fk_to_m2m(apps, schema_editor):
    """Copie chaque Operation.id_metrique FK dans la table de liaison."""
    CorOperationMetrique = apps.get_model('plans', 'CorOperationMetrique')

    # Lecture directe via SQL pour éviter les problèmes d'état du modèle
    # (le champ id_metrique existe encore en DB à ce stade)
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute(
            'SELECT id_operation, id_metrique FROM "general"."t_operations" '
            'WHERE id_metrique IS NOT NULL'
        )
        rows = cursor.fetchall()

    links = [
        CorOperationMetrique(id_operation_id=op_id, id_metrique_id=met_id)
        for op_id, met_id in rows
    ]
    CorOperationMetrique.objects.bulk_create(links, batch_size=1000)


def reverse_m2m_to_fk(apps, schema_editor):
    """Reverse: copie la première métrique de chaque M2M vers la FK."""
    CorOperationMetrique = apps.get_model('plans', 'CorOperationMetrique')

    from django.db import connection
    with connection.cursor() as cursor:
        # Pour chaque opération, prendre la première métrique (id le plus petit)
        cursor.execute(
            'UPDATE "general"."t_operations" o '
            'SET id_metrique = sub.id_metrique '
            'FROM ('
            '  SELECT DISTINCT ON (id_operation) id_operation, id_metrique '
            '  FROM "general"."cor_operation_metrique" '
            '  ORDER BY id_operation, id_metrique'
            ') sub '
            'WHERE o.id_operation = sub.id_operation'
        )


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0045_remove_id_type_suivi_from_suiviinventaire"),
    ]

    operations = [
        # 1. Créer la table de liaison
        migrations.CreateModel(
            name="CorOperationMetrique",
            fields=[
                ("id", models.AutoField(primary_key=True, serialize=False)),
                (
                    "id_operation",
                    models.ForeignKey(
                        db_column="id_operation",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="plans.operation",
                        verbose_name="Opération",
                    ),
                ),
                (
                    "id_metrique",
                    models.ForeignKey(
                        db_column="id_metrique",
                        on_delete=django.db.models.deletion.CASCADE,
                        to="plans.metrique",
                        verbose_name="Métrique",
                    ),
                ),
            ],
            options={
                "db_table": '"general"."cor_operation_metrique"',
                "db_table_comment": "Liaison opérations - métriques",
                "verbose_name": "Opération - Métrique",
                "verbose_name_plural": "Opérations - Métriques",
                "unique_together": {("id_operation", "id_metrique")},
            },
        ),
        # 2. Copier les données FK → M2M
        migrations.RunPython(migrate_fk_to_m2m, reverse_m2m_to_fk),
        # 3. Supprimer la FK id_metrique (libère related_name='operations')
        migrations.RemoveField(
            model_name="operation",
            name="id_metrique",
        ),
        # 4. Ajouter le champ M2M metriques (avec related_name='operations')
        migrations.AddField(
            model_name="operation",
            name="metriques",
            field=models.ManyToManyField(
                blank=True,
                help_text="Métriques associées à cette opération",
                related_name="operations",
                through="plans.CorOperationMetrique",
                to="plans.metrique",
                verbose_name="Métriques",
            ),
        ),
    ]
