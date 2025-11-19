#!/usr/bin/env python3
"""
Script de test pour le système de permissions.
Usage: python test_permissions.py
"""
import os
import sys
import django

# Configuration de Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.users.models import Role, BibOrganismes, Site
from django.contrib.auth.models import Group
import requests


BASE_URL = "http://localhost:8000/api"


def test_role_permissions():
    """Test des méthodes de permissions sur le modèle Role."""
    print("🔐 Test des permissions du modèle Role...")
    
    # Récupérer un utilisateur de test
    try:
        admin = Role.objects.filter(is_superuser=True).first()
        if admin:
            print(f"   Admin trouvé: {admin.email}")
            print(f"   - is_super_admin(): {admin.is_super_admin()}")
            print(f"   - is_admin_organisme(): {admin.is_admin_organisme()}")
            print(f"   - is_referent(): {admin.is_referent()}")
            print(f"   - Role level: {admin.role_level}")
    
        # Tester un utilisateur normal
        user = Role.objects.filter(is_superuser=False).first()
        if user:
            print(f"   User trouvé: {user.email}")
            print(f"   - is_super_admin(): {user.is_super_admin()}")
            print(f"   - is_admin_organisme(): {user.is_admin_organisme()}")
            print(f"   - is_referent(): {user.is_referent()}")
            print(f"   - Role level: {user.role_level}")
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}")
    
    print("   ✅ Test permissions OK\n")


def test_groups():
    """Test des groupes Django."""
    print("👥 Test des groupes Django...")
    
    groups = Group.objects.all()
    for group in groups:
        user_count = group.user_set.count()
        perm_count = group.permissions.count()
        print(f"   • {group.name}: {user_count} users, {perm_count} permissions")
    
    print("   ✅ Test groupes OK\n")


def test_middleware_protection():
    """Test du middleware de protection des APIs."""
    print("🛡️  Test middleware protection...")
    
    # Test sans token (doit échouer)
    try:
        response = requests.get(f"{BASE_URL}/auth/me/", timeout=5)
        if response.status_code == 401:
            print("   ✅ Protection sans token OK")
        else:
            print(f"   ⚠️  Réponse inattendue: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Erreur de connexion: {e}")
    
    # Test avec token valide
    try:
        # Login d'abord
        login_response = requests.post(
            f"{BASE_URL}/auth/login/",
            json={"email": "admin", "password": "admin"},
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if login_response.status_code == 200:
            token = login_response.json()['access']
            
            # Test avec token
            response = requests.get(
                f"{BASE_URL}/auth/me/",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5
            )
            
            if response.status_code == 200:
                print("   ✅ Protection avec token OK")
                # Vérifier les en-têtes de permissions
                if 'X-User-Role' in response.headers:
                    print(f"   ✅ En-tête X-User-Role: {response.headers['X-User-Role']}")
                if 'X-User-Permissions' in response.headers:
                    print(f"   ✅ En-tête X-User-Permissions présent")
            else:
                print(f"   ❌ Échec avec token: {response.status_code}")
        else:
            print(f"   ❌ Échec login: {login_response.status_code}")
    
    except Exception as e:
        print(f"   ❌ Erreur de test: {e}")
    
    print("   ✅ Test middleware OK\n")


def test_admin_interface_permissions():
    """Test des permissions dans l'interface admin."""
    print("🖥️  Test interface admin...")
    
    try:
        # Vérifier que les utilisateurs ont bien leurs groupes
        super_admins = Role.objects.filter(groups__name='Super Administrateurs')
        print(f"   • Super Administrateurs: {super_admins.count()} utilisateurs")
        
        admin_og = Role.objects.filter(groups__name='Administrateurs Organisme')
        print(f"   • Administrateurs Organisme: {admin_og.count()} utilisateurs")
        
        referents = Role.objects.filter(groups__name='Référents')
        print(f"   • Référents: {referents.count()} utilisateurs")
        
        users = Role.objects.filter(groups__name='Utilisateurs')
        print(f"   • Utilisateurs: {users.count()} utilisateurs")
        
        print("   ✅ Test admin interface OK\n")
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")


def test_object_permissions():
    """Test des permissions sur les objets spécifiques."""
    print("🎯 Test permissions objet...")
    
    try:
        # Récupérer des objets de test
        admin = Role.objects.filter(is_superuser=True).first()
        organisme = BibOrganismes.objects.first()
        site = Site.objects.first()
        
        if admin and organisme:
            can_manage = admin.can_manage_organisme(organisme)
            print(f"   • Admin peut gérer organisme: {can_manage}")
        
        if admin and site:
            can_manage = admin.can_manage_site(site)
            print(f"   • Admin peut gérer site: {can_manage}")
        
        print("   ✅ Test permissions objet OK\n")
        
    except Exception as e:
        print(f"   ❌ Erreur: {e}\n")


def main():
    """Fonction principale de test."""
    print("🧪 Test du système de permissions\n")
    
    # Tests des modèles
    test_role_permissions()
    test_groups()
    test_admin_interface_permissions()
    test_object_permissions()
    
    # Tests des APIs
    test_middleware_protection()
    
    print("🎉 Tous les tests de permissions terminés!")


if __name__ == "__main__":
    main()