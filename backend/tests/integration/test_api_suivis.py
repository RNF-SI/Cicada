"""
Tests d'intégration pour l'API REST Suivis/Inventaires (standalone).
"""
import pytest
from rest_framework import status

from apps.plans.models_operations import SuiviInventaire, Protocole
from tests.factories.enjeux import (
    SuiviInventaireFactory, ProtocoleFactory,
)
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory


@pytest.fixture
def suivi_test_data(db):
    """Fixture providing common test data for suivis tests."""
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan Test Suivis', statut='valide')
    CorSitePgFactory(plan_de_gestion=plan, site=site)

    # Users
    super_admin = SuperAdminFactory()
    admin_og = AdminOrganismeFactory(id_organisme=organisme)
    referent = ReferentFactory(id_organisme=organisme)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan.referents.add(referent)
    user = RoleFactory()

    # Suivis/Inventaires
    suivi1 = SuiviInventaireFactory(
        intitule='Suivi floristique prairie humide',
        actif=True,
        annee_lancement_suivi=2020,
        annee_fin_suivi=None,
        objectif_principal='conservation',
        cibles_principales='flore',
        commentaires='Premier suivi de test',
        id_utilisateur_ajout=referent,
    )
    suivi2 = SuiviInventaireFactory(
        intitule='Inventaire avifaune nicheuse',
        actif=True,
        annee_lancement_suivi=2018,
        annee_fin_suivi=2023,
        objectif_principal='connaissance',
        cibles_principales='faune',
        commentaires='Deuxième suivi de test',
        id_utilisateur_ajout=referent,
    )
    suivi3 = SuiviInventaireFactory(
        intitule='Suivi inactif ancien',
        actif=False,
        annee_lancement_suivi=2010,
        annee_fin_suivi=2015,
        id_utilisateur_ajout=referent,
    )

    return {
        'organisme': organisme,
        'site': site,
        'plan': plan,
        'super_admin': super_admin,
        'admin_og': admin_og,
        'referent': referent,
        'user': user,
        'suivi1': suivi1,
        'suivi2': suivi2,
        'suivi3': suivi3,
    }


