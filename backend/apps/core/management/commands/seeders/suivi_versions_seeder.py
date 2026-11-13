"""Seeder « Suivi entre versions » (#803) — un seul suivi par rang.

Deux chaînes de versions **au même rang**, construites à partir du plan
*Ventilation validée — par organisme, type de budget et type de poste* (son
contenu, son suivi, ses ajustements annuels), pour recetter le passage du
suivi d'une version à l'autre :

- **« Suivi entre versions — à valider »** : v1 validée, suivi saisi ; v2 en
  brouillon. Le testeur valide la v2 et voit le suivi y passer.
- **« Suivi entre versions — déjà basculé »** : v1 archivée, v2 validée
  (« modifié ») qui porte déjà le suivi ; la v1 renvoie vers elle.

Dans les deux v2, les actions ont évolué depuis la v1 :

- **PA1 supprimée** → son suivi (N-1, saisi sur la v1) y reste, consultable ;
- **IP1 renommée** (« … — libellé revu dans la v2 ») → son suivi la suit ;
- **CS1 sans l'année N-2** dans sa programmation → l'année saisie la suit, sans
  prévu ;
- **une action ajoutée** (copie d'IP1, « Action ajoutée dans la v2 ») → part
  sans suivi.

Chaîne « déjà basculé » seulement : l'année N-1 de CS1 avait été ressaisie dans
la v2 avant sa validation (« Ressaisi dans la v2 ») → c'est elle qui reste, la
saisie de la v1 pour cette année demeure sur la v1.

Codes d'action ``CAM-VENT-SV…`` : le préfixe ``CAM-VENT-`` les tient à l'écart
de ``RealisationsSeeder``, qui poserait sinon un second suivi.
"""
from datetime import date
from typing import List

from django.db.models import Q

from apps.plans.element_copy import ElementCopyService
from apps.plans.models import PlanGestion
from apps.plans.models_indicateurs import (
    Indicateur, IndicateurMesure, IndicateurRealisationGlobale, Mesure, Metrique,
)
from apps.plans.models_operations import (
    Financeur, Operation, OperationAnnee, OperationAnneeOrganisme, OperationAnneeRH,
    OperationRealisationGlobale, Poste, Protocole, RealisationFinanceur,
    RealisationOperationAnnee, RealisationOperationAnneeOrganisme, RealisationOperationAnneeRH,
    SuiviInventaire,
)
from apps.plans.models_planification import (
    AjustementAnnuel, AjustementAnnuelFinanceur, AjustementAnnuelOrganisme, AjustementAnnuelRH,
)
from apps.plans.access import plan_operation_ids
from apps.plans.services import PlanDuplicationService
from apps.plans.suivi_version import correspondances, modeles, objets_du_plan, transferer_suivi

from .base import BaseSeeder

PLAN_SOURCE = 'Ventilation validée — par organisme, type de budget et type de poste'
PREFIXE = 'Suivi entre versions — '
CODE_SOURCE = 'CAM-VENT-VAL-'
#: (libellé de la chaîne, code, déjà basculée ?)
CHAINES = (
    ('à valider', 'CAM-VENT-SVA-', False),
    ('déjà basculé', 'CAM-VENT-SVB-', True),
)
SUFFIXE_RENOMMEE = ' — libellé revu dans la v2'
LIBELLE_AJOUTEE = 'Action ajoutée dans la v2'
RESSAISI = 'Ressaisi dans la v2 avant sa validation'


