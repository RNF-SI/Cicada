"""
Tâches Celery pour l'import en masse de sites.
"""
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def bulk_import_sites_task(self, import_job_id):
    """
    Importe des sites en masse de façon asynchrone.
    Met à jour le BulkImportJob au fur et à mesure.
    """
    from .models import BulkImportJob
    from .services_bulk_import import BulkSiteImportService

    try:
        job = BulkImportJob.objects.get(id=import_job_id)
    except BulkImportJob.DoesNotExist:
        logger.error(f"BulkImportJob {import_job_id} not found")
        return

    job.status = 'processing'
    job.save(update_fields=['status'])

    try:
        sites = job.import_data.get('sites', [])
        selected_indices = job.import_data.get('selected_indices', [])

        result = BulkSiteImportService.import_sites(
            sites, job.user, selected_indices
        )

        job.status = 'completed'
        job.processed_sites = result['created'] + result['failed'] + result['validation_pending']
        job.created_sites = result['created']
        job.failed_sites = result['failed']
        job.validation_pending_sites = result['validation_pending']
        job.result_data = result
        job.completed_at = timezone.now()
        job.save()

        logger.info(
            f"BulkImportJob {import_job_id} completed: "
            f"{result['created']} created, {result['failed']} failed, "
            f"{result['validation_pending']} pending"
        )

    except Exception as exc:
        logger.error(f"BulkImportJob {import_job_id} failed: {exc}")
        job.status = 'failed'
        job.result_data = {'error': str(exc)}
        job.completed_at = timezone.now()
        job.save(update_fields=['status', 'result_data', 'completed_at'])

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
