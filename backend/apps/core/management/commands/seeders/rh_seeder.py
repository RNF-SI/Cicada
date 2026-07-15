"""
Seeder RH (#560) — personnes, fonctions et lignes de temps de travail.

Enrichit le plan de gestion « Lacs et zones humides continentales » (créé par
MinimalPlansSeeder) avec des personnes, leurs fonctions, et des lignes de temps
de travail prévisionnel (et réalisé quand un suivi existe) sur ses actions. Les
lignes RH génériques issues de la migration #560 sont remplacées par des lignes
réalistes pointant vers des personnes/fonctions, avec ventilation financé /
non financé.
"""
from decimal import Decimal

from django.db.models import Q

from apps.plans.models import PlanGestion
from apps.plans.models_operations import (
    Operation, OperationAnnee, OperationAnneeRH,
    RealisationOperationAnneeRH,
    Fonction, PersonnePlan, PersonneFonction,
)

from .base import BaseSeeder


_PLAN_SLUG = 'plan-de-gestion-2023-2033-lacs-et-zones-humides-continentales'

# Personnes du PG : (nom, [(fonction, quotité %)]).
_PERSONNES = [
    ('Camille Rivière', [('Conservateur', 100)]),
    ('Louis Marchand', [('Garde-technicien', 100)]),
    ('Sarah Benali', [('Animateur nature', 60), ('Chargé de communication', 40)]),
    ('Théo Lefèvre', [('Service civique', 100)]),
    ('Bénévoles LPO', [('Bénévole', None)]),
]

# Fonctions non financées par défaut (cohérent avec le socle #560).
_NON_FINANCEES = {'bénévole', 'écovolontaire', 'partenaire'}


class RhSeeder(BaseSeeder):
    name = 'rh'
    dependencies = ['minimal_plans', 'realisations']

    def seed(self) -> dict:
        self.log_header('Ressources humaines (#560)')
        plan = PlanGestion.objects.filter(slug=_PLAN_SLUG).first()
        if not plan:
            self.log('Plan zones humides introuvable, RH ignoré.', 'WARNING')
            return {'personnes': 0, 'lignes_prev': 0, 'lignes_reel': 0}

        # 1. Personnes + fonctions
        personnes = {}
        for nom, fonctions in _PERSONNES:
            personne, _ = PersonnePlan.objects.get_or_create(id_pg=plan, nom=nom)
            PersonneFonction.objects.filter(id_personne_plan=personne).delete()
            for libelle, pct in fonctions:
                fonction = self._get_fonction(libelle)
                PersonneFonction.objects.create(
                    id_personne_plan=personne,
                    id_fonction=fonction,
                    pourcentage=Decimal(str(pct)) if pct is not None else None,
                )
            personnes[nom] = personne

        fonction_benevole = self._get_fonction('Bénévole')

        # 2. Lignes RH sur les actions du plan
        operations = self._plan_operations(plan)
        lignes_prev = 0
        lignes_reel = 0
        for idx, op in enumerate(operations):
            variant = self._variant_for(idx, personnes, fonction_benevole)
            for oa in OperationAnnee.objects.filter(id_operation=op):
                # Remplace les lignes génériques migrées par des lignes réalistes.
                OperationAnneeRH.objects.filter(id_operation_annee=oa).delete()
                prevues = []
                for line in variant:
                    prevues.append(
                        OperationAnneeRH.objects.create(id_operation_annee=oa, **line)
                    )
                    lignes_prev += 1

                # Réel : quand un suivi de l'année existe, saisir ~85 % du prévu.
                real = getattr(oa, 'realisation', None)
                if real is not None:
                    RealisationOperationAnneeRH.objects.filter(
                        id_realisation_operation_annee=real
                    ).delete()
                    for prevue, line in zip(prevues, variant):
                        reel = dict(line)
                        if reel['jours'] is not None:
                            reel['jours'] = round(reel['jours'] * Decimal('0.85'), 2)
                        RealisationOperationAnneeRH.objects.create(
                            id_realisation_operation_annee=real,
                            # Le réel réalise la ligne prévue correspondante :
                            # sans ce lien il remonterait en « non prévu ».
                            id_operation_annee_rh=prevue,
                            **reel,
                        )
                        lignes_reel += 1

        self.log_summary(len(personnes), 'personnes créées')
        self.log_summary(lignes_prev, 'lignes RH prévisionnelles créées')
        self.log_summary(lignes_reel, 'lignes RH réalisées créées')
        return {
            'personnes': len(personnes),
            'lignes_prev': lignes_prev,
            'lignes_reel': lignes_reel,
        }

    def _variant_for(self, idx, personnes, fonction_benevole):
        """Composition RH déterministe variée selon l'action."""
        conservateur = personnes['Camille Rivière']
        garde = personnes['Louis Marchand']
        animateur = personnes['Sarah Benali']
        service_civique = personnes['Théo Lefèvre']
        benevoles = personnes['Bénévoles LPO']
        variants = [
            [
                dict(id_personne_plan=conservateur, id_fonction=None, jours=Decimal('8'), finance=True),
                dict(id_personne_plan=garde, id_fonction=None, jours=Decimal('12'), finance=True),
                dict(id_personne_plan=benevoles, id_fonction=fonction_benevole, jours=Decimal('5'), finance=False),
            ],
            [
                dict(id_personne_plan=animateur, id_fonction=None, jours=Decimal('6'), finance=True),
                dict(id_personne_plan=service_civique, id_fonction=None, jours=Decimal('10'), finance=False),
            ],
            [
                dict(id_personne_plan=garde, id_fonction=None, jours=Decimal('15'), finance=True),
            ],
            [
                dict(id_personne_plan=conservateur, id_fonction=None, jours=Decimal('4'), finance=True),
                dict(id_personne_plan=benevoles, id_fonction=fonction_benevole, jours=Decimal('8'), finance=False),
            ],
        ]
        return variants[idx % len(variants)]

    def _get_fonction(self, libelle):
        fonction = Fonction.objects.filter(libelle__iexact=libelle).first()
        if fonction:
            return fonction
        return Fonction.objects.create(
            libelle=libelle,
            finance_par_defaut=libelle.lower() not in _NON_FINANCEES,
            is_socle=False,
        )

    def _plan_operations(self, plan):
        return list(
            Operation.objects.filter(
                Q(metriques__id_indicateur__id_ne__id_olt__id_enjeu__id_pg=plan)
                | Q(id_suivi__id_pg=plan)
            ).distinct()
        )

    def reset(self) -> int:
        plan = PlanGestion.objects.filter(slug=_PLAN_SLUG).first()
        if not plan:
            return 0
        count = 0
        for op in self._plan_operations(plan):
            for oa in OperationAnnee.objects.filter(id_operation=op):
                count += OperationAnneeRH.objects.filter(id_operation_annee=oa).delete()[0]
                real = getattr(oa, 'realisation', None)
                if real is not None:
                    count += RealisationOperationAnneeRH.objects.filter(
                        id_realisation_operation_annee=real
                    ).delete()[0]
        count += PersonnePlan.objects.filter(id_pg=plan).delete()[0]
        return count

    def get_dry_run_summary(self) -> list:
        return [
            f'{len(_PERSONNES)} personnes sur le plan « Lacs et zones humides continentales »',
            'lignes RH prévisionnelles (et réalisées) sur ses actions, financé / non financé',
        ]
