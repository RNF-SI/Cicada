"""
Seeder minimal pour les plans Marais de Brouage, Scandola et Lac de Remoray.

Ces 3 plans existent côté `PlansSeeder` (créés par défaut) mais n'avaient
aucune chaîne Enjeu → OLT → NE → Indicateur → Métrique → Opération. Du coup
les pages Suivi des actions, Saisie et Bilan affichaient des écrans vides
pour eux.

Ce seeder ajoute, pour chaque plan, **2 enjeux + 1 chaîne minimale**
(1 OLT × 1 NE × 1 indicateur × 1 métrique) et **3 opérations** dont les
`annee_min` sont étalées sur le passé pour produire de la donnée historique.

Dépend de `enjeux` (au cas où EnjeuxSeeder serait en cours de réécriture).
S'exécute avant `realisations` qui se charge de remplir les réalisations.
"""
from datetime import date
from typing import List

from apps.core.models import Nomenclature
from apps.plans.models import PlanGestion
from apps.plans.models_enjeux import (
    Enjeu, ObjectifLongTerme, NiveauExigence,
)
from apps.plans.models_indicateurs import (
    Indicateur, Metrique, Mesure,
)
from apps.plans.models_operations import (
    Operation, CorOperationMetrique,
)

from .base import BaseSeeder
from ._geo_helpers import make_operation_geom


