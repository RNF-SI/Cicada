"""
Tests d'intégration pour l'API REST Opérations (Actions).
"""
import pytest
from rest_framework import status

from apps.plans.models_operations import Operation, Protocole, SuiviInventaire
from tests.factories.enjeux import (
    EnjeuFactory, NomenclatureEnjeuFactory,
    ObjectifLongTermeFactory, NiveauExigenceFactory,
    IndicateurFactory, MetriqueFactory, ProtocoleFactory, SuiviInventaireFactory, OperationFactory,
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

    # Create metriques for the indicateurs
    metrique1 = MetriqueFactory(
        id_indicateur=indicateur1, nom_metrique='Métrique Test Op 1',
        id_utilisateur_ajout=referent
    )
    metrique2 = MetriqueFactory(
        id_indicateur=indicateur2, nom_metrique='Métrique Test Op 2',
        id_utilisateur_ajout=referent
    )

    # Operations linked via id_metrique FK
    op1 = OperationFactory(
        libelle='Restauration des berges',
        id_priorite=priorite_1,
        code_operation='OP-001',
        description='Restauration écologique des berges du cours d\'eau',
        annee_min=2024, annee_max=2028,
        id_metrique=metrique1,
        id_utilisateur_ajout=referent
    )

    op2 = OperationFactory(
        libelle='Suivi floristique annuel',
        id_priorite=priorite_2,
        code_operation='OP-002',
        annee_min=2024, annee_max=2030,
        id_metrique=metrique1,
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
        'indicateur1': indicateur1,
        'indicateur2': indicateur2,
        'metrique1': metrique1,
        'metrique2': metrique2,
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

    def test_list_includes_metrique_info(self, api_client, operation_test_data):
        """Test list response includes id_metrique and metrique_nom."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert 'id_metrique' in item
            assert 'metrique_nom' in item

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
            'id_metrique': operation_test_data['metrique1'].id_metrique,
        }, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_creates_operation(self, api_client, operation_test_data):
        """Test super admin can create an operation."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Nouvelle opération SA',
            'id_metrique': operation_test_data['metrique1'].id_metrique,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Operation.objects.filter(libelle='Nouvelle opération SA').exists()

    def test_referent_creates_operation(self, api_client, operation_test_data):
        """Test referent can create an operation."""
        api_client.force_authenticate(user=operation_test_data['referent'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Nouvelle opération Ref',
            'id_metrique': operation_test_data['metrique1'].id_metrique,
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
            'id_metrique': operation_test_data['metrique1'].id_metrique,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération Complète')
        assert op.code_operation == 'OP-COMP'
        assert op.annee_min == 2025
        assert op.annee_max == 2030
        assert op.id_metrique == operation_test_data['metrique1']

    def test_create_with_minimal_fields(self, api_client, operation_test_data):
        """Test create with only required field (libelle)."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération Minimale',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération Minimale')
        assert op.id_metrique is None

    def test_create_missing_libelle_returns_400(self, api_client, operation_test_data):
        """Test create without required libelle returns 400."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'description': 'Missing libelle',
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_metrique(self, api_client, operation_test_data):
        """Test id_metrique FK is properly set."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        met_id = operation_test_data['metrique1'].id_metrique
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération avec Métrique',
            'id_metrique': met_id,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération avec Métrique')
        assert op.id_metrique_id == met_id

    def test_audit_field_set_on_create(self, api_client, operation_test_data):
        """Test id_utilisateur_ajout is set on create."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération Audit',
            'id_metrique': operation_test_data['metrique1'].id_metrique,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération Audit')
        assert op.id_utilisateur_ajout == operation_test_data['super_admin']

    def test_create_with_suivi_inventaire(self, api_client, operation_test_data):
        """Test creating operation with nested suivi_inventaire and protocole."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération avec suivi',
            'est_suivi_existant': False,
            'suivi_inventaire': {
                'objectif_principal': 'OBJ_ETAT_CONSERVATION',
                'cibles_principales': 'ESPECES',
                'taxon_taxref': 'Taxon Test',
                'protocole': {
                    'protocole_dans_campanule': True,
                    'protocole_campanule_nom': 'Proto Test',
                },
            },
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération avec suivi')
        assert op.id_suivi is not None
        assert op.id_suivi.objectif_principal == 'OBJ_ETAT_CONSERVATION'
        assert op.id_suivi.cibles_principales == 'ESPECES'
        assert op.id_suivi.id_protocole is not None
        assert op.id_suivi.id_protocole.protocole_dans_campanule is True
        assert op.id_suivi.id_protocole.protocole_campanule_nom == 'Proto Test'

    def test_create_without_suivi_inventaire(self, api_client, operation_test_data):
        """Test creating operation without suivi_inventaire."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération sans suivi',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération sans suivi')
        assert op.id_suivi is None
        assert op.est_suivi_existant is False


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

    def test_detail_includes_metrique_info(self, api_client, operation_test_data):
        """Test detail includes id_metrique, metrique_nom, indicateur_id, indicateur_nom."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id_metrique'] == operation_test_data['metrique1'].id_metrique
        assert response.data['metrique_nom'] == operation_test_data['metrique1'].nom_metrique
        assert response.data['indicateur_id'] == operation_test_data['indicateur1'].id_indicateur
        assert response.data['indicateur_nom'] == operation_test_data['indicateur1'].nom_indicateur

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

    def test_detail_includes_est_suivi_existant(self, api_client, operation_test_data):
        """Test detail includes est_suivi_existant field."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'est_suivi_existant' in response.data
        assert response.data['est_suivi_existant'] is False

    def test_detail_includes_suivi_inventaire(self, api_client, operation_test_data):
        """Test detail includes nested suivi_inventaire with protocole when linked."""
        protocole = ProtocoleFactory(
            protocole_dans_campanule=True,
            protocole_campanule_nom='Proto Detail Test',
            id_utilisateur_ajout=operation_test_data['referent']
        )
        suivi = SuiviInventaireFactory(
            objectif_principal='OBJ_INVENTAIRE_INITIAL',
            id_protocole=protocole,
            id_utilisateur_ajout=operation_test_data['referent']
        )
        op = operation_test_data['op1']
        op.id_suivi = suivi
        op.save(update_fields=['id_suivi'])

        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get(f'/api/plans/operations/{op.id_operation}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['suivi_inventaire'] is not None
        assert response.data['suivi_inventaire']['objectif_principal'] == 'OBJ_INVENTAIRE_INITIAL'
        assert response.data['suivi_inventaire']['protocole'] is not None
        assert response.data['suivi_inventaire']['protocole']['protocole_campanule_nom'] == 'Proto Detail Test'

    def test_detail_campanule_protocole_roundtrip(self, api_client, operation_test_data):
        """Test create + GET detail with Campanule protocol returns all fields for edit form."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])

        # Create operation with Campanule protocol
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Op Campanule Roundtrip',
            'est_suivi_existant': False,
            'suivi_inventaire': {
                'intitule': 'Suivi STOC',
                'objectif_principal': 'OBJ_ETAT_CONSERVATION',
                'cibles_principales': 'ESPECES',
                'taxon_taxref': 'Aves',
                'protocole': {
                    'protocole_dans_campanule': True,
                    'protocole_campanule_nom': 'STOC-EPS',
                    'cd_protocole_campanule': 42,
                    'description_protocole': 'Description auto-remplie depuis Campanule',
                    'objectif_protocole': 'Objectif auto-rempli',
                    'periode_echantillonnage': 'Avril - Juin',
                    'respect_protocole': True,
                },
            },
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op_id = response.data['id_operation']

        # GET detail — simulates opening the edit form
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_200_OK

        suivi = response.data['suivi_inventaire']
        assert suivi is not None
        assert suivi['intitule'] == 'Suivi STOC'
        assert suivi['objectif_principal'] == 'OBJ_ETAT_CONSERVATION'
        assert suivi['cibles_principales'] == 'ESPECES'
        assert suivi['taxon_taxref'] == 'Aves'

        proto = suivi['protocole']
        assert proto is not None
        assert proto['protocole_dans_campanule'] is True
        assert proto['protocole_campanule_nom'] == 'STOC-EPS'
        assert proto['cd_protocole_campanule'] == 42
        assert proto['description_protocole'] == 'Description auto-remplie depuis Campanule'
        assert proto['objectif_protocole'] == 'Objectif auto-rempli'
        assert proto['periode_echantillonnage'] == 'Avril - Juin'
        assert proto['respect_protocole'] is True
        # Non-Campanule fields should be empty/null
        assert proto['nom_protocole'] == ''
        assert proto['nb_etp_cycle'] is None

    def test_detail_non_campanule_protocole_roundtrip(self, api_client, operation_test_data):
        """Test create + GET detail with custom protocol returns all fields for edit form."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])

        # Create operation with custom (non-Campanule) protocol
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Op Custom Roundtrip',
            'est_suivi_existant': False,
            'suivi_inventaire': {
                'intitule': 'Suivi piézo',
                'objectif_principal': 'OBJ_PHYSICO_CHIMIQUES',
                'cibles_principales': 'ABIOTIQUE',
                'protocole': {
                    'protocole_dans_campanule': False,
                    'nom_protocole': 'Protocole piézométrique maison',
                    'nb_etp_cycle': '1.50',
                    'description_protocole': 'Description libre',
                    'objectif_protocole': 'Objectif libre',
                    'periode_echantillonnage': 'Toute année',
                    'respect_protocole': False,
                    'justification_non_respect': 'Adaptations locales nécessaires',
                    'differences_protocole': 'Fréquence mensuelle au lieu de bimensuelle',
                },
            },
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op_id = response.data['id_operation']

        # GET detail — simulates opening the edit form
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_200_OK

        suivi = response.data['suivi_inventaire']
        assert suivi is not None

        proto = suivi['protocole']
        assert proto is not None
        assert proto['protocole_dans_campanule'] is False
        assert proto['nom_protocole'] == 'Protocole piézométrique maison'
        assert float(proto['nb_etp_cycle']) == 1.5
        assert proto['description_protocole'] == 'Description libre'
        assert proto['objectif_protocole'] == 'Objectif libre'
        assert proto['periode_echantillonnage'] == 'Toute année'
        assert proto['respect_protocole'] is False
        assert proto['justification_non_respect'] == 'Adaptations locales nécessaires'
        assert proto['differences_protocole'] == 'Fréquence mensuelle au lieu de bimensuelle'
        # Campanule fields should be empty/null
        assert proto['cd_protocole_campanule'] is None
        assert proto['protocole_campanule_nom'] == ''

    def test_update_protocole_campanule_to_custom(self, api_client, operation_test_data):
        """Test PATCH: switch protocol from Campanule to custom and verify roundtrip."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])

        # Create with Campanule
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Op Switch Protocol',
            'est_suivi_existant': False,
            'suivi_inventaire': {
                'intitule': 'Suivi switch',
                'objectif_principal': 'OBJ_ETAT_CONSERVATION',
                'cibles_principales': 'ESPECES',
                'protocole': {
                    'protocole_dans_campanule': True,
                    'protocole_campanule_nom': 'EPOC',
                    'cd_protocole_campanule': 99,
                    'respect_protocole': True,
                },
            },
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op_id = response.data['id_operation']

        # PATCH: switch to custom protocol
        response = api_client.patch(f'/api/plans/operations/{op_id}/', {
            'suivi_inventaire': {
                'protocole': {
                    'protocole_dans_campanule': False,
                    'protocole_campanule_nom': '',
                    'cd_protocole_campanule': None,
                    'nom_protocole': 'Mon nouveau protocole',
                    'nb_etp_cycle': '2.00',
                    'description_protocole': 'Nouvelle description',
                    'respect_protocole': False,
                    'justification_non_respect': 'Changement de méthode',
                },
            },
        }, format='json')
        assert response.status_code == status.HTTP_200_OK

        # GET detail to verify
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        proto = response.data['suivi_inventaire']['protocole']
        assert proto['protocole_dans_campanule'] is False
        assert proto['cd_protocole_campanule'] is None
        assert proto['nom_protocole'] == 'Mon nouveau protocole'
        assert float(proto['nb_etp_cycle']) == 2.0
        assert proto['respect_protocole'] is False
        assert proto['justification_non_respect'] == 'Changement de méthode'

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

    def test_update_metrique_replaces(self, api_client, operation_test_data):
        """Test updating id_metrique replaces existing FK."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        met2_id = operation_test_data['metrique2'].id_metrique

        # op1 currently linked to metrique1
        response = api_client.patch(f'/api/plans/operations/{op_id}/', {
            'id_metrique': met2_id
        }, format='json')
        assert response.status_code == status.HTTP_200_OK

        operation_test_data['op1'].refresh_from_db()
        assert operation_test_data['op1'].id_metrique_id == met2_id

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

    def test_delete_does_not_cascade_to_metrique(self, api_client, operation_test_data):
        """Test deleting operation does not cascade to metrique (SET_NULL)."""
        op_id = operation_test_data['op2'].id_operation
        met_id = operation_test_data['op2'].id_metrique_id

        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Operation.objects.filter(id_operation=op_id).exists()
        # Metrique should still exist
        from apps.plans.models_indicateurs import Metrique
        assert Metrique.objects.filter(id_metrique=met_id).exists()

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
        ind1_id = operation_test_data['indicateur1'].id_indicateur
        response = api_client.get(f'/api/plans/operations/?id_indicateur={ind1_id}')
        assert response.status_code == status.HTTP_200_OK
        # Both op1 and op2 are linked to metrique1 which belongs to indicateur1
        assert len(response.data['results']) == 2

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
