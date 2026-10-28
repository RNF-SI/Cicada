"""
Export des sites au format GeoJSON, relu tel quel par l'import en masse.

Le fichier sert à faire passer des sites d'une instance CICADA à une autre
(ou vers un SIG). Ses propriétés portent donc les noms que reconnaît la
correspondance automatique de ``BulkSiteImportService`` et uniquement des
valeurs qui ont un sens hors de l'instance :

- le type de site en **mnémonique** (« RNN »), pas en identifiant de
  nomenclature ;
- les organismes gestionnaires par leur **nom** (principal en tête), que
  l'import retrouve s'ils existent et signale sinon ;
- aucun identifiant local (``id_site``, ``slug``, ``id_organisme``) ni aucune
  personne : la liste des utilisateurs d'un site ne sort pas.
"""

import json

from .models import CorOgSite

# Séparateur multi-valeurs accepté par l'import en masse (« A ; B »).
SEPARATEUR_ORGANISMES = ' ; '


def _organismes_par_site(site_ids):
    """Noms des organismes gestionnaires de chaque site, principal en tête."""
    noms = {}
    liens = (
        CorOgSite.objects.filter(id_site_id__in=site_ids)
        .select_related('uuid_og')
        .order_by('-principal', 'uuid_og__nom_organisme')
    )
    for lien in liens:
        if lien.uuid_og and lien.uuid_og.nom_organisme:
            noms.setdefault(lien.id_site_id, []).append(lien.uuid_og.nom_organisme)
    return noms


def site_vers_feature(site, organismes):
    """Une ``Feature`` GeoJSON prête à réimporter."""
    type_site = site.id_type_site
    return {
        'type': 'Feature',
        'geometry': json.loads(site.geom.geojson) if site.geom else None,
        'properties': {
            'nom_site': site.nom_site,
            'id_inpn': site.id_inpn,
            'id_local': site.id_local,
            'type_site': type_site.mnemonique if type_site else None,
            'type_site_libelle': type_site.label if type_site else None,
            'surf_off': site.surf_off,
            'marin': site.marin,
            'outre_mer': site.outre_mer,
            'organisme': SEPARATEUR_ORGANISMES.join(organismes) or None,
        },
    }


def build_sites_geojson(sites):
    """FeatureCollection (octets UTF-8) des sites donnés."""
    sites = list(sites)
    organismes = _organismes_par_site([s.id_site for s in sites])
    collection = {
        'type': 'FeatureCollection',
        'features': [
            site_vers_feature(site, organismes.get(site.id_site, []))
            for site in sites
        ],
    }
    return json.dumps(collection, ensure_ascii=False, indent=2).encode('utf-8')
