"""Tâches planifiées de l'authentification."""
from celery import shared_task
from django.core.management import call_command


@shared_task(name='authentication.purger_jetons_expires')
def purger_jetons_expires():
    """Retire de la liste de révocation les jetons déjà expirés."""
    call_command('flushexpiredtokens')
