"""
Commande Django pour importer le référentiel TaxRef depuis l'INPN.

Télécharge le ZIP depuis geonature.fr, décompresse et charge les CSV
via PostgreSQL COPY pour la performance (~700k lignes).

Usage:
    python manage.py import_taxref                    # Import complet (v18)
    python manage.py import_taxref --lite             # Import allégé (~8k taxons, pour dev/tests)
    python manage.py import_taxref --version 17       # Version spécifique
    python manage.py import_taxref --force             # Force le rechargement
    python manage.py import_taxref --cache-dir /tmp    # Répertoire de cache
"""

import csv
import io
import logging
import os
import tempfile
import urllib.request
import zipfile
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# URL template - la version est injectée dynamiquement
TAXREF_URL_TEMPLATE = (
    'https://geonature.fr/data/inpn/taxonomie/TAXREF_v{version}_2025.zip'
)

# Versions connues et leurs URLs
TAXREF_VERSIONS = {
    '18': 'https://geonature.fr/data/inpn/taxonomie/TAXREF_v18_2025.zip',
    '17': 'https://geonature.fr/data/inpn/taxonomie/TAXREF_v17_2024.zip',
}

DEFAULT_VERSION = '18'

# Mapping CSV colonne -> DB colonne
# Les noms CSV (en majuscules) diffèrent parfois des noms de colonnes DB.
TAXREF_CSV_TO_DB = {
    'CD_NOM': 'cd_nom',
    'FR': 'id_statut',
    'HABITAT': 'id_habitat',
    'RANG': 'id_rang',
    'REGNE': 'regne',
    'PHYLUM': 'phylum',
    'CLASSE': 'classe',
    'ORDRE': 'ordre',
    'FAMILLE': 'famille',
    'SOUS_FAMILLE': 'sous_famille',
    'TRIBU': 'tribu',
    'CD_TAXSUP': 'cd_taxsup',
    'CD_SUP': 'cd_sup',
    'CD_REF': 'cd_ref',
    'LB_NOM': 'lb_nom',
    'LB_AUTEUR': 'lb_auteur',
    'NOM_COMPLET': 'nom_complet',
    'NOM_COMPLET_HTML': 'nom_complet_html',
    'NOM_VALIDE': 'nom_valide',
    'NOM_VERN': 'nom_vern',
    'NOM_VERN_ENG': 'nom_vern_eng',
    'GROUP1_INPN': 'group1_inpn',
    'GROUP2_INPN': 'group2_inpn',
    'GROUP3_INPN': 'group3_inpn',
    'URL': 'url',
}

# Colonnes DB dans l'ordre d'insertion
TAXREF_DB_COLUMNS = list(TAXREF_CSV_TO_DB.values())
# Colonnes CSV correspondantes
TAXREF_CSV_COLUMNS = list(TAXREF_CSV_TO_DB.keys())

# Données de référence pour bib_taxref_rangs
RANGS = [
    ('Dumm', 'Dummy', 0),
    ('KD', 'Règne', 1),
    ('PH', 'Phylum', 3),
    ('CL', 'Classe', 5),
    ('OR', 'Ordre', 7),
    ('FM', 'Famille', 11),
    ('SFAM', 'Sous-Famille', 12),
    ('TR', 'Tribu', 13),
    ('GN', 'Genre', 15),
    ('AGES', 'Agrégat', 20),
    ('ES', 'Espèce', 22),
    ('SSES', 'Sous-Espèce', 23),
    ('VAR', 'Variété', 27),
    ('CVAR', 'Cultivar', 33),
    ('HYB', 'Hybride', 35),
    ('AB', 'Aberration', 36),
]

# Données de référence pour bib_taxref_habitats
HABITATS = [
    (1, 'Marin'),
    (2, 'Eau douce'),
    (3, 'Terrestre'),
    (4, 'Marin et Eau douce'),
    (5, 'Marin et Terrestre'),
    (6, 'Eau douce et Terrestre'),
    (7, 'Marin, Eau douce et Terrestre'),
    (8, 'Continental (Terrestre et/ou Eau douce)'),
]

