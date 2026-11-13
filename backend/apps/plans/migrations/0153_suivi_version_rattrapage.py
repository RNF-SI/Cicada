"""#803 — Rattrapage : un seul suivi par rang.

Les versions d'un même rang créées avant #803 ont chacune leur suivi, sans
lien entre une action et sa copie. On apparie les objets de chaque version
avec ceux de la précédente (code et libellé des actions, nom des indicateurs,
métriques et postes), puis on fait suivre le suivi jusqu'à la dernière version
validée du rang — la saisie déjà faite sur une version plus récente prime.

Sans retour : le suivi déplacé reste sur la version qui le porte (rien n'est
perdu, et le défaire mélangerait les saisies faites depuis).
"""
from django.db import migrations


def rattraper(apps, schema_editor):
    from apps.plans.suivi_version import rattraper as appliquer
    appliquer(apps)


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0152_suivi_version_origine'),
    ]

    operations = [
        migrations.RunPython(rattraper, migrations.RunPython.noop),
    ]
