"""
Restructuration EtatActuel / ObjectifLongTerme.

Avant : Enjeu → OLT (FK id_enjeu) → EtatActuel (1:1 id_olt)
Après : Enjeu → EtatActuel (FK id_enjeu) → OLT (FK id_etat_actuel)
"""
from django.db import migrations, models
import django.db.models.deletion


def migrate_data_forward(apps, schema_editor):
    """
    Migrer les données de l'ancien modèle vers le nouveau.
    Pour chaque EtatActuel existant :
      - Récupérer l'enjeu via son OLT (etat.id_olt.id_enjeu)
      - Remplir le nouveau champ id_enjeu
    Pour chaque OLT existant :
      - Si un EtatActuel pointait vers cet OLT, remplir id_etat_actuel
    """
    EtatActuel = apps.get_model('plans', 'EtatActuel')
    ObjectifLongTerme = apps.get_model('plans', 'ObjectifLongTerme')

    # Step 1: For each EtatActuel, set id_enjeu from its OLT's enjeu
    for etat in EtatActuel.objects.select_related('id_olt').all():
        if etat.id_olt_id:
            olt = ObjectifLongTerme.objects.get(pk=etat.id_olt_id)
            etat.id_enjeu_id = olt.id_enjeu_id
            etat.save(update_fields=['id_enjeu_id'])

    # Step 2: For each OLT, find its EtatActuel and set id_etat_actuel
    for olt in ObjectifLongTerme.objects.all():
        try:
            etat = EtatActuel.objects.get(id_olt_id=olt.pk)
            olt.id_etat_actuel_id = etat.pk
            olt.save(update_fields=['id_etat_actuel_id'])
        except EtatActuel.DoesNotExist:
            # OLT without EtatActuel - we need to create one
            # so the OLT has a valid parent
            etat = EtatActuel.objects.create(
                id_enjeu_id=olt.id_enjeu_id,
                id_olt_id=olt.pk,
                libelle=f"État actuel de {olt.libelle}",
                description="",
                id_utilisateur_ajout_id=olt.id_utilisateur_ajout_id,
                id_utilisateur_maj_id=olt.id_utilisateur_maj_id,
            )
            olt.id_etat_actuel_id = etat.pk
            olt.save(update_fields=['id_etat_actuel_id'])


def migrate_data_backward(apps, schema_editor):
    """Reverse: set id_olt on EtatActuel and id_enjeu on OLT."""
    EtatActuel = apps.get_model('plans', 'EtatActuel')
    ObjectifLongTerme = apps.get_model('plans', 'ObjectifLongTerme')

    for olt in ObjectifLongTerme.objects.select_related('id_etat_actuel').all():
        if olt.id_etat_actuel_id:
            etat = EtatActuel.objects.get(pk=olt.id_etat_actuel_id)
            etat.id_olt_id = olt.pk
            etat.save(update_fields=['id_olt_id'])
            olt.id_enjeu_id = etat.id_enjeu_id
            olt.save(update_fields=['id_enjeu_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0028_remove_suiviinventaire_annee_lancement_suivi_and_more'),
    ]

    operations = [
        # Step 1: Add new nullable fields
        migrations.AddField(
            model_name='etatactuel',
            name='id_enjeu',
            field=models.ForeignKey(
                blank=True,
                null=True,
                db_column='id_enjeu',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='etats_actuels',
                to='plans.enjeu',
                verbose_name='Enjeu',
            ),
        ),
        migrations.AddField(
            model_name='objectiflongterme',
            name='id_etat_actuel',
            field=models.ForeignKey(
                blank=True,
                null=True,
                db_column='id_etat_actuel',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='objectifs_long_terme',
                to='plans.etatactuel',
                verbose_name='État actuel',
            ),
        ),

        # Step 2: Migrate data
        migrations.RunPython(migrate_data_forward, migrate_data_backward),

        # Step 3: Remove old fields
        migrations.RemoveField(
            model_name='etatactuel',
            name='id_olt',
        ),
        migrations.RemoveField(
            model_name='objectiflongterme',
            name='id_enjeu',
        ),

        # Step 4: Make new fields non-nullable
        migrations.AlterField(
            model_name='etatactuel',
            name='id_enjeu',
            field=models.ForeignKey(
                db_column='id_enjeu',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='etats_actuels',
                to='plans.enjeu',
                verbose_name='Enjeu',
            ),
        ),
        migrations.AlterField(
            model_name='objectiflongterme',
            name='id_etat_actuel',
            field=models.ForeignKey(
                db_column='id_etat_actuel',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='objectifs_long_terme',
                to='plans.etatactuel',
                verbose_name='État actuel',
            ),
        ),
    ]