# Données de référence pour bib_taxref_statuts
STATUTS = [
    ('A', 'Absent'),
    ('B', 'Occasionnel'),
    ('C', 'Cryptogène'),
    ('D', 'Douteux'),
    ('E', 'Endémique'),
    ('I', 'Introduit'),
    ('J', 'Introduit envahissant'),
    ('M', 'Introduit non établi'),
    ('P', 'Présent'),
    ('Q', 'Mentionné par erreur'),
    ('S', 'Subendémique'),
    ('W', 'Disparu'),
    ('X', 'Eteint'),
    ('Y', 'Introduit éteint'),
    ('Z', 'Endémique éteint'),
]

# ── Mode lite ──────────────────────────────────────────────────────────
# Sous-ensemble représentatif pour le développement et les tests.
# On ne garde que les noms de référence (cd_nom == cd_ref), au rang
# espèce ou supérieur, dans les groupes taxonomiques les plus utiles
# pour la gestion d'espaces naturels (CEN/RNF).
# Le cap par groupe permet de rester à ~8000 taxons total.

LITE_RANGS_ALLOWED = {'KD', 'PH', 'CL', 'OR', 'FM', 'GN', 'ES'}

LITE_GROUP_CAPS = {
    'Oiseaux': 700,
    'Mammiferes': 250,
    'Reptiles': 100,
    'Amphibiens': 60,
    'Poissons': 500,
    'Angiospermes': 3000,
    'Gymnospermes': 60,
    'Pteridophytes': 200,
    'Insectes': 2000,
    'Mousses': 300,
    'Champignons': 500,
    'Lichens': 200,
    'Crustaces': 200,
    'Mollusques': 300,
}

# Pour les groupes non listés ci-dessus, on prend quand même quelques
# taxons de rang supérieur (familles, ordres) pour la cohérence.
LITE_DEFAULT_CAP = 50


