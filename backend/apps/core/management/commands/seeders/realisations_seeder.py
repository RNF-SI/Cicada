"""
Seeder pour le suivi de réalisation des opérations (Phase 1 - Suivis).

Crée des entrées RealisationOperationAnnee et RealisationOperationAnneeOrganisme
pour les opérations seedées par EnjeuxSeeder, sur les années passées et l'année
courante (les futures restent vides, comme dans la réalité d'un PG en cours).
"""
from datetime import date
from decimal import Decimal
from typing import List

from apps.core.models import Nomenclature
from apps.plans.models_operations import (
    OperationAnnee,
    OperationAnneeOrganisme,
    RealisationOperationAnnee,
    RealisationOperationAnneeOrganisme,
)

from .base import BaseSeeder


# Ratio par niveau de réalisation, appliqué au prévisionnel pour fabriquer
# du réalisé déterministe et cohérent avec le label affiché.
_RATIO_BY_NIVEAU = {
    'TERMINE':     Decimal('0.95'),
    'PARTIEL':     Decimal('0.55'),
    'EN_COURS':    Decimal('0.40'),
    'REPORTE':     Decimal('0.10'),
    'NON_DEMARRE': Decimal('0.00'),
    'ABANDONNE':   Decimal('0.20'),
}

# Distribution déterministe des niveaux pour varier les statuts dans le seed,
# afin d'alimenter correctement les graphiques du Bilan (#Phase 4) et la légende
# du Suivi des actions. Le bucket est calculé par (op_id + annee) % 10.
_DISTRIBUTION_PAST = {
    # 60% terminé, 20% partiel, 10% reporté, 10% abandonné
    0: 'TERMINE', 1: 'TERMINE', 2: 'TERMINE',
    3: 'TERMINE', 4: 'TERMINE', 5: 'TERMINE',
    6: 'PARTIEL', 7: 'PARTIEL',
    8: 'REPORTE',
    9: 'ABANDONNE',
}
_DISTRIBUTION_CURRENT = {
    # 50% en cours, 20% partiel, 20% non démarré, 10% terminé (avance)
    0: 'EN_COURS', 1: 'EN_COURS', 2: 'EN_COURS',
    3: 'EN_COURS', 4: 'EN_COURS',
    5: 'PARTIEL', 6: 'PARTIEL',
    7: 'NON_DEMARRE', 8: 'NON_DEMARRE',
    9: 'TERMINE',
}


