"""
Tests d'intégration pour l'API REST Opérations (Actions).
"""
import pytest
from rest_framework import status

from apps.plans.models_operations import Operation, CorOperationIndicateur
from tests.factories.enjeux import (
    EnjeuFactory, NomenclatureEnjeuFactory,
    ObjectifLongTermeFactory, NiveauExigenceFactory,
    IndicateurFactory, OperationFactory, CorOperationIndicateurFactory,
    NomenclaturePrioriteOperationFactory,
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)


@pytest.fixture
def operation_test_data(db):
    """Fixture providing common test data for operations tests."""
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan Test Operations', statut='valide')
    CorSitePgFactory(plan_de_gestion=plan, site=site)

    # Users
    super_admin = SuperAdminFactory()
    admin_og = AdminOrganismeFactory(id_organisme=organisme)
    referent = ReferentFactory(id_organisme=organisme)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan.referents.add(referent)
    user = RoleFactory()

    # Nomenclatures
    cat_enjeu = NomenclatureEnjeuFactory()
    priorite_1 = NomenclaturePrioriteOperationFactory(
        mnemonique='PRIORITE_1', cd_nomenclature='P1', label='Priorité 1'
    )
    priorite_2 = NomenclaturePrioriteOperationFactory(
        mnemonique='PRIORITE_2', cd_nomenclature='P2', label='Priorité 2'
    )

    # Hierarchy: Enjeu > OLT > NE > Indicateur
    enjeu = EnjeuFactory(
        id_pg=plan, id_categorie=cat_enjeu, libelle='Enjeu Test Op',
        rang=1, categorie_ecologique=True,
        id_utilisateur_ajout=referent
    )
    olt = ObjectifLongTermeFactory(
        id_enjeu=enjeu, libelle='OLT Test Op',
        id_utilisateur_ajout=referent
    )
    ne = NiveauExigenceFactory(
        id_olt=olt, libelle='NE Test Op',
        id_utilisateur_ajout=referent
    )
    indicateur1 = IndicateurFactory(
        id_ne=ne, nom_indicateur='Indicateur Test Op 1',
        id_utilisateur_ajout=referent
    )
    indicateur2 = IndicateurFactory(
        id_ne=ne, nom_indicateur='Indicateur Test Op 2',
        id_utilisateur_ajout=referent
    )

    # Operations
    op1 = OperationFactory(
        libelle='Restauration des berges',
        id_priorite=priorite_1,
        code_operation='OP-001',
        description='Restauration écologique des berges du cours d\'eau',
        annee_min=2024, annee_max=2028,
        id_utilisateur_ajout=referent
    )
    CorOperationIndicateurFactory(id_operation=op1, id_indicateur=indicateur1)

    op2 = OperationFactory(
        libelle='Suivi floristique annuel',
        id_priorite=priorite_2,
        code_operation='OP-002',
        annee_min=2024, annee_max=2030,
        id_utilisateur_ajout=referent
    )
    CorOperationIndicateurFactory(id_operation=op2, id_indicateur=indicateur1)
    CorOperationIndicateurFactory(id_operation=op2, id_indicateur=indicateur2)

    return {
        'organisme': organisme,
        'site': site,
        'plan': plan,
        'super_admin': super_admin,
        'admin_og': admin_og,
        'referent': referent,
        'user': user,
        'enjeu': enjeu,
        'indicateur1': indicateur1,
        'indicateur2': indicateur2,
        'op1': op1,
        'op2': op2,
        'priorite_1': priorite_1,
        'priorite_2': priorite_2,
    }


