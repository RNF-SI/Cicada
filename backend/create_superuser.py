"""
Script pour créer un superutilisateur de test.
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.users.models import Role

# Création du superutilisateur
try:
    existing_admin = Role.objects.filter(email='admin').first()
    if existing_admin:
        # Mettre a jour role_level si necessaire
        if existing_admin.role_level != 'super_admin':
            existing_admin.role_level = 'super_admin'
            existing_admin.save(update_fields=['role_level'])
            print("✅ Superutilisateur mis à jour: role_level='super_admin'")
        else:
            print("ℹ️ Superutilisateur déjà existant et correctement configuré")
    else:
        Role.objects.create_superuser(
            email='admin',
            password='admin',
            nom_role='admin',
            prenom_role=''
        )
        print("✅ Superutilisateur créé avec succès !")
        print("Email: admin")
        print("Mot de passe: admin")
except Exception as e:
    print(f"❌ Erreur lors de la création: {e}")