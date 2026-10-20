"""
Organisme d'un rédacteur externe rattaché à un plan (#714).

Un rédacteur externe (``role_level='redacteur'``, #700) rattaché à un plan
— membre ou référent — rend son organisme **organisme rédacteur** du plan.
Ce lien n'est qu'une mention : il n'ouvre le plan à aucun autre utilisateur de
cet organisme (cf. :mod:`apps.plans.access`).
"""
from .models import CorRedacteurPlan, CorRolePlan


def rattacher_organisme_redacteur(plan, user):
    """Inscrit l'organisme de ``user`` parmi les rédacteurs du plan s'il est rédacteur externe.

    #739 — il s'ajoute EN DESSOUS du rédacteur principal, qui reste
    l'organisme gestionnaire : un bureau d'étude missionné ne devient pas
    rédacteur principal du plan. Si le plan n'en a pas encore, on désigne
    l'organisme gestionnaire de son site principal.
    """
    if not user.is_redacteur() or not user.id_organisme_id:
        return
    if not CorRedacteurPlan.objects.filter(plan_de_gestion=plan, principal=True).exists():
        gestionnaire = organisme_gestionnaire_principal(plan)
        if gestionnaire is not None and gestionnaire.pk != user.id_organisme_id:
            CorRedacteurPlan.objects.update_or_create(
                plan_de_gestion=plan, uuid_og=gestionnaire, defaults={'principal': True})
    CorRedacteurPlan.objects.get_or_create(plan_de_gestion=plan, uuid_og=user.id_organisme)


def organisme_gestionnaire_principal(plan):
    """Organisme gestionnaire du site principal du plan (gestionnaire principal d'abord)."""
    from apps.users.models import CorOgSite

    site = plan.get_principal_site()
    if site is None:
        return None
    lien = (CorOgSite.objects.filter(id_site=site).select_related('uuid_og')
            .order_by('-principal', 'pk').first())
    return lien.uuid_og if lien else None


def enregistrer_organismes_redacteurs(plan, organisme_ids, principal_id=None, principal_fourni=False):
    """#739 — remplace les organismes rédacteurs du plan par ceux du formulaire.

    ``principal_id`` désigne le rédacteur principal ; s'il n'est pas fourni,
    c'est le premier de la liste (création). Aucun organisme n'est réinscrit
    d'office : celui d'un rédacteur externe se retire comme les autres, sans
    que le rédacteur perde son accès au plan.
    """
    from apps.users.models import BibOrganismes

    ids = list(dict.fromkeys(organisme_ids or []))
    if principal_fourni:
        if principal_id is not None and principal_id not in ids:
            ids.insert(0, principal_id)
    else:
        principal_id = ids[0] if ids else None
    organismes = {o.id_organisme: o for o in BibOrganismes.objects.filter(id_organisme__in=ids)}

    CorRedacteurPlan.objects.filter(plan_de_gestion=plan).delete()
    for org_id in ids:
        if org_id in organismes:
            CorRedacteurPlan.objects.create(
                plan_de_gestion=plan, uuid_og=organismes[org_id], principal=org_id == principal_id)


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
