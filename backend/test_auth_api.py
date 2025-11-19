#!/usr/bin/env python3
"""
Script de test pour l'API d'authentification JWT.
Usage: python test_auth_api.py
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api/auth"

def test_health_check():
    """Test du health check (endpoint public)."""
    print("🔍 Test Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/health/")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        assert response.status_code == 200
        print("   ✅ Health check OK\n")
        return True
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
        return False

def test_login(email="admin", password="admin"):
    """Test de connexion."""
    print(f"🔐 Test Login ({email})...")
    try:
        response = requests.post(
            f"{BASE_URL}/login/",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   User: {data['user']['email']} ({data['user']['nom']} {data['user']['prenom']})")
            if data['user'].get('organisme'):
                print(f"   Organisme: {data['user']['organisme']['nom']}")
            print("   ✅ Login OK")
            return data['access'], data['refresh']
        else:
            print(f"   ❌ Erreur: {response.text}")
            return None, None
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
        return None, None

def test_user_info(access_token):
    """Test récupération infos utilisateur."""
    print("👤 Test User Info...")
    try:
        response = requests.get(
            f"{BASE_URL}/me/",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ID: {data['id_role']}")
            print(f"   Email: {data['email']}")
            print(f"   Staff: {data['is_staff']}")
            print(f"   Superuser: {data['is_superuser']}")
            print("   ✅ User info OK\n")
            return True
        else:
            print(f"   ❌ Erreur: {response.text}\n")
            return False
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
        return False

def test_refresh_token(refresh_token):
    """Test du refresh token."""
    print("🔄 Test Refresh Token...")
    try:
        response = requests.post(
            f"{BASE_URL}/refresh/",
            json={"refresh": refresh_token},
            headers={"Content-Type": "application/json"}
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Token refresh OK\n")
            return data['access']
        else:
            print(f"   ❌ Erreur: {response.text}\n")
            return None
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
        return None

def test_logout(access_token, refresh_token):
    """Test de déconnexion."""
    print("🚪 Test Logout...")
    try:
        response = requests.post(
            f"{BASE_URL}/logout/",
            json={"refresh": refresh_token},
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
        )
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   ✅ Logout OK\n")
            return True
        else:
            print(f"   ❌ Erreur: {response.text}\n")
            return False
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")
        return False

def main():
    """Fonction principale de test."""
    print("🧪 Test de l'API d'authentification JWT\n")
    
    # Test health check
    if not test_health_check():
        print("❌ Health check échoué, arrêt des tests")
        sys.exit(1)
    
    # Test login admin
    access_token, refresh_token = test_login("admin", "admin")
    if not access_token:
        print("❌ Login admin échoué, arrêt des tests")
        sys.exit(1)
    
    # Test user info
    if not test_user_info(access_token):
        print("❌ User info échoué")
        sys.exit(1)
    
    # Test refresh token
    new_access_token = test_refresh_token(refresh_token)
    if not new_access_token:
        print("❌ Refresh token échoué")
        sys.exit(1)
    
    # Test user info avec nouveau token
    if not test_user_info(new_access_token):
        print("❌ User info avec nouveau token échoué")
        sys.exit(1)
    
    # Test login utilisateur avec organisme
    print("🏢 Test avec utilisateur organisme...")
    access_token2, refresh_token2 = test_login("marie.dupont@rnf.fr", "password123")
    if access_token2:
        test_user_info(access_token2)
    
    # Test logout
    test_logout(access_token, refresh_token)
    
    print("🎉 Tous les tests sont passés avec succès !")

if __name__ == "__main__":
    main()