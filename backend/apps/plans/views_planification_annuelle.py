"""
API de la planification annuelle ajustée (#794).

- ``GET  /api/plans/planification-annuelle/plan/{plan_id}/?annee=N``
  tableau de l'année : pour chaque action, plan de gestion / ajusté, statut,
  mois, reports reçus, revue ; « X / Y actions revues ».
- ``GET | PUT | DELETE /api/plans/planification-annuelle/operation/{id}/{annee}/``
  ajustement d'une action pour une année. ``PUT`` l'enregistre et marque
  l'action revue ; ``DELETE`` revient à la programmation du plan.
- ``POST /api/plans/planification-annuelle/operation/{id}/{annee}/report/``
  report total (décalage de la suite) ou partiel, avec ``apercu: true`` pour
  l'avant / après sans rien écrire.

Données de suivi : lecture pour les utilisateurs liés au plan, écriture pour
le périmètre de saisie des suivis (#740), jamais pour un rédacteur externe
(#700) ; écriture sur un plan validé seulement. Aucune de ces routes n'est
ouverte à l'exploration (#683) : budget et RH n'en sortent pas.
"""
import re

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from .access import assert_suivi_access, plan_operation_ids, user_can_access_suivi
from .models import PlanGestion
from .models_operations import Financeur, Operation, OperationAnneeOrganisme
from .models_planification import AjustementAnnuel, AjustementAnnuelOrganisme
from .planification_annuelle import (
    PLANIFIEE, REPORTEE, Planification, ReportImpossible, contenu_ajuste, contenu_pg,
    ecrire, financeurs_pg,
)
from .serializers_planification import (
    AjustementsDuPlanSerializer, ApercuReportSerializer, ContenuAnnuelSerializer,
    DetailAnnuelSerializer,
    ReportDemandeSerializer, TableauAnnuelSerializer,
)
from .services_export_finance import plan_operations, temps_par_poste

#: Refus de report qui tiennent à la demande (400) ; les autres tiennent à l'état (409).
_REPORT_INVALIDE = {'annee_hors_plan', 'annee_report_invalide', 'annee_report_hors_plan'}


def _codes(plan):
    from .serializers_operations import compute_operation_codes_for_plan
    try:
        return compute_operation_codes_for_plan(plan.pk)
    except Exception:
        return {}


def _ordre(code, op):
    morceaux = re.match(r'^([^\d]*)(\d*)', code or '')
    lettres, nombre = morceaux.group(1), morceaux.group(2)
    return (lettres or 'zzz', int(nombre) if nombre else 0, op.id_operation)


def _peut_saisir(user, plan):
    return plan.statut in PlanGestion.VALIDATED_STATUSES and user_can_access_suivi(user, plan)


def _realise(planif, op_id, annee):
    realisation = planif.realisation(op_id, annee)
    niveau = getattr(realisation, 'id_niveau_realisation', None)
    return {'saisi': realisation is not None,
            'niveau': getattr(niveau, 'mnemonique', None)}


def _annee_demandee(valeur, annees):
    from datetime import date
    if valeur in (None, ''):
        courante = date.today().year
        if not annees:
            return courante
        return min(max(courante, annees[0]), annees[-1])
    try:
        annee = int(valeur)
    except (TypeError, ValueError):
        raise ValidationError({'annee': "Année invalide."})
    if annee not in annees:
        raise ValidationError({'annee': "Cette année n'appartient pas au plan de gestion.",
                               'code': 'annee_hors_plan'})
    return annee


class TableauPlanificationAnnuelleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Planification annuelle d'un plan pour une année (#794)",
        parameters=[OpenApiParameter(
            'annee', int, required=False,
            description="Année du plan (défaut : l'année en cours, bornée à la période du plan).")],
        responses=TableauAnnuelSerializer,
    )
    def get(self, request, plan_id):
        plan = get_object_or_404(PlanGestion, pk=plan_id)
        assert_suivi_access(request.user, plan, lecture=True)
        annees = plan.annees_plan()
        annee = _annee_demandee(request.query_params.get('annee'), annees)
        codes = _codes(plan)
        operations = sorted(plan_operations(plan),
                            key=lambda op: _ordre(codes.get(op.id_operation), op))
        planif = Planification(plan, operations)
        lignes, revues = [], 0
        for op in operations:
            op_id = op.id_operation
            ajustement = planif.ajustement(op_id, annee)
            revue = bool(ajustement and ajustement.date_revue)
            revues += revue
            globale = planif.annee_globale(op_id) if op.programmation_globale else None
            lignes.append({
                'id_operation': op_id,
                'code': codes.get(op_id) or op.code_operation or '',
                'libelle': op.libelle or '',
                'programmation_globale': bool(op.programmation_globale),
                'pg': planif.resume(op_id, planif.pg(op_id, annee)),
                'pg_global': planif.resume(op_id, contenu_pg(globale)) if globale else None,
                'ajuste': planif.resume(op_id, planif.effectif(op_id, annee)),
                'ajustee': ajustement is not None,
                'diverge': planif.diverge(op_id, annee),
                'revue': revue,
                'date_revue': ajustement.date_revue if ajustement else None,
                'reports_entrants': planif.reports_entrants(op_id, annee),
                'realise': _realise(planif, op_id, annee),
            })
        donnees = {
            'id_pg': plan.pk, 'annee': annee, 'annees': annees,
            'revues': revues, 'total': len(operations),
            'peut_saisir': _peut_saisir(request.user, plan),
            'actions': lignes,
        }
        return Response(TableauAnnuelSerializer(donnees).data)


class AjustementsDuPlanView(APIView):
    """Toutes les années ajustées des actions d'un plan, pour le suivi."""
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Années ajustées des actions d'un plan (#794)",
        description="Le suivi (icônes, budget / RH, planification mensuelle) calcule son "
                    "prévu sur la planification ajustée : une année sans ajustement suit "
                    "le plan de gestion.",
        responses=AjustementsDuPlanSerializer,
    )
    def get(self, request, plan_id):
        plan = get_object_or_404(PlanGestion, pk=plan_id)
        assert_suivi_access(request.user, plan, lecture=True)
        ajustements = (
            AjustementAnnuel.objects.filter(id_operation__in=plan_operation_ids(plan))
            .prefetch_related('organismes__id_organisme', 'financeurs', 'rh_lignes__id_poste')
            .order_by('id_operation', 'annee'))
        lignes = []
        for ajustement in ajustements:
            contenu = contenu_ajuste(ajustement)
            postes = {l.id_poste_id: l.id_poste for l in ajustement.rh_lignes.all() if l.id_poste_id}
            noms = {o.id_organisme_id: o.id_organisme.nom_organisme or ''
                    for o in ajustement.organismes.all()}
            for org in contenu['organismes']:
                org['organisme_nom'] = noms.get(org['id_organisme'], '')
            for ligne in contenu['rh_lignes']:
                poste = postes.get(ligne['id_poste'])
                ligne['poste_cout_jour'] = getattr(poste, 'cout_jour', None)
                ligne['poste_id_organisme'] = getattr(poste, 'id_organisme_id', None)
            lignes.append(dict(
                contenu, id_operation=ajustement.id_operation_id, annee=ajustement.annee,
                revue=ajustement.date_revue is not None))
        return Response(AjustementsDuPlanSerializer({'ajustements': lignes}).data)


