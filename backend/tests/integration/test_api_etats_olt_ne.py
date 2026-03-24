"""
Tests d'intégration pour l'API REST Objectifs Long Terme et Niveaux d'Exigence.
"""
import pytest
from rest_framework import status

from apps.plans.models_enjeux import Enjeu, ObjectifLongTerme, NiveauExigence
from tests.factories.enjeux import (
    EnjeuFactory, ObjectifLongTermeFactory, NiveauExigenceFactory,
    NomenclatureEnjeuFactory,
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)


@pytest.fixture
def olt_test_data(db):
    """Fixture providing test data for OLTs and niveaux d'exigence tests."""
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan OLT Test', statut='valide')
    CorSitePgFactory(plan_de_gestion=plan, site=site)

    super_admin = SuperAdminFactory()
    admin_og = AdminOrganismeFactory(id_organisme=organisme)
    referent = ReferentFactory(id_organisme=organisme)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan.referents.add(referent)
    user = RoleFactory()

    cat_enjeu = NomenclatureEnjeuFactory()
    enjeu = EnjeuFactory(
        id_pg=plan, id_categorie=cat_enjeu, libelle='Enjeu OLT Test',
        id_utilisateur_ajout=referent
    )
    olt1 = ObjectifLongTermeFactory(
        id_enjeu=enjeu, libelle='OLT Conservation',
        description='Maintenir les habitats humides',
        id_utilisateur_ajout=referent
    )
    olt2 = ObjectifLongTermeFactory(
        id_enjeu=enjeu, libelle='OLT Restauration',
        id_utilisateur_ajout=referent
    )
    ne1 = NiveauExigenceFactory(
        id_olt=olt1, libelle='NE Bon état',
        description='Surface minimale de 100 ha',
        id_utilisateur_ajout=referent
    )
    ne2 = NiveauExigenceFactory(
        id_olt=olt1, libelle='NE Très bon état',
        id_utilisateur_ajout=referent
    )

    return {
        'organisme': organisme,
        'site': site,
        'plan': plan,
        'super_admin': super_admin,
        'admin_og': admin_og,
        'referent': referent,
        'user': user,
        'enjeu': enjeu,
        'olt1': olt1,
        'olt2': olt2,
        'ne1': ne1,
        'ne2': ne2,
    }


# =============================================================================
# ObjectifLongTerme CRUD
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifLongTermeList:
    """Tests for GET /api/plans/objectifs-long-terme/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/objectifs-long-terme/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, olt_test_data):
        """Test super admin sees all OLTs."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.get('/api/plans/objectifs-long-terme/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_referent_sees_own(self, api_client, olt_test_data):
        """Test referent sees OLTs from their plans."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        response = api_client.get('/api/plans/objectifs-long-terme/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifLongTermeCreate:
    """Tests for POST /api/plans/objectifs-long-terme/"""

    def test_referent_creates(self, api_client, olt_test_data):
        """Test referent can create an OLT."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        response = api_client.post('/api/plans/objectifs-long-terme/', {
            'id_enjeu': olt_test_data['enjeu'].id_enjeu,
            'libelle': 'Nouvel OLT',
            'description': 'Description test OLT',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert ObjectifLongTerme.objects.filter(libelle='Nouvel OLT').exists()

    def test_non_referent_denied(self, api_client, olt_test_data):
        """Test non-referent cannot create."""
        api_client.force_authenticate(user=olt_test_data['user'])
        response = api_client.post('/api/plans/objectifs-long-terme/', {
            'id_enjeu': olt_test_data['enjeu'].id_enjeu,
            'libelle': 'Should Fail',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_minimal_fields(self, api_client, olt_test_data):
        """Test create with minimal fields."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.post('/api/plans/objectifs-long-terme/', {
            'id_enjeu': olt_test_data['enjeu'].id_enjeu,
            'libelle': 'OLT Minimal',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_with_description(self, api_client, olt_test_data):
        """Test create with optional description."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.post('/api/plans/objectifs-long-terme/', {
            'id_enjeu': olt_test_data['enjeu'].id_enjeu,
            'libelle': 'OLT Avec Description',
            'description': 'Description détaillée de l\'OLT',
        })
        assert response.status_code == status.HTTP_201_CREATED
        olt = ObjectifLongTerme.objects.get(libelle='OLT Avec Description')
        assert olt.description == 'Description détaillée de l\'OLT'

    def test_audit_fields_set(self, api_client, olt_test_data):
        """Test audit fields are set on create."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.post('/api/plans/objectifs-long-terme/', {
            'id_enjeu': olt_test_data['enjeu'].id_enjeu,
            'libelle': 'OLT Audit',
        })
        assert response.status_code == status.HTTP_201_CREATED
        olt = ObjectifLongTerme.objects.get(libelle='OLT Audit')
        assert olt.id_utilisateur_ajout == olt_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifLongTermeDetail:
    """Tests for GET /api/plans/objectifs-long-terme/{id}/"""

    def test_referent_gets_detail(self, api_client, olt_test_data):
        """Test referent can retrieve OLT detail."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.get(f'/api/plans/objectifs-long-terme/{olt_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['libelle'] == 'OLT Conservation'

    def test_detail_includes_niveaux(self, api_client, olt_test_data):
        """Test detail includes nested niveaux_exigence."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.get(f'/api/plans/objectifs-long-terme/{olt_id}/')
        assert 'niveaux_exigence' in response.data
        assert len(response.data['niveaux_exigence']) >= 2

    def test_nb_niveaux_exigence_correct(self, api_client, olt_test_data):
        """Test nb_niveaux_exigence is correct."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.get(f'/api/plans/objectifs-long-terme/{olt_id}/')
        assert response.data['nb_niveaux_exigence'] == 2

    def test_nonexistent_returns_404(self, api_client, olt_test_data):
        """Test nonexistent OLT returns 404."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.get('/api/plans/objectifs-long-terme/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_detail_includes_createur_nom(self, api_client, olt_test_data):
        """Test detail includes createur_nom."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.get(f'/api/plans/objectifs-long-terme/{olt_id}/')
        assert 'createur_nom' in response.data


