"""#739 — rédacteur principal d'un plan parmi ses organismes rédacteurs."""
from django.db import migrations, models


def marquer_principal(apps, schema_editor):
    """Principal = le plus ancien organisme rédacteur qui n'est pas celui d'un
    rédacteur externe rattaché au plan. Aucun s'ils le sont tous : le référent
    le choisira dans la fiche du plan."""
    CorRedacteurPlan = apps.get_model('plans', 'CorRedacteurPlan')
    Role = apps.get_model('users', 'Role')
    plans = CorRedacteurPlan.objects.values_list('plan_de_gestion_id', flat=True).distinct()
    for plan_id in plans:
        externes = set(
            Role.objects.filter(role_level='redacteur')
            .filter(models.Q(plan_associations__plan_de_gestion_id=plan_id)
                    | models.Q(plans_referents__pk=plan_id))
            .values_list('id_organisme__uuid_organisme', flat=True)
        )
        candidat = (CorRedacteurPlan.objects.filter(plan_de_gestion_id=plan_id)
                    .exclude(uuid_og_id__in=[u for u in externes if u])
                    .order_by('date_association', 'pk').first())
        if candidat:
            candidat.principal = True
            candidat.save(update_fields=['principal'])


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0132_realisation_reglages_suivi'),
        ('users', '0012_role_usershub_id_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='corredacteurplan',
            name='principal',
            field=models.BooleanField(default=False, verbose_name='Rédacteur principal'),
        ),
        migrations.AlterModelOptions(
            name='corredacteurplan',
            options={'ordering': ['-principal', 'date_association', 'pk'],
                     'verbose_name': 'Organisme rédacteur - Plan',
                     'verbose_name_plural': 'Organismes rédacteurs - Plans'},
        ),
        migrations.RunPython(marquer_principal, migrations.RunPython.noop),
    ]
