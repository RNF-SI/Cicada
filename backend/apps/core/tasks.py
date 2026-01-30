"""
Taches Celery pour le module core.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='core.cleanup_old_error_logs')
def cleanup_old_error_logs(days: int = 90, acknowledged_days: int = 30) -> dict:
    """
    Supprime les anciens logs d'erreur.

    - Logs acquittes de plus de `acknowledged_days` jours (defaut: 30)
    - Logs non acquittes de plus de `days` jours (defaut: 90)

    Args:
        days: Nombre de jours avant suppression des logs non acquittes
        acknowledged_days: Nombre de jours avant suppression des logs acquittes

    Returns:
        dict: Statistiques de suppression
    """
    from apps.core.models import ErrorLog

    now = timezone.now()
    stats = {
        'acknowledged_deleted': 0,
        'unacknowledged_deleted': 0,
        'total_deleted': 0,
    }

    # Supprimer les logs acquittes anciens
    acknowledged_cutoff = now - timedelta(days=acknowledged_days)
    acknowledged_deleted, _ = ErrorLog.objects.filter(
        acknowledged=True,
        created_at__lt=acknowledged_cutoff
    ).delete()
    stats['acknowledged_deleted'] = acknowledged_deleted

    # Supprimer les logs non acquittes tres anciens
    unacknowledged_cutoff = now - timedelta(days=days)
    unacknowledged_deleted, _ = ErrorLog.objects.filter(
        acknowledged=False,
        created_at__lt=unacknowledged_cutoff
    ).delete()
    stats['unacknowledged_deleted'] = unacknowledged_deleted

    stats['total_deleted'] = acknowledged_deleted + unacknowledged_deleted

    if stats['total_deleted'] > 0:
        logger.info(
            f"Cleanup error logs: {stats['acknowledged_deleted']} acknowledged, "
            f"{stats['unacknowledged_deleted']} unacknowledged deleted"
        )

    return stats


@shared_task(name='core.count_error_logs')
def count_error_logs() -> dict:
    """
    Compte les logs d'erreur par niveau et statut.
    Utile pour le monitoring.

    Returns:
        dict: Statistiques des logs
    """
    from django.db.models import Count
    from apps.core.models import ErrorLog

    total = ErrorLog.objects.count()
    unacknowledged = ErrorLog.objects.filter(acknowledged=False).count()

    by_level = dict(
        ErrorLog.objects
        .values('level')
        .annotate(count=Count('id'))
        .values_list('level', 'count')
    )

    return {
        'total': total,
        'unacknowledged': unacknowledged,
        'by_level': by_level,
    }