# =============================================================================
# TestOperationListEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationListEndpoint:
    """Tests for GET /api/plans/operations/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/operations/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, operation_test_data):
        """Test super admin can see all operations."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_admin_og_sees_own_org_operations(self, api_client, operation_test_data):
        """Test admin organisme sees operations from their organisation's plans."""
        api_client.force_authenticate(user=operation_test_data['admin_og'])
        response = api_client.get('/api/plans/operations/')
        assert response.status_code == status.HTTP_200_OK

    def test_referent_sees_own_plans_operations(self, api_client, operation_test_data):
        """Test referent sees operations from their plans."""
        api_client.force_authenticate(user=operation_test_data['referent'])
        response = api_client.get('/api/plans/operations/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_pagination_works(self, api_client, operation_test_data):
        """Test pagination is present in response."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_list_includes_nb_indicateurs(self, api_client, operation_test_data):
        """Test list response includes nb_indicateurs."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert 'nb_indicateurs' in item

    def test_list_includes_priorite_label(self, api_client, operation_test_data):
        """Test list response includes priorite_label."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/')
        assert response.status_code == status.HTTP_200_OK
        op1_data = next(
            (o for o in response.data['results']
             if o['id_operation'] == operation_test_data['op1'].id_operation),
            None
        )
        assert op1_data is not None
        assert op1_data['priorite_label'] == 'Priorité 1'

    def test_search_by_libelle(self, api_client, operation_test_data):
        """Test search filters by libelle."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/?search=Restauration')
        assert response.status_code == status.HTTP_200_OK
        libelles = [o['libelle'] for o in response.data['results']]
        assert 'Restauration des berges' in libelles


# =============================================================================
# TestOperationCreateEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationCreateEndpoint:
    """Tests for POST /api/plans/operations/"""

    def test_unauthenticated_returns_401(self, api_client, operation_test_data):
        """Test unauthenticated create returns 401."""
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Nouvelle opération',
            'indicateur_ids': [operation_test_data['indicateur1'].id_indicateur],
        }, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_creates_operation(self, api_client, operation_test_data):
        """Test super admin can create an operation."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Nouvelle opération SA',
            'indicateur_ids': [operation_test_data['indicateur1'].id_indicateur],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Operation.objects.filter(libelle='Nouvelle opération SA').exists()

    def test_referent_creates_operation(self, api_client, operation_test_data):
        """Test referent can create an operation."""
        api_client.force_authenticate(user=operation_test_data['referent'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Nouvelle opération Ref',
            'indicateur_ids': [operation_test_data['indicateur1'].id_indicateur],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_with_all_fields(self, api_client, operation_test_data):
        """Test create with all optional fields."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération Complète',
            'id_priorite': operation_test_data['priorite_1'].id_nomenclature,
            'code_operation': 'OP-COMP',
            'id_referentiel_operations': 'REF-COMP',
            'description': 'Description complète de l\'opération',
            'annee_min': 2025,
            'annee_max': 2030,
            'indicateur_ids': [
                operation_test_data['indicateur1'].id_indicateur,
                operation_test_data['indicateur2'].id_indicateur,
            ],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération Complète')
        assert op.code_operation == 'OP-COMP'
        assert op.annee_min == 2025
        assert op.annee_max == 2030
        assert op.indicateurs.count() == 2

    def test_create_with_minimal_fields(self, api_client, operation_test_data):
        """Test create with only required field (libelle)."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération Minimale',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération Minimale')
        assert op.indicateurs.count() == 0

    def test_create_missing_libelle_returns_400(self, api_client, operation_test_data):
        """Test create without required libelle returns 400."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'description': 'Missing libelle',
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_m2m_indicateurs(self, api_client, operation_test_data):
        """Test M2M indicateur_ids are properly linked."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        ind1_id = operation_test_data['indicateur1'].id_indicateur
        ind2_id = operation_test_data['indicateur2'].id_indicateur
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération Multi-Indicateurs',
            'indicateur_ids': [ind1_id, ind2_id],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération Multi-Indicateurs')
        ind_ids = list(op.indicateurs.values_list('id_indicateur', flat=True))
        assert ind1_id in ind_ids
        assert ind2_id in ind_ids

    def test_audit_field_set_on_create(self, api_client, operation_test_data):
        """Test id_utilisateur_ajout is set on create."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération Audit',
            'indicateur_ids': [operation_test_data['indicateur1'].id_indicateur],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération Audit')
        assert op.id_utilisateur_ajout == operation_test_data['super_admin']


