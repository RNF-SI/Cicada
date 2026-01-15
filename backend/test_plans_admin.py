#!/usr/bin/env python3
"""
Script de test pour l'interface admin des Plans de Gestion.
"""
import os
import sys
import django

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.plans.models import PlanGestion, CorSitePg, CorPgFichier
from apps.users.models import Role, Site
from apps.core.models import Nomenclature


def test_plans_admin():
    """Tester l'interface admin des Plans de Gestion."""
    
    print("🔧 Test de l'interface admin des Plans de Gestion...")
    
    # Test 1: Vérifier que les modèles sont accessibles
    print(f"✅ Plans de Gestion: {PlanGestion.objects.count()}")
    print(f"✅ Relations Site-Plan: {CorSitePg.objects.count()}")
    print(f"✅ Fichiers: {CorPgFichier.objects.count()}")
    
    # Test 2: Affichage détaillé des plans
    print("\n📋 Détail des Plans de Gestion:")
    for plan in PlanGestion.objects.all():
        print(f"\n🔹 {plan.nom}")
        print(f"   Statut: {plan.get_statut_display()}")
        print(f"   Période: {plan.get_periode_gestion()}")
        print(f"   Créateur: {plan.id_utilisateur_ajout}")
        print(f"   Sites associés: {plan.sites.count()}")
        
        # Afficher les sites
        for cor_site_pg in plan.sites.select_related('site'):
            print(f"     - {cor_site_pg.site.nom_site} (rang {cor_site_pg.rang or 'N/A'})")
        
        # Afficher les fichiers
        fichiers = plan.fichiers.all()
        if fichiers:
            print(f"   Fichiers: {fichiers.count()}")
            for fichier in fichiers:
                print(f"     - {fichier.nom_fichier} ({fichier.get_type_fichier_display()})")
        
        # Afficher les référents
        referents = plan.referents.all()
        if referents:
            print(f"   Référents: {', '.join([str(r) for r in referents])}")
    
    # Test 3: Vérifier les nomenclatures
    print("\n📚 Nomenclatures disponibles:")
    types_eval = Nomenclature.objects.filter(id_type__mnemonique='PLAN_EVALUATION')
    print(f"   Types d'évaluation: {types_eval.count()}")
    for nom in types_eval:
        print(f"     - {nom.label_fr}")
    
    types_red = Nomenclature.objects.filter(id_type__mnemonique='PLAN_REDACTEUR_TYPE')
    print(f"   Types de rédacteur: {types_red.count()}")
    for nom in types_red:
        print(f"     - {nom.label_fr}")
    
    # Test 4: Vérifier les méthodes des modèles
    print("\n🧪 Test des méthodes des modèles:")
    plan = PlanGestion.objects.first()
    if plan:
        print(f"   Plan test: {plan.nom}")
        print(f"   Est multi-sites: {plan.is_multi_sites()}")
        print(f"   Organismes gestionnaires: {len(plan.get_organismes_gestionnaires())}")
        print(f"   Sites liés: {len(plan.get_sites())}")
    
    # Test 5: Vérifier les fichiers
    fichier = CorPgFichier.objects.first()
    if fichier:
        print(f"   Fichier test: {fichier.nom_fichier}")
        print(f"   Taille lisible: {fichier.get_file_size_human()}")
        print(f"   Est une image: {fichier.is_image()}")
        print(f"   Est un document: {fichier.is_document()}")
    
    print("\n✅ Tests terminés avec succès!")
    
    print(f"\n🌐 Accès Web:")
    print(f"   Admin général: http://localhost:8000/admin/")
    print(f"   Plans de Gestion: http://localhost:8000/admin/plans/plangestion/")
    print(f"   Relations Site-Plan: http://localhost:8000/admin/plans/corsitepg/")
    print(f"   Fichiers: http://localhost:8000/admin/plans/corpgfichier/")
    print(f"")
    print(f"🔑 Connexion admin: admin / admin")


if __name__ == '__main__':
    test_plans_admin()