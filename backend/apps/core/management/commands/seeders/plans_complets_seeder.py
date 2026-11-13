"""
Les fonctionnalités récentes sur les plans « réalistes » du jeu d'essai.

Les plans « Ventilation — … » couvrent chaque réglage, un par plan, avec un
contenu identique. Les plans réalistes (Camargue, Aiguilles Rouges,
Vercors-Écrins, Lacs et zones humides, Scandola, Remoray, Brouage) restaient
en retrait des derniers chantiers : ce seeder les met au niveau, sans toucher à
leur programmation ni à leurs totaux.

- **Financeurs (#790)** : chaque action a ses financeurs, rattachés aux
  financeurs du plan, avec un montant prévu (réparti sur le budget prévu de
  l'action) et un réalisé annuel. Volontairement : un financeur à catégorie
  libre (« Mécénat »), une action dont les montants ne couvrent pas le budget
  (alerte ``ecart_budget``), un financeur non prévu au suivi, et le plan de
  Brouage sans montants (ils sont facultatifs).
- **Types d'action complémentaires (#792)** : sur une partie des actions qui ne
  sont pas CS (un type CS complémentaire exigerait un suivi).
- **Planification annuelle ajustée (#794)** de l'année en cours, sur les plans
  validés : action revue sans changement, revue avec ajustement (et financeurs
  de l'année), non prévue cette année, reportée en totalité (suite décalée,
  dernière année abandonnée), report partiel, et des actions encore à revoir.
  Une année reportée ou non prévue n'a pas de réalisé (hors niveau « Reportée »).
- **Appariements de types d'action (#770)** : le référentiel propre de RNF et
  du CEN, tel qu'un import précédent l'aurait enregistré.

Idempotent : chaque passage repart des données posées par les seeders
précédents (``realisations``, ``rh``) et réécrit les siennes.
"""
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

from apps.core.models import Nomenclature
from apps.plans.models import PlanGestion
from apps.plans.models_operations import (
    CorOperationTypeAction,
    FinanceOperation,
    Financeur,
    Operation,
    OperationAnnee,
    RealisationFinanceur,
    RealisationOperationAnnee,
    RealisationOperationAnneeOrganisme,
)

from .base import BaseSeeder

#: Plans réalistes du jeu d'essai (``PlansSeeder``), par nom.
PLANS_REALISTES = (
    'Plan de gestion 2020-2030 - Camargue',
    'Plan de gestion 2018-2028 - Aiguilles Rouges',
    'Plan de gestion inter-sites Vercors-Écrins 2021-2031',
    'Plan de gestion 2023-2033 - Lacs et zones humides continentales',
    'Plan de gestion - Scandola (étendu +2 ans)',
    'Plan de gestion 2017-2026 - Lac de Remoray (à étendre)',
    'Plan de gestion - Marais de Brouage (ENS étendu +2 ans)',
)
#: #790 — montants facultatifs : ce plan les laisse vides.
PLAN_SANS_MONTANTS = 'Plan de gestion - Marais de Brouage (ENS étendu +2 ans)'

#: Financeurs des actions qui n'en avaient pas, par préfixe de code.
FINANCEURS_PAR_DEFAUT = {
    'SCA-': [("Office de l'Environnement de la Corse", 'REGION'), ('OFB', 'ETAT')],
    'REM2-': [('Agence de l\'Eau Rhône-Méditerranée', 'ETAT'), ('Département du Doubs', 'DEPARTEMENT')],
    'BRG-': [('Département de la Charente-Maritime', 'DEPARTEMENT'), ('FEAMPA', 'EUROPE')],
}
#: Un financeur à catégorie libre (hors nomenclature), par action.
MECENAT = ('Fondation Nature & Découvertes', 'Mécénat')
ACTIONS_MECENAT = ('CAM-SE02', 'REM-TU06', 'VER-CC01')
#: Action dont les montants ne couvrent que 80 % du budget (alerte, non bloquante).
ACTION_ECART_BUDGET = 'AR-PR01'
#: Financeur non prévu, apparu au suivi de l'an dernier.
FINANCEUR_NON_PREVU = ('CAM-IP02', ('Commune des Saintes-Maries-de-la-Mer', 'COMMUNE'))

#: #792 — type complémentaire selon la famille du type principal.
COMPLEMENTAIRES = {
    'SP': ('CC1',),          # surveillance → sensibilisation
    'IP2': ('PA1',),         # entretien → animation
    'IP1': ('IP2', 'PA1'),   # restauration → entretien, animation
    'CC': ('PA1',),          # communication → animation
}

