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

    Plans principaux (10) + plans historiques (6) pour chaines de versions.

    Chaines de versions:
    - Camargue (5 niveaux): Plan initial 2000-2010 (archive) → Eval mi-parcours 2000-2010 (archive)
      → Plan revise 2010-2020 (archive) → Plan actuel 2020-2030 (valide) → Eval mi-parcours (draft)
    - Aiguilles Rouges (4 niveaux): Plan initial 2008-2018 (archive) → Plan 2018-2028 (valide)
      → Eval mi-parcours (draft) → Plan revise (draft)
    - Vercors-Ecrins (3 niveaux): Plan initial 2011-2021 (archive)
      → Plan actuel 2021-2031 (valide) → Eval mi-parcours (draft)
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

        plans = [
            # Plan Camargue + Brouage: super_admin referent, referent.camargue referent, admin.rnf membre
            {
                'nom': 'Plan de gestion 2020-2030 - Zones humides mediterraneennes',
                'annee_debut': 2020,
                'annee_fin': 2030,
                'rang': 3,
                'surface': 13117,
                'statut': 'valide',
                'version': '2.0',
                'gestion_partagee': True,
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
                'sites': [sites[0], sites[4]],  # Camargue + Marais de Brouage
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
            # Plan Lac de Remoray + Grand-Voyeux: super_admin referent, admin.rnf membre
            {
                'nom': 'Plan de gestion 2023-2033 - Lacs et zones humides continentales',
                'annee_debut': 2023,
                'annee_fin': 2033,
                'rang': 3,
                'surface': 286,
                'statut': 'draft',
                'version': '0.9',
                'gestion_partagee': True,
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
                'sites': [sites[6], sites[2]],  # Lac de Remoray + Grand-Voyeux
                'membres': [
                    (users[0], True),   # super_admin - referent
                    (users[1], False),  # admin.rnf - membre simple
                ]
            },
            # Plans archives
            {
                'nom': 'Plan de gestion 2010-2020 - Camargue et Brouage (ancien)',
                'annee_debut': 2010,
                'annee_fin': 2020,
                'rang': 2,
                'surface': 13117,
                'statut': 'archive',
                'version': '1.5',
                'gestion_partagee': True,
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
                'sites': [sites[0], sites[4]],  # Camargue + Marais de Brouage
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

        # Plans supplementaires sur des sites RNF sans membres directs
        # (utiles pour tester "Demander l'acces")
        # Plan sur Camargue (sites[0]) : admin est lie au site → test acces direct
        plans.append({
            'nom': 'Plan complementaire 2024-2034 - Littoral et zones humides',
            'annee_debut': 2024,
            'annee_fin': 2034,
            'rang': 1,
            'surface': 5000,
            'statut': 'valide',
            'version': '1.0',
            'gestion_partagee': True,
            'ct88': False,
            'risque_incendie': False,
            'id_evaluation': eval_int,
            'id_redacteur_type': redac_gest,
            'redacteur_nom': 'RNF - Equipe Camargue',
            'commentaire': 'Plan complementaire pour les zones humides et littorales. '
                           'Sans membres directs, pour tester la demande d\'acces.',
            'sites': [sites[0], sites[5]],  # Camargue + Scandola
            'membres': []
        })
        # Plan sur Lac de Remoray (sites[6]) : admin n'est PAS lie au site → test acces combine
        plans.append({
            'nom': 'Plan de gestion 2025-2035 - Lac de Remoray phase 2',
            'annee_debut': 2025,
            'annee_fin': 2035,
            'rang': 1,
            'surface': 286,
            'statut': 'draft',
            'version': '0.1',
            'gestion_partagee': False,
            'ct88': False,
            'risque_incendie': False,
            'id_evaluation': None,
            'id_redacteur_type': redac_gest,
            'redacteur_nom': 'RNF - Equipe Franche-Comte',
            'commentaire': 'Plan en preparation pour la phase 2 du Lac de Remoray. '
                           'Sans membres directs, pour tester la demande d\'acces combinee.',
            'sites': [sites[6]],  # Lac de Remoray
            'membres': []
        })

        return plans

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

        # =====================================================================
        # Chaînes de versions complètes
        # =====================================================================
        plan_initial_type = Nomenclature.objects.filter(mnemonique='PLAN_INITIAL').first()
        eval_mi_type = Nomenclature.objects.filter(mnemonique='EVAL_MI_PARCOURS').first()
        plan_revise_type = Nomenclature.objects.filter(mnemonique='PLAN_REVISE').first()

        if not (plan_initial_type and eval_mi_type and plan_revise_type):
            self.log_item('skip', 'Nomenclatures Type document plan manquantes, chaînes de versions ignorées')
        else:
            self.stdout.write('')
            self.log_header('Chaînes de versions')

            # -----------------------------------------------------------------
            # Chaîne Camargue (5 niveaux) — la plus complète
            # Plan initial 2000-2010 (archive) → Eval mi-parcours (archive)
            # → Plan révisé 2010-2020 (archive, index 6) → Plan actuel 2020-2030 (valide, index 0)
            # → Eval mi-parcours en cours (draft)
            # -----------------------------------------------------------------

            # Noeud racine : Plan initial 2000-2010
            camargue_root, _ = PlanGestion.objects.update_or_create(
                nom='Plan de gestion 2000-2010 - Camargue (plan initial)',
                defaults={
                    'plan_parent': None,
                    'id_type_document': plan_initial_type,
                    'statut': 'archive',
                    'version': '1.0',
                    'annee_debut': 2000,
                    'annee_fin': 2010,
                    'rang': 1,
                    'surface': 13117,
                    'gestion_partagee': True,
                    'ct88': True,
                    'risque_incendie': True,
                    'id_evaluation': Nomenclature.objects.filter(mnemonique='Finale').first(),
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='OG').first(),
                    'redacteur_nom': 'RNF - Équipe historique Camargue',
                    'redacteurs': 'L. Hoffmann, P. Grillas (Tour du Valat)',
                    'relecteurs': 'CSRPN PACA',
                    'date_validation_cspn': date(2000, 5, 12),
                    'commentaire': 'Premier plan de gestion de la Réserve de Camargue. '
                                   'Diagnostic initial et premières orientations de gestion.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for s in [sites[0], sites[4]]:
                CorSitePg.objects.get_or_create(site=s, plan_de_gestion=camargue_root, defaults={'rang': 1})
            plans.append(camargue_root)

            # Eval mi-parcours du plan initial (archivée)
            camargue_eval1, _ = PlanGestion.objects.update_or_create(
                nom='Évaluation mi-parcours 2005 - Camargue',
                defaults={
                    'plan_parent': camargue_root,
                    'id_type_document': eval_mi_type,
                    'statut': 'archive',
                    'version': '1.1',
                    'annee_debut': 2000,
                    'annee_fin': 2010,
                    'rang': 1,
                    'surface': 13117,
                    'gestion_partagee': True,
                    'ct88': True,
                    'risque_incendie': True,
                    'id_evaluation': Nomenclature.objects.filter(mnemonique='Intermediaire').first(),
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='OG').first(),
                    'redacteur_nom': 'RNF - Équipe Camargue',
                    'commentaire': 'Évaluation à mi-parcours du plan 2000-2010. '
                                   'Bilan positif sur la gestion hydraulique, '
                                   'ajustements nécessaires sur le volet fréquentation.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for s in [sites[0], sites[4]]:
                CorSitePg.objects.get_or_create(site=s, plan_de_gestion=camargue_eval1, defaults={'rang': 1})
            plans.append(camargue_eval1)

            # Relier le plan révisé 2010-2020 (index 6) au plan initial
            plans[6].plan_parent = camargue_eval1
            plans[6].id_type_document = plan_revise_type
            plans[6].version = '2.0'
            plans[6].save(update_fields=['plan_parent', 'id_type_document', 'version'])

            # Relier le plan actuel 2020-2030 (index 0) au plan révisé 2010-2020
            plans[0].plan_parent = plans[6]
            plans[0].id_type_document = plan_revise_type
            plans[0].version = '3.0'
            plans[0].save(update_fields=['plan_parent', 'id_type_document', 'version'])

            # Eval mi-parcours du plan actuel (en cours, draft)
            camargue_eval2, _ = PlanGestion.objects.update_or_create(
                nom='Évaluation mi-parcours 2025 - Zones humides méditerranéennes',
                defaults={
                    'plan_parent': plans[0],
                    'id_type_document': eval_mi_type,
                    'statut': 'draft',
                    'version': '3.1',
                    'annee_debut': 2020,
                    'annee_fin': 2030,
                    'rang': 3,
                    'surface': 13117,
                    'gestion_partagee': True,
                    'ct88': True,
                    'risque_incendie': True,
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='OG').first(),
                    'redacteur_nom': 'RNF - Équipe Camargue',
                    'commentaire': 'Évaluation mi-parcours en cours de rédaction. '
                                   'Premiers résultats encourageants sur la restauration '
                                   'des habitats humides.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for s in [sites[0], sites[4]]:
                CorSitePg.objects.get_or_create(site=s, plan_de_gestion=camargue_eval2, defaults={'rang': 1})
            camargue_eval2.referents.set(plans[0].referents.all())
            plans.append(camargue_eval2)

            self.log_item('chain', 'Camargue: 5 niveaux (initial → eval → révisé → actuel → eval)')

            # -----------------------------------------------------------------
            # Chaîne Aiguilles Rouges (4 niveaux)
            # Plan initial 2008-2018 (archive, index 7) → Plan 2018-2028 (valide, index 1)
            # → Eval mi-parcours (valide) → Plan révisé (draft)
            # -----------------------------------------------------------------

            # Relier le plan initial (index 7)
            plans[7].id_type_document = plan_initial_type
            plans[7].version = '1.0'
            plans[7].save(update_fields=['id_type_document', 'version'])

            # Relier le plan actuel (index 1) au plan initial
            plans[1].plan_parent = plans[7]
            plans[1].id_type_document = plan_revise_type
            plans[1].version = '2.0'
            plans[1].save(update_fields=['plan_parent', 'id_type_document', 'version'])

            # Eval mi-parcours (validée — l'évaluation a été terminée)
            ar_eval, _ = PlanGestion.objects.update_or_create(
                nom='Évaluation mi-parcours 2023 - Aiguilles Rouges',
                defaults={
                    'plan_parent': plans[1],
                    'id_type_document': eval_mi_type,
                    'statut': 'valide',
                    'version': '2.1',
                    'annee_debut': 2018,
                    'annee_fin': 2028,
                    'rang': 2,
                    'surface': 3279,
                    'gestion_partagee': False,
                    'ct88': False,
                    'risque_incendie': False,
                    'id_evaluation': Nomenclature.objects.filter(mnemonique='Intermediaire').first(),
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='BE').first(),
                    'redacteur_nom': 'Cabinet Natura Consulting',
                    'date_validation_cspn': date(2023, 11, 15),
                    'commentaire': 'Évaluation mi-parcours validée. Bilan globalement positif. '
                                   'Recommandations de renforcer le suivi du gypaète barbu '
                                   'et de mieux encadrer la fréquentation estivale.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for cor_site in plans[1].sites.all():
                CorSitePg.objects.get_or_create(site=cor_site.site, plan_de_gestion=ar_eval, defaults={'rang': cor_site.rang})
            ar_eval.referents.set(plans[1].referents.all())
            plans.append(ar_eval)

            # Plan révisé suite à l'évaluation (en cours de rédaction)
            ar_revise, _ = PlanGestion.objects.update_or_create(
                nom='Plan de gestion révisé 2018-2028 - Aiguilles Rouges',
                defaults={
                    'plan_parent': ar_eval,
                    'id_type_document': plan_revise_type,
                    'statut': 'draft',
                    'version': '2.2',
                    'annee_debut': 2018,
                    'annee_fin': 2028,
                    'rang': 2,
                    'surface': 3279,
                    'gestion_partagee': False,
                    'ct88': False,
                    'risque_incendie': False,
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='BE').first(),
                    'redacteur_nom': 'Cabinet Natura Consulting',
                    'commentaire': 'Révision du plan suite à l\'évaluation mi-parcours. '
                                   'Intègre les nouvelles orientations : renforcement du suivi '
                                   'du gypaète, création d\'un zonage de quiétude estivale.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for cor_site in plans[1].sites.all():
                CorSitePg.objects.get_or_create(site=cor_site.site, plan_de_gestion=ar_revise, defaults={'rang': cor_site.rang})
            ar_revise.referents.set(plans[1].referents.all())
            plans.append(ar_revise)

            self.log_item('chain', 'Aiguilles Rouges: 4 niveaux (initial → révisé → eval → révisé)')

            # -----------------------------------------------------------------
            # Chaîne Vercors-Ecrins (3 niveaux)
            # Plan initial 2011-2021 (archive) → Plan actuel 2021-2031 (valide, index 3)
            # → Eval mi-parcours (draft)
            # -----------------------------------------------------------------

            vercors_root, _ = PlanGestion.objects.update_or_create(
                nom='Plan de gestion 2011-2021 - Vercors-Ecrins (plan initial)',
                defaults={
                    'plan_parent': None,
                    'id_type_document': plan_initial_type,
                    'statut': 'archive',
                    'version': '1.0',
                    'annee_debut': 2011,
                    'annee_fin': 2021,
                    'rang': 1,
                    'surface': plans[3].surface if plans[3].surface else None,
                    'gestion_partagee': True,
                    'ct88': True,
                    'risque_incendie': True,
                    'id_evaluation': Nomenclature.objects.filter(mnemonique='Finale').first(),
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='BE').first(),
                    'redacteur_nom': 'DREAL Rhône-Alpes',
                    'date_validation_cspn': date(2011, 3, 20),
                    'commentaire': 'Premier plan inter-sites couvrant le Vercors et les Écrins. '
                                   'Diagnostic partagé entre PNR et Parc National.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for cor_site in plans[3].sites.all():
                CorSitePg.objects.get_or_create(site=cor_site.site, plan_de_gestion=vercors_root, defaults={'rang': cor_site.rang})
            plans.append(vercors_root)

            # Relier le plan actuel (index 3) au plan initial
            plans[3].plan_parent = vercors_root
            plans[3].id_type_document = plan_revise_type
            plans[3].version = '2.0'
            plans[3].save(update_fields=['plan_parent', 'id_type_document', 'version'])

            # Eval mi-parcours du plan actuel (draft)
            vercors_eval, _ = PlanGestion.objects.update_or_create(
                nom='Évaluation mi-parcours 2026 - Vercors-Ecrins',
                defaults={
                    'plan_parent': plans[3],
                    'id_type_document': eval_mi_type,
                    'statut': 'draft',
                    'version': '2.1',
                    'annee_debut': 2021,
                    'annee_fin': 2031,
                    'rang': 1,
                    'gestion_partagee': True,
                    'ct88': True,
                    'risque_incendie': True,
                    'id_redacteur_type': Nomenclature.objects.filter(mnemonique='BE').first(),
                    'redacteur_nom': 'DREAL Auvergne-Rhône-Alpes',
                    'commentaire': 'Évaluation mi-parcours en préparation. '
                                   'Premiers retours terrain en cours de compilation.',
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin,
                }
            )
            for cor_site in plans[3].sites.all():
                CorSitePg.objects.get_or_create(site=cor_site.site, plan_de_gestion=vercors_eval, defaults={'rang': cor_site.rang})
            vercors_eval.referents.set(plans[3].referents.all())
            plans.append(vercors_eval)

            self.log_item('chain', 'Vercors-Ecrins: 3 niveaux (initial → révisé → eval)')

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
            '\nPlans de gestion principaux (10):',
            '  - Plan 2020-2030 Zones humides mediterraneennes (valide) - multisites',
            '  - Plan 2018-2028 Aiguilles Rouges (valide) - admin membre',
            '  - Plan 2022-2032 Grand-Voyeux (draft) - CEN',
            '  - Plan inter-sites Vercors-Ecrins 2021-2031 (valide) - multisites',
            '  - Plan 2019-2029 Marais de Brouage (archive) - DREAL',
            '  - Plan 2023-2033 Lacs et zones humides (draft) - multisites',
            '  - Plan 2010-2020 Camargue et Brouage ancien (archive) - multisites',
            '  - Plan 2008-2018 Aiguilles Rouges ancien (archive)',
            '  - Plan complementaire 2024-2034 Littoral (valide) - multisites, sans membres',
            '  - Plan 2025-2035 Lac de Remoray phase 2 (draft) - sans membres',
            '\nChaînes de versions (8 plans historiques):',
            '  Camargue (5 niveaux):',
            '    v1.0 Plan initial 2000-2010 (archive)',
            '    v1.1 → Eval mi-parcours 2005 (archive)',
            '    v2.0 → Plan révisé 2010-2020 (archive)',
            '    v3.0 → Plan actuel 2020-2030 (valide)',
            '    v3.1 → Eval mi-parcours 2025 (draft)',
            '  Aiguilles Rouges (4 niveaux):',
            '    v1.0 Plan initial 2008-2018 (archive)',
            '    v2.0 → Plan révisé 2018-2028 (valide)',
            '    v2.1 → Eval mi-parcours 2023 (valide)',
            '    v2.2 → Plan révisé (draft)',
            '  Vercors-Ecrins (3 niveaux):',
            '    v1.0 Plan initial 2011-2021 (archive)',
            '    v2.0 → Plan révisé 2021-2031 (valide)',
            '    v2.1 → Eval mi-parcours 2026 (draft)',
        ]
