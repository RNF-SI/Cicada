"""
Migration manuelle : Restructuration EtatActuel ↔ OLT.

Avant : Enjeu → EtatActuel (1:N, via id_enjeu) → OLT (1:N, via id_etat) → NE
Après  : Enjeu → OLT (1:N, via id_enjeu) → EtatActuel (1:1, via id_olt) → NE (via id_olt inchangé)

Étapes :
1. Ajouter id_enjeu (nullable) sur ObjectifLongTerme
2. Data migration : copier id_etat.id_enjeu → olt.id_enjeu
3. Rendre id_enjeu non-nullable + supprimer id_etat de ObjectifLongTerme
4. Ajouter id_olt (nullable) sur EtatActuel
5. Data migration : retrouver l'OLT lié et écrire etat.id_olt
6. Rendre id_olt non-nullable unique + supprimer id_enjeu de EtatActuel
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def migrate_olt_to_enjeu(apps, schema_editor):
    """Pour chaque OLT, copier id_etat.id_enjeu vers olt.id_enjeu."""
    ObjectifLongTerme = apps.get_model('plans', 'ObjectifLongTerme')
    for olt in ObjectifLongTerme.objects.select_related('id_etat').all():
        olt.id_enjeu_id = olt.id_etat.id_enjeu_id
        olt.save(update_fields=['id_enjeu_id'])


def migrate_etat_to_olt(apps, schema_editor):
    """Pour chaque EtatActuel, retrouver le premier OLT lié et écrire etat.id_olt."""
    EtatActuel = apps.get_model('plans', 'EtatActuel')
    ObjectifLongTerme = apps.get_model('plans', 'ObjectifLongTerme')
    for etat in EtatActuel.objects.all():
        olt = ObjectifLongTerme.objects.filter(id_etat_id=etat.id_etat_actuel).first()
        if olt:
            etat.id_olt_id = olt.id_olt
            etat.save(update_fields=['id_olt_id'])
        else:
            # EtatActuel sans OLT : créer un OLT par défaut
            olt = ObjectifLongTerme.objects.create(
                id_enjeu_id=etat.id_enjeu_id,
                libelle=f'OLT de {etat.libelle[:450]}',
                description=None,
                id_utilisateur_ajout_id=etat.id_utilisateur_ajout_id,
            )
            etat.id_olt_id = olt.id_olt
            etat.save(update_fields=['id_olt_id'])


def reverse_olt_to_etat(apps, schema_editor):
    """Reverse: pour chaque OLT, recréer id_etat depuis etat_actuel."""
    ObjectifLongTerme = apps.get_model('plans', 'ObjectifLongTerme')
    EtatActuel = apps.get_model('plans', 'EtatActuel')
    for olt in ObjectifLongTerme.objects.all():
        etat = EtatActuel.objects.filter(id_olt_id=olt.id_olt).first()
        if etat:
            olt.id_etat_id = etat.id_etat_actuel
            olt.save(update_fields=['id_etat_id'])


def reverse_etat_to_enjeu(apps, schema_editor):
    """Reverse: pour chaque EtatActuel, recréer id_enjeu depuis olt.id_enjeu."""
    EtatActuel = apps.get_model('plans', 'EtatActuel')
    ObjectifLongTerme = apps.get_model('plans', 'ObjectifLongTerme')
    for etat in EtatActuel.objects.all():
        olt = ObjectifLongTerme.objects.filter(id_etat_id=etat.id_etat_actuel).first()
        if olt:
            etat.id_enjeu_id = olt.id_enjeu_id
            etat.save(update_fields=['id_enjeu_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0008_indicateurs_metriques_mesures'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # === Step 1: Add id_enjeu to ObjectifLongTerme (nullable) ===
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

        # === Step 2: Data migration - copy EtatActuel.id_enjeu to OLT.id_enjeu ===
        migrations.RunPython(migrate_olt_to_enjeu, reverse_olt_to_etat),

        # === Step 3: Make id_enjeu non-nullable ===
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

        # === Step 4: Add id_olt to EtatActuel (nullable) ===
        migrations.AddField(
            model_name='etatactuel',
            name='id_olt',
            field=models.OneToOneField(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='etat_actuel',
                db_column='id_olt',
                to='plans.objectiflongterme',
                verbose_name='Objectif à long terme',
            ),
        ),

        # === Step 5: Data migration - link EtatActuel to OLT ===
        migrations.RunPython(migrate_etat_to_olt, reverse_etat_to_enjeu),

        # === Step 6: Make id_olt non-nullable + unique ===
        migrations.AlterField(
            model_name='etatactuel',
            name='id_olt',
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='etat_actuel',
                db_column='id_olt',
                to='plans.objectiflongterme',
                verbose_name='Objectif à long terme',
            ),
        ),

        # === Step 7: Remove old FK columns ===
        migrations.RemoveField(
            model_name='objectiflongterme',
            name='id_etat',
        ),
        migrations.RemoveField(
            model_name='etatactuel',
            name='id_enjeu',
        ),

        # === Step 8: Update table comments ===
        migrations.AlterModelOptions(
            name='etatactuel',
            options={
                'ordering': ['libelle'],
                'verbose_name': 'État actuel',
                'verbose_name_plural': 'États actuels',
            },
        ),
        migrations.AlterModelTableComment(
            name='etatactuel',
            table_comment='États actuels des objectifs à long terme (1:1)',
        ),
        migrations.AlterModelTableComment(
            name='objectiflongterme',
            table_comment="Objectifs à long terme des enjeux",
        ),
    ]
