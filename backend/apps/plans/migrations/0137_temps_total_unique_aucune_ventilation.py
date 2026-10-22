"""
#759 — « aucune ventilation » : un seul « Temps de travail total » par année.

Les actions ni ventilées ni déclinées par poste pouvaient porter plusieurs lots
de temps sans cible (agent + partenaire / bénévole). Ils sont fusionnés en une
seule ligne financée, au prévisionnel comme au réalisé ; le réalisé reste
rattaché à la ligne prévue gardée. Les lignes visant un poste ou un organisme
ne sont pas touchées.

Irréversible au sens des données (la répartition agent / partenaire de ces
lots n'est pas conservée) ; le retour arrière ne fait rien.
"""

from django.db import migrations


def fusionner(apps, schema_editor):
    from apps.plans.rh_total import est_temps_total_unique, fusionner_annee

    Operation = apps.get_model('plans', 'Operation')
    OperationAnnee = apps.get_model('plans', 'OperationAnnee')
    for op in Operation.objects.filter(ventilation_mode='none').iterator():
        if not est_temps_total_unique(op):
            continue
        # Gestionnaire de base du modèle historique : ligne de la période
        # (#735, sans année) comprise.
        for annee in OperationAnnee.objects.filter(id_operation=op):
            fusionner_annee(annee)


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0136_documents_uuid_public'),
    ]

    operations = [
        migrations.RunPython(fusionner, migrations.RunPython.noop),
    ]
