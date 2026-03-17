"""
Seeder pour les sites.
"""
from typing import Any, Dict, List, Tuple

from django.contrib.gis.geos import Point, MultiPolygon, Polygon

from apps.core.models import Nomenclature
from apps.users.models import Site, CorOgSite, BibOrganismes

from .base import BaseSeeder


class SitesSeeder(BaseSeeder):
    """
    Cree les sites de test avec geometries.

    Sites:
    - Reserve Naturelle de la Camargue (RNN)
    - Reserve Naturelle des Aiguilles Rouges (RNN)
    - Reserve Naturelle Regionale du Grand-Voyeux (RNR)
    - Parc Naturel Regional du Vercors (PNR)
    - Espace Naturel Sensible des Marais de Brouage (ENS)
    - Reserve Naturelle de Scandola (RNN)
    - Reserve Naturelle du Lac de Remoray (RNN)
    """

    name = 'sites'
    dependencies = ['organismes']

    # Coordonnees reelles des sites naturels francais (lon, lat, offset)
    SITES_COORDS = {
        'Reserve Naturelle de la Camargue': (4.63, 43.45, 0.15),
        'Reserve Naturelle des Aiguilles Rouges': (6.93, 45.98, 0.08),
        'Reserve Naturelle Regionale du Grand-Voyeux': (2.88, 49.02, 0.03),
        'Parc Naturel Regional du Vercors': (5.45, 44.95, 0.25),
        'Espace Naturel Sensible des Marais de Brouage': (-1.05, 45.87, 0.06),
        'Reserve Naturelle de Scandola': (8.55, 42.37, 0.05),
        'Reserve Naturelle du Lac de Remoray': (6.21, 46.77, 0.04),
    }

    def _get_sites_data(self, organismes: List[BibOrganismes]) -> List[Dict]:
        """Retourne les donnees des sites avec les organismes."""
        # Recuperer les types de site par mnemonique
        type_rnn = Nomenclature.objects.filter(mnemonique='RNN').first()
        type_rnr = Nomenclature.objects.filter(mnemonique='RNR').first()
        type_pnr = Nomenclature.objects.filter(mnemonique='PNR').first()
        type_ens = Nomenclature.objects.filter(mnemonique='ENS').first()

        return [
            {
                'nom_site': 'Reserve Naturelle de la Camargue',
                'id_local': 'RN13',
                'id_inpn': 'FR3600013',
                'id_type_site': type_rnn,
                'surf_off': 13117.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[0], organismes[4]]  # RNF + OFB
            },
            {
                'nom_site': 'Reserve Naturelle des Aiguilles Rouges',
                'id_local': 'RN1',
                'id_inpn': 'FR3600001',
                'id_type_site': type_rnn,
                'surf_off': 3279.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[0]]  # RNF
            },
            {
                'nom_site': 'Reserve Naturelle Regionale du Grand-Voyeux',
                'id_local': 'RNR145',
                'id_inpn': 'FR9300145',
                'id_type_site': type_rnr,
                'surf_off': 264.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[1]]  # CEN AURA
            },
            {
                'nom_site': 'Parc Naturel Regional du Vercors',
                'id_local': 'PNR38',
                'id_inpn': 'FR8000038',
                'id_type_site': type_pnr,
                'surf_off': 206000.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[1], organismes[2]]  # CEN AURA + DREAL
            },
            {
                'nom_site': 'Espace Naturel Sensible des Marais de Brouage',
                'id_local': 'ENS17',
                'id_inpn': 'FR5400017',
                'id_type_site': type_ens,
                'surf_off': 1250.0,
                'marin': True,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[2]]  # DREAL
            },
            {
                'nom_site': 'Reserve Naturelle de Scandola',
                'id_local': 'RN2A',
                'id_inpn': 'FR9300002',
                'id_type_site': type_rnn,
                'surf_off': 1919.0,
                'marin': True,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[3], organismes[4]]  # Parc Ecrins + OFB
            },
            {
                'nom_site': 'Reserve Naturelle du Lac de Remoray',
                'id_local': 'RN25',
                'id_inpn': 'FR3600025',
                'id_type_site': type_rnn,
                'surf_off': 430.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[0]]  # RNF
            },
        ]

    def _create_site_geometry(
        self, lon: float, lat: float, offset: float = 0.05
    ) -> Tuple[MultiPolygon, Point]:
        """
        Cree une geometrie polygone et un point de reference pour un site.

        Args:
            lon: Longitude du centre (WGS84)
            lat: Latitude du centre (WGS84)
            offset: Taille approximative du polygone en degres (~5km par defaut)

        Returns:
            tuple: (MultiPolygon, Point)
        """
        coords = [
            (lon - offset, lat - offset),
            (lon + offset, lat - offset),
            (lon + offset, lat + offset),
            (lon - offset, lat + offset),
            (lon - offset, lat - offset),
        ]
        polygon = Polygon(coords, srid=4326)
        multipolygon = MultiPolygon(polygon, srid=4326)
        point = Point(lon, lat, srid=4326)

        return multipolygon, point

    def seed(self) -> List[Site]:
        """
        Cree les sites de test.

        Returns:
            Liste des sites crees
        """
        self.log_header('Creation des sites')

        organismes = self.context.require('organismes')
        sites_data = self._get_sites_data(organismes)

        sites = []
        for site_data in sites_data:
            organismes_list = site_data.pop('organismes')
            site_name = site_data['nom_site']

            # Ajouter la geometrie
            if site_name in self.SITES_COORDS:
                lon, lat, offset = self.SITES_COORDS[site_name]
                geom, geom_pt = self._create_site_geometry(lon, lat, offset)
                site_data['geom'] = geom
                site_data['geom_pt'] = geom_pt

            site, created = Site.objects.update_or_create(
                nom_site=site_data['nom_site'],
                defaults=site_data
            )
            sites.append(site)

            # Lier aux organismes (le premier est le gestionnaire principal)
            for i, org in enumerate(organismes_list):
                CorOgSite.objects.update_or_create(
                    id_site=site,
                    uuid_og=org,
                    defaults={'principal': i == 0}
                )

            status = "cree" if created else "mis a jour"
            type_code = site.id_type_site.mnemonique if site.id_type_site else 'N/A'
            self.log_item(status, f"{site.nom_site} ({type_code})")
            if self.verbosity >= 2:
                principal_org = organismes_list[0].nom_organisme if organismes_list else 'N/A'
                self.stdout.write(f"              Gestionnaire principal: {principal_org}")

        self.log_summary(len(sites), 'sites')
        self.context.set('sites', sites)
        return sites

    def reset(self) -> int:
        """
        Supprime les sites de test.

        Returns:
            Nombre de sites supprimes
        """
        return Site.objects.all().delete()[0]

    def get_dry_run_summary(self) -> List[str]:
        """
        Resume des sites qui seraient crees.

        Returns:
            Liste des lignes du resume
        """
        return [
            '\nSites (7) avec organismes gestionnaires:',
            '  - Reserve Naturelle de la Camargue (RNN)',
            '      Organismes: RNF [PRINCIPAL], OFB',
            '  - Reserve Naturelle des Aiguilles Rouges (RNN)',
            '      Organismes: RNF [PRINCIPAL]',
            '  - Reserve Naturelle Regionale du Grand-Voyeux (RNR)',
            '      Organismes: CEN AURA [PRINCIPAL]',
            '  - Parc Naturel Regional du Vercors (PNR)',
            '      Organismes: CEN AURA [PRINCIPAL], DREAL',
            '  - Espace Naturel Sensible des Marais de Brouage (ENS)',
            '      Organismes: DREAL [PRINCIPAL]',
            '  - Reserve Naturelle de Scandola (RNN)',
            '      Organismes: Parc Ecrins [PRINCIPAL], OFB',
            '  - Reserve Naturelle du Lac de Remoray (RNN)',
            '      Organismes: RNF [PRINCIPAL]',
        ]
