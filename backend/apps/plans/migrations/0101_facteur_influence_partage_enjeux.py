"""
#552 — Un facteur d'influence peut être PARTAGÉ entre plusieurs enjeux.

Passe la relation FacteurInfluence → Enjeu d'un FK unique (``id_enjeu``) à un
ManyToMany via la table de liaison ``cor_facteur_enjeu``. L'``ordre`` d'affichage
(auparavant global sur le facteur) devient propre à chaque enjeu et migre sur la
table de liaison.

Ordre des opérations (dans une seule migration réversible) :
  1. crée la table de liaison ``cor_facteur_enjeu`` (avec ``ordre``) ;
  2. libère le reverse accessor ``facteurs_influence`` du FK et rend ``id_enjeu``
     nullable (pour que le re-ajout à la descente ne casse pas sur une table peuplée) ;
  3. déclare le M2M ``enjeux`` (through explicite → opération d'état, pas de SQL) ;
  4. peuple la table de liaison depuis ``id_enjeu``/``ordre`` existants ;
  5. supprime les colonnes ``id_enjeu`` et ``ordre`` du facteur.

Descente réversible mais LOSSY : un facteur partagé sur N enjeux se recollapse sur
le premier enjeu lié (comportement attendu — la notion de partage n'existe plus).
"""
from django.db import migrations, models
import django.db.models.deletion


def populate_cor_facteur_enjeu(apps, schema_editor):
    """Une ligne cor_facteur_enjeu par facteur existant, reprenant id_enjeu + ordre."""
    CorFacteurEnjeu = apps.get_model('plans', 'CorFacteurEnjeu')
    FacteurInfluence = apps.get_model('plans', 'FacteurInfluence')

    rows = [
        CorFacteurEnjeu(
            id_facteur_influence_id=fi.id_facteur_influence,
            id_enjeu_id=fi.id_enjeu_id,
            ordre=fi.ordre,
        )
        for fi in FacteurInfluence.objects.filter(id_enjeu__isnull=False).iterator()
    ]
    if rows:
        CorFacteurEnjeu.objects.bulk_create(rows, ignore_conflicts=True)


def reverse_populate(apps, schema_editor):
    """Repeuple id_enjeu/ordre depuis la table de liaison (premier enjeu lié)."""
    CorFacteurEnjeu = apps.get_model('plans', 'CorFacteurEnjeu')
    FacteurInfluence = apps.get_model('plans', 'FacteurInfluence')

    for cor in CorFacteurEnjeu.objects.order_by('id_facteur_influence_id', 'ordre', 'id').iterator():
        FacteurInfluence.objects.filter(
            pk=cor.id_facteur_influence_id, id_enjeu__isnull=True
        ).update(id_enjeu=cor.id_enjeu_id, ordre=cor.ordre)


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0100_seed_fonctions_migrate_rh'),
    ]

    operations = [
        # 1. Table de liaison partagée.
        migrations.CreateModel(
            name='CorFacteurEnjeu',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('ordre', models.PositiveIntegerField(db_index=True, default=0, help_text="Ordre d'affichage du facteur parmi ceux de cet enjeu (0 = haut)", verbose_name='Ordre')),
                ('id_facteur_influence', models.ForeignKey(
                    db_column='id_facteur_influence',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cor_enjeux',
                    to='plans.facteurinfluence',
                    verbose_name="Facteur d'influence",
                )),
                ('id_enjeu', models.ForeignKey(
                    db_column='id_enjeu',
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='cor_facteurs',
                    to='plans.enjeu',
                    verbose_name='Enjeu',
                )),
            ],
            options={
                'db_table': '"general"."cor_facteur_enjeu"',
                'db_table_comment': "Liaison partagée facteurs d'influence ↔ enjeux (#552)",
                'verbose_name': 'Lien Facteur-Enjeu',
                'verbose_name_plural': 'Liens Facteur-Enjeu',
                'ordering': ['ordre', 'id'],
                'unique_together': {('id_facteur_influence', 'id_enjeu')},
            },
        ),

        # 2. Libère le reverse accessor et rend id_enjeu nullable (re-ajout sûr à la descente).
        migrations.AlterField(
            model_name='facteurinfluence',
            name='id_enjeu',
            field=models.ForeignKey(
                db_column='id_enjeu',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='+',
                to='plans.enjeu',
                verbose_name='Enjeu',
            ),
        ),

        # 3. Déclare le M2M (through explicite → pas de table créée, opération d'état).
        migrations.AddField(
            model_name='facteurinfluence',
            name='enjeux',
            field=models.ManyToManyField(
                through='plans.CorFacteurEnjeu',
                related_name='facteurs_influence',
                to='plans.enjeu',
                verbose_name='Enjeux',
                help_text="Enjeux auxquels ce facteur d'influence est rattaché (partagé, #552)",
            ),
        ),

        # 4. Peuple la liaison depuis les données existantes.
        migrations.RunPython(populate_cor_facteur_enjeu, reverse_populate),

        # 5. Supprime les colonnes désormais portées par la liaison.
        migrations.RemoveField(model_name='facteurinfluence', name='id_enjeu'),
        migrations.RemoveField(model_name='facteurinfluence', name='ordre'),

        # 6. L'ordering ne référence plus le champ 'ordre' (supprimé).
        migrations.AlterModelOptions(
            name='facteurinfluence',
            options={
                'ordering': ['id_facteur_influence'],
                'verbose_name': "Facteur d'influence",
                'verbose_name_plural': "Facteurs d'influence",
            },
        ),
    ]
