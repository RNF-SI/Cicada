"""
#622 — Retrait du « prestataire » des types de poste proposés.

Un prestataire n'a pas de coût jour : on ne lui associe donc pas de temps de
travail dans la programmation, et le garder parmi les types de poste ajoutait
de la confusion. Son coût continue de se saisir là où il a du sens — la ligne
« Coût prestataire » du budget de l'action, en saisie comme en suivi — qui
n'est pas touchée ici.

La fonction socle « Prestataire » est **désactivée**, pas supprimée : les
postes qui la portent déjà restent valides et éditables (le formulaire
réinjecte la fonction inactive dans sa liste). Le type reste également
disponible en base pour ces données historiques.
"""
from django.db import migrations


def desactiver_fonction_prestataire(apps, schema_editor):
    Fonction = apps.get_model("plans", "Fonction")
    Fonction.objects.filter(type_poste="prestataire", actif=True).update(actif=False)


def reactiver_fonction_prestataire(apps, schema_editor):
    Fonction = apps.get_model("plans", "Fonction")
    Fonction.objects.filter(type_poste="prestataire", is_socle=True).update(actif=True)


class Migration(migrations.Migration):

    dependencies = [
        ("plans", "0118_operationannee_autre_cout_and_more"),
    ]

    operations = [
        migrations.RunPython(
            desactiver_fonction_prestataire, reactiver_fonction_prestataire
        ),
    ]
