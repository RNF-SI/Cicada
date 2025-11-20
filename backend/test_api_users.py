#!/usr/bin/env python3
"""
Script de test pour l'API REST des utilisateurs.
Usage: python test_api_users.py
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

from apps.users.models import Role, BibOrganismes

BASE_URL = "http://localhost:8000/api"


class APIUsersTester:
    """Classe pour tester l'API des utilisateurs."""
    
    def __init__(self):
        self.admin_token = None
        self.user_token = None
        self.test_user_id = None
    
    def get_auth_token(self, email="admin", password="admin"):
        """Obtient un token d'authentification."""
        response = requests.post(
            f"{BASE_URL}/auth/login/",
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
        url = f"{BASE_URL}/users{endpoint}"
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
                        elif 'email' in response_data:
                            print(f"      User: {response_data['email']}")
                        elif 'message' in response_data:
                            print(f"      Message: {response_data['message']}")
                except:
                    pass
            elif not success:
                print(f"      Erreur: {response.text[:100]}...")
            
            print()
            return response, success
            
        except Exception as e:
            print(f"   ❌ Erreur de connexion: {e}\n")
            return None, False
    
    def test_list_users(self):
        """Test la liste des utilisateurs."""
        print("📋 Test liste des utilisateurs...")
        
        # Admin peut voir tous les utilisateurs
        response, success = self.make_request('GET', '/', self.admin_token)
        if success and response:
            data = response.json()
            print(f"      Admin voit {data.get('pagination', {}).get('count', 0)} utilisateurs")
        
        # Utilisateur normal voit seulement son profil
        if self.user_token:
            response, success = self.make_request('GET', '/', self.user_token)
            if success and response:
                data = response.json()
                print(f"      User voit {data.get('pagination', {}).get('count', 0)} utilisateurs")
        
        return success
    
    def test_user_detail(self):
        """Test le détail d'un utilisateur."""
        print("👤 Test détail utilisateur...")
        
        # Récupérer l'ID du premier utilisateur
        response, _ = self.make_request('GET', '/', self.admin_token)
        if response and response.status_code == 200:
            data = response.json()
            if data.get('results'):
                user_id = data['results'][0]['id_role']
                self.test_user_id = user_id
                
                # Test détail avec admin
                response, success = self.make_request('GET', f'/{user_id}/', self.admin_token)
                return success
        
        return False
    
    def test_create_user(self):
        """Test création d'utilisateur."""
        print("➕ Test création utilisateur...")
        
        # Données pour créer un utilisateur
        new_user_data = {
            "email": f"test.user.{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
            "nom_role": "Test",
            "prenom_role": "User",
            "role_level": "utilisateur",
            "password": "TestPassword123!",
            "password_confirm": "TestPassword123!",
            "active": True
        }
        
        # Test création avec admin
        response, success = self.make_request(
            'POST', '/', self.admin_token, new_user_data, 201
        )
        
        if success and response:
            created_user = response.json()
            self.test_user_id = created_user.get('id_role')
            print(f"      Utilisateur créé: {created_user.get('email')}")
        
        # Test création avec utilisateur normal (doit échouer)
        if self.user_token:
            self.make_request(
                'POST', '/', self.user_token, new_user_data, 403
            )
        
        return success
    
    def test_update_user(self):
        """Test modification d'utilisateur."""
        print("✏️  Test modification utilisateur...")
        
        if not self.test_user_id:
            print("      ⚠️  Pas d'ID utilisateur pour test")
            return False
        
        # Données de modification
        update_data = {
            "desc_role": f"Description modifiée le {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        }
        
        # Test modification avec admin
        response, success = self.make_request(
            'PATCH', f'/{self.test_user_id}/', self.admin_token, update_data
        )
        
        return success
    
    def test_change_password(self):
        """Test changement de mot de passe."""
        print("🔑 Test changement mot de passe...")
        
        if not self.test_user_id:
            print("      ⚠️  Pas d'ID utilisateur pour test")
            return False
        
        # Données pour changer le mot de passe
        password_data = {
            "password": "NewPassword123!",
            "password_confirm": "NewPassword123!"
        }
        
        # Test changement avec admin
        response, success = self.make_request(
            'POST', f'/{self.test_user_id}/change-password/', 
            self.admin_token, password_data
        )
        
        return success
    
    def test_me_endpoint(self):
        """Test endpoint /me/."""
        print("🙋 Test endpoint /me/...")
        
        # Test avec admin
        response, success = self.make_request('GET', '/me/', self.admin_token)
        
        # Test avec utilisateur normal
        if self.user_token:
            response, success2 = self.make_request('GET', '/me/', self.user_token)
            success = success and success2
        
        return success
    
    def test_stats_endpoint(self):
        """Test endpoint statistiques."""
        print("📊 Test endpoint statistiques...")
        
        # Test avec admin
        response, success = self.make_request('GET', '/stats/', self.admin_token)
        
        if success and response:
            data = response.json()
            print(f"      Total utilisateurs: {data.get('total_users', 0)}")
            print(f"      Utilisateurs actifs: {data.get('active_users', 0)}")
        
        # Test avec utilisateur normal (doit échouer)
        if self.user_token:
            self.make_request('GET', '/stats/', self.user_token, expected_status=403)
        
        return success
    
    def test_site_assignment(self):
        """Test assignation de sites."""
        print("🏛️  Test assignation sites...")
        
        if not self.test_user_id:
            print("      ⚠️  Pas d'ID utilisateur pour test")
            return False
        
        # Données d'assignation (site ID 1 par défaut)
        assignment_data = {
            "site_id": 1,
            "referent": True,
            "referent_valid": True
        }
        
        # Test assignation avec admin
        response, success = self.make_request(
            'POST', f'/{self.test_user_id}/assign-site/', 
            self.admin_token, assignment_data, 201
        )
        
        # Test désassignation
        if success:
            response2, success2 = self.make_request(
                'DELETE', f'/{self.test_user_id}/sites/1/', 
                self.admin_token, expected_status=204
            )
            success = success and success2
        
        return success
    
    def test_filters_and_search(self):
        """Test filtres et recherche."""
        print("🔍 Test filtres et recherche...")
        
        # Test recherche
        response, success1 = self.make_request('GET', '/?search=admin', self.admin_token)
        
        # Test filtre par role_level
        response, success2 = self.make_request('GET', '/?role_level=super_admin', self.admin_token)
        
        # Test filtre par organisme
        response, success3 = self.make_request('GET', '/?organisme=1', self.admin_token)
        
        # Test tri
        response, success4 = self.make_request('GET', '/?ordering=-date_insert', self.admin_token)
        
        return success1 and success2 and success3 and success4
    
    def test_pagination(self):
        """Test pagination."""
        print("📄 Test pagination...")
        
        # Test avec taille de page personnalisée
        response, success1 = self.make_request('GET', '/?page_size=5', self.admin_token)
        
        if success1 and response:
            data = response.json()
            pagination = data.get('pagination', {})
            print(f"      Page actuelle: {pagination.get('current_page')}")
            print(f"      Total pages: {pagination.get('total_pages')}")
        
        # Test page suivante si disponible
        response, success2 = self.make_request('GET', '/?page=2', self.admin_token)
        
        return success1 and success2
    
    def test_delete_user(self):
        """Test suppression d'utilisateur."""
        print("🗑️  Test suppression utilisateur...")
        
        if not self.test_user_id:
            print("      ⚠️  Pas d'ID utilisateur pour test")
            return False
        
        # Test suppression avec admin
        response, success = self.make_request(
            'DELETE', f'/{self.test_user_id}/', self.admin_token, expected_status=204
        )
        
        return success
    
    def run_all_tests(self):
        """Lance tous les tests."""
        print("🧪 Test complet de l'API REST Utilisateurs\n")
        
        self.setup_tokens()
        
        tests = [
            self.test_list_users,
            self.test_user_detail,
            self.test_me_endpoint,
            self.test_stats_endpoint,
            self.test_create_user,
            self.test_update_user,
            self.test_change_password,
            self.test_site_assignment,
            self.test_filters_and_search,
            self.test_pagination,
            self.test_delete_user,
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
            print("🎉 Tous les tests API sont passés avec succès !")
        else:
            print(f"⚠️  {total - passed} test(s) ont échoué")
        
        return passed == total


def main():
    """Fonction principale."""
    tester = APIUsersTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()