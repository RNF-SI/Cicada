"""
Service pour l'import en masse de sites depuis des fichiers GeoJSON ou CSV.
"""
import csv
import io
import json
import logging

from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon
from django.db import transaction
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from apps.core.models import Nomenclature
from apps.notifications.models import ValidationRequest
from apps.notifications.services import NotificationService

from .models import BulkImportJob, CorOgSite, CorRoleSite, Site

logger = logging.getLogger(__name__)

# Mapping auto-détection: clé source (lowercase) -> champ cible
FIELD_MAPPING_HINTS = {
    # nom_site
    'nom_site': 'nom_site',
    'nom': 'nom_site',
    'name': 'nom_site',
    'site_name': 'nom_site',
    'site': 'nom_site',
    'label': 'nom_site',
    'libelle': 'nom_site',
    # id_inpn
    'id_inpn': 'id_inpn',
    'inpn': 'id_inpn',
    'code_inpn': 'id_inpn',
    'cdsinp': 'id_inpn',
    # id_local
    'id_local': 'id_local',
    'id': 'id_local',
    'code': 'id_local',
    'code_local': 'id_local',
    'identifiant': 'id_local',
    # type_site_id
    'type_site_id': 'type_site_id',
    'type_site': 'type_site_id',
    'type': 'type_site_id',
    'id_type_site': 'type_site_id',
    # surf_off
    'surf_off': 'surf_off',
    'surface': 'surf_off',
    'superficie': 'surf_off',
    'area': 'surf_off',
    'surface_ha': 'surf_off',
    # marin
    'marin': 'marin',
    'marine': 'marin',
    'milieu_marin': 'marin',
    # outre_mer
    'outre_mer': 'outre_mer',
    'outremer': 'outre_mer',
    'overseas': 'outre_mer',
}

TARGET_FIELDS = ['nom_site', 'id_inpn', 'id_local', 'type_site_id', 'surf_off', 'marin', 'outre_mer']