class _AjustementBase(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def charger(self, request, operation_id, annee, lecture):
        operation = get_object_or_404(Operation, pk=operation_id)
        plan = operation.get_plan_de_gestion()
        if plan is None:
            return None, None, None, Response(
                {'detail': "Cette action n'est rattachée à aucun plan de gestion."},
                status=status.HTTP_404_NOT_FOUND)
        assert_suivi_access(request.user, plan, lecture=lecture)
        if int(annee) not in plan.annees_plan():
            return None, None, None, Response(
                {'detail': "Cette année n'appartient pas au plan de gestion.",
                 'code': 'annee_hors_plan'}, status=status.HTTP_400_BAD_REQUEST)
        if not lecture and plan.statut not in PlanGestion.VALIDATED_STATUSES:
            return None, None, None, Response(
                {'detail': "La planification annuelle s'ajuste une fois le plan de gestion validé.",
                 'code': 'plan_non_valide'}, status=status.HTTP_409_CONFLICT)
        return operation, plan, Planification(plan, [operation]), None


def _detail(request, planif, operation, plan, annee):
    op_id = operation.id_operation
    ajustement = planif.ajustement(op_id, annee)
    globale = planif.annee_globale(op_id) if operation.programmation_globale else None
    pg = planif.pg(op_id, annee)
    effectif = planif.effectif(op_id, annee)
    lu = None
    if ajustement is not None:
        revue_par = ajustement.id_utilisateur_revue
        lu = dict(contenu_ajuste(ajustement),
                  id_ajustement_annuel=ajustement.pk, date_revue=ajustement.date_revue,
                  revue_par=revue_par.get_full_name() if revue_par else None,
                  date_maj=ajustement.date_maj)
    donnees = {
        'id_operation': op_id,
        'code': _codes(plan).get(op_id) or operation.code_operation or '',
        'libelle': operation.libelle or '',
        'annee': annee,
        'annees': planif.annees,
        'reglages': {
            'ventilation_mode': operation.ventilation_mode or 'none',
            'declinaison_par_poste': bool(operation.declinaison_par_poste),
            'declinaison_par_type_cout': bool(operation.declinaison_par_type_cout),
            'cout_salarial_auto': bool(operation.cout_salarial_auto),
            'programmation_globale': bool(operation.programmation_globale),
            'temps_par_poste': temps_par_poste(operation),
        },
        'pg': pg,
        'pg_resume': planif.resume(op_id, pg),
        'pg_global': contenu_pg(globale) if globale else None,
        'pg_global_resume': planif.resume(op_id, contenu_pg(globale)) if globale else None,
        'financeurs_pg': financeurs_pg(operation),
        'ajustement': lu,
        'effectif': effectif,
        'effectif_resume': planif.resume(op_id, effectif),
        'diverge': planif.diverge(op_id, annee),
        'reports_entrants': planif.reports_entrants(op_id, annee),
        'realise': _realise(planif, op_id, annee),
        'fixe': planif.annee_fixee(op_id, annee),
        'peut_saisir': _peut_saisir(request.user, plan),
        'choix': _choix(plan, operation, planif),
    }
    return DetailAnnuelSerializer(donnees).data


def _choix(plan, operation, planif):
    """Organismes, postes et financeurs que le formulaire peut proposer."""
    from apps.users.models import BibOrganismes
    organismes = BibOrganismes.objects.filter(
        pk__in=_organismes_admis(plan, operation, planif)).order_by('nom_organisme')
    return {
        'organismes': [{'id_organisme': o.pk, 'nom': o.nom_organisme or ''} for o in organismes],
        'postes': [
            {'id_poste': p.pk, 'libelle': p.libelle or str(p), 'id_organisme': p.id_organisme_id,
             'cout_jour': p.cout_jour, 'finance_par_defaut': p.is_finance_par_defaut()}
            for p in sorted(planif.postes.values(), key=lambda p: (p.libelle or '', p.pk))],
        'financeurs': [
            {'id_financeur': f.pk, 'nom': f.nom}
            for f in Financeur.objects.filter(id_pg=plan).order_by('nom', 'pk')],
    }


def _organismes_admis(plan, operation, planif):
    admis = {o.id_organisme for o in plan.get_organismes_gestionnaires()}
    admis |= set(OperationAnneeOrganisme.objects.filter(
        id_operation_annee__id_operation=operation).values_list('id_organisme', flat=True))
    admis |= set(AjustementAnnuelOrganisme.objects.filter(
        id_ajustement_annuel__id_operation=operation).values_list('id_organisme', flat=True))
    return admis


def _controler_references(contenu, plan, operation, planif):
    """Organismes, postes et financeurs doivent appartenir au plan."""
    erreurs = {}
    organismes = _organismes_admis(plan, operation, planif)
    ids = [o['id_organisme'] for o in contenu['organismes']]
    if len(ids) != len(set(ids)):
        erreurs['organismes'] = "Un organisme figure deux fois."
    elif set(ids) - organismes:
        erreurs['organismes'] = "Organisme étranger au plan de gestion."
    for ligne in contenu['rh_lignes']:
        if ligne.get('id_poste') is not None and ligne['id_poste'] not in planif.postes:
            erreurs['rh_lignes'] = "Poste étranger au plan de gestion."
        if ligne.get('id_organisme') is not None and ligne['id_organisme'] not in organismes:
            erreurs['rh_lignes'] = "Organisme étranger au plan de gestion."
    financeurs = set(Financeur.objects.filter(id_pg=plan).values_list('pk', flat=True))
    ids = [f['id_financeur'] for f in contenu['financeurs']]
    if len(ids) != len(set(ids)):
        erreurs['financeurs'] = "Un financeur figure deux fois."
    elif set(ids) - financeurs:
        erreurs['financeurs'] = "Financeur étranger au plan de gestion."
    if erreurs:
        raise ValidationError(erreurs)


class AjustementAnnuelView(_AjustementBase):

    @extend_schema(summary="Ajustement d'une action pour une année (#794)",
                   responses=DetailAnnuelSerializer)
    def get(self, request, operation_id, annee):
        operation, plan, planif, refus = self.charger(request, operation_id, annee, lecture=True)
        if refus:
            return refus
        return Response(_detail(request, planif, operation, plan, int(annee)))

    @extend_schema(
        summary="Enregistrer l'ajustement d'une action pour une année (#794)",
        description="Remplace l'ajustement de l'année (organismes, temps et financeurs "
                    "compris) et marque l'action revue, même sans changement. Un report "
                    "passe par la route `report/`.",
        request=ContenuAnnuelSerializer, responses=DetailAnnuelSerializer,
    )
    def put(self, request, operation_id, annee):
        operation, plan, planif, refus = self.charger(request, operation_id, annee, lecture=False)
        if refus:
            return refus
        annee = int(annee)
        serializer = ContenuAnnuelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contenu = dict(serializer.validated_data)
        existant = planif.ajustement(operation.id_operation, annee)
        if contenu['statut'] == REPORTEE and (existant is None or existant.statut != REPORTEE):
            return Response(
                {'detail': "Pour reporter l'action, utiliser le report (aperçu du décalage).",
                 'code': 'report_par_la_route_dediee'}, status=status.HTTP_400_BAD_REQUEST)
        _controler_references(contenu, plan, operation, planif)
        # Le report se pose par sa route ; un changement de statut l'annule.
        garde_report = existant is not None and existant.statut == contenu['statut']
        contenu['annee_report'] = existant.annee_report if garde_report else None
        contenu['report_de'] = existant.report_de if existant is not None else None
        if contenu['statut'] != PLANIFIEE and contenu['statut'] != REPORTEE:
            contenu['report_de'] = None
        ecrire(operation, annee, contenu, request.user, revue=True, ajustement=existant)
        planif = Planification(plan, [operation])
        return Response(_detail(request, planif, operation, plan, annee))

    @extend_schema(
        summary="Revenir à la programmation du plan de gestion pour l'année (#794)",
        responses={204: OpenApiResponse(description="Ajustement supprimé.")},
    )
    def delete(self, request, operation_id, annee):
        operation, plan, planif, refus = self.charger(request, operation_id, annee, lecture=False)
        if refus:
            return refus
        AjustementAnnuel.objects.filter(id_operation=operation, annee=int(annee)).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ReportAnnuelView(_AjustementBase):

    @extend_schema(
        summary="Reporter une action (#794)",
        description=(
            "Report **total** : l'année passe « reportée » et toute la suite de la "
            "programmation est décalée d'autant (moyens et mois, ajustés ou non). Une année "
            "où du réalisé est saisi ne bouge pas ; ce qui tombe après la fin du plan "
            "(prolongation comprise) est abandonné.\n\n"
            "Report **partiel** (`partiel: true`) : l'année reste planifiée, l'année cible "
            "reçoit en plus le reste à faire (prévu − réalisé) ; la suite ne bouge pas.\n\n"
            "`apercu: true` rend l'avant / après sans rien écrire."),
        request=ReportDemandeSerializer, responses=ApercuReportSerializer,
    )
    def post(self, request, operation_id, annee):
        operation, plan, planif, refus = self.charger(request, operation_id, annee, lecture=False)
        if refus:
            return refus
        demande = ReportDemandeSerializer(data=request.data)
        demande.is_valid(raise_exception=True)
        donnees = demande.validated_data
        args = (operation.id_operation, int(annee), donnees['annee_report'])
        try:
            if donnees['apercu']:
                resultat = planif.apercu_report(*args, partiel=donnees['partiel'])
            else:
                resultat = planif.reporter(*args, request.user, partiel=donnees['partiel'])
        except ReportImpossible as refus_report:
            return Response(
                {'detail': str(refus_report), 'code': refus_report.code},
                status=(status.HTTP_400_BAD_REQUEST if refus_report.code in _REPORT_INVALIDE
                        else status.HTTP_409_CONFLICT))
        resultat = dict(resultat, applique=not donnees['apercu'])
        resultat.pop('contenus', None)
        return Response(ApercuReportSerializer(resultat).data)
