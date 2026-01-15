#!/usr/bin/env python3
"""
Script de test pour l'API REST Plans de Gestion.
"""
import os
import sys
import django
import json
from datetime import datetime

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

import requests
from apps.users.models import Role
from apps.plans.models import PlanGestion


def get_auth_token(email='admin', password='admin'):
    """Obtenir un token JWT d'authentification."""
    url = 'http://localhost:8000/api/auth/login/'
    data = {'email': email, 'password': password}
    
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return response.json()['access']
        else:
            print(f"❌ Erreur d'authentification: {response.status_code}")
            print(response.text)
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de connexion: {e}")
        return None


def test_plans_api():
    """Tester l'API REST Plans de Gestion."""
    
    print("🔧 Test de l'API REST Plans de Gestion...")
    
    # 1. Authentification
    print("\n1️⃣ Test d'authentification...")
    token = get_auth_token()
    if not token:
        print("❌ Impossible de s'authentifier")
        return
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    print("✅ Token obtenu avec succès")
    
    # 2. Test GET /api/plans/plans/ (liste)
    print("\n2️⃣ Test de la liste des plans...")
    try:
        response = requests.get('http://localhost:8000/api/plans/plans/', headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Liste obtenue: {data['count']} plans trouvés")
            print(f"   Pagination: page {data.get('current_page', 1)}/{data.get('total_pages', 1)}")
        else:
            print(f"❌ Erreur liste: {response.status_code}")
            print(response.text)
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur de requête: {e}")
    
    # 3. Test GET avec filtres
    print("\n3️⃣ Test des filtres...")
    filters_test = [
        ('statut=valide', 'Plans validés'),
        ('gestion_partagee=true', 'Plans multi-sites'),
        ('ct88=true', 'Plans CT88'),
        ('actif_en_annee=2024', 'Plans actifs en 2024'),
    ]
    
    for filter_param, description in filters_test:
        try:
            url = f'http://localhost:8000/api/plans/plans/?{filter_param}'
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                count = response.json()['count']
                print(f"✅ {description}: {count} résultats")
            else:
                print(f"❌ Erreur filtre {filter_param}: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Erreur requête {filter_param}: {e}")
    
    # 4. Test recherche textuelle
    print("\n4️⃣ Test de la recherche...")
    try:
        response = requests.get(
            'http://localhost:8000/api/plans/plans/?search=Camargue', 
            headers=headers
        )
        if response.status_code == 200:
            count = response.json()['count']
            print(f"✅ Recherche 'Camargue': {count} résultats")
        else:
            print(f"❌ Erreur recherche: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur recherche: {e}")
    
    # 5. Test GET détail d'un plan
    print("\n5️⃣ Test du détail d'un plan...")
    
    # Récupérer l'ID du premier plan
    try:
        response = requests.get('http://localhost:8000/api/plans/plans/', headers=headers)
        if response.status_code == 200 and response.json()['count'] > 0:
            plan_id = response.json()['results'][0]['id_pg']
            
            # Tester le détail
            response = requests.get(
                f'http://localhost:8000/api/plans/plans/{plan_id}/', 
                headers=headers
            )
            if response.status_code == 200:
                plan = response.json()
                print(f"✅ Détail plan #{plan_id}: {plan['nom']}")
                print(f"   Période: {plan['periode_gestion']}")
                print(f"   Sites: {len(plan['sites'])} sites liés")
                print(f"   Fichiers: {len(plan['fichiers'])} fichiers")
                print(f"   Référents: {len(plan['referents'])} référents")
            else:
                print(f"❌ Erreur détail plan: {response.status_code}")
        else:
            print("⚠️ Aucun plan disponible pour tester le détail")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur détail: {e}")
    
    # 6. Test GeoJSON
    print("\n6️⃣ Test du format GeoJSON...")
    try:
        response = requests.get(
            'http://localhost:8000/api/plans/plans/geojson_list/', 
            headers=headers
        )
        if response.status_code == 200:
            geojson = response.json()
            print(f"✅ GeoJSON obtenu: {len(geojson['features'])} features")
            if geojson['features']:
                print(f"   Premier plan: {geojson['features'][0]['properties']['nom']}")
        else:
            print(f"❌ Erreur GeoJSON: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur GeoJSON: {e}")
    
    # 7. Test des statistiques
    print("\n7️⃣ Test des statistiques...")
    try:
        response = requests.get(
            'http://localhost:8000/api/plans/plans/stats/', 
            headers=headers
        )
        if response.status_code == 200:
            stats = response.json()
            print(f"✅ Statistiques obtenues:")
            print(f"   Total: {stats['total']} plans")
            print(f"   Gestion partagée: {stats['gestion_partagee']}")
            print(f"   Avec géométrie: {stats['avec_geometrie']}")
            print(f"   CT88: {stats['ct88']}")
            print(f"   Par statut: {stats['par_statut']}")
        else:
            print(f"❌ Erreur statistiques: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur statistiques: {e}")
    
    # 8. Test création d'un plan (si super admin)
    print("\n8️⃣ Test de création de plan...")
    try:
        # Vérifier si l'utilisateur peut créer des plans
        user = Role.objects.get(email='admin')
        if user.is_super_admin() or user.is_admin_organisme():
            plan_data = {
                'nom': f'Plan de test API - {datetime.now().strftime("%Y%m%d_%H%M%S")}',
                'id_cdr': 999999,
                'annee_debut': 2024,
                'annee_fin': 2034,
                'gestion_partagee': False,
                'ct88': False,
                'statut': 'draft',
                'version': '1.0',
                'evaluation_id': 1,  # Supposer qu'une nomenclature existe
                'redacteur_type_id': 1,  # Supposer qu'une nomenclature existe
                'redacteur_nom': 'Test API',
                'commentaire': 'Plan créé automatiquement pour tester l\'API REST',
            }
            
            response = requests.post(
                'http://localhost:8000/api/plans/plans/',
                headers=headers,
                json=plan_data
            )
            
            if response.status_code == 201:
                created_plan = response.json()
                print(f"✅ Plan créé avec succès: {created_plan['nom']}")
                print(f"   ID: {created_plan['id_pg']}")
                
                # Test de modification
                update_data = {
                    'commentaire': 'Plan modifié via API REST'
                }
                
                response = requests.patch(
                    f'http://localhost:8000/api/plans/plans/{created_plan["id_pg"]}/',
                    headers=headers,
                    json=update_data
                )
                
                if response.status_code == 200:
                    print("✅ Plan modifié avec succès")
                else:
                    print(f"❌ Erreur modification: {response.status_code}")
                
            else:
                print(f"❌ Erreur création plan: {response.status_code}")
                print(response.text)
        else:
            print("⚠️ Utilisateur sans permissions pour créer des plans")
            
    except Exception as e:
        print(f"❌ Erreur test création: {e}")
    
    # 9. Test de l'API fichiers
    print("\n9️⃣ Test de l'API fichiers...")
    try:
        response = requests.get(
            'http://localhost:8000/api/plans/fichiers/', 
            headers=headers
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API fichiers fonctionnelle: {data['count']} fichiers")
            
            # Test des filtres fichiers
            response = requests.get(
                'http://localhost:8000/api/plans/fichiers/?type_fichier=document', 
                headers=headers
            )
            if response.status_code == 200:
                count = response.json()['count']
                print(f"   Documents: {count} fichiers")
        else:
            print(f"❌ Erreur API fichiers: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur API fichiers: {e}")
    
    # 10. Test export GeoJSON
    print("\n🔟 Test export GeoJSON complet...")
    try:
        response = requests.get(
            'http://localhost:8000/api/plans/export_geojson/', 
            headers=headers
        )
        if response.status_code == 200:
            geojson = response.json()
            print(f"✅ Export GeoJSON: {len(geojson['features'])} features exportées")
        else:
            print(f"❌ Erreur export: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur export: {e}")
    
    print("\n✅ Tests API Plans de Gestion terminés!")
    
    print(f"\n📋 Résumé des endpoints testés:")
    print(f"   GET  /api/plans/plans/                    - ✅ Liste des plans")
    print(f"   GET  /api/plans/plans/?filters            - ✅ Filtres avancés")
    print(f"   GET  /api/plans/plans/?search=terme       - ✅ Recherche textuelle")
    print(f"   GET  /api/plans/plans/{{id}}/               - ✅ Détail d'un plan")
    print(f"   GET  /api/plans/plans/geojson_list/       - ✅ Liste GeoJSON")
    print(f"   GET  /api/plans/plans/stats/              - ✅ Statistiques")
    print(f"   POST /api/plans/plans/                    - ✅ Création de plan")
    print(f"   PATCH /api/plans/plans/{{id}}/             - ✅ Modification")
    print(f"   GET  /api/plans/fichiers/                 - ✅ API fichiers")
    print(f"   GET  /api/plans/export_geojson/           - ✅ Export GeoJSON")
    
    print(f"\n🔗 Accès Web:")
    print(f"   Documentation API: http://localhost:8000/api/plans/")
    print(f"   Admin Plans: http://localhost:8000/admin/plans/")


if __name__ == '__main__':
    test_plans_api()