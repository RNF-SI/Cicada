"""
Permissions personnalisées pour l'application plans.

Implémente la règle métier #248 : les modifications (POST/PUT/PATCH/DELETE)
d'un plan de gestion et de toutes ses entités enfants ne sont autorisées que
lorsque le plan est en statut `draft`. Pour modifier un plan validé/archivé,
l'utilisateur doit explicitement passer le plan en brouillon ou créer une
nouvelle version (duplicate / create_evaluation).
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import PlanGestion


class IsReferentOrReadOnly(BasePermission):
    """
    #610 — Lecture ouverte à tout utilisateur authentifié, écriture réservée
    aux référents (au sens `Role.is_referent()`).

    Le périmètre réel de lecture est borné par les `get_queryset()` des
    ViewSets (cf. `apps.plans.access`) : un utilisateur ne voit que le contenu
    des plans auxquels il est lié. Exiger `IsReferent` au niveau de la vue
    bloquait à tort en 403 les non-référents pourtant liés au plan (membre
    `CorRolePlan`, utilisateur rattaché à un site du plan…), qui doivent
    pouvoir consulter le plan en lecture seule.

    Généralisation du correctif #372 appliqué à `CorPgFichierViewSet`.
    """

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_referent()


class CanModifyOnlyDraftPlan(BasePermission):
    """
    Bloque les écritures sur le plan et ses entités enfants quand le plan
    associé n'est pas en statut `draft`. Les méthodes SAFE et certaines
    actions de cycle de vie (`change_status`, `duplicate`, `create_evaluation`,
    associations sites/référents/membres) restent ouvertes.

    Pour fonctionner :
    - Les modèles concernés doivent exposer `get_plan_de_gestion()` qui
      retourne l'instance `PlanGestion` à laquelle ils sont rattachés
      (ou `None` quand le rattachement ne peut pas être déterminé).
    - Les ViewSets qui créent des objets liés à un plan peuvent exposer
      `get_plan_for_payload(data)` pour permettre le check sur POST avant
      la sérialisation. Sans cela, le contrôle a lieu dans `perform_create`
      via le mixin `DraftPlanRequiredMixin`.
    """

    message = (
        "Le plan de gestion associé n'est pas en brouillon. "
        "Pour modifier ce plan, repassez-le en brouillon ou créez une nouvelle version."
    )

    # Statuts qui autorisent les modifications. Seul `draft` est éditable :
    # l'extension de durée (#250) est un attribut orthogonal au statut
    # (`annees_extension`), pas un statut qui débloquerait l'édition.
    EDITABLE_STATUSES = frozenset({"draft"})

    EXEMPT_ACTIONS = frozenset({
        # Cycle de vie / versions
        "change_status",
        "duplicate",
        "create_evaluation",
        "create_next_rang",
        "extend_duration",
        "remove_extension",
        "start_revision",
        "end_revision",
        # Associations plan ↔ site
        "assign_site",
        "remove_site",
        "replace_site",
        # Associations plan ↔ utilisateur
        "assign_referent",
        "remove_referent",
        "assign_member",
        "remove_member",
        # Lecture / consultations
        "by_plan",
        "by_ne",
        "by_oo",
        "by_resultat",
        "by_enjeu",
        "by_indicateur",
        "by_metrique",
    })

    # ──────────────────────────────────────────────────────────────────
    # Permission framework
    # ──────────────────────────────────────────────────────────────────

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if self._is_exempt_action(view):
            return True
        if request.method == "POST":
            plan = self._resolve_plan_from_payload(request, view)
            if plan is not None and plan.statut not in self.EDITABLE_STATUSES:
                return False
        return True

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if self._is_exempt_action(view):
            return True
        plan = self._resolve_plan_from_object(obj)
        return plan is None or plan.statut in self.EDITABLE_STATUSES

    # ──────────────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────────────

    @classmethod
    def _is_exempt_action(cls, view) -> bool:
        return getattr(view, "action", None) in cls.EXEMPT_ACTIONS

    @staticmethod
    def _resolve_plan_from_object(obj):
        """Tente d'extraire le plan attaché à l'objet."""
        if isinstance(obj, PlanGestion):
            return obj
        getter = getattr(obj, "get_plan_de_gestion", None)
        if callable(getter):
            try:
                return getter()
            except Exception:
                return None
        return None

    @staticmethod
    def _resolve_plan_from_payload(request, view):
        """Tente d'extraire le plan associé à la création depuis le payload."""
        getter = getattr(view, "get_plan_for_payload", None)
        if callable(getter):
            try:
                return getter(request.data)
            except Exception:
                return None
        return None


class DraftPlanRequiredMixin:
    """
    Filet de sécurité côté `perform_create / perform_update / perform_destroy`
    pour les ViewSets qui ne peuvent pas exposer `get_plan_for_payload` en amont.

    À utiliser conjointement avec `CanModifyOnlyDraftPlan` dans `permission_classes`.
    """

    def _check_plan_is_draft(self, plan):
        if plan is not None and plan.statut not in CanModifyOnlyDraftPlan.EDITABLE_STATUSES:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied(
                "Le plan de gestion associé n'est pas en brouillon. "
                "Pour modifier ce plan, repassez-le en brouillon ou créez une nouvelle version."
            )

    def perform_create(self, serializer):
        plan = self._plan_for_serializer(serializer)
        self._check_plan_is_draft(plan)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        plan = self._plan_for_serializer(serializer)
        self._check_plan_is_draft(plan)
        super().perform_update(serializer)

    def perform_destroy(self, instance):
        plan = CanModifyOnlyDraftPlan._resolve_plan_from_object(instance)
        self._check_plan_is_draft(plan)
        super().perform_destroy(instance)

    def _plan_for_serializer(self, serializer):
        """
        Retourne le plan associé à ce serializer (instance pour update,
        données validées pour create). Les ViewSets peuvent l'overrider.
        """
        instance = getattr(serializer, "instance", None)
        if instance is not None:
            return CanModifyOnlyDraftPlan._resolve_plan_from_object(instance)
        return None
