#!/usr/bin/env python
"""
Script pour creer des utilisateurs de test avec differents niveaux de droits.
Permet de tester facilement l'authentification et les permissions.

Usage:
    python create_test_users.py

Utilisateurs crees:
    - admin@test.fr (Super Administrateur, is_staff=True)
    - admin.org@test.fr (Administrateur Organisme)
    - referent@test.fr (Referent)
    - user@test.fr (Utilisateur simple)

Mot de passe pour tous: Test123!
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.users.models import Role, BibOrganismes

# Mot de passe par defaut pour tous les utilisateurs de test
DEFAULT_PASSWORD = 'Test123!'


def get_or_create_organisme():
    """Cree ou recupere un organisme de test."""
    organisme, created = BibOrganismes.objects.get_or_create(
        nom_organisme='Organisme Test',
        defaults={
            'email_organisme': 'contact@organisme-test.fr',
            'ville_organisme': 'Paris',
            'cp_organisme': '75001'
        }
    )
    if created:
        print(f"  Organisme 'Organisme Test' cree")
    return organisme


def create_test_users():
    """Cree des utilisateurs de test avec differents niveaux de permissions."""

    print("\n" + "=" * 60)
    print("Creation des utilisateurs de test")
    print("=" * 60 + "\n")

    # Recuperer ou creer l'organisme de test
    organisme = get_or_create_organisme()

    # Definition des utilisateurs de test
    test_users = [
        {
            'email': 'admin@test.fr',
            'nom_role': 'Admin',
            'prenom_role': 'Super',
            'identifiant': 'super_admin',
            'role_level': 'super_admin',
            'is_staff': True,
            'is_superuser': True,
            'id_organisme': None,
            'description': 'Super Administrateur (acces complet + admin Django)'
        },
        {
            'email': 'admin.org@test.fr',
            'nom_role': 'Durand',
            'prenom_role': 'Pierre',
            'identifiant': 'admin_org',
            'role_level': 'admin_og',
            'is_staff': True,
            'is_superuser': False,
            'id_organisme': organisme,
            'description': 'Administrateur Organisme (gestion organisme + admin Django)'
        },
        {
            'email': 'referent@test.fr',
            'nom_role': 'Martin',
            'prenom_role': 'Sophie',
            'identifiant': 'referent',
            'role_level': 'utilisateur',  # Sera referent via CorRoleSite
            'is_staff': False,
            'is_superuser': False,
            'id_organisme': organisme,
            'description': 'Utilisateur referent de site (via CorRoleSite)'
        },
        {
            'email': 'user@test.fr',
            'nom_role': 'Petit',
            'prenom_role': 'Jean',
            'identifiant': 'utilisateur',
            'role_level': 'utilisateur',
            'is_staff': False,
            'is_superuser': False,
            'id_organisme': organisme,
            'description': 'Utilisateur simple (lecture seule)'
        },
    ]

    created_count = 0
    updated_count = 0

    for user_data in test_users:
        description = user_data.pop('description')
        email = user_data['email']

        user, created = Role.objects.update_or_create(
            email=email,
            defaults={
                'nom_role': user_data['nom_role'],
                'prenom_role': user_data['prenom_role'],
                'identifiant': user_data['identifiant'],
                'role_level': user_data['role_level'],
                'is_staff': user_data['is_staff'],
                'is_superuser': user_data['is_superuser'],
                'id_organisme': user_data['id_organisme'],
                'active': True,
            }
        )

        # Definir le mot de passe
        user.set_password(DEFAULT_PASSWORD)
        user.save()

        status = "cree" if created else "mis a jour"
        if created:
            created_count += 1
        else:
            updated_count += 1

        print(f"  [{status.upper()}] {email}")
        print(f"           Role: {user_data['role_level']}")
        print(f"           {description}")
        print()

    # Resume
    print("=" * 60)
    print("Resume")
    print("=" * 60)
    print(f"\n  Utilisateurs crees: {created_count}")
    print(f"  Utilisateurs mis a jour: {updated_count}")
    print(f"  Mot de passe pour tous: {DEFAULT_PASSWORD}")

    # Afficher les credentials
    print("\n" + "-" * 60)
    print("Credentials de test")
    print("-" * 60)
    print("""
  | Email             | Mot de passe | Role              | Admin |
  |-------------------|--------------|-------------------|-------|
  | admin@test.fr     | Test123!     | Super Admin       | Oui   |
  | admin.org@test.fr | Test123!     | Admin Organisme   | Oui   |
  | referent@test.fr  | Test123!     | Referent          | Non   |
  | user@test.fr      | Test123!     | Utilisateur       | Non   |
    """)

    print("-" * 60)
    print("URLs utiles")
    print("-" * 60)
    print("""
  Frontend:           http://localhost:4200/auth/login
  Admin Django:       http://localhost:8000/admin/
  API Auth Login:     POST http://localhost:8000/api/auth/login/
  API Auth Me:        GET http://localhost:8000/api/auth/me/
    """)


def reset_test_users():
    """Supprime tous les utilisateurs de test."""
    test_emails = [
        'admin@test.fr',
        'admin.org@test.fr',
        'referent@test.fr',
        'user@test.fr'
    ]

    deleted_count = 0
    for email in test_emails:
        deleted, _ = Role.objects.filter(email=email).delete()
        if deleted:
            deleted_count += 1
            print(f"  Supprime: {email}")

    print(f"\n  Total supprime: {deleted_count}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description='Gestion des utilisateurs de test'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Supprimer les utilisateurs de test au lieu de les creer'
    )
    args = parser.parse_args()

    try:
        if args.reset:
            print("\nSuppression des utilisateurs de test...")
            reset_test_users()
        else:
            create_test_users()
    except Exception as e:
        print(f"\nErreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
