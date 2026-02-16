"""
Seeder pour les plans de gestion.
"""
from datetime import date
from typing import Any, Dict, List

from apps.core.models import Nomenclature
from apps.plans.models import PlanGestion, CorSitePg, CorRolePlan
from apps.users.models import Role, Site

from .base import BaseSeeder


class PlansSeeder(BaseSeeder):
    """
    Cree les plans de gestion de test.

    Plans actifs (6):
    - Plan 2020-2030 Camargue (valide)
    - Plan 2018-2028 Aiguilles Rouges (valide)
    - Plan 2022-2032 Grand-Voyeux (draft)
    - Plan inter-sites Vercors-Ecrins 2021-2031 (valide)
    - Plan 2019-2029 Marais de Brouage (archive)
    - Plan 2023-2033 Lac de Remoray (draft)

    Plans archives (2):
    - Plan 2010-2020 Camargue ancien (archive)
    - Plan 2008-2018 Aiguilles Rouges ancien (archive)
    """

    name = 'plans'
    dependencies = ['users', 'sites', 'nomenclatures']

    def _get_plans_data(self, users: List[Role], sites: List[Site]) -> List[Dict]:
        """Retourne les donnees des plans de gestion."""
        # Recuperer les nomenclatures
        eval_int = Nomenclature.objects.filter(mnemonique='Intermediaire').first()
        eval_fin = Nomenclature.objects.filter(mnemonique='Finale').first()
        redac_gest = Nomenclature.objects.filter(mnemonique='OG').first()
        redac_be = Nomenclature.objects.filter(mnemonique='BE').first()

        return [
            # Plan Camargue: super_admin referent, referent.camargue referent, admin.rnf membre
            {
                'nom': 'Plan de gestion 2020-2030 - Reserve de la Camargue',
                'annee_debut': 2020,
                'annee_fin': 2030,
                'rang': 3,
                'surface': 13117,
                'statut': 'valide',
                'version': '2.0',
                'gestion_partagee': False,
                'ct88': True,
                'risque_incendie': True,
                'id_evaluation': eval_int,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Equipe Camargue',
                'redacteurs': 'Marie Dupont, Jean-Pierre Martin (RNF)',
                'relecteurs': 'CSRPN PACA, Commission Biodiversite RNF',
                'date_validation_cspn': date(2020, 3, 15),
                'commentaire': 'Plan de gestion valide pour la periode 2020-2030. '
                               '3eme plan successif, faisant suite au plan 2010-2020. '
                               'Enjeux principaux : habitats humides, flamant rose, '
                               'gestion hydraulique et activites traditionnelles.',
                'sites': [sites[0]],
                # Format: (user, is_referent)
                'membres': [
                    (users[0], True),   # super_admin - referent
                    (users[3], True),   # referent.camargue - referent
                    (users[1], False),  # admin.rnf - membre simple
                ]
            },
            # Plan Aiguilles Rouges: admin.rnf referent, super_admin membre
            {
                'nom': 'Plan de gestion 2018-2028 - Aiguilles Rouges',
                'annee_debut': 2018,
                'annee_fin': 2028,
                'rang': 2,
                'surface': 3279,
                'statut': 'valide',
                'version': '1.1',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_be,
                'redacteur_nom': 'Cabinet Natura Consulting',
                'redacteurs': 'Cabinet Natura Consulting (F. Leroy, A. Bernard)',
                'relecteurs': 'CSRPN Auvergne-Rhone-Alpes, DREAL ARA',
                'date_validation_cspn': date(2018, 6, 20),
                'commentaire': 'Plan de gestion en vigueur. Evaluation finale positive. '
                               'Enjeux centres sur les pelouses alpines, la faune '
                               'de haute montagne et la maitrise de la frequentation.',
                'sites': [sites[1]],
                'membres': [
                    (users[1], True),   # admin.rnf - referent
                    (users[0], False),  # super_admin - membre simple
                ]
            },
            # Plan Grand-Voyeux: admin.cen referent
            {
                'nom': 'Plan de gestion 2022-2032 - Grand-Voyeux',
                'annee_debut': 2022,
                'annee_fin': 2032,
                'statut': 'draft',
                'version': '1.0',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': None,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'CEN Auvergne-Rhone-Alpes',
                'commentaire': 'Plan en cours de redaction',
                'sites': [sites[2]],
                'membres': [
                    (users[2], True),   # admin.cen - referent
                ]
            },
            # Plan Vercors-Ecrins: referent.vercors et admin.cen referents
            {
                'nom': 'Plan de gestion inter-sites Vercors-Ecrins 2021-2031',
                'annee_debut': 2021,
                'annee_fin': 2031,
                'statut': 'valide',
                'version': '1.0',
                'gestion_partagee': True,
                'ct88': True,
                'risque_incendie': True,
                'id_evaluation': eval_int,
                'id_redacteur_type': redac_be,
                'redacteur_nom': 'DREAL Auvergne-Rhone-Alpes',
                'commentaire': 'Plan de gestion partage entre le PNR du Vercors et le Parc des Ecrins',
                'sites': [sites[3], sites[5]],  # Vercors + Scandola
                'membres': [
                    (users[4], True),   # referent.vercors - referent
                    (users[2], True),   # admin.cen - referent
                ]
            },
            # Plan Brouage: archive sans membres
            {
                'nom': 'Plan de gestion 2019-2029 - Marais de Brouage',
                'annee_debut': 2019,
                'annee_fin': 2029,
                'statut': 'archive',
                'version': '3.0',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'DREAL Nouvelle-Aquitaine',
                'commentaire': 'Plan archive - nouvelle version en preparation',
                'sites': [sites[4]],
                'membres': []
            },
            # Plan Lac de Remoray: super_admin referent, admin.rnf membre
            {
                'nom': 'Plan de gestion 2023-2033 - Lac de Remoray',
                'annee_debut': 2023,
                'annee_fin': 2033,
                'rang': 3,
                'surface': 286,
                'statut': 'draft',
                'version': '0.9',
                'gestion_partagee': False,
                'ct88': True,
                'risque_incendie': False,
                'id_evaluation': None,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Equipe Franche-Comte',
                'redacteurs': 'Sophie Moreau, Pierre Leclerc (DREAL BFC)',
                'relecteurs': 'CSRPN Bourgogne-Franche-Comte',
                'commentaire': 'Nouveau plan en cours de finalisation. '
                               'Enjeux principaux : qualite des eaux du lac, '
                               'tourbieres et prairies humides, balbuzard pecheur, '
                               'gestion des especes exotiques envahissantes.',
                'sites': [sites[6]],
                'membres': [
                    (users[0], True),   # super_admin - referent
                    (users[1], False),  # admin.rnf - membre simple
                ]
            },
            # Plans archives
            {
                'nom': 'Plan de gestion 2010-2020 - Camargue (ancien)',
                'annee_debut': 2010,
                'annee_fin': 2020,
                'rang': 2,
                'surface': 13117,
                'statut': 'archive',
                'version': '1.5',
                'gestion_partagee': False,
                'ct88': True,
                'risque_incendie': True,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Equipe Camargue',
                'redacteurs': 'P. Grillas, A. Crivelli (Tour du Valat / RNF)',
                'relecteurs': 'CSRPN PACA',
                'date_validation_cspn': date(2010, 1, 10),
                'commentaire': 'Ancien plan termine, remplace par le plan 2020-2030. '
                               'Evaluation finale realisee en 2019.',
                'sites': [sites[0]],
                'membres': []
            },
            {
                'nom': 'Plan de gestion 2008-2018 - Aiguilles Rouges (ancien)',
                'annee_debut': 2008,
                'annee_fin': 2018,
                'rang': 1,
                'surface': 3279,
                'statut': 'archive',
                'version': '2.0',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_be,
                'redacteur_nom': 'Bureau Natura 2000',
                'redacteurs': 'Bureau Natura 2000 (D. Petit)',
                'relecteurs': 'CSRPN Rhone-Alpes',
                'date_validation_cspn': date(2008, 9, 5),
                'commentaire': 'Plan archive suite a la mise en place du nouveau plan 2018-2028. '
                               '1er plan de gestion de la reserve.',
                'sites': [sites[1]],
                'membres': []
            },
        ]

    def seed(self) -> List[PlanGestion]:
        """
        Cree les plans de gestion de test.

        Returns:
            Liste des plans crees
        """
        self.log_header('Creation des plans de gestion')

        users = self.context.require('users')
        sites = self.context.require('sites')

        admin = users[0]  # Pour id_utilisateur_ajout
        plans_data = self._get_plans_data(users, sites)

        plans = []
        for plan_data in plans_data:
            plan_sites = plan_data.pop('sites')
            plan_membres = plan_data.pop('membres')

            plan, created = PlanGestion.objects.update_or_create(
                nom=plan_data['nom'],
                defaults={
                    **plan_data,
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin
                }
            )

            # Lier aux sites
            for i, site in enumerate(plan_sites):
                CorSitePg.objects.get_or_create(
                    site=site,
                    plan_de_gestion=plan,
                    defaults={'rang': i + 1}
                )

            # Ajouter les membres et referents via CorRolePlan
            referents_list = []
            for user, is_referent in plan_membres:
                CorRolePlan.objects.update_or_create(
                    id_role=user,
                    plan_de_gestion=plan,
                    defaults={'referent': is_referent}
                )
                if is_referent:
                    referents_list.append(user)

            # Aussi mettre à jour le ManyToMany referents pour compatibilité
            plan.referents.set(referents_list)

            plans.append(plan)
            status = "cree" if created else "mis a jour"
            sites_names = ", ".join([s.nom_site[:20] for s in plan_sites])
            membres_count = len(plan_membres)
            referents_count = len(referents_list)
            self.log_item(status, f"{plan.nom[:50]}... ({plan.statut})")
            if self.verbosity >= 2:
                self.stdout.write(f"              Sites: {sites_names}")
                self.stdout.write(f"              Membres: {membres_count} (dont {referents_count} referents)")

        self.log_summary(len(plans), 'plans de gestion')
        self.context.set('plans', plans)
        return plans

    def reset(self) -> int:
        """
        Supprime les plans de gestion de test.

        Returns:
            Nombre de plans supprimes
        """
        return PlanGestion.objects.all().delete()[0]

    def get_dry_run_summary(self) -> List[str]:
        """
        Resume des plans qui seraient crees.

        Returns:
            Liste des lignes du resume
        """
        return [
            '\nPlans de gestion actifs (6):',
            '  - Plan 2020-2030 Camargue (valide)',
            '  - Plan 2018-2028 Aiguilles Rouges (valide)',
            '  - Plan 2022-2032 Grand-Voyeux (draft)',
            '  - Plan inter-sites Vercors-Ecrins 2021-2031 (valide)',
            '  - Plan 2019-2029 Marais de Brouage (archive)',
            '  - Plan 2023-2033 Lac de Remoray (draft)',
            '\nPlans de gestion archives (2):',
            '  - Plan 2010-2020 Camargue ancien (archive)',
            '  - Plan 2008-2018 Aiguilles Rouges ancien (archive)',
        ]
