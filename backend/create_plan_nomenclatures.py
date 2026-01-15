#!/usr/bin/env python3
"""
Script pour créer les nomenclatures nécessaires aux Plans de Gestion.
"""
import os
import sys
import django

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.core.models import TypeNomenclature, Nomenclature


def create_plan_nomenclatures():
    """Créer les nomenclatures pour les Plans de Gestion."""
    
    print("🔧 Création des nomenclatures pour les Plans de Gestion...")
    
    # 1. Type d'évaluation des plans
    type_evaluation, created = TypeNomenclature.objects.get_or_create(
        mnemonique='PLAN_EVALUATION',
        defaults={
            'label_default': 'Type d\'évaluation de plan de gestion',
            'label_fr': 'Type d\'évaluation de plan de gestion',
            'definition_default': 'Classification des types d\'évaluation des plans de gestion',
            'definition_fr': 'Classification des types d\'évaluation des plans de gestion',
            'source': 'RNF',
            'statut': 'Actif'
        }
    )
    if created:
        print(f"✅ TypeNomenclature créé: {type_evaluation.label_fr}")
    
    # Nomenclatures pour le type d'évaluation
    evaluations = [
        ('EVAL_INITIALE', 'Évaluation initiale', 'Évaluation réalisée avant la mise en œuvre du plan'),
        ('EVAL_INTERMEDIAIRE', 'Évaluation intermédiaire', 'Évaluation réalisée en cours de mise en œuvre'),
        ('EVAL_FINALE', 'Évaluation finale', 'Évaluation réalisée en fin de période du plan'),
        ('EVAL_BILAN', 'Bilan d\'application', 'Bilan global de l\'application du plan'),
        ('EVAL_AUTRE', 'Autre évaluation', 'Autre type d\'évaluation'),
    ]
    
    for code, label, definition in evaluations:
        nom, created = Nomenclature.objects.get_or_create(
            id_type=type_evaluation,
            cd_nomenclature=code,
            defaults={
                'label_default': label,
                'label_fr': label,
                'definition_default': definition,
                'definition_fr': definition,
                'active': True
            }
        )
        if created:
            print(f"  ➕ Nomenclature créée: {nom.label_fr}")
    
    # 2. Type de rédacteur des plans
    type_redacteur, created = TypeNomenclature.objects.get_or_create(
        mnemonique='PLAN_REDACTEUR_TYPE',
        defaults={
            'label_default': 'Type de rédacteur de plan de gestion',
            'label_fr': 'Type de rédacteur de plan de gestion',
            'definition_default': 'Classification des types de rédacteurs des plans de gestion',
            'definition_fr': 'Classification des types de rédacteurs des plans de gestion',
            'source': 'RNF',
            'statut': 'Actif'
        }
    )
    if created:
        print(f"✅ TypeNomenclature créé: {type_redacteur.label_fr}")
    
    # Nomenclatures pour le type de rédacteur
    redacteurs = [
        ('RED_GESTIONNAIRE', 'Gestionnaire', 'Plan rédigé par l\'organisme gestionnaire'),
        ('RED_BUREAU_ETUDE', 'Bureau d\'étude', 'Plan rédigé par un bureau d\'étude externe'),
        ('RED_CONSULTANT', 'Consultant indépendant', 'Plan rédigé par un consultant indépendant'),
        ('RED_UNIVERSITE', 'Université/Recherche', 'Plan rédigé par une institution universitaire ou de recherche'),
        ('RED_COLLECTIVITE', 'Collectivité territoriale', 'Plan rédigé par une collectivité territoriale'),
        ('RED_MIXTE', 'Rédaction mixte', 'Plan rédigé conjointement par plusieurs types d\'acteurs'),
        ('RED_AUTRE', 'Autre', 'Autre type de rédacteur'),
    ]
    
    for code, label, definition in redacteurs:
        nom, created = Nomenclature.objects.get_or_create(
            id_type=type_redacteur,
            cd_nomenclature=code,
            defaults={
                'label_default': label,
                'label_fr': label,
                'definition_default': definition,
                'definition_fr': definition,
                'active': True
            }
        )
        if created:
            print(f"  ➕ Nomenclature créée: {nom.label_fr}")
    
    # 3. Statuts de validation des plans (optionnel, pour workflow avancé)
    type_statut, created = TypeNomenclature.objects.get_or_create(
        mnemonique='PLAN_STATUT_VALIDATION',
        defaults={
            'label_default': 'Statut de validation du plan de gestion',
            'label_fr': 'Statut de validation du plan de gestion',
            'definition_default': 'Statuts du workflow de validation des plans de gestion',
            'definition_fr': 'Statuts du workflow de validation des plans de gestion',
            'source': 'RNF',
            'statut': 'Actif'
        }
    )
    if created:
        print(f"✅ TypeNomenclature créé: {type_statut.label_fr}")
    
    # Nomenclatures pour le statut de validation
    statuts = [
        ('STATUT_DRAFT', 'Brouillon', 'Plan en cours de rédaction'),
        ('STATUT_ATTENTE_VALIDATION', 'En attente de validation', 'Plan soumis pour validation'),
        ('STATUT_VALIDE', 'Validé', 'Plan validé et approuvé'),
        ('STATUT_PUBLIE', 'Publié', 'Plan publié et en vigueur'),
        ('STATUT_ARCHIVE', 'Archivé', 'Plan archivé (fin de période ou remplacé)'),
        ('STATUT_REFUSE', 'Refusé', 'Plan refusé lors de la validation'),
    ]
    
    for code, label, definition in statuts:
        nom, created = Nomenclature.objects.get_or_create(
            id_type=type_statut,
            cd_nomenclature=code,
            defaults={
                'label_default': label,
                'label_fr': label,
                'definition_default': definition,
                'definition_fr': definition,
                'active': True
            }
        )
        if created:
            print(f"  ➕ Nomenclature créée: {nom.label_fr}")
    
    print("✅ Nomenclatures pour les Plans de Gestion créées avec succès!")
    print("\nRésumé:")
    print(f"- Types d'évaluation: {Nomenclature.objects.filter(id_type__mnemonique='PLAN_EVALUATION').count()}")
    print(f"- Types de rédacteur: {Nomenclature.objects.filter(id_type__mnemonique='PLAN_REDACTEUR_TYPE').count()}")
    print(f"- Statuts de validation: {Nomenclature.objects.filter(id_type__mnemonique='PLAN_STATUT_VALIDATION').count()}")


if __name__ == '__main__':
    create_plan_nomenclatures()