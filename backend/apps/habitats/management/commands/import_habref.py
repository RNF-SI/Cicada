"""
Commande Django pour importer le référentiel HabRef depuis l'INPN.

Télécharge le ZIP depuis geonature.fr, décompresse et charge les CSV
via PostgreSQL COPY.

Les fichiers HabRef sont en UTF-8 avec le délimiteur ';'.

Usage:
    python manage.py import_habref                  # Import standard
    python manage.py import_habref --force           # Force le rechargement
    python manage.py import_habref --cache-dir /tmp  # Répertoire de cache
"""

import csv
import io
import logging
import os
import tempfile
import urllib.request
import zipfile

from django.core.management.base import BaseCommand
from django.db import connection, transaction

logger = logging.getLogger(__name__)

HABREF_URL = 'https://geonature.fr/data/inpn/habitats/HABREF_50.zip'

# Mapping des fichiers CSV -> tables SQL
# csv_to_db : mapping { nom_colonne_CSV -> nom_colonne_DB }
# Seules les colonnes listées ici sont importées.
HABREF_FILES = {
    'TYPOREF': {
        'table': 'ref_habitats.typoref',
        'csv_to_db': {
            'CD_TYPO': 'cd_typo',
            'CD_TABLE': 'cd_table',
            'LB_NOM_TYPO': 'lb_typo',
            'NOM_JEU_DONNEES': 'nom_jeu_donnees',
            'DATE_CREATION': 'date_creation',
            'DATE_MISE_JOUR_TABLE': 'date_mise_jour',
            'AUTEUR_TYPO': 'auteur_jeu_donnees',
            'TERRITOIRE': 'territoire',
        },
    },
    'HABREF': {
        'table': 'ref_habitats.habref',
        'csv_to_db': {
            'CD_HAB': 'cd_hab',
            'FG_VALIDITE': 'fg_validite',
            'CD_TYPO': 'cd_typo',
            'LB_CODE': 'lb_code',
            'LB_HAB_FR': 'lb_hab_fr',
            'LB_HAB_FR_COMPLET': 'lb_hab_fr_complet',
            'LB_HAB_EN': 'lb_hab_en',
            'LB_AUTEUR': 'lb_auteur',
            'NIVEAU': 'niveau',
            'LB_DESCRIPTION': 'lb_description',
            'CD_HAB_SUP': 'cd_hab_sup',
            'PATH_CD_HAB': 'path_cd_hab',
        },
        # Colonnes absentes du CSV mais dans le modèle (seront vides)
    },
    'HABREF_CORRESP_HAB': {
        'table': 'ref_habitats.habref_corresp_hab',
        'csv_to_db': {
            'CD_HAB_ENTRE': 'cd_hab',
            'CD_HAB_SORTIE': 'cd_hab_entre',
            'CD_TYPO_ENTRE': 'cd_typo_entre',
            'CD_TYPE_RELATION': 'type_rel',
        },
        'has_id': True,
    },
    'HABREF_CORRESP_TAXON': {
        'table': 'ref_habitats.habref_corresp_taxon',
        'csv_to_db': {
            'CD_HAB_ENTRE': 'cd_hab',
            'CD_NOM': 'cd_nom',
            'NOM_CITE': 'nom_cite',
        },
        'has_id': True,
    },
}