class Command(BaseCommand):
    help = 'Importe le référentiel TaxRef depuis geonature.fr'

    def add_arguments(self, parser):
        parser.add_argument(
            '--taxref-version',
            default=DEFAULT_VERSION,
            dest='taxref_version',
            help=f'Version de TaxRef à importer (défaut: {DEFAULT_VERSION})',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force le rechargement même si la version est déjà installée',
        )
        parser.add_argument(
            '--lite',
            action='store_true',
            help='Import allégé (~8000 taxons représentatifs) pour dev/tests',
        )
        parser.add_argument(
            '--cache-dir',
            default=None,
            help='Répertoire pour le cache des fichiers téléchargés',
        )

    def handle(self, *args, **options):
        version = options['taxref_version']
        force = options['force']
        self.lite_mode = options['lite']
        cache_dir = options['cache_dir'] or os.path.join(
            tempfile.gettempdir(), 'cicada_taxref_cache'
        )

        mode_label = ' (LITE)' if self.lite_mode else ''
        self.stdout.write(self.style.MIGRATE_HEADING(
            f'=== IMPORT TAXREF v{version}{mode_label} ==='
        ))

        # Vérifier si déjà installé
        installed_mode = self._get_installed_mode(version)
        if not force and installed_mode is not None:
            # Si on est en mode complet et qu'une version lite est
            # installée, il faut recharger
            if not self.lite_mode and installed_mode == 'lite':
                self.stdout.write(
                    '  Version lite détectée, rechargement en mode complet...'
                )
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'TaxRef v{version}{" (lite)" if installed_mode == "lite" else ""}'
                    ' est déjà installé. '
                    'Utilisez --force pour forcer le rechargement.'
                ))
                return

        # Créer le répertoire de cache
        os.makedirs(cache_dir, exist_ok=True)

        # Étape 1 : Télécharger le ZIP
        zip_path = self._download_zip(version, cache_dir)

        # Étape 2 : Décompresser
        extract_dir = self._extract_zip(zip_path, cache_dir, version)

        # Étape 3 : Trouver le fichier CSV principal
        csv_file = self._find_taxref_csv(extract_dir)

        # Étape 4 : Charger les données
        with transaction.atomic():
            self._ensure_schema_and_extensions()
            self._load_reference_data()
            self._load_taxref_csv(csv_file)
            self._create_or_refresh_materialized_view()
            self._update_meta(version)

        self.stdout.write(self.style.SUCCESS(
            f'Import TaxRef v{version}{mode_label} terminé avec succès!'
        ))

    def _get_installed_mode(self, version):
        """
        Retourne le mode d'installation ('full', 'lite') ou None.
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT referential_name FROM taxonomie.t_meta_taxref '
                    'WHERE version = %s ORDER BY update_date DESC LIMIT 1',
                    [version],
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                name = row[0]
                return 'lite' if 'lite' in name else 'full'
        except Exception:
            return None

    def _download_zip(self, version, cache_dir):
        """Télécharge le ZIP TaxRef (avec cache local)."""
        url = TAXREF_VERSIONS.get(
            version,
            TAXREF_URL_TEMPLATE.format(version=version),
        )
        zip_filename = f'TAXREF_v{version}.zip'
        zip_path = os.path.join(cache_dir, zip_filename)

        if os.path.exists(zip_path):
            self.stdout.write(
                f'  Fichier en cache trouvé : {zip_path}'
            )
            return zip_path

        self.stdout.write(f'  Téléchargement de {url} ...')
        try:
            urllib.request.urlretrieve(url, zip_path)
        except Exception as e:
            self.stderr.write(self.style.ERROR(
                f'Erreur de téléchargement : {e}'
            ))
            raise
        self.stdout.write(self.style.SUCCESS(
            f'  Téléchargé : {zip_path}'
        ))
        return zip_path

    def _extract_zip(self, zip_path, cache_dir, version):
        """Décompresse le ZIP."""
        extract_dir = os.path.join(cache_dir, f'TAXREF_v{version}')
        if os.path.isdir(extract_dir) and os.listdir(extract_dir):
            self.stdout.write(
                f'  Répertoire déjà décompressé : {extract_dir}'
            )
            return extract_dir

        self.stdout.write(f'  Décompression de {zip_path} ...')
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
        self.stdout.write(self.style.SUCCESS('  Décompression terminée'))
        return extract_dir

    def _find_taxref_csv(self, extract_dir):
        """Cherche le fichier CSV principal de TaxRef (TAXREFvXX.txt)."""
        # Noms à ignorer (pas le fichier principal)
        ignore_patterns = {'CHANGES', 'LIENS', 'DISPARUS', 'TAXVERN'}

        for root, _dirs, files in os.walk(extract_dir):
            for f in sorted(files):
                f_upper = f.upper()
                if not f_upper.startswith('TAXREF'):
                    continue
                if not (f.endswith('.txt') or f.endswith('.csv')):
                    continue
                if any(p in f_upper for p in ignore_patterns):
                    continue
                path = os.path.join(root, f)
                self.stdout.write(f'  Fichier TaxRef trouvé : {path}')
                return path

        raise FileNotFoundError(
            f"Aucun fichier TaxRef trouvé dans {extract_dir}"
        )

    def _ensure_schema_and_extensions(self):
        """S'assure que le schema et les extensions existent."""
        with connection.cursor() as cursor:
            cursor.execute('CREATE SCHEMA IF NOT EXISTS taxonomie')
            cursor.execute(
                'CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public'
            )
            cursor.execute(
                'CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA public'
            )

    def _load_reference_data(self):
        """Charge les données de référence (rangs, habitats, statuts)."""
        self.stdout.write('  Chargement des données de référence...')
        with connection.cursor() as cursor:
            # Rangs
            cursor.execute('TRUNCATE TABLE taxonomie.bib_taxref_rangs CASCADE')
            for id_rang, nom_rang, tri_rang in RANGS:
                cursor.execute(
                    'INSERT INTO taxonomie.bib_taxref_rangs '
                    '(id_rang, nom_rang, tri_rang) VALUES (%s, %s, %s)',
                    [id_rang, nom_rang, tri_rang],
                )

            # Habitats
            cursor.execute(
                'TRUNCATE TABLE taxonomie.bib_taxref_habitats CASCADE'
            )
            for id_habitat, nom_habitat in HABITATS:
                cursor.execute(
                    'INSERT INTO taxonomie.bib_taxref_habitats '
                    '(id_habitat, nom_habitat) VALUES (%s, %s)',
                    [id_habitat, nom_habitat],
                )

            # Statuts
            cursor.execute(
                'TRUNCATE TABLE taxonomie.bib_taxref_statuts CASCADE'
            )
            for id_statut, nom_statut in STATUTS:
                cursor.execute(
                    'INSERT INTO taxonomie.bib_taxref_statuts '
                    '(id_statut, nom_statut) VALUES (%s, %s)',
                    [id_statut, nom_statut],
                )

        self.stdout.write(self.style.SUCCESS(
            '  Données de référence chargées'
        ))

    def _should_include_row_lite(self, row, group_counts):
        """
        Filtre une ligne CSV pour le mode lite.

        Critères :
        - Uniquement les noms de référence (cd_nom == cd_ref)
        - Rang espèce ou supérieur (pas sous-espèce, variété, etc.)
        - Respect du cap par groupe taxonomique
        """
        cd_nom = row.get('CD_NOM', '')
        cd_ref = row.get('CD_REF', '')
        rang = row.get('RANG', '')
        group2 = row.get('GROUP2_INPN', '')

        # Noms de référence uniquement
        if cd_nom != cd_ref:
            return False

        # Rangs autorisés
        if rang not in LITE_RANGS_ALLOWED:
            return False

        # Cap par groupe
        cap = LITE_GROUP_CAPS.get(group2, LITE_DEFAULT_CAP)
        if group_counts[group2] >= cap:
            return False

        group_counts[group2] += 1
        return True

    def _load_taxref_csv(self, csv_file):
        """
        Charge le CSV TaxRef via PostgreSQL COPY.

        Le fichier est encodé en WIN1252 avec des tabulations comme
        délimiteur. En mode --lite, seul un sous-ensemble représentatif
        est chargé (~8000 taxons).
        """
        mode_label = ' (mode lite)' if self.lite_mode else ''
        self.stdout.write(f'  Chargement du CSV TaxRef{mode_label} (COPY) ...')

        with connection.cursor() as cursor:
            cursor.execute('TRUNCATE TABLE taxonomie.taxref CASCADE')

        # Lire le CSV et préparer un flux UTF-8 pour COPY
        output = io.StringIO()
        group_counts = defaultdict(int)

        # Détecter l'encodage : essayer UTF-8 d'abord, sinon latin-1
        file_encoding = 'utf-8'
        try:
            with open(csv_file, 'r', encoding='utf-8') as test_f:
                test_f.read(4096)
        except UnicodeDecodeError:
            file_encoding = 'latin-1'
        self.stdout.write(f'  Encodage détecté : {file_encoding}')

        with open(csv_file, 'r', encoding=file_encoding) as f:
            reader = csv.DictReader(f, delimiter='\t')
            writer = csv.writer(output, delimiter='\t')
            writer.writerow(TAXREF_DB_COLUMNS)

            count = 0
            for row in reader:
                # En mode lite, filtrer les lignes
                if self.lite_mode and not self._should_include_row_lite(
                    row, group_counts
                ):
                    continue

                values = []
                for csv_col in TAXREF_CSV_COLUMNS:
                    val = row.get(csv_col, '')
                    if val is None:
                        val = ''
                    values.append(val)
                writer.writerow(values)
                count += 1

        output.seek(0)

        columns_str = ', '.join(TAXREF_DB_COLUMNS)
        copy_sql = (
            f"COPY taxonomie.taxref ({columns_str}) "
            f"FROM STDIN WITH (FORMAT CSV, DELIMITER E'\\t', "
            f"HEADER TRUE, NULL '')"
        )

        # psycopg3 : utiliser cursor.copy() au lieu de copy_expert()
        raw_conn = connection.connection
        with raw_conn.cursor() as raw_cursor:
            with raw_cursor.copy(copy_sql) as copy:
                while data := output.read(8192):
                    copy.write(data.encode('utf-8'))

        self.stdout.write(self.style.SUCCESS(
            f'  {count} taxons chargés via COPY'
        ))

        if self.lite_mode:
            # Afficher le résumé par groupe
            for group, cnt in sorted(
                group_counts.items(), key=lambda x: -x[1]
            ):
                self.stdout.write(f'    {group}: {cnt}')

    def _create_or_refresh_materialized_view(self):
        """Crée ou rafraîchit la vue matérialisée pour l'autocomplete."""
        self.stdout.write(
            '  Création/rafraîchissement de la vue matérialisée...'
        )
        with connection.cursor() as cursor:
            cursor.execute(
                'DROP MATERIALIZED VIEW IF EXISTS '
                'taxonomie.vm_taxref_list_forautocomplete'
            )

            cursor.execute("""
                CREATE MATERIALIZED VIEW
                    taxonomie.vm_taxref_list_forautocomplete AS
                SELECT
                    t.cd_nom,
                    t.cd_ref,
                    COALESCE(t.lb_nom, '') || ' ' ||
                        COALESCE(t.nom_vern, '') AS search_name,
                    t.nom_valide,
                    t.nom_vern,
                    t.lb_nom,
                    t.regne,
                    t.group2_inpn,
                    t.id_rang
                FROM taxonomie.taxref t
                WHERE t.cd_nom = t.cd_ref
                ORDER BY t.lb_nom
            """)

            # Index trigramme pour la recherche floue
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_vm_taxref_autocomplete_trgm
                ON taxonomie.vm_taxref_list_forautocomplete
                USING gin (search_name gin_trgm_ops)
            """)

            # Rendre unaccent() IMMUTABLE + index trigramme sans accents. Sur une
            # base où l'app n'est PAS propriétaire de la fonction (ALTER refusé),
            # on saute l'index — dégradé mais non bloquant — via un SAVEPOINT,
            # sinon l'échec de l'ALTER annule tout l'import (piège base partagée).
            try:
                with transaction.atomic():
                    cursor.execute("""
                        ALTER FUNCTION public.unaccent(text)
                        IMMUTABLE
                    """)
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS
                            idx_vm_taxref_autocomplete_unaccent
                        ON taxonomie.vm_taxref_list_forautocomplete
                        USING gin (public.unaccent(search_name) gin_trgm_ops)
                    """)
            except Exception:
                pass  # unaccent non modifiable : index sans accents ignoré

            # Index sur cd_nom pour les lookups
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS
                    idx_vm_taxref_autocomplete_cd_nom
                ON taxonomie.vm_taxref_list_forautocomplete (cd_nom)
            """)

        self.stdout.write(self.style.SUCCESS(
            '  Vue matérialisée créée avec index trigramme'
        ))

    def _update_meta(self, version):
        """Met à jour les métadonnées de version."""
        ref_name = 'taxref_lite' if self.lite_mode else 'taxref'
        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM taxonomie.t_meta_taxref "
                "WHERE referential_name LIKE 'taxref%%'"
            )
            cursor.execute(
                'INSERT INTO taxonomie.t_meta_taxref '
                '(referential_name, version, update_date) '
                'VALUES (%s, %s, %s)',
                [ref_name, version, timezone.now()],
            )
        mode_label = ' (lite)' if self.lite_mode else ''
        self.stdout.write(self.style.SUCCESS(
            f'  Métadonnées mises à jour : TaxRef v{version}{mode_label}'
        ))