# =============================================================================
# TestSuivisListEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisListEndpoint:
    """Tests for GET /api/inventaires/suivis/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/inventaires/suivis/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, suivi_test_data):
        """Test super admin can see all suivis."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 3

    def test_filter_by_actif(self, api_client, suivi_test_data):
        """Test filtering by actif=true shows only active suivis."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/?actif=true')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['actif'] is True

    def test_filter_by_inactif(self, api_client, suivi_test_data):
        """Test filtering by actif=false shows only inactive suivis."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/?actif=false')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['actif'] is False

    def test_search_by_intitule(self, api_client, suivi_test_data):
        """Test search filters by intitule."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/?search=floristique')
        assert response.status_code == status.HTTP_200_OK
        intitules = [s['intitule'] for s in response.data['results']]
        assert 'Suivi floristique prairie humide' in intitules

    def test_pagination_works(self, api_client, suivi_test_data):
        """Test pagination is present in response."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data
        assert 'pagination' in response.data
        assert 'count' in response.data['pagination']

    def test_list_includes_expected_fields(self, api_client, suivi_test_data):
        """Test list response includes expected fields."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get('/api/inventaires/suivis/')
        assert response.status_code == status.HTTP_200_OK
        if response.data['results']:
            item = response.data['results'][0]
            assert 'intitule' in item
            assert 'actif' in item
            assert 'nb_operations' in item
            assert 'annee_lancement_suivi' in item


# =============================================================================
# TestSuivisCreateEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisCreateEndpoint:
    """Tests for POST /api/inventaires/suivis/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated create returns 401."""
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Nouveau suivi',
        }, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_creates_suivi(self, api_client, suivi_test_data):
        """Test super admin can create a suivi."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Nouveau suivi SA',
            'objectif_principal': 'surveillance',
            'cibles_principales': 'habitat',
            'annee_lancement_suivi': 2025,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert SuiviInventaire.objects.filter(intitule='Nouveau suivi SA').exists()

    def test_create_with_nested_protocole(self, api_client, suivi_test_data):
        """Test creating suivi with nested protocole."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Suivi avec protocole',
            'objectif_principal': 'conservation',
            'cibles_principales': 'flore',
            'protocole': {
                'protocole_dans_campanule': True,
                'protocole_campanule_nom': 'Proto Test',
                'nom_protocole': '',
                'description_protocole': 'Description du protocole',
            },
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        suivi = SuiviInventaire.objects.get(intitule='Suivi avec protocole')
        assert suivi.id_protocole is not None
        assert suivi.id_protocole.protocole_campanule_nom == 'Proto Test'

    def test_create_with_minimal_fields(self, api_client, suivi_test_data):
        """Test create with only intitule."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Suivi Minimal',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_audit_field_set_on_create(self, api_client, suivi_test_data):
        """Test id_utilisateur_ajout is set on create."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.post('/api/inventaires/suivis/', {
            'intitule': 'Suivi Audit',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        suivi = SuiviInventaire.objects.get(intitule='Suivi Audit')
        assert suivi.id_utilisateur_ajout == suivi_test_data['super_admin']


# =============================================================================
# TestSuivisDetailEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisDetailEndpoint:
    """Tests for GET /api/inventaires/suivis/{id}/"""

    def test_unauthenticated_returns_401(self, api_client, suivi_test_data):
        """Test unauthenticated detail returns 401."""
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.get(f'/api/inventaires/suivis/{suivi_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_gets_detail(self, api_client, suivi_test_data):
        """Test super admin can get detail of a suivi."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.get(f'/api/inventaires/suivis/{suivi_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['intitule'] == 'Suivi floristique prairie humide'
        assert 'protocole' in response.data
        assert 'nb_operations' in response.data
        assert 'createur_nom' in response.data

    def test_detail_with_protocole(self, api_client, suivi_test_data):
        """Test detail includes nested protocole when present."""
        # Create a suivi with protocole
        protocole = ProtocoleFactory(
            protocole_dans_campanule=True,
            protocole_campanule_nom='Proto Detail',
            id_utilisateur_ajout=suivi_test_data['referent'],
        )
        suivi_with_proto = SuiviInventaireFactory(
            intitule='Suivi avec proto detail',
            id_protocole=protocole,
            id_utilisateur_ajout=suivi_test_data['referent'],
        )

        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        response = api_client.get(f'/api/inventaires/suivis/{suivi_with_proto.id_suivi_inventaire}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['protocole'] is not None
        assert response.data['protocole']['protocole_campanule_nom'] == 'Proto Detail'


# =============================================================================
# TestSuivisUpdateEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisUpdateEndpoint:
    """Tests for PATCH /api/inventaires/suivis/{id}/"""

    def test_super_admin_updates_suivi(self, api_client, suivi_test_data):
        """Test super admin can update a suivi."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.patch(f'/api/inventaires/suivis/{suivi_id}/', {
            'intitule': 'Suivi modifié',
            'commentaires': 'Commentaire mis à jour',
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        suivi_test_data['suivi1'].refresh_from_db()
        assert suivi_test_data['suivi1'].intitule == 'Suivi modifié'
        assert suivi_test_data['suivi1'].commentaires == 'Commentaire mis à jour'

    def test_update_with_nested_protocole(self, api_client, suivi_test_data):
        """Test updating suivi with nested protocole creation."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.patch(f'/api/inventaires/suivis/{suivi_id}/', {
            'protocole': {
                'protocole_dans_campanule': False,
                'nom_protocole': 'Protocole custom',
            },
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        suivi_test_data['suivi1'].refresh_from_db()
        assert suivi_test_data['suivi1'].id_protocole is not None

    def test_audit_field_set_on_update(self, api_client, suivi_test_data):
        """Test id_utilisateur_maj is set on update."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.patch(f'/api/inventaires/suivis/{suivi_id}/', {
            'intitule': 'Suivi audit update',
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        suivi_test_data['suivi1'].refresh_from_db()
        assert suivi_test_data['suivi1'].id_utilisateur_maj == suivi_test_data['super_admin']


# =============================================================================
# TestSuivisDeleteEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestSuivisDeleteEndpoint:
    """Tests for DELETE /api/inventaires/suivis/{id}/"""

    def test_unauthenticated_returns_401(self, api_client, suivi_test_data):
        """Test unauthenticated delete returns 401."""
        suivi_id = suivi_test_data['suivi1'].id_suivi_inventaire
        response = api_client.delete(f'/api/inventaires/suivis/{suivi_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_deletes_suivi(self, api_client, suivi_test_data):
        """Test super admin can delete a suivi."""
        api_client.force_authenticate(user=suivi_test_data['super_admin'])
        suivi_id = suivi_test_data['suivi3'].id_suivi_inventaire
        response = api_client.delete(f'/api/inventaires/suivis/{suivi_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not SuiviInventaire.objects.filter(id_suivi_inventaire=suivi_id).exists()
