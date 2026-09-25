"""
Integration tests for bulk site import API.
Tests upload, validation, execution and status endpoints.
"""
import json

import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.users.models import Site, CorRoleSite, CorOgSite, BulkImportJob
from apps.notifications.models import ValidationRequest
from tests.factories.users import (
    SuperAdminFactory,
    AdminOrganismeFactory,
    RoleFactory,
    OrganismeFactory,
    SiteFactory,
)


def _make_geojson_file(features):
    """Helper to create a GeoJSON FeatureCollection file."""
    data = {
        "type": "FeatureCollection",
        "features": features,
    }
    content = json.dumps(data).encode('utf-8')
    return SimpleUploadedFile("sites.geojson", content, content_type="application/json")


def _make_csv_file(header, rows):
    """Helper to create a CSV file."""
    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join(str(v) for v in row))
    content = "\n".join(lines).encode('utf-8')
    return SimpleUploadedFile("sites.csv", content, content_type="text/csv")


def _make_feature(name, inpn=None, geometry=None):
    """Helper to create a GeoJSON Feature."""
    properties = {"nom": name}
    if inpn:
        properties["inpn"] = inpn
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": geometry,
    }


SIMPLE_POLYGON = {
    "type": "Polygon",
    "coordinates": [[[2.0, 46.0], [2.1, 46.0], [2.1, 46.1], [2.0, 46.1], [2.0, 46.0]]],
}


@pytest.fixture
def api_client():
    return APIClient()


