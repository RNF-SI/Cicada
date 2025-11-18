"""
Script pour créer des données de test.
"""
import os
import sys
import django

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.users.models import Role, BibOrganismes, Site
from apps.core.models import TypeNomenclature, Nomenclature

def create_test_data():
    """Crée des données de test pour valider l'admin."""
    
    print("🏗️  Création des données de test...")
    
    # 1. Type de nomenclature pour les types de sites
    type_site, created = TypeNomenclature.objects.get_or_create(
        mnemonique='TYPE_SITE',
        defaults={
            'label_default': 'Type de site',
            'label_fr': 'Type de site',
            'definition_fr': 'Classification des types de sites naturels',
            'statut': 'Validé',
            'source': 'RNF'
        }
    )
    if created:
        print("✅ Type nomenclature 'Type de site' créé")
    
    # 2. Nomenclatures pour types de sites
    types_sites = [
        ('RN', 'Réserve Naturelle'),
        ('RNN', 'Réserve Naturelle Nationale'),
        ('RNR', 'Réserve Naturelle Régionale'),
        ('PNR', 'Parc Naturel Régional'),
        ('ENS', 'Espace Naturel Sensible'),
    ]
    
    for cd, label in types_sites:
        nom_type, created = Nomenclature.objects.get_or_create(
            id_type=type_site,
            cd_nomenclature=cd,
            defaults={
                'label_default': label,
                'label_fr': label,
                'mnemonique': cd,
                'active': True
            }
        )
        if created:
            print(f"✅ Nomenclature '{label}' créée")
    
    # 3. Organismes gestionnaires
    organismes = [
        {
            'nom_organisme': 'Réserves Naturelles de France',
            'email_organisme': 'contact@reserves-naturelles.org',
            'ville_organisme': 'Dijon',
            'cp_organisme': '21000'
        },
        {
            'nom_organisme': 'CEN Auvergne-Rhône-Alpes',
            'email_organisme': 'contact@cen-aura.org',
            'ville_organisme': 'Lyon',
            'cp_organisme': '69000'
        },
        {
            'nom_organisme': 'DREAL Nouvelle-Aquitaine',
            'email_organisme': 'contact@nouvelle-aquitaine.gouv.fr',
            'ville_organisme': 'Bordeaux',
            'cp_organisme': '33000'
        }
    ]
    
    for org_data in organismes:
        org, created = BibOrganismes.objects.get_or_create(
            nom_organisme=org_data['nom_organisme'],
            defaults=org_data
        )
        if created:
            print(f"✅ Organisme '{org.nom_organisme}' créé")
    
    # 4. Sites
    rnf = BibOrganismes.objects.get(nom_organisme='Réserves Naturelles de France')
    type_rnn = Nomenclature.objects.get(cd_nomenclature='RNN')
    type_rnr = Nomenclature.objects.get(cd_nomenclature='RNR')
    
    sites = [
        {
            'nom_site': 'Réserve Naturelle de la Camargue',
            'id_local': 'RN13',
            'id_inpn': 'FR3600013',
            'id_type_site': type_rnn,
            'surf_off': 13117.0,
            'marin': False,
            'outre_mer': False,
            'active': True
        },
        {
            'nom_site': 'Réserve Naturelle des Aiguilles Rouges',
            'id_local': 'RN1',
            'id_inpn': 'FR3600001',
            'id_type_site': type_rnn,
            'surf_off': 3279.0,
            'marin': False,
            'outre_mer': False,
            'active': True
        },
        {
            'nom_site': 'Réserve Naturelle Régionale du Grand-Voyeux',
            'id_local': 'RNR145',
            'id_type_site': type_rnr,
            'surf_off': 264.0,
            'marin': False,
            'outre_mer': False,
            'active': True
        }
    ]
    
    for site_data in sites:
        site, created = Site.objects.get_or_create(
            nom_site=site_data['nom_site'],
            defaults=site_data
        )
        if created:
            print(f"✅ Site '{site.nom_site}' créé")
    
    # 5. Utilisateurs
    cen_aura = BibOrganismes.objects.get(nom_organisme='CEN Auvergne-Rhône-Alpes')
    
    users = [
        {
            'email': 'marie.dupont@rnf.fr',
            'nom_role': 'Dupont',
            'prenom_role': 'Marie',
            'id_organisme': rnf,
            'is_staff': True
        },
        {
            'email': 'jean.martin@cen-aura.org',
            'nom_role': 'Martin',
            'prenom_role': 'Jean',
            'id_organisme': cen_aura,
            'is_staff': False
        }
    ]
    
    for user_data in users:
        email = user_data.pop('email')
        user, created = Role.objects.get_or_create(
            email=email,
            defaults={**user_data, 'email': email}
        )
        if created:
            user.set_password('password123')
            user.save()
            print(f"✅ Utilisateur '{user.get_full_name()}' créé")
    
    print("\n🎉 Données de test créées avec succès !")
    print("📊 Résumé :")
    print(f"   - {TypeNomenclature.objects.count()} types de nomenclatures")
    print(f"   - {Nomenclature.objects.count()} nomenclatures")
    print(f"   - {BibOrganismes.objects.count()} organismes")
    print(f"   - {Site.objects.count()} sites")
    print(f"   - {Role.objects.count()} utilisateurs")
    print("\n🔗 Accès admin : http://localhost:8000/admin/")
    print("   - Superuser : admin@example.com / admin123")


if __name__ == '__main__':
    create_test_data()