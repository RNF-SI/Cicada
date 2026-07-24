"""
#605 — Rattrapage du type de poste « partenaire ».

La fonction socle « Partenaire » avait été seedée (migration 0100) puis typée
« salarie » par défaut (migration 0110, avant l'existence du type partenaire).
On la reclasse en « partenaire », comme les prestataires : organisme saisi
librement, catégorie de dépense « bénévolat / partenariat ».
"""
from django.db import migrations


def backfill_partenaire(apps, schema_editor):
    Fonction = apps.get_model("plans", "Fonction")
    for f in Fonction.objects.all():
        libelle = (f.libelle or "").lower()
        if "partenaire" in libelle and f.type_poste == "salarie":
            f.type_poste = "partenaire"
            # Un partenaire n'est pas financé par défaut (cohérent socle).
            f.finance_par_defaut = False
            f.save(update_fields=["type_poste", "finance_par_defaut"])


def noop(apps, schema_editor):
    # Reversible : on ne rebascule pas en « salarie » pour ne pas écraser un
    # éventuel reclassement manuel.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0115_realisationoperationanneeorganisme_autre_cout_commentaire_realise_and_more"),
    ]

    operations = [
        migrations.RunPython(backfill_partenaire, noop),
    ]
