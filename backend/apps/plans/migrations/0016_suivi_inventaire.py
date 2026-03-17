# Migration: Move 12 suivi fields from Operation to new SuiviInventaire model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_operation_suivi_data(apps, schema_editor):
    """
    For each Operation that has data in any of the 12 suivi fields,
    create a SuiviInventaire and link it.
    """
    Operation = apps.get_model('plans', 'Operation')
    SuiviInventaire = apps.get_model('plans', 'SuiviInventaire')

    for op in Operation.objects.all():
        has_data = any([
            op.objectif_principal,
            op.cibles_principales,
            op.taxon_taxref,
            op.annee_lancement_suivi is not None,
            op.protocole_dans_campanule is not None,
            op.protocole_campanule_nom,
            op.respect_protocole is not None,
            op.justification_non_respect,
            op.differences_protocole,
            op.outil_bancarisation,
            op.outil_saisie,
            op.transmission_donnee is not None,
        ])
        if has_data:
            suivi = SuiviInventaire.objects.create(
                objectif_principal=op.objectif_principal or '',
                cibles_principales=op.cibles_principales or '',
                taxon_taxref=op.taxon_taxref or '',
                annee_lancement_suivi=op.annee_lancement_suivi,
                protocole_dans_campanule=op.protocole_dans_campanule,
                protocole_campanule_nom=op.protocole_campanule_nom or '',
                respect_protocole=op.respect_protocole,
                justification_non_respect=op.justification_non_respect or '',
                differences_protocole=op.differences_protocole or '',
                outil_bancarisation=op.outil_bancarisation or '',
                outil_saisie=op.outil_saisie or '',
                transmission_donnee=op.transmission_donnee,
                id_utilisateur_ajout=op.id_utilisateur_ajout,
            )
            op.id_suivi = suivi
            op.save(update_fields=['id_suivi'])


