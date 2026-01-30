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
