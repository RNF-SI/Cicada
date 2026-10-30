"""#789 — un référent du plan a toujours sa ligne membre, et inversement.

Un utilisateur était référent d'un plan par ``PlanGestion.referents`` ou par
``CorRolePlan(referent=True)`` ; plusieurs chemins n'écrivaient que l'un des deux,
et le retrait depuis « Gérer les utilisateurs du plan » échouait. Les signaux
tiennent désormais les deux ensemble ; on réaligne ici l'existant : est référent
qui l'est dans l'une OU l'autre écriture.
"""

from django.db import migrations


def aligner_referents(apps, schema_editor):
    PlanGestion = apps.get_model('plans', 'PlanGestion')
    CorRolePlan = apps.get_model('plans', 'CorRolePlan')
    Liaison = PlanGestion.referents.through

    par_relation = set(Liaison.objects.values_list('plangestion_id', 'role_id'))
    lignes = {(p, r): ref for p, r, ref in
              CorRolePlan.objects.values_list('plan_de_gestion_id', 'id_role_id', 'referent')}

    manquantes = [CorRolePlan(plan_de_gestion_id=p, id_role_id=r, referent=True)
                  for p, r in par_relation if (p, r) not in lignes]
    CorRolePlan.objects.bulk_create(manquantes, ignore_conflicts=True)
    for p, r in par_relation:
        if lignes.get((p, r)) is False:
            CorRolePlan.objects.filter(plan_de_gestion_id=p, id_role_id=r).update(referent=True)

    Liaison.objects.bulk_create(
        [Liaison(plangestion_id=p, role_id=r)
         for (p, r), ref in lignes.items() if ref and (p, r) not in par_relation],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0143_libelle_action_sans_code_type'),
    ]

    operations = [
        migrations.RunPython(aligner_referents, migrations.RunPython.noop),
    ]
