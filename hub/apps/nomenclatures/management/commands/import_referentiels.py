"""
Importe toutes les versions des référentiels livrées avec CICADA et leurs
tables de correspondance (#780) : types d'action (Eden 62, Gestref…), PressRef,
TaxRef, HabRef.

Les fichiers sont ceux de CICADA, montés en lecture seule (dev) ou copiés dans
l'image (prod) sous `apps/nomenclatures/data/` :
`referentiels_types_action/<version>/` et `referentiels_versions/<ref>/<version>/`.

Idempotent : relancé à chaque démarrage, il ajoute les nouvelles versions et
met à jour les autres ; une version déjà importée n'est jamais supprimée (le
hub garde l'historique, même si un fichier disparaît d'une livraison).
"""
import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.nomenclatures.models import (
    CorrespondanceReferentiel, LigneReferentiel, Nomenclature, VersionReferentiel,
)

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'


def dossiers_versions(racine: Path = DATA_DIR):
    for d in sorted((racine / 'referentiels_types_action').glob('*/version.json')):
        yield 'TYPE_ACTION', d.parent
    for d in sorted((racine / 'referentiels_versions').glob('*/*/version.json')):
        yield d.parent.parent.name.upper(), d.parent


def _csv(chemin: Path):
    if not chemin.exists():
        return []
    with open(chemin, encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


@transaction.atomic
def importer(racine: Path = DATA_DIR) -> int:
    n = 0
    # Version de départ des instances : la codification Eden 62, relevée dans
    # les nomenclatures importées (TYPE_ACTION du fichier SQL de CICADA).
    eden, _ = VersionReferentiel.objects.update_or_create(
        referentiel='TYPE_ACTION', code='EDEN62', defaults={'libelle': 'Codification unique Eden 62'})
    for code, label in (Nomenclature.objects.filter(id_type__mnemonique='TYPE_ACTION')
                        .values_list('cd_nomenclature', 'label')):
        if code:
            LigneReferentiel.objects.update_or_create(version=eden, code=code,
                                                      defaults={'libelle': label or ''})
    for ref, dossier in dossiers_versions(racine):
        meta = json.loads((dossier / 'version.json').read_text(encoding='utf-8'))
        version, _ = VersionReferentiel.objects.update_or_create(
            referentiel=ref, code=meta['code'],
            defaults={'libelle': meta.get('libelle', meta['code']), 'depuis': meta.get('depuis', '')})
        for row in _csv(dossier / 'referentiel.csv'):
            if (row.get('code') or '').strip():
                LigneReferentiel.objects.update_or_create(
                    version=version, code=row['code'].strip(),
                    defaults={'libelle': ' '.join((row.get('libelle') or '').split())})
        for row in _csv(dossier / 'correspondance.csv'):
            ancien = (row.get('ancien_code') or '').strip()
            if not ancien:
                continue
            CorrespondanceReferentiel.objects.update_or_create(
                version=version, ancien_code=ancien,
                defaults={'nouveau_code': (row.get('nouveau_code') or '').strip(),
                          'options': [c.strip() for c in (row.get('options') or '').split('|') if c.strip()],
                          'confiance': (row.get('confiance') or '').strip()})
        n += 1
    return n


class Command(BaseCommand):
    help = "Importe les versions des référentiels de CICADA et leurs correspondances (#780)."

    def handle(self, *args, **options):
        n = importer()
        self.stdout.write(self.style.SUCCESS(
            f"✓ Référentiels : {n} version(s) livrée(s), "
            f"{CorrespondanceReferentiel.objects.count()} correspondance(s) en base."))
