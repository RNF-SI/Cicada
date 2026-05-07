"""
Tests d'intégration pour l'API REST Facteurs d'Influence et Pressions.
"""
import pytest
from rest_framework import status

from apps.plans.models_enjeux import FacteurInfluence, Pression
from tests.factories.enjeux import (
    EnjeuFactory, FacteurInfluenceFactory, PressionFactory,
    NomenclatureEnjeuFactory,
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)


@pytest.fixture
def facteur_test_data(db):
    """Fixture providing test data for facteurs and pressions tests."""
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan Facteurs Test', statut='draft')
    CorSitePgFactory(plan_de_gestion=plan, site=site)

    super_admin = SuperAdminFactory()
    admin_og = AdminOrganismeFactory(id_organisme=organisme)
    referent = ReferentFactory(id_organisme=organisme)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan.referents.add(referent)
    user = RoleFactory()

    cat_enjeu = NomenclatureEnjeuFactory()
    enjeu = EnjeuFactory(
        id_pg=plan, id_categorie=cat_enjeu, libelle='Enjeu Principal',
        id_utilisateur_ajout=referent
    )
    facteur1 = FacteurInfluenceFactory(
        id_enjeu=enjeu, libelle='Facteur Climat',
        description='Impact du changement climatique',
        id_utilisateur_ajout=referent
    )
    facteur2 = FacteurInfluenceFactory(
        id_enjeu=enjeu, libelle='Facteur Urbanisation',
        id_utilisateur_ajout=referent
    )
    pression1 = PressionFactory(
        id_facteur_influence=facteur1, libelle='Sécheresse',
        id_utilisateur_ajout=referent
    )
    pression2 = PressionFactory(
        id_facteur_influence=facteur1, libelle='Inondations',
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
        'facteur1': facteur1,
        'facteur2': facteur2,
        'pression1': pression1,
        'pression2': pression2,
    }