def reverse_migrate_suivi_data(apps, schema_editor):
    """Reverse: copy SuiviInventaire data back to Operation fields."""
    Operation = apps.get_model('plans', 'Operation')

    for op in Operation.objects.select_related('id_suivi').filter(id_suivi__isnull=False):
        suivi = op.id_suivi
        op.objectif_principal = suivi.objectif_principal
        op.cibles_principales = suivi.cibles_principales
        op.taxon_taxref = suivi.taxon_taxref
        op.annee_lancement_suivi = suivi.annee_lancement_suivi
        op.protocole_dans_campanule = suivi.protocole_dans_campanule
        op.protocole_campanule_nom = suivi.protocole_campanule_nom
        op.respect_protocole = suivi.respect_protocole
        op.justification_non_respect = suivi.justification_non_respect
        op.differences_protocole = suivi.differences_protocole
        op.outil_bancarisation = suivi.outil_bancarisation
        op.outil_saisie = suivi.outil_saisie
        op.transmission_donnee = suivi.transmission_donnee
        op.save()


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0015_operation_programmation_mode"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Create SuiviInventaire table
        migrations.CreateModel(
            name="SuiviInventaire",
            fields=[
                (
                    "id_suivi_inventaire",
                    models.AutoField(primary_key=True, serialize=False),
                ),
                (
                    "objectif_principal",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Objectif principal de l'action",
                        verbose_name="Objectif principal",
                    ),
                ),
                (
                    "cibles_principales",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Cible(s) principale(s) (Flore, Faune, Habitat, etc.)",
                        max_length=255,
                        verbose_name="Cible(s) principale(s)",
                    ),
                ),
                (
                    "taxon_taxref",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Référence taxon dans Taxref",
                        max_length=255,
                        verbose_name="Taxon - Taxref",
                    ),
                ),
                (
                    "annee_lancement_suivi",
                    models.IntegerField(
                        blank=True,
                        help_text="Année de lancement du suivi (si antérieur)",
                        null=True,
                        verbose_name="Année de lancement du suivi",
                    ),
                ),
                (
                    "protocole_dans_campanule",
                    models.BooleanField(
                        blank=True,
                        help_text="Le protocole est-il répertorié dans Campanule ?",
                        null=True,
                        verbose_name="Protocole répertorié dans Campanule",
                    ),
                ),
                (
                    "protocole_campanule_nom",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Nom du protocole dans Campanule",
                        max_length=255,
                        verbose_name="Protocole (Campanule)",
                    ),
                ),
                (
                    "respect_protocole",
                    models.BooleanField(
                        blank=True,
                        help_text="Respectez-vous strictement le protocole ?",
                        null=True,
                        verbose_name="Respect strict du protocole",
                    ),
                ),
                (
                    "justification_non_respect",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Pourquoi ne respectez-vous pas le protocole ?",
                        verbose_name="Justification non-respect",
                    ),
                ),
                (
                    "differences_protocole",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Quelques différences avec le protocole ?",
                        verbose_name="Différences avec le protocole",
                    ),
                ),
                (
                    "outil_bancarisation",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Outil de bancarisation utilisé",
                        max_length=255,
                        verbose_name="Outil de bancarisation",
                    ),
                ),
                (
                    "outil_saisie",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Existe t-il un outil de saisie ?",
                        max_length=255,
                        verbose_name="Outil de saisie",
                    ),
                ),
                (
                    "transmission_donnee",
                    models.BooleanField(
                        blank=True,
                        help_text="Transmission de la donnée à l'organisme porteur ?",
                        null=True,
                        verbose_name="Transmission de la donnée",
                    ),
                ),
                (
                    "date_ajout",
                    models.DateTimeField(
                        auto_now_add=True, verbose_name="Date d'ajout"
                    ),
                ),
                (
                    "date_maj",
                    models.DateTimeField(
                        auto_now=True, verbose_name="Date de modification"
                    ),
                ),
                (
                    "id_utilisateur_ajout",
                    models.ForeignKey(
                        db_column="id_utilisateur_ajout",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Créateur",
                    ),
                ),
                (
                    "id_utilisateur_maj",
                    models.ForeignKey(
                        blank=True,
                        db_column="id_utilisateur_maj",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="+",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Dernier modificateur",
                    ),
                ),
            ],
            options={
                "verbose_name": "Suivi / Inventaire",
                "verbose_name_plural": "Suivis / Inventaires",
                "db_table": '"general"."t_suivi_inventaires"',
                "db_table_comment": "Suivis et inventaires associés aux opérations",
            },
        ),
        # Step 2: Add new fields to Operation (before removing old ones)
        migrations.AddField(
            model_name="operation",
            name="est_suivi_existant",
            field=models.BooleanField(
                default=False,
                help_text="Inventaire ou suivi déjà saisi dans le module Mes inventaires et suivis ?",
                verbose_name="Inventaire ou suivi existant",
            ),
        ),
        migrations.AddField(
            model_name="operation",
            name="id_suivi",
            field=models.ForeignKey(
                blank=True,
                db_column="id_suivi",
                help_text="Suivi ou inventaire associé à cette opération",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="operations",
                to="plans.suiviinventaire",
                verbose_name="Suivi / Inventaire lié",
            ),
        ),
        # Step 3: Migrate existing data
        migrations.RunPython(
            migrate_operation_suivi_data,
            reverse_migrate_suivi_data,
        ),
        # Step 4: Remove old fields from Operation
        migrations.RemoveField(model_name="operation", name="objectif_principal"),
        migrations.RemoveField(model_name="operation", name="cibles_principales"),
        migrations.RemoveField(model_name="operation", name="taxon_taxref"),
        migrations.RemoveField(model_name="operation", name="annee_lancement_suivi"),
        migrations.RemoveField(model_name="operation", name="protocole_dans_campanule"),
        migrations.RemoveField(model_name="operation", name="protocole_campanule_nom"),
        migrations.RemoveField(model_name="operation", name="respect_protocole"),
        migrations.RemoveField(model_name="operation", name="justification_non_respect"),
        migrations.RemoveField(model_name="operation", name="differences_protocole"),
        migrations.RemoveField(model_name="operation", name="outil_bancarisation"),
        migrations.RemoveField(model_name="operation", name="outil_saisie"),
        migrations.RemoveField(model_name="operation", name="transmission_donnee"),
        # Step 5: AlterField that changed
        migrations.AlterField(
            model_name="operation",
            name="programmation_mensuelle_defaut",
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Template mensuel appliqué à toutes les années en mode récurrent. Format: {"1": true, "2": false, ..., "12": true}',
                verbose_name="Programmation mensuelle par défaut",
            ),
        ),
    ]
