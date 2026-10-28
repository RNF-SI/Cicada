"""
Déclinaison par type de poste découplée de la déclinaison par type de coût.

Jusqu'ici (#735, retour 21/10), cocher « Déclinaison par type de coût »
déclinait d'office le temps de travail par poste, dans tous les modes. Ce lien
est retiré : la fiche action a désormais sa propre case « Déclinaison par type
de poste » (`declinaison_par_poste`). Les actions existantes à coûts détaillés
gardent leur temps par poste : on pose la case pour elles. Réversible sans
retour (la règle précédente le déduisait de toute façon).
"""

from django.db import migrations

POSTE_MODES = ('by_type_poste', 'by_org_type_poste')


def poser_case(apps, schema_editor):
    Operation = apps.get_model('plans', 'Operation')
    (Operation.objects
     .filter(declinaison_par_type_cout=True, declinaison_par_poste=False)
     .exclude(ventilation_mode__in=POSTE_MODES)
     .update(declinaison_par_poste=True))


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0139_referentiel_types_action"),
    ]

    operations = [
        migrations.RunPython(poser_case, migrations.RunPython.noop),
    ]
