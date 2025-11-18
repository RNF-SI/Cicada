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
    if not Role.objects.filter(email='admin').exists():
        Role.objects.create_superuser(
            email='admin',
            password='admin',
            nom_role='admin',
            prenom_role=''
        )
        print("✅ Superutilisateur créé avec succès !")
        print("Email: admin")
        print("Mot de passe: admin")
    else:
        print("ℹ️ Superutilisateur déjà existant")
except Exception as e:
    print(f"❌ Erreur lors de la création: {e}")