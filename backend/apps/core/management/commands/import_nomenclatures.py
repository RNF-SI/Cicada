"""
Commande Django pour importer les nomenclatures de référence.

Les nomenclatures sont des données essentielles au fonctionnement de l'application
(types de sites, types d'évaluation, types de documents, etc.).

Modes de fonctionnement :
  - Sans argument    : Skip si les données existent déjà (démarrage rapide)
  - --force          : Upsert intelligent (met à jour labels/définitions, ajoute les nouvelles)
  - --force --prune  : Upsert + supprime les entrées qui ne sont plus dans les fichiers SQL

Usage:
    python manage.py import_nomenclatures                # Skip si déjà fait
    python manage.py import_nomenclatures --force        # Upsert (ajouter + mettre à jour)
    python manage.py import_nomenclatures --force --prune # Upsert + supprimer les obsolètes
"""
import logging
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection, transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Importe les nomenclatures de référence depuis les fichiers SQL (upsert intelligent)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force la réimportation via upsert (ajoute et met à jour)',
        )
        parser.add_argument(
            '--prune',
            action='store_true',
            help='Supprime les nomenclatures absentes des fichiers SQL (implique --force)',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== IMPORT DES NOMENCLATURES ==='))

        force = options['force']
        prune = options['prune']

        # --prune implique --force
        if prune:
            force = True

        if not force:
            if self._nomenclatures_already_exist():
                self.stdout.write(self.style.SUCCESS(
                    '✓ Les nomenclatures sont déjà importées - import ignoré'
                ))
                self.stdout.write('  (Utilisez --force pour mettre à jour, --force --prune pour nettoyer)')
                return
            # Base partielle (quelques entrées créées par migrations/seeds) :
            # bascule automatiquement en upsert pour éviter les conflits PK.
            if self._has_partial_data():
                self.stdout.write(self.style.WARNING(
                    '⚠ Données partielles détectées - bascule en mode upsert'
                ))
                force = True

        # Chemins vers les fichiers SQL
        project_dir = Path(__file__).resolve().parents[4]  # backend/
        types_file = project_dir / 'nomenclatures_data' / 'types_inserts.sql'
        nomenclatures_file = project_dir / 'nomenclatures_data' / 'nomenclatures_inserts.sql'

        if not types_file.exists():
            self.stderr.write(self.style.ERROR(f'Fichier non trouvé: {types_file}'))
            return

        if not nomenclatures_file.exists():
            self.stderr.write(self.style.ERROR(f'Fichier non trouvé: {nomenclatures_file}'))
            return

        try:
            with transaction.atomic():
                if force:
                    # Upsert mode: add new entries + update existing ones
                    type_ids = self._upsert_file(
                        types_file, 'types de nomenclatures',
                        'bib_nomenclatures_types', 'id_type'
                    )
                    nom_ids = self._upsert_file(
                        nomenclatures_file, 'nomenclatures',
                        't_nomenclatures', 'id_nomenclature'
                    )

                    if prune:
                        self._prune_obsolete(type_ids, nom_ids)
                else:
                    # First import: plain INSERT (faster for initial load)
                    self._execute_insert_file(types_file, 'types de nomenclatures')
                    self._execute_insert_file(nomenclatures_file, 'nomenclatures')

                # Mettre à jour les séquences
                self._update_sequences()

                # Vérifier l'import
                self._verify_import()

            self.stdout.write(self.style.SUCCESS('✓ Import des nomenclatures terminé avec succès!'))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f'✗ Erreur lors de l\'import: {e}'))
            raise

    def _nomenclatures_already_exist(self):
        """Vérifie si l'import des nomenclatures est complet.

        Compare le nombre de lignes en base au nombre d'INSERT dans les fichiers
        source. Permet d'éviter de skipper l'import quand seules quelques entrées
        ont été créées par ailleurs (migrations, seed_testdata partiels, etc.).
        """
        try:
            project_dir = Path(__file__).resolve().parents[4]
            types_file = project_dir / 'nomenclatures_data' / 'types_inserts.sql'
            noms_file = project_dir / 'nomenclatures_data' / 'nomenclatures_inserts.sql'
            if not types_file.exists() or not noms_file.exists():
                return False

            expected_types = sum(
                1 for line in types_file.read_text().splitlines()
                if line.strip().upper().startswith('INSERT')
            )
            expected_noms = sum(
                1 for line in noms_file.read_text().splitlines()
                if line.strip().upper().startswith('INSERT')
            )

            with connection.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM bib_nomenclatures_types')
                types_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM t_nomenclatures')
                noms_count = cursor.fetchone()[0]
            return types_count >= expected_types and noms_count >= expected_noms
        except Exception:
            return False

    def _has_partial_data(self):
        """Renvoie True s'il y a au moins une entrée en base (mais pas tout)."""
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT COUNT(*) FROM bib_nomenclatures_types')
                types_count = cursor.fetchone()[0]
                cursor.execute('SELECT COUNT(*) FROM t_nomenclatures')
                noms_count = cursor.fetchone()[0]
            return types_count > 0 or noms_count > 0
        except Exception:
            return False

    def _transform_to_upsert(self, statement, pk_column):
        """Transforme un INSERT en INSERT ... ON CONFLICT DO UPDATE SET."""
        # Extraire la liste des colonnes entre parenthèses avant VALUES
        col_match = re.search(r'\(([^)]+)\)\s*VALUES', statement)
        if not col_match:
            return statement

        columns = [c.strip() for c in col_match.group(1).split(',')]
        update_cols = [c for c in columns if c != pk_column]
        set_clause = ', '.join(f'{c} = EXCLUDED.{c}' for c in update_cols)

        # Ajouter ON CONFLICT avant le ; final
        base = statement.rstrip().rstrip(';').rstrip()
        return f'{base} ON CONFLICT ({pk_column}) DO UPDATE SET {set_clause};'

    def _extract_pk_value(self, statement):
        """Extrait la valeur de la PK (premier entier après VALUES) d'un INSERT."""
        val_match = re.search(r'VALUES\s*\(\s*(\d+)', statement)
        return int(val_match.group(1)) if val_match else None

    def _upsert_file(self, file_path, description, table_name, pk_column):
        """Exécute un fichier SQL en mode upsert et retourne les IDs traités."""
        self.stdout.write(f'  Upsert des {description}...')

        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        if not sql_content.strip():
            self.stderr.write(self.style.WARNING(f'  Fichier vide: {file_path}'))
            return set()

        collected_ids = set()
        inserted = 0
        updated = 0

        with connection.cursor() as cursor:
            for statement in sql_content.split('\n'):
                statement = statement.strip()
                if not statement.startswith('INSERT INTO'):
                    continue

                pk_val = self._extract_pk_value(statement)
                if pk_val is not None:
                    collected_ids.add(pk_val)

                # Vérifier si l'entrée existe déjà (pour le compteur)
                exists = False
                if pk_val is not None:
                    cursor.execute(
                        f'SELECT 1 FROM {table_name} WHERE {pk_column} = %s',
                        [pk_val]
                    )
                    exists = cursor.fetchone() is not None

                upsert_sql = self._transform_to_upsert(statement, pk_column)
                cursor.execute(upsert_sql)

                if exists:
                    updated += 1
                else:
                    inserted += 1

        self.stdout.write(self.style.SUCCESS(
            f'  ✓ {description}: {inserted} ajoutés, {updated} mis à jour'
        ))
        return collected_ids

    def _prune_obsolete(self, type_ids, nomenclature_ids):
        """Supprime les entrées qui ne sont plus dans les fichiers SQL."""
        self.stdout.write('  Recherche des entrées obsolètes...')

        with connection.cursor() as cursor:
            # Nomenclatures obsolètes (traiter en premier à cause des FK)
            if nomenclature_ids:
                placeholders = ', '.join(['%s'] * len(nomenclature_ids))
                cursor.execute(
                    f'SELECT id_nomenclature, mnemonique, label FROM t_nomenclatures '
                    f'WHERE id_nomenclature NOT IN ({placeholders})',
                    list(nomenclature_ids)
                )
                obsolete_noms = cursor.fetchall()
            else:
                obsolete_noms = []

            # Types obsolètes
            if type_ids:
                placeholders = ', '.join(['%s'] * len(type_ids))
                cursor.execute(
                    f'SELECT id_type, mnemonique, label FROM bib_nomenclatures_types '
                    f'WHERE id_type NOT IN ({placeholders})',
                    list(type_ids)
                )
                obsolete_types = cursor.fetchall()
            else:
                obsolete_types = []

            if not obsolete_noms and not obsolete_types:
                self.stdout.write(self.style.SUCCESS('  ✓ Aucune entrée obsolète à supprimer'))
                return

            # Supprimer les nomenclatures obsolètes
            pruned_noms = 0
            skipped_noms = 0
            for id_nom, mnem, label in obsolete_noms:
                try:
                    cursor.execute(
                        'DELETE FROM t_nomenclatures WHERE id_nomenclature = %s',
                        [id_nom]
                    )
                    pruned_noms += 1
                    self.stdout.write(
                        f'    Supprimé: nomenclature {mnem} ({label})'
                    )
                except Exception as e:
                    skipped_noms += 1
                    self.stdout.write(self.style.WARNING(
                        f'    ⚠ Impossible de supprimer {mnem} ({label}): '
                        f'référencé par des données existantes'
                    ))
                    logger.debug(f'Prune skip {mnem}: {e}')

            # Supprimer les types obsolètes
            pruned_types = 0
            skipped_types = 0
            for id_type, mnem, label in obsolete_types:
                try:
                    cursor.execute(
                        'DELETE FROM bib_nomenclatures_types WHERE id_type = %s',
                        [id_type]
                    )
                    pruned_types += 1
                    self.stdout.write(
                        f'    Supprimé: type {mnem} ({label})'
                    )
                except Exception as e:
                    skipped_types += 1
                    self.stdout.write(self.style.WARNING(
                        f'    ⚠ Impossible de supprimer type {mnem} ({label}): '
                        f'référencé par des nomenclatures existantes'
                    ))
                    logger.debug(f'Prune skip type {mnem}: {e}')

            summary_parts = []
            if pruned_noms:
                summary_parts.append(f'{pruned_noms} nomenclatures supprimées')
            if pruned_types:
                summary_parts.append(f'{pruned_types} types supprimés')
            if skipped_noms or skipped_types:
                summary_parts.append(
                    f'{skipped_noms + skipped_types} ignorés (références FK)'
                )

            self.stdout.write(self.style.SUCCESS(
                f'  ✓ Nettoyage: {", ".join(summary_parts) if summary_parts else "rien à faire"}'
            ))

    def _execute_insert_file(self, file_path, description):
        """Exécute un fichier contenant des INSERT statements (mode initial)."""
        self.stdout.write(f'  Import des {description}...')

        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()

        if not sql_content.strip():
            self.stderr.write(self.style.WARNING(f'  Fichier vide: {file_path}'))
            return

        with connection.cursor() as cursor:
            for statement in sql_content.split('\n'):
                statement = statement.strip()
                if statement and statement.startswith('INSERT INTO'):
                    cursor.execute(statement)

        self.stdout.write(self.style.SUCCESS(f'  ✓ {description} importés'))

    def _update_sequences(self):
        """Met à jour les séquences PostgreSQL après l'import."""
        with connection.cursor() as cursor:
            # Séquence pour bib_nomenclatures_types
            cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence('ref_nomenclatures.bib_nomenclatures_types', 'id_type'),
                    COALESCE((SELECT MAX(id_type) FROM bib_nomenclatures_types), 1),
                    true
                )
            """)
            # Séquence pour t_nomenclatures
            cursor.execute("""
                SELECT setval(
                    pg_get_serial_sequence('ref_nomenclatures.t_nomenclatures', 'id_nomenclature'),
                    COALESCE((SELECT MAX(id_nomenclature) FROM t_nomenclatures), 1),
                    true
                )
            """)

    def _verify_import(self):
        """Vérifie et affiche le résultat de l'import."""
        with connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM bib_nomenclatures_types')
            types_count = cursor.fetchone()[0]

            cursor.execute('SELECT COUNT(*) FROM t_nomenclatures')
            nomenclatures_count = cursor.fetchone()[0]

        self.stdout.write(f'  ✓ Types de nomenclatures: {types_count}')
        self.stdout.write(f'  ✓ Nomenclatures: {nomenclatures_count}')
