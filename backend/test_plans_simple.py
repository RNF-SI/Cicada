#!/usr/bin/env python3
"""
Script de test simple pour l'API Plans de Gestion (sans requests).
"""
import os
import sys
import django
from datetime import datetime

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.plans.models import PlanGestion, CorSitePg, CorPgFichier
from apps.users.models import Role, Site
from apps.core.models import Nomenclature


def test_plans_models():
    """Test des modèles Plans de Gestion."""
    
    print("🔧 Test des modèles Plans de Gestion...")
    
    # 1. Vérifier les données existantes
    print(f"\n📊 État actuel:")
    print(f"   Plans de Gestion: {PlanGestion.objects.count()}")
    print(f"   Relations Site-Plan: {CorSitePg.objects.count()}")
    print(f"   Fichiers: {CorPgFichier.objects.count()}")
    
    # 2. Test création simple d'un plan
    try:
        admin_user = Role.objects.get(email='admin')
        print(f"✅ Utilisateur admin trouvé: {admin_user}")
        
        # Récupérer des nomenclatures
        try:
            eval_nomenclature = Nomenclature.objects.filter(
                id_type__mnemonique='PLAN_EVALUATION'
            ).first()
            red_nomenclature = Nomenclature.objects.filter(
                id_type__mnemonique='PLAN_REDACTEUR_TYPE'
            ).first()
            
            if eval_nomenclature and red_nomenclature:
                print(f"✅ Nomenclatures trouvées: {eval_nomenclature}, {red_nomenclature}")
                
                # Créer un plan de test
                plan_test = PlanGestion.objects.create(
                    nom=f"Plan API Test - {datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    id_cdr=999999,
                    annee_debut=2024,
                    annee_fin=2034,
                    gestion_partagee=False,
                    ct88=False,
                    statut='draft',
                    version='1',
                    id_evaluation=eval_nomenclature,
                    id_redacteur_type=red_nomenclature,
                    redacteur_nom='Test API',
                    commentaire='Plan créé pour tester l\'API',
                    id_utilisateur_ajout=admin_user,
                    id_utilisateur_maj=admin_user
                )
                
                print(f"✅ Plan créé: {plan_test.nom}")
                print(f"   ID: {plan_test.id_pg}")
                print(f"   Période: {plan_test.get_periode_gestion()}")
                print(f"   Statut: {plan_test.get_statut_display()}")
                
                # Test des méthodes du modèle
                print(f"   Est multi-sites: {plan_test.is_multi_sites()}")
                print(f"   Organismes gestionnaires: {plan_test.get_organismes_gestionnaires()}")
                
            else:
                print("❌ Nomenclatures manquantes")
                
        except Exception as e:
            print(f"❌ Erreur nomenclatures: {e}")
    
    except Role.DoesNotExist:
        print("❌ Utilisateur admin non trouvé")
    except Exception as e:
        print(f"❌ Erreur création plan: {e}")
    
    # 3. Test assignation d'un site
    try:
        site = Site.objects.first()
        if site and plan_test:
            cor_site_pg = CorSitePg.objects.create(
                plan_de_gestion=plan_test,
                site=site,
                rang=1,
                commentaire='Test assignation API'
            )
            print(f"✅ Site assigné: {site.nom_site} → {plan_test.nom}")
        
    except Exception as e:
        print(f"❌ Erreur assignation site: {e}")
    
    # 4. Vérifier les filtres et requêtes
    print(f"\n🔍 Test des requêtes:")
    
    # Plans par statut
    for statut, label in PlanGestion.STATUT_CHOICES:
        count = PlanGestion.objects.filter(statut=statut).count()
        if count > 0:
            print(f"   {label}: {count} plans")
    
    # Plans actifs cette année
    current_year = datetime.now().year
    plans_actifs = PlanGestion.objects.filter(
        annee_debut__lte=current_year,
        annee_fin__gte=current_year
    ).count()
    print(f"   Plans actifs en {current_year}: {plans_actifs}")
    
    # Plans avec géométrie
    plans_geo = PlanGestion.objects.filter(geometrie__isnull=False).count()
    print(f"   Plans avec géométrie: {plans_geo}")
    
    print(f"\n✅ Test des modèles terminé!")


def test_api_urls():
    """Test basique que les URLs sont bien configurées."""
    print(f"\n🔗 Test des URLs API...")
    
    try:
        from django.urls import reverse
        from django.test import Client
        from django.contrib.auth import authenticate
        
        # Créer un client de test
        client = Client()
        
        # Test d'authentification
        user = Role.objects.get(email='admin')
        if user:
            # Simuler une requête authentifiée serait complexe avec JWT
            print(f"✅ Utilisateur pour les tests: {user}")
            print(f"   Permissions: Super Admin: {user.is_super_admin()}")
        
        # Vérifier que les patterns URL sont valides
        from apps.plans.urls import urlpatterns
        print(f"✅ URLs Plans configurées: {len(urlpatterns)} routes")
        
        # Test simple d'accès (sans auth, devrait être refusé)
        try:
            response = client.get('/api/plans/plans/')
            print(f"   GET /api/plans/plans/ → {response.status_code} (normal: 401/403 sans auth)")
        except Exception as e:
            print(f"   Erreur route plans: {e}")
    
    except Exception as e:
        print(f"❌ Erreur test URLs: {e}")


if __name__ == '__main__':
    test_plans_models()
    test_api_urls()
    
    print(f"\n📋 API REST Plans de Gestion implémentée!")
    print(f"📋 Endpoints disponibles:")
    print(f"   GET    /api/plans/plans/                    - Liste des plans")
    print(f"   POST   /api/plans/plans/                    - Créer un plan")
    print(f"   GET    /api/plans/plans/{{id}}/               - Détail d'un plan")
    print(f"   PATCH  /api/plans/plans/{{id}}/               - Modifier un plan")
    print(f"   DELETE /api/plans/plans/{{id}}/               - Supprimer un plan")
    print(f"   GET    /api/plans/plans/geojson_list/       - Liste GeoJSON")
    print(f"   GET    /api/plans/plans/{{id}}/geojson/       - GeoJSON individuel")
    print(f"   POST   /api/plans/plans/{{id}}/assign_site/   - Assigner un site")
    print(f"   DELETE /api/plans/plans/{{id}}/remove_site/   - Retirer un site")
    print(f"   POST   /api/plans/plans/{{id}}/assign_referent/ - Assigner référent")
    print(f"   GET    /api/plans/plans/stats/              - Statistiques")
    print(f"   GET    /api/plans/fichiers/                 - Liste des fichiers")
    print(f"   POST   /api/plans/fichiers/                 - Upload de fichier")
    print(f"   GET    /api/plans/fichiers/{{id}}/download/   - Télécharger fichier")
    print(f"   GET    /api/plans/export_geojson/           - Export GeoJSON complet")
    print(f"\n🔑 Authentification: Bearer Token JWT requis")
    print(f"🔗 Admin: http://localhost:8000/admin/plans/")