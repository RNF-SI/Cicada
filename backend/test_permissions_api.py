#!/usr/bin/env python3
"""
Script de test pour l'API de permissions.
Usage: python test_permissions_api.py
"""
import requests
import json
import sys

BASE_URL = "http://localhost:8000/api"


def get_auth_token(email="admin", password="admin"):
    """Obtient un token d'authentification."""
    response = requests.post(
        f"{BASE_URL}/auth/login/",
        json={"email": email, "password": password},
        headers={"Content-Type": "application/json"}
    )
    
    if response.status_code == 200:
        return response.json()['access']
    return None


def test_endpoint(url, token, expected_status=200, description=""):
    """Teste un endpoint avec un token."""
    try:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        response = requests.get(url, headers=headers)
        
        status_ok = response.status_code == expected_status
        status_emoji = "✅" if status_ok else "❌"
        
        print(f"   {status_emoji} {description}")
        print(f"      URL: {url}")
        print(f"      Status: {response.status_code} (attendu: {expected_status})")
        
        if status_ok and response.status_code == 200:
            try:
                data = response.json()
                if 'message' in data:
                    print(f"      Message: {data['message']}")
            except:
                pass
        elif not status_ok:
            print(f"      Erreur: {response.text[:100]}...")
        
        print()
        return status_ok
        
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}\n")
        return False


def test_permissions_info(token):
    """Teste la vue d'information des permissions."""
    print("📋 Test informations permissions...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/users/permissions/",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        if response.status_code == 200:
            data = response.json()
            user = data.get('user', {})
            permissions = data.get('permissions', {})
            groups = data.get('groups', [])
            
            print(f"   ✅ Utilisateur: {user.get('email')} ({user.get('role_level')})")
            print(f"   ✅ Organisme: {user.get('organisme', 'Aucun')}")
            print(f"   ✅ Groupes: {', '.join(groups)}")
            print(f"   ✅ Super Admin: {permissions.get('is_super_admin')}")
            print(f"   ✅ Admin Organisme: {permissions.get('is_admin_organisme')}")
            print(f"   ✅ Référent: {permissions.get('is_referent')}")
            print()
            return True
        else:
            print(f"   ❌ Erreur: {response.status_code}\n")
            return False
            
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
        return False


def main():
    """Test principal des permissions API."""
    print("🧪 Test des permissions API\n")
    
    # Obtenir un token d'admin
    print("🔐 Connexion en tant qu'admin...")
    admin_token = get_auth_token("admin", "admin")
    if not admin_token:
        print("❌ Impossible de se connecter en tant qu'admin")
        sys.exit(1)
    print("✅ Token admin obtenu\n")
    
    # Test des informations de permissions
    if not test_permissions_info(admin_token):
        print("❌ Échec du test d'informations")
        return False
    
    # Test des endpoints avec permissions DRF
    print("🔒 Test endpoints avec permissions DRF...")
    
    success_tests = [
        (f"{BASE_URL}/users/test/super-admin/", admin_token, 200, "Super Admin (OK)"),
        (f"{BASE_URL}/users/test/admin-organisme/", admin_token, 200, "Admin Organisme (OK)"),
        (f"{BASE_URL}/users/test/referent/", admin_token, 200, "Référent (OK)"),
    ]
    
    for url, token, expected, desc in success_tests:
        test_endpoint(url, token, expected, desc)
    
    # Test des endpoints avec décorateurs
    print("🎭 Test endpoints avec décorateurs...")
    
    decorator_tests = [
        (f"{BASE_URL}/users/test/decorator-super-admin/", admin_token, 200, "Décorateur Super Admin (OK)"),
        (f"{BASE_URL}/users/test/decorator-admin-organisme/", admin_token, 200, "Décorateur Admin Organisme (OK)"),
        (f"{BASE_URL}/users/test/decorator-referent/", admin_token, 200, "Décorateur Référent (OK)"),
    ]
    
    for url, token, expected, desc in decorator_tests:
        test_endpoint(url, token, expected, desc)
    
    # Test des endpoints sans token (doivent échouer)
    print("🚫 Test endpoints sans token (doivent échouer)...")
    
    no_token_tests = [
        (f"{BASE_URL}/users/test/super-admin/", None, 401, "Super Admin sans token (ÉCHEC ATTENDU)"),
        (f"{BASE_URL}/users/permissions/", None, 401, "Permissions sans token (ÉCHEC ATTENDU)"),
    ]
    
    for url, token, expected, desc in no_token_tests:
        test_endpoint(url, token, expected, desc)
    
    # Test avec utilisateur normal (si disponible)
    print("👤 Test avec utilisateur normal...")
    user_token = get_auth_token("marie.dupont@rnf.fr", "password123")
    
    if user_token:
        print("✅ Token utilisateur obtenu")
        
        # L'utilisateur normal ne doit pas avoir accès aux endpoints admin
        user_fail_tests = [
            (f"{BASE_URL}/users/test/super-admin/", user_token, 403, "User → Super Admin (ÉCHEC ATTENDU)"),
            (f"{BASE_URL}/users/test/admin-organisme/", user_token, 403, "User → Admin Organisme (ÉCHEC ATTENDU)"),
        ]
        
        for url, token, expected, desc in user_fail_tests:
            test_endpoint(url, token, expected, desc)
        
        # Mais doit avoir accès à ses infos
        test_permissions_info(user_token)
    else:
        print("⚠️  Pas d'utilisateur normal disponible pour test\n")
    
    # Test d'endpoints d'objets spécifiques
    print("🎯 Test permissions objets spécifiques...")
    
    object_tests = [
        (f"{BASE_URL}/users/organismes/1/", admin_token, 200, "Accès organisme #1 (admin)"),
        (f"{BASE_URL}/users/sites/1/", admin_token, 200, "Accès site #1 (admin)"),
    ]
    
    for url, token, expected, desc in object_tests:
        test_endpoint(url, token, expected, desc)
    
    print("🎉 Tests des permissions API terminés!")
    

if __name__ == "__main__":
    main()