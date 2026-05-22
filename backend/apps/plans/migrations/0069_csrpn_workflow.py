# #277 — Workflow de validation CSRPN multi-étapes.
#
# - Rename `date_validation_cspn` → `date_avis_csrpn` (préserve les données).
# - Ajout des champs `date_validation_comite`, `date_arrete_pref`,
#   `numero_arrete_pref`.
# - Ajout des statuts `avis_csrpn`, `comite_consultatif`, `arrete_pref` aux
#   choix de `statut`.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0067_add_modifie_mi_parcours_statuses"),
        ("plans", "0068_operation_statut"),
    ]

    operations = [
        migrations.RenameField(
            model_name="plangestion",
            old_name="date_validation_cspn",
            new_name="date_avis_csrpn",
        ),
        migrations.AlterField(
            model_name="plangestion",
            name="date_avis_csrpn",
            field=models.DateField(
                blank=True,
                help_text="Date à laquelle l'avis du CSRPN a été rendu.",
                null=True,
                verbose_name="Date d'avis CSRPN",
            ),
        ),
        migrations.AddField(
            model_name="plangestion",
            name="date_validation_comite",
            field=models.DateField(
                blank=True,
                help_text="Date de validation par le comité consultatif de gestion.",
                null=True,
                verbose_name="Date de validation comité consultatif",
            ),
        ),
        migrations.AddField(
            model_name="plangestion",
            name="date_arrete_pref",
            field=models.DateField(
                blank=True,
                help_text="Date de l'arrêté préfectoral (RNN uniquement).",
                null=True,
                verbose_name="Date d'arrêté préfectoral",
            ),
        ),
        migrations.AddField(
            model_name="plangestion",
            name="numero_arrete_pref",
            field=models.CharField(
                blank=True,
                help_text="Numéro de référence de l'arrêté préfectoral.",
                max_length=100,
                null=True,
                verbose_name="Numéro d'arrêté préfectoral",
            ),
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
                    ("etendu", "Étendu"),
                    ("en_revision", "En cours de révision"),
                    ("archive", "Archivé"),
                ],
                default="draft",
                max_length=20,
                verbose_name="Statut",
            ),
        ),
    ]
