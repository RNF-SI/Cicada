"""
#560 — Rattache les lignes RH réalisées à la ligne prévisionnelle qu'elles
réalisent (`RealisationOperationAnneeRH.id_operation_annee_rh`).

Les lignes créées par la migration 0100 (conversion de etp / etp_realise) n'ont
pas ce lien : sans backfill, chaque temps réalisé hérité remonterait dans la
page de suivi comme « réalisé non prévu », à côté d'un prévisionnel affiché
comme non réalisé.

Rapprochement conservateur : on ne relie que lorsqu'une **unique** ligne
prévisionnelle de la même année partage (personne, fonction, financé) — ce qui
est le cas des données converties, toutes en « fonction non précisée, financé ».
En cas d'ambiguïté (plusieurs candidats), on laisse le lien vide plutôt que de
risquer un rapprochement arbitraire.
"""
from django.db import migrations


def backfill(apps, schema_editor):
    RealisationOperationAnneeRH = apps.get_model('plans', 'RealisationOperationAnneeRH')

    lignes = (
        RealisationOperationAnneeRH.objects
        .filter(id_operation_annee_rh__isnull=True)
        .select_related('id_realisation_operation_annee__id_operation_annee')
    )
    for ligne in lignes:
        operation_annee = ligne.id_realisation_operation_annee.id_operation_annee
        candidats = list(
            operation_annee.rh_lignes.filter(
                id_personne_plan=ligne.id_personne_plan_id,
                id_fonction=ligne.id_fonction_id,
                finance=ligne.finance,
            )[:2]
        )
        if len(candidats) == 1:
            ligne.id_operation_annee_rh = candidats[0]
            ligne.save(update_fields=['id_operation_annee_rh'])


def unbackfill(apps, schema_editor):
    """Le lien est purement dérivé : on peut le retirer sans perte."""
    RealisationOperationAnneeRH = apps.get_model('plans', 'RealisationOperationAnneeRH')
    RealisationOperationAnneeRH.objects.update(id_operation_annee_rh=None)


class Migration(migrations.Migration):

    dependencies = [
        ('plans', '0102_realisationoperationanneerh_id_operation_annee_rh'),
    ]

    operations = [
        migrations.RunPython(backfill, unbackfill),
    ]
