# Migration: Extract protocole fields from SuiviInventaire to new Protocole model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_protocole_data(apps, schema_editor):
    """
    For each SuiviInventaire that has protocole data,
    create a Protocole and link it via id_protocole.
    """
    SuiviInventaire = apps.get_model('plans', 'SuiviInventaire')
    Protocole = apps.get_model('plans', 'Protocole')

    for suivi in SuiviInventaire.objects.all():
        has_protocole_data = any([
            suivi.protocole_dans_campanule is not None,
            suivi.protocole_campanule_nom,
            suivi.respect_protocole is not None,
            suivi.justification_non_respect,
            suivi.differences_protocole,
        ])
        if has_protocole_data:
            protocole = Protocole.objects.create(
                protocole_dans_campanule=suivi.protocole_dans_campanule,
                protocole_campanule_nom=suivi.protocole_campanule_nom or '',
                respect_protocole=suivi.respect_protocole,
                justification_non_respect=suivi.justification_non_respect or '',
                differences_protocole=suivi.differences_protocole or '',
                description_protocole='',
                objectif_protocole='',
                periode_echantillonnage='',
                id_utilisateur_ajout=suivi.id_utilisateur_ajout,
            )
            suivi.id_protocole = protocole
            suivi.save(update_fields=['id_protocole'])


def reverse_migrate_protocole_data(apps, schema_editor):
    """
    Reverse: copy Protocole data back to SuiviInventaire fields.
    """
    SuiviInventaire = apps.get_model('plans', 'SuiviInventaire')

    for suivi in SuiviInventaire.objects.select_related('id_protocole').filter(
        id_protocole__isnull=False
    ):
        protocole = suivi.id_protocole
        suivi.protocole_dans_campanule = protocole.protocole_dans_campanule
        suivi.protocole_campanule_nom = protocole.protocole_campanule_nom
        suivi.respect_protocole = protocole.respect_protocole
        suivi.justification_non_respect = protocole.justification_non_respect
        suivi.differences_protocole = protocole.differences_protocole
        suivi.save()


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0016_suivi_inventaire"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Step 1: Create Protocole table
        migrations.CreateModel(
            name="Protocole",
            fields=[
                (
                    "id_protocole",
                    models.AutoField(primary_key=True, serialize=False),
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
                    "description_protocole",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Description du protocole (depuis Campanule)",
                        verbose_name="Description du protocole",
                    ),
                ),
                (
                    "objectif_protocole",
                    models.TextField(
                        blank=True,
                        default="",
                        help_text="Détails de l'objectif du protocole",
                        verbose_name="Objectif du protocole",
                    ),
                ),
                (
                    "periode_echantillonnage",
                    models.CharField(
                        blank=True,
                        default="",
                        help_text="Période d'échantillonnage du protocole",
                        max_length=255,
                        verbose_name="Période d'échantillonnage",
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
                "verbose_name": "Protocole",
                "verbose_name_plural": "Protocoles",
                "db_table": '"general"."t_protocoles"',
                "db_table_comment": "Protocoles associés aux suivis/inventaires",
            },
        ),
        # Step 2: Add id_protocole FK on SuiviInventaire
        migrations.AddField(
            model_name="suiviinventaire",
            name="id_protocole",
            field=models.ForeignKey(
                blank=True,
                db_column="id_protocole",
                help_text="Protocole associé au suivi/inventaire",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="suivis",
                to="plans.protocole",
                verbose_name="Protocole",
            ),
        ),
        # Step 3: Migrate existing protocole data
        migrations.RunPython(
            migrate_protocole_data,
            reverse_migrate_protocole_data,
        ),
        # Step 4: Remove old protocole fields from SuiviInventaire
        migrations.RemoveField(
            model_name="suiviinventaire", name="protocole_dans_campanule"
        ),
        migrations.RemoveField(
            model_name="suiviinventaire", name="protocole_campanule_nom"
        ),
        migrations.RemoveField(
            model_name="suiviinventaire", name="respect_protocole"
        ),
        migrations.RemoveField(
            model_name="suiviinventaire", name="justification_non_respect"
        ),
        migrations.RemoveField(
            model_name="suiviinventaire", name="differences_protocole"
        ),
    ]
