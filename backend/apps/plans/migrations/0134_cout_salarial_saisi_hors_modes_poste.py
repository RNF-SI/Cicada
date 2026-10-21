"""
#735 (retour 21/10) — la « déclinaison par type de coût » décline désormais le
temps de travail par poste dans TOUS les modes, et y propose le coût salarial
calculé automatiquement (jours × coût jour).

Jusqu'ici, hors modes « + type de poste », le coût salarial d'une action
détaillée était toujours SAISI, quelle que soit la valeur (True par défaut) de
`cout_salarial_auto`. Sans cette migration, ces actions basculeraient en calcul
automatique : leur coût salarial saisi disparaîtrait des totaux (et leur temps,
sans poste, vaudrait 0 €). On les fige donc en « coût salarial saisi », au
prévisionnel comme au réalisé — totaux inchangés.
"""

from django.db import migrations

POSTE_MODES = ("by_type_poste", "by_org_type_poste")


def figer_cout_salarial_saisi(apps, schema_editor):
    Operation = apps.get_model("plans", "Operation")
    Globale = apps.get_model("plans", "OperationRealisationGlobale")

    hors_poste = Operation.objects.exclude(ventilation_mode__in=POSTE_MODES)
    # Prévisionnel détaillé : le salarial était saisi.
    hors_poste.filter(declinaison_par_type_cout=True, cout_salarial_auto=True).update(
        cout_salarial_auto=False)
    # Réalisé détaillé par le seul suivi (#741) : idem.
    Globale.objects.filter(
        id_operation__in=hors_poste,
        declinaison_par_type_cout_realise=True,
    ).exclude(cout_salarial_auto_realise=False).update(cout_salarial_auto_realise=False)


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0133_corredacteurplan_principal"),
    ]

    operations = [
        migrations.RunPython(figer_cout_salarial_saisi, migrations.RunPython.noop),
    ]
