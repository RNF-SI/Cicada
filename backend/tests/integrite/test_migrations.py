"""Filet « perte de données » — famille G : migrations qui détruisent ou ne reviennent pas.

Une migration qui supprime un champ ou une table, ou qui transforme des données
sans retour, perd de l'information au déploiement : on ne revient en arrière
qu'en restaurant la sauvegarde prise juste avant (#796). Chacune doit donc avoir
été vue. Elles sont consignées dans ``migrations_irreversibles.txt`` ; une
nouvelle fait échouer ce test tant qu'elle n'y a pas été ajoutée, avec ce
qu'elle perd et pourquoi c'est acceptable.
"""
from pathlib import Path

from django.db import migrations
from django.db.migrations.loader import MigrationLoader

FICHIER = Path(__file__).with_name('migrations_irreversibles.txt')


def _operations_destructrices(migration):
    for operation in migration.operations:
        if isinstance(operation, migrations.RunPython) and operation.reverse_code is None:
            yield 'RunPython sans retour'
        elif isinstance(operation, migrations.RunPython) and \
                operation.reverse_code is migrations.RunPython.noop:
            yield 'RunPython au retour vide'
        elif isinstance(operation, migrations.RunSQL) and operation.reverse_sql in (
                None, migrations.RunSQL.noop):
            yield 'RunSQL sans retour'
        elif isinstance(operation, migrations.RemoveField):
            yield f'RemoveField {operation.model_name}.{operation.name}'
        elif isinstance(operation, migrations.DeleteModel):
            yield f'DeleteModel {operation.name}'


def destructrices_actuelles():
    loader = MigrationLoader(None, ignore_no_migrations=True)
    lignes = set()
    for (app, nom), migration in loader.disk_migrations.items():
        if not migration.__module__.startswith('apps.'):
            continue
        for operation in _operations_destructrices(migration):
            lignes.add(f'{app}.{nom} : {operation}')
    return lignes


def relues():
    return {
        ligne.split('#', 1)[0].strip()
        for ligne in FICHIER.read_text(encoding='utf-8').splitlines()
        if ligne.split('#', 1)[0].strip()
    }


def test_toute_migration_destructrice_a_ete_relue():
    nouvelles = sorted(destructrices_actuelles() - relues())
    assert not nouvelles, (
        "Migration qui supprime ou transforme sans retour : écrire son retour "
        "(reverse_code / reverse_sql), ou l'ajouter à "
        f"{FICHIER.name} avec ce qu'elle perd :\n" + "\n".join(nouvelles))
