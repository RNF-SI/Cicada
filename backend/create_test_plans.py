#!/usr/bin/env python3
"""
Script pour créer des Plans de Gestion de test.
"""
import os
import sys
import django
from datetime import datetime, date

# Setup Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.plans.models import PlanGestion, CorSitePg, CorPgFichier
from apps.users.models import Role, Site
from apps.core.models import Nomenclature


def create_test_plans():
    """Créer des Plans de Gestion de test."""
    
    print("🔧 Création de Plans de Gestion de test...")
    
    # Récupérer les utilisateurs et sites existants
    try:
        admin_user = Role.objects.get(email='admin')
    except Role.DoesNotExist:
        print("❌ Utilisateur admin non trouvé. Exécutez d'abord create_test_data.py")
        return
    
    try:
        marie = Role.objects.get(email='marie.dupont@rnf.fr')
    except Role.DoesNotExist:
        print("❌ Utilisateur marie.dupont@rnf.fr non trouvé. Exécutez d'abord create_test_data.py")
        return
    
    # Récupérer les sites existants
    sites = list(Site.objects.all())
    if not sites:
        print("❌ Aucun site trouvé. Exécutez d'abord create_test_data.py")
        return
    
    # Récupérer les nomenclatures
    try:
        eval_initiale = Nomenclature.objects.get(cd_nomenclature='EVAL_INITIALE')
        eval_finale = Nomenclature.objects.get(cd_nomenclature='EVAL_FINALE')
        red_gestionnaire = Nomenclature.objects.get(cd_nomenclature='RED_GESTIONNAIRE')
        red_bureau = Nomenclature.objects.get(cd_nomenclature='RED_BUREAU_ETUDE')
    except Nomenclature.DoesNotExist:
        print("❌ Nomenclatures non trouvées. Exécutez d'abord create_plan_nomenclatures.py")
        return
    
    print(f"✅ {len(sites)} sites disponibles pour les tests")
    
    # Plan 1: Plan mono-site (Camargue)
    plan1, created = PlanGestion.objects.get_or_create(
        nom="Plan de gestion 2020-2030 - Réserve Naturelle de Camargue",
        defaults={
            'id_cdr': 2020001,
            'annee_debut': 2020,
            'annee_fin': 2030,
            'gestion_partagee': False,
            'ct88': True,
            'risque_incendie': True,
            'id_evaluation': eval_initiale,
            'id_redacteur_type': red_gestionnaire,
            'redacteur_nom': 'SNPN - Réserve de Camargue',
            'commentaire': 'Plan de gestion quinquennal pour la période 2020-2030. Accent sur la gestion hydraulique et la protection des oiseaux migrateurs.',
            'statut': 'valide',
            'version': '2.0',
            'id_utilisateur_ajout': admin_user,
            'id_utilisateur_maj': marie
        }
    )
    if created:
        print(f"✅ Plan créé: {plan1.nom}")
        # Associer le site Camargue (premier site)
        if sites:
            CorSitePg.objects.get_or_create(
                plan_de_gestion=plan1,
                site=sites[0],  # Premier site (normalement Camargue)
                defaults={
                    'rang': 1,
                    'commentaire': 'Site principal du plan de gestion'
                }
            )
        # Ajouter des référents
        plan1.referents.add(marie)
    
    # Plan 2: Plan multi-sites
    plan2, created = PlanGestion.objects.get_or_create(
        nom="Plan de gestion inter-réserves Auvergne-Rhone-Alpes 2022-2027",
        defaults={
            'id_cdr': 2022015,
            'annee_debut': 2022,
            'annee_fin': 2027,
            'gestion_partagee': True,
            'ct88': False,
            'risque_incendie': False,
            'id_evaluation': eval_finale,
            'id_redacteur_type': red_bureau,
            'redacteur_nom': 'Bureau Biotope - Lyon',
            'commentaire': 'Plan de gestion coordonné pour plusieurs réserves naturelles régionales. Focus sur la continuité écologique et les corridors biologiques.',
            'statut': 'draft',
            'version': '1.0',
            'id_utilisateur_ajout': marie,
            'id_utilisateur_maj': marie
        }
    )
    if created:
        print(f"✅ Plan créé: {plan2.nom}")
        # Associer plusieurs sites
        for i, site in enumerate(sites[1:], 1):  # Sites 2 et suivants
            if i <= 2:  # Limiter à 2 sites
                CorSitePg.objects.get_or_create(
                    plan_de_gestion=plan2,
                    site=site,
                    defaults={
                        'rang': i,
                        'commentaire': f'Site {i} du plan multi-sites'
                    }
                )
        # Ajouter des référents
        plan2.referents.add(admin_user, marie)
    
    # Plan 3: Plan archivé
    plan3, created = PlanGestion.objects.get_or_create(
        nom="Plan de gestion 2010-2020 - Réserve Naturelle des Aiguilles Rouges",
        defaults={
            'id_cdr': 2010003,
            'annee_debut': 2010,
            'annee_fin': 2020,
            'gestion_partagee': False,
            'ct88': True,
            'risque_incendie': False,
            'id_evaluation': eval_finale,
            'id_redacteur_type': red_gestionnaire,
            'redacteur_nom': 'Réserves Naturelles de France',
            'commentaire': 'Plan de gestion terminé. Remplacé par le nouveau plan 2021-2031.',
            'statut': 'archive',
            'version': '1.3',
            'id_utilisateur_ajout': admin_user,
            'id_utilisateur_maj': admin_user
        }
    )
    if created:
        print(f"✅ Plan créé: {plan3.nom}")
        # Associer un site
        if len(sites) >= 2:
            CorSitePg.objects.get_or_create(
                plan_de_gestion=plan3,
                site=sites[1],  # Deuxième site
                defaults={
                    'rang': 1,
                    'commentaire': 'Plan archivé - fin de période'
                }
            )
    
    # Créer des fichiers fictifs pour le plan 1
    if plan1:
        fichiers_test = [
            {
                'nom_fichier': 'Plan_Camargue_2020-2030_Document_Principal.pdf',
                'type_fichier': 'document',
                'titre': 'Document principal du plan de gestion',
                'description': 'Document principal contenant l\'ensemble du plan de gestion',
                'auteur': 'SNPN',
                'public': True,
                'ordre_affichage': 1
            },
            {
                'nom_fichier': 'Carte_Zonage_Camargue.jpg',
                'type_fichier': 'carte',
                'titre': 'Carte de zonage de la réserve',
                'description': 'Carte détaillée du zonage réglementaire',
                'auteur': 'SNPN - SIG',
                'public': True,
                'ordre_affichage': 2
            },
            {
                'nom_fichier': 'Etude_Avifaune_2019.pdf',
                'type_fichier': 'rapport',
                'titre': 'Étude avifaunistique 2019',
                'description': 'Rapport d\'étude sur l\'avifaune migratrice',
                'auteur': 'LPO PACA',
                'public': False,
                'ordre_affichage': 3
            }
        ]
        
        for fichier_data in fichiers_test:
            fichier, created = CorPgFichier.objects.get_or_create(
                plan_de_gestion=plan1,
                nom_fichier=fichier_data['nom_fichier'],
                defaults={
                    'chemin_fichier': f'/media/plans/{plan1.id_pg}/{fichier_data["nom_fichier"]}',
                    'type_fichier': fichier_data['type_fichier'],
                    'titre': fichier_data['titre'],
                    'description': fichier_data['description'],
                    'auteur': fichier_data['auteur'],
                    'public': fichier_data['public'],
                    'ordre_affichage': fichier_data['ordre_affichage'],
                    'taille_fichier': 1024000 + (fichier_data['ordre_affichage'] * 500000),  # Taille fictive
                    'extension': '.pdf' if 'pdf' in fichier_data['nom_fichier'] else '.jpg',
                    'id_utilisateur_upload': admin_user
                }
            )
            if created:
                print(f"  ➕ Fichier créé: {fichier_data['nom_fichier']}")
    
    print("✅ Plans de Gestion de test créés avec succès!")
    print("\nRésumé:")
    print(f"- Nombre total de plans: {PlanGestion.objects.count()}")
    print(f"- Plans en brouillon: {PlanGestion.objects.filter(statut='draft').count()}")
    print(f"- Plans validés: {PlanGestion.objects.filter(statut='valide').count()}")
    print(f"- Plans archivés: {PlanGestion.objects.filter(statut='archive').count()}")
    print(f"- Relations site-plan: {CorSitePg.objects.count()}")
    print(f"- Fichiers associés: {CorPgFichier.objects.count()}")
    
    print(f"\n🔗 Accès admin: http://localhost:8000/admin/plans/")


if __name__ == '__main__':
    create_test_plans()