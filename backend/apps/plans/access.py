"""
Périmètre de LECTURE d'un plan de gestion et de son contenu (#610).

Règle métier : un utilisateur *lié* à un plan de gestion doit pouvoir consulter
l'intégralité de son contenu en lecture seule, même s'il n'est pas « référent ».
Est considéré comme lié :

- membre ou référent du plan (``CorRolePlan``) ;
- référent du plan via le M2M ``PlanGestion.referents`` ;
- utilisateur rattaché à un des sites du plan (``CorRoleSite``) ;
- utilisateur d'un organisme rédacteur du plan ;
- utilisateur d'un organisme gestionnaire d'un des sites du plan.

Ce périmètre est **le même** que celui de ``PlanGestionViewSet.get_queryset()`` :
voir le plan implique voir son contenu. Les helpers ci-dessous factorisent cette
logique, auparavant dupliquée dans une vingtaine de ``get_queryset()`` avec des
variantes divergentes (certaines ouvraient tout plan ``statut='valide'`` à
n'importe quel compte, d'autres ignoraient les membres ou les référents).

L'écriture reste gouvernée par ``IsReferent`` + ``CanModifyOnlyDraftPlan``.
"""
from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from .models import CorRolePlan, PlanGestion


# Chemins ORM menant d'un Indicateur à son plan : via le niveau d'exigence
# (indicateur d'état) ou via le résultat attendu (indicateur de réponse),
# lui-même rattaché à un OO par ses pressions ou directement par un enjeu (#337).
INDICATEUR_TO_PG_PATHS = (
    'id_ne__id_olt__id_enjeu__id_pg',
    'id_resultat_attendu__id_oo__pressions__id_facteur_influence__enjeux__id_pg',
    'id_resultat_attendu__id_oo__id_enjeu__id_pg',
)


def prefix_paths(prefix, paths):
    """Préfixe une série de chemins ORM (``'id_indicateur'`` + ``'id_ne__…'``)."""
    return tuple(f'{prefix}__{path}' for path in paths)


# Chemins ORM menant d'une Operation à son plan : par son suivi/inventaire en
# priorité, sinon par son indicateur ou par une de ses métriques.
OPERATION_TO_PG_PATHS = (
    prefix_paths('metriques__id_indicateur', INDICATEUR_TO_PG_PATHS)
    + prefix_paths('id_indicateur', INDICATEUR_TO_PG_PATHS)
    + ('id_suivi__id_pg',)
)


def has_global_plan_access(user) -> bool:
    """Vrai pour les rôles qui voient tous les plans (super admin, rédacteur principal)."""
    return user.is_super_admin() or user.is_redacteur_principal()


def plan_scope_q(user) -> Q:
    """
    Construit le ``Q`` de filtrage des ``PlanGestion`` accessibles à ``user``.

    Ne doit pas être appelé pour un utilisateur à accès global :
    cf. :func:`has_global_plan_access`.
    """
    organisme = user.id_organisme if user.id_organisme_id else None

    # Admin organisme : les plans de ses sites et ceux dont son organisme est rédacteur.
    if user.is_admin_organisme() and organisme is not None:
        return (
            Q(sites__site__corogsite__uuid_og=organisme) |
            Q(organismes_redacteurs__uuid_og=organisme)
        )

    scope = (
        Q(pk__in=CorRolePlan.objects.filter(id_role=user).values('plan_de_gestion_id')) |
        Q(referents=user) |
        Q(sites__site__corrolesite__id_role=user)
    )
    if organisme is not None:
        scope |= Q(organismes_redacteurs__uuid_og=organisme)
        scope |= Q(sites__site__corogsite__uuid_og=organisme)
    return scope


def accessible_plan_ids(user):
    """
    Queryset (paresseux) des IDs de plans accessibles à ``user``, destiné à être
    utilisé comme sous-requête dans un ``__in``. Retourne ``None`` pour un
    utilisateur à accès global (aucun filtrage nécessaire).
    """
    if has_global_plan_access(user):
        return None
    return PlanGestion.objects.filter(plan_scope_q(user)).values('id_pg')


def scope_by_plan(queryset, user, paths='', extra=None):
    """
    Restreint ``queryset`` aux objets rattachés à un plan accessible à ``user``.

    :param paths: chemin ORM (ou tuple de chemins) menant de l'objet filtré
        jusqu'au ``PlanGestion``. Chaîne vide pour filtrer ``PlanGestion``
        lui-même. Plusieurs chemins sont combinés en OR (une entité peut être
        rattachée au plan par plusieurs branches de l'arborescence).
    :param extra: ``Q`` additionnel OR-é au périmètre (ex. le créateur d'une
        opération orpheline, qui doit continuer à la voir).
    """
    plan_ids = accessible_plan_ids(user)
    if plan_ids is None:
        return queryset

    if isinstance(paths, str):
        paths = (paths,)

    scope = Q()
    for path in paths:
        scope |= Q(**{f'{path}__in' if path else 'pk__in': plan_ids})
    if extra is not None:
        scope |= extra
    return queryset.filter(scope).distinct()


