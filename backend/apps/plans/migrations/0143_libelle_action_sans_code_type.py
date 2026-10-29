"""#784 — intitulé d'action repris du type d'action : sans son code.

Le formulaire enregistrait « <code> - <libellé du type> » quand aucun
intitulé n'était saisi ; il enregistre désormais le seul libellé. Les actions
existantes dont l'intitulé est exactement ce motif, pour un type d'action
(actuel ou ancien référentiel), reprennent le libellé seul. Un intitulé saisi
à la main n'est jamais touché.
"""

from django.db import migrations


def retirer_code(apps, schema_editor):
    Nomenclature = apps.get_model('core', 'Nomenclature')
    Operation = apps.get_model('plans', 'Operation')

    motifs = {}
    for code, mnemonique, label in (Nomenclature.objects
                                    .filter(id_type__mnemonique='TYPE_ACTION')
                                    .values_list('cd_nomenclature', 'mnemonique', 'label')):
        if not label:
            continue
        for c in {code, mnemonique} - {None, ''}:
            motifs[f"{c} - {label}"] = label
    if not motifs:
        return
    for op in Operation.objects.filter(libelle__in=list(motifs)).only('pk', 'libelle'):
        Operation.objects.filter(pk=op.pk).update(libelle=motifs[op.libelle])


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0142_referentiels_generiques'),
    ]

    operations = [
        # Sens inverse sans objet : on ne sait plus quel intitulé était automatique.
        migrations.RunPython(retirer_code, migrations.RunPython.noop),
    ]
