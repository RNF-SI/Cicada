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

    message = "Seuls les référents de ce plan et ses gestionnaires peuvent le modifier."

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        if not request.user.is_referent():
            return False
        return _peut_ecrire_les_plans_vises(request, view)

    def has_object_permission(self, request, view, obj):
        return _peut_ecrire_l_objet(request, view, obj)


def _predicat(view):
    """Contenu du plan : ``user_can_write_plan``. Données de suivi (mesures,
    réalisations — vues marquées ``ecriture_de_suivi``) : périmètre de saisie
    des suivis, qui inclut les référents validés d'un site (#610, #740)."""
    from .access import user_can_access_suivi, user_can_write_plan

    if getattr(view, 'ecriture_de_suivi', False):
        return user_can_access_suivi
    return user_can_write_plan


def _peut_ecrire_les_plans_vises(request, view):
    """Chaque plan désigné par les données reçues doit être modifiable par l'utilisateur."""
    from .ecriture import modele_de_la_vue, plans_vises

    predicat = _predicat(view)
    return all(
        predicat(request.user, plan)
        for plan in plans_vises(modele_de_la_vue(view), request.data)
    )


def _peut_ecrire_l_objet(request, view, obj):
    """Le plan de l'objet modifié doit être modifiable par l'utilisateur."""
    from .ecriture import plan_de

    if request.method in SAFE_METHODS:
        return True
    if getattr(view, 'action', None) in PeutEcrireLePlan.ACTIONS_SANS_ECRITURE:
        return True
    plan = plan_de(obj)
    return plan is None or _predicat(view)(request.user, plan)


class PeutEcrireLePlan(BasePermission):
    """
    Écriture réservée à qui peut écrire dans **ce** plan (``user_can_write_plan``) :
    celui de l'objet modifié et ceux que désignent les données reçues.

    Pour les vues qui ne passent pas par :class:`IsReferentOrReadOnly` (plan,
    suivis-inventaires, documents, fonctions) — celle-ci n'exige en plus aucun
    rôle global : la création d'un plan reste régie par :class:`CanCreatePlan`.
    """

    message = IsReferentOrReadOnly.message

    #: Actions en POST qui n'écrivent rien sur le plan (le client transmet le
    #: tableau à mettre en forme, #638) et portent leur propre contrôle.
    ACTIONS_SANS_ECRITURE = frozenset({
        'export_tableau_de_bord_xlsx', 'export_suivi_actions_xlsx',
    })

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _peut_ecrire_les_plans_vises(request, view)

    def has_object_permission(self, request, view, obj):
        return _peut_ecrire_l_objet(request, view, obj)


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
        "assign_redacteur_externe",
        # Exports — POST seulement parce que le client transmet le tableau
        # affiché à mettre en forme (#638) : rien n'est écrit sur le plan, un
        # plan validé doit rester exportable.
        "export_tableau_de_bord_xlsx",
        "export_suivi_actions_xlsx",
        # #751 — type d'une action à actualiser après un passage de
        # référentiel : la vue n'autorise hors brouillon que ce cas.
        "actualiser_type",
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
        # Le plan d'arrivée aussi : déplacer un objet (``id_pg``, ``id_olt``…)
        # ou le relier (``pression_ids``…) vers un plan validé le modifierait.
        from .ecriture import modele_de_la_vue, plans_vises
        return all(
            plan.statut in self.EDITABLE_STATUSES
            for plan in plans_vises(modele_de_la_vue(view), request.data)
        )

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


class CanCreatePlan(BasePermission):
    """
    Création d'un plan de gestion (``POST /api/plans/plans/``).

    - Admin organisme et au-dessus (rédacteur principal, super admin) : sur
      n'importe quel site.
    - Tout autre utilisateur **rattaché à un site** (``CorRoleSite``, référent
      ou simple membre) : sur ce(s) site(s) uniquement. Tous les sites du plan
      doivent être des sites auxquels il est rattaché. Être référent d'un plan
      ne suffit pas : le créateur devenant référent de son plan, ce statut
      ouvrirait sinon tous les sites dès le premier plan créé.
    - Rédacteur externe (#700) : ses sites n'ouvrent rien, il ne crée pas de
      plan (il demande l'accès à un plan existant).

    Un payload sans site est laissé passer pour un utilisateur rattaché :
    le serializer renvoie alors le 400 « Au moins un site est requis ».
    """

    message = (
        "Vous ne pouvez créer un plan de gestion que sur un site auquel vous "
        "êtes rattaché."
    )

    def has_permission(self, request, view):
        from apps.users.models import CorRoleSite

        user = request.user
        if not (user and user.is_authenticated):
            return False
        if user.is_admin_organisme():
            return True
        if user.is_redacteur():
            return False

        liens = CorRoleSite.objects.filter(id_role=user)
        data = request.data
        raw_ids = data.getlist('sites_ids') if hasattr(data, 'getlist') else data.get('sites_ids')
        if not raw_ids:
            return liens.exists()
        try:
            site_ids = {int(site_id) for site_id in raw_ids}
        except (TypeError, ValueError):
            return False
        return liens.filter(id_site__in=site_ids).values('id_site').distinct().count() == len(site_ids)


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


class PeutGererLeSite(BasePermission):
    """Écriture d'un objet rattaché à un **site** (responsabilités) : réservée à
    qui gère ce site (``Role.can_manage_site`` ; le rédacteur principal a un
    accès global aux sites) — celui de l'objet et celui désigné par ``id_site``.
    Être référent d'autre chose ne suffit pas."""

    message = "Seuls les référents de ce site et ses gestionnaires peuvent le modifier."

    @staticmethod
    def _gere(user, site):
        return site is not None and (user.is_redacteur_principal() or user.can_manage_site(site))

    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.method in SAFE_METHODS:
            return True
        site_id = request.data.get('id_site') if hasattr(request.data, 'get') else None
        if site_id in (None, ''):
            return True
        from apps.users.models import Site
        try:
            site = Site.objects.filter(pk=int(site_id)).first()
        except (TypeError, ValueError):
            return False
        return self._gere(request.user, site)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return self._gere(request.user, getattr(obj, 'id_site', None))