@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifLongTermeUpdate:
    """Tests for PATCH /api/plans/objectifs-long-terme/{id}/"""

    def test_referent_updates(self, api_client, olt_test_data):
        """Test referent can update an OLT."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.patch(f'/api/plans/objectifs-long-terme/{olt_id}/', {
            'libelle': 'OLT Mis à Jour'
        })
        assert response.status_code == status.HTTP_200_OK
        olt_test_data['olt1'].refresh_from_db()
        assert olt_test_data['olt1'].libelle == 'OLT Mis à Jour'

    def test_patch_description(self, api_client, olt_test_data):
        """Test PATCH description only."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.patch(f'/api/plans/objectifs-long-terme/{olt_id}/', {
            'description': 'Nouvelle description OLT'
        })
        assert response.status_code == status.HTTP_200_OK
        olt_test_data['olt1'].refresh_from_db()
        assert olt_test_data['olt1'].description == 'Nouvelle description OLT'

    def test_audit_updated(self, api_client, olt_test_data):
        """Test audit fields updated on PATCH."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.patch(f'/api/plans/objectifs-long-terme/{olt_id}/', {
            'libelle': 'Updated Audit'
        })
        assert response.status_code == status.HTTP_200_OK
        olt_test_data['olt1'].refresh_from_db()
        assert olt_test_data['olt1'].id_utilisateur_maj == olt_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifLongTermeDelete:
    """Tests for DELETE /api/plans/objectifs-long-terme/{id}/"""

    def test_referent_deletes(self, api_client, olt_test_data):
        """Test referent can delete an OLT."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        olt_id = olt_test_data['olt2'].id_olt
        response = api_client.delete(f'/api/plans/objectifs-long-terme/{olt_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ObjectifLongTerme.objects.filter(id_olt=olt_id).exists()

    def test_non_referent_denied(self, api_client, olt_test_data):
        """Test non-referent cannot delete."""
        api_client.force_authenticate(user=olt_test_data['user'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.delete(f'/api/plans/objectifs-long-terme/{olt_id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cascade_ne_deleted(self, api_client, olt_test_data):
        """Test deleting OLT cascades to niveaux d'exigence."""
        olt_id = olt_test_data['olt1'].id_olt
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/objectifs-long-terme/{olt_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not NiveauExigence.objects.filter(id_olt_id=olt_id).exists()

    def test_enjeu_parent_intact(self, api_client, olt_test_data):
        """Test deleting OLT does NOT cascade to parent Enjeu."""
        enjeu_id = olt_test_data['enjeu'].id_enjeu
        olt_id = olt_test_data['olt2'].id_olt
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/objectifs-long-terme/{olt_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Enjeu.objects.filter(id_enjeu=enjeu_id).exists()

    def test_other_olt_intact(self, api_client, olt_test_data):
        """Test deleting OLT does not affect other OLTs under the same enjeu."""
        other_olt_id = olt_test_data['olt1'].id_olt
        olt_id = olt_test_data['olt2'].id_olt
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/objectifs-long-terme/{olt_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert ObjectifLongTerme.objects.filter(id_olt=other_olt_id).exists()


# =============================================================================
# ObjectifLongTerme by-enjeu endpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOltByEnjeuEndpoint:
    """Tests for GET /api/plans/objectifs-long-terme/by-enjeu/{enjeu_id}/"""

    def test_unauthenticated_returns_401(self, api_client, olt_test_data):
        """Test unauthenticated access returns 401."""
        enjeu_id = olt_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/objectifs-long-terme/by-enjeu/{enjeu_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_referent_gets_by_enjeu(self, api_client, olt_test_data):
        """Test referent can get OLTs by enjeu."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        enjeu_id = olt_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/objectifs-long-terme/by-enjeu/{enjeu_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['enjeu_id'] == enjeu_id

    def test_response_structure(self, api_client, olt_test_data):
        """Test response has correct structure."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        enjeu_id = olt_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/objectifs-long-terme/by-enjeu/{enjeu_id}/')
        assert 'enjeu_id' in response.data
        assert 'enjeu_libelle' in response.data
        assert 'objectifs_long_terme' in response.data
        assert 'total' in response.data

    def test_correct_count(self, api_client, olt_test_data):
        """Test enjeu returns correct OLT count."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        enjeu_id = olt_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/objectifs-long-terme/by-enjeu/{enjeu_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 2

    def test_nonexistent_enjeu_returns_404(self, api_client, olt_test_data):
        """Test nonexistent enjeu returns 404."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.get('/api/plans/objectifs-long-terme/by-enjeu/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_includes_createur_nom(self, api_client, olt_test_data):
        """Test OLTs include createur_nom."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        enjeu_id = olt_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/objectifs-long-terme/by-enjeu/{enjeu_id}/')
        for olt in response.data['objectifs_long_terme']:
            assert 'createur_nom' in olt


# =============================================================================
# NiveauExigence CRUD
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestNiveauExigenceList:
    """Tests for GET /api/plans/niveaux-exigence/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/niveaux-exigence/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, olt_test_data):
        """Test super admin sees all niveaux d'exigence."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.get('/api/plans/niveaux-exigence/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_referent_sees_own(self, api_client, olt_test_data):
        """Test referent sees niveaux d'exigence from their plans."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        response = api_client.get('/api/plans/niveaux-exigence/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
class TestNiveauExigenceCreate:
    """Tests for POST /api/plans/niveaux-exigence/"""

    def test_referent_creates(self, api_client, olt_test_data):
        """Test referent can create a niveau d'exigence."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        response = api_client.post('/api/plans/niveaux-exigence/', {
            'id_olt': olt_test_data['olt1'].id_olt,
            'libelle': 'Nouveau NE',
            'description': 'Description test NE',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert NiveauExigence.objects.filter(libelle='Nouveau NE').exists()

    def test_non_referent_denied(self, api_client, olt_test_data):
        """Test non-referent cannot create."""
        api_client.force_authenticate(user=olt_test_data['user'])
        response = api_client.post('/api/plans/niveaux-exigence/', {
            'id_olt': olt_test_data['olt1'].id_olt,
            'libelle': 'Should Fail',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_minimal_fields(self, api_client, olt_test_data):
        """Test create with minimal fields."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.post('/api/plans/niveaux-exigence/', {
            'id_olt': olt_test_data['olt1'].id_olt,
            'libelle': 'NE Minimal',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_with_description(self, api_client, olt_test_data):
        """Test create with optional description."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.post('/api/plans/niveaux-exigence/', {
            'id_olt': olt_test_data['olt1'].id_olt,
            'libelle': 'NE Avec Description',
            'description': 'Seuil de 50% de recouvrement végétal',
        })
        assert response.status_code == status.HTTP_201_CREATED
        ne = NiveauExigence.objects.get(libelle='NE Avec Description')
        assert ne.description == 'Seuil de 50% de recouvrement végétal'

    def test_audit_fields_set(self, api_client, olt_test_data):
        """Test audit fields are set on create."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.post('/api/plans/niveaux-exigence/', {
            'id_olt': olt_test_data['olt1'].id_olt,
            'libelle': 'NE Audit',
        })
        assert response.status_code == status.HTTP_201_CREATED
        ne = NiveauExigence.objects.get(libelle='NE Audit')
        assert ne.id_utilisateur_ajout == olt_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestNiveauExigenceDetail:
    """Tests for GET /api/plans/niveaux-exigence/{id}/"""

    def test_referent_gets_detail(self, api_client, olt_test_data):
        """Test referent can retrieve NE detail."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        ne_id = olt_test_data['ne1'].id_ne
        response = api_client.get(f'/api/plans/niveaux-exigence/{ne_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['libelle'] == 'NE Bon état'

    def test_detail_includes_createur_nom(self, api_client, olt_test_data):
        """Test detail includes createur_nom."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        ne_id = olt_test_data['ne1'].id_ne
        response = api_client.get(f'/api/plans/niveaux-exigence/{ne_id}/')
        assert 'createur_nom' in response.data

    def test_nonexistent_returns_404(self, api_client, olt_test_data):
        """Test nonexistent NE returns 404."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.get('/api/plans/niveaux-exigence/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.integration
class TestNiveauExigenceUpdate:
    """Tests for PATCH /api/plans/niveaux-exigence/{id}/"""

    def test_referent_updates(self, api_client, olt_test_data):
        """Test referent can update a NE."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        ne_id = olt_test_data['ne1'].id_ne
        response = api_client.patch(f'/api/plans/niveaux-exigence/{ne_id}/', {
            'libelle': 'NE Mis à Jour'
        })
        assert response.status_code == status.HTTP_200_OK
        olt_test_data['ne1'].refresh_from_db()
        assert olt_test_data['ne1'].libelle == 'NE Mis à Jour'

    def test_patch_description(self, api_client, olt_test_data):
        """Test PATCH description only."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        ne_id = olt_test_data['ne1'].id_ne
        response = api_client.patch(f'/api/plans/niveaux-exigence/{ne_id}/', {
            'description': 'Nouvelle description NE'
        })
        assert response.status_code == status.HTTP_200_OK
        olt_test_data['ne1'].refresh_from_db()
        assert olt_test_data['ne1'].description == 'Nouvelle description NE'

    def test_audit_updated(self, api_client, olt_test_data):
        """Test audit fields updated on PATCH."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        ne_id = olt_test_data['ne1'].id_ne
        response = api_client.patch(f'/api/plans/niveaux-exigence/{ne_id}/', {
            'libelle': 'Updated Audit'
        })
        assert response.status_code == status.HTTP_200_OK
        olt_test_data['ne1'].refresh_from_db()
        assert olt_test_data['ne1'].id_utilisateur_maj == olt_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestNiveauExigenceDelete:
    """Tests for DELETE /api/plans/niveaux-exigence/{id}/"""

    def test_referent_deletes(self, api_client, olt_test_data):
        """Test referent can delete a NE."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        ne_id = olt_test_data['ne2'].id_ne
        response = api_client.delete(f'/api/plans/niveaux-exigence/{ne_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not NiveauExigence.objects.filter(id_ne=ne_id).exists()

    def test_non_referent_denied(self, api_client, olt_test_data):
        """Test non-referent cannot delete."""
        api_client.force_authenticate(user=olt_test_data['user'])
        ne_id = olt_test_data['ne1'].id_ne
        response = api_client.delete(f'/api/plans/niveaux-exigence/{ne_id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_olt_parent_intact(self, api_client, olt_test_data):
        """Test deleting NE does not delete parent OLT."""
        olt_id = olt_test_data['olt1'].id_olt
        ne_id = olt_test_data['ne1'].id_ne
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/niveaux-exigence/{ne_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert ObjectifLongTerme.objects.filter(id_olt=olt_id).exists()

    def test_enjeu_grandparent_intact(self, api_client, olt_test_data):
        """Test deleting NE does not affect enjeu."""
        enjeu_id = olt_test_data['enjeu'].id_enjeu
        ne_id = olt_test_data['ne1'].id_ne
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/niveaux-exigence/{ne_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Enjeu.objects.filter(id_enjeu=enjeu_id).exists()


# =============================================================================
# NiveauExigence by-olt endpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestNeByOltEndpoint:
    """Tests for GET /api/plans/niveaux-exigence/by-olt/{olt_id}/"""

    def test_unauthenticated_returns_401(self, api_client, olt_test_data):
        """Test unauthenticated access returns 401."""
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.get(f'/api/plans/niveaux-exigence/by-olt/{olt_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_referent_gets_by_olt(self, api_client, olt_test_data):
        """Test referent can get NEs by OLT."""
        api_client.force_authenticate(user=olt_test_data['referent'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.get(f'/api/plans/niveaux-exigence/by-olt/{olt_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['olt_id'] == olt_id

    def test_response_structure(self, api_client, olt_test_data):
        """Test response has correct structure."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.get(f'/api/plans/niveaux-exigence/by-olt/{olt_id}/')
        assert 'olt_id' in response.data
        assert 'olt_libelle' in response.data
        assert 'niveaux_exigence' in response.data
        assert 'total' in response.data

    def test_empty_olt_returns_empty_list(self, api_client, olt_test_data):
        """Test OLT without NEs returns empty list."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        olt_id = olt_test_data['olt2'].id_olt
        response = api_client.get(f'/api/plans/niveaux-exigence/by-olt/{olt_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 0

    def test_nonexistent_olt_returns_404(self, api_client, olt_test_data):
        """Test nonexistent OLT returns 404."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        response = api_client.get('/api/plans/niveaux-exigence/by-olt/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_includes_createur_nom(self, api_client, olt_test_data):
        """Test NEs include createur_nom."""
        api_client.force_authenticate(user=olt_test_data['super_admin'])
        olt_id = olt_test_data['olt1'].id_olt
        response = api_client.get(f'/api/plans/niveaux-exigence/by-olt/{olt_id}/')
        for ne in response.data['niveaux_exigence']:
            assert 'createur_nom' in ne
