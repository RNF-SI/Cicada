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

# Lecture des variables d'environnement
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin')

# Création du superutilisateur
try:
    existing_admin = Role.objects.filter(email=email).first()
    if existing_admin:
        # Mettre a jour role_level si necessaire
        if existing_admin.role_level != 'super_admin':
            existing_admin.role_level = 'super_admin'
            existing_admin.save(update_fields=['role_level'])
            print(f"✅ Superutilisateur mis à jour: role_level='super_admin' ({email})")
        else:
            print(f"ℹ️ Superutilisateur déjà existant et correctement configuré ({email})")
    else:
        Role.objects.create_superuser(
            email=email,
            password=password,
            nom_role=email.split('@')[0] if '@' in email else email,
            prenom_role=''
        )
        print(f"✅ Superutilisateur créé avec succès !")
        print(f"Email: {email}")
except Exception as e:
    print(f"❌ Erreur lors de la création: {e}")