class SuiviVersionsSeeder(BaseSeeder):
    """Chaînes de versions au même rang pour recetter #803."""

    name = 'suivi_versions'
    dependencies = ['ventilation_plans']

    # ------------------------------------------------------------- utilitaires

    @staticmethod
    def _actions(plan):
        return Operation.objects.filter(pk__in=plan_operation_ids(plan))

    def _action(self, plan, suffixe):
        return self._actions(plan).filter(code_operation__endswith=f'-{suffixe}').first()

    def _version(self, source, admin, nom, version, statut, parent):
        plan = PlanDuplicationService.duplicate_plan(source, admin)
        plan.nom = nom
        plan.slug = ''
        plan.version = version
        plan.statut = statut
        plan.plan_parent = parent
        plan.rang = source.rang
        plan.save()
        return plan

    def _cloner_suivi(self, source, plan, admin):
        """Recopie le suivi de ``source`` sur ``plan`` (sa copie), objet par objet."""
        dup = PlanDuplicationService._dup
        corr = correspondances(source.pk, plan.pk, modeles())
        postes = corr['poste']

        def financeur(f):
            return Financeur.pour(plan, f.nom, f.id_categorie_id, f.categorie_libre)

        for src_op, op in corr['operation'].items():
            for rea in RealisationOperationAnnee.objects.filter(
                    id_operation_annee__id_operation_id=src_op).select_related('id_operation_annee'):
                oa, _ = OperationAnnee.objects.get_or_create(
                    id_operation_id=op, annee=rea.id_operation_annee.annee,
                    defaults={'periodicite': False})
                nouvelle = dup(rea, admin, id_operation_annee=oa)
                nouvelle.save()
                lignes_rh = list(OperationAnneeRH.objects.filter(id_operation_annee=oa))
                for ligne in RealisationOperationAnneeRH.objects.filter(
                        id_realisation_operation_annee=rea):
                    poste_id = postes.get(ligne.id_poste_id)
                    dup(ligne, admin, id_realisation_operation_annee=nouvelle, id_poste_id=poste_id,
                        id_operation_annee_rh=next((
                            p for p in lignes_rh if p.id_poste_id == poste_id
                            and p.id_organisme_id == ligne.id_organisme_id
                            and p.categorie_depense == ligne.categorie_depense), None)).save()
                for ligne in RealisationFinanceur.objects.filter(id_realisation_operation_annee=rea):
                    dup(ligne, admin, id_realisation_operation_annee=nouvelle,
                        id_financeur=financeur(ligne.id_financeur)).save()
            for rea in RealisationOperationAnneeOrganisme.objects.filter(
                    id_operation_annee_organisme__id_operation_annee__id_operation_id=src_op
            ).select_related('id_operation_annee_organisme__id_operation_annee'):
                oao_src = rea.id_operation_annee_organisme
                oa, _ = OperationAnnee.objects.get_or_create(
                    id_operation_id=op, annee=oao_src.id_operation_annee.annee,
                    defaults={'periodicite': False})
                oao, _ = OperationAnneeOrganisme.objects.get_or_create(
                    id_operation_annee=oa, id_organisme_id=oao_src.id_organisme_id)
                dup(rea, admin, id_operation_annee_organisme=oao).save()
            for globale in OperationRealisationGlobale.objects.filter(id_operation_id=src_op):
                dup(globale, admin, id_operation_id=op).save()
            for aj in AjustementAnnuel.objects.filter(id_operation_id=src_op):
                nouveau = dup(aj, admin, id_operation_id=op)
                nouveau.save()
                for ligne in AjustementAnnuelOrganisme.objects.filter(id_ajustement_annuel=aj):
                    dup(ligne, admin, id_ajustement_annuel=nouveau).save()
                for ligne in AjustementAnnuelRH.objects.filter(id_ajustement_annuel=aj):
                    dup(ligne, admin, id_ajustement_annuel=nouveau,
                        id_poste_id=postes.get(ligne.id_poste_id)).save()
                for ligne in AjustementAnnuelFinanceur.objects.filter(id_ajustement_annuel=aj):
                    dup(ligne, admin, id_ajustement_annuel=nouveau,
                        id_financeur=financeur(ligne.id_financeur)).save()
        for src_met, met in corr['metrique'].items():
            for mesure in Mesure.objects.filter(id_metrique_id=src_met):
                dup(mesure, admin, id_metrique_id=met).save()
        for src_ind, ind in corr['indicateur'].items():
            for score in IndicateurMesure.objects.filter(id_indicateur_id=src_ind):
                dup(score, admin, id_indicateur_id=ind).save()
            for score in IndicateurRealisationGlobale.objects.filter(id_indicateur_id=src_ind):
                dup(score, admin, id_indicateur_id=ind).save()

        # La v1 est une version d'origine : aucun lien vers le plan « Ventilation ».
        objets = objets_du_plan(plan.pk, modeles())
        for modele, nature in ((Operation, 'operation'), (Indicateur, 'indicateur'),
                               (Metrique, 'metrique'), (Poste, 'poste')):
            modele.objects.filter(pk__in=objets[nature]).update(origine=None)

    def _suivi_action_supprimee(self, v1, admin):
        """PA1 n'a pas de suivi dans le plan source : on lui en saisit un (N-1,
        sa première année programmée, calqué sur IP1) pour que sa suppression
        dans la v2 se voie."""
        dup = PlanDuplicationService._dup
        annee = date.today().year - 1
        ip1, pa1 = self._action(v1, 'IP1'), self._action(v1, 'PA1')
        oa_ip1 = OperationAnnee.objects.filter(id_operation=ip1, annee=annee).first()
        oa_pa1 = OperationAnnee.objects.filter(id_operation=pa1, annee=annee).first()
        if not (oa_ip1 and oa_pa1):
            return
        lignes_rh = list(OperationAnneeRH.objects.filter(id_operation_annee=oa_pa1))
        for rea in RealisationOperationAnnee.objects.filter(id_operation_annee=oa_ip1):
            nouvelle = dup(rea, admin, id_operation_annee=oa_pa1,
                           commentaires=f'Animations {annee} — suivi saisi sur la v1')
            nouvelle.save()
            for ligne in RealisationOperationAnneeRH.objects.filter(id_realisation_operation_annee=rea):
                dup(ligne, admin, id_realisation_operation_annee=nouvelle,
                    id_operation_annee_rh=next((
                        p for p in lignes_rh if p.id_poste_id == ligne.id_poste_id
                        and p.id_organisme_id == ligne.id_organisme_id
                        and p.categorie_depense == ligne.categorie_depense), None)).save()
            for ligne in RealisationFinanceur.objects.filter(id_realisation_operation_annee=rea):
                dup(ligne, admin, id_realisation_operation_annee=nouvelle).save()
        for rea in RealisationOperationAnneeOrganisme.objects.filter(
                id_operation_annee_organisme__id_operation_annee=oa_ip1
        ).select_related('id_operation_annee_organisme'):
            oao, _ = OperationAnneeOrganisme.objects.get_or_create(
                id_operation_annee=oa_pa1,
                id_organisme_id=rea.id_operation_annee_organisme.id_organisme_id)
            dup(rea, admin, id_operation_annee_organisme=oao).save()

    def _recoder(self, plan, code):
        for op in self._actions(plan):
            if op.code_operation and op.code_operation.startswith(CODE_SOURCE):
                op.code_operation = code + op.code_operation[len(CODE_SOURCE):]
                op.save(update_fields=['code_operation'])

    def _faire_evoluer(self, v2, code, admin):
        """Les évolutions d'une action entre la v1 et la v2."""
        annee = date.today().year
        pa1 = self._action(v2, 'PA1')
        if pa1:
            pa1.delete()                                   # supprimée
        ip1 = self._action(v2, 'IP1')
        if ip1:
            ip1.libelle = f'{ip1.libelle}{SUFFIXE_RENOMMEE}'  # renommée
            ip1.save(update_fields=['libelle'])
            metrique = ip1.metriques.first()
            if metrique is not None:                        # ajoutée
                ajoutee = ElementCopyService.copy_operation(ip1, admin, target_metrique=metrique)
                ajoutee.libelle = LIBELLE_AJOUTEE
                ajoutee.code_operation = f'{code}NEW1'
                ajoutee.numero_manuel = None
                ajoutee.save(update_fields=['libelle', 'code_operation', 'numero_manuel'])
        cs1 = self._action(v2, 'CS1')
        if cs1:                                            # année retirée
            OperationAnnee.objects.filter(id_operation=cs1, annee=annee - 2).delete()

    # -------------------------------------------------------------------- seed

    def seed(self) -> dict:
        self.log_header('Suivi entre versions au même rang (#803)')
        self.reset()
        source = PlanGestion.objects.filter(nom=PLAN_SOURCE).first()
        if source is None:
            self.log(f'Plan « {PLAN_SOURCE} » introuvable — seeder ignoré.', 'WARNING')
            return {}
        users = self.context.get('users') or []
        admin = users[0] if users else None
        annee = date.today().year

        plans: List[PlanGestion] = []
        for libelle, code, basculee in CHAINES:
            v1 = self._version(source, admin, f'{PREFIXE}{libelle} (v1)', '1', 'valide', None)
            self._cloner_suivi(source, v1, admin)
            self._suivi_action_supprimee(v1, admin)
            self._recoder(v1, code)
            v2 = self._version(v1, admin, f'{PREFIXE}{libelle} (v2)', '2', 'draft', v1)
            self._faire_evoluer(v2, code, admin)
            if basculee:
                cs1 = self._action(v2, 'CS1')
                oa = OperationAnnee.objects.filter(id_operation=cs1, annee=annee - 1).first()
                rea_v1 = RealisationOperationAnnee.objects.filter(
                    id_operation_annee__id_operation=cs1.origine,
                    id_operation_annee__annee=annee - 1).first()
                if oa and rea_v1:
                    RealisationOperationAnnee.objects.create(
                        id_operation_annee=oa, commentaires=RESSAISI,
                        id_niveau_realisation=rea_v1.id_niveau_realisation,
                        budget_realise=rea_v1.budget_realise)
                v2.statut = 'modifie'
                v2.save(update_fields=['statut'])
                transferer_suivi(v2)
                v1.statut = 'archive'
                v1.save(update_fields=['statut'])
            plans += [v1, v2]
            self.log_item('plan', f'{v1.nom} → {v2.nom} ({v2.get_statut_display()})')
            self._created_count += 2
        self.context.set('suivi_versions', plans)
        return {'plans': plans}

    def reset(self) -> int:
        plans = PlanGestion.objects.filter(nom__startswith=PREFIXE)
        count = 0
        op_ids = set()
        for plan in plans:
            op_ids |= plan_operation_ids(plan)
        op_ids |= set(Operation.objects.filter(
            Q(code_operation__startswith=CHAINES[0][1]) | Q(code_operation__startswith=CHAINES[1][1])
        ).values_list('pk', flat=True))
        suivis = SuiviInventaire.objects.filter(id_pg__in=plans)
        count += Protocole.objects.filter(suivis__in=suivis).delete()[0]
        count += suivis.delete()[0]
        count += Operation.objects.filter(pk__in=op_ids).delete()[0]
        # Les versions renvoient l'une vers l'autre : on coupe les liens d'abord.
        plans.update(suivi_poursuivi_dans=None, plan_parent=None)
        count += plans.delete()[0]
        return count

    def get_dry_run_summary(self) -> List[str]:
        return [f'{PREFIXE}{libelle} (v1 → v2)' for libelle, _c, _b in CHAINES]