# =============================================================================
# TestOperationDetailEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationDetailEndpoint:
    """Tests for GET /api/plans/operations/{id}/"""

    def test_super_admin_gets_detail(self, api_client, operation_test_data):
        """Test super admin can retrieve operation detail."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['libelle'] == 'Restauration des berges'

    def test_referent_gets_detail(self, api_client, operation_test_data):
        """Test referent can retrieve operation detail."""
        api_client.force_authenticate(user=operation_test_data['referent'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_detail_includes_indicateur_ids(self, api_client, operation_test_data):
        """Test detail includes indicateur_ids."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op2'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'indicateur_ids' in response.data
        assert len(response.data['indicateur_ids']) == 2

    def test_detail_includes_nb_indicateurs(self, api_client, operation_test_data):
        """Test detail includes nb_indicateurs."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.data['nb_indicateurs'] == 1

    def test_detail_includes_priorite_label(self, api_client, operation_test_data):
        """Test detail includes priorite_label."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.data['priorite_label'] == 'Priorité 1'

    def test_detail_includes_createur_nom(self, api_client, operation_test_data):
        """Test detail includes createur_nom."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert 'createur_nom' in response.data

    def test_nonexistent_id_returns_404(self, api_client, operation_test_data):
        """Test nonexistent ID returns 404."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TestOperationUpdateEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationUpdateEndpoint:
    """Tests for PATCH /api/plans/operations/{id}/"""

    def test_super_admin_updates(self, api_client, operation_test_data):
        """Test super admin can update an operation."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.patch(f'/api/plans/operations/{op_id}/', {
            'libelle': 'Opération Mise à Jour'
        })
        assert response.status_code == status.HTTP_200_OK
        operation_test_data['op1'].refresh_from_db()
        assert operation_test_data['op1'].libelle == 'Opération Mise à Jour'

    def test_referent_updates(self, api_client, operation_test_data):
        """Test referent can update an operation."""
        api_client.force_authenticate(user=operation_test_data['referent'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.patch(f'/api/plans/operations/{op_id}/', {
            'libelle': 'Opération Mise à Jour Ref'
        })
        assert response.status_code == status.HTTP_200_OK

    def test_update_priorite(self, api_client, operation_test_data):
        """Test updating priority field."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.patch(f'/api/plans/operations/{op_id}/', {
            'id_priorite': operation_test_data['priorite_2'].id_nomenclature
        })
        assert response.status_code == status.HTTP_200_OK
        operation_test_data['op1'].refresh_from_db()
        assert operation_test_data['op1'].id_priorite == operation_test_data['priorite_2']

    def test_update_indicateur_ids_replaces(self, api_client, operation_test_data):
        """Test updating indicateur_ids replaces existing M2M relations."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        ind2_id = operation_test_data['indicateur2'].id_indicateur

        # op1 currently linked to indicateur1 only
        response = api_client.patch(f'/api/plans/operations/{op_id}/', {
            'indicateur_ids': [ind2_id]
        }, format='json')
        assert response.status_code == status.HTTP_200_OK

        operation_test_data['op1'].refresh_from_db()
        linked_ids = list(operation_test_data['op1'].indicateurs.values_list('id_indicateur', flat=True))
        assert ind2_id in linked_ids
        assert operation_test_data['indicateur1'].id_indicateur not in linked_ids

    def test_update_annee_range(self, api_client, operation_test_data):
        """Test updating year range."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.patch(f'/api/plans/operations/{op_id}/', {
            'annee_min': 2025,
            'annee_max': 2035,
        })
        assert response.status_code == status.HTTP_200_OK
        operation_test_data['op1'].refresh_from_db()
        assert operation_test_data['op1'].annee_min == 2025
        assert operation_test_data['op1'].annee_max == 2035

    def test_audit_field_updated(self, api_client, operation_test_data):
        """Test id_utilisateur_maj is updated on PATCH."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.patch(f'/api/plans/operations/{op_id}/', {
            'libelle': 'Updated for Audit'
        })
        assert response.status_code == status.HTTP_200_OK
        operation_test_data['op1'].refresh_from_db()
        assert operation_test_data['op1'].id_utilisateur_maj == operation_test_data['super_admin']

    def test_nonexistent_id_returns_404(self, api_client, operation_test_data):
        """Test updating nonexistent ID returns 404."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.patch('/api/plans/operations/99999/', {
            'libelle': 'Nope'
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TestOperationDeleteEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationDeleteEndpoint:
    """Tests for DELETE /api/plans/operations/{id}/"""

    def test_super_admin_deletes(self, api_client, operation_test_data):
        """Test super admin can delete an operation."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.delete(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Operation.objects.filter(id_operation=op_id).exists()

    def test_referent_deletes(self, api_client, operation_test_data):
        """Test referent can delete an operation."""
        api_client.force_authenticate(user=operation_test_data['referent'])
        op_id = operation_test_data['op2'].id_operation
        response = api_client.delete(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_cascade_cor_deleted(self, api_client, operation_test_data):
        """Test deleting operation cascades to cor_operation_indicateur."""
        op_id = operation_test_data['op2'].id_operation
        assert CorOperationIndicateur.objects.filter(id_operation_id=op_id).count() == 2

        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CorOperationIndicateur.objects.filter(id_operation_id=op_id).exists()

    def test_nonexistent_id_returns_404(self, api_client, operation_test_data):
        """Test deleting nonexistent ID returns 404."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.delete('/api/plans/operations/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TestOperationByIndicateurEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationByIndicateurEndpoint:
    """Tests for GET /api/plans/operations/by-indicateur/{indicateur_id}/"""

    def test_unauthenticated_returns_401(self, api_client, operation_test_data):
        """Test unauthenticated access returns 401."""
        ind_id = operation_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/operations/by-indicateur/{ind_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_returns_operations_for_indicateur(self, api_client, operation_test_data):
        """Test returns operations linked to an indicateur."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        ind_id = operation_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/operations/by-indicateur/{ind_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['indicateur_id'] == ind_id
        assert response.data['total'] == 2  # op1 and op2 both linked to indicateur1

    def test_response_structure(self, api_client, operation_test_data):
        """Test response has expected structure."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        ind_id = operation_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/operations/by-indicateur/{ind_id}/')
        assert 'indicateur_id' in response.data
        assert 'indicateur_nom' in response.data
        assert 'operations' in response.data
        assert 'total' in response.data

    def test_indicateur_with_no_operations(self, api_client, operation_test_data):
        """Test indicateur with no operations returns empty list."""
        # Create an indicateur with no operations
        ne = operation_test_data['indicateur1'].id_ne
        ind_empty = IndicateurFactory(
            id_ne=ne, nom_indicateur='Indicateur Sans Op',
            id_utilisateur_ajout=operation_test_data['referent']
        )
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get(f'/api/plans/operations/by-indicateur/{ind_empty.id_indicateur}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 0
        assert len(response.data['operations']) == 0

    def test_nonexistent_indicateur_returns_404(self, api_client, operation_test_data):
        """Test nonexistent indicateur returns 404."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/by-indicateur/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TestOperationFilters
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationFilters:
    """Tests for OperationFilter on /api/plans/operations/"""

    def test_filter_by_id_indicateur(self, api_client, operation_test_data):
        """Test filter by indicateur ID."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        ind2_id = operation_test_data['indicateur2'].id_indicateur
        response = api_client.get(f'/api/plans/operations/?id_indicateur={ind2_id}')
        assert response.status_code == status.HTTP_200_OK
        # Only op2 is linked to indicateur2
        assert len(response.data['results']) == 1
        assert response.data['results'][0]['libelle'] == 'Suivi floristique annuel'

    def test_filter_by_id_priorite(self, api_client, operation_test_data):
        """Test filter by priority."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        prio_id = operation_test_data['priorite_1'].id_nomenclature
        response = api_client.get(f'/api/plans/operations/?id_priorite={prio_id}')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['id_priorite'] == prio_id

    def test_filter_by_annee_min(self, api_client, operation_test_data):
        """Test filter by annee_min (gte)."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/?annee_min=2024')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            if item['annee_min'] is not None:
                assert item['annee_min'] >= 2024

    def test_filter_by_annee_max(self, api_client, operation_test_data):
        """Test filter by annee_max (lte)."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/?annee_max=2029')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            if item['annee_max'] is not None:
                assert item['annee_max'] <= 2029

    def test_search_by_code_operation(self, api_client, operation_test_data):
        """Test search by code_operation."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/?search=OP-001')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
        codes = [o['code_operation'] for o in response.data['results']]
        assert 'OP-001' in codes

    def test_filter_returns_empty_when_no_match(self, api_client, operation_test_data):
        """Test filters return empty results when nothing matches."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/?search=ZZZNoMatchXXX')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0
