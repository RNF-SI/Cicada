"""
Data migration #250 (suite retour de test) — Suppression du statut `etendu`.

Contexte : l'extension de durée d'un plan n'est pas un statut à part entière
mais un attribut indépendant (colonne `annees_extension`). Un plan peut être
`valide`, `modifie`, `mi_parcours` ou `en_revision` ET étendu en même temps.
La présence de `etendu` dans STATUT_CHOICES créait une ambiguïté (le plan
perdait son statut de base) et débloquait à tort l'édition d'un plan validé.

Cette migration :
  1. Repasse à `valide` tous les plans actuellement en `statut='etendu'`
     (en conservant `annees_extension` qui reste l'indicateur d'extension).
  2. Retire `etendu` des choices du champ `statut`.
"""
import django.core.validators
from django.db import migrations, models


def remove_etendu_status(apps, schema_editor):
    PlanGestion = apps.get_model('plans', 'PlanGestion')
    PlanGestion.objects.filter(statut='etendu').update(statut='valide')


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0070_backfill_operation_statut_valide"),
    ]

    operations = [
        migrations.RunPython(
            remove_etendu_status,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="plangestion",
            name="statut",
            field=models.CharField(
                choices=[
                    ("draft", "Brouillon"),
                    ("avis_csrpn", "Avis CSRPN demandé"),
                    ("comite_consultatif", "Validation comité consultatif"),
                    ("arrete_pref", "Arrêté préfectoral"),
                    ("valide", "Validé"),
                    ("modifie", "Modifié"),
                    ("mi_parcours", "Modifié à mi-parcours"),
                    ("en_revision", "En cours de révision"),
                    ("archive", "Archivé"),
                ],
                default="draft",
                max_length=20,
                verbose_name="Statut",
            ),
        ),
        migrations.AlterField(
            model_name="plangestion",
            name="annees_extension",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Nombre d'années ajoutées au plan. 0, 1 ou 2.",
                validators=[django.core.validators.MaxValueValidator(2)],
                verbose_name="Années d'extension",
            ),
        ),
    ]