def user_can_access_plan(user, plan) -> bool:
    """Vrai si ``user`` a accès (au moins en lecture) au plan donné."""
    if has_global_plan_access(user):
        return True
    return PlanGestion.objects.filter(pk=plan.pk).filter(plan_scope_q(user)).exists()


def user_manages_plan(user, plan) -> bool:
    """Vrai si ``user`` a déjà la main sur ce plan **par son rôle** (#657).

    C'est-à-dire : super admin, rédacteur principal, ou admin d'un organisme
    gestionnaire d'un des sites du plan / rédacteur du plan. Ces comptes ne
    demandent pas l'accès à un plan de leur périmètre — ils l'ont déjà, et la
    demande n'aurait aucun destinataire pertinent.

    À distinguer de :func:`user_can_access_plan`, qui est vrai pour tout compte
    simplement *lié* au plan (membre, référent, utilisateur d'un site) : ceux-là
    peuvent légitimement demander à être rattachés au plan.
    """
    if has_global_plan_access(user):
        return True
    if not user.is_admin_organisme() or not user.id_organisme_id:
        return False
    organisme = user.id_organisme
    return PlanGestion.objects.filter(pk=plan.pk).filter(
        Q(sites__site__corogsite__uuid_og=organisme) |
        Q(organismes_redacteurs__uuid_og=organisme)
    ).exists()


def assert_plan_access(user, plan):
    """
    Lève une 403 si ``user`` n'a pas accès au plan.

    À utiliser dans les ``@action`` prenant un ``plan_id`` et qui interrogent
    les modèles directement (agrégations du bilan…) : celles-là ne passent pas
    par ``get_queryset()`` et ne sont donc pas bornées par le périmètre.
    """
    if not user_can_access_plan(user, plan):
        raise PermissionDenied("Vous n'avez pas accès à ce plan de gestion.")


# ---------------------------------------------------------------------------
# Accès aux SUIVIS (bilan, suivi des actions, tableau de bord) — #610
#
# Contrairement au contenu du plan (arborescence, fiches action prévisionnelles),
# les suivis ne sont PAS ouverts à tout utilisateur simplement lié : ils sont
# réservés aux référents (du plan ou d'un de ses sites) et aux gestionnaires
# (admin de l'organisme du plan, super admin, rédacteur principal). Un simple
# membre ou un utilisateur lié par organisme/site n'y accède pas.
# ---------------------------------------------------------------------------

def suivi_scope_q(user) -> Q:
    """``Q`` des plans dont ``user`` peut voir les suivis (#610).

    Ne doit pas être appelé pour un utilisateur à accès global
    (cf. :func:`has_global_plan_access`)."""
    scope = (
        Q(referents=user) |
        Q(sites__site__corrolesite__id_role=user,
          sites__site__corrolesite__referent=True,
          sites__site__corrolesite__referent_valid=True)
    )
    if user.is_admin_organisme() and user.id_organisme_id:
        organisme = user.id_organisme
        scope |= Q(organismes_redacteurs__uuid_og=organisme)
        scope |= Q(sites__site__corogsite__uuid_og=organisme)
    return scope


def suivi_accessible_plan_ids(user):
    """IDs des plans dont ``user`` peut voir les suivis (``None`` si accès global)."""
    if has_global_plan_access(user):
        return None
    return PlanGestion.objects.filter(suivi_scope_q(user)).values('id_pg')


def scope_suivi_by_plan(queryset, user, paths='', extra=None):
    """Comme :func:`scope_by_plan`, mais borné au périmètre SUIVI (#610)."""
    plan_ids = suivi_accessible_plan_ids(user)
    if plan_ids is None:
        return queryset

    if isinstance(paths, str):
        paths = (paths,)

    scope = Q()
    for path in paths:
        scope |= Q(**{f'{path}__in' if path else 'pk__in': plan_ids})
    if extra is not None:
        scope |= extra
    return queryset.filter(scope).distinct()


def user_can_access_suivi(user, plan) -> bool:
    """Vrai si ``user`` peut voir les suivis du plan (#610)."""
    if has_global_plan_access(user):
        return True
    return PlanGestion.objects.filter(pk=plan.pk).filter(suivi_scope_q(user)).exists()


def assert_suivi_access(user, plan):
    """Lève une 403 si ``user`` n'a pas accès aux suivis du plan (#610)."""
    if not user_can_access_suivi(user, plan):
        raise PermissionDenied(
            "Les suivis de ce plan sont réservés à ses référents et gestionnaires."
        )
