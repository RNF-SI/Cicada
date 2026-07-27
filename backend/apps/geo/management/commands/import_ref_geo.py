"""
Import du référentiel géographique administratif (régions, départements).

Les contours des départements sont lus dans le GeoJSON embarqué
``apps/geo/data/departements.geojson`` (cf. le README du dossier pour la source
et la procédure de mise à jour). Les régions ne sont pas importées : elles sont
reconstruites par agrégation ``ST_Union`` des départements de même ``reg_code``,
ce qui garantit que les deux niveaux du filtre « zone géographique » collent
exactement.

Le rattachement des sites est recalculé dans la foulée, sauf ``--no-link``.

Usage :
    python manage.py import_ref_geo              # import (ignoré si déjà fait)
    python manage.py import_ref_geo --force      # réimport complet
    python manage.py import_ref_geo --no-link    # sans recalcul des sites
"""

import json
import os

from django.contrib.gis.db.models import Union
from django.contrib.gis.geos import GEOSGeometry, MultiPolygon
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.geo.models import AreaType, LArea
from apps.geo.services import refresh_all_site_areas

DATA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'data', 'departements.geojson',
)


class Command(BaseCommand):
    help = "Importe les régions et départements dans le schéma ref_geo"

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true',
            help="Force le rechargement même si les zones sont déjà importées",
        )
        parser.add_argument(
            '--no-link', action='store_true',
            help="N'effectue pas le recalcul du rattachement des sites",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING('=== IMPORT REF_GEO ==='))

        if not options['force'] and LArea.objects.exists():
            self.stdout.write(self.style.SUCCESS(
                f'Référentiel géographique déjà importé '
                f'({LArea.objects.count()} zones). '
                f'Utilisez --force pour le recharger.'
            ))
            return

        if not os.path.exists(DATA_FILE):
            self.stderr.write(self.style.ERROR(
                f'Fichier de données introuvable : {DATA_FILE}'
            ))
            return

        with transaction.atomic():
            type_dep, type_reg = self._ensure_types()
            nb_dep = self._import_departements(type_dep)
            nb_reg = self._build_regions(type_reg, type_dep)

        self.stdout.write(self.style.SUCCESS(
            f'  {nb_dep} départements et {nb_reg} régions importés'
        ))

        if options['no_link']:
            self.stdout.write(
                '  Rattachement des sites ignoré (--no-link). '
                'Lancez `refresh_site_areas` pour le calculer.'
            )
            return

        self.stdout.write('=== Rattachement administratif des sites ===')
        stats = refresh_all_site_areas(stdout=self.stdout)
        self.stdout.write(self.style.SUCCESS(
            f"  {stats['rattaches']}/{stats['sites']} sites rattachés "
            f"({stats['sans_geometrie']} sans géométrie, "
            f"{stats['orphelins']} sans zone trouvée)"
        ))

    # ------------------------------------------------------------------ #

    def _ensure_types(self):
        type_dep, _ = AreaType.objects.update_or_create(
            type_code=AreaType.DEPARTEMENT,
            defaults={
                'type_name': 'Département',
                'type_desc': 'Départements et collectivités assimilées',
            },
        )
        type_reg, _ = AreaType.objects.update_or_create(
            type_code=AreaType.REGION,
            defaults={
                'type_name': 'Région',
                'type_desc': 'Régions et collectivités assimilées',
            },
        )
        return type_dep, type_reg

    def _import_departements(self, type_dep):
        with open(DATA_FILE, encoding='utf-8') as fh:
            data = json.load(fh)

        # Purge complète : le référentiel est un tout cohérent, un import
        # partiel laisserait des régions calculées sur d'anciens contours.
        LArea.objects.all().delete()

        self._region_codes = {}
        objets = []
        for feature in data['features']:
            props = feature['properties']
            geom = GEOSGeometry(json.dumps(feature['geometry']), srid=4326)
            if geom.geom_type == 'Polygon':
                geom = MultiPolygon(geom, srid=4326)

            self._region_codes[props['dep_code']] = (
                props['reg_code'], props['reg_name']
            )
            objets.append(LArea(
                id_type=type_dep,
                area_code=props['dep_code'],
                area_name=props['dep_name'],
                geom=geom,
                centroid=geom.centroid,
            ))

        LArea.objects.bulk_create(objets, batch_size=50)
        return len(objets)

    def _build_regions(self, type_reg, type_dep):
        """Agrège les départements en régions, puis rattache les enfants."""
        regions = {}
        for dep_code, (reg_code, reg_name) in self._region_codes.items():
            regions.setdefault(reg_code, {'name': reg_name, 'deps': []})
            regions[reg_code]['deps'].append(dep_code)

        for reg_code, infos in regions.items():
            # ST_Union agrège les contours des départements de la région.
            # L'agrégat rend un Polygon quand la région est d'un seul tenant.
            geom = LArea.objects.filter(
                id_type=type_dep, area_code__in=infos['deps']
            ).aggregate(fusion=Union('geom'))['fusion']
            if geom.geom_type == 'Polygon':
                geom = MultiPolygon(geom, srid=4326)
            geom.srid = 4326

            region = LArea.objects.create(
                id_type=type_reg,
                area_code=reg_code,
                area_name=infos['name'],
                geom=geom,
                centroid=geom.centroid,
            )
            LArea.objects.filter(
                id_type=type_dep, area_code__in=infos['deps']
            ).update(parent=region)

        return len(regions)
