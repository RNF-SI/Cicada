"""
Tests d'intégration pour l'API REST Opérations (Actions).
"""
from decimal import Decimal

import pytest
from rest_framework import status

from apps.plans.models_operations import Operation, Protocole, SuiviInventaire, CorOperationMetrique
from tests.factories.enjeux import (
    EnjeuFactory, NomenclatureEnjeuFactory,
    ObjectifLongTermeFactory, NiveauExigenceFactory,
    IndicateurFactory, MetriqueFactory, ProtocoleFactory, SuiviInventaireFactory, OperationFactory,
    NomenclaturePrioriteOperationFactory, NomenclatureTypeIndicateurFactory,
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

    plan = PlanGestionFactory(nom='Plan Test Operations', statut='draft')
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
    # Types État/Pression explicites : sans ça, l'Iterator de la factory peut
    # produire un indicateur REPONSE, ce qui fausse les tests sur `metrique_ids`
    # (les liens REPONSE étant désormais préservés à la re-synchro, #398).
    type_etat = NomenclatureTypeIndicateurFactory(
        cd_nomenclature='ETAT', mnemonique='ETAT', label='État',
    )
    type_pression = NomenclatureTypeIndicateurFactory(
        cd_nomenclature='PRESSION', mnemonique='PRESSION', label='Pression',
    )
    indicateur1 = IndicateurFactory(
        id_ne=ne, nom_indicateur='Indicateur Test Op 1',
        type_indicateur=type_etat,
        id_utilisateur_ajout=referent
    )
    indicateur2 = IndicateurFactory(
        id_ne=ne, nom_indicateur='Indicateur Test Op 2',
        type_indicateur=type_pression,
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

    # Operations linked via metriques M2M
    op1 = OperationFactory(
        libelle='Restauration des berges',
        id_priorite=priorite_1,
        code_operation='OP-001',
        description='Restauration écologique des berges du cours d\'eau',
        annee_min=2024, annee_max=2028,
        metriques=[metrique1],
        id_utilisateur_ajout=referent
    )

    op2 = OperationFactory(
        libelle='Suivi floristique annuel',
        id_priorite=priorite_2,
        code_operation='OP-002',
        annee_min=2024, annee_max=2030,
        metriques=[metrique1],
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
        """Test list response includes metriques and metrique_ids."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert 'metriques' in item
            assert 'metrique_ids' in item

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
            'metrique_ids': [operation_test_data['metrique1'].id_metrique],
        }, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_creates_operation(self, api_client, operation_test_data):
        """Test super admin can create an operation."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Nouvelle opération SA',
            'metrique_ids': [operation_test_data['metrique1'].id_metrique],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert Operation.objects.filter(libelle='Nouvelle opération SA').exists()

    def test_referent_creates_operation(self, api_client, operation_test_data):
        """Test referent can create an operation."""
        api_client.force_authenticate(user=operation_test_data['referent'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Nouvelle opération Ref',
            'metrique_ids': [operation_test_data['metrique1'].id_metrique],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_action_on_indicateur_without_metrique(self, api_client, operation_test_data):
        """#367 — créer une action rattachée directement à un indicateur, sans métrique."""
        api_client.force_authenticate(user=operation_test_data['referent'])
        indicateur = operation_test_data['indicateur1']
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Action sans métrique',
            'id_indicateur': indicateur.id_indicateur,
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED, response.data
        op = Operation.objects.get(libelle='Action sans métrique')
        assert op.id_indicateur_id == indicateur.id_indicateur
        assert op.metriques.count() == 0
        # Le plan doit être résolu via l'indicateur (permission draft, #248/#367).
        assert op.get_plan_de_gestion() is not None

    def test_indicateur_action_appears_in_by_indicateur(self, api_client, operation_test_data):
        """#367 — une action rattachée à l'indicateur apparaît dans by-indicateur."""
        api_client.force_authenticate(user=operation_test_data['referent'])
        indicateur = operation_test_data['indicateur1']
        api_client.post('/api/plans/operations/', {
            'libelle': 'Action directe indicateur',
            'id_indicateur': indicateur.id_indicateur,
        }, format='json')
        response = api_client.get(f'/api/plans/operations/by-indicateur/{indicateur.id_indicateur}/')
        assert response.status_code == status.HTTP_200_OK
        libelles = [o['libelle'] for o in response.data['operations']]
        assert 'Action directe indicateur' in libelles

    def test_create_with_year_cost_detail(self, api_client, operation_test_data):
        """#624 — mode « par type de budget + type de poste » : le détail des
        coûts est saisi sur l'ANNÉE (pas sur l'organisme) et persisté tel quel.
        """
        from apps.plans.models_operations import OperationAnnee
        api_client.force_authenticate(user=operation_test_data['referent'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Action détail coûts sans organisme',
            'metrique_ids': [operation_test_data['metrique1'].id_metrique],
            'ventilation_mode': 'by_type_poste',
            'declinaison_par_poste': True,
            'operation_annees': [{
                'annee': 2024,
                'periodicite': True,
                # Budget total dérivé ; les enveloppes fonct/invest restent nulles.
                'budget': '2150.00',
                'cout_stage': '200.00',
                'cout_prestataire': '1000.00',
                'autre_cout': '150.00',
                'autre_cout_commentaire': 'Consommables',
                'cout_prestataire_invest': '700.00',
                'autre_cout_invest': '100.00',
                'autre_cout_invest_commentaire': 'Matériel',
            }],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED, response.data
        op = Operation.objects.get(libelle='Action détail coûts sans organisme')
        oa = OperationAnnee.objects.get(id_operation=op, annee=2024)
        assert oa.cout_stage == Decimal('200.00')
        assert oa.cout_prestataire == Decimal('1000.00')
        assert oa.autre_cout_commentaire == 'Consommables'
        assert oa.cout_prestataire_invest == Decimal('700.00')
        assert oa.autre_cout_invest_commentaire == 'Matériel'
        assert oa.budget_fonctionnement is None
        # Relu par l'API (le formulaire les recharge à la réouverture).
        detail = api_client.get(f'/api/plans/operations/{op.id_operation}/')
        annee = detail.data['operation_annees'][0]
        assert annee['cout_stage'] == '200.00'
        assert annee['autre_cout_invest'] == '100.00'

    def test_create_with_manual_salary_and_cost_detail_flags(self, api_client, operation_test_data):
        """#600 (retour 08/2026) — réglages du tableau de programmation.

        « Déclinaison par type de coût » et « saisie automatique du coût
        salarial » sont persistés sur l'action ; en saisie manuelle, le coût
        salarial est enregistré sur l'année (et relu tel quel).
        """
        from apps.plans.models_operations import OperationAnnee
        api_client.force_authenticate(user=operation_test_data['referent'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Action coût salarial saisi',
            'metrique_ids': [operation_test_data['metrique1'].id_metrique],
            'ventilation_mode': 'by_type',
            'declinaison_par_type_cout': True,
            'cout_salarial_auto': False,
            'operation_annees': [{
                'annee': 2024,
                'periodicite': True,
                'budget': '2500.00',
                'cout_salarial': '1800.00',
                'cout_salarial_invest': '450.00',
                'cout_prestataire': '250.00',
            }],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED, response.data
        op = Operation.objects.get(libelle='Action coût salarial saisi')
        assert op.declinaison_par_type_cout is True
        assert op.cout_salarial_auto is False
        oa = OperationAnnee.objects.get(id_operation=op, annee=2024)
        assert oa.cout_salarial == Decimal('1800.00')
        assert oa.cout_salarial_invest == Decimal('450.00')

        detail = api_client.get(f'/api/plans/operations/{op.id_operation}/')
        assert detail.data['declinaison_par_type_cout'] is True
        assert detail.data['cout_salarial_auto'] is False
        annee = detail.data['operation_annees'][0]
        assert annee['cout_salarial'] == '1800.00'
        assert annee['cout_salarial_invest'] == '450.00'

    def test_cost_detail_flag_defaults_to_true(self, api_client, operation_test_data):
        """#600 — sans précision, la déclinaison par type de coût et la saisie
        automatique du coût salarial sont actives (cases cochées par défaut)."""
        api_client.force_authenticate(user=operation_test_data['referent'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Action réglages par défaut',
            'metrique_ids': [operation_test_data['metrique1'].id_metrique],
            'ventilation_mode': 'by_org_type',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED, response.data
        op = Operation.objects.get(libelle='Action réglages par défaut')
        assert op.declinaison_par_type_cout is True
        assert op.cout_salarial_auto is True

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
            'metrique_ids': [operation_test_data['metrique1'].id_metrique],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération Complète')
        assert op.code_operation == 'OP-COMP'
        assert op.annee_min == 2025
        assert op.annee_max == 2030
        assert list(op.metriques.values_list('id_metrique', flat=True)) == [operation_test_data['metrique1'].id_metrique]

    def test_create_with_minimal_fields(self, api_client, operation_test_data):
        """Test create with only required field (libelle)."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération Minimale',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération Minimale')
        assert op.metriques.count() == 0

    def test_create_missing_libelle_returns_400(self, api_client, operation_test_data):
        """Test create without required libelle returns 400."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'description': 'Missing libelle',
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_metrique(self, api_client, operation_test_data):
        """Test metrique_ids M2M is properly set."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        met_id = operation_test_data['metrique1'].id_metrique
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération avec Métrique',
            'metrique_ids': [met_id],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        op = Operation.objects.get(libelle='Opération avec Métrique')
        assert list(op.metriques.values_list('id_metrique', flat=True)) == [met_id]

    def test_audit_field_set_on_create(self, api_client, operation_test_data):
        """Test id_utilisateur_ajout is set on create."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération Audit',
            'metrique_ids': [operation_test_data['metrique1'].id_metrique],
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
        assert op.id_suivi.protocoles.count() == 1
        proto = op.id_suivi.protocoles.first()
        assert proto.protocole_dans_campanule is True
        assert proto.protocole_campanule_nom == 'Proto Test'

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
        """Test detail includes metriques list and metrique_ids."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['metrique_ids'] == [operation_test_data['metrique1'].id_metrique]
        assert len(response.data['metriques']) == 1
        assert response.data['metriques'][0]['nom_metrique'] == operation_test_data['metrique1'].nom_metrique
        assert response.data['metriques'][0]['indicateur_id'] == operation_test_data['indicateur1'].id_indicateur
        assert response.data['metriques'][0]['indicateur_nom'] == operation_test_data['indicateur1'].nom_indicateur

    def test_detail_includes_priorite_label(self, api_client, operation_test_data):
        """Test detail includes priorite_label."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.data['priorite_label'] == 'Priorité 1'

    def test_detail_includes_enjeu_slug(self, api_client, operation_test_data):
        """#531 — le détail expose l'enjeu parent (via NE → OLT → Enjeu) pour
        naviguer vers la position de l'action dans l'architecture du plan."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.get(f'/api/plans/operations/{op_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['enjeu_slug'] == operation_test_data['enjeu'].slug

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
            protocoles=[protocole],
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

    def test_detail_resolves_objectif_cible_labels(self, api_client, operation_test_data):
        """#571 — objectif/cible exposent le libellé de nomenclature (pas le mnémonique)."""
        from tests.factories.core import NomenclatureFactory, TypeNomenclatureFactory
        obj_type = TypeNomenclatureFactory(mnemonique='OBJECTIF_SUIVI', label='Objectif suivi')
        cible_type = TypeNomenclatureFactory(mnemonique='CIBLE_SUIVI', label='Cible suivi')
        NomenclatureFactory(
            id_type=obj_type, mnemonique='OBJ_PHYSICO_CHIMIQUES',
            label='Paramètres physico-chimiques et climatiques',
        )
        NomenclatureFactory(
            id_type=cible_type, mnemonique='ABIOTIQUE', label='Composante abiotique',
        )
        suivi = SuiviInventaireFactory(
            objectif_principal='OBJ_PHYSICO_CHIMIQUES',
            cibles_principales='ABIOTIQUE',
            id_utilisateur_ajout=operation_test_data['referent'],
        )
        op = operation_test_data['op1']
        op.id_suivi = suivi
        op.save(update_fields=['id_suivi'])

        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get(f'/api/plans/operations/{op.id_operation}/')
        assert response.status_code == status.HTTP_200_OK
        suivi_data = response.data['suivi_inventaire']
        # Le mnémonique brut reste exposé, mais un label lisible est ajouté.
        assert suivi_data['objectif_principal'] == 'OBJ_PHYSICO_CHIMIQUES'
        assert suivi_data['objectif_principal_label'] == 'Paramètres physico-chimiques et climatiques'
        assert suivi_data['cibles_principales_label'] == 'Composante abiotique'

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

    def test_update_metrique_ids_preserves_response_indicator(self, api_client, operation_test_data):
        """#398 — la (re)synchro de `metrique_ids` au save ne touche QUE les liens
        vers des métriques État/Pression. Un indicateur de réponse (lié à l'action
        via sa propre métrique) doit survivre, et ne pas figurer dans `metrique_ids`."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op = operation_test_data['op1']

        # Indicateur de réponse + sa métrique, rattachés à l'action.
        reponse_type = NomenclatureTypeIndicateurFactory(
            cd_nomenclature='REPONSE', mnemonique='REPONSE', label='Réponse',
        )
        reponse_ind = IndicateurFactory(
            id_ne=operation_test_data['indicateur1'].id_ne,
            type_indicateur=reponse_type,
            nom_indicateur='Indicateur de réponse',
            id_utilisateur_ajout=operation_test_data['referent'],
        )
        reponse_met = MetriqueFactory(
            id_indicateur=reponse_ind, nom_metrique='Métrique de réponse',
            id_utilisateur_ajout=operation_test_data['referent'],
        )
        CorOperationMetrique.objects.create(id_operation=op, id_metrique=reponse_met)

        etat_met_id = operation_test_data['metrique1'].id_metrique

        # Le front n'envoie que la métrique État (la réponse ne transite pas par la liste).
        response = api_client.patch(f'/api/plans/operations/{op.id_operation}/', {
            'metrique_ids': [etat_met_id],
        }, format='json')
        assert response.status_code == status.HTTP_200_OK

        # Le lien vers la métrique de réponse a survécu…
        linked = set(op.metriques.values_list('id_metrique', flat=True))
        assert reponse_met.id_metrique in linked
        assert etat_met_id in linked
        # …mais `metrique_ids` exposé n'inclut QUE l'État/Pression.
        assert response.data['metrique_ids'] == [etat_met_id]

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
        """Test updating metrique_ids replaces existing M2M links."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        met2_id = operation_test_data['metrique2'].id_metrique

        # op1 currently linked to metrique1
        response = api_client.patch(f'/api/plans/operations/{op_id}/', {
            'metrique_ids': [met2_id]
        }, format='json')
        assert response.status_code == status.HTTP_200_OK

        op = Operation.objects.get(id_operation=op_id)
        assert list(op.metriques.values_list('id_metrique', flat=True)) == [met2_id]

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
# TestOperationStatut — #251 (Brouillon vs Validé)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationStatut:
    """Tests for #251 — statut 'draft' / 'valide' on Operation."""

    def test_default_statut_is_valide(self, api_client, operation_test_data):
        """Statut par défaut à la création (sans champ fourni) = 'valide' (cf. commit 4fbf736)."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Action sans statut explicite',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['statut'] == 'valide'

    def test_create_with_explicit_draft(self, api_client, operation_test_data):
        """saveDraft envoie statut='draft'."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Brouillon',
            'statut': 'draft',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['statut'] == 'draft'

    def test_create_with_valide(self, api_client, operation_test_data):
        """save (Valider) envoie statut='valide'."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Validée',
            'statut': 'valide',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['statut'] == 'valide'

    def test_patch_promotes_to_valide(self, api_client, operation_test_data):
        """PATCH avec statut='valide' fait passer un brouillon à validé."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op = operation_test_data['op1']
        op.statut = 'draft'
        op.save()
        response = api_client.patch(f'/api/plans/operations/{op.id_operation}/', {
            'statut': 'valide'
        })
        assert response.status_code == status.HTTP_200_OK
        op.refresh_from_db()
        assert op.statut == 'valide'

    def test_patch_demotes_to_draft(self, api_client, operation_test_data):
        """PATCH avec statut='draft' fait régresser une action validée en brouillon
        (cas où on enregistre des modifs WIP sur une action déjà validée)."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op = operation_test_data['op1']
        op.statut = 'valide'
        op.save()
        response = api_client.patch(f'/api/plans/operations/{op.id_operation}/', {
            'statut': 'draft'
        })
        assert response.status_code == status.HTTP_200_OK
        op.refresh_from_db()
        assert op.statut == 'draft'

    def test_list_exposes_statut(self, api_client, operation_test_data):
        """La liste expose le statut pour permettre l'affichage de la chip."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        response = api_client.get('/api/plans/operations/')
        assert response.status_code == status.HTTP_200_OK
        assert all('statut' in op for op in response.data['results'])


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
        """Test deleting operation does not cascade to metrique (M2M link deleted, metrique preserved)."""
        op_id = operation_test_data['op2'].id_operation
        met_id = operation_test_data['metrique1'].id_metrique

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
# TestOperationCreateIndicator (indicateurs de réponse)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationCreateIndicator:
    """Tests for POST /api/plans/operations/{id}/create-indicator/ (indicateur de réponse)."""

    def test_create_indicator_from_metrique_parent(self, api_client, operation_test_data):
        """Action rattachée à une métrique → indicateur de réponse créé sous le même NE/RA."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op = operation_test_data['op1']  # lié à metrique1 (indicateur1, sous NE)
        response = api_client.post(
            f'/api/plans/operations/{op.id_operation}/create-indicator/',
            {'nom_indicateur': 'Indicateur de réponse A'}, format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom_indicateur'] == 'Indicateur de réponse A'
        # Le nouvel indicateur est rattaché au plan via l'op (vérif via by-indicateur)
        new_ind_id = response.data['id_indicateur']
        from apps.plans.models_indicateurs import Indicateur
        new_ind = Indicateur.objects.get(pk=new_ind_id)
        assert new_ind.id_ne_id == operation_test_data['indicateur1'].id_ne_id

    def test_create_indicator_defaults_to_empty_metric_name(self, api_client, operation_test_data):
        """#398 — sans `nom_metrique`, la métrique reste sans nom (au lieu d'hériter
        du nom de l'indicateur), pour ne pas s'afficher à tort comme une métrique."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op = operation_test_data['op1']
        response = api_client.post(
            f'/api/plans/operations/{op.id_operation}/create-indicator/',
            {'nom_indicateur': 'Indicateur de réponse sans métrique'}, format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom_metrique'] == ''

    def test_create_indicator_from_direct_indicator_no_metrique(self, api_client, operation_test_data):
        """#367 — action rattachée directement à un indicateur (sans métrique) :
        l'indicateur de réponse est tout de même créé (parent hérité de l'indicateur direct)."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_direct = OperationFactory(
            id_indicateur=operation_test_data['indicateur1'],
            id_utilisateur_ajout=operation_test_data['referent'],
        )  # pas de métrique
        response = api_client.post(
            f'/api/plans/operations/{op_direct.id_operation}/create-indicator/',
            {'nom_indicateur': 'Réponse sans métrique'}, format='json',
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom_indicateur'] == 'Réponse sans métrique'

    def test_create_indicator_without_name_returns_400(self, api_client, operation_test_data):
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op = operation_test_data['op1']
        response = api_client.post(
            f'/api/plans/operations/{op.id_operation}/create-indicator/',
            {'nom_indicateur': '  '}, format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_indicator_without_parent_returns_400(self, api_client, operation_test_data):
        """Ni métrique ni indicateur direct → 400."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        orphan = OperationFactory(id_utilisateur_ajout=operation_test_data['referent'])
        response = api_client.post(
            f'/api/plans/operations/{orphan.id_operation}/create-indicator/',
            {'nom_indicateur': 'Orpheline'}, format='json',
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST


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


# =============================================================================
# TestOperationAddRemoveMetrique
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOperationAddRemoveMetrique:
    """Tests for POST /api/plans/operations/{id}/add-metrique/ and remove-metrique/"""

    def test_add_metrique_creates_link(self, api_client, operation_test_data):
        """Test adding a metrique creates the M2M link."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        met2_id = operation_test_data['metrique2'].id_metrique

        # op1 initially has metrique1 only
        assert operation_test_data['op1'].metriques.count() == 1

        response = api_client.post(
            f'/api/plans/operations/{op_id}/add-metrique/',
            {'metrique_id': met2_id},
            format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert met2_id in response.data['metrique_ids']

        # Verify in DB
        operation_test_data['op1'].refresh_from_db()
        assert operation_test_data['op1'].metriques.count() == 2

    def test_add_metrique_idempotent(self, api_client, operation_test_data):
        """Test adding same metrique twice is idempotent (200 on second call)."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        met1_id = operation_test_data['metrique1'].id_metrique

        # op1 already has metrique1
        response = api_client.post(
            f'/api/plans/operations/{op_id}/add-metrique/',
            {'metrique_id': met1_id},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert operation_test_data['op1'].metriques.count() == 1

    def test_add_metrique_missing_id_returns_400(self, api_client, operation_test_data):
        """Test missing metrique_id returns 400."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.post(
            f'/api/plans/operations/{op_id}/add-metrique/',
            {},
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_metrique_nonexistent_returns_404(self, api_client, operation_test_data):
        """Test adding nonexistent metrique returns 404."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.post(
            f'/api/plans/operations/{op_id}/add-metrique/',
            {'metrique_id': 99999},
            format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_metrique_unauthenticated_returns_401(self, api_client, operation_test_data):
        """Test unauthenticated add-metrique returns 401."""
        op_id = operation_test_data['op1'].id_operation
        response = api_client.post(
            f'/api/plans/operations/{op_id}/add-metrique/',
            {'metrique_id': operation_test_data['metrique2'].id_metrique},
            format='json'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_remove_metrique_deletes_link(self, api_client, operation_test_data):
        """Test removing a metrique deletes the M2M link."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op = operation_test_data['op1']
        met1_id = operation_test_data['metrique1'].id_metrique

        assert op.metriques.count() == 1

        response = api_client.post(
            f'/api/plans/operations/{op.id_operation}/remove-metrique/',
            {'metrique_id': met1_id},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert met1_id not in response.data['metrique_ids']

        op.refresh_from_db()
        assert op.metriques.count() == 0

    def test_remove_metrique_idempotent(self, api_client, operation_test_data):
        """Test removing a non-linked metrique is a no-op."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        met2_id = operation_test_data['metrique2'].id_metrique

        # op1 is not linked to metrique2
        response = api_client.post(
            f'/api/plans/operations/{op_id}/remove-metrique/',
            {'metrique_id': met2_id},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK

    def test_remove_metrique_missing_id_returns_400(self, api_client, operation_test_data):
        """Test missing metrique_id returns 400."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op_id = operation_test_data['op1'].id_operation
        response = api_client.post(
            f'/api/plans/operations/{op_id}/remove-metrique/',
            {},
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_with_multiple_metriques(self, api_client, operation_test_data):
        """Test creating an operation with multiple metriques at once."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        met1_id = operation_test_data['metrique1'].id_metrique
        met2_id = operation_test_data['metrique2'].id_metrique

        response = api_client.post('/api/plans/operations/', {
            'libelle': 'Opération Multi-Métriques',
            'metrique_ids': [met1_id, met2_id],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert len(response.data['metrique_ids']) == 2
        assert met1_id in response.data['metrique_ids']
        assert met2_id in response.data['metrique_ids']

    def test_update_replaces_all_metriques(self, api_client, operation_test_data):
        """Test PATCH with metrique_ids replaces all existing links."""
        api_client.force_authenticate(user=operation_test_data['super_admin'])
        op = operation_test_data['op1']
        met2_id = operation_test_data['metrique2'].id_metrique

        # op1 has metrique1, replace with metrique2
        response = api_client.patch(
            f'/api/plans/operations/{op.id_operation}/',
            {'metrique_ids': [met2_id]},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK

        op.refresh_from_db()
        assert list(op.metriques.values_list('id_metrique', flat=True)) == [met2_id]
