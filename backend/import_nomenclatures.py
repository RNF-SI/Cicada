#!/usr/bin/env python3
"""
Script d'import des nomenclatures dans l'outil Plan de Gestion.
Ce script remplace les nomenclatures existantes par celles des fichiers SQL fournis.
"""

import os
import sys
import django
from pathlib import Path

# Configuration Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection, transaction
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def execute_insert_file(file_path, description):
    """Exécute un fichier contenant des INSERT statements."""
    logger.info(f"Exécution de {description}...")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        if not sql_content.strip():
            logger.warning(f"Fichier vide: {file_path}")
            return False
        
        with connection.cursor() as cursor:
            for statement in sql_content.split('\n'):
                statement = statement.strip()
                if statement and statement.startswith('INSERT INTO'):
                    # Remplacer les références au schéma referentiels par public
                    statement = statement.replace('INSERT INTO referentiels.', 'INSERT INTO ')
                    cursor.execute(statement)
            
        logger.info(f"✓ {description} exécuté avec succès")
        return True
        
    except Exception as e:
        logger.error(f"✗ Erreur lors de l'exécution de {description}: {e}")
        return False


def migrate_existing_data():
    """Migre les données existantes depuis le schéma referentiels vers public."""
    logger.info("Migration des données existantes...")

    try:
        with connection.cursor() as cursor:
            # Vérifier si le schéma referentiels existe
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.schemata
                WHERE schema_name = 'referentiels'
            """)
            if cursor.fetchone()[0] == 0:
                logger.info("Schéma referentiels inexistant, pas de migration nécessaire")
                logger.info("✓ Migration terminée")
                return

            # Vérifier s'il y a des données dans referentiels
            cursor.execute("SELECT COUNT(*) FROM referentiels.t_nomenclatures")
            ref_count = cursor.fetchone()[0]

            if ref_count > 0:
                logger.info(f"Migration de {ref_count} nomenclatures depuis referentiels...")
                logger.info("Migration ignorée - les données seront rechargées depuis les fichiers SQL")
            else:
                logger.info("Aucune donnée à migrer depuis referentiels")
    except Exception as e:
        # Rollback la transaction pour éviter l'état "aborted"
        connection.rollback()
        logger.info(f"Pas de migration nécessaire: {e}")

    logger.info("✓ Migration terminée")


def clear_existing_data():
    """Vide les tables existantes."""
    logger.info("Vidage des tables existantes...")
    
    with connection.cursor() as cursor:
        # Vider d'abord la table t_nomenclatures (dépendante)
        cursor.execute("TRUNCATE TABLE t_nomenclatures CASCADE;")
        
        # Puis la table bib_nomenclatures_types
        cursor.execute("TRUNCATE TABLE bib_nomenclatures_types CASCADE;")
    
    logger.info("✓ Tables vidées")


def create_schema_if_needed():
    """Crée le schéma referentiels si nécessaire pour la migration."""
    logger.info("Vérification des schémas...")
    
    with connection.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS referentiels;")
    
    logger.info("✓ Schémas prêts")


def load_data_from_files():
    """Charge les données à partir des fichiers INSERT purs."""
    
    # Chemins vers les fichiers SQL (dans le répertoire du projet)
    project_dir = Path(__file__).parent
    types_file = project_dir / "nomenclatures_data" / "types_inserts.sql"
    nomenclatures_file = project_dir / "nomenclatures_data" / "nomenclatures_inserts.sql"
    
    if not os.path.exists(types_file):
        logger.error(f"Fichier non trouvé: {types_file}")
        return False
        
    if not os.path.exists(nomenclatures_file):
        logger.error(f"Fichier non trouvé: {nomenclatures_file}")
        return False
    
    # Charger d'abord les types de nomenclatures
    success1 = execute_insert_file(types_file, "import des types de nomenclatures")
    
    # Puis les nomenclatures
    success2 = execute_insert_file(nomenclatures_file, "import des nomenclatures")
    
    return success1 and success2


def verify_import():
    """Vérifie que l'import s'est bien déroulé."""
    logger.info("Vérification de l'import...")
    
    with connection.cursor() as cursor:
        # Compter les types de nomenclatures
        cursor.execute("SELECT COUNT(*) FROM bib_nomenclatures_types")
        types_count = cursor.fetchone()[0]
        
        # Compter les nomenclatures
        cursor.execute("SELECT COUNT(*) FROM t_nomenclatures")
        nomenclatures_count = cursor.fetchone()[0]
        
        logger.info(f"✓ Types de nomenclatures importés: {types_count}")
        logger.info(f"✓ Nomenclatures importées: {nomenclatures_count}")
        
        # Afficher quelques exemples
        cursor.execute("""
            SELECT id_type, mnemonique, label 
            FROM bib_nomenclatures_types 
            LIMIT 5
        """)
        
        logger.info("Exemples de types:")
        for row in cursor.fetchall():
            logger.info(f"  - {row[0]}: {row[1]} - {row[2]}")
        
        cursor.execute("""
            SELECT id_nomenclature, mnemonique, label 
            FROM t_nomenclatures 
            LIMIT 5
        """)
        
        logger.info("Exemples de nomenclatures:")
        for row in cursor.fetchall():
            logger.info(f"  - {row[0]}: {row[1]} - {row[2]}")


def nomenclatures_already_exist():
    """Vérifie si les nomenclatures sont déjà importées."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM t_nomenclatures")
            count = cursor.fetchone()[0]
            return count > 0
    except Exception:
        return False


def main():
    """Fonction principale."""
    logger.info("=== IMPORT DES NOMENCLATURES ===")

    # Vérifier si les nomenclatures existent déjà
    if nomenclatures_already_exist():
        logger.info("✓ Les nomenclatures sont déjà importées - import ignoré")
        logger.info("  (Utilisez --force pour forcer la réimportation)")
        return

    logger.info("Ce script va importer les nomenclatures depuis les fichiers SQL.")

    try:
        # 1. Créer le schéma pour la migration (hors transaction atomique)
        create_schema_if_needed()

        # 2. Migrer les données existantes (hors transaction atomique - peut échouer)
        migrate_existing_data()

        # 3-5. Opérations critiques dans une transaction atomique
        with transaction.atomic():
            # 3. Vider les tables pour un import propre
            clear_existing_data()

            # 4. Charger les données des fichiers INSERT
            if not load_data_from_files():
                raise Exception("Échec de l'import des données")

            # 5. Vérifier l'import
            verify_import()

        logger.info("✓ Import des nomenclatures terminé avec succès!")

    except Exception as e:
        logger.error(f"✗ Erreur durante l'import: {e}")
        logger.error("La transaction a été annulée.")
        sys.exit(1)


if __name__ == "__main__":
    main()