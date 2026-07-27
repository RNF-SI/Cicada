"""
Recalcule le rattachement administratif (département / région) des sites.

À lancer après un import de sites en masse, une correction de géométries, ou
une mise à jour du référentiel `ref_geo`. Le recalcul est idempotent et ne
touche pas aux rattachements saisis manuellement (`source='manual'`).

Usage :
    python manage.py refresh_site_areas               # tous les sites
    python manage.py refresh_site_areas --site 12     # un site
    python manage.py refresh_site_areas --missing     # sites non rattachés
"""

from django.core.management.base import BaseCommand

from apps.geo.services import refresh_all_site_areas


class Command(BaseCommand):
    help = "Recalcule le rattachement administratif des sites"

    def add_arguments(self, parser):
        parser.add_argument(
            '--site', type=int, action='append', dest='sites',
            help="Identifiant d'un site à recalculer (répétable)",
        )
        parser.add_argument(
            '--missing', action='store_true',
            help="Ne traite que les sites n'ayant aucun rattachement",
        )

    def handle(self, *args, **options):
        from apps.users.models import Site

        queryset = Site.objects.all()
        if options['sites']:
            queryset = queryset.filter(pk__in=options['sites'])
        if options['missing']:
            queryset = queryset.filter(areas__isnull=True)

        self.stdout.write(self.style.MIGRATE_HEADING(
            '=== RATTACHEMENT ADMINISTRATIF DES SITES ==='
        ))
        stats = refresh_all_site_areas(queryset=queryset, stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(
            f"  {stats['rattaches']}/{stats['sites']} sites rattachés "
            f"({stats['sans_geometrie']} sans géométrie, "
            f"{stats['orphelins']} sans zone trouvée)"
        ))