# Schéma minimal par plan : 2 enjeux + 1 chaîne complète + 3 ops.
# La 2e enjeu reste sans OLT/NE (illustre un cas de réflexion à compléter).
_PLAN_SPECS = [
    {
        'plan_keyword': 'Marais de Brouage',
        'plan_id_fallback': 638,
        'plan_year_min': 2014,
        'enjeux': [
            {
                'libelle': 'Conservation des vasières et zostères marines',
                'intitule_court': 'Vasières',
                'rang': 1, 'priorite': 'PRIORITE_1',
                'olt': "Maintenir l'étendue des herbiers de zostère naine",
                'ne': 'Surface des herbiers de zostère ≥ 80 ha',
                'indicateur': 'Surface des herbiers de zostère naine',
                'metrique': 'Surface mesurée (ha)',
                'unite': 'ha',
                'measures': [(2015, '76'), (2017, '78'), (2019, '80'), (2021, '81'), (2022, '82')],
            },
            {
                'libelle': 'Accueil migration anatidés et limicoles',
                'intitule_court': 'Avifaune migratoire',
                'rang': 2, 'priorite': 'PRIORITE_2',
                'olt': "Maintenir des conditions d'hivernage favorables",
                'ne': 'Effectif maximal hivernal anatidés ≥ 8 000 individus',
                'indicateur': "Effectif maximum hivernal d'anatidés",
                'metrique': 'Nombre maximum d\'individus comptés',
                'unite': 'individus',
                'measures': [(2016, '7400'), (2018, '8100'), (2020, '8500'), (2022, '8200')],
            },
        ],
        'operations': [
            {
                'code': 'BRG-CS01', 'cat': 'CS', 'prio': 'PRIORITE_1',
                'libelle': 'Cartographie annuelle des herbiers de zostère',
                'description': 'Relevés terrain + drone des herbiers de zostère naine '
                               'sur l\'ensemble du périmètre marin.',
                'annee_min': 2015, 'annee_max': 2023,
            },
            {
                'code': 'BRG-IP01', 'cat': 'IP', 'prio': 'PRIORITE_1',
                'libelle': 'Restauration des chenaux et reconnexions hydrauliques',
                'description': 'Travaux d\'entretien des chenaux tidaux pour favoriser '
                               'les flux de marées et l\'hydrologie des prés-salés.',
                'annee_min': 2017, 'annee_max': 2023,
            },
            {
                'code': 'BRG-SP01', 'cat': 'SP', 'prio': 'PRIORITE_2',
                'libelle': 'Police de la pêche à pied récréative',
                'description': 'Patrouilles et opérations de sensibilisation auprès '
                               'des pêcheurs à pied pour respect des quotas.',
                'annee_min': 2019, 'annee_max': 2023,
            },
        ],
    },
    {
        'plan_keyword': 'Scandola',
        'plan_id_fallback': 630,
        'plan_year_min': 2016,
        'enjeux': [
            {
                'libelle': 'Préservation des habitats benthiques rocheux',
                'intitule_court': 'Habitats benthiques',
                'rang': 1, 'priorite': 'PRIORITE_1',
                'olt': 'Maintenir l\'intégrité des coralligènes profonds',
                'ne': 'Recouvrement coralligène ≥ 60% sur les stations témoins',
                'indicateur': 'Recouvrement du coralligène sur les stations témoins',
                'metrique': 'Recouvrement moyen (%)',
                'unite': '%',
                'measures': [(2017, '55'), (2019, '58'), (2021, '61'), (2023, '63'), (2024, '64')],
            },
            {
                'libelle': 'Régulation de la fréquentation maritime',
                'intitule_court': 'Fréquentation',
                'rang': 2, 'priorite': 'PRIORITE_2',
                'olt': 'Réduire la pression nautique sur les zones sensibles',
                'ne': 'Pic journalier ≤ 80 embarcations en haute saison',
                'indicateur': 'Comptage embarcations zone réserve (haute saison)',
                'metrique': 'Pic journalier (bateaux)',
                'unite': 'bateaux/jour',
                'measures': [(2018, '120'), (2020, '95'), (2022, '85'), (2024, '78')],
            },
        ],
        'operations': [
            {
                'code': 'SCA-CS01', 'cat': 'CS', 'prio': 'PRIORITE_1',
                'libelle': 'Suivi photographique annuel des stations coralligène',
                'description': 'Plongées + photogrammétrie sur 12 stations témoins '
                               'pour suivre la dynamique du coralligène.',
                'annee_min': 2017, 'annee_max': 2025,
            },
            {
                'code': 'SCA-SP01', 'cat': 'SP', 'prio': 'PRIORITE_1',
                'libelle': 'Surveillance maritime des zones réglementées',
                'description': 'Patrouilles nautiques en haute saison pour faire '
                               'respecter les interdictions de mouillage et de pêche.',
                'annee_min': 2018, 'annee_max': 2025,
            },
            {
                'code': 'SCA-CC01', 'cat': 'CC', 'prio': 'PRIORITE_2',
                'libelle': 'Création de supports pédagogiques pour les opérateurs nautiques',
                'description': 'Production de fiches et vidéos à destination des '
                               'compagnies de bateaux promenade pour limiter le dérangement.',
                'annee_min': 2020, 'annee_max': 2025,
            },
        ],
    },
    {
        'plan_keyword': 'Lac de Remoray (à étendre)',
        'plan_id_fallback': 631,
        'plan_year_min': 2017,
        'enjeux': [
            {
                'libelle': 'Conservation des roselières du lac',
                'intitule_court': 'Roselières',
                'rang': 1, 'priorite': 'PRIORITE_1',
                'olt': 'Stopper la régression des roselières lacustres',
                'ne': 'Surface des roselières ≥ surface 2018',
                'indicateur': 'Surface des roselières (ha)',
                'metrique': 'Surface roselières mesurée',
                'unite': 'ha',
                'measures': [(2017, '12.6'), (2018, '12.5'), (2020, '12.3'), (2022, '12.1'), (2024, '12.0')],
            },
            {
                'libelle': 'Maintien du caractère oligotrophe du lac',
                'intitule_court': 'Lac oligotrophe',
                'rang': 2, 'priorite': 'PRIORITE_1',
                'olt': 'Maintenir le bon état écologique du lac',
                'ne': 'Phosphore total < 25 µg/L (moyenne annuelle)',
                'indicateur': 'Concentration en phosphore total',
                'metrique': 'Phosphore total (µg/L)',
                'unite': 'µg/L',
                'measures': [(2018, '21'), (2020, '23'), (2022, '22'), (2024, '20')],
            },
        ],
        'operations': [
            {
                'code': 'REM2-CS01', 'cat': 'CS', 'prio': 'PRIORITE_1',
                'libelle': 'Suivi photogrammétrique des roselières par drone',
                'description': 'Acquisition annuelle par drone et mesure '
                               'de l\'évolution des contours des roselières.',
                'annee_min': 2017, 'annee_max': 2026,
            },
            {
                'code': 'REM2-IP01', 'cat': 'IP', 'prio': 'PRIORITE_1',
                'libelle': 'Faucardage sélectif des secteurs envahis',
                'description': 'Coupes mécaniques ciblées dans les secteurs colonisés '
                               'par les espèces compétitrices pour relâcher la pression.',
                'annee_min': 2019, 'annee_max': 2026,
            },
            {
                'code': 'REM2-PA01', 'cat': 'PA', 'prio': 'PRIORITE_2',
                'libelle': 'Animations grand public sur les zones humides',
                'description': 'Sorties guidées et ateliers nature en partenariat '
                               'avec les écoles riveraines.',
                'annee_min': 2020, 'annee_max': 2026,
            },
        ],
    },
]


class MinimalPlansSeeder(BaseSeeder):
    """
    Crée une chaîne minimale pour 3 plans qui n'avaient aucune donnée :
    Marais de Brouage, Scandola, Lac de Remoray.

    Permet d'alimenter les pages Suivi/Saisie/Bilan avec des opérations
    couvrant des années passées pour ces plans-là aussi.
    """

    name = 'minimal_plans'
    dependencies = ['enjeux']

    def _get_nomenclature(self, type_mnemonique: str, mnemonique: str) -> Nomenclature:
        return Nomenclature.objects.filter(
            id_type__mnemonique=type_mnemonique,
            mnemonique=mnemonique,
        ).first()

    def _find_plan(self, keyword: str, fallback_id: int) -> PlanGestion:
        plan = PlanGestion.objects.filter(nom__icontains=keyword).first()
        if plan:
            return plan
        try:
            return PlanGestion.objects.get(pk=fallback_id)
        except PlanGestion.DoesNotExist:
            return None

    def seed(self) -> dict:
        self.log_header('Création hiérarchie minimale (Brouage, Scandola, Remoray)')

        users = self.context.require('users')
        admin = users[0] if users else None

        # Nomenclatures partagées
        cat_enjeu = self._get_nomenclature('CATEGORIE_ENJEU', 'ENJEU')
        type_ind_etat = self._get_nomenclature('TYPE_INDICATEUR', 'ETAT')
        type_met_num = self._get_nomenclature('TYPE_METRIQUE', 'NUMERIQUE')

        if not cat_enjeu or not type_ind_etat or not type_met_num:
            self.log(
                '  Nomenclatures (CATEGORIE_ENJEU/TYPE_INDICATEUR/TYPE_METRIQUE) '
                'manquantes — seeder ignoré.',
                'WARNING',
            )
            return {}

        # Priorités enjeu et opération + catégories d'action réserve
        prios_enjeu = {
            mn: self._get_nomenclature('IMPORTANCE_ENJEU', mn)
            for mn in ('PRIORITE_1', 'PRIORITE_2', 'PRIORITE_3')
        }
        prios_op = {
            mn: self._get_nomenclature('PRIORITE_OPERATION', mn)
            for mn in ('PRIORITE_1', 'PRIORITE_2', 'PRIORITE_3')
        }
        cat_reserve = {
            code: self._get_nomenclature('CATEGORIE_ACTION_RESERVE', code)
            for code in ('CS', 'IP', 'SP', 'CC', 'PA', 'MS')
        }

        created_operations: List[Operation] = []
        created_enjeux = []

        for spec in _PLAN_SPECS:
            plan = self._find_plan(spec['plan_keyword'], spec['plan_id_fallback'])
            if not plan:
                self.log_item('—', f'Plan introuvable : {spec["plan_keyword"]}')
                continue

            self.log_item('plan', f'{plan.id_pg} {plan.nom[:50]}')

            # ===== Enjeux + chaîne complète =====
            for e_spec in spec['enjeux']:
                enjeu, _ = Enjeu.objects.update_or_create(
                    id_pg=plan,
                    libelle=e_spec['libelle'],
                    defaults={
                        'id_categorie': cat_enjeu,
                        'intitule_court': e_spec['intitule_court'],
                        'rang': e_spec['rang'],
                        'id_importance': prios_enjeu.get(e_spec['priorite']),
                        'categorie_ecologique': True,
                        'habitat': True,
                        'id_utilisateur_ajout': admin,
                    },
                )
                created_enjeux.append(enjeu)

                if not e_spec.get('olt'):
                    continue

                olt, _ = ObjectifLongTerme.objects.update_or_create(
                    id_enjeu=enjeu, libelle=e_spec['olt'],
                    defaults={'id_utilisateur_ajout': admin},
                )
                ne, _ = NiveauExigence.objects.update_or_create(
                    id_olt=olt, libelle=e_spec['ne'],
                    defaults={'id_utilisateur_ajout': admin},
                )
                indicateur, _ = Indicateur.objects.update_or_create(
                    id_ne=ne, nom_indicateur=e_spec['indicateur'],
                    defaults={
                        'type_indicateur': type_ind_etat,
                        'id_utilisateur_ajout': admin,
                    },
                )
                metrique, _ = Metrique.objects.update_or_create(
                    id_indicateur=indicateur,
                    nom_metrique=e_spec['metrique'],
                    defaults={
                        'type_metrique': type_met_num,
                        'unite': e_spec.get('unite', ''),
                        'sens_variation': 'CROISSANT',
                        'id_utilisateur_ajout': admin,
                    },
                )
                # Stocker l'id_metrique dans le spec pour le lier aux ops
                e_spec['_metrique'] = metrique

                # Mesures de référence
                for year, valeur in e_spec.get('measures', []):
                    Mesure.objects.update_or_create(
                        id_metrique=metrique, date_mesure=date(year, 6, 15),
                        defaults={'valeur': valeur, 'id_utilisateur_ajout': admin},
                    )

            # ===== Opérations =====
            # Chaque opération du plan est rattachée à TOUTES les métriques
            # créées (en pratique : 2 métriques = 2 indicateurs de réponse
            # dans le formulaire de saisie).
            all_metriques = [e['_metrique'] for e in spec['enjeux'] if e.get('_metrique')]
            if not all_metriques:
                continue

            for op_idx, op_spec in enumerate(spec['operations']):
                op, _ = Operation.objects.update_or_create(
                    code_operation=op_spec['code'],
                    defaults={
                        'libelle': op_spec['libelle'],
                        'id_priorite': prios_op.get(op_spec['prio']),
                        'id_categorie_action_reserve': cat_reserve.get(op_spec['cat']),
                        'description': op_spec['description'],
                        'annee_min': op_spec['annee_min'],
                        'annee_max': op_spec['annee_max'],
                        'id_utilisateur_ajout': admin,
                    },
                )
                # Emprise spatiale au format Site (MultiPolygon SRID 4326)
                if not op.geom:
                    op.geom = make_operation_geom(op_spec['code'], op_idx)
                    op.save(update_fields=['geom'])

                for m in all_metriques:
                    CorOperationMetrique.objects.get_or_create(
                        id_operation=op, id_metrique=m,
                    )
                created_operations.append(op)
                self.log_item(
                    '—',
                    f'  Op {op_spec["code"]} {op_spec["annee_min"]}-{op_spec["annee_max"]} '
                    f'({op_spec["cat"]})',
                )

        # Les OperationAnnee + ventilation seront créées par EnjeuxSeeder en mode
        # idempotent ? Non — EnjeuxSeeder a déjà tourné. Il faut les créer ici.
        self._create_annees_for(created_operations, admin, prios_op, cat_reserve)

        # Enrichissement supplémentaire : le plan Lacs et zones humides (déjà
        # construit par EnjeuxSeeder) reçoit une 2e métrique par opération et
        # des mesures historiques densifiées, comme Brouage/Scandola/Remoray.
        nb_lacs_ops, nb_lacs_mesures = self._enrich_lacs(admin)

        self.log_summary(len(created_enjeux), 'enjeux créés')
        self.log_summary(len(created_operations), 'opérations créées')
        self.log_summary(nb_lacs_ops, 'ops Lacs enrichies avec une 2e métrique')
        self.log_summary(nb_lacs_mesures, 'mesures historiques ajoutées sur Lacs')

        return {
            'minimal_plans_enjeux': created_enjeux,
            'minimal_plans_operations': created_operations,
        }

    def _enrich_lacs(self, admin) -> tuple[int, int]:
        """
        Pour le plan "Lacs et zones humides continentales" (déjà construit par
        EnjeuxSeeder), s'assure que chaque opération est rattachée à au moins
        2 métriques distinctes du plan + ajoute des mesures historiques pour
        chaque métrique sur 2017-2024.

        Retourne (nb_ops_enrichies, nb_mesures_ajoutées).
        """
        from datetime import date
        from apps.plans.models_indicateurs import Metrique, Mesure

        plan = PlanGestion.objects.filter(
            slug='plan-de-gestion-2023-2033-lacs-et-zones-humides-continentales',
        ).first()
        if not plan:
            return 0, 0

        # Toutes les métriques rattachées au plan via la chaîne enjeux.
        metriques_plan = list(
            Metrique.objects.filter(
                id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan,
            ).distinct()
        )
        if len(metriques_plan) < 2:
            return 0, 0

        # Opérations du plan
        ops = (
            Operation.objects.filter(
                metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan,
            ).distinct()
        )

        nb_ops_enriched = 0
        for idx, op in enumerate(ops):
            current_metriques_ids = set(op.metriques.values_list('id_metrique', flat=True))
            if len(current_metriques_ids) >= 2:
                continue
            # Choisir une 2e métrique différente de celles déjà liées (rotation déterministe).
            candidate = next(
                (m for i, m in enumerate(metriques_plan)
                 if m.id_metrique not in current_metriques_ids
                 and (i + idx) % len(metriques_plan) != 0),
                None,
            ) or next(
                (m for m in metriques_plan if m.id_metrique not in current_metriques_ids),
                None,
            )
            if candidate is None:
                continue
            CorOperationMetrique.objects.get_or_create(
                id_operation=op, id_metrique=candidate,
            )
            nb_ops_enriched += 1

        # Mesures historiques : pour chaque métrique du plan, garantir au moins
        # 4 mesures réparties sur 2017-2024 (idempotent).
        target_years = [2017, 2019, 2021, 2023]
        nb_mesures_added = 0
        for m_idx, met in enumerate(metriques_plan):
            for y_idx, year in enumerate(target_years):
                # Valeur déterministe variée selon la métrique et l'année
                base = 50 + (m_idx % 5) * 20
                drift = (y_idx - 1) * 5  # tendance temporelle
                valeur = f'{base + drift}'
                _, created = Mesure.objects.get_or_create(
                    id_metrique=met,
                    date_mesure=date(year, 9, 15),
                    defaults={
                        'valeur': valeur,
                        'commentaire': f'Mesure historique (seed Lacs) — {year}',
                        'id_utilisateur_ajout': admin,
                    },
                )
                if created:
                    nb_mesures_added += 1

        # Enrichissement ciblé sur OLT 1/2/3 + OO 1/2 (demande utilisateur).
        # On garantit la cohérence thématique des liaisons op ↔ métriques :
        # chaque opération rattachée à un OLT/OO ciblé est aussi liée à TOUTES
        # les métriques de cet OLT/OO (pas juste une au hasard).
        extra_ops, extra_mes = self._enrich_target_olts_oos_lacs(plan, admin)
        nb_ops_enriched += extra_ops
        nb_mesures_added += extra_mes

        # Création de nouveaux indicateurs de réponse sur chaque OLT/OO ciblé
        # (demande utilisateur du 2026-05-28).
        new_inds, new_mes = self._add_response_indicators_lacs(plan, admin)
        if new_mes:
            nb_mesures_added += new_mes
        self.log_item('—', f'{new_inds} nouveaux indicateurs de réponse créés sur OLT/OO ciblés')

        return nb_ops_enriched, nb_mesures_added

    def _enrich_target_olts_oos_lacs(self, plan, admin) -> tuple[int, int]:
        """
        Enrichissement ciblé sur les OLTs et OOs prioritaires du plan Lacs :

          - OLT 1 : "Atteindre le bon état écologique du lac"
          - OLT 2 : "Restaurer le fonctionnement hydrologique des tourbières"
          - OLT 3 : "Garantir la quiétude du site en période de migration"
          - OO 1  : "Maintenir le niveau piézométrique des tourbières"
          - OO 2  : "Restaurer les communautés végétales turficoles"

        Pour chacun :
          - lier chaque opération rattachée à ce parent à TOUTES ses métriques
            propres (cohérence thématique des indicateurs de réponse) ;
          - densifier les mesures historiques sur 8 années (2017-2024) au lieu
            de 4 pour valoriser la timeline ;
          - agrandir le polygone d'emprise des opérations ciblées pour les
            rendre plus visibles sur la carte (~2-3 km de côté).
        """
        from datetime import date
        from apps.plans.models_enjeux import ObjectifLongTerme, ObjectifOperationnel
        from apps.plans.models_indicateurs import Metrique, Mesure
        from django.contrib.gis.geos import MultiPolygon, Polygon

        target_olt_libelles = [
            'Atteindre le bon état écologique du lac',
            'Restaurer le fonctionnement hydrologique des tourbières',
            'Garantir la quiétude du site en période de migration',
        ]
        target_oo_libelles = [
            'Maintenir le niveau piézométrique des tourbières',
            'Restaurer les communautés végétales turficoles',
        ]

        olts = ObjectifLongTerme.objects.filter(
            id_enjeu__id_pg=plan, libelle__in=target_olt_libelles,
        ).distinct()
        oos = ObjectifOperationnel.objects.filter(
            pressions__id_facteur_influence__enjeux__id_pg=plan,
            libelle__in=target_oo_libelles,
        ).distinct()

        nb_links = 0
        targeted_metriques: set = set()

        # --- OLTs ciblés ---------------------------------------------------
        for olt in olts:
            metriques_olt = Metrique.objects.filter(
                id_indicateur__id_ne__id_olt=olt,
            ).distinct()
            ops_olt = Operation.objects.filter(
                metriques__id_indicateur__id_ne__id_olt=olt,
            ).distinct()
            for op in ops_olt:
                for met in metriques_olt:
                    _, created = CorOperationMetrique.objects.get_or_create(
                        id_operation=op, id_metrique=met,
                    )
                    if created:
                        nb_links += 1
                    targeted_metriques.add(met.id_metrique)

        # --- OOs ciblés (via Résultats Attendus) ---------------------------
        for oo in oos:
            metriques_oo = Metrique.objects.filter(
                id_indicateur__id_resultat_attendu__id_oo=oo,
            ).distinct()
            ops_oo = Operation.objects.filter(
                metriques__id_indicateur__id_resultat_attendu__id_oo=oo,
            ).distinct()
            for op in ops_oo:
                for met in metriques_oo:
                    _, created = CorOperationMetrique.objects.get_or_create(
                        id_operation=op, id_metrique=met,
                    )
                    if created:
                        nb_links += 1
                    targeted_metriques.add(met.id_metrique)

        # --- Mesures historiques 2017-2024 sur les métriques ciblées -------
        extra_years = [2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024]
        nb_mesures = 0
        for met_id in targeted_metriques:
            met = Metrique.objects.get(pk=met_id)
            for y_idx, year in enumerate(extra_years):
                base = 60 + (met_id % 7) * 15
                drift = (y_idx - 3) * 3
                _, created = Mesure.objects.get_or_create(
                    id_metrique=met, date_mesure=date(year, 6, 30),
                    defaults={
                        'valeur': f'{base + drift}',
                        'commentaire': f'Suivi annuel OLT/OO ciblé (seed) — {year}',
                        'id_utilisateur_ajout': admin,
                    },
                )
                if created:
                    nb_mesures += 1

        # --- Emprises agrandies pour les ops sous OLTs/OOs ciblés ----------
        # Polygone plus grand (~2-3 km) pour mieux ressortir sur la carte.
        ops_to_resize = Operation.objects.filter(
            metriques__id_metrique__in=targeted_metriques,
        ).distinct()

        # Centre Remoray (utilisé dans _geo_helpers pour préfixe REM)
        center_lon, center_lat = 6.27, 46.77
        for idx, op in enumerate(ops_to_resize):
            dx = (idx % 5) * 0.012
            dy = (idx // 5) * 0.012
            half = 0.013 + (idx % 3) * 0.005  # ~1.5 à 3 km de côté
            cx = center_lon + dx
            cy = center_lat + dy
            coords = [
                (cx - half, cy - half),
                (cx + half, cy - half),
                (cx + half, cy + half),
                (cx - half, cy + half),
                (cx - half, cy - half),
            ]
            op.geom = MultiPolygon(Polygon(coords, srid=4326), srid=4326)
            op.save(update_fields=['geom'])

        return nb_links, nb_mesures

    def _add_response_indicators_lacs(self, plan, admin) -> tuple[int, int]:
        """
        Crée des indicateurs de réponse supplémentaires sur les OLT/OO ciblés
        du plan Lacs, avec leurs métriques et mesures historiques.

        Retourne (nb_indicateurs_créés, nb_mesures_créées).
        """
        from datetime import date
        from apps.plans.models_enjeux import ObjectifLongTerme, ObjectifOperationnel, NiveauExigence, ResultatAttendu
        from apps.plans.models_indicateurs import Indicateur, Metrique, Mesure

        type_ind_reponse = (
            Nomenclature.objects.filter(
                id_type__mnemonique='TYPE_INDICATEUR', mnemonique='REPONSE',
            ).first()
            or Nomenclature.objects.filter(
                id_type__mnemonique='TYPE_INDICATEUR', mnemonique='ETAT',
            ).first()
        )
        type_met_num = Nomenclature.objects.filter(
            id_type__mnemonique='TYPE_METRIQUE', mnemonique='NUMERIQUE',
        ).first()
        if not type_ind_reponse or not type_met_num:
            return 0, 0

        # Définition des nouveaux indicateurs à créer.
        # Structure : { parent_kind: 'olt' | 'oo', libelle_parent: ..., indicateurs: [...] }
        specs = [
            {
                'parent_kind': 'olt',
                'parent_libelle': 'Atteindre le bon état écologique du lac',
                'indicateurs': [
                    {
                        'nom': 'Transparence du lac (disque de Secchi)',
                        'description': "Profondeur moyenne de disparition du disque de Secchi mesurée sur 3 stations.",
                        'metrique': 'Profondeur moyenne (m)',
                        'unite': 'm',
                        'cible': '≥ 5 m',
                        'measures': [(2018, '4.2'), (2020, '4.5'), (2022, '4.4'), (2024, '4.6')],
                    },
                    {
                        'nom': 'Concentration en chlorophylle a',
                        'description': 'Indicateur d\'eutrophisation : concentration moyenne annuelle.',
                        'metrique': 'Chlorophylle a (µg/L)',
                        'unite': 'µg/L',
                        'cible': '≤ 5 µg/L',
                        'measures': [(2018, '8.5'), (2020, '7.2'), (2022, '6.8'), (2024, '6.5')],
                    },
                ],
            },
            {
                'parent_kind': 'olt',
                'parent_libelle': 'Restaurer le fonctionnement hydrologique des tourbières',
                'indicateurs': [
                    {
                        'nom': 'Surface en eau libre des dépressions humides',
                        'description': 'Surface mesurée des dépressions en eau au printemps.',
                        'metrique': 'Surface en eau (ha)',
                        'unite': 'ha',
                        'cible': '≥ 3 ha',
                        'measures': [(2019, '2.1'), (2021, '2.4'), (2023, '2.7')],
                    },
                ],
            },
            {
                'parent_kind': 'olt',
                'parent_libelle': 'Garantir la quiétude du site en période de migration',
                'indicateurs': [
                    {
                        'nom': 'Délai moyen avant première installation de balbuzard',
                        'description': 'Nombre de jours après l\'ouverture saisonnière avant la 1re halte observée.',
                        'metrique': 'Délai (jours)',
                        'unite': 'jours',
                        'cible': '≤ 5 jours',
                        'measures': [(2019, '12'), (2021, '9'), (2023, '7')],
                    },
                ],
            },
            {
                'parent_kind': 'oo',
                'parent_libelle': 'Maintenir le niveau piézométrique des tourbières',
                'indicateurs': [
                    {
                        'nom': 'Amplitude saisonnière des niveaux piézométriques',
                        'description': 'Différence max-min annuelle des niveaux dans les piézomètres témoins.',
                        'metrique': 'Amplitude (cm)',
                        'unite': 'cm',
                        'cible': '≤ 25 cm',
                        'measures': [(2018, '38'), (2020, '34'), (2022, '32'), (2024, '30')],
                    },
                ],
            },
            {
                'parent_kind': 'oo',
                'parent_libelle': 'Restaurer les communautés végétales turficoles',
                'indicateurs': [
                    {
                        'nom': 'Recouvrement des Sphagnum sur les placettes témoins',
                        'description': 'Pourcentage de recouvrement des sphaignes mesuré par placette.',
                        'metrique': 'Recouvrement Sphagnum (%)',
                        'unite': '%',
                        'cible': '≥ 60 %',
                        'measures': [(2019, '42'), (2021, '48'), (2023, '53')],
                    },
                ],
            },
        ]

        nb_inds, nb_mes = 0, 0
        for spec in specs:
            # Trouver le NE ou RA parent
            parent_ne, parent_ra = None, None
            if spec['parent_kind'] == 'olt':
                olt = ObjectifLongTerme.objects.filter(
                    id_enjeu__id_pg=plan, libelle=spec['parent_libelle'],
                ).first()
                if not olt:
                    continue
                parent_ne = NiveauExigence.objects.filter(id_olt=olt).first()
                if not parent_ne:
                    continue
            else:
                oo = ObjectifOperationnel.objects.filter(
                    pressions__id_facteur_influence__enjeux__id_pg=plan,
                    libelle=spec['parent_libelle'],
                ).first()
                if not oo:
                    continue
                parent_ra = ResultatAttendu.objects.filter(id_oo=oo).first()
                if not parent_ra:
                    continue

            for ind_spec in spec['indicateurs']:
                # Indicateur
                ind, created = Indicateur.objects.get_or_create(
                    nom_indicateur=ind_spec['nom'],
                    id_ne=parent_ne,
                    id_resultat_attendu=parent_ra,
                    defaults={
                        'type_indicateur': type_ind_reponse,
                        'description': ind_spec['description'],
                        'id_utilisateur_ajout': admin,
                    },
                )
                if created:
                    nb_inds += 1

                # Métrique (avec cible / état de référence pour la vue globale d'action)
                cible = ind_spec.get('cible', '')
                met, met_created = Metrique.objects.get_or_create(
                    id_indicateur=ind,
                    nom_metrique=ind_spec['metrique'],
                    defaults={
                        'type_metrique': type_met_num,
                        'unite': ind_spec['unite'],
                        'sens_variation': 'CROISSANT',
                        'etat_reference': cible,
                        'id_utilisateur_ajout': admin,
                    },
                )
                # Backfill idempotent de la cible si la métrique existait déjà sans.
                if not met_created and cible and not (met.etat_reference or '').strip():
                    met.etat_reference = cible
                    met.save(update_fields=['etat_reference'])

                # Mesures
                for year, valeur in ind_spec['measures']:
                    _, c = Mesure.objects.get_or_create(
                        id_metrique=met, date_mesure=date(year, 7, 1),
                        defaults={
                            'valeur': valeur,
                            'commentaire': f'Mesure indicateur de réponse (seed Lacs) — {year}',
                            'id_utilisateur_ajout': admin,
                        },
                    )
                    if c:
                        nb_mes += 1

                # Lier la métrique aux opérations rattachées à ce parent
                # (pour qu'elle apparaisse dans le formulaire de saisie)
                if parent_ne:
                    ops_to_link = Operation.objects.filter(
                        metriques__id_indicateur__id_ne__id_olt=parent_ne.id_olt,
                    ).distinct()
                else:
                    ops_to_link = Operation.objects.filter(
                        metriques__id_indicateur__id_resultat_attendu__id_oo=parent_ra.id_oo,
                    ).distinct()
                for op in ops_to_link:
                    CorOperationMetrique.objects.get_or_create(
                        id_operation=op, id_metrique=met,
                    )

        return nb_inds, nb_mes

    def _create_annees_for(self, operations, admin, prios_op, cat_reserve):
        """
        Crée les OperationAnnee + ventilation pour chacune des opérations
        ajoutées par ce seeder. Réutilise la logique simple : périodicité=True
        annuelle, budget et ETP issus de profils variés (reproduit l'esprit
        d'EnjeuxSeeder mais en plus court).
        """
        from apps.plans.models_operations import OperationAnnee, OperationAnneeOrganisme
        from apps.users.models import BibOrganismes

        # Profils budget / ETP pour varier les chiffres entre opérations.
        budget_profiles = [
            {'base': 1500, 'var': 300},
            {'base': 800, 'var': 200},
            {'base': 2500, 'var': 500},
        ]
        etp_profiles = [4, 8, 12, 6, 10]

        # Modes de ventilation alternés pour couvrir les 4 cas.
        ventilation_modes = ['none', 'by_org', 'by_type', 'by_org_type']

        organismes = list(BibOrganismes.objects.all()[:2])  # 2 orgs pour ventilation

        for idx, op in enumerate(operations):
            v_mode = ventilation_modes[idx % 4]
            op.ventilation_mode = v_mode
            op.save(update_fields=['ventilation_mode'])

            if not op.annee_min or not op.annee_max:
                continue

            profile = budget_profiles[idx % len(budget_profiles)]
            etp_base = etp_profiles[idx % len(etp_profiles)]

            for offset, year in enumerate(range(op.annee_min, op.annee_max + 1)):
                budget = profile['base'] + (offset * profile['var'] // 4)
                etp = etp_base + (offset // 3)

                defaults = {'periodicite': True}
                if v_mode == 'none':
                    defaults['budget'] = budget
                    defaults['etp'] = etp
                elif v_mode == 'by_type':
                    defaults['budget_fonctionnement'] = round(budget * 0.6, 2)
                    defaults['budget_investissement'] = round(budget * 0.4, 2)
                    defaults['budget'] = budget
                    defaults['etp'] = etp
                else:
                    # by_org / by_org_type : budget total sera l'agrégation des orgs.
                    defaults['budget'] = budget
                    defaults['etp'] = etp

                oa, _ = OperationAnnee.objects.update_or_create(
                    id_operation=op, annee=year, defaults=defaults,
                )

                # Ventilation par organismes
                if v_mode in ('by_org', 'by_org_type') and organismes:
                    per_org_budget = budget / len(organismes)
                    per_org_etp = etp / len(organismes)
                    for org in organismes:
                        if v_mode == 'by_org':
                            org_defaults = {
                                'budget_fonctionnement': round(per_org_budget, 2),
                                'budget_investissement': None,
                                'etp': round(per_org_etp, 2),
                            }
                        else:
                            org_defaults = {
                                'budget_fonctionnement': round(per_org_budget * 0.6, 2),
                                'budget_investissement': round(per_org_budget * 0.4, 2),
                                'etp': round(per_org_etp, 2),
                            }
                        OperationAnneeOrganisme.objects.update_or_create(
                            id_operation_annee=oa, id_organisme=org,
                            defaults=org_defaults,
                        )

    def reset(self) -> int:
        # On supprime les opérations qu'on a créées (par code) et leurs deps via cascade.
        codes = []
        for spec in _PLAN_SPECS:
            codes.extend(op['code'] for op in spec['operations'])
        count = Operation.objects.filter(code_operation__in=codes).delete()[0]
        # Les enjeux/OLT/NE/etc créés ici sont liés à des plans existants ; on
        # laisse EnjeuxSeeder.reset() les supprimer en cascade.
        return count

    def get_dry_run_summary(self) -> List[str]:
        return [
            '\nHiérarchie minimale pour 3 plans (Phase 4 - démo) :',
            f'  - {len(_PLAN_SPECS)} plans cibles : Brouage, Scandola, Remoray',
            f'  - {sum(len(s["enjeux"]) for s in _PLAN_SPECS)} enjeux',
            f'  - {sum(1 for s in _PLAN_SPECS for e in s["enjeux"] if e.get("olt"))} chaînes OLT/NE/Ind/Métrique',
            f'  - {sum(len(s["operations"]) for s in _PLAN_SPECS)} opérations',
        ]
