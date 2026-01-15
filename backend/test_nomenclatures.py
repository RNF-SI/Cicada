#!/usr/bin/env python3
"""
Script de test pour vérifier les nomenclatures importées.
"""

import os
import sys
import django
from pathlib import Path

# Configuration Django
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.db import connection
from apps.core.models import TypeNomenclature, Nomenclature
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_nomenclatures():
    """Test des nomenclatures importées."""
    logger.info("=== TEST DES NOMENCLATURES ===")
    
    try:
        # Test via SQL direct
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM referentiels.bib_nomenclatures_types")
            types_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM referentiels.t_nomenclatures")
            nomenclatures_count = cursor.fetchone()[0]
            
            logger.info(f"Types de nomenclatures (SQL): {types_count}")
            logger.info(f"Nomenclatures (SQL): {nomenclatures_count}")
            
            # Afficher quelques exemples
            logger.info("\n--- Exemples de types de nomenclatures ---")
            cursor.execute("""
                SELECT id_type, mnemonique, label 
                FROM referentiels.bib_nomenclatures_types 
                ORDER BY id_type 
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                logger.info(f"  {row[0]:2d}: {row[1]:<20} - {row[2]}")
            
            logger.info("\n--- Exemples de nomenclatures ---")
            cursor.execute("""
                SELECT n.id_nomenclature, t.mnemonique as type_mnem, n.mnemonique, n.label
                FROM referentiels.t_nomenclatures n
                LEFT JOIN referentiels.bib_nomenclatures_types t ON n.id_type = t.id_type
                ORDER BY n.id_nomenclature
                LIMIT 15
            """)
            
            for row in cursor.fetchall():
                logger.info(f"  {row[0]:3d}: [{row[1]}] {row[2]:<15} - {row[3]}")
            
            # Test de quelques types spécifiques
            logger.info("\n--- Types d'espaces naturels ---")
            cursor.execute("""
                SELECT n.mnemonique, n.label
                FROM referentiels.t_nomenclatures n
                JOIN referentiels.bib_nomenclatures_types t ON n.id_type = t.id_type
                WHERE t.mnemonique = 'Espace naturel'
                ORDER BY n.id_nomenclature
            """)
            
            for row in cursor.fetchall():
                logger.info(f"  - {row[0]:<5}: {row[1]}")
                
            # Test des sources de financement
            logger.info("\n--- Sources de financement ---")
            cursor.execute("""
                SELECT n.mnemonique, n.label, n.hierarchy
                FROM referentiels.t_nomenclatures n
                JOIN referentiels.bib_nomenclatures_types t ON n.id_type = t.id_type
                WHERE t.id_type = 10
                ORDER BY n.hierarchy, n.id_nomenclature
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                hierarchy = row[2] or ""
                logger.info(f"  {hierarchy:<4}: {row[0]:<15} - {row[1]}")
            
        logger.info("\n✓ Test des nomenclatures terminé avec succès!")
        
    except Exception as e:
        logger.error(f"✗ Erreur lors du test: {e}")
        return False
    
    return True


if __name__ == "__main__":
    test_nomenclatures()