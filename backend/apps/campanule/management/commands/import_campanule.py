"""
Commande Django pour importer le référentiel CAMPanule.

CAMPanule = CATalogue des Méthodes et des Protocoles de collecte
de données naturalistes (INPN / PatriNat).

Les fichiers CSV sont embarqués dans le projet (apps/campanule/data/).
Encodage : UTF-8 (convertis depuis CP1252), délimiteur ';'.

Usage:
    python manage.py import_campanule              # Import standard
    python manage.py import_campanule --force      # Force le rechargement
"""

import csv
import io
import logging
import os

from django.core.management.base import BaseCommand
from django.db import connection, transaction

logger = logging.getLogger(__name__)

# Répertoire contenant les fichiers CSV embarqués
DATA_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    '..', '..', 'data',
)

# Mapping des fichiers CSV -> tables SQL
# Clé = nom du fichier CSV (sans extension)
# csv_to_db = { colonne_CSV -> colonne_DB }
CAMPANULE_FILES = {
    'ATTRIBUTS': {
        'table': 'ref_campanule.attributs',
        'csv_to_db': {
            'CD_ATTRIBUT': 'cd_attribut',
            'LB_ATTRIBUT': 'lb_attribut',
            'CATEGORIE_ATTRIBUT': 'categorie_attribut',
        },
    },
    'DOCS_WEB': {
        'table': 'ref_campanule.docs_web',
        'csv_to_db': {
            'CD_DOC': 'cd_doc',
            'REFERENCE': 'reference',
        },
    },
    'PROTOCOLES': {
        'table': 'ref_campanule.protocoles',
        'csv_to_db': {
            'CD_PROTOCOLE': 'cd_protocole',
            'LB_PROTOCOLE_COURT': 'lb_protocole_court',
            'CD_PROT_METIER': 'cd_prot_metier',
            'CODE_v0_9': 'code_v0_9',
            'CD_PROT_REF': 'cd_prot_ref',
            'LB_PROTOCOLE_COMPLET': 'lb_protocole_complet',
            'LB_PROTOCOLE_EN': 'lb_protocole_en',
            'DATE_PUBLI': 'date_publi',
            'VERSION': 'version',
            'OBSOLETE': 'obsolete',
            'PROT_AUTEUR': 'prot_auteur',
            'URL_PERM': 'url_perm',
            'URL': 'url',
            'URL_COMPLEMENTAIRE': 'url_complementaire',
            'DESCRIPTION': 'description',
            'DESCR_CIBLE_PROT': 'descr_cible_prot',
            'DESCR_OBJECTIF_PROT': 'descr_objectif_prot',
            'CIBLE': 'cible',
            'ECHELLE_RESTIT': 'echelle_restit',
            'SAISIE': 'saisie',
            'BIOLOGIE': 'biologie',
            'ABIOTIQUE': 'abiotique',
            'NATURE_DONNEES': 'nature_donnees',
            'ANALYSE_REFERENCE': 'analyse_reference',
            'GUIDE_SINP_DONNEES': 'guide_sinp_donnees',
            'NORME': 'norme',
            'INDICATEUR': 'indicateur',
            'CATEGORIE_PROT': 'categorie_prot',
            'UUID': 'uuid',
            'GELE': 'gele',
        },
    },
    'METHODES': {
        'table': 'ref_campanule.methodes',
        'csv_to_db': {
            'CD_METHODE': 'cd_methode',
            'CD_METH_METIER': 'cd_meth_metier',
            'LB_METHODE_COURT': 'lb_methode_court',
            'LB_METHODE_COMPLET': 'lb_methode_complet',
            'LB_METHODE_EN': 'lb_methode_en',
            'URL_PERM': 'url_perm',
            'URL_COMPLEMENTAIRE': 'url_complementaire',
            'DESCR_METHODE': 'descr_methode',
            'EXEMPLES_CIBLE_METH': 'exemples_cible_meth',
            'DESCR_OBJECTIF_METH': 'descr_objectif_meth',
            'NATURE_DONNEES': 'nature_donnees',
            'ANALYSE_REFERENCE': 'analyse_reference',
            'UUID': 'uuid',
            'GELE': 'gele',
        },
    },
    'TECHNIQUES': {
        'table': 'ref_campanule.techniques',
        'csv_to_db': {
            'CD_TECHNIQUE': 'cd_technique',
            'LB_TECHNIQUE_FR': 'lb_technique_fr',
            'NIVEAU': 'niveau',
            'CD_TECH_METIER': 'cd_tech_metier',
            'CD_TECH_SUP': 'cd_tech_sup',
            'LB_TECH_COMPLET_FR': 'lb_tech_complet_fr',
            'LB_TECHNIQUE_EN': 'lb_technique_en',
            'CATEGORIE_TECH': 'categorie_tech',
            'CIBLE': 'cible',
            'DESCR_TECHNIQUE': 'descr_technique',
            'DESCR_CIBLE_TECH': 'descr_cible_tech',
            'ACTIVE': 'active',
            'DERANGEMENT': 'derangement',
            'PRELEVEMENT': 'prelevement',
            'COMM_COLLECTE': 'comm_collecte',
            'CORRESP_OCCTAX': 'corresp_occtax',
            'CORRESP_SOH': 'corresp_soh',
            'TAG_TAX': 'tag_tax',
            'TAG_HAB': 'tag_hab',
            'UUID': 'uuid',
            'GELE': 'gele',
        },
    },
    'PROT_ECHANTILLONNAGE': {
        'table': 'ref_campanule.prot_echantillonnage',
        'csv_to_db': {
            'CD_PROT_ECHANTILLONNAGE': 'cd_prot_echantillonnage',
            'CD_PROTOCOLE': 'cd_protocole',
            'UNITE': 'unite',
            'NB_UNITE': 'nb_unite',
            'DUREE': 'duree',
            'TAILLE': 'taille',
            'PASSAGES_AN': 'passages_an',
            'PERIODE_AN': 'periode_an',
            'PLAN_ECH': 'plan_ech',
            'COMMENTAIRE': 'commentaire',
            'NIVEAU': 'niveau',
        },
    },
    # Tables de correspondance
    'PROT_ATTRIBUTS_REL': {
        'table': 'ref_campanule.prot_attributs_rel',
        'csv_to_db': {
            'CD_PROTOCOLE': 'cd_protocole',
            'CD_ATTRIBUT': 'cd_attribut',
        },
        'has_id': True,
    },
    'PROT_BIBLIO_REL': {
        'table': 'ref_campanule.prot_biblio_rel',
        'csv_to_db': {
            'CD_PROTOCOLE': 'cd_protocole',
            'CD_DOC': 'cd_doc',
            'PAGE': 'page',
        },
        'has_id': True,
    },
    'PROT_METH_REL': {
        'table': 'ref_campanule.prot_meth_rel',
        'csv_to_db': {
            'CD_PROTOCOLE': 'cd_protocole',
            'CD_METHODE': 'cd_methode',
            'COMMENTAIRE': 'commentaire',
        },
        'has_id': True,
    },
    'PROT_TECH_REL': {
        'table': 'ref_campanule.prot_tech_rel',
        'csv_to_db': {
            'CD_PROTOCOLE': 'cd_protocole',
            'CD_TECHNIQUE': 'cd_technique',
            'COMMENTAIRE': 'commentaire',
        },
        'has_id': True,
    },
    'METH_ATTRIBUTS_REL': {
        'table': 'ref_campanule.meth_attributs_rel',
        'csv_to_db': {
            'CD_METHODE': 'cd_methode',
            'CD_ATTRIBUT': 'cd_attribut',
        },
        'has_id': True,
    },
    'METH_BIBLIO_REL': {
        'table': 'ref_campanule.meth_biblio_rel',
        'csv_to_db': {
            'CD_METHODE': 'cd_methode',
            'CD_DOC': 'cd_doc',
            'PAGE': 'page',
        },
        'has_id': True,
    },
    'TECH_ATTRIBUTS_REL': {
        'table': 'ref_campanule.tech_attributs_rel',
        'csv_to_db': {
            'CD_TECHNIQUE': 'cd_technique',
            'CD_ATTRIBUT': 'cd_attribut',
        },
        'has_id': True,
    },
    'TECH_BIBLIO_REL': {
        'table': 'ref_campanule.tech_biblio_rel',
        'csv_to_db': {
            'CD_TECHNIQUE': 'cd_technique',
            'CD_DOC': 'cd_doc',
            'PAGE': 'page',
        },
        'has_id': True,
    },
}

