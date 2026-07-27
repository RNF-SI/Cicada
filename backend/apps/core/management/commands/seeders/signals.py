"""
Gestion centralisee des signaux pour les seeders.

Ce module fournit un context manager pour desactiver/reactiver
les signaux Django pendant la creation ou suppression des donnees de test.
"""
from contextlib import contextmanager
from typing import List, Tuple, Callable, Any

from django.db.models.signals import post_save, post_delete, pre_save, pre_delete, m2m_changed


def _get_signal_registry() -> List[Tuple[Any, Callable, Any]]:
    """
    Retourne la liste des signaux a desactiver.

    Returns:
        Liste de tuples (signal, handler, sender)
    """
    # Import des modeles et handlers de signaux (lazy)
    from apps.users.models import Role, BibOrganismes, CorRoleSite, Site
    from apps.notifications.models import ValidationRequest
    from apps.plans.models import PlanGestion
    from apps.notifications import signals as notif_signals
    from apps.users import signals as user_signals
    from apps.core import activity_signals

    return [
        # =============================================
        # Signaux de apps.notifications.signals
        # =============================================
        (post_save, notif_signals.notify_user_site_association, CorRoleSite),
        # #446 — check_site_orphaned_on_user_removal retiré (doublon) ; la
        # détection est faite par users.signals.check_site_orphaned_after_user_removed.
        (post_delete, notif_signals.notify_user_removed_from_site, CorRoleSite),
        (pre_save, notif_signals.track_user_deactivation, Role),
        (post_save, notif_signals.notify_user_deactivation, Role),
        (post_save, notif_signals.notify_new_validation_request, ValidationRequest),
        (post_save, notif_signals.handle_validation_result, ValidationRequest),
        (pre_save, notif_signals.track_validation_status, ValidationRequest),

        # =============================================
        # Signaux de apps.users.signals
        # =============================================
        (pre_delete, user_signals.notify_users_before_organisme_delete, BibOrganismes),
        (pre_delete, user_signals.notify_users_before_site_delete, Site),
        (post_save, user_signals.handle_user_deactivation, Role),
        (post_save, user_signals.check_organisme_admin_after_role_change, Role),
        (post_delete, user_signals.check_organisme_admin_after_role_delete, Role),
        (post_delete, user_signals.check_site_orphaned_after_user_removed, CorRoleSite),
        (post_save, user_signals.check_sites_after_user_deactivation, Role),

        # =============================================
        # Signaux de apps.core.activity_signals
        # =============================================
        # Sites
        (pre_save, activity_signals.track_site_previous_values, Site),
        (post_save, activity_signals.log_site_activity_on_save, Site),
        (pre_delete, activity_signals.log_site_activity_on_delete, Site),

        # Plans
        (pre_save, activity_signals.track_plan_previous_values, PlanGestion),
        (post_save, activity_signals.log_plan_activity_on_save, PlanGestion),
        (pre_delete, activity_signals.log_plan_activity_on_delete, PlanGestion),

        # Membres (CorRoleSite)
        (pre_save, activity_signals.track_cor_role_site_previous_values, CorRoleSite),
        (post_save, activity_signals.log_member_activity_on_save, CorRoleSite),
        (post_delete, activity_signals.log_member_activity_on_delete, CorRoleSite),

        # Referents de plan (M2M)
        (m2m_changed, activity_signals.log_plan_referent_activity, PlanGestion.referents.through),

        # Utilisateurs
        (pre_save, activity_signals.track_user_previous_values, Role),
        (post_save, activity_signals.log_user_activity_on_save, Role),

        # Organismes
        (pre_save, activity_signals.track_organisme_previous_values, BibOrganismes),
        (post_save, activity_signals.log_organisme_activity_on_save, BibOrganismes),
        (pre_delete, activity_signals.log_organisme_activity_on_delete, BibOrganismes),

        # Validations
        (pre_save, activity_signals.track_validation_previous_status, ValidationRequest),
        (post_save, activity_signals.log_validation_activity_on_save, ValidationRequest),

        # Note : les signaux de apps.geo (rattachement administratif des sites)
        # ne sont volontairement PAS désactivés. Ils ne produisent ni
        # notification ni log d'activité, et les sites de test ont besoin de
        # leur rattachement département/région pour que les filtres de
        # l'exploration des données soient testables.
    ]


@contextmanager
def signals_disabled(stdout=None):
    """
    Context manager pour desactiver tous les signaux pendant l'execution.

    Usage:
        with signals_disabled(stdout):
            # Les signaux sont desactives ici
            do_something()
        # Les signaux sont reactives ici

    Args:
        stdout: OutputWrapper optionnel pour afficher les messages de log
    """
    signal_registry = _get_signal_registry()

    # Deconnecter tous les signaux
    for signal, handler, sender in signal_registry:
        signal.disconnect(handler, sender=sender)

    if stdout:
        stdout.write('  Signaux de notifications et activite desactives')

    try:
        yield
    finally:
        # Reconnecter tous les signaux
        for signal, handler, sender in signal_registry:
            signal.connect(handler, sender=sender)

        if stdout:
            stdout.write('  Signaux de notifications et activite reactives')


def disconnect_all_signals(stdout=None) -> None:
    """
    Deconnecte tous les signaux.

    Utile pour les tests ou les operations de maintenance.

    Args:
        stdout: OutputWrapper optionnel pour afficher les messages de log
    """
    for signal, handler, sender in _get_signal_registry():
        signal.disconnect(handler, sender=sender)

    if stdout:
        stdout.write('  Signaux de notifications et activite desactives')


def reconnect_all_signals(stdout=None) -> None:
    """
    Reconnecte tous les signaux.

    Args:
        stdout: OutputWrapper optionnel pour afficher les messages de log
    """
    for signal, handler, sender in _get_signal_registry():
        signal.connect(handler, sender=sender)

    if stdout:
        stdout.write('  Signaux de notifications et activite reactives')
