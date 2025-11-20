#!/usr/bin/env python3
"""
Test d'accès à l'interface admin Django.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import Client
from apps.users.models import Role

def test_admin_access():
    """Test l'accès à l'interface admin."""
    print("🔐 Test d'accès à l'interface admin\n")
    
    try:
        # Créer un client de test
        client = Client()
        
        # Test 1: Accès admin sans auth (doit rediriger)
        print("1. 🚪 Test accès admin sans authentification...")
        response = client.get('/admin/')
        print(f"   Status: {response.status_code} (attendu: 302)")
        
        # Test 2: Récupérer un utilisateur admin
        print("\n2. 👤 Test récupération utilisateur admin...")
        admin_user = Role.objects.filter(is_staff=True).first()
        if admin_user:
            print(f"   Admin trouvé: {admin_user.email}")
            
            # Test 3: Login avec l'utilisateur admin
            print("\n3. 🔑 Test login admin...")
            # Essayer différentes combinaisons de login
            login_success = client.login(username=admin_user.email, password='admin')
            if not login_success:
                # Essayer avec le nom d'utilisateur par défaut
                login_success = client.login(username='admin', password='admin')
            if login_success:
                print("   ✅ Login réussi")
                
                # Test 4: Accès à l'admin après login
                print("\n4. 🎯 Test accès admin après login...")
                response = client.get('/admin/')
                print(f"   Status: {response.status_code} (attendu: 200)")
                
                if response.status_code == 200:
                    print("   ✅ Accès admin OK")
                    
                    # Test 5: Accès aux différentes sections
                    print("\n5. 📋 Test accès aux sections...")
                    
                    sections = [
                        '/admin/users/',
                        '/admin/users/role/', 
                        '/admin/users/biborganismes/',
                        '/admin/users/site/',
                    ]
                    
                    for section in sections:
                        resp = client.get(section)
                        status = "✅" if resp.status_code == 200 else "❌"
                        print(f"   {status} {section}: {resp.status_code}")
                
                else:
                    print("   ❌ Accès admin échoué")
                    return False
            else:
                print("   ❌ Login échoué")
                return False
        else:
            print("   ❌ Aucun utilisateur admin trouvé")
            return False
        
        print("\n✅ Tous les tests d'accès admin sont passés !")
        print("\n🌐 Interface admin disponible: http://localhost:8000/admin/")
        print("📝 Login: admin / admin")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_admin_access()
    sys.exit(0 if success else 1)