class BulkSiteImportService:
    """Service pour parser, valider et importer des sites en masse."""

    @staticmethod
    def parse_geojson(file_content):
        """
        Parse un fichier GeoJSON (FeatureCollection).
        Retourne une liste de dicts avec 'properties' et 'geometry'.
        """
        try:
            data = json.loads(file_content)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"Fichier JSON invalide: {e}")

        if not isinstance(data, dict) or data.get('type') != 'FeatureCollection':
            raise ValueError("Le fichier doit être un GeoJSON de type FeatureCollection.")

        features = data.get('features', [])
        if not features:
            raise ValueError("Le fichier ne contient aucune feature.")

        result = []
        for i, feature in enumerate(features):
            if not isinstance(feature, dict) or feature.get('type') != 'Feature':
                continue
            properties = feature.get('properties', {}) or {}
            geometry = feature.get('geometry')
            result.append({
                'row_index': i,
                'properties': properties,
                'geometry': geometry,
            })

        if not result:
            raise ValueError("Aucune feature valide trouvée dans le fichier.")

        return result

    @staticmethod
    def parse_csv(file_content):
        """
        Parse un fichier CSV.
        Retourne une liste de dicts avec 'properties' (pas de géométrie).
        """
        try:
            if isinstance(file_content, bytes):
                file_content = file_content.decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(file_content))
            rows = list(reader)
        except Exception as e:
            raise ValueError(f"Fichier CSV invalide: {e}")

        if not rows:
            raise ValueError("Le fichier CSV est vide.")

        result = []
        for i, row in enumerate(rows):
            # Filter out None keys from csv.DictReader
            properties = {k: v for k, v in row.items() if k is not None}
            result.append({
                'row_index': i,
                'properties': properties,
                'geometry': None,
            })

        return result

    @staticmethod
    def detect_field_mapping(property_names):
        """
        Auto-détecte le mapping entre les propriétés source et les champs cibles.
        Retourne un dict {source_property: target_field}.
        """
        mapping = {}
        used_targets = set()

        for prop in property_names:
            prop_lower = prop.lower().strip()
            target = FIELD_MAPPING_HINTS.get(prop_lower)
            if target and target not in used_targets:
                mapping[prop] = target
                used_targets.add(target)

        return mapping

    @staticmethod
    def apply_field_mapping(sites, mapping):
        """
        Applique le mapping des champs aux données parsées.
        Retourne une liste de dicts avec les champs cibles.
        """
        result = []
        for site_data in sites:
            properties = site_data['properties']
            mapped = {}
            for source_key, target_field in mapping.items():
                if source_key in properties:
                    mapped[target_field] = properties[source_key]

            result.append({
                'row_index': site_data['row_index'],
                'original_properties': properties,
                'mapped_data': mapped,
                'geometry': site_data.get('geometry'),
            })
        return result

    @staticmethod
    def validate_batch(sites):
        """
        Valide un batch de sites.
        Retourne la même liste enrichie de 'errors', 'warnings', 'duplicate_info'.
        """
        # Collect all id_inpn in DB for duplicate check
        all_inpn_in_batch = [
            s['mapped_data'].get('id_inpn', '').strip()
            for s in sites
            if s['mapped_data'].get('id_inpn')
        ]
        existing_inpn_sites = {}
        if all_inpn_in_batch:
            for site in Site.objects.filter(id_inpn__in=all_inpn_in_batch).values('id_inpn', 'nom_site', 'id_site'):
                existing_inpn_sites[site['id_inpn']] = site

        # Collect all nom_site in DB for exact name duplicate check
        all_names_in_batch = [
            s['mapped_data'].get('nom_site', '').strip()
            for s in sites
            if s['mapped_data'].get('nom_site')
        ]
        existing_name_sites = {}
        if all_names_in_batch:
            name_q = Q()
            for name in all_names_in_batch:
                if name:
                    name_q |= Q(nom_site__iexact=name)
            if name_q:
                for site in Site.objects.filter(name_q, active=True).values('nom_site', 'id_site'):
                    existing_name_sites[site['nom_site'].lower()] = site

        # Track intra-batch duplicates
        seen_inpn = {}
        seen_names = {}

        # Build lookup tables for site type nomenclatures
        site_type_nomenclatures = Nomenclature.objects.filter(
            id_type__mnemonique='Espace naturel'
        )
        valid_nomenclature_ids = set()
        nomenclature_by_mnemonique = {}
        nomenclature_by_label = {}
        for nom in site_type_nomenclatures:
            valid_nomenclature_ids.add(nom.id_nomenclature)
            nomenclature_by_mnemonique[nom.mnemonique.lower()] = nom.id_nomenclature
            nomenclature_by_label[nom.label.lower()] = nom.id_nomenclature

        valid_type_names = [
            f"{n.mnemonique} ({n.label})"
            for n in site_type_nomenclatures
        ]

        for site_data in sites:
            errors = []
            warnings = []
            duplicate_info = None
            mapped = site_data['mapped_data']

            # Validate nom_site
            nom_site = (mapped.get('nom_site') or '').strip()
            if not nom_site:
                errors.append("Le nom du site est obligatoire.")
            elif len(nom_site) < 3:
                errors.append("Le nom doit contenir au moins 3 caractères.")

            # Validate surf_off
            surf_off = mapped.get('surf_off')
            if surf_off is not None and surf_off != '':
                try:
                    surf_val = float(surf_off)
                    if surf_val < 0:
                        errors.append("La surface ne peut pas être négative.")
                except (ValueError, TypeError):
                    errors.append("La surface doit être un nombre.")

            # Validate and resolve type_site_id (accepts ID, mnemonique or label)
            type_site_id = mapped.get('type_site_id')
            if type_site_id is not None and type_site_id != '':
                resolved_id = _resolve_site_type(
                    type_site_id, valid_nomenclature_ids,
                    nomenclature_by_mnemonique, nomenclature_by_label,
                )
                if resolved_id is not None:
                    mapped['type_site_id'] = resolved_id
                else:
                    errors.append(
                        f"Type de site introuvable : \"{type_site_id}\". "
                        f"Valeurs acceptées : {', '.join(valid_type_names)}"
                    )

            # Validate id_inpn uniqueness
            id_inpn = (mapped.get('id_inpn') or '').strip()
            if id_inpn:
                # Check DB duplicate
                if id_inpn in existing_inpn_sites:
                    db_site = existing_inpn_sites[id_inpn]
                    errors.append(
                        f"Ce code INPN est déjà utilisé par le site \"{db_site['nom_site']}\"."
                    )
                    duplicate_info = {
                        'type': 'exact_inpn',
                        'existing_site_id': db_site['id_site'],
                        'existing_site_name': db_site['nom_site'],
                    }
                # Check intra-batch duplicate
                elif id_inpn in seen_inpn:
                    errors.append(
                        f"Code INPN en doublon dans le fichier (ligne {seen_inpn[id_inpn] + 1})."
                    )
                else:
                    seen_inpn[id_inpn] = site_data['row_index']

            # Validate nom_site uniqueness
            if nom_site:
                nom_site_lower = nom_site.lower()
                # Check DB duplicate (exact match, case-insensitive)
                if nom_site_lower in existing_name_sites:
                    db_site = existing_name_sites[nom_site_lower]
                    errors.append(
                        f"Ce nom de site est déjà utilisé par le site \"{db_site['nom_site']}\"."
                    )
                    if not duplicate_info:
                        duplicate_info = {
                            'type': 'exact_name',
                            'existing_site_id': db_site['id_site'],
                            'existing_site_name': db_site['nom_site'],
                        }
                # Check intra-batch duplicate (exact match, case-insensitive)
                elif nom_site_lower in seen_names:
                    errors.append(
                        f"Nom de site en doublon dans le fichier (ligne {seen_names[nom_site_lower] + 1})."
                    )
                else:
                    seen_names[nom_site_lower] = site_data['row_index']

            # Validate geometry
            geometry = site_data.get('geometry')
            has_geometry = False
            if geometry:
                try:
                    geom = GEOSGeometry(json.dumps(geometry))
                    if geom.geom_type not in ('Polygon', 'MultiPolygon'):
                        errors.append("La géométrie doit être un Polygon ou MultiPolygon.")
                    else:
                        has_geometry = True
                except Exception as e:
                    errors.append(f"Géométrie invalide: {e}")

            site_data['errors'] = errors
            site_data['warnings'] = warnings
            site_data['duplicate_info'] = duplicate_info
            site_data['has_geometry'] = has_geometry

        return sites

    @staticmethod
    def import_sites(sites, user, selected_indices=None):
        """
        Importe les sites validés.
        - Super admin: sites actifs + CorRoleSite(referent) + CorOgSite(principal)
        - Autres: sites inactifs + ValidationRequest(site_creation)

        Returns dict with {created, failed, validation_pending, details}.
        """
        if selected_indices is not None:
            sites = [s for s in sites if s['row_index'] in selected_indices]

        is_super_admin = user.is_super_admin()
        created = 0
        failed = 0
        validation_pending = 0
        details = []

        for site_data in sites:
            mapped = site_data['mapped_data']
            nom_site = (mapped.get('nom_site') or '').strip()

            try:
                with transaction.atomic():
                    # Prepare site fields
                    site_kwargs = {
                        'nom_site': nom_site,
                        'active': is_super_admin,
                    }

                    id_local = mapped.get('id_local')
                    if id_local:
                        site_kwargs['id_local'] = str(id_local).strip()

                    id_inpn = (mapped.get('id_inpn') or '').strip()
                    if id_inpn:
                        site_kwargs['id_inpn'] = id_inpn

                    surf_off = mapped.get('surf_off')
                    if surf_off is not None and surf_off != '':
                        site_kwargs['surf_off'] = float(surf_off)

                    marin = mapped.get('marin')
                    if marin is not None and marin != '':
                        site_kwargs['marin'] = _parse_bool(marin)

                    outre_mer = mapped.get('outre_mer')
                    if outre_mer is not None and outre_mer != '':
                        site_kwargs['outre_mer'] = _parse_bool(outre_mer)

                    # Type de site (already resolved to ID during validation)
                    type_site_id = mapped.get('type_site_id')
                    if type_site_id is not None and type_site_id != '':
                        try:
                            site_kwargs['id_type_site'] = Nomenclature.objects.get(
                                id_nomenclature=int(type_site_id)
                            )
                        except (Nomenclature.DoesNotExist, ValueError, TypeError):
                            pass

                    # Create site
                    site = Site(**site_kwargs)

                    # Geometry
                    geometry = site_data.get('geometry')
                    if geometry:
                        geom = GEOSGeometry(json.dumps(geometry))
                        if geom.geom_type == 'Polygon':
                            geom = MultiPolygon(geom)
                        site.geom = geom

                    site.save()

                    if is_super_admin:
                        # Super admin: referent + org link
                        CorRoleSite.objects.create(
                            id_site=site,
                            id_role=user,
                            referent=True,
                            referent_valid=True,
                            conservateur=False,
                        )
                        if user.id_organisme:
                            CorOgSite.objects.get_or_create(
                                id_site=site,
                                uuid_og=user.id_organisme,
                                defaults={'principal': True},
                            )
                        created += 1
                        details.append({
                            'row_index': site_data['row_index'],
                            'nom_site': nom_site,
                            'status': 'created',
                            'site_id': site.id_site,
                        })
                    else:
                        # Non-admin: validation request
                        validation_request = ValidationRequest.objects.create(
                            request_type='site_creation',
                            status='pending',
                            requester=user,
                            target_site=site,
                            justification=f"Import en masse - Création du site {nom_site}",
                            request_as_referent=True,
                        )
                        NotificationService.notify_validators(validation_request)
                        validation_pending += 1
                        details.append({
                            'row_index': site_data['row_index'],
                            'nom_site': nom_site,
                            'status': 'validation_pending',
                            'site_id': site.id_site,
                            'validation_request_id': validation_request.id,
                        })

            except Exception as e:
                logger.error(f"Erreur import site ligne {site_data['row_index']}: {e}")
                failed += 1
                details.append({
                    'row_index': site_data['row_index'],
                    'nom_site': nom_site,
                    'status': 'failed',
                    'error': str(e),
                })

        return {
            'created': created,
            'failed': failed,
            'validation_pending': validation_pending,
            'details': details,
        }


def _resolve_site_type(value, valid_ids, by_mnemonique, by_label):
    """
    Resolve a site type value to a nomenclature ID.
    Accepts: numeric ID, mnemonique (e.g. 'RNN'), or label (e.g. 'Réserve Naturelle Nationale').
    Case-insensitive for mnemonique and label.
    Returns the id_nomenclature or None if not found.
    """
    # Try as numeric ID first
    try:
        type_id = int(value)
        if type_id in valid_ids:
            return type_id
    except (ValueError, TypeError):
        pass

    # Try as mnemonique or label (case-insensitive)
    value_lower = str(value).strip().lower()
    if value_lower in by_mnemonique:
        return by_mnemonique[value_lower]
    if value_lower in by_label:
        return by_label[value_lower]

    return None


def _parse_bool(value):
    """Parse a boolean value from various formats."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ('true', '1', 'oui', 'yes', 'o', 'y')
    return bool(value)
