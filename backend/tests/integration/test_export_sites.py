"""
Export GeoJSON des sites, réimportable par l'import en masse.

Le fichier doit faire passer un site d'une instance à une autre : on vérifie
donc l'aller-retour complet (export → validation → création) et qu'il ne
contient rien de propre à l'instance d'origine (identifiants, personnes).
"""
import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient

from apps.users.models import CorOgSite, CorRoleSite, Site
from tests.factories.core import NomenclatureFactory, TypeNomenclatureFactory
from tests.factories.users import (
    CorOgSiteFactory, OrganismeFactory, RoleFactory, SiteFactory, SuperAdminFactory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def type_rnn():
    type_site = TypeNomenclatureFactory(mnemonique='Espace naturel')
    return NomenclatureFactory(id_type=type_site, mnemonique='RNN_EXPORT', label='Réserve naturelle nationale')


def _telecharger(response):
    assert response.status_code == status.HTTP_200_OK
    assert 'attachment' in response['Content-Disposition']
    return json.loads(response.content)


@pytest.mark.django_db
@pytest.mark.integration
class TestExportSite:

    def test_proprietes_portables_sans_identifiant_ni_personne(self, api_client, type_rnn):
        admin = SuperAdminFactory()
        site = SiteFactory(nom_site='Casse de la Belle Henriette', id_inpn='FR3600999', id_type_site=type_rnn)
        CorOgSiteFactory(id_site=site, uuid_og=OrganismeFactory(nom_organisme='OFB'))
        CorOgSiteFactory(id_site=site, uuid_og=OrganismeFactory(nom_organisme='LPO'), principal=True)
        CorRoleSite.objects.create(id_site=site, id_role=RoleFactory(email='camille@lpo.fr'), referent=True)

        api_client.force_authenticate(user=admin)
        data = _telecharger(api_client.get(f'/api/users/sites/{site.slug}/export-geojson/'))

        assert data['type'] == 'FeatureCollection'
        feature = data['features'][0]
        assert feature['geometry']['type'] == 'MultiPolygon'
        props = feature['properties']
        assert props['nom_site'] == 'Casse de la Belle Henriette'
        assert props['id_inpn'] == 'FR3600999'
        assert props['type_site'] == 'RNN_EXPORT'
        # Principal en tête, au format multi-valeurs de l'import
        assert props['organisme'] == 'LPO ; OFB'
        assert 'id' not in feature
        contenu = json.dumps(data)
        for interdit in ('id_site', 'slug', 'id_organisme', 'users_assignes', 'camille@lpo.fr'):
            assert interdit not in contenu

    def test_site_hors_perimetre(self, api_client):
        site = SiteFactory()
        api_client.force_authenticate(user=RoleFactory())
        response = api_client.get(f'/api/users/sites/{site.slug}/export-geojson/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.integration
class TestExportSitesListe:

    def test_borne_au_perimetre_et_aux_ids(self, api_client):
        user = RoleFactory()
        visible_a = SiteFactory(nom_site='Visible A')
        visible_b = SiteFactory(nom_site='Visible B')
        SiteFactory(nom_site='Invisible')
        for site in (visible_a, visible_b):
            CorRoleSite.objects.create(id_site=site, id_role=user)

        api_client.force_authenticate(user=user)
        data = _telecharger(api_client.get('/api/users/sites/export-geojson/'))
        assert {f['properties']['nom_site'] for f in data['features']} == {'Visible A', 'Visible B'}

        data = _telecharger(api_client.get(f'/api/users/sites/export-geojson/?ids={visible_a.id_site}'))
        assert [f['properties']['nom_site'] for f in data['features']] == ['Visible A']

    def test_ids_invalides(self, api_client):
        api_client.force_authenticate(user=SuperAdminFactory())
        response = api_client.get('/api/users/sites/export-geojson/?ids=abc')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
@pytest.mark.integration
class TestExportReimport:
    """Le fichier exporté passe tel quel dans l'import en masse."""

    def test_aller_retour(self, api_client, type_rnn):
        org = OrganismeFactory(nom_organisme='LPO')
        admin = SuperAdminFactory(id_organisme=org)
        site = SiteFactory(
            nom_site='Sept-Îles', id_inpn='FR3600888', id_type_site=type_rnn,
            surf_off=280.0, marin=True,
        )
        CorOgSiteFactory(id_site=site, uuid_og=org, principal=True)
        api_client.force_authenticate(user=admin)

        contenu = api_client.get(f'/api/users/sites/{site.slug}/export-geojson/').content
        geom_origine = site.geom
        site.delete()  # l'instance d'arrivée ne connaît pas le site

        fichier = SimpleUploadedFile('sites.geojson', contenu, content_type='application/geo+json')
        validation = api_client.post('/api/users/sites/bulk_import_validate/', {'file': fichier}, format='multipart')
        assert validation.status_code == status.HTTP_200_OK
        mapping = validation.data['suggested_mapping']
        for champ in ('nom_site', 'id_inpn', 'id_local', 'surf_off', 'marin', 'outre_mer', 'organisme'):
            assert mapping[champ] == champ
        assert mapping['type_site'] == 'type_site_id'
        ligne = validation.data['sites'][0]
        assert ligne['errors'] == []

        execution = api_client.post(
            '/api/users/sites/bulk_import_execute/',
            {'sites': validation.data['sites'], 'selected_indices': [0]},
            format='json',
        )
        assert execution.status_code == status.HTTP_201_CREATED

        recree = Site.objects.get(id_inpn='FR3600888')
        assert recree.nom_site == 'Sept-Îles'
        assert recree.id_type_site == type_rnn
        assert recree.surf_off == 280.0
        assert recree.marin is True
        assert recree.geom.equals_exact(geom_origine, tolerance=1e-9)
        assert CorOgSite.objects.filter(id_site=recree, uuid_og=org).exists()