# =============================================================================
# TestFacteurInfluenceCRUD
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestFacteurInfluenceList:
    """Tests for GET /api/plans/facteurs-influence/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/facteurs-influence/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, facteur_test_data):
        """Test super admin can see all facteurs."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.get('/api/plans/facteurs-influence/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_referent_sees_own(self, api_client, facteur_test_data):
        """Test referent sees facteurs from their plans."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        response = api_client.get('/api/plans/facteurs-influence/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2


@pytest.mark.django_db
@pytest.mark.integration
class TestFacteurInfluenceCreate:
    """Tests for POST /api/plans/facteurs-influence/"""

    def test_referent_creates(self, api_client, facteur_test_data):
        """Test referent can create a facteur d'influence."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        response = api_client.post('/api/plans/facteurs-influence/', {
            'id_enjeu': facteur_test_data['enjeu'].id_enjeu,
            'libelle': 'Nouveau Facteur',
            'description': 'Description test',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert FacteurInfluence.objects.filter(libelle='Nouveau Facteur').exists()

    def test_non_referent_denied(self, api_client, facteur_test_data):
        """Test non-referent cannot create."""
        api_client.force_authenticate(user=facteur_test_data['user'])
        response = api_client.post('/api/plans/facteurs-influence/', {
            'id_enjeu': facteur_test_data['enjeu'].id_enjeu,
            'libelle': 'Should Fail',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_minimal_fields(self, api_client, facteur_test_data):
        """Test create with minimal fields."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.post('/api/plans/facteurs-influence/', {
            'id_enjeu': facteur_test_data['enjeu'].id_enjeu,
            'libelle': 'Facteur Minimal',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_with_description(self, api_client, facteur_test_data):
        """Test create with optional description."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.post('/api/plans/facteurs-influence/', {
            'id_enjeu': facteur_test_data['enjeu'].id_enjeu,
            'libelle': 'Facteur Avec Description',
            'description': 'Description détaillée du facteur',
        })
        assert response.status_code == status.HTTP_201_CREATED
        facteur = FacteurInfluence.objects.get(libelle='Facteur Avec Description')
        assert facteur.description == 'Description détaillée du facteur'

    def test_audit_fields_set(self, api_client, facteur_test_data):
        """Test audit fields are set on create."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.post('/api/plans/facteurs-influence/', {
            'id_enjeu': facteur_test_data['enjeu'].id_enjeu,
            'libelle': 'Facteur Audit',
        })
        assert response.status_code == status.HTTP_201_CREATED
        facteur = FacteurInfluence.objects.get(libelle='Facteur Audit')
        assert facteur.id_utilisateur_ajout == facteur_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestFacteurInfluenceDetail:
    """Tests for GET /api/plans/facteurs-influence/{id}/"""

    def test_referent_gets_detail(self, api_client, facteur_test_data):
        """Test referent can retrieve facteur detail."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.get(f'/api/plans/facteurs-influence/{facteur_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['libelle'] == 'Facteur Climat'

    def test_detail_includes_pressions(self, api_client, facteur_test_data):
        """Test detail includes nested pressions."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.get(f'/api/plans/facteurs-influence/{facteur_id}/')
        assert 'pressions' in response.data
        assert len(response.data['pressions']) >= 2

    def test_nb_pressions_correct(self, api_client, facteur_test_data):
        """Test nb_pressions is correct."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.get(f'/api/plans/facteurs-influence/{facteur_id}/')
        assert response.data['nb_pressions'] == 2

    def test_nonexistent_returns_404(self, api_client, facteur_test_data):
        """Test nonexistent facteur returns 404."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.get('/api/plans/facteurs-influence/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.integration
class TestFacteurInfluenceUpdate:
    """Tests for PATCH /api/plans/facteurs-influence/{id}/"""

    def test_referent_updates(self, api_client, facteur_test_data):
        """Test referent can update a facteur."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.patch(f'/api/plans/facteurs-influence/{facteur_id}/', {
            'libelle': 'Facteur Mis à Jour'
        })
        assert response.status_code == status.HTTP_200_OK
        facteur_test_data['facteur1'].refresh_from_db()
        assert facteur_test_data['facteur1'].libelle == 'Facteur Mis à Jour'

    def test_patch_description(self, api_client, facteur_test_data):
        """Test PATCH description only."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.patch(f'/api/plans/facteurs-influence/{facteur_id}/', {
            'description': 'Nouvelle description'
        })
        assert response.status_code == status.HTTP_200_OK
        facteur_test_data['facteur1'].refresh_from_db()
        assert facteur_test_data['facteur1'].description == 'Nouvelle description'

    def test_audit_updated(self, api_client, facteur_test_data):
        """Test audit fields updated on PATCH."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.patch(f'/api/plans/facteurs-influence/{facteur_id}/', {
            'libelle': 'Updated Audit'
        })
        assert response.status_code == status.HTTP_200_OK
        facteur_test_data['facteur1'].refresh_from_db()
        assert facteur_test_data['facteur1'].id_utilisateur_maj == facteur_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestFacteurInfluenceDelete:
    """Tests for DELETE /api/plans/facteurs-influence/{id}/"""

    def test_referent_deletes(self, api_client, facteur_test_data):
        """Test referent can delete a facteur."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        facteur_id = facteur_test_data['facteur2'].id_facteur_influence
        response = api_client.delete(f'/api/plans/facteurs-influence/{facteur_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not FacteurInfluence.objects.filter(id_facteur_influence=facteur_id).exists()

    def test_non_referent_denied(self, api_client, facteur_test_data):
        """Test non-referent cannot delete."""
        api_client.force_authenticate(user=facteur_test_data['user'])
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.delete(f'/api/plans/facteurs-influence/{facteur_id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cascade_pressions_deleted(self, api_client, facteur_test_data):
        """Test deleting facteur cascades to pressions."""
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/facteurs-influence/{facteur_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Pression.objects.filter(id_facteur_influence_id=facteur_id).exists()

    def test_enjeu_parent_intact(self, api_client, facteur_test_data):
        """Test deleting facteur does not delete parent enjeu."""
        enjeu_id = facteur_test_data['enjeu'].id_enjeu
        facteur_id = facteur_test_data['facteur2'].id_facteur_influence
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/facteurs-influence/{facteur_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        from apps.plans.models_enjeux import Enjeu
        assert Enjeu.objects.filter(id_enjeu=enjeu_id).exists()


# =============================================================================
# TestFacteurByEnjeuEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestFacteurByEnjeuEndpoint:
    """Tests for GET /api/plans/facteurs-influence/by-enjeu/{enjeu_id}/"""

    def test_unauthenticated_returns_401(self, api_client, facteur_test_data):
        """Test unauthenticated access returns 401."""
        enjeu_id = facteur_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/facteurs-influence/by-enjeu/{enjeu_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_referent_gets_by_enjeu(self, api_client, facteur_test_data):
        """Test referent can get facteurs by enjeu."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        enjeu_id = facteur_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/facteurs-influence/by-enjeu/{enjeu_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['enjeu_id'] == enjeu_id

    def test_response_structure(self, api_client, facteur_test_data):
        """Test response has correct structure."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        enjeu_id = facteur_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/facteurs-influence/by-enjeu/{enjeu_id}/')
        assert 'enjeu_id' in response.data
        assert 'enjeu_libelle' in response.data
        assert 'facteurs_influence' in response.data
        assert 'total' in response.data

    def test_includes_pressions(self, api_client, facteur_test_data):
        """Test facteurs include nested pressions."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        enjeu_id = facteur_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/facteurs-influence/by-enjeu/{enjeu_id}/')
        facteurs = response.data['facteurs_influence']
        facteur_climat = next(
            (f for f in facteurs if f['libelle'] == 'Facteur Climat'), None
        )
        assert facteur_climat is not None
        assert 'pressions' in facteur_climat

    def test_nonexistent_enjeu_returns_404(self, api_client, facteur_test_data):
        """Test nonexistent enjeu returns 404."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.get('/api/plans/facteurs-influence/by-enjeu/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_empty_enjeu_returns_empty_list(self, api_client, facteur_test_data):
        """Test enjeu without facteurs returns empty list."""
        empty_enjeu = EnjeuFactory(
            id_pg=facteur_test_data['plan'],
            id_utilisateur_ajout=facteur_test_data['referent']
        )
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.get(f'/api/plans/facteurs-influence/by-enjeu/{empty_enjeu.id_enjeu}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 0
        assert len(response.data['facteurs_influence']) == 0


# =============================================================================
# TestPressionCRUD
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPressionList:
    """Tests for GET /api/plans/pressions/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/pressions/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, facteur_test_data):
        """Test super admin sees all pressions."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.get('/api/plans/pressions/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_referent_sees_own(self, api_client, facteur_test_data):
        """Test referent sees pressions from their plans."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        response = api_client.get('/api/plans/pressions/')
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
@pytest.mark.integration
class TestPressionCreate:
    """Tests for POST /api/plans/pressions/"""

    def test_referent_creates(self, api_client, facteur_test_data):
        """Test referent can create a pression."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        response = api_client.post('/api/plans/pressions/', {
            'id_facteur_influence': facteur_test_data['facteur1'].id_facteur_influence,
            'libelle': 'Nouvelle Pression',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Pression.objects.filter(libelle='Nouvelle Pression').exists()

    def test_non_referent_denied(self, api_client, facteur_test_data):
        """Test non-referent cannot create."""
        api_client.force_authenticate(user=facteur_test_data['user'])
        response = api_client.post('/api/plans/pressions/', {
            'id_facteur_influence': facteur_test_data['facteur1'].id_facteur_influence,
            'libelle': 'Should Fail',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_minimal_fields(self, api_client, facteur_test_data):
        """Test create with minimal fields."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.post('/api/plans/pressions/', {
            'id_facteur_influence': facteur_test_data['facteur1'].id_facteur_influence,
            'libelle': 'Pression Minimale',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_with_description_and_pressref(self, api_client, facteur_test_data):
        """Test create with description and id_pressref."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.post('/api/plans/pressions/', {
            'id_facteur_influence': facteur_test_data['facteur1'].id_facteur_influence,
            'libelle': 'Pression Complète',
            'description': 'Description détaillée',
            'id_pressref': 'PRESS_REF_001',
        })
        assert response.status_code == status.HTTP_201_CREATED
        pression = Pression.objects.get(libelle='Pression Complète')
        assert pression.description == 'Description détaillée'
        assert pression.id_pressref == 'PRESS_REF_001'

    def test_audit_fields_set(self, api_client, facteur_test_data):
        """Test audit fields are set on create."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.post('/api/plans/pressions/', {
            'id_facteur_influence': facteur_test_data['facteur1'].id_facteur_influence,
            'libelle': 'Pression Audit',
        })
        assert response.status_code == status.HTTP_201_CREATED
        pression = Pression.objects.get(libelle='Pression Audit')
        assert pression.id_utilisateur_ajout == facteur_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestPressionDetail:
    """Tests for GET /api/plans/pressions/{id}/"""

    def test_referent_gets_detail(self, api_client, facteur_test_data):
        """Test referent can retrieve pression detail."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        pression_id = facteur_test_data['pression1'].id_pression
        response = api_client.get(f'/api/plans/pressions/{pression_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['libelle'] == 'Sécheresse'

    def test_detail_includes_createur_nom(self, api_client, facteur_test_data):
        """Test detail includes createur_nom."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        pression_id = facteur_test_data['pression1'].id_pression
        response = api_client.get(f'/api/plans/pressions/{pression_id}/')
        assert 'createur_nom' in response.data

    def test_nonexistent_returns_404(self, api_client, facteur_test_data):
        """Test nonexistent pression returns 404."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.get('/api/plans/pressions/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.integration
class TestPressionUpdate:
    """Tests for PATCH /api/plans/pressions/{id}/"""

    def test_referent_updates(self, api_client, facteur_test_data):
        """Test referent can update a pression."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        pression_id = facteur_test_data['pression1'].id_pression
        response = api_client.patch(f'/api/plans/pressions/{pression_id}/', {
            'libelle': 'Sécheresse Mise à Jour'
        })
        assert response.status_code == status.HTTP_200_OK
        facteur_test_data['pression1'].refresh_from_db()
        assert facteur_test_data['pression1'].libelle == 'Sécheresse Mise à Jour'

    def test_patch_description(self, api_client, facteur_test_data):
        """Test PATCH description only."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        pression_id = facteur_test_data['pression1'].id_pression
        response = api_client.patch(f'/api/plans/pressions/{pression_id}/', {
            'description': 'Nouvelle description pression'
        })
        assert response.status_code == status.HTTP_200_OK
        facteur_test_data['pression1'].refresh_from_db()
        assert facteur_test_data['pression1'].description == 'Nouvelle description pression'

    def test_audit_updated(self, api_client, facteur_test_data):
        """Test audit fields updated on PATCH."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        pression_id = facteur_test_data['pression1'].id_pression
        response = api_client.patch(f'/api/plans/pressions/{pression_id}/', {
            'libelle': 'Updated Audit'
        })
        assert response.status_code == status.HTTP_200_OK
        facteur_test_data['pression1'].refresh_from_db()
        assert facteur_test_data['pression1'].id_utilisateur_maj == facteur_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestPressionDelete:
    """Tests for DELETE /api/plans/pressions/{id}/"""

    def test_referent_deletes(self, api_client, facteur_test_data):
        """Test referent can delete a pression."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        pression_id = facteur_test_data['pression2'].id_pression
        response = api_client.delete(f'/api/plans/pressions/{pression_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Pression.objects.filter(id_pression=pression_id).exists()

    def test_non_referent_denied(self, api_client, facteur_test_data):
        """Test non-referent cannot delete."""
        api_client.force_authenticate(user=facteur_test_data['user'])
        pression_id = facteur_test_data['pression1'].id_pression
        response = api_client.delete(f'/api/plans/pressions/{pression_id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_facteur_parent_intact(self, api_client, facteur_test_data):
        """Test deleting pression does not delete parent facteur."""
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        pression_id = facteur_test_data['pression1'].id_pression
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/pressions/{pression_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert FacteurInfluence.objects.filter(id_facteur_influence=facteur_id).exists()

    def test_enjeu_grandparent_intact(self, api_client, facteur_test_data):
        """Test deleting pression does not affect enjeu."""
        enjeu_id = facteur_test_data['enjeu'].id_enjeu
        pression_id = facteur_test_data['pression1'].id_pression
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/pressions/{pression_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        from apps.plans.models_enjeux import Enjeu
        assert Enjeu.objects.filter(id_enjeu=enjeu_id).exists()


# =============================================================================
# TestPressionByFacteurEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestPressionByFacteurEndpoint:
    """Tests for GET /api/plans/pressions/by-facteur/{facteur_id}/"""

    def test_unauthenticated_returns_401(self, api_client, facteur_test_data):
        """Test unauthenticated access returns 401."""
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.get(f'/api/plans/pressions/by-facteur/{facteur_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_referent_gets_by_facteur(self, api_client, facteur_test_data):
        """Test referent can get pressions by facteur."""
        api_client.force_authenticate(user=facteur_test_data['referent'])
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.get(f'/api/plans/pressions/by-facteur/{facteur_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['facteur_id'] == facteur_id

    def test_response_structure(self, api_client, facteur_test_data):
        """Test response has correct structure."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.get(f'/api/plans/pressions/by-facteur/{facteur_id}/')
        assert 'facteur_id' in response.data
        assert 'facteur_libelle' in response.data
        assert 'pressions' in response.data
        assert 'total' in response.data

    def test_empty_facteur_returns_empty_list(self, api_client, facteur_test_data):
        """Test facteur without pressions returns empty list."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        facteur_id = facteur_test_data['facteur2'].id_facteur_influence
        response = api_client.get(f'/api/plans/pressions/by-facteur/{facteur_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 0

    def test_nonexistent_facteur_returns_404(self, api_client, facteur_test_data):
        """Test nonexistent facteur returns 404."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        response = api_client.get('/api/plans/pressions/by-facteur/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_includes_createur_nom(self, api_client, facteur_test_data):
        """Test pressions include createur_nom."""
        api_client.force_authenticate(user=facteur_test_data['super_admin'])
        facteur_id = facteur_test_data['facteur1'].id_facteur_influence
        response = api_client.get(f'/api/plans/pressions/by-facteur/{facteur_id}/')
        for pression in response.data['pressions']:
            assert 'createur_nom' in pression
