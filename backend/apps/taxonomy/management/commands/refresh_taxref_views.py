"""
Commande pour rafraîchir les vues matérialisées TaxRef.

Usage:
    python manage.py refresh_taxref_views
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Rafraîchit les vues matérialisées TaxRef (autocomplete)'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            '=== RAFRAÎCHISSEMENT DES VUES MATÉRIALISÉES TAXREF ==='
        ))

        with connection.cursor() as cursor:
            self.stdout.write('  Rafraîchissement de vm_taxref_list_forautocomplete...')
            cursor.execute(
                'REFRESH MATERIALIZED VIEW CONCURRENTLY '
                'taxonomie.vm_taxref_list_forautocomplete'
            )

        self.stdout.write(self.style.SUCCESS(
            'Vues matérialisées rafraîchies avec succès!'
        ))
