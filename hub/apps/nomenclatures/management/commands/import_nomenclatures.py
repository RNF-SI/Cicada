"""
Import des nomenclatures de référence depuis les fichiers SQL de CICADA.

Volontairement plus simple que la commande homonyme de CICADA, qui fait un
upsert ligne à ligne pour préserver les clés étrangères des données métier. Ici
**rien ne référence les nomenclatures par identifiant** : l'index stocke des
codes (`type_site_codes`, `sous_type`), jamais des `id_nomenclature`. Recharger
la table à blanc est donc sans conséquence, et évite de réimplémenter un upsert
dont personne n'a besoin.

Les fichiers SQL sont **ceux de CICADA**, montés en lecture seule (cf.
``docker-compose.hub.yml``). Ils portent des identifiants explicites, ce qui
fait d'ailleurs des nomenclatures le seul référentiel dont les identifiants
coïncident entre instances — mais les documents transportent quand même les
mnémoniques, pour ne pas dépendre de cette coïncidence.

Usage :
    python manage.py import_nomenclatures            # import (ignoré si déjà fait)
    python manage.py import_nomenclatures --force    # rechargement à blanc
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.nomenclatures.models import Nomenclature, TypeNomenclature

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
FICHIER_TYPES = DATA_DIR / 'types_inserts.sql'
FICHIER_VALEURS = DATA_DIR / 'nomenclatures_inserts.sql'


class Command(BaseCommand):
    help = "Importe les nomenclatures de référence dans le schéma ref_nomenclatures"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help="Recharge à blanc même si les nomenclatures sont déjà présentes",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.MIGRATE_HEADING('=== IMPORT DES NOMENCLATURES (hub) ===')
        )

        if not options['force'] and Nomenclature.objects.exists():
            self.stdout.write(self.style.SUCCESS(
                f'Nomenclatures déjà importées '
                f'({Nomenclature.objects.count()} valeurs). '
                f'Utilisez --force pour recharger.'
            ))
            return

        for fichier in (FICHIER_TYPES, FICHIER_VALEURS):
            if not fichier.exists():
                # Échec franc : sans nomenclatures, les facettes « type d'aire
                # protégée », « catégorie d'action » et « type d'indicateur »
                # sont vides et l'exploration paraît fonctionner alors qu'elle
                # ne propose plus rien à filtrer.
                raise CommandError(
                    f'Fichier introuvable : {fichier}. '
                    f'Le montage du dossier de données de CICADA est-il en place ?'
                )

        with transaction.atomic(), connection.cursor() as cur:
            # CASCADE : `t_nomenclatures` référence `bib_nomenclatures_types`.
            cur.execute(
                'TRUNCATE ref_nomenclatures.bib_nomenclatures_types '
                'RESTART IDENTITY CASCADE;'
            )
            cur.execute(FICHIER_TYPES.read_text(encoding='utf-8'))
            cur.execute(FICHIER_VALEURS.read_text(encoding='utf-8'))

            # Les inserts portent des identifiants explicites : sans recaler les
            # séquences, la première création ultérieure entrerait en collision.
            for table, colonne in (
                ('ref_nomenclatures.bib_nomenclatures_types', 'id_type'),
                ('ref_nomenclatures.t_nomenclatures', 'id_nomenclature'),
            ):
                cur.execute(
                    f"SELECT setval(pg_get_serial_sequence('{table}', '{colonne}'), "
                    f"COALESCE((SELECT MAX({colonne}) FROM {table}), 1));"
                )

        self.stdout.write(self.style.SUCCESS(
            f'  {TypeNomenclature.objects.count()} types et '
            f'{Nomenclature.objects.count()} nomenclatures importés'
        ))
