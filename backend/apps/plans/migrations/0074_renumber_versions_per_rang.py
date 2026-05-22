"""
Data migration — Versions scopées au rang.

Contexte : avant cette migration, la version `version` était calculée comme
max(versions de la chaîne) + 1, sans tenir compte du rang. Un changement de
rang gardait donc une numérotation continue (v3, v4...). Or sémantiquement
un changement de rang = un NOUVEAU plan de gestion → la version doit
repartir à v1.

Cette migration parcourt chaque chaîne racine (plan sans `plan_parent`),
puis renumérote les versions par rang :
- Pour chaque rang, ordonne les plans par date_ajout
- Attribue v1, v2, v3... séquentiellement
"""
from django.db import migrations


def renumber_versions_per_rang(apps, schema_editor):
    PlanGestion = apps.get_model('plans', 'PlanGestion')

    # Récupère toutes les racines (plans sans parent)
    roots = PlanGestion.objects.filter(plan_parent__isnull=True)

    visited = set()

    def collect_chain(root):
        """Retourne tous les plans de la chaîne d'un root (BFS)."""
        result = []
        queue = [root]
        local_visited = set()
        while queue:
            current = queue.pop(0)
            if current.pk in local_visited:
                continue
            local_visited.add(current.pk)
            result.append(current)
            for child in PlanGestion.objects.filter(plan_parent_id=current.pk).order_by('date_ajout'):
                queue.append(child)
        return result

    for root in roots:
        if root.pk in visited:
            continue
        chain = collect_chain(root)
        visited.update(p.pk for p in chain)

        # Grouper par rang
        by_rang = {}
        for plan in chain:
            r = plan.rang or 1
            by_rang.setdefault(r, []).append(plan)

        # Pour chaque rang, trier par date_ajout et renuméroter à partir de 1
        for r, plans_in_rang in by_rang.items():
            plans_in_rang.sort(key=lambda p: p.date_ajout or p.pk)
            for idx, plan in enumerate(plans_in_rang, start=1):
                new_version = str(idx)
                if plan.version != new_version:
                    plan.version = new_version
                    plan.save(update_fields=['version'])


def noop_reverse(apps, schema_editor):
    """Pas de reverse : on ne peut pas reconstruire les anciennes versions."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0073_is_mi_parcours_as_attribute"),
    ]

    operations = [
        migrations.RunPython(renumber_versions_per_rang, noop_reverse),
    ]