#: #794 — scénario de l'année en cours, par code d'action.
REVUE_IDENTIQUE = 'identique'
REVUE_AJUSTEE = 'ajustee'
NON_PREVUE = 'non_prevue'
REPORT_TOTAL = 'report_total'
REPORT_PARTIEL = 'report_partiel'
SCENARIOS_PLANIFICATION = {
    'Plan de gestion 2020-2030 - Camargue': {
        'CAM-SE01': REVUE_IDENTIQUE,
        'CAM-SE02': REVUE_AJUSTEE,
        'CAM-IP01': REPORT_TOTAL,   # suite décalée, 2030 → 2031 abandonnée
        'CAM-GE01': NON_PREVUE,
        # CAM-IP02, CAM-TRANS01 : à revoir
    },
    'Plan de gestion 2018-2028 - Aiguilles Rouges': {
        'AR-CS01': REVUE_AJUSTEE,
        'AR-CC01': REPORT_PARTIEL,
        # AR-PR01 : à revoir
    },
    'Plan de gestion inter-sites Vercors-Écrins 2021-2031': {
        'VER-CS01': REPORT_TOTAL,
        'VER-PR01': REVUE_IDENTIQUE,
        # VER-CC01, VER-CS02 : à revoir
    },
}
COMMENTAIRES = {
    REVUE_IDENTIQUE: "Revue en comité de gestion : programmation maintenue.",
    REVUE_AJUSTEE: "Moyens revus à la baisse (−15 %) ; interventions regroupées à l'automne.",
    NON_PREVUE: "Négociation suspendue cette année dans l'attente du nouveau schéma départemental.",
    REPORT_TOTAL: "Reportée : autorisations administratives non obtenues à temps.",
    REPORT_PARTIEL: "Une partie des animations glisse sur l'an prochain (intempéries).",
}

#: #770 — référentiel propre des structures, apparié à Gestref.
APPARIEMENTS = {
    0: [  # RNF
        ('Suivi scientifique flore', 'CS3'),
        ('Inventaire faune', 'CS8'),
        ('Surveillance / police', 'SP1'),
        ('Animation grand public', 'PA1'),
        ('Travaux de restauration', 'IP1'),
    ],
    1: [  # CEN AURA
        ('GH - entretien par fauche', 'IP2_1'),
        ('GH - pâturage', 'IP2_2'),
        ('SE - suivi végétation', 'CS3'),
        ('FA - accueil du public', 'PA1'),
        ('AD - communication', 'CC1'),
    ],
}

_RATIO_REALISE = {
    'TERMINE': Decimal('0.95'), 'PARTIEL': Decimal('0.55'), 'EN_COURS': Decimal('0.40'),
    'ABANDONNE': Decimal('0.20'), 'NON_REALISE': Decimal('0'), 'NON_DEMARRE': Decimal('0'),
    'REPORTE': Decimal('0'),
}


def _arrondi(valeur) -> Optional[Decimal]:
    return None if valeur is None else Decimal(valeur).quantize(Decimal('0.01'))