# =============================================================================
# VALIDATION TESTS
# =============================================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestBulkImportValidation:
    """Tests for POST /api/users/sites/bulk_import_validate/"""

    def test_upload_geojson_valid(self, api_client):
        """Upload a valid GeoJSON FeatureCollection returns parsed sites."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        features = [
            _make_feature("Site Alpha", inpn="INPN001", geometry=SIMPLE_POLYGON),
            _make_feature("Site Beta", inpn="INPN002"),
            _make_feature("Site Gamma"),
        ]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data['total'] == 3
        assert 'nom' in data['detected_properties']
        assert len(data['sites']) == 3
        assert data['suggested_mapping']['nom'] == 'nom_site'

    def test_upload_csv_valid(self, api_client):
        """Upload a valid CSV returns parsed sites."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        f = _make_csv_file(
            ["nom_site", "id_inpn", "surface"],
            [
                ["Réserve du Lac", "INPN100", "500"],
                ["Parc des Monts", "INPN101", "1200"],
            ],
        )

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data['total'] == 2
        assert data['suggested_mapping']['nom_site'] == 'nom_site'
        assert data['suggested_mapping']['surface'] == 'surf_off'

    def test_reject_invalid_format(self, api_client):
        """Reject non-supported file formats."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        f = SimpleUploadedFile("data.txt", b"hello", content_type="text/plain")

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Format' in response.data.get('error', '')

    def test_reject_non_feature_collection(self, api_client):
        """Reject GeoJSON that is not a FeatureCollection."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        content = json.dumps({"type": "Point", "coordinates": [0, 0]}).encode()
        f = SimpleUploadedFile("bad.geojson", content, content_type="application/json")

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_reject_bare_polygon_with_explicit_message(self, api_client):
        """#439 — Une géométrie nue (Polygon seul, sans propriétés) est refusée
        avec un message explicite expliquant qu'on attend une FeatureCollection
        de sites. C'est exactement le fichier `polygon_invalid.geojson` testé."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        content = json.dumps({
            "type": "Polygon",
            "coordinates": [[[2.0, 46.0], [3.0, 47.0], [2.0, 47.0], [3.0, 46.0], [2.0, 46.0]]],
        }).encode()
        f = SimpleUploadedFile("polygon_invalid.geojson", content, content_type="application/json")

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error = response.data.get('error', '')
        # Message explicite : mentionne la géométrie nue ET la FeatureCollection attendue.
        assert 'géométrie' in error.lower()
        assert 'FeatureCollection' in error

    def test_accept_single_feature(self, api_client):
        """#439 — Une Feature seule (avec propriétés) est acceptée comme un site."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        feature = _make_feature("Site unique", inpn="FR9999999", geometry=SIMPLE_POLYGON)
        content = json.dumps(feature).encode()
        f = SimpleUploadedFile("one.geojson", content, content_type="application/json")

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 1

    def test_auto_detection_mapping(self, api_client):
        """Auto-detection maps common property names."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        features = [_make_feature("Test Site", inpn="X123")]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        mapping = response.data['suggested_mapping']
        assert mapping.get('nom') == 'nom_site'
        assert mapping.get('inpn') == 'id_inpn'

    def test_custom_field_mapping(self, api_client):
        """Custom field_mapping overrides auto-detection."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        features = [
            {
                "type": "Feature",
                "properties": {"label": "Mon Site", "code": "C001"},
                "geometry": None,
            }
        ]
        f = _make_geojson_file(features)
        custom_mapping = json.dumps({"label": "nom_site", "code": "id_inpn"})

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f, 'field_mapping': custom_mapping},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        site = response.data['sites'][0]
        assert site['mapped_data']['nom_site'] == 'Mon Site'
        assert site['mapped_data']['id_inpn'] == 'C001'

    def test_validate_short_name_error(self, api_client):
        """Site with name < 3 chars produces error."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        features = [_make_feature("AB")]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['errors'] == 1
        assert len(response.data['sites'][0]['errors']) > 0

    def test_duplicate_inpn_in_db(self, api_client):
        """Existing INPN code in DB produces blocking error."""
        admin = SuperAdminFactory()
        SiteFactory(id_inpn="EXISTING01", nom_site="Existing Site")
        api_client.force_authenticate(user=admin)

        features = [_make_feature("New Site", inpn="EXISTING01")]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['errors'] >= 1
        site = response.data['sites'][0]
        assert site['duplicate_info'] is not None
        assert site['duplicate_info']['type'] == 'exact_inpn'

    def test_duplicate_inpn_intra_batch(self, api_client):
        """Duplicate INPN within the same batch produces error."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        features = [
            _make_feature("Site A", inpn="DUP001"),
            _make_feature("Site B", inpn="DUP001"),
        ]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        # Second site should have the error
        assert response.data['errors'] >= 1

    def test_duplicate_name_in_db(self, api_client):
        """Existing site name (case-insensitive) produces blocking error."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site="Réserve du Lac")
        api_client.force_authenticate(user=admin)

        features = [_make_feature("réserve du lac")]  # same name, different case
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['errors'] >= 1
        site = response.data['sites'][0]
        assert len(site['errors']) > 0
        assert site['duplicate_info'] is not None
        assert site['duplicate_info']['type'] == 'exact_name'

    def test_similar_name_in_db_returns_warning(self, api_client):
        """Site with similar name in DB produces non-blocking warning."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site="Réserve Naturelle de Camargue")
        api_client.force_authenticate(user=admin)

        features = [_make_feature("Camargue")]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        site = response.data['sites'][0]
        # Should have warning, not error
        assert len(site['warnings']) > 0
        assert 'similaire' in site['warnings'][0].lower()
        assert len(site['errors']) == 0
        assert site['duplicate_info'] is None
        # similar_names should contain the existing site
        assert len(site['similar_names']) > 0
        assert site['similar_names'][0]['nom_site'] == 'Réserve Naturelle de Camargue'

    def test_similar_name_no_warning_on_exact_match(self, api_client):
        """Exact name match produces error, not similar name warning."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site="Camargue")
        api_client.force_authenticate(user=admin)

        features = [_make_feature("Camargue")]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        site = response.data['sites'][0]
        # Should have blocking error, no similar name warning
        assert len(site['errors']) > 0
        assert site['duplicate_info'] is not None
        assert site['duplicate_info']['type'] == 'exact_name'
        # No similar name warning
        similar_warnings = [w for w in site['warnings'] if 'similaire' in w.lower()]
        assert len(similar_warnings) == 0

    def test_similar_name_short_name_ignored(self, api_client):
        """Names shorter than 3 characters don't trigger similar name search."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site="AB Testing Site")
        api_client.force_authenticate(user=admin)

        features = [_make_feature("AB")]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        site = response.data['sites'][0]
        # Should have validation error (name too short), no similar name warning
        similar_warnings = [w for w in site['warnings'] if 'similaire' in w.lower()]
        assert len(similar_warnings) == 0

    def test_similar_name_does_not_block_import(self, api_client):
        """Sites with similar name warnings can still be imported."""
        org = OrganismeFactory()
        admin = SuperAdminFactory(id_organisme=org)
        SiteFactory(nom_site="Réserve Naturelle de Camargue")
        api_client.force_authenticate(user=admin)

        # First validate
        features = [_make_feature("Camargue")]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        site = response.data['sites'][0]
        assert len(site['warnings']) > 0
        assert len(site['errors']) == 0

        # Now import - should succeed
        sites = [
            {'row_index': 0, 'mapped_data': {'nom_site': 'Camargue'}},
        ]
        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['created'] == 1
        assert Site.objects.filter(nom_site='Camargue').exists()

    def test_similar_name_inactive_sites_excluded(self, api_client):
        """Inactive sites are not considered for similar name detection."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site="Réserve Naturelle de Camargue", active=False)
        api_client.force_authenticate(user=admin)

        features = [_make_feature("Camargue")]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        site = response.data['sites'][0]
        # No similar name warning because the existing site is inactive
        similar_warnings = [w for w in site['warnings'] if 'similaire' in w.lower()]
        assert len(similar_warnings) == 0

    def test_similar_name_word_overlap_in_db(self, api_client):
        """Sites sharing significant words with DB sites get a warning."""
        admin = SuperAdminFactory()
        SiteFactory(nom_site="Réserve naturelle du Marais de Lavours")
        api_client.force_authenticate(user=admin)

        features = [_make_feature("Parc naturel régional du Marais de Lavours")]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        site = response.data['sites'][0]
        assert len(site['errors']) == 0
        assert len(site['warnings']) > 0
        assert 'similaire' in site['warnings'][0].lower()
        assert 'existants' in site['warnings'][0].lower()

    def test_similar_name_intra_batch(self, api_client):
        """Sites with similar names within the same batch get a warning."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        features = [
            _make_feature("Réserve naturelle du Marais de Lavours"),
            _make_feature("Parc naturel régional du Marais de Lavours"),
        ]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        site_a = response.data['sites'][0]
        site_b = response.data['sites'][1]
        # Both should have intra-batch similarity warnings
        batch_warnings_a = [w for w in site_a['warnings'] if 'fichier' in w.lower()]
        batch_warnings_b = [w for w in site_b['warnings'] if 'fichier' in w.lower()]
        assert len(batch_warnings_a) > 0, f"Expected intra-batch warning for site A, got: {site_a['warnings']}"
        assert len(batch_warnings_b) > 0, f"Expected intra-batch warning for site B, got: {site_b['warnings']}"
        # Both should still be importable (no errors)
        assert len(site_a['errors']) == 0
        assert len(site_b['errors']) == 0

    def test_similar_name_no_false_positive_different_sites(self, api_client):
        """Sites with different geographic names don't trigger similarity."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        features = [
            _make_feature("Réserve naturelle de Camargue"),
            _make_feature("Réserve naturelle de la Vanoise"),
        ]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        site_a = response.data['sites'][0]
        site_b = response.data['sites'][1]
        # Should NOT have similarity warnings (different geographic names)
        batch_warnings_a = [w for w in site_a['warnings'] if 'similaire' in w.lower()]
        batch_warnings_b = [w for w in site_b['warnings'] if 'similaire' in w.lower()]
        assert len(batch_warnings_a) == 0, f"Unexpected warning: {site_a['warnings']}"
        assert len(batch_warnings_b) == 0, f"Unexpected warning: {site_b['warnings']}"

    def test_permission_denied_for_regular_user(self, api_client):
        """Regular user cannot access bulk import."""
        user = RoleFactory()
        api_client.force_authenticate(user=user)

        features = [_make_feature("Test")]
        f = _make_geojson_file(features)

        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': f},
            format='multipart',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# EXECUTION TESTS
# =============================================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestBulkImportExecution:
    """Tests for POST /api/users/sites/bulk_import_execute/"""

    def test_import_sync_valid_sites(self, api_client):
        """Import 3 valid sites synchronously."""
        admin = SuperAdminFactory(id_organisme=OrganismeFactory())
        api_client.force_authenticate(user=admin)

        sites = [
            {'row_index': 0, 'mapped_data': {'nom_site': 'Import Site A'}, 'geometry': SIMPLE_POLYGON},
            {'row_index': 1, 'mapped_data': {'nom_site': 'Import Site B'}},
            {'row_index': 2, 'mapped_data': {'nom_site': 'Import Site C', 'id_inpn': 'IMP003'}},
        ]

        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0, 1, 2]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.data
        assert data['async'] is False
        assert data['created'] == 3
        assert data['failed'] == 0

        # Verify sites exist
        assert Site.objects.filter(nom_site='Import Site A').exists()
        assert Site.objects.filter(nom_site='Import Site B').exists()
        assert Site.objects.filter(id_inpn='IMP003').exists()

    def test_super_admin_creates_active_sites_with_relations(self, api_client):
        """Super admin creates active sites with CorRoleSite and CorOgSite."""
        org = OrganismeFactory()
        admin = SuperAdminFactory(id_organisme=org)
        api_client.force_authenticate(user=admin)

        sites = [
            {'row_index': 0, 'mapped_data': {'nom_site': 'Active Site'}},
        ]

        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        site = Site.objects.get(nom_site='Active Site')
        assert site.active is True
        assert CorRoleSite.objects.filter(id_site=site, id_role=admin, referent=True).exists()
        assert CorOgSite.objects.filter(id_site=site, uuid_og=org, principal=True).exists()

    def test_admin_og_creates_inactive_sites_with_validation(self, api_client):
        """Admin organisme creates inactive sites with validation requests."""
        org = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=org)
        api_client.force_authenticate(user=admin_og)

        sites = [
            {'row_index': 0, 'mapped_data': {'nom_site': 'Pending Site'}},
        ]

        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['validation_pending'] == 1
        site = Site.objects.get(nom_site='Pending Site')
        assert site.active is False
        assert ValidationRequest.objects.filter(
            target_site=site,
            request_type='site_creation',
            status='pending',
        ).exists()

    def test_only_selected_indices_imported(self, api_client):
        """Only sites with selected indices are imported."""
        admin = SuperAdminFactory(id_organisme=OrganismeFactory())
        api_client.force_authenticate(user=admin)

        sites = [
            {'row_index': 0, 'mapped_data': {'nom_site': 'Selected Site'}},
            {'row_index': 1, 'mapped_data': {'nom_site': 'Not Selected Site'}},
        ]

        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['created'] == 1
        assert Site.objects.filter(nom_site='Selected Site').exists()
        assert not Site.objects.filter(nom_site='Not Selected Site').exists()

    def test_empty_selection_rejected(self, api_client):
        """Empty selection returns 400."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': [], 'selected_indices': []},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_import_polygon_geometry_converted_to_multipolygon(self, api_client):
        """Import d'un Polygon simple -> stocké en MultiPolygon valide, SRID 4326."""
        admin = SuperAdminFactory(id_organisme=OrganismeFactory())
        api_client.force_authenticate(user=admin)

        sites = [
            {'row_index': 0, 'mapped_data': {'nom_site': 'Import Geom Poly'},
             'geometry': SIMPLE_POLYGON},
        ]
        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['created'] == 1
        site = Site.objects.get(nom_site='Import Geom Poly')
        assert site.geom is not None
        assert site.geom.geom_type == 'MultiPolygon'
        assert site.geom.valid
        assert site.geom.srid == 4326

    def test_import_unclosed_ring_is_repaired(self, api_client):
        """Import d'un anneau non fermé (Shapefile/GeoJSON) -> réparé."""
        admin = SuperAdminFactory(id_organisme=OrganismeFactory())
        api_client.force_authenticate(user=admin)

        unclosed = {
            "type": "Polygon",
            "coordinates": [[[2.0, 46.0], [2.1, 46.0], [2.1, 46.1], [2.0, 46.1]]],
        }
        sites = [
            {'row_index': 0, 'mapped_data': {'nom_site': 'Import Unclosed'},
             'geometry': unclosed},
        ]
        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['created'] == 1
        site = Site.objects.get(nom_site='Import Unclosed')
        assert site.geom.geom_type == 'MultiPolygon'
        assert site.geom.valid


