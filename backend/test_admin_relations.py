#!/usr/bin/env python3
"""
Test spécifique des relations admin après corrections.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.users.models import Role, BibOrganismes, Site
from apps.users.admin import RoleAdmin, BibOrganismesAdmin, SiteAdmin
from django.contrib.admin.sites import AdminSite

def test_admin_relations():
    """Test les relations après corrections."""
    print("🔧 Test des relations admin après corrections\n")
    
    try:
        # Test Role relations
        print("1. 🧑 Test Role relations...")
        role = Role.objects.first()
        if role:
            print(f"   Utilisateur: {role.email}")
            sites_count = role.corrolesite_set.count()
            print(f"   Sites (corrolesite_set): {sites_count}")
        
        # Test BibOrganismes relations  
        print("\n2. 🏢 Test BibOrganismes relations...")
        org = BibOrganismes.objects.first()
        if org:
            print(f"   Organisme: {org.nom_organisme}")
            users_count = org.role_set.count()
            sites_count = org.corogsite_set.count()
            print(f"   Utilisateurs (role_set): {users_count}")
            print(f"   Sites (corogsite_set): {sites_count}")
        
        # Test Site relations
        print("\n3. 🏛️ Test Site relations...")
        site = Site.objects.first()
        if site:
            print(f"   Site: {site.nom_site}")
            users_count = site.corrolesite_set.count()
            orgs_count = site.corogsite_set.count()
            print(f"   Utilisateurs (corrolesite_set): {users_count}")
            print(f"   Organismes (corogsite_set): {orgs_count}")
        
        # Test Admin methods
        print("\n4. ⚙️ Test Admin methods...")
        site = AdminSite()
        role_admin = RoleAdmin(Role, site)
        org_admin = BibOrganismesAdmin(BibOrganismes, site)
        site_admin = SiteAdmin(Site, site)
        
        print("   ✅ RoleAdmin initialisé")
        print("   ✅ BibOrganismesAdmin initialisé") 
        print("   ✅ SiteAdmin initialisé")
        
        # Test queryset optimizations
        print("\n5. 🚀 Test queryset optimizations...")
        
        # Simuler une request (None car pas besoin pour le test)
        roles_qs = role_admin.get_queryset(None)
        orgs_qs = org_admin.get_queryset(None)
        sites_qs = site_admin.get_queryset(None)
        
        print(f"   Roles queryset: {roles_qs.count()} objets")
        print(f"   Organismes queryset: {orgs_qs.count()} objets") 
        print(f"   Sites queryset: {sites_qs.count()} objets")
        
        print("\n✅ Tous les tests de relations sont passés !")
        return True
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_admin_relations()
    sys.exit(0 if success else 1)