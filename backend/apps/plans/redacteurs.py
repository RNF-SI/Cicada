"""
Organisme d'un rédacteur externe rattaché à un plan (#714).

Un rédacteur externe (``role_level='redacteur'``, #700) rattaché à un plan
— membre ou référent — rend son organisme **organisme rédacteur** du plan.
Ce lien n'est qu'une mention : il n'ouvre le plan à aucun autre utilisateur de
cet organisme (cf. :mod:`apps.plans.access`).
"""
from .models import CorRedacteurPlan, CorRolePlan


def rattacher_organisme_redacteur(plan, user):
    """Inscrit l'organisme de ``user`` parmi les rédacteurs du plan s'il est rédacteur externe."""
    if not user.is_redacteur() or not user.id_organisme_id:
        return
    CorRedacteurPlan.objects.get_or_create(plan_de_gestion=plan, uuid_og=user.id_organisme)


def organismes_redacteurs_externes(plan):
    """Organismes des rédacteurs externes rattachés au plan (membres ou référents)."""
    from django.db.models import Q

    from apps.users.models import BibOrganismes, Role

    redacteurs = Role.objects.filter(role_level='redacteur').filter(
        Q(plan_associations__plan_de_gestion=plan) | Q(plans_referents=plan)
    )
    return BibOrganismes.objects.filter(
        uuid_organisme__in=redacteurs.values('id_organisme')
    ).distinct()