# =============================================================================
# STATUS TESTS
# =============================================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestBulkImportStatus:
    """Tests for GET /api/users/sites/bulk_import_status/"""

    def test_get_job_status(self, api_client):
        """Returns correct job status."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        job = BulkImportJob.objects.create(
            user=admin,
            status='completed',
            total_sites=5,
            processed_sites=5,
            created_sites=3,
            failed_sites=1,
            validation_pending_sites=1,
        )

        response = api_client.get(
            f'/api/users/sites/bulk_import_status/?job_id={job.id}'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'completed'
        assert response.data['total_sites'] == 5
        assert response.data['created_sites'] == 3

    def test_job_not_found(self, api_client):
        """Non-existing job returns 404."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        response = api_client.get(
            '/api/users/sites/bulk_import_status/?job_id=99999'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_job_of_other_user_forbidden(self, api_client):
        """Non-super admin cannot see another user's job."""
        org = OrganismeFactory()
        admin1 = AdminOrganismeFactory(id_organisme=org)
        admin2 = AdminOrganismeFactory(id_organisme=OrganismeFactory())

        job = BulkImportJob.objects.create(
            user=admin1,
            status='processing',
            total_sites=10,
        )

        api_client.force_authenticate(user=admin2)
        response = api_client.get(
            f'/api/users/sites/bulk_import_status/?job_id={job.id}'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# RATTACHEMENT ORGANISME / RÉFÉRENT PAR LIGNE (#647)
# =============================================================================


@pytest.mark.django_db
@pytest.mark.integration
class TestBulkImportPerRowRelations:
    """
    Colonnes « organisme » et « référent » : chaque site est rattaché à sa
    propre structure au lieu d'hériter de celle de l'importateur (#647).
    """

    def test_mapping_detects_organisme_and_referent_columns(self, api_client):
        """Les en-têtes organisme / référent sont auto-détectés."""
        admin = SuperAdminFactory(id_organisme=OrganismeFactory())
        api_client.force_authenticate(user=admin)

        csv_file = _make_csv_file(
            ['nom', 'gestionnaire', 'referent'],
            [['Site Detect', 'CEN Machin', 'a@test.fr']],
        )
        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': csv_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        mapping = response.data['suggested_mapping']
        assert mapping['gestionnaire'] == 'organisme'
        assert mapping['referent'] == 'referent'

    def test_validation_resolves_organisme_by_name(self, api_client):
        """Un nom d'organisme connu (casse/accents libres) est résolu."""
        admin = SuperAdminFactory(id_organisme=OrganismeFactory())
        org = OrganismeFactory(nom_organisme='Conservatoire des Espaces Naturels')
        api_client.force_authenticate(user=admin)

        csv_file = _make_csv_file(
            ['nom', 'organisme'],
            [['Site Resolu', 'conservatoire des espaces naturels']],
        )
        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': csv_file},
            format='multipart',
        )

        assert response.status_code == status.HTTP_200_OK
        row = response.data['sites'][0]
        assert row['resolved_organismes'] == [
            {'id_organisme': org.id_organisme, 'nom_organisme': org.nom_organisme}
        ]
        assert row['errors'] == []

    def test_validation_warns_on_unknown_organisme(self, api_client):
        """Organisme introuvable : avertissement non bloquant, pas d'erreur."""
        importer_org = OrganismeFactory(nom_organisme='RNF')
        admin = SuperAdminFactory(id_organisme=importer_org)
        api_client.force_authenticate(user=admin)

        csv_file = _make_csv_file(
            ['nom', 'organisme'],
            [['Site Inconnu', 'Structure Fantome']],
        )
        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': csv_file},
            format='multipart',
        )

        row = response.data['sites'][0]
        assert row['errors'] == []
        assert row['resolved_organismes'] == []
        assert any('Structure Fantome' in w for w in row['warnings'])
        assert any('RNF' in w for w in row['warnings'])

    def test_import_links_each_site_to_its_own_organisme(self, api_client):
        """Deux sites, deux organismes : chacun garde le sien."""
        importer_org = OrganismeFactory(nom_organisme='RNF National')
        admin = SuperAdminFactory(id_organisme=importer_org)
        org_a = OrganismeFactory(nom_organisme='CEN Alpha')
        org_b = OrganismeFactory(nom_organisme='CEN Beta')
        api_client.force_authenticate(user=admin)

        sites = [
            {'row_index': 0, 'mapped_data': {'nom_site': 'Site Alpha', 'organisme': 'CEN Alpha'}},
            {'row_index': 1, 'mapped_data': {'nom_site': 'Site Beta', 'organisme': 'CEN Beta'}},
        ]
        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0, 1]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        site_a = Site.objects.get(nom_site='Site Alpha')
        site_b = Site.objects.get(nom_site='Site Beta')
        assert CorOgSite.objects.filter(id_site=site_a, uuid_og=org_a, principal=True).exists()
        assert CorOgSite.objects.filter(id_site=site_b, uuid_og=org_b, principal=True).exists()
        # L'organisme de l'importateur n'est plus imposé
        assert not CorOgSite.objects.filter(id_site=site_a, uuid_og=importer_org).exists()

    def test_import_accepts_several_organismes_first_is_principal(self, api_client):
        """« A ; B » : les deux sont rattachés, le premier est principal."""
        admin = SuperAdminFactory(id_organisme=OrganismeFactory())
        org_a = OrganismeFactory(nom_organisme='Gestionnaire Un')
        org_b = OrganismeFactory(nom_organisme='Gestionnaire Deux')
        api_client.force_authenticate(user=admin)

        sites = [{
            'row_index': 0,
            'mapped_data': {
                'nom_site': 'Site Cogere',
                'organisme': 'Gestionnaire Un ; Gestionnaire Deux',
            },
        }]
        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        site = Site.objects.get(nom_site='Site Cogere')
        assert CorOgSite.objects.get(id_site=site, uuid_og=org_a).principal is True
        assert CorOgSite.objects.get(id_site=site, uuid_og=org_b).principal is False

    def test_import_falls_back_to_importer_organisme(self, api_client):
        """Sans colonne organisme, le comportement historique est conservé."""
        org = OrganismeFactory()
        admin = SuperAdminFactory(id_organisme=org)
        api_client.force_authenticate(user=admin)

        sites = [{'row_index': 0, 'mapped_data': {'nom_site': 'Site Sans Org'}}]
        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        site = Site.objects.get(nom_site='Site Sans Org')
        assert CorOgSite.objects.filter(id_site=site, uuid_og=org, principal=True).exists()
        assert CorRoleSite.objects.filter(id_site=site, id_role=admin, referent=True).exists()

    def test_import_links_referent_from_file(self, api_client):
        """Le référent déclaré (email) devient référent, pas l'importateur."""
        admin = SuperAdminFactory(id_organisme=OrganismeFactory())
        referent = RoleFactory(email='Camille.Referente@test.fr')
        api_client.force_authenticate(user=admin)

        sites = [{
            'row_index': 0,
            'mapped_data': {'nom_site': 'Site Referent', 'referent': 'camille.referente@test.fr'},
        }]
        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        site = Site.objects.get(nom_site='Site Referent')
        assert CorRoleSite.objects.filter(
            id_site=site, id_role=referent, referent=True, referent_valid=True
        ).exists()
        assert not CorRoleSite.objects.filter(id_site=site, id_role=admin).exists()

    def test_admin_og_cannot_link_user_of_another_organisme(self, api_client):
        """Un admin d'organisme ne rattache que ses propres utilisateurs."""
        org = OrganismeFactory()
        other_org = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=org)
        outsider = RoleFactory(email='dehors@test.fr', id_organisme=other_org)
        api_client.force_authenticate(user=admin_og)

        sites = [{
            'row_index': 0,
            'mapped_data': {'nom_site': 'Site Hors Perimetre', 'referent': 'dehors@test.fr'},
        }]
        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        site = Site.objects.get(nom_site='Site Hors Perimetre')
        assert not CorRoleSite.objects.filter(id_site=site, id_role=outsider).exists()

    def test_deactivated_user_is_not_linked(self, api_client):
        """Un compte désactivé n'est pas rattaché au site."""
        admin = SuperAdminFactory(id_organisme=OrganismeFactory())
        inactive = RoleFactory(email='parti@test.fr', active=False)
        api_client.force_authenticate(user=admin)

        sites = [{
            'row_index': 0,
            'mapped_data': {'nom_site': 'Site Compte Ferme', 'referent': 'parti@test.fr'},
        }]
        response = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': sites, 'selected_indices': [0]},
            format='json',
        )

        assert response.status_code == status.HTTP_201_CREATED
        site = Site.objects.get(nom_site='Site Compte Ferme')
        assert not CorRoleSite.objects.filter(id_site=site, id_role=inactive).exists()
        # Repli : l'importateur reste référent pour ne pas laisser le site orphelin
        assert CorRoleSite.objects.filter(id_site=site, id_role=admin, referent=True).exists()

    def test_validation_warns_on_unknown_referent(self, api_client):
        """Utilisateur introuvable : avertissement, import non bloqué."""
        admin = SuperAdminFactory(id_organisme=OrganismeFactory())
        api_client.force_authenticate(user=admin)

        csv_file = _make_csv_file(
            ['nom', 'referent'],
            [['Site Sans Referent', 'inconnu@test.fr']],
        )
        response = api_client.post(
            '/api/users/sites/bulk_import_validate/',
            {'file': csv_file},
            format='multipart',
        )

        row = response.data['sites'][0]
        assert row['errors'] == []
        assert row['resolved_referents'] == []
        assert any('inconnu@test.fr' in w for w in row['warnings'])