class PlansCompletsSeeder(BaseSeeder):
    """Financeurs, types complémentaires, planification ajustée et
    appariements sur les plans réalistes du jeu d'essai."""

    name = 'plans_complets'
    dependencies = ['realisations', 'rh', 'minimal_plans']

    # ------------------------------------------------------------- utilitaires

    @staticmethod
    def _nomenclature(type_mnemo: str, mnemo: str) -> Optional[Nomenclature]:
        return Nomenclature.objects.filter(
            id_type__mnemonique=type_mnemo, mnemonique=mnemo, actif=True).first()

    @staticmethod
    def _plans() -> List[PlanGestion]:
        return list(PlanGestion.objects.filter(nom__in=PLANS_REALISTES).order_by('id_pg'))

    @staticmethod
    def _actions(plan) -> List[Operation]:
        from apps.plans.access import plan_operation_ids
        return list(Operation.objects.filter(pk__in=plan_operation_ids(plan))
                    .select_related('id_type_action').order_by('code_operation'))

    # -------------------------------------------------------------------- seed

    def seed(self) -> Dict:
        self.log_header('Fonctionnalités récentes sur les plans réalistes')
        users = self.context.require('users')
        admin = users[0] if users else None
        annee = date.today().year

        plans = self._plans()
        if not plans:
            self.log('  Aucun plan réaliste trouvé — seeder ignoré.', 'WARNING')
            return {}

        nb_fin = nb_compl = nb_ajust = 0
        for plan in plans:
            actions = self._actions(plan)
            nb_fin += self._financeurs_prevus(plan, actions)
            nb_compl += self._types_complementaires(actions)
            nb_ajust += self._planification(plan, actions, annee, admin)
        # Le réalisé par financeur après la planification : une année reportée
        # ou non prévue y a perdu son réalisé.
        nb_real = sum(self._financeurs_realises(plan, self._actions(plan)) for plan in plans)
        nb_app = self._appariements(admin)

        self.log_summary(nb_fin, 'montants prévus par financeur (#790)')
        self.log_summary(nb_real, 'montants réalisés par financeur (#790)')
        self.log_summary(nb_compl, "types d'action complémentaires (#792)")
        self.log_summary(nb_ajust, 'années ajustées (#794)')
        self.log_summary(nb_app, "appariements de types d'action (#770)")
        self.context.set('plans_complets', plans)
        return {'plans_complets': plans}

    # ------------------------------------------------------------ financeurs

    def _financeurs_prevus(self, plan, actions) -> int:
        """#790 — financeurs rattachés au plan, montant prévu global."""
        from apps.plans.financeurs import budget_prevu

        categories = {
            code: self._nomenclature('CATEGORIE_FINANCE', code)
            for code in ('ETAT', 'REGION', 'DEPARTEMENT', 'EUROPE', 'COMMUNE')}
        n = 0
        for op in actions:
            code = op.code_operation or ''
            if not op.finances.exists():
                prefixe = next((p for p in FINANCEURS_PAR_DEFAUT if code.startswith(p)), None)
                for nom, cat in FINANCEURS_PAR_DEFAUT.get(prefixe, []):
                    financeur = Financeur.pour(plan, nom, categories.get(cat))
                    FinanceOperation.objects.update_or_create(
                        id_operation=op, libelle=nom,
                        defaults={'id_categorie': financeur.id_categorie, 'id_financeur': financeur})
            # Les lignes héritées sans financeur du plan y sont rattachées.
            for fin in op.finances.filter(id_financeur__isnull=True):
                fin.id_financeur = Financeur.pour(plan, fin.libelle, fin.id_categorie)
                fin.save(update_fields=['id_financeur'])
            if code in ACTIONS_MECENAT:
                nom, libre = MECENAT
                financeur = Financeur.pour(plan, nom, None, categorie_libre=libre)
                FinanceOperation.objects.update_or_create(
                    id_operation=op, libelle=nom,
                    defaults={'id_categorie': None, 'id_financeur': financeur})

            lignes = list(op.finances.order_by('id_finance_operation'))
            if plan.nom == PLAN_SANS_MONTANTS or not lignes:
                FinanceOperation.objects.filter(id_operation=op).update(montant=None)
                continue
            budget = budget_prevu(op).quantize(Decimal('1'))
            if code == ACTION_ECART_BUDGET:
                budget = (budget * Decimal('0.8')).quantize(Decimal('1'))
            # Le premier financeur porte la plus grosse part : 60 / 40,
            # 50 / 30 / 20 ; le dernier prend le reste (total exact).
            parts = {1: ['1'], 2: ['0.6', '0.4'], 3: ['0.5', '0.3', '0.2']}.get(
                len(lignes), [str(Decimal(1) / len(lignes))] * len(lignes))
            reste = budget
            for i, fin in enumerate(lignes):
                montant = reste if i == len(lignes) - 1 else (budget * Decimal(parts[i])).quantize(Decimal('1'))
                reste -= montant
                fin.montant = montant
                fin.save(update_fields=['montant'])
                n += 1
        return n

    def _financeurs_realises(self, plan, actions) -> int:
        """#790 — réalisé annuel par financeur, au prorata du niveau de l'année."""
        n = 0
        for op in actions:
            reals = list(RealisationOperationAnnee.objects.filter(
                id_operation_annee__id_operation=op).select_related('id_niveau_realisation'))
            RealisationFinanceur.objects.filter(id_realisation_operation_annee__in=reals).delete()
            lignes = [f for f in op.finances.select_related('id_financeur') if f.montant is not None]
            if not lignes:
                continue
            nb_annees = OperationAnnee.objects.filter(id_operation=op).count() or 1
            for real in reals:
                ratio = _RATIO_REALISE.get(getattr(real.id_niveau_realisation, 'mnemonique', None),
                                           Decimal('0'))
                if not ratio:
                    continue
                for fin in lignes:
                    RealisationFinanceur.objects.create(
                        id_realisation_operation_annee=real, id_financeur=fin.id_financeur,
                        montant=(fin.montant / nb_annees * ratio).quantize(Decimal('1')))
                    n += 1
            code, (nom, cat) = FINANCEUR_NON_PREVU
            if op.code_operation == code:
                # Un financeur qui n'était pas prévu, apparu au suivi de l'an dernier.
                real = next((r for r in reals
                             if r.id_operation_annee.annee == date.today().year - 1), None)
                if real is not None:
                    financeur = Financeur.pour(plan, nom, self._nomenclature('CATEGORIE_FINANCE', cat))
                    RealisationFinanceur.objects.create(
                        id_realisation_operation_annee=real, id_financeur=financeur,
                        montant=Decimal('1500'))
                    n += 1
        return n

    # ------------------------------------------------- types complémentaires

    def _types_complementaires(self, actions) -> int:
        """#792 — une action sur deux (hors CS) reçoit un ou deux types complémentaires."""
        n = 0
        for i, op in enumerate(actions):
            CorOperationTypeAction.objects.filter(id_operation=op).delete()
            principal = op.id_type_action.mnemonique if op.id_type_action else ''
            if not principal or principal.startswith('CS') or i % 2:
                continue
            famille = next((f for f in sorted(COMPLEMENTAIRES, key=len, reverse=True)
                            if principal.startswith(f)), None)
            if famille is None:
                continue
            ordre = 0
            for mnemo in COMPLEMENTAIRES[famille]:
                nomenclature = self._nomenclature('TYPE_ACTION', mnemo)
                if nomenclature is None or nomenclature.pk == op.id_type_action_id:
                    continue
                CorOperationTypeAction.objects.create(
                    id_operation=op, id_type_action=nomenclature, ordre=ordre)
                ordre += 1
                n += 1
        return n

    # ------------------------------------------------ planification ajustée

    @staticmethod
    def _effacer_realise(op, annee, niveau=None, commentaire='') -> None:
        """Une année reportée (ou non prévue) n'a pas de réalisé : seul le
        niveau « Reportée » reste, pour une action reportée."""
        oa = OperationAnnee.objects.filter(id_operation=op, annee=annee).first()
        if oa is None:
            return
        RealisationOperationAnneeOrganisme.objects.filter(
            id_operation_annee_organisme__id_operation_annee=oa).delete()
        RealisationOperationAnnee.objects.filter(id_operation_annee=oa).delete()
        if niveau is not None:
            RealisationOperationAnnee.objects.create(
                id_operation_annee=oa, id_niveau_realisation=niveau,
                periodicite_realisee=False, commentaires=commentaire)

    def _planification(self, plan, actions, annee, admin) -> int:
        """#794 — scénario de l'année en cours ; le plan de gestion n'est pas touché."""
        from apps.plans.models_planification import (
            CHAMPS_COUTS_ANNEE, CHAMPS_COUTS_ORGANISME, AjustementAnnuel,
        )
        from apps.plans.planification_annuelle import (
            NON_PREVUE as STATUT_NON_PREVUE, Planification, ReportImpossible, contenu_vide, ecrire,
        )

        AjustementAnnuel.objects.filter(id_operation__in=actions).delete()
        scenario = SCENARIOS_PLANIFICATION.get(plan.nom)
        if not scenario or annee not in plan.annees_plan():
            return 0
        reporte = self._nomenclature('NIVEAU_REALISATION', 'REPORTE')
        par_code = {op.code_operation: op for op in actions}

        # Les années reportées / non prévues perdent leur réalisé avant de lire
        # la planification (un réalisé saisi fige l'année).
        for code, cas in scenario.items():
            op = par_code.get(code)
            if op is None:
                continue
            if cas == REPORT_TOTAL:
                self._effacer_realise(op, annee, reporte, COMMENTAIRES[cas])
            elif cas == NON_PREVUE:
                self._effacer_realise(op, annee)

        def _baisser(valeur):
            return None if valeur is None else _arrondi(Decimal(valeur) * Decimal('0.85'))

        n = 0
        for code, cas in scenario.items():
            op = par_code.get(code)
            if op is None:
                continue
            planif = Planification(plan, actions)
            try:
                if cas == REVUE_IDENTIQUE:
                    contenu = planif.pg(op.pk, annee)
                    contenu['commentaire'] = COMMENTAIRES[cas]
                    ecrire(op, annee, contenu, admin)
                elif cas == REVUE_AJUSTEE:
                    contenu = planif.effectif(op.pk, annee)
                    for champ in CHAMPS_COUTS_ANNEE:
                        contenu[champ] = _baisser(contenu[champ])
                    for org in contenu['organismes']:
                        for champ in CHAMPS_COUTS_ORGANISME:
                            org[champ] = _baisser(org[champ])
                    for ligne in contenu['rh_lignes']:
                        ligne['jours'] = _baisser(ligne['jours'])
                    contenu['periodicite_mensuelle'] = {'9': True, '10': True, '11': True}
                    contenu['commentaire'] = COMMENTAIRES[cas]
                    # Financeurs de l'année (le plan n'a qu'un montant global).
                    nb_annees = OperationAnnee.objects.filter(id_operation=op).count() or 1
                    contenu['financeurs'] = [
                        {'id_financeur': f.id_financeur_id,
                         'montant': _arrondi(f.montant / nb_annees * Decimal('0.85'))}
                        for f in op.finances.all() if f.montant is not None and f.id_financeur_id]
                    ecrire(op, annee, contenu, admin)
                elif cas == NON_PREVUE:
                    contenu = contenu_vide(STATUT_NON_PREVUE)
                    contenu['commentaire'] = COMMENTAIRES[cas]
                    ecrire(op, annee, contenu, admin)
                elif cas in (REPORT_TOTAL, REPORT_PARTIEL):
                    planif.reporter(op.pk, annee, annee + 1, admin, partiel=cas == REPORT_PARTIEL)
                    aj = AjustementAnnuel.objects.get(id_operation=op, annee=annee)
                    aj.commentaire = COMMENTAIRES[cas]
                    aj.save(update_fields=['commentaire'])
            except ReportImpossible as exc:
                self.log(f'  {code} : report impossible ({exc}).', 'WARNING')
                continue
            n += AjustementAnnuel.objects.filter(id_operation=op).count()
            self.log_item('ajusté', f'{code} {annee} ({cas})')
        return n

    # ---------------------------------------------------------- appariements

    def _appariements(self, admin) -> int:
        """#770 — correspondances gardées par organisme, proposées à l'import."""
        from apps.plans.models_referentiel import AppariementTypeAction
        from apps.plans.referentiel_actions import _cle

        organismes = self.context.get('organismes') or []
        n = 0
        for index, lignes in APPARIEMENTS.items():
            if index >= len(organismes):
                continue
            organisme = organismes[index]
            for valeur, mnemo in lignes:
                type_action = self._nomenclature('TYPE_ACTION', mnemo)
                if type_action is None:
                    continue
                AppariementTypeAction.objects.update_or_create(
                    organisme=organisme, cle=_cle(valeur),
                    defaults={'valeur': valeur, 'id_type_action': type_action,
                              'id_utilisateur_maj': admin})
                n += 1
        return n

    # ------------------------------------------------------------------- reset

    def reset(self) -> int:
        from apps.plans.models_planification import AjustementAnnuel
        from apps.plans.models_referentiel import AppariementTypeAction

        actions = [op for plan in self._plans() for op in self._actions(plan)]
        count = AjustementAnnuel.objects.filter(id_operation__in=actions).delete()[0]
        count += CorOperationTypeAction.objects.filter(id_operation__in=actions).delete()[0]
        count += RealisationFinanceur.objects.filter(
            id_realisation_operation_annee__id_operation_annee__id_operation__in=actions).delete()[0]
        valeurs = [_v for lignes in APPARIEMENTS.values() for _v, _ in lignes]
        count += AppariementTypeAction.objects.filter(valeur__in=valeurs).delete()[0]
        return count

    def get_dry_run_summary(self) -> List[str]:
        return [
            '\nPlans réalistes — fonctionnalités récentes :',
            '  - #790 : montants prévus par financeur (Brouage sans montants), réalisé annuel,',
            '           mécénat (catégorie libre), écart au budget, financeur non prévu',
            "  - #792 : types d'action complémentaires (une action sur deux, hors CS)",
            "  - #794 : année en cours ajustée sur Camargue, Aiguilles Rouges, Vercors-Écrins",
            "  - #770 : appariements du référentiel de RNF et du CEN AURA vers Gestref",
        ]
