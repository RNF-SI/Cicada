"""
Vues API REST pour les Indicateurs, Métriques et Mesures.
"""
from django.db.models import Q
from django.shortcuts import get_object_or_404

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from django.db import transaction

from .models_indicateurs import (
    Indicateur, Metrique, Mesure, IndicateurMesure, IndicateurRealisationGlobale,
    CorIndicateurTaxon, CorIndicateurHabitat, CorIndicateurGeologie,
)
from .models_enjeux import NiveauExigence, ResultatAttendu
from .models import CorRolePlan
from apps.users.permissions import IsReferent
from .permissions import CanModifyOnlyDraftPlan
from .reorder import do_reorder
from .serializers_indicateurs import (
    IndicateurSerializer, IndicateurListSerializer, IndicateurCreateSerializer,
    MetriqueSerializer, MetriqueListSerializer, MetriqueCreateSerializer,
    MesureSerializer, MesureCreateSerializer, IndicateurMesureSerializer,
)
from .filters_indicateurs import IndicateurFilter, MetriqueFilter, MesureFilter


class IndicateurViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Indicateurs.

    Endpoints:
    - GET /api/plans/indicateurs/ - Liste
    - GET /api/plans/indicateurs/{id}/ - Détail
    - POST /api/plans/indicateurs/ - Créer
    - PATCH /api/plans/indicateurs/{id}/ - Modifier
    - DELETE /api/plans/indicateurs/{id}/ - Supprimer
    - GET /api/plans/indicateurs/by-ne/{ne_id}/ - Par niveau d'exigence
    """

    queryset = Indicateur.objects.select_related(
        'id_ne', 'id_resultat_attendu', 'type_indicateur',
        'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related(
        'metriques', 'metriques__type_metrique', 'metriques__id_utilisateur_ajout',
        'metriques__mesures', 'metriques__mesures__id_utilisateur_ajout',
        'taxons', 'habitats', 'geologies',
        'metriques__operations', 'metriques__operations__id_priorite', 'metriques__operations__id_utilisateur_ajout'
    )

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = IndicateurFilter
    search_fields = ['nom_indicateur', 'description']
    ordering_fields = ['nom_indicateur', 'date_ajout', 'date_maj', 'id_indicateur']
    ordering = ['id_indicateur']

    def get_plan_for_payload(self, data):
        """#248 — check draft à la création via le parent (NE ou RA)."""
        ne_id = data.get('id_ne')
        if ne_id:
            try:
                return NiveauExigence.objects.select_related(
                    'id_olt__id_enjeu'
                ).get(pk=ne_id).get_plan_de_gestion()
            except NiveauExigence.DoesNotExist:
                return None
        ra_id = data.get('id_resultat_attendu')
        if ra_id:
            try:
                return ResultatAttendu.objects.get(pk=ra_id).get_plan_de_gestion()
            except ResultatAttendu.DoesNotExist:
                return None
        return None

    def get_serializer_class(self):
        if self.action == 'list':
            return IndicateurListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return IndicateurCreateSerializer
        return IndicateurSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_redacteur_principal():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                Q(id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme) |
                Q(id_resultat_attendu__id_oo__pressions__id_facteur_influence__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme)
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_ne__id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_resultat_attendu__id_oo__pressions__id_facteur_influence__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_resultat_attendu__id_oo__pressions__id_facteur_influence__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_ne__id_olt__id_enjeu__id_pg__statut='valide') |
            Q(id_resultat_attendu__id_oo__pressions__id_facteur_influence__id_enjeu__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=True, methods=['get'], url_path='global')
    def global_evaluation(self, request, pk=None):
        """
        #355 — Évaluation GLOBALE d'un indicateur (État/Pression) sur la période.

        GET /api/plans/indicateurs/{id}/global/

        Retourne, par métrique et au niveau indicateur :
          - la série annuelle (valeur → score 1-5),
          - l'état courant (score de la dernière année renseignée),
          - la moyenne des scores et la tendance (premier ↔ dernier).
        La « globale partielle » est naturelle : seules les années renseignées
        comptent. Lecture seule (GET), accès aligné sur le tableau de bord.
        """
        from collections import defaultdict

        ind = self.get_object()

        def _score(value, m):
            """1-5 selon la grille de la métrique, 0 si hors plage / non numérique."""
            try:
                v = float(value)
            except (TypeError, ValueError):
                return 0
            inactive = set(getattr(m, 'inactive_levels', None) or [])
            for i in range(1, 6):
                if i in inactive:
                    continue
                inf = getattr(m, f'score_{i}_inf', None)
                sup = getattr(m, f'score_{i}_sup', None)
                if inf is None or sup is None:
                    continue
                if float(inf) <= v <= float(sup):
                    return i
            return 0

        def _trend(scores_by_year):
            """Tendance : comparaison premier ↔ dernier score renseigné."""
            years = sorted(scores_by_year.keys())
            if len(years) < 2:
                return 'stable'
            first, last = scores_by_year[years[0]], scores_by_year[years[-1]]
            if last > first:
                return 'hausse'
            if last < first:
                return 'baisse'
            return 'stable'

        metriques_payload = []
        ind_year_scores = defaultdict(list)  # année -> [scores métriques]

        for m in ind.metriques.all().prefetch_related('mesures'):
            # Dernière mesure par année (par date_mesure puis date_ajout)
            by_year = {}
            for mes in m.mesures.all():
                if not mes.date_mesure:
                    continue
                y = mes.date_mesure.year
                key = (mes.date_mesure, mes.date_ajout)
                prev = by_year.get(y)
                if prev is None or key >= prev['key']:
                    by_year[y] = {'valeur': mes.valeur, 'key': key}

            series = []
            scores_by_year = {}
            for y in sorted(by_year.keys()):
                val = by_year[y]['valeur']
                sc = _score(val, m)
                series.append({'annee': y, 'valeur': val, 'score': sc or None})
                if sc > 0:
                    scores_by_year[y] = sc
                    ind_year_scores[y].append(sc)

            etat_courant = None
            if scores_by_year:
                ly = max(scores_by_year.keys())
                etat_courant = {'annee': ly, 'score': scores_by_year[ly]}
            moyenne = (
                round(sum(scores_by_year.values()) / len(scores_by_year), 2)
                if scores_by_year else None
            )
            metriques_payload.append({
                'id_metrique': m.id_metrique,
                'nom_metrique': m.nom_metrique,
                'etat_reference': m.etat_reference,
                'sens_variation': m.sens_variation,
                'series': series,
                'etat_courant': etat_courant,
                'moyenne': moyenne,
                'tendance': _trend(scores_by_year),
            })

        # Agrégat indicateur : moyenne des scores métriques par année
        ind_series = []
        ind_scores_by_year = {}
        for y in sorted(ind_year_scores.keys()):
            avg = round(sum(ind_year_scores[y]) / len(ind_year_scores[y]), 2)
            ind_series.append({'annee': y, 'score': avg})
            ind_scores_by_year[y] = avg
        etat_courant_score = (
            ind_scores_by_year[max(ind_scores_by_year)] if ind_scores_by_year else None
        )
        moyenne_score = (
            round(sum(ind_scores_by_year.values()) / len(ind_scores_by_year), 2)
            if ind_scores_by_year else None
        )

        # #356 — Surcharge manuelle d'interprétation (icône d'évaluation forcée).
        # Le score calculé reste inchangé ; l'icône affichée = override si posé.
        override = ind.get_evaluation_globale()
        score_override = override.score_override if override else None
        etat_courant_effectif = (
            score_override if score_override is not None else etat_courant_score
        )

        return Response({
            'id_indicateur': ind.id_indicateur,
            'nom_indicateur': ind.nom_indicateur,
            'type_indicateur': getattr(ind.type_indicateur, 'mnemonique', None),
            'type_indicateur_label': getattr(ind.type_indicateur, 'label', None),
            'metriques': metriques_payload,
            'serie': ind_series,
            'etat_courant_score': etat_courant_score,
            'moyenne_score': moyenne_score,
            'tendance': _trend(ind_scores_by_year),
            'score_override': score_override,
            'commentaire': override.commentaire_override if override else None,
            'etat_courant_effectif': etat_courant_effectif,
            'manuel': score_override is not None,
        })

    @action(detail=False, methods=['post'], url_path='reorder')
    def reorder(self, request):
        """
        Réordonne les indicateurs d'un parent NE ou RA (#249/#261).

        Cas spécial : un indicateur a deux parents possibles (id_ne XOR
        id_resultat_attendu). Le payload doit donc inclure `parent_type`.

        Payload:
            {
                "parent_type": "ne" | "ra",
                "parent_id": <id_ne|id_ra>,
                "ordered_ids": [id1, id2, ...]
            }
        """
        parent_type = request.data.get('parent_type')
        if parent_type not in ('ne', 'ra'):
            return Response(
                {"detail": "Le champ 'parent_type' doit valoir 'ne' ou 'ra'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        parent_field = 'id_ne' if parent_type == 'ne' else 'id_resultat_attendu'
        return do_reorder(self, request, parent_filter=parent_field)

    @action(detail=True, methods=['post'], url_path='move')
    def move(self, request, pk=None):
        """
        Déplace un indicateur entre niveaux d'exigence (NE) ou résultats
        attendus (RA) — #261.

        Payload : {"new_parent_type": "ne"|"ra", "new_parent_id": <int>, "position": <int>}

        Garde-fous :
        - Le nouveau parent doit exister et être dans le même plan que l'ancien.
        - Le plan doit être en brouillon (verrou #248).
        - Renumérote les siblings dans le nouveau parent.
        """
        indicateur = self.get_object()
        new_parent_type = request.data.get('new_parent_type')
        new_parent_id = request.data.get('new_parent_id')
        position = request.data.get('position', 0)

        if new_parent_type not in ('ne', 'ra') or new_parent_id is None:
            return Response(
                {"detail": "Payload invalide : 'new_parent_type' ('ne'|'ra') et 'new_parent_id' requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            new_parent_id = int(new_parent_id)
            position = int(position)
        except (TypeError, ValueError):
            return Response(
                {"detail": "'new_parent_id' et 'position' doivent être des entiers."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            if new_parent_type == 'ne':
                new_parent = NiveauExigence.objects.get(pk=new_parent_id)
            else:
                new_parent = ResultatAttendu.objects.get(pk=new_parent_id)
        except (NiveauExigence.DoesNotExist, ResultatAttendu.DoesNotExist):
            return Response(
                {"detail": "Parent introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Garde : même plan que la source
        source_plan = indicateur.get_plan_de_gestion()
        target_plan = new_parent.get_plan_de_gestion()
        if source_plan and target_plan and source_plan.pk != target_plan.pk:
            return Response(
                {"detail": "Déplacement entre plans interdit."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Verrou #248 — plan doit être en statut éditable (draft uniquement)
        if target_plan and target_plan.statut not in CanModifyOnlyDraftPlan.EDITABLE_STATUSES:
            return Response(
                {"detail": "Modification interdite hors brouillon."},
                status=status.HTTP_403_FORBIDDEN,
            )

        filter_kwargs = (
            {'id_ne': new_parent.pk} if new_parent_type == 'ne'
            else {'id_resultat_attendu': new_parent.pk}
        )

        with transaction.atomic():
            if new_parent_type == 'ne':
                indicateur.id_ne = new_parent
                indicateur.id_resultat_attendu = None
            else:
                indicateur.id_ne = None
                indicateur.id_resultat_attendu = new_parent
            indicateur.ordre = position
            indicateur.save()

            # Renumérotation des siblings dans le nouveau parent
            siblings = (
                Indicateur.objects
                .filter(**filter_kwargs)
                .exclude(pk=indicateur.pk)
                .order_by('ordre', 'id_indicateur')
            )
            for idx, sib in enumerate(siblings):
                new_pos = idx if idx < position else idx + 1
                if sib.ordre != new_pos:
                    sib.ordre = new_pos
                    sib.save(update_fields=['ordre'])

        serializer = self.get_serializer(indicateur)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path=r'by-ne/(?P<ne_id>\d+)')
    def by_ne(self, request, ne_id=None):
        """
        Récupérer les indicateurs d'un niveau d'exigence.

        GET /api/plans/indicateurs/by-ne/{ne_id}/
        """
        ne = get_object_or_404(NiveauExigence, id_ne=ne_id)
        indicateurs = self.get_queryset().filter(id_ne=ne)
        return Response({
            'ne_id': int(ne_id),
            'ne_libelle': ne.libelle,
            'indicateurs': IndicateurSerializer(indicateurs, many=True).data,
            'total': indicateurs.count()
        })

    @action(detail=False, methods=['get'], url_path=r'by-ra/(?P<ra_id>\d+)')
    def by_resultat_attendu(self, request, ra_id=None):
        """
        Récupérer les indicateurs d'un résultat attendu.

        GET /api/plans/indicateurs/by-ra/{ra_id}/
        """
        ra = get_object_or_404(ResultatAttendu, id_ra=ra_id)
        indicateurs = self.get_queryset().filter(id_resultat_attendu=ra)
        return Response({
            'ra_id': int(ra_id),
            'ra_libelle': ra.libelle,
            'indicateurs': IndicateurSerializer(indicateurs, many=True).data,
            'total': indicateurs.count()
        })

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplique un indicateur (avec ses métriques et liens taxonomiques)
        sur un ou plusieurs niveaux d'exigence ou résultats attendus cibles
        (#262).

        POST /api/plans/indicateurs/{id}/duplicate/
        Body: { "ne_ids": [int], "ra_ids": [int] }

        Retourne la liste des IDs des indicateurs créés. Le clone porte le
        même nom (suffixe « (copie) ») et reprend la description, les
        métriques (avec leurs seuils de scores) et les liens taxon/
        habitat/géologie. Les mesures (données chiffrées dans le temps) ne
        sont **pas** copiées : elles restent associées à l'indicateur
        d'origine.
        """
        source = self.get_object()
        ne_ids = request.data.get('ne_ids') or []
        ra_ids = request.data.get('ra_ids') or []

        if not isinstance(ne_ids, list) or not isinstance(ra_ids, list):
            return Response(
                {'error': "ne_ids et ra_ids doivent être des listes."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not ne_ids and not ra_ids:
            return Response(
                {'error': "Au moins un niveau d'exigence ou résultat attendu cible est requis."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Le get_queryset garantit déjà que la source est accessible à
        # l'utilisateur. Pour les cibles, on vérifie qu'elles appartiennent
        # à un plan en draft accessible (CanModifyOnlyDraftPlan ne couvre
        # pas explicitement ce cas — on contrôle ici).
        targets_ne = list(NiveauExigence.objects.filter(pk__in=ne_ids).select_related('id_olt__id_enjeu__id_pg'))
        targets_ra = list(ResultatAttendu.objects.filter(pk__in=ra_ids).select_related('id_oo'))

        for ne in targets_ne:
            plan = ne.get_plan_de_gestion()
            if plan is None or plan.statut != 'draft':
                return Response(
                    {'error': f"Le niveau d'exigence {ne.id_ne} n'est pas dans un plan en brouillon."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        for ra in targets_ra:
            plan = ra.get_plan_de_gestion()
            if plan is None or plan.statut != 'draft':
                return Response(
                    {'error': f"Le résultat attendu {ra.id_ra} n'est pas dans un plan en brouillon."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        with transaction.atomic():
            created = []
            for ne in targets_ne:
                created.append(self._clone_indicateur(source, id_ne=ne, id_resultat_attendu=None, user=request.user))
            for ra in targets_ra:
                created.append(self._clone_indicateur(source, id_ne=None, id_resultat_attendu=ra, user=request.user))

        return Response({
            'created_ids': [ind.id_indicateur for ind in created],
            'count': len(created),
        }, status=status.HTTP_201_CREATED)

    @staticmethod
    def _clone_indicateur(source: Indicateur, id_ne, id_resultat_attendu, user) -> Indicateur:
        """
        Clone un indicateur sur un nouveau parent. Copie : champs simples,
        métriques (avec seuils de scores), liens taxonomiques. Ne copie
        PAS les mesures (données dans le temps qui restent rattachées
        à l'instance d'origine).
        """
        new_ind = Indicateur.objects.create(
            id_ne=id_ne,
            id_resultat_attendu=id_resultat_attendu,
            nom_indicateur=f"{source.nom_indicateur} (copie)",
            description=source.description,
            type_indicateur=source.type_indicateur,
            est_standardise=source.est_standardise,
            id_utilisateur_ajout=user,
        )
        # Cloner les métriques
        for met in source.metriques.all():
            Metrique.objects.create(
                id_indicateur=new_ind,
                nom_metrique=met.nom_metrique,
                description=met.description,
                type_metrique=met.type_metrique,
                unite=met.unite,
                ponderation=met.ponderation,
                etat_reference=met.etat_reference,
                score_1_inf=met.score_1_inf, score_1_sup=met.score_1_sup,
                score_2_inf=met.score_2_inf, score_2_sup=met.score_2_sup,
                score_3_inf=met.score_3_inf, score_3_sup=met.score_3_sup,
                score_4_inf=met.score_4_inf, score_4_sup=met.score_4_sup,
                score_5_inf=met.score_5_inf, score_5_sup=met.score_5_sup,
                id_utilisateur_ajout=user,
            )
        # Cloner les liens taxonomiques
        for cor in source.taxons.all():
            CorIndicateurTaxon.objects.create(
                id_indicateur=new_ind,
                cd_nom=cor.cd_nom,
                nom_complet=cor.nom_complet,
                nom_vern=cor.nom_vern,
            )
        for cor in source.habitats.all():
            CorIndicateurHabitat.objects.create(
                id_indicateur=new_ind,
                cd_hab=cor.cd_hab,
                lb_hab_fr=cor.lb_hab_fr,
            )
        for cor in source.geologies.all():
            CorIndicateurGeologie.objects.create(
                id_indicateur=new_ind,
                id_inpg=cor.id_inpg,
                nom=cor.nom,
            )
        return new_ind


class MetriqueViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Métriques.

    Endpoints:
    - GET /api/plans/metriques/ - Liste
    - GET /api/plans/metriques/{id}/ - Détail
    - POST /api/plans/metriques/ - Créer
    - PATCH /api/plans/metriques/{id}/ - Modifier
    - DELETE /api/plans/metriques/{id}/ - Supprimer
    - GET /api/plans/metriques/by-indicateur/{indicateur_id}/ - Par indicateur
    """

    queryset = Metrique.objects.select_related(
        'id_indicateur', 'type_metrique', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    ).prefetch_related('mesures', 'mesures__id_utilisateur_ajout')

    permission_classes = [permissions.IsAuthenticated, IsReferent, CanModifyOnlyDraftPlan]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MetriqueFilter
    search_fields = ['nom_metrique', 'description']
    ordering_fields = ['nom_metrique', 'date_ajout', 'date_maj', 'id_metrique']
    ordering = ['id_metrique']

    def get_plan_for_payload(self, data):
        """#248 — check draft à la création via l'indicateur parent."""
        indicateur_id = data.get('id_indicateur')
        if not indicateur_id:
            return None
        try:
            return Indicateur.objects.select_related(
                'id_ne__id_olt__id_enjeu', 'id_resultat_attendu'
            ).get(pk=indicateur_id).get_plan_de_gestion()
        except Indicateur.DoesNotExist:
            return None

    def get_serializer_class(self):
        if self.action == 'list':
            return MetriqueListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return MetriqueCreateSerializer
        return MetriqueSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_redacteur_principal():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_indicateur__id_ne__id_olt__id_enjeu__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-indicateur/(?P<indicateur_id>\d+)')
    def by_indicateur(self, request, indicateur_id=None):
        """
        Récupérer les métriques d'un indicateur.

        GET /api/plans/metriques/by-indicateur/{indicateur_id}/
        """
        indicateur = get_object_or_404(Indicateur, id_indicateur=indicateur_id)
        metriques = self.get_queryset().filter(id_indicateur=indicateur)
        return Response({
            'indicateur_id': int(indicateur_id),
            'indicateur_nom': indicateur.nom_indicateur,
            'metriques': MetriqueSerializer(metriques, many=True).data,
            'total': metriques.count()
        })


class MesureViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour les Mesures.

    Endpoints:
    - GET /api/plans/mesures/ - Liste
    - GET /api/plans/mesures/{id}/ - Détail
    - POST /api/plans/mesures/ - Créer
    - PATCH /api/plans/mesures/{id}/ - Modifier
    - DELETE /api/plans/mesures/{id}/ - Supprimer
    - GET /api/plans/mesures/by-metrique/{metrique_id}/ - Par métrique
    """

    queryset = Mesure.objects.select_related(
        'id_metrique', 'id_utilisateur_ajout', 'id_utilisateur_maj'
    )

    # Pas de CanModifyOnlyDraftPlan : une Mesure est une valeur *réalisée*
    # (indicateur de réponse, datée via date_mesure), saisie pendant la vie
    # active du plan — comme la réalisation annuelle (RealisationOperationAnnee).
    # Le verrou « brouillon uniquement » (#248) bloquait à tort cette saisie sur
    # un plan validé (403 à l'enregistrement d'un indicateur de réponse).
    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_class = MesureFilter
    search_fields = ['valeur', 'commentaire']
    ordering_fields = ['date_mesure', 'date_ajout', 'date_maj']
    ordering = ['-date_mesure', '-date_ajout']

    def get_plan_for_payload(self, data):
        """#248 — check draft à la création via la métrique parent."""
        metrique_id = data.get('id_metrique')
        if not metrique_id:
            return None
        try:
            return Metrique.objects.select_related(
                'id_indicateur__id_ne__id_olt__id_enjeu',
                'id_indicateur__id_resultat_attendu',
            ).get(pk=metrique_id).get_plan_de_gestion()
        except Metrique.DoesNotExist:
            return None

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MesureCreateSerializer
        return MesureSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = self.queryset

        if user.is_super_admin():
            return queryset

        if user.is_admin_organisme() and user.id_organisme:
            return queryset.filter(
                id_metrique__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corogsite__uuid_og=user.id_organisme
            ).distinct()

        user_plan_ids = CorRolePlan.objects.filter(id_role=user).values_list('plan_de_gestion_id', flat=True)
        return queryset.filter(
            Q(id_metrique__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__in=user_plan_ids) |
            Q(id_metrique__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__sites__site__corrolesite__id_role=user) |
            Q(id_metrique__id_indicateur__id_ne__id_olt__id_enjeu__id_pg__statut='valide')
        ).distinct()

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_ajout=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['get'], url_path=r'by-metrique/(?P<metrique_id>\d+)')
    def by_metrique(self, request, metrique_id=None):
        """
        Récupérer les mesures d'une métrique.

        GET /api/plans/mesures/by-metrique/{metrique_id}/
        """
        metrique = get_object_or_404(Metrique, id_metrique=metrique_id)
        mesures = self.get_queryset().filter(id_metrique=metrique)
        return Response({
            'metrique_id': int(metrique_id),
            'metrique_nom': metrique.nom_metrique,
            'mesures': MesureSerializer(mesures, many=True).data,
            'total': mesures.count()
        })


# =============================================================================
# IndicateurMesure — saisie annuelle au niveau indicateur (override manuel
# + calcul auto exposé pour le frontend)
# =============================================================================


def _value_to_score(value, metrique) -> int | None:
    """Convertit une valeur numérique en score 1-5 via les seuils de la métrique."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    inactive = set(getattr(metrique, 'inactive_levels', None) or [])
    for i in range(1, 6):
        if i in inactive:
            continue
        inf = getattr(metrique, f'score_{i}_inf', None)
        sup = getattr(metrique, f'score_{i}_sup', None)
        if inf is None or sup is None:
            continue
        if float(inf) <= v <= float(sup):
            return i
    return None


def _compute_indicator_auto_score(indicateur: Indicateur, annee: int):
    """
    Calcule le score auto d'un indicateur pour une année donnée :
    moyenne pondérée des scores 1-5 de chaque métrique (la mesure
    retenue est la plus récente de l'année).

    Retourne {
        'score': 1-5 | None,
        'has_data': bool,                 # vrai si au moins une métrique scorée
        'per_metrique': [{ id_metrique, score, valeur }],
    }.
    """
    from datetime import date as _date
    metriques = indicateur.metriques.all()
    per_met = []
    weighted_sum = 0.0
    weight_total = 0.0
    has_any = False
    for met in metriques:
        # Mesure de l'année (la plus récente sur cette année)
        mesure = (
            met.mesures
            .filter(date_mesure__year=annee)
            .order_by('-date_mesure', '-date_ajout')
            .first()
        )
        if mesure is None:
            # Fallback : prendre la mesure la plus récente toutes années
            mesure = met.mesures.order_by('-date_mesure', '-date_ajout').first()
        score = _value_to_score(mesure.valeur, met) if mesure else None
        weight = float(met.ponderation) if met.ponderation else 1.0
        per_met.append({
            'id_metrique': met.id_metrique,
            'score': score,
            'valeur': mesure.valeur if mesure else None,
            'ponderation': weight,
        })
        if score is not None:
            has_any = True
            weighted_sum += score * weight
            weight_total += weight
    if not has_any or weight_total == 0:
        return {'score': None, 'has_data': False, 'per_metrique': per_met}
    score_avg = round(weighted_sum / weight_total)
    score_avg = max(1, min(5, score_avg))
    return {'score': score_avg, 'has_data': True, 'per_metrique': per_met}


def _can_manage_indicateur_global(user, indicateur):
    """
    #356 — Droit de surcharger l'évaluation GLOBALE d'un indicateur.
    Réservé aux gestionnaires du plan (cf. canManageLifecycle côté front) :
    super_admin / rédacteur principal, admin de l'organisme du plan, ou
    référent du plan.
    """
    if user.is_super_admin() or user.is_redacteur_principal():
        return True
    plan = indicateur.get_plan_de_gestion()
    if plan is None:
        return False
    if user.is_admin_organisme() and user.id_organisme:
        return plan.sites.filter(
            site__corogsite__uuid_og=user.id_organisme
        ).exists()
    return plan.referents.filter(pk=user.pk).exists()


class IndicateurMesureViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour la saisie annuelle au niveau Indicateur (override manuel).

    Endpoints:
    - GET    /api/plans/indicateur-mesures/            Liste (filtrable)
    - GET    /api/plans/indicateur-mesures/{id}/       Détail
    - POST   /api/plans/indicateur-mesures/            Créer
    - PATCH  /api/plans/indicateur-mesures/{id}/       Modifier
    - DELETE /api/plans/indicateur-mesures/{id}/       Supprimer
    - POST   /api/plans/indicateur-mesures/upsert/     Upsert par (indicateur, annee)
    - GET    /api/plans/indicateur-mesures/auto-score/?id_indicateur=X&annee=Y
                                                      Score auto calculé
    - GET    /api/plans/indicateur-mesures/resolved/?id_indicateur=X&annee=Y
                                                      Score effectif (override si présent, sinon auto)
    """

    queryset = IndicateurMesure.objects.select_related(
        'id_indicateur', 'id_indicateur__id_ne__id_olt__id_enjeu',
        'id_indicateur__id_resultat_attendu__id_oo',
    )
    serializer_class = IndicateurMesureSerializer
    permission_classes = [permissions.IsAuthenticated, IsReferent]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = {
        'id_indicateur': ['exact'],
        'annee': ['exact', 'gte', 'lte'],
    }
    ordering = ['-annee']

    def perform_create(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    def perform_update(self, serializer):
        serializer.save(id_utilisateur_maj=self.request.user)

    @action(detail=False, methods=['post'], url_path='upsert')
    def upsert(self, request):
        """Crée ou met à jour la saisie d'un (indicateur, année)."""
        id_ind = request.data.get('id_indicateur')
        annee = request.data.get('annee')
        if not id_ind or annee is None:
            return Response(
                {'detail': 'id_indicateur et annee sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            annee = int(annee)
        except (TypeError, ValueError):
            return Response({'detail': 'annee invalide.'}, status=status.HTTP_400_BAD_REQUEST)

        indicateur = get_object_or_404(Indicateur, pk=id_ind)
        instance, _ = IndicateurMesure.objects.get_or_create(
            id_indicateur=indicateur, annee=annee,
        )
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(id_utilisateur_maj=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], url_path='auto-score')
    def auto_score(self, request):
        """Score auto d'un indicateur pour une année donnée."""
        id_ind = request.query_params.get('id_indicateur')
        annee = request.query_params.get('annee')
        if not id_ind or annee is None:
            return Response(
                {'detail': 'id_indicateur et annee sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            annee = int(annee)
        except (TypeError, ValueError):
            return Response({'detail': 'annee invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        indicateur = get_object_or_404(Indicateur, pk=id_ind)
        result = _compute_indicator_auto_score(indicateur, annee)
        return Response({
            'id_indicateur': indicateur.id_indicateur,
            'annee': annee,
            **result,
        })

    @action(detail=False, methods=['get'], url_path='resolved')
    def resolved(self, request):
        """
        Score effectif d'un indicateur pour une année donnée :
        retourne le score_override s'il existe, sinon le score auto calculé.
        """
        id_ind = request.query_params.get('id_indicateur')
        annee = request.query_params.get('annee')
        if not id_ind or annee is None:
            return Response(
                {'detail': 'id_indicateur et annee sont requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            annee = int(annee)
        except (TypeError, ValueError):
            return Response({'detail': 'annee invalide.'}, status=status.HTTP_400_BAD_REQUEST)
        indicateur = get_object_or_404(Indicateur, pk=id_ind)
        auto = _compute_indicator_auto_score(indicateur, annee)
        override = IndicateurMesure.objects.filter(
            id_indicateur=indicateur, annee=annee, score_override__isnull=False,
        ).first()
        return Response({
            'id_indicateur': indicateur.id_indicateur,
            'annee': annee,
            # #424 — id de l'override pour permettre au front de le supprimer
            # (repassage en calcul automatique).
            'id_indicateur_mesure': override.id_indicateur_mesure if override else None,
            'score_auto': auto['score'],
            'score_override': override.score_override if override else None,
            'commentaire_override': override.commentaire_override if override else None,
            'is_overridden': override is not None,
            'score_effective': override.score_override if override else auto['score'],
            'per_metrique': auto['per_metrique'],
        })

    @staticmethod
    def _global_eval_payload(indicateur):
        """État effectif de l'évaluation globale d'un indicateur (#356)."""
        override = indicateur.get_evaluation_globale()
        return {
            'id_indicateur': indicateur.id_indicateur,
            'score_override': override.score_override if override else None,
            'commentaire': override.commentaire_override if override else None,
            'manuel': bool(override and override.score_override is not None),
        }

    @action(detail=False, methods=['get', 'post', 'delete'],
            url_path=r'global-evaluation/(?P<indicateur_id>\d+)')
    def global_evaluation(self, request, indicateur_id=None):
        """
        #356 — Surcharge manuelle de l'évaluation GLOBALE d'un indicateur.

        GET    /api/plans/indicateur-mesures/global-evaluation/{indicateur_id}/
          → surcharge effective (score_override, commentaire, manuel).
        POST   …  body { score_override?, commentaire_override? }
          → pose/met à jour. Les deux sont optionnels : un commentaire seul est
            possible (n'active pas le mode manuel). Le score calculé ne change pas ;
            score_override ne fait que changer l'icône d'interprétation affichée.
        DELETE …  → retire la surcharge (retour au calcul automatique, commentaire effacé).

        Écritures réservées aux gestionnaires du plan. Non verrouillé brouillon
        (donnée de suivi, éditable après validation).
        """
        indicateur = get_object_or_404(Indicateur, pk=indicateur_id)

        if request.method == 'GET':
            return Response(self._global_eval_payload(indicateur))

        if not _can_manage_indicateur_global(request.user, indicateur):
            return Response(
                {'detail': "Action réservée aux gestionnaires du plan."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if request.method == 'DELETE':
            IndicateurRealisationGlobale.objects.filter(id_indicateur=indicateur).delete()
            return Response(self._global_eval_payload(indicateur))

        # POST — score et/ou commentaire (au moins l'un des deux requis).
        score = request.data.get('score_override')
        commentaire = request.data.get('commentaire_override')
        if score in (None, '') and commentaire is None:
            return Response(
                {'detail': 'score_override ou commentaire_override est requis.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if score in (None, ''):
            score_value = None
        else:
            try:
                score_value = int(score)
            except (TypeError, ValueError):
                return Response({'detail': 'score_override invalide.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if not (1 <= score_value <= 5):
                return Response({'detail': 'score_override doit être entre 1 et 5.'},
                                status=status.HTTP_400_BAD_REQUEST)
        IndicateurRealisationGlobale.objects.update_or_create(
            id_indicateur=indicateur,
            defaults={
                'score_override': score_value,
                'commentaire_override': commentaire or '',
                'id_utilisateur_maj': request.user,
            },
        )
        return Response(self._global_eval_payload(indicateur))