# Ordre de chargement (tables sans FK d'abord)
LOAD_ORDER = [
    # Tables indépendantes
    'ATTRIBUTS',
    'DOCS_WEB',
    # Tables principales
    'PROTOCOLES',
    'METHODES',
    'TECHNIQUES',
    # Tables complémentaires
    'PROT_ECHANTILLONNAGE',
    # Tables de correspondance
    'PROT_ATTRIBUTS_REL',
    'PROT_BIBLIO_REL',
    'PROT_METH_REL',
    'PROT_TECH_REL',
    'METH_ATTRIBUTS_REL',
    'METH_BIBLIO_REL',
    'TECH_ATTRIBUTS_REL',
    'TECH_BIBLIO_REL',
]


class Command(BaseCommand):
    help = 'Importe le référentiel CAMPanule (protocoles, méthodes, techniques)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force le rechargement complet',
        )

    def handle(self, *args, **options):
        force = options['force']

        self.stdout.write(self.style.MIGRATE_HEADING(
            '=== IMPORT CAMPANULE ==='
        ))

        # Vérifier si déjà installé
        if not force and self._is_installed():
            # Le catalogue INPN est déjà chargé : on s'assure au minimum que les
            # protocoles standardisés MhéO (#565) sont présents, sans recharger
            # tout le référentiel (idempotent, appliqué au démarrage suivant).
            if not self._mheo_installed():
                with transaction.atomic():
                    self._load_mheo()
                    self._generate_autocomplete_data()
                self.stdout.write(self.style.SUCCESS(
                    'Protocoles standardisés MhéO ajoutés.'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    'CAMPanule est déjà installé. '
                    'Utilisez --force pour forcer le rechargement.'
                ))
            return

        data_dir = os.path.normpath(DATA_DIR)
        if not os.path.isdir(data_dir):
            self.stderr.write(self.style.ERROR(
                f'Répertoire de données introuvable : {data_dir}'
            ))
            return

        with transaction.atomic():
            self._ensure_schema()
            self._load_all_csv(data_dir)
            self._load_mheo()
            self._generate_autocomplete_data()

        self.stdout.write(self.style.SUCCESS(
            'Import CAMPanule terminé avec succès!'
        ))

    def _is_installed(self):
        """Vérifie si CAMPanule est déjà importé."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    'SELECT COUNT(*) FROM ref_campanule.protocoles'
                )
                return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def _mheo_installed(self):
        """Vérifie si les protocoles standardisés MhéO sont déjà présents."""
        from apps.campanule.data_mheo import MHEO_BASE
        from apps.campanule.models import CampanuleProtocole
        return CampanuleProtocole.objects.filter(
            cd_protocole__gt=MHEO_BASE
        ).exists()

    def _load_mheo(self):
        """
        Charge les protocoles standardisés MhéO (#565) via l'ORM.

        Ces protocoles ne sont pas dans le catalogue INPN : ils sont ajoutés en
        plus des lignes issues des CSV, dans une plage de codes réservée
        (>= MHEO_BASE). L'opération est idempotente : les éventuelles lignes
        MhéO existantes sont d'abord supprimées.
        """
        from apps.campanule.data_mheo import MHEO_BASE, MHEO_PROTOCOLES
        from apps.campanule.models import (
            CampanuleProtocole,
            CampanuleProtEchantillonnage,
            CampanuleMethode,
            CampanuleTechnique,
            CampanuleProtMethRel,
            CampanuleProtTechRel,
        )

        self.stdout.write('  Chargement des protocoles standardisés MhéO ...')

        # Nettoyage idempotent de la plage MhéO.
        CampanuleProtTechRel.objects.filter(
            cd_protocole__gt=MHEO_BASE).delete()
        CampanuleProtMethRel.objects.filter(
            cd_protocole__gt=MHEO_BASE).delete()
        CampanuleProtEchantillonnage.objects.filter(
            cd_protocole__gt=MHEO_BASE).delete()
        CampanuleTechnique.objects.filter(
            cd_technique__gt=MHEO_BASE).delete()
        CampanuleMethode.objects.filter(
            cd_methode__gt=MHEO_BASE).delete()
        CampanuleProtocole.objects.filter(
            cd_protocole__gt=MHEO_BASE).delete()

        # Codes séquentiels pour les méthodes / techniques / échantillonnages.
        next_methode = MHEO_BASE + 1
        next_technique = MHEO_BASE + 1
        next_ech = MHEO_BASE + 1

        for proto in MHEO_PROTOCOLES:
            cd_protocole = proto['cd_protocole']
            CampanuleProtocole.objects.create(
                cd_protocole=cd_protocole, **proto['fields']
            )

            ech = proto.get('echantillonnage')
            if ech:
                CampanuleProtEchantillonnage.objects.create(
                    cd_prot_echantillonnage=next_ech,
                    cd_protocole=cd_protocole,
                    **ech,
                )
                next_ech += 1

            methode = proto.get('methode')
            if methode:
                CampanuleMethode.objects.create(
                    cd_methode=next_methode,
                    lb_methode_court='Méthodes de collecte',
                    descr_methode=methode,
                )
                CampanuleProtMethRel.objects.create(
                    cd_protocole=cd_protocole,
                    cd_methode=next_methode,
                )
                next_methode += 1

            for lb_technique, descr in proto.get('techniques', []):
                CampanuleTechnique.objects.create(
                    cd_technique=next_technique,
                    lb_technique_fr=lb_technique,
                    descr_technique=descr,
                )
                CampanuleProtTechRel.objects.create(
                    cd_protocole=cd_protocole,
                    cd_technique=next_technique,
                )
                next_technique += 1

        self.stdout.write(self.style.SUCCESS(
            f'    {len(MHEO_PROTOCOLES)} protocoles MhéO chargés'
        ))

    def _ensure_schema(self):
        """S'assure que le schema existe."""
        with connection.cursor() as cursor:
            cursor.execute('CREATE SCHEMA IF NOT EXISTS ref_campanule')
            cursor.execute(
                'CREATE EXTENSION IF NOT EXISTS pg_trgm SCHEMA public'
            )
            cursor.execute(
                'CREATE EXTENSION IF NOT EXISTS unaccent SCHEMA public'
            )

    def _load_all_csv(self, data_dir):
        """Charge tous les fichiers CSV dans l'ordre."""
        for key in LOAD_ORDER:
            csv_path = os.path.join(data_dir, f'{key}.csv')
            if not os.path.exists(csv_path):
                self.stdout.write(self.style.WARNING(
                    f'  Fichier {key}.csv non trouvé, ignoré'
                ))
                continue

            file_info = CAMPANULE_FILES[key]
            self._load_single_csv(
                csv_path,
                file_info['table'],
                file_info['csv_to_db'],
                has_id=file_info.get('has_id', False),
                key=key,
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

        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f, delimiter=';')
            writer = csv.writer(output, delimiter='\t')
            # En-tête avec les noms de colonnes DB
            writer.writerow(db_columns)

            for row in reader:
                values = []
                for csv_col in csv_columns:
                    val = row.get(csv_col, '')
                    if val is None:
                        val = ''
                    # Nettoyer les retours à la ligne dans les valeurs
                    val = val.replace('\r\n', ' ').replace('\r', ' ')
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
        Génère la table d'autocomplete pour les protocoles.

        Combine le libellé court, complet et la description pour la
        recherche floue par trigramme.
        """
        self.stdout.write('  Génération des données autocomplete...')
        with connection.cursor() as cursor:
            cursor.execute(
                'TRUNCATE TABLE ref_campanule.autocomplete_protocole CASCADE'
            )

            cursor.execute("""
                INSERT INTO ref_campanule.autocomplete_protocole
                    (cd_protocole, search_name, lb_protocole_court,
                     lb_protocole_complet, description, cible,
                     categorie_prot, prot_auteur, obsolete)
                SELECT
                    p.cd_protocole,
                    COALESCE(p.lb_protocole_court, '') || ' ' ||
                    COALESCE(p.lb_protocole_complet, '') || ' ' ||
                    COALESCE(p.prot_auteur, '') || ' ' ||
                    COALESCE(p.cible, '') || ' ' ||
                    COALESCE(p.descr_cible_prot, '') AS search_name,
                    p.lb_protocole_court,
                    p.lb_protocole_complet,
                    p.description,
                    p.cible,
                    p.categorie_prot,
                    p.prot_auteur,
                    p.obsolete
                FROM ref_campanule.protocoles p
                WHERE COALESCE(p.obsolete, 'false') != 'true'
            """)

            # Index trigramme pour l'autocomplete
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_autocomplete_prot_trgm
                ON ref_campanule.autocomplete_protocole
                USING gin (search_name gin_trgm_ops)
            """)
            # Index unaccent pour recherche sans accents
            try:
                cursor.execute("""
                    ALTER FUNCTION public.unaccent(text)
                    IMMUTABLE
                """)
            except Exception:
                pass  # Déjà IMMUTABLE
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_autocomplete_prot_unaccent
                ON ref_campanule.autocomplete_protocole
                USING gin (public.unaccent(search_name) gin_trgm_ops)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_autocomplete_prot_cible
                ON ref_campanule.autocomplete_protocole (cible)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_autocomplete_prot_categorie
                ON ref_campanule.autocomplete_protocole (categorie_prot)
            """)

            cursor.execute(
                'SELECT COUNT(*) FROM ref_campanule.autocomplete_protocole'
            )
            count = cursor.fetchone()[0]

        self.stdout.write(self.style.SUCCESS(
            f'  {count} protocoles dans la table autocomplete'
        ))
