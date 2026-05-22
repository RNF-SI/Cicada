"""
Data migration #276 (suite retour de test) — `mi_parcours` devient un attribut
orthogonal au statut.

Contexte : « modifié à mi-parcours » est conceptuellement une **modification
déclarée comme l'évaluation mi-parcours du plan**. C'est la même logique que
`etendu` et `en_revision` : un drapeau qui s'ajoute à un statut de base
(`modifie`), pas un statut séparé.

Cette migration :
  1. Ajoute la colonne `is_mi_parcours` (bool, default False).
  2. Repasse tous les plans `statut='mi_parcours'` vers
     `statut='modifie', is_mi_parcours=True`.
  3. Retire `mi_parcours` des choices du champ `statut`.
"""
from django.db import migrations, models


def convert_mi_parcours_to_attribute(apps, schema_editor):
    PlanGestion = apps.get_model('plans', 'PlanGestion')
    PlanGestion.objects.filter(statut='mi_parcours').update(
        statut='modifie',
        is_mi_parcours=True,
    )


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0072_en_revision_as_attribute"),
    ]

    operations = [
        migrations.AddField(
            model_name="plangestion",
            name="is_mi_parcours",
            field=models.BooleanField(
                default=False,
                help_text=(
                    "Indique que cette version est l'évaluation à mi-parcours du plan. "
                    "Unique par chaîne."
                ),
                verbose_name="Évaluation mi-parcours",
            ),
        ),
        migrations.RunPython(
            convert_mi_parcours_to_attribute,
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
                    ("archive", "Archivé"),
                ],
                default="draft",
                max_length=20,
                verbose_name="Statut",
            ),
        ),
    ]
