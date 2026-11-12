"""Filet « perte de données » — famille B : la carte des suppressions en cascade.

Supprimer un objet de référence (organisme, site, financeur, poste, fonction,
nomenclature…) peut effacer ou vider en silence des données saisies dans les
plans, y compris validés. Chaque chemin ``CASCADE`` / ``SET_NULL`` existant a été
relu ; il est consigné dans ``cascades_relues.txt``. Un chemin nouveau fait
échouer ce test tant qu'il n'a pas été relu et ajouté à la liste, avec la
raison pour laquelle il ne perd rien d'important (ou le garde-fou qui le borne).
"""
from pathlib import Path

from django.apps import apps
from django.db import models

FICHIER = Path(__file__).with_name('cascades_relues.txt')
APPLICATIONS = ('plans', 'users', 'core', 'notifications')
SURVEILLES = {models.CASCADE: 'CASCADE', models.SET_NULL: 'SET_NULL'}


def carte_actuelle():
    lignes = set()
    for label in APPLICATIONS:
        for modele in apps.get_app_config(label).get_models():
            for champ in modele._meta.get_fields():
                if not (champ.is_relation and champ.concrete and champ.many_to_one or
                        getattr(champ, 'one_to_one', False) and champ.concrete):
                    continue
                regle = SURVEILLES.get(champ.remote_field.on_delete)
                if regle is None:
                    continue
                lignes.add(
                    f"{modele._meta.label}.{champ.name} -> "
                    f"{champ.related_model._meta.label} : {regle}")
    return lignes


def carte_relue():
    return {
        ligne.split('#', 1)[0].strip()
        for ligne in FICHIER.read_text(encoding='utf-8').splitlines()
        if ligne.split('#', 1)[0].strip()
    }


def test_aucune_suppression_en_cascade_non_relue():
    nouvelles = sorted(carte_actuelle() - carte_relue())
    assert not nouvelles, (
        "Suppression en cascade non relue : vérifier qu'elle n'efface pas de donnée "
        "saisie (sinon PROTECT, ou refus dans la vue), puis l'ajouter à "
        f"{FICHIER.name} :\n" + "\n".join(nouvelles))


def test_la_liste_relue_ne_garde_pas_de_chemin_disparu():
    disparues = sorted(carte_relue() - carte_actuelle())
    assert not disparues, "À retirer de la liste relue :\n" + "\n".join(disparues)
