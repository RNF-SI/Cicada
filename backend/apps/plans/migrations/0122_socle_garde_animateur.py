"""
#632 — Fonctions oubliées du socle.

- Ajout de « Garde animateur », qui manquait alors que le poste combiné
  garde + animateur est courant en réserve.
- Retrait de la fonction « test », créée par erreur en recette et visible de
  tous les plans. Elle n'est supprimée que si aucun poste ne l'utilise ;
  sinon elle est désactivée, pour ne casser aucune donnée saisie.
"""
from django.db import migrations


GARDE_ANIMATEUR = "Garde animateur"


def ajouter_garde_animateur(apps, schema_editor):
    Fonction = apps.get_model("plans", "Fonction")
    Fonction.objects.update_or_create(
        libelle=GARDE_ANIMATEUR,
        id_pg=None,
        defaults={
            "type_poste": "salarie",
            "finance_par_defaut": True,
            "is_socle": True,
            "actif": True,
        },
    )


def retirer_garde_animateur(apps, schema_editor):
    Fonction = apps.get_model("plans", "Fonction")
    Fonction.objects.filter(
        libelle=GARDE_ANIMATEUR, id_pg__isnull=True, is_socle=True
    ).delete()


def retirer_fonction_test(apps, schema_editor):
    Fonction = apps.get_model("plans", "Fonction")
    PosteFonction = apps.get_model("plans", "PosteFonction")

    for fonction in Fonction.objects.filter(libelle__iexact="test"):
        if PosteFonction.objects.filter(id_fonction=fonction).exists():
            fonction.actif = False
            fonction.save(update_fields=["actif"])
        else:
            fonction.delete()


class Migration(migrations.Migration):
    dependencies = [
        ("plans", "0121_poste_nom_local_commentaire"),
    ]

    operations = [
        migrations.RunPython(ajouter_garde_animateur, retirer_garde_animateur),
        # Retour arrière : on ne recrée pas une fonction créée par erreur.
        migrations.RunPython(retirer_fonction_test, migrations.RunPython.noop),
    ]
