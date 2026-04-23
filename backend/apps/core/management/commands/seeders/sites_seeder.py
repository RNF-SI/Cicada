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
    Crée les sites de test avec géométries.

    Sites:
    - Réserve Naturelle de la Camargue (RNN)
    - Réserve Naturelle des Aiguilles Rouges (RNN)
    - Réserve Naturelle Régionale du Grand-Voyeux (RNR)
    - Parc Naturel Régional du Vercors (PNR)
    - Espace Naturel Sensible des Marais de Brouage (ENS)
    - Réserve Naturelle de Scandola (RNN)
    - Réserve Naturelle du Lac de Remoray (RNN)
    - Espace Naturel Sensible Départemental de la Forêt de Saou (ENSD, sans code INPN)
    """

    name = 'sites'
    dependencies = ['organismes']

    # Coordonnées réelles des sites naturels français (lon, lat, offset)
    SITES_COORDS = {
        'Réserve Naturelle de la Camargue': (4.63, 43.45, 0.15),
        'Réserve Naturelle des Aiguilles Rouges': (6.93, 45.98, 0.08),
        'Réserve Naturelle Régionale du Grand-Voyeux': (2.88, 49.02, 0.03),
        'Parc Naturel Régional du Vercors': (5.45, 44.95, 0.25),
        'Espace Naturel Sensible des Marais de Brouage': (-1.05, 45.87, 0.06),
        'Réserve Naturelle de Scandola': (8.55, 42.37, 0.05),
        'Réserve Naturelle du Lac de Remoray': (6.21, 46.77, 0.04),
        'Espace Naturel Sensible Départemental de la Forêt de Saou': (5.04, 44.68, 0.05),
    }

    def _get_sites_data(self, organismes: List[BibOrganismes]) -> List[Dict]:
        """Retourne les données des sites avec les organismes."""
        # Récupérer les types de site par mnémonique
        type_rnn = Nomenclature.objects.filter(mnemonique='RNN').first()
        type_rnr = Nomenclature.objects.filter(mnemonique='RNR').first()
        type_pnr = Nomenclature.objects.filter(mnemonique='PNR').first()
        type_ens = Nomenclature.objects.filter(mnemonique='ENS').first()
        type_ensd = Nomenclature.objects.filter(mnemonique='ENSD').first()

        return [
            {
                'nom_site': 'Réserve Naturelle de la Camargue',
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
                'nom_site': 'Réserve Naturelle des Aiguilles Rouges',
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
                'nom_site': 'Réserve Naturelle Régionale du Grand-Voyeux',
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
                'nom_site': 'Parc Naturel Régional du Vercors',
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
                'nom_site': 'Réserve Naturelle de Scandola',
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
                'nom_site': 'Réserve Naturelle du Lac de Remoray',
                'id_local': 'RN25',
                'id_inpn': 'FR3600025',
                'id_type_site': type_rnn,
                'surf_off': 430.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[0]]  # RNF
            },
            {
                'nom_site': 'Espace Naturel Sensible Départemental de la Forêt de Saou',
                'id_local': 'ENSD26',
                'id_inpn': None,  # ENSD : pas de code INPN
                'id_type_site': type_ensd,
                'surf_off': 2500.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[1]]  # CEN AURA
            },
        ]

    def _create_site_geometry(
        self, lon: float, lat: float, offset: float = 0.05
    ) -> Tuple[MultiPolygon, Point]:
        """
        Crée une géométrie polygone et un point de référence pour un site.

        Args:
            lon: Longitude du centre (WGS84)
            lat: Latitude du centre (WGS84)
            offset: Taille approximative du polygone en degrés (~5km par défaut)

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
        Crée les sites de test.

        Returns:
            Liste des sites créés
        """
        self.log_header('Création des sites')

        organismes = self.context.require('organismes')
        sites_data = self._get_sites_data(organismes)

        sites = []
        for site_data in sites_data:
            organismes_list = site_data.pop('organismes')
            site_name = site_data['nom_site']

            # Ajouter la géométrie
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

            status = "créé" if created else "mis à jour"
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
            Nombre de sites supprimés
        """
        return Site.objects.all().delete()[0]

    def get_dry_run_summary(self) -> List[str]:
        """
        Résumé des sites qui seraient créés.

        Returns:
            Liste des lignes du résumé
        """
        return [
            '\nSites (8) avec organismes gestionnaires:',
            '  - Réserve Naturelle de la Camargue (RNN)',
            '      Organismes: RNF [PRINCIPAL], OFB',
            '  - Réserve Naturelle des Aiguilles Rouges (RNN)',
            '      Organismes: RNF [PRINCIPAL]',
            '  - Réserve Naturelle Régionale du Grand-Voyeux (RNR)',
            '      Organismes: CEN AURA [PRINCIPAL]',
            '  - Parc Naturel Régional du Vercors (PNR)',
            '      Organismes: CEN AURA [PRINCIPAL], DREAL',
            '  - Espace Naturel Sensible des Marais de Brouage (ENS)',
            '      Organismes: DREAL [PRINCIPAL]',
            '  - Réserve Naturelle de Scandola (RNN)',
            '      Organismes: Parc Écrins [PRINCIPAL], OFB',
            '  - Réserve Naturelle du Lac de Remoray (RNN)',
            '      Organismes: RNF [PRINCIPAL]',
            '  - Espace Naturel Sensible Départemental de la Forêt de Saou (ENSD, sans code INPN)',
            '      Organismes: CEN AURA [PRINCIPAL]',
        ]