class Command(BaseCommand):
    help = 'Importe le référentiel HabRef depuis geonature.fr'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force le rechargement complet',
        )
        parser.add_argument(
            '--cache-dir',
            default=None,
            help='Répertoire pour le cache des fichiers téléchargés',
        )

    def handle(self, *args, **options):
        force = options['force']
        cache_dir = options['cache_dir'] or os.path.join(
            tempfile.gettempdir(), 'cicada_habref_cache'
        )

        self.stdout.write(self.style.MIGRATE_HEADING(
            '=== IMPORT HABREF ==='
        ))

        # Vérifier si déjà installé
        if not force and self._is_installed():
            self.stdout.write(self.style.SUCCESS(
                'HabRef est déjà installé. '
                'Utilisez --force pour forcer le rechargement.'
            ))
            return

        os.makedirs(cache_dir, exist_ok=True)

        # Étape 1 : Télécharger
        zip_path = self._download_zip(cache_dir)

        # Étape 2 : Décompresser
        extract_dir = self._extract_zip(zip_path, cache_dir)

        # Étape 3 : Charger les fichiers
        with transaction.atomic():
            self._ensure_schema_and_extensions()
            csv_files = self._find_csv_files(extract_dir)
            self._load_csv_files(csv_files)
            self._generate_autocomplete_data()

        self.stdout.write(self.style.SUCCESS(
            'Import HabRef terminé avec succès!'
        ))

    def _is_installed(self):
        """Vérifie si HabRef est déjà importé."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT COUNT(*) FROM ref_habitats.habref'
                )
                return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def _download_zip(self, cache_dir):
        """Télécharge le ZIP HabRef (avec cache local)."""
        zip_filename = 'HABREF_50.zip'
        zip_path = os.path.join(cache_dir, zip_filename)

        if os.path.exists(zip_path):
            self.stdout.write(f'  Fichier en cache : {zip_path}')
            return zip_path

        self.stdout.write(f'  Téléchargement de {HABREF_URL} ...')
        try:
            urllib.request.urlretrieve(HABREF_URL, zip_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f'Erreur de téléchargement : {e}'
            ))
            raise
        self.stdout.write(self.style.SUCCESS(f'  Téléchargé : {zip_path}'))
        return zip_path

    def _extract_zip(self, zip_path, cache_dir):
        """Décompresse le ZIP."""
        extract_dir = os.path.join(cache_dir, 'HABREF_50')
        if os.path.isdir(extract_dir) and os.listdir(extract_dir):
            self.stdout.write(f'  Répertoire déjà décompressé : {extract_dir}')
            return extract_dir

        self.stdout.write(f'  Décompression de {zip_path} ...')
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
        self.stdout.write(self.style.SUCCESS('  Décompression terminée'))
        return extract_dir

    def _ensure_schema_and_extensions(self):
        """S'assure que le schema et les extensions existent."""
        with connection.cursor() as cursor:
            cursor.execute('CREATE SCHEMA IF NOT EXISTS ref_habitats')
            cursor.execute(
                'CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public'
            )
            cursor.execute(
                'CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA public'
            )

    def _find_csv_files(self, extract_dir):
        """Trouve les fichiers CSV dans le répertoire extrait."""
        found = {}
        for root, _dirs, files in os.walk(extract_dir):
            for f in sorted(files):
                if not (f.endswith('.csv') or f.endswith('.txt')):
                    continue
                fname_upper = f.upper().replace('.CSV', '').replace('.TXT', '')
                # Préférer les versions NOHTML si disponibles
                for key in HABREF_FILES:
                    if key in fname_upper:
                        # Ne pas écraser par une version non-NOHTML
                        if key in found and 'NOHTML' not in fname_upper:
                            continue
                        found[key] = os.path.join(root, f)
                        break

        self.stdout.write(
            f'  Fichiers trouvés : {len(found)}/{len(HABREF_FILES)}'
        )
        for key, path in found.items():
            self.stdout.write(f'    {key}: {path}')
        return found

    def _load_csv_files(self, csv_files):
        """Charge les fichiers CSV via COPY."""
        # Ordre de chargement (les tables avec FK en dernier)
        load_order = ['TYPOREF', 'HABREF', 'HABREF_CORRESP_HAB',
                       'HABREF_CORRESP_TAXON']

        for key in load_order:
            if key not in csv_files:
                self.stdout.write(self.style.WARNING(
                    f'  Fichier {key} non trouvé, ignoré'
                ))
                continue

            file_info = HABREF_FILES[key]
            csv_path = csv_files[key]
            self._load_single_csv(
                csv_path, file_info['table'], file_info['csv_to_db'],
                has_id=file_info.get('has_id', False), key=key,
            )

    def _load_single_csv(self, csv_path, table, csv_to_db, has_id=False,
                          key=''):
        """Charge un fichier CSV unique via COPY."""
        self.stdout.write(f'  Chargement {key} -> {table} ...')

        with connection.cursor() as cursor:
            cursor.execute(f'TRUNCATE TABLE {table} CASCADE')

        db_columns = list(csv_to_db.values())
        csv_columns = list(csv_to_db.keys())

        # Lire le CSV et préparer le flux pour COPY
        output = io.StringIO()
        count = 0

        # Les fichiers HabRef sont en UTF-8, délimiteur ';'
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            # Détecter le délimiteur
            first_line = f.readline()
            delimiter = ';' if ';' in first_line else '\t'
            f.seek(0)

            reader = csv.DictReader(f, delimiter=delimiter)
            writer = csv.writer(output, delimiter='\t')
            # En-tête avec les noms de colonnes DB
            writer.writerow(db_columns)

            for row in reader:
                values = []
                skip = False
                for csv_col in csv_columns:
                    val = row.get(csv_col, '')
                    if val is None:
                        val = ''
                    values.append(val)
                writer.writerow(values)
                count += 1

        if count == 0:
            self.stdout.write(self.style.WARNING(
                f'    Aucune ligne dans {key}'
            ))
            return

        output.seek(0)
        columns_str = ', '.join(db_columns)
        copy_sql = (
            f"COPY {table} ({columns_str}) "
            f"FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', "
            f"HEADER TRUE, NULL '')"
        )

        # psycopg3 : utiliser cursor.copy()
        raw_conn = connection.connection
        with raw_conn.cursor() as raw_cursor:
            with raw_cursor.copy(copy_sql) as copy:
                while data := output.read(8192):
                    copy.write(data.encode('utf-8'))

        # Mettre à jour la séquence si la table a un id auto
        if has_id:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT setval(
                        pg_get_serial_sequence('{table}', 'id'),
                        COALESCE((SELECT MAX(id) FROM {table}), 1),
                        true
                    )
                """)

        self.stdout.write(self.style.SUCCESS(
            f'    {count} lignes chargées dans {table}'
        ))

    def _generate_autocomplete_data(self):
        """
        Génère la table d'autocomplete pour les habitats.

        Combine le nom français avec le code pour permettre la recherche.
        """
        self.stdout.write('  Génération des données autocomplete...')
        with connection.cursor() as cursor:
            cursor.execute(
                'TRUNCATE TABLE ref_habitats.autocomplete_habitat CASCADE'
            )

            cursor.execute("""
                INSERT INTO ref_habitats.autocomplete_habitat
                    (cd_hab, cd_typo, lb_code, search_name,
                     lb_hab_fr, lb_hab_fr_complet, lb_typo, niveau)
                SELECT
                    h.cd_hab,
                    h.cd_typo,
                    h.lb_code,
                    COALESCE(h.lb_code, '') || ' ' ||
                    COALESCE(h.lb_hab_fr, '') || ' ' ||
                    COALESCE(h.lb_hab_fr_complet, '') AS search_name,
                    h.lb_hab_fr,
                    h.lb_hab_fr_complet,
                    t.lb_typo,
                    h.niveau
                FROM ref_habitats.habref h
                LEFT JOIN ref_habitats.typoref t ON h.cd_typo = t.cd_typo
                WHERE h.fg_validite NOT IN ('SUPPR', 'ERR')
                   OR h.fg_validite IS NULL
            """)

            # Index trigramme pour l'autocomplete
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_autocomplete_habitat_trgm
                ON ref_habitats.autocomplete_habitat
                USING gin (search_name gin_trgm_ops)
            """)
            # Rendre unaccent() IMMUTABLE pour permettre l'indexation
            cursor.execute("""
                ALTER FUNCTION public.unaccent(text)
                IMMUTABLE
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_autocomplete_habitat_unaccent
                ON ref_habitats.autocomplete_habitat
                USING gin (public.unaccent(search_name) gin_trgm_ops)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_autocomplete_habitat_cd_typo
                ON ref_habitats.autocomplete_habitat (cd_typo)
            """)

            cursor.execute(
                'SELECT COUNT(*) FROM ref_habitats.autocomplete_habitat'
            )
            count = cursor.fetchone()[0]

        self.stdout.write(self.style.SUCCESS(
            f'  {count} habitats dans la table autocomplete'
        ))
