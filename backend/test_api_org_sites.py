#!/usr/bin/env python3
"""
Script de test pour l'API REST des organismes et sites.
Usage: python test_api_org_sites.py
"""
import os
import sys
import django
import requests
import json
from datetime import datetime

# Configuration de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.users.models import Role, BibOrganismes, Site

BASE_URL = "http://localhost:8000/api/users"


class APIOrganismesSitesTester:
    """Classe pour tester l'API des organismes et sites."""
    
    def __init__(self):
        self.admin_token = None
        self.user_token = None
        self.test_organisme_id = None
        self.test_site_id = None
    
    def get_auth_token(self, email="admin", password="admin"):
        """Obtient un token d'authentification."""
        response = requests.post(
            f"http://localhost:8000/api/auth/login/",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            return response.json()['access']
        return None
    
    def setup_tokens(self):
        """Configure les tokens pour les tests."""
        print("🔐 Configuration des tokens d'authentification...")
        
        self.admin_token = self.get_auth_token("admin", "admin")
        if not self.admin_token:
            print("❌ Impossible de se connecter en tant qu'admin")
            sys.exit(1)
        print("✅ Token admin obtenu")
        
        self.user_token = self.get_auth_token("marie.dupont@rnf.fr", "password123")
        if self.user_token:
            print("✅ Token utilisateur obtenu")
        else:
            print("⚠️  Token utilisateur non disponible")
        
        print()
    
    def make_request(self, method, endpoint, token=None, data=None, expected_status=200):
        """Fait une requête HTTP avec gestion d'erreurs."""
        url = f"{BASE_URL}{endpoint}"
        headers = {}
        
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        if data:
            headers["Content-Type"] = "application/json"
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=headers)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == 'PATCH':
                response = requests.patch(url, headers=headers, json=data)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Méthode non supportée: {method}")
            
            success = response.status_code == expected_status
            emoji = "✅" if success else "❌"
            
            print(f"   {emoji} {method.upper()} {endpoint}")
            print(f"      Status: {response.status_code} (attendu: {expected_status})")
            
            if success and response.content and response.status_code != 204:
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict):
                        if 'results' in response_data:
                            print(f"      Résultats: {len(response_data['results'])} éléments")
                        elif 'nom_organisme' in response_data:
                            print(f"      Organisme: {response_data['nom_organisme']}")
                        elif 'nom_site' in response_data:
                            print(f"      Site: {response_data['nom_site']}")
                        elif 'message' in response_data:
                            print(f"      Message: {response_data['message']}")
                except:
                    pass
            elif not success:
                print(f"      Erreur: {response.text[:100]}...")
            
            print()
            return response, success
            
        except Exception as e:
            print(f"   ❌ Erreur de connexion: {e}\\n")
            return None, False

    # Tests pour les Organismes
    
    def test_list_organismes(self):
        """Test la liste des organismes."""
        print("🏢 Test liste des organismes...")
        
        # Admin peut voir tous les organismes
        response, success = self.make_request('GET', '/organismes/', self.admin_token)
        if success and response:
            data = response.json()
            print(f"      Admin voit {data.get('pagination', {}).get('count', 0)} organismes")
            if data.get('results'):
                self.test_organisme_id = data['results'][0]['id_organisme']
        
        return success
    
    def test_organisme_detail(self):
        """Test le détail d'un organisme."""
        print("🏢 Test détail organisme...")
        
        if not self.test_organisme_id:
            print("      ⚠️  Pas d'ID organisme pour test")
            return False
        
        response, success = self.make_request(
            'GET', f'/organismes/{self.test_organisme_id}/', self.admin_token
        )
        
        return success
    
    def test_create_organisme(self):
        """Test création d'organisme."""
        print("➕ Test création organisme...")
        
        new_org_data = {
            "nom_organisme": f"Organisme Test {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "ville_organisme": "Test City",
            "email_organisme": f"test.{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
            "active": True
        }
        
        response, success = self.make_request(
            'POST', '/organismes/', self.admin_token, new_org_data, 201
        )
        
        if success and response:
            created_org = response.json()
            self.test_organisme_id = created_org.get('id_organisme')
            print(f"      Organisme créé: {created_org.get('nom_organisme')}")
        
        return success
    
    def test_organismes_stats(self):
        """Test statistiques organismes."""
        print("📊 Test statistiques organismes...")
        
        response, success = self.make_request('GET', '/organismes/stats/', self.admin_token)
        
        if success and response:
            data = response.json()
            print(f"      Total organismes: {data.get('total_organismes', 0)}")
            print(f"      Organismes actifs: {data.get('active_organismes', 0)}")
        
        return success
    
    def test_organisme_sites(self):
        """Test liste des sites d'un organisme."""
        print("🏛️  Test sites de l'organisme...")
        
        if not self.test_organisme_id:
            print("      ⚠️  Pas d'ID organisme pour test")
            return False
        
        response, success = self.make_request(
            'GET', f'/organismes/{self.test_organisme_id}/sites/', self.admin_token
        )
        
        return success

    # Tests pour les Sites
    
    def test_list_sites(self):
        """Test la liste des sites."""
        print("🏛️  Test liste des sites...")
        
        # Admin peut voir tous les sites
        response, success = self.make_request('GET', '/sites/', self.admin_token)
        if success and response:
            data = response.json()
            print(f"      Admin voit {data.get('pagination', {}).get('count', 0)} sites")
            if data.get('results'):
                self.test_site_id = data['results'][0]['id_site']
        
        return success
    
    def test_site_detail(self):
        """Test le détail d'un site."""
        print("🏛️  Test détail site...")
        
        if not self.test_site_id:
            print("      ⚠️  Pas d'ID site pour test")
            return False
        
        response, success = self.make_request(
            'GET', f'/sites/{self.test_site_id}/', self.admin_token
        )
        
        return success
    
    def test_site_geojson(self):
        """Test format GeoJSON d'un site."""
        print("🗺️  Test GeoJSON site...")
        
        if not self.test_site_id:
            print("      ⚠️  Pas d'ID site pour test")
            return False
        
        response, success = self.make_request(
            'GET', f'/sites/{self.test_site_id}/geojson/', self.admin_token
        )
        
        if success and response:
            data = response.json()
            print(f"      Type: {data.get('type', 'N/A')}")
            print(f"      Géométrie: {'✅' if data.get('geometry') else '❌'}")
        
        return success
    
    def test_sites_geojson_list(self):
        """Test liste GeoJSON des sites."""
        print("🗺️  Test liste GeoJSON sites...")
        
        response, success = self.make_request('GET', '/sites/geojson_list/', self.admin_token)
        
        if success and response:
            data = response.json()
            print(f"      FeatureCollection avec {len(data.get('features', []))} sites")
        
        return success
    
    def test_create_site(self):
        """Test création de site."""
        print("➕ Test création site...")
        
        # Créer un site simple sans géométrie
        new_site_data = {
            "nom_site": f"Site Test {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "id_local": f"TEST_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "surf_off": 100.5,
            "marin": False,
            "outre_mer": False,
            "active": True
        }
        
        response, success = self.make_request(
            'POST', '/sites/', self.admin_token, new_site_data, 201
        )
        
        if success and response:
            created_site = response.json()
            self.test_site_id = created_site.get('id_site')
            print(f"      Site créé: {created_site.get('nom_site')}")
        
        return success
    
    def test_create_site_with_geojson(self):
        """Test création de site avec géométrie GeoJSON."""
        print("🗺️  Test création site avec GeoJSON...")
        
        # Point de référence simple
        point_geojson = {
            "type": "Point",
            "coordinates": [2.3522, 48.8566]  # Paris
        }
        
        new_site_data = {
            "nom_site": f"Site GeoJSON {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "id_local": f"GEOJ_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "surf_off": 250.0,
            "geom_pt_geojson": point_geojson,
            "active": True
        }
        
        response, success = self.make_request(
            'POST', '/sites/', self.admin_token, new_site_data, 201
        )
        
        if success and response:
            created_site = response.json()
            print(f"      Site GeoJSON créé: {created_site.get('nom_site')}")
        
        return success
    
    def test_sites_stats(self):
        """Test statistiques sites."""
        print("📊 Test statistiques sites...")
        
        response, success = self.make_request('GET', '/sites/stats/', self.admin_token)
        
        if success and response:
            data = response.json()
            print(f"      Total sites: {data.get('total_sites', 0)}")
            print(f"      Sites actifs: {data.get('active_sites', 0)}")
            print(f"      Surface totale: {data.get('surface_totale_ha', 0)} ha")
        
        return success
    
    def test_site_users(self):
        """Test utilisateurs assignés à un site."""
        print("👥 Test utilisateurs du site...")
        
        if not self.test_site_id:
            print("      ⚠️  Pas d'ID site pour test")
            return False
        
        response, success = self.make_request(
            'GET', f'/sites/{self.test_site_id}/users/', self.admin_token
        )
        
        return success
    
    def test_site_organismes(self):
        """Test organismes gestionnaires d'un site."""
        print("🏢 Test organismes du site...")
        
        if not self.test_site_id:
            print("      ⚠️  Pas d'ID site pour test")
            return False
        
        response, success = self.make_request(
            'GET', f'/sites/{self.test_site_id}/organismes/', self.admin_token
        )
        
        return success

    # Tests des relations et assignations
    
    def test_assign_site_to_organisme(self):
        """Test assignation site à organisme."""
        print("🔗 Test assignation site → organisme...")
        
        if not self.test_organisme_id or not self.test_site_id:
            print("      ⚠️  Pas d'ID organisme ou site pour test")
            return False
        
        assignment_data = {"site_id": self.test_site_id}
        
        response, success = self.make_request(
            'POST', f'/organismes/{self.test_organisme_id}/assign_site/', 
            self.admin_token, assignment_data, 201
        )
        
        return success
    
    def test_bulk_assign_sites(self):
        """Test assignation en masse de sites."""
        print("🔗 Test assignation en masse...")
        
        if not self.test_organisme_id:
            print("      ⚠️  Pas d'ID organisme pour test")
            return False
        
        # Récupérer quelques IDs de sites
        response, _ = self.make_request('GET', '/sites/?page_size=3', self.admin_token)
        if not response or response.status_code != 200:
            print("      ⚠️  Impossible de récupérer les sites")
            return False
        
        sites_data = response.json()
        site_ids = [site['id_site'] for site in sites_data.get('results', [])[:2]]
        
        if not site_ids:
            print("      ⚠️  Aucun site disponible")
            return False
        
        bulk_data = {"site_ids": site_ids}
        
        response, success = self.make_request(
            'POST', f'/organismes/{self.test_organisme_id}/bulk_assign_sites/', 
            self.admin_token, bulk_data, 200
        )
        
        if success and response:
            data = response.json()
            print(f"      Assignés: {len(data.get('assigned', []))}")
            print(f"      Déjà assignés: {len(data.get('already_assigned', []))}")
        
        return success

    # Tests des filtres et recherche
    
    def test_filters_organismes(self):
        """Test filtres et recherche organismes."""
        print("🔍 Test filtres organismes...")
        
        # Test recherche
        response, success1 = self.make_request('GET', '/organismes/?search=RNF', self.admin_token)
        
        # Test filtre par ville
        response, success2 = self.make_request('GET', '/organismes/?ville=paris', self.admin_token)
        
        # Test filtre actifs
        response, success3 = self.make_request('GET', '/organismes/?active=true', self.admin_token)
        
        # Test tri
        response, success4 = self.make_request('GET', '/organismes/?ordering=nom', self.admin_token)
        
        return success1 and success2 and success3 and success4
    
    def test_filters_sites(self):
        """Test filtres et recherche sites."""
        print("🔍 Test filtres sites...")
        
        # Test recherche
        response, success1 = self.make_request('GET', '/sites/?search=camargue', self.admin_token)
        
        # Test filtre par surface
        response, success2 = self.make_request('GET', '/sites/?surf_min=100', self.admin_token)
        
        # Test filtre marin
        response, success3 = self.make_request('GET', '/sites/?marin=false', self.admin_token)
        
        # Test tri par nom
        response, success4 = self.make_request('GET', '/sites/?ordering=nom', self.admin_token)
        
        return success1 and success2 and success3 and success4
    
    def run_all_tests(self):
        """Lance tous les tests."""
        print("🧪 Test complet de l'API REST Organismes et Sites\\n")
        
        self.setup_tokens()
        
        tests = [
            # Tests organismes
            self.test_list_organismes,
            self.test_organisme_detail,
            self.test_create_organisme,
            self.test_organismes_stats,
            self.test_organisme_sites,
            
            # Tests sites
            self.test_list_sites,
            self.test_site_detail,
            self.test_site_geojson,
            self.test_sites_geojson_list,
            self.test_create_site,
            self.test_create_site_with_geojson,
            self.test_sites_stats,
            self.test_site_users,
            self.test_site_organismes,
            
            # Tests relations
            self.test_assign_site_to_organisme,
            self.test_bulk_assign_sites,
            
            # Tests filtres
            self.test_filters_organismes,
            self.test_filters_sites,
        ]
        
        results = []
        for test in tests:
            try:
                result = test()
                results.append(result)
            except Exception as e:
                print(f"❌ Erreur dans {test.__name__}: {e}")
                results.append(False)
        
        # Résumé
        passed = sum(results)
        total = len(results)
        
        print(f"📈 Résumé des tests: {passed}/{total} réussis")
        
        if passed == total:
            print("🎉 Tous les tests API Organismes et Sites sont passés avec succès !")
        else:
            print(f"⚠️  {total - passed} test(s) ont échoué")
        
        return passed == total


def main():
    """Fonction principale."""
    tester = APIOrganismesSitesTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()