class RealisationsSeeder(BaseSeeder):
    """
    Crée les suivis de réalisation pour les opérations seedées.

    Stratégie :
      - Pour chaque OperationAnnee où annee < année courante :
        * niveau choisi dans _DISTRIBUTION_PAST (TERMINE 60% / PARTIEL 20% /
          REPORTE 10% / ABANDONNE 10%) selon (op_id + annee) % 10
        * périodicité réalisée si niveau ∈ {TERMINE, PARTIEL}, budget/ETP au ratio
          correspondant
      - Pour chaque OperationAnnee où annee = année courante :
        * niveau choisi dans _DISTRIBUTION_CURRENT (EN_COURS 50% / PARTIEL 20% /
          NON_DEMARRE 20% / TERMINE 10%) selon le même hash
      - Pour annee > année courante : aucune réalisation
      - Ventilation par organisme respectée (RealisationOperationAnneeOrganisme
        créé en miroir de chaque OperationAnneeOrganisme).
    """

    name = 'realisations'
    dependencies = ['enjeux']

    def _get_niveau(self, mnemonique: str) -> Nomenclature:
        return Nomenclature.objects.filter(
            id_type__mnemonique='NIVEAU_REALISATION',
            mnemonique=mnemonique,
        ).first()

    def _mul(self, value, ratio: Decimal) -> Decimal | None:
        if value is None:
            return None
        return (Decimal(value) * ratio).quantize(Decimal('0.01'))

    def seed(self) -> dict:
        self.log_header('Création des suivis de réalisation')

        users = self.context.require('users')
        admin = users[0] if users else None

        # Précharger toutes les nomenclatures NIVEAU_REALISATION pour pouvoir
        # varier les niveaux. Si l'une manque, on saute le seeder.
        niveaux_cache = {
            m: self._get_niveau(m)
            for m in ('TERMINE', 'PARTIEL', 'EN_COURS',
                      'REPORTE', 'NON_DEMARRE', 'ABANDONNE')
        }
        if not all(niveaux_cache.values()):
            self.log(
                '  Nomenclatures NIVEAU_REALISATION manquantes — seeder ignoré.',
                'WARNING',
            )
            return {'realisations_annee': [], 'realisations_organisme': []}

        current_year = date.today().year
        realisations_annee = []
        realisations_organisme = []
        # Suivi des compteurs par mnémonique (utile pour le log final).
        per_niveau = {m: 0 for m in niveaux_cache}

        # On limite aux opérations qui ont au moins une année passée ou en cours.
        operation_annees = OperationAnnee.objects.filter(
            annee__lte=current_year,
        ).select_related('id_operation').prefetch_related('organismes')

        for oa in operation_annees:
            is_complete = oa.annee < current_year
            distribution = _DISTRIBUTION_PAST if is_complete else _DISTRIBUTION_CURRENT
            bucket = (oa.id_operation_id + oa.annee) % 10
            niveau_mnemo = distribution[bucket]
            niveau = niveaux_cache[niveau_mnemo]
            ratio = _RATIO_BY_NIVEAU[niveau_mnemo]
            per_niveau[niveau_mnemo] += 1

            mode = oa.id_operation.ventilation_mode

            # Périodicité réalisée : vrai uniquement si l'action a effectivement
            # avancé (TERMINE, PARTIEL, EN_COURS) — pas pour NON_DEMARRE/ABANDONNE/REPORTE.
            has_progressed = niveau_mnemo in ('TERMINE', 'PARTIEL', 'EN_COURS')

            defaults = {
                'id_niveau_realisation': niveau,
                'periodicite_realisee': bool(oa.periodicite) and has_progressed,
                'commentaires': (
                    f"Réalisation {oa.annee} (seed) - "
                    f"niveau {niveau.label.lower()}."
                ),
                'id_utilisateur_maj': admin,
            }

            # Budget / ETP : ne sont stockés sur la table annuelle que si le mode
            # de ventilation ne porte pas sur les organismes.
            if mode == 'none':
                defaults['budget_realise'] = self._mul(oa.budget, ratio)
                defaults['etp_realise'] = self._mul(oa.etp, ratio)
            elif mode == 'by_type':
                defaults['budget_fonctionnement_realise'] = self._mul(
                    oa.budget_fonctionnement, ratio
                )
                defaults['budget_investissement_realise'] = self._mul(
                    oa.budget_investissement, ratio
                )
                defaults['etp_realise'] = self._mul(oa.etp, ratio)
            # else: by_org / by_org_type → budget/etp portés par les organismes,
            # on laisse les champs annuels nulls.

            realisation, created = RealisationOperationAnnee.objects.update_or_create(
                id_operation_annee=oa,
                defaults=defaults,
            )
            realisations_annee.append(realisation)
            self.log_item(
                'créé' if created else 'mis à jour',
                f'Réal. {oa.id_operation.code_operation or oa.id_operation_id} '
                f'{oa.annee} ({niveau.label})'
            )

            # Ventilation par organisme : 1 réalisation par OperationAnneeOrganisme
            if mode in ('by_org', 'by_org_type'):
                for oao in oa.organismes.all():
                    org_defaults = {
                        'etp_realise': self._mul(oao.etp, ratio),
                    }
                    if mode == 'by_org':
                        # Le budget total est stocké dans budget_fonctionnement
                        # côté planifié (cf. enjeux_seeder).
                        org_defaults['budget_fonctionnement_realise'] = self._mul(
                            oao.budget_fonctionnement, ratio
                        )
                        org_defaults['budget_investissement_realise'] = None
                    else:
                        org_defaults['budget_fonctionnement_realise'] = self._mul(
                            oao.budget_fonctionnement, ratio
                        )
                        org_defaults['budget_investissement_realise'] = self._mul(
                            oao.budget_investissement, ratio
                        )
                    real_oao, _ = RealisationOperationAnneeOrganisme.objects.update_or_create(
                        id_operation_annee_organisme=oao,
                        defaults=org_defaults,
                    )
                    realisations_organisme.append(real_oao)

        self.log_summary(len(realisations_annee), 'réalisations annuelles créées')
        self.log_summary(len(realisations_organisme), 'réalisations par organisme créées')
        # Détail par niveau (utile pour confirmer la variété sur la page Bilan).
        for mnemo, count in per_niveau.items():
            if count:
                self.log_item('—', f'{count} × {niveaux_cache[mnemo].label}')

        self.context.set('realisations_annee', realisations_annee)
        self.context.set('realisations_organisme', realisations_organisme)

        return {
            'realisations_annee': realisations_annee,
            'realisations_organisme': realisations_organisme,
        }

    def reset(self) -> int:
        count = 0
        count += RealisationOperationAnneeOrganisme.objects.all().delete()[0]
        count += RealisationOperationAnnee.objects.all().delete()[0]
        return count

    def get_dry_run_summary(self) -> List[str]:
        return [
            '\nSuivis de réalisation (Phase 1):',
            "  - 1 RealisationOperationAnnee par OperationAnnee dont annee <= année courante",
            "  - 1 RealisationOperationAnneeOrganisme par OperationAnneeOrganisme idem",
            "  - Années passées : niveau Terminé, ~95% du planifié",
            f"  - Année courante ({date.today().year}) : niveau En cours, ~50% du planifié",
        ]
