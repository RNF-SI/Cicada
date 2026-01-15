"""
Script pour créer des plans de gestion avec les nomenclatures correctes.
"""
import os
import sys
import django
from datetime import datetime

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from apps.plans.models import PlanGestion, CorSitePg
from apps.users.models import Role, Site
from apps.core.models import Nomenclature

def create_plans_data():
    """Crée des plans de gestion avec les bonnes nomenclatures."""
    
    print("🏗️  Création des plans de gestion...")
    
    try:
        # Récupérer les utilisateurs
        admin = Role.objects.get(email='admin')
        marie = Role.objects.filter(email='marie.dupont@rnf.fr').first()
        
        # Récupérer les sites
        sites = Site.objects.all()
        if not sites:
            print("⚠️  Aucun site trouvé, création des plans annulée")
            return
        
        # Récupérer les nomenclatures
        eval_finale = Nomenclature.objects.get(id_nomenclature=46)  # Évaluation finale
        eval_aucune = Nomenclature.objects.get(id_nomenclature=45)  # Aucune évaluation
        eval_intermediaire = Nomenclature.objects.get(id_nomenclature=47)  # Évaluation intermédiaire
        
        redacteur_og = Nomenclature.objects.get(id_nomenclature=48)  # Organisme Gestionnaire
        redacteur_be = Nomenclature.objects.get(id_nomenclature=49)  # Bureau d'études
        
        # Créer des plans de gestion
        plans = [
            {
                'nom': 'Plan de gestion 2020-2030 - Réserve Naturelle de Camargue',
                'annee_debut': 2020,
                'annee_fin': 2030,
                'ct88': True,
                'risque_incendie': True,
                'id_evaluation': eval_finale,
                'id_redacteur_type': redacteur_og,
                'redacteur_nom': 'RNF - Service technique',
                'commentaire': 'Plan de gestion décennal pour la RN Camargue',
                'statut': 'valide',
                'id_utilisateur_ajout': admin
            },
            {
                'nom': 'Plan de gestion 2010-2020 - Réserve Naturelle des Aiguilles Rouges',
                'annee_debut': 2010,
                'annee_fin': 2020,
                'ct88': True,
                'risque_incendie': False,
                'id_evaluation': eval_intermediaire,
                'id_redacteur_type': redacteur_be,
                'redacteur_nom': 'Bureau d\'études Alpes Nature',
                'commentaire': 'Plan de gestion précédent, évaluation intermédiaire réalisée',
                'statut': 'archive',
                'id_utilisateur_ajout': marie or admin
            },
            {
                'nom': 'Plan de gestion inter-réserves Auvergne-Rhone-Alpes 2022-2027',
                'annee_debut': 2022,
                'annee_fin': 2027,
                'gestion_partagee': True,
                'ct88': False,
                'risque_incendie': True,
                'id_evaluation': eval_aucune,
                'id_redacteur_type': redacteur_og,
                'redacteur_nom': 'CEN AURA',
                'commentaire': 'Plan mutualisé pour plusieurs sites',
                'statut': 'draft',
                'id_utilisateur_ajout': admin
            }
        ]
        
        created_plans = []
        for plan_data in plans:
            plan, created = PlanGestion.objects.get_or_create(
                nom=plan_data['nom'],
                defaults=plan_data
            )
            if created:
                created_plans.append(plan)
                print(f"✅ Plan de gestion '{plan.nom}' créé")
                print(f"   - Évaluation: {plan.id_evaluation.label}")
                print(f"   - Type rédacteur: {plan.id_redacteur_type.label}")
        
        # Associer les plans aux sites
        if created_plans:
            # Plan 1: Camargue
            camargue = sites.filter(nom_site__icontains='camargue').first()
            if camargue and len(created_plans) > 0:
                CorSitePg.objects.get_or_create(
                    site=camargue,
                    plan_de_gestion=created_plans[0],
                    defaults={'rang': 1, 'commentaire': 'Site principal'}
                )
            
            # Plan 2: Aiguilles Rouges
            aiguilles = sites.filter(nom_site__icontains='aiguilles').first()
            if aiguilles and len(created_plans) > 1:
                CorSitePg.objects.get_or_create(
                    site=aiguilles,
                    plan_de_gestion=created_plans[1],
                    defaults={'rang': 1}
                )
            
            # Plan 3: Multi-sites
            if len(created_plans) > 2:
                for i, site in enumerate(sites[:2], 1):
                    CorSitePg.objects.get_or_create(
                        site=site,
                        plan_de_gestion=created_plans[2],
                        defaults={'rang': i, 'commentaire': f'Site {i} du plan mutualisé'}
                    )
        
        print(f"\n✅ {PlanGestion.objects.count()} plans de gestion créés au total")
        print(f"✅ {CorSitePg.objects.count()} associations site-plan créées")
        
    except Exception as e:
        print(f"⚠️  Erreur lors de la création des plans: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    create_plans_data()