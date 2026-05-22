"""
Data migration #278 (suite retour de test) — `en_revision` devient un attribut
orthogonal au statut.

Contexte : « en cours de révision » ne signifie pas que le plan est dans un
état différent de « validé ». Un plan reste fonctionnellement validé pendant
sa révision (la révision peut même commencer avant que `annee_fin` ne soit
atteint). Garder `en_revision` comme statut faisait perdre cette information
dans l'UI.

Cette migration :
  1. Ajoute les colonnes `en_revision` (bool) et `next_rang_plan_id` (FK self).
  2. Repasse tous les plans `statut='en_revision'` vers `statut='valide',
     en_revision=True`.
  3. Pour chaque plan converti, tente de pré-renseigner `next_rang_plan` avec
     l'enfant direct dont `rang > self.rang` (cohérent avec la chaîne
     plan_parent existante).
  4. Retire `en_revision` des choices du champ `statut`.
"""
from django.db import migrations, models


def convert_en_revision_to_attribute(apps, schema_editor):
    PlanGestion = apps.get_model('plans', 'PlanGestion')
    qs = PlanGestion.objects.filter(statut='en_revision')
    for plan in qs:
        plan.statut = 'valide'
        plan.en_revision = True
        # Tentative d'auto-link : enfant direct du rang suivant
        if plan.rang is not None:
            next_plan = (
                PlanGestion.objects.filter(plan_parent_id=plan.pk, rang__gt=plan.rang)
                .order_by('rang', 'date_ajout')
                .first()
            )
            if next_plan:
                plan.next_rang_plan = next_plan
        plan.save(update_fields=['statut', 'en_revision', 'next_rang_plan'])


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0071_remove_etendu_statut"),
    ]

    operations = [
        migrations.AddField(
            model_name="plangestion",
            name="en_revision",
            field=models.BooleanField(
                default=False,
                help_text="Indique qu'une nouvelle version (rang suivant) est en cours de rédaction.",
                verbose_name="En cours de révision",
            ),
        ),
        migrations.AddField(
            model_name="plangestion",
            name="next_rang_plan",
            field=models.ForeignKey(
                blank=True,
                help_text="Plan correspondant au rang suivant (en cours d'élaboration).",
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="previous_rang_plans",
                to="plans.plangestion",
                verbose_name="Plan du rang suivant",
            ),
        ),
        migrations.RunPython(
            convert_en_revision_to_attribute,
            reverse_code=migrations.RunPython.noop,
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
                    ("archive", "Archivé"),
                ],
                default="draft",
                max_length=20,
                verbose_name="Statut",
            ),
        ),
    ]
