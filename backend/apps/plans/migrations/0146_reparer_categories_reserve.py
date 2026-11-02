"""
#788 — Réparation automatique des catégories d'action réserve (CT88) sur une
instance où un passage Gestref a été appliqué avant la correction.

Une migration plutôt qu'un geste d'exploitant : la mise à jour se fait par le
bouton, sans commande ni SQL, et une migration s'exécute **une seule fois** par
instance — relancer la réparation à chaque démarrage écraserait une catégorie
choisie depuis par un référent. Sur une instance qui n'a jamais appliqué de
passage, rien n'est modifié (``apps/plans/categories_reserve.py``).

Les actions corrigées n'ont pas été réindexées (pas de signal dans une
migration) : l'index de recherche est alors marqué périmé, et
``rebuild_search_index --if-stale``, lancé au démarrage juste après
``migrate``, le reconstruit.
"""
from django.db import migrations


def reparer(apps, schema_editor):
    from apps.plans.categories_reserve import reparer as reparer_categories

    modeles = {
        'Nomenclature': apps.get_model('core', 'Nomenclature'),
        'Operation': apps.get_model('plans', 'Operation'),
        'PassageReferentielObjet': apps.get_model('plans', 'PassageReferentielObjet'),
        'VersionReferentielActions': apps.get_model('plans', 'VersionReferentielActions'),
    }
    rapport = reparer_categories(appliquer=True, modeles=modeles)
    if rapport['actions_corrigees']:
        ContenuIndexe = apps.get_model('search', 'ContenuIndexe')
        ContenuIndexe.objects.update(index_version=0)


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0145_financeurs_du_plan'),
        ('core', '0020_alter_activitylog_entity_type'),
        ('search', '0011_codes_referentiel'),
    ]

    operations = [
        migrations.RunPython(reparer, migrations.RunPython.noop),
    ]
