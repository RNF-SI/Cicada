"""
Tests d'intégration pour l'API REST Enjeux et FCR.
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient

from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, Pression,
    CorEnjeuTaxon, CorEnjeuHabitat,
)
from apps.plans.models import PlanGestion
from tests.factories.enjeux import (
    EnjeuFactory, FcrFactory,
    FacteurInfluenceFactory, PressionFactory,
    NomenclatureEnjeuFactory, NomenclatureFcrFactory,
    NomenclatureCategorieFcrFactory,
    CorEnjeuTaxonFactory, CorEnjeuHabitatFactory,
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)


@pytest.fixture
def enjeu_test_data(db):
    """Fixture providing common test data for enjeux tests."""
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan Test Enjeux', statut='draft')
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
    cat_fcr = NomenclatureFcrFactory()

    # Enjeux & FCR
    enjeu1 = EnjeuFactory(
        id_pg=plan, id_categorie=cat_enjeu, libelle='Enjeu Biodiversité',
        rang=1, categorie_ecologique=True, habitat=True,
        id_utilisateur_ajout=referent
    )
    enjeu2 = EnjeuFactory(
        id_pg=plan, id_categorie=cat_enjeu, libelle='Enjeu Paysage',
        rang=2, categorie_ecologique=False, espece=True,
        id_utilisateur_ajout=referent
    )
    fcr1 = FcrFactory(
        id_pg=plan, libelle='FCR Connaissance',
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
        'cat_enjeu': cat_enjeu,
        'cat_fcr': cat_fcr,
        'enjeu1': enjeu1,
        'enjeu2': enjeu2,
        'fcr1': fcr1,
    }


# =============================================================================
# TestEnjeuListEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestEnjeuListEndpoint:
    """Tests for GET /api/plans/enjeux/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/enjeux/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, enjeu_test_data):
        """Test super admin can see all enjeux."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 3

    def test_admin_og_sees_own_org_enjeux(self, api_client, enjeu_test_data):
        """Test admin organisme sees enjeux from their organisation's plans."""
        api_client.force_authenticate(user=enjeu_test_data['admin_og'])
        response = api_client.get('/api/plans/enjeux/')
        assert response.status_code == status.HTTP_200_OK

    def test_referent_sees_own_plans_enjeux(self, api_client, enjeu_test_data):
        """Test referent sees enjeux from their plans."""
        api_client.force_authenticate(user=enjeu_test_data['referent'])
        response = api_client.get('/api/plans/enjeux/')
        assert response.status_code == status.HTTP_200_OK
        # Referent should see at least the enjeux on their plan
        plan_ids = [e['id_pg'] for e in response.data['results']]
        assert enjeu_test_data['plan'].id_pg in plan_ids

    def test_non_referent_user_denied(self, api_client, enjeu_test_data):
        """Test non-referent user is denied access to enjeux (IsReferent permission)."""
        api_client.force_authenticate(user=enjeu_test_data['user'])
        response = api_client.get('/api/plans/enjeux/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_pagination_works(self, api_client, enjeu_test_data):
        """Test pagination is present in response."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data

    def test_search_by_libelle(self, api_client, enjeu_test_data):
        """Test search filters by libelle."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?search=Biodiversité')
        assert response.status_code == status.HTTP_200_OK
        libelles = [e['libelle'] for e in response.data['results']]
        assert 'Enjeu Biodiversité' in libelles

    def test_nb_facteurs_influence_in_response(self, api_client, enjeu_test_data):
        """Test nb_facteurs_influence is present in list response."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert 'nb_facteurs_influence' in item


# =============================================================================
# TestEnjeuCreateEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestEnjeuCreateEndpoint:
    """Tests for POST /api/plans/enjeux/"""

    def test_unauthenticated_returns_401(self, api_client, enjeu_test_data):
        """Test unauthenticated create returns 401."""
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Nouvel Enjeu',
            'rang': 1
        })
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_creates_enjeu(self, api_client, enjeu_test_data):
        """Test super admin can create an enjeu."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Nouvel Enjeu SA',
            'rang': 2,
            'categorie_ecologique': True
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert Enjeu.objects.filter(libelle='Nouvel Enjeu SA').exists()

    def test_referent_creates_enjeu(self, api_client, enjeu_test_data):
        """Test referent can create an enjeu on their plan."""
        api_client.force_authenticate(user=enjeu_test_data['referent'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Nouvel Enjeu Ref',
            'rang': 1,
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_non_referent_denied(self, api_client, enjeu_test_data):
        """Test non-referent user cannot create an enjeu."""
        api_client.force_authenticate(user=enjeu_test_data['user'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Nouvel Enjeu',
            'rang': 1,
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_with_minimal_fields(self, api_client, enjeu_test_data):
        """Test create with minimal required fields."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Enjeu Minimal',
        })
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_with_all_optional_fields(self, api_client, enjeu_test_data):
        """Test create with all optional fields."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Enjeu Complet',
            'intitule_court': 'EC',
            'description': 'Description complète',
            'rang': 3,
            'categorie_ecologique': False,
            'habitat': True,
            'espece': True,
            'processus': False,
            'etat_enjeu': 'État bon',
        })
        assert response.status_code == status.HTTP_201_CREATED
        enjeu = Enjeu.objects.get(libelle='Enjeu Complet')
        assert enjeu.intitule_court == 'EC'
        assert enjeu.habitat is True

    def test_create_with_taxon_ids(self, api_client, enjeu_test_data):
        """Test create enjeu with taxon_ids."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Enjeu avec Taxons',
            'rang': 1,
            'taxon_ids': [12345, 67890],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        enjeu = Enjeu.objects.get(libelle='Enjeu avec Taxons')
        assert enjeu.taxons.count() == 2

    def test_create_with_habitat_ids(self, api_client, enjeu_test_data):
        """Test create enjeu with habitat_ids."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Enjeu avec Habitats',
            'rang': 1,
            'habitat_ids': ['HAB_A', 'HAB_B'],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        enjeu = Enjeu.objects.get(libelle='Enjeu avec Habitats')
        assert enjeu.habitats.count() == 2

    def test_create_with_free_text_habitats(self, api_client, enjeu_test_data):
        """#368 — création d'un enjeu avec des habitats libres (hors HabRef, sans cd_hab)."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Enjeu habitats libres',
            'rang': 1,
            'habitat': True,
            'habitats_data': [
                {'cd_hab': '24', 'lb_hab_fr': 'Habitat HabRef'},
                {'cd_hab': '', 'lb_hab_fr': 'Mangrove de Mayotte'},
                {'lb_hab_fr': 'Forêt sèche de Nouvelle-Calédonie'},
            ],
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        enjeu = Enjeu.objects.get(libelle='Enjeu habitats libres')
        assert enjeu.habitats.count() == 3
        # Deux habitats libres (cd_hab NULL) coexistent grâce aux NULL distincts.
        libres = enjeu.habitats.filter(cd_hab__isnull=True)
        assert libres.count() == 2
        assert set(libres.values_list('lb_hab_fr', flat=True)) == {
            'Mangrove de Mayotte', 'Forêt sèche de Nouvelle-Calédonie'
        }

    def test_create_habitat_without_code_nor_label_rejected(self, api_client, enjeu_test_data):
        """#368 — un habitat sans cd_hab ni libellé est rejeté (400)."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Enjeu habitat vide',
            'rang': 1,
            'habitat': True,
            'habitats_data': [{'cd_hab': '', 'lb_hab_fr': ''}],
        }, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_missing_required_fields(self, api_client, enjeu_test_data):
        """Test create without required fields returns 400."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.post('/api/plans/enjeux/', {
            'libelle': 'Missing plan'
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_fcr(self, api_client, enjeu_test_data):
        """Test create a FCR."""
        cat_fcr_nom = NomenclatureCategorieFcrFactory()
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_fcr'].id_nomenclature,
            'libelle': 'FCR Nouveau',
            'id_categorie_fcr': cat_fcr_nom.id_nomenclature,
        })
        assert response.status_code == status.HTTP_201_CREATED
        fcr = Enjeu.objects.get(libelle='FCR Nouveau')
        assert fcr.is_fcr()

    def test_audit_field_set_on_create(self, api_client, enjeu_test_data):
        """Test id_utilisateur_ajout is set on create."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.post('/api/plans/enjeux/', {
            'id_pg': enjeu_test_data['plan'].id_pg,
            'id_categorie': enjeu_test_data['cat_enjeu'].id_nomenclature,
            'libelle': 'Enjeu Audit',
            'rang': 1,
        })
        assert response.status_code == status.HTTP_201_CREATED
        enjeu = Enjeu.objects.get(libelle='Enjeu Audit')
        assert enjeu.id_utilisateur_ajout == enjeu_test_data['super_admin']


# =============================================================================
# TestEnjeuDetailEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestEnjeuDetailEndpoint:
    """Tests for GET /api/plans/enjeux/{id}/"""

    def test_super_admin_gets_detail(self, api_client, enjeu_test_data):
        """Test super admin can retrieve enjeu detail."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.get(f'/api/plans/enjeux/{enjeu_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['libelle'] == 'Enjeu Biodiversité'

    def test_referent_gets_detail(self, api_client, enjeu_test_data):
        """Test referent can retrieve enjeu detail."""
        api_client.force_authenticate(user=enjeu_test_data['referent'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.get(f'/api/plans/enjeux/{enjeu_id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_detail_includes_facteurs_influence(self, api_client, enjeu_test_data):
        """Test detail includes nested facteurs_influence."""
        FacteurInfluenceFactory(
            id_enjeu=enjeu_test_data['enjeu1'],
            id_utilisateur_ajout=enjeu_test_data['referent']
        )
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.get(f'/api/plans/enjeux/{enjeu_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'facteurs_influence' in response.data
        assert len(response.data['facteurs_influence']) >= 1

    def test_detail_includes_taxons(self, api_client, enjeu_test_data):
        """Test detail includes nested taxons."""
        CorEnjeuTaxonFactory(id_enjeu=enjeu_test_data['enjeu1'])
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.get(f'/api/plans/enjeux/{enjeu_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'taxons' in response.data
        assert len(response.data['taxons']) >= 1

    def test_nb_facteurs_influence_correct(self, api_client, enjeu_test_data):
        """Test nb_facteurs_influence count is correct."""
        FacteurInfluenceFactory(
            id_enjeu=enjeu_test_data['enjeu1'],
            id_utilisateur_ajout=enjeu_test_data['referent']
        )
        FacteurInfluenceFactory(
            id_enjeu=enjeu_test_data['enjeu1'],
            id_utilisateur_ajout=enjeu_test_data['referent']
        )
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.get(f'/api/plans/enjeux/{enjeu_id}/')
        assert response.data['nb_facteurs_influence'] == 2

    def test_fcr_detail_includes_categorie_fcr_label(self, api_client, enjeu_test_data):
        """Test FCR detail includes categorie_fcr_label."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        fcr_id = enjeu_test_data['fcr1'].id_enjeu
        response = api_client.get(f'/api/plans/enjeux/{fcr_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'categorie_fcr_label' in response.data

    def test_nonexistent_id_returns_404(self, api_client, enjeu_test_data):
        """Test nonexistent ID returns 404."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TestEnjeuUpdateEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestEnjeuUpdateEndpoint:
    """Tests for PATCH /api/plans/enjeux/{id}/"""

    def test_super_admin_updates(self, api_client, enjeu_test_data):
        """Test super admin can update an enjeu."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.patch(f'/api/plans/enjeux/{enjeu_id}/', {
            'libelle': 'Enjeu Mis à Jour'
        })
        assert response.status_code == status.HTTP_200_OK
        enjeu_test_data['enjeu1'].refresh_from_db()
        assert enjeu_test_data['enjeu1'].libelle == 'Enjeu Mis à Jour'

    def test_referent_updates(self, api_client, enjeu_test_data):
        """Test referent can update an enjeu on their plan."""
        api_client.force_authenticate(user=enjeu_test_data['referent'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.patch(f'/api/plans/enjeux/{enjeu_id}/', {
            'libelle': 'Enjeu Mis à Jour Ref'
        })
        assert response.status_code == status.HTTP_200_OK

    def test_non_referent_denied(self, api_client, enjeu_test_data):
        """Test non-referent cannot update."""
        api_client.force_authenticate(user=enjeu_test_data['user'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.patch(f'/api/plans/enjeux/{enjeu_id}/', {
            'libelle': 'Should Fail'
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_patch_libelle_only(self, api_client, enjeu_test_data):
        """Test PATCH only libelle field."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        original_rang = enjeu_test_data['enjeu1'].rang
        response = api_client.patch(f'/api/plans/enjeux/{enjeu_id}/', {
            'libelle': 'Libelle Seul'
        })
        assert response.status_code == status.HTTP_200_OK
        enjeu_test_data['enjeu1'].refresh_from_db()
        assert enjeu_test_data['enjeu1'].rang == original_rang

    def test_update_rang(self, api_client, enjeu_test_data):
        """Test updating rang field."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.patch(f'/api/plans/enjeux/{enjeu_id}/', {
            'rang': 3
        })
        assert response.status_code == status.HTTP_200_OK
        enjeu_test_data['enjeu1'].refresh_from_db()
        assert enjeu_test_data['enjeu1'].rang == 3

    def test_update_taxon_ids_replaces(self, api_client, enjeu_test_data):
        """Test updating taxon_ids replaces existing taxons."""
        CorEnjeuTaxonFactory(id_enjeu=enjeu_test_data['enjeu1'], cd_nom=11111)
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.patch(f'/api/plans/enjeux/{enjeu_id}/', {
            'taxon_ids': [22222, 33333]
        }, format='json')
        assert response.status_code == status.HTTP_200_OK
        taxon_cds = list(enjeu_test_data['enjeu1'].taxons.values_list('cd_nom', flat=True))
        assert 11111 not in taxon_cds
        assert 22222 in taxon_cds
        assert 33333 in taxon_cds

    def test_audit_field_updated(self, api_client, enjeu_test_data):
        """Test id_utilisateur_maj is updated on PATCH."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.patch(f'/api/plans/enjeux/{enjeu_id}/', {
            'libelle': 'Updated for Audit'
        })
        assert response.status_code == status.HTTP_200_OK
        enjeu_test_data['enjeu1'].refresh_from_db()
        assert enjeu_test_data['enjeu1'].id_utilisateur_maj == enjeu_test_data['super_admin']

    def test_nonexistent_id_returns_404(self, api_client, enjeu_test_data):
        """Test updating nonexistent ID returns 404."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.patch('/api/plans/enjeux/99999/', {
            'libelle': 'Nope'
        })
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TestEnjeuDeleteEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestEnjeuDeleteEndpoint:
    """Tests for DELETE /api/plans/enjeux/{id}/"""

    def test_super_admin_deletes(self, api_client, enjeu_test_data):
        """Test super admin can delete an enjeu."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.delete(f'/api/plans/enjeux/{enjeu_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Enjeu.objects.filter(id_enjeu=enjeu_id).exists()

    def test_referent_deletes(self, api_client, enjeu_test_data):
        """Test referent can delete an enjeu on their plan."""
        api_client.force_authenticate(user=enjeu_test_data['referent'])
        enjeu_id = enjeu_test_data['enjeu2'].id_enjeu
        response = api_client.delete(f'/api/plans/enjeux/{enjeu_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_non_referent_denied(self, api_client, enjeu_test_data):
        """Test non-referent cannot delete."""
        api_client.force_authenticate(user=enjeu_test_data['user'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.delete(f'/api/plans/enjeux/{enjeu_id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_cascade_facteurs_deleted(self, api_client, enjeu_test_data):
        """Test deleting enjeu deletes its facteurs_influence (non partagés)."""
        enjeu = enjeu_test_data['enjeu1']
        facteur = FacteurInfluenceFactory(
            id_enjeu=enjeu, id_utilisateur_ajout=enjeu_test_data['referent']
        )
        facteur_id = facteur.id_facteur_influence

        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/enjeux/{enjeu.id_enjeu}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        # #552 — plus de FK : le facteur est supprimé parce qu'il devient
        # orphelin (aucun autre enjeu lié), pas par cascade de la base.
        assert not FacteurInfluence.objects.filter(pk=facteur_id).exists()

    def test_shared_facteur_survives_enjeu_deletion(self, api_client, enjeu_test_data):
        """#552 — un facteur partagé survit à la suppression de l'un de ses enjeux."""
        enjeu1 = enjeu_test_data['enjeu1']
        enjeu2 = enjeu_test_data['enjeu2']
        facteur = FacteurInfluenceFactory(
            enjeux=[enjeu1, enjeu2], id_utilisateur_ajout=enjeu_test_data['referent']
        )
        facteur_id = facteur.id_facteur_influence

        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/enjeux/{enjeu1.id_enjeu}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        facteur.refresh_from_db()
        assert list(facteur.enjeux.all()) == [enjeu2]

    def test_cascade_pressions_deleted(self, api_client, enjeu_test_data):
        """Test deleting enjeu cascades to pressions via facteurs."""
        enjeu = enjeu_test_data['enjeu1']
        facteur = FacteurInfluenceFactory(id_enjeu=enjeu, id_utilisateur_ajout=enjeu_test_data['referent'])
        PressionFactory(id_facteur_influence=facteur, id_utilisateur_ajout=enjeu_test_data['referent'])
        facteur_id = facteur.id_facteur_influence

        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.delete(f'/api/plans/enjeux/{enjeu.id_enjeu}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Pression.objects.filter(id_facteur_influence_id=facteur_id).exists()

    def test_nonexistent_id_returns_404(self, api_client, enjeu_test_data):
        """Test deleting nonexistent ID returns 404."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.delete('/api/plans/enjeux/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# TestEnjeuByPlanEndpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestEnjeuByPlanEndpoint:
    """Tests for GET /api/plans/enjeux/by-plan/{plan_id}/"""

    def test_unauthenticated_returns_401(self, api_client, enjeu_test_data):
        """Test unauthenticated access returns 401."""
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_gets_by_plan(self, api_client, enjeu_test_data):
        """Test super admin can get enjeux by plan."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['plan_id'] == plan_id
        assert response.data['plan_nom'] == 'Plan Test Enjeux'

    def test_referent_gets_own_plan(self, api_client, enjeu_test_data):
        """Test referent can get enjeux on their plan."""
        api_client.force_authenticate(user=enjeu_test_data['referent'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_response_structure(self, api_client, enjeu_test_data):
        """Test response has expected structure."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        assert 'plan_id' in response.data
        assert 'plan_nom' in response.data
        assert 'enjeux' in response.data
        assert 'fcr' in response.data
        assert 'total_enjeux' in response.data
        assert 'total_fcr' in response.data

    def test_enjeux_separated_from_fcr(self, api_client, enjeu_test_data):
        """Test enjeux and FCR are separated in response."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        assert response.data['total_enjeux'] >= 2  # enjeu1, enjeu2
        assert response.data['total_fcr'] >= 1  # fcr1

    def test_empty_plan_returns_zero_totals(self, api_client, enjeu_test_data):
        """Test empty plan returns zero totals."""
        empty_plan = PlanGestionFactory(statut='valide')
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=empty_plan, site=site)

        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get(f'/api/plans/enjeux/by-plan/{empty_plan.id_pg}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_enjeux'] == 0
        assert response.data['total_fcr'] == 0

    def test_facteurs_influence_nested(self, api_client, enjeu_test_data):
        """Test facteurs_influence are nested in enjeux."""
        FacteurInfluenceFactory(
            id_enjeu=enjeu_test_data['enjeu1'],
            id_utilisateur_ajout=enjeu_test_data['referent']
        )
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        # Find enjeu1 in the enjeux list
        enjeu1_data = next(
            (e for e in response.data['enjeux']
             if e['id_enjeu'] == enjeu_test_data['enjeu1'].id_enjeu),
            None
        )
        assert enjeu1_data is not None
        assert 'facteurs_influence' in enjeu1_data

    def test_nonexistent_plan_returns_404(self, api_client, enjeu_test_data):
        """Test nonexistent plan returns 404."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/by-plan/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_enjeux_sorted_by_rang_then_libelle(self, api_client, enjeu_test_data):
        """Test enjeux are sorted by rang then libelle."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        enjeux = response.data['enjeux']
        if len(enjeux) >= 2:
            # Check ordering: rang ascending, then libelle ascending
            for i in range(len(enjeux) - 1):
                if enjeux[i]['rang'] == enjeux[i + 1]['rang']:
                    assert enjeux[i]['libelle'] <= enjeux[i + 1]['libelle']
                else:
                    assert (enjeux[i]['rang'] or 0) <= (enjeux[i + 1]['rang'] or 0)


# =============================================================================
# TestEnjeuTaxonHabitatActions
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestEnjeuTaxonHabitatActions:
    """Tests for add_taxon, remove_taxon, add_habitat, remove_habitat actions."""

    def test_add_taxon(self, api_client, enjeu_test_data):
        """Test adding a taxon to an enjeu."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.post(f'/api/plans/enjeux/{enjeu_id}/add_taxon/', {
            'cd_nom': 55555,
            'nom_complet': 'Taxon Test'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert CorEnjeuTaxon.objects.filter(id_enjeu_id=enjeu_id, cd_nom=55555).exists()

    def test_add_taxon_duplicate_returns_400(self, api_client, enjeu_test_data):
        """Test adding duplicate taxon returns 400."""
        CorEnjeuTaxonFactory(id_enjeu=enjeu_test_data['enjeu1'], cd_nom=55555)
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.post(f'/api/plans/enjeux/{enjeu_id}/add_taxon/', {
            'cd_nom': 55555,
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_taxon(self, api_client, enjeu_test_data):
        """Test removing a taxon from an enjeu."""
        CorEnjeuTaxonFactory(id_enjeu=enjeu_test_data['enjeu1'], cd_nom=55555)
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.delete(f'/api/plans/enjeux/{enjeu_id}/remove_taxon/55555/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CorEnjeuTaxon.objects.filter(id_enjeu_id=enjeu_id, cd_nom=55555).exists()

    def test_remove_nonexistent_taxon_returns_404(self, api_client, enjeu_test_data):
        """Test removing nonexistent taxon returns 404."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.delete(f'/api/plans/enjeux/{enjeu_id}/remove_taxon/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_habitat(self, api_client, enjeu_test_data):
        """Test adding a habitat to an enjeu."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.post(f'/api/plans/enjeux/{enjeu_id}/add_habitat/', {
            'cd_hab': 'HAB_TEST',
            'lb_hab_fr': 'Habitat Test'
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert CorEnjeuHabitat.objects.filter(id_enjeu_id=enjeu_id, cd_hab='HAB_TEST').exists()

    def test_add_habitat_duplicate_returns_400(self, api_client, enjeu_test_data):
        """Test adding duplicate habitat returns 400."""
        CorEnjeuHabitatFactory(id_enjeu=enjeu_test_data['enjeu1'], cd_hab='HAB_DUP')
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.post(f'/api/plans/enjeux/{enjeu_id}/add_habitat/', {
            'cd_hab': 'HAB_DUP',
        })
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_remove_habitat(self, api_client, enjeu_test_data):
        """Test removing a habitat from an enjeu."""
        CorEnjeuHabitatFactory(id_enjeu=enjeu_test_data['enjeu1'], cd_hab='HAB_RM')
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        enjeu_id = enjeu_test_data['enjeu1'].id_enjeu
        response = api_client.delete(f'/api/plans/enjeux/{enjeu_id}/remove_habitat/HAB_RM/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_stats_endpoint(self, api_client, enjeu_test_data):
        """Test stats endpoint returns correct structure."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/stats/')
        assert response.status_code == status.HTTP_200_OK
        assert 'total_enjeux' in response.data
        assert 'total_fcr' in response.data
        assert 'par_priorite' in response.data
        assert 'par_type' in response.data


# =============================================================================
# TestEnjeuFilters
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestEnjeuFilters:
    """Tests for EnjeuFilter on /api/plans/enjeux/"""

    def test_filter_by_id_pg(self, api_client, enjeu_test_data):
        """Test filter by plan ID."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/?id_pg={plan_id}')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['id_pg'] == plan_id

    def test_filter_is_enjeu_true(self, api_client, enjeu_test_data):
        """Test filter is_enjeu=true."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?is_enjeu=true')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['categorie_mnemonique'] == 'ENJEU'

    def test_filter_is_fcr_true(self, api_client, enjeu_test_data):
        """Test filter is_fcr=true."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?is_fcr=true')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['categorie_mnemonique'] == 'FCR'

    def test_filter_by_rang(self, api_client, enjeu_test_data):
        """Test filter by exact rang."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?rang=1')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['rang'] == 1

    def test_filter_rang_min(self, api_client, enjeu_test_data):
        """Test filter by rang_min."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?rang_min=2')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            if item['rang'] is not None:
                assert item['rang'] >= 2

    def test_filter_rang_max(self, api_client, enjeu_test_data):
        """Test filter by rang_max."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?rang_max=2')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            if item['rang'] is not None:
                assert item['rang'] <= 2

    def test_filter_categorie_ecologique(self, api_client, enjeu_test_data):
        """Test filter by categorie_ecologique."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?categorie_ecologique=true')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['categorie_ecologique'] is True

    def test_filter_habitat_true(self, api_client, enjeu_test_data):
        """Test filter habitat=true."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?habitat=true')
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['habitat'] is True

    def test_filter_has_taxons(self, api_client, enjeu_test_data):
        """Test filter has_taxons=true."""
        CorEnjeuTaxonFactory(id_enjeu=enjeu_test_data['enjeu1'])
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?has_taxons=true')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_filter_has_habitats(self, api_client, enjeu_test_data):
        """Test filter has_habitats=true."""
        CorEnjeuHabitatFactory(id_enjeu=enjeu_test_data['enjeu1'])
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?has_habitats=true')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_filter_search(self, api_client, enjeu_test_data):
        """Test search filter on libelle."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?search=Paysage')
        assert response.status_code == status.HTTP_200_OK
        libelles = [e['libelle'] for e in response.data['results']]
        assert 'Enjeu Paysage' in libelles

    def test_combined_filters(self, api_client, enjeu_test_data):
        """Test combining multiple filters."""
        plan_id = enjeu_test_data['plan'].id_pg
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get(
            f'/api/plans/enjeux/?id_pg={plan_id}&rang=1&categorie_ecologique=true'
        )
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['id_pg'] == plan_id
            assert item['rang'] == 1
            assert item['categorie_ecologique'] is True

    def test_filter_returns_empty_when_no_match(self, api_client, enjeu_test_data):
        """Test filters return empty results when nothing matches."""
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        response = api_client.get('/api/plans/enjeux/?search=ZZZNoMatchXXX')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) == 0


# =============================================================================
# TestByPlanScoreOverrides (#518)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestByPlanScoreOverrides:
    """#518 — l'endpoint by-plan expose les scores forcés manuellement
    (override au niveau indicateur) pour que le tableau de bord les affiche."""

    def _indicateur_on_plan(self, enjeu_test_data):
        from tests.factories.enjeux import (
            ObjectifLongTermeFactory, NiveauExigenceFactory, IndicateurFactory,
        )
        olt = ObjectifLongTermeFactory(id_enjeu=enjeu_test_data['enjeu1'])
        ne = NiveauExigenceFactory(id_olt=olt)
        # #518 — type figé sur ETAT : la mnemonique de la factory cycle
        # ETAT/PRESSION/REPONSE, et un indicateur REPONSE serait exclu de
        # l'endpoint by-plan (#477), rendant le test dépendant de l'ordre.
        return IndicateurFactory(
            id_ne=ne,
            type_indicateur__cd_nomenclature='ETAT',
            type_indicateur__mnemonique='ETAT',
        )

    def test_score_overrides_exposes_manual_score(self, api_client, enjeu_test_data):
        """Un IndicateurMesure avec score_override est renvoyé dans score_overrides."""
        from apps.plans.models_indicateurs import IndicateurMesure
        indic = self._indicateur_on_plan(enjeu_test_data)
        IndicateurMesure.objects.create(
            id_indicateur=indic, annee=2024, score_override=5,
        )

        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        assert response.status_code == status.HTTP_200_OK

        found = self._find_indicateur(response.data, indic.id_indicateur)
        assert found is not None
        assert found['score_overrides'] == {'2024': 5}

    def test_score_overrides_empty_without_override(self, api_client, enjeu_test_data):
        """Sans override, score_overrides est un dictionnaire vide."""
        indic = self._indicateur_on_plan(enjeu_test_data)

        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        assert response.status_code == status.HTTP_200_OK

        found = self._find_indicateur(response.data, indic.id_indicateur)
        assert found is not None
        assert found['score_overrides'] == {}

    def test_global_score_override_exposed(self, api_client, enjeu_test_data):
        """#518 (2e retour) — l'évaluation globale forcée manuellement (#356)
        est renvoyée dans `global_score_override` pour la colonne « Global »."""
        from apps.plans.models_indicateurs import IndicateurRealisationGlobale
        indic = self._indicateur_on_plan(enjeu_test_data)
        IndicateurRealisationGlobale.objects.create(
            id_indicateur=indic, score_override=4,
        )

        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        assert response.status_code == status.HTTP_200_OK

        found = self._find_indicateur(response.data, indic.id_indicateur)
        assert found is not None
        assert found['global_score_override'] == 4

    def test_global_score_override_null_without_force(self, api_client, enjeu_test_data):
        """Sans évaluation globale forcée, `global_score_override` vaut None."""
        indic = self._indicateur_on_plan(enjeu_test_data)

        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        assert response.status_code == status.HTTP_200_OK

        found = self._find_indicateur(response.data, indic.id_indicateur)
        assert found is not None
        assert found['global_score_override'] is None

    def test_global_score_override_null_when_comment_only(self, api_client, enjeu_test_data):
        """Un commentaire global seul (sans score forcé) ne pose pas d'override."""
        from apps.plans.models_indicateurs import IndicateurRealisationGlobale
        indic = self._indicateur_on_plan(enjeu_test_data)
        IndicateurRealisationGlobale.objects.create(
            id_indicateur=indic, score_override=None, commentaire_override="RAS",
        )

        api_client.force_authenticate(user=enjeu_test_data['super_admin'])
        plan_id = enjeu_test_data['plan'].id_pg
        response = api_client.get(f'/api/plans/enjeux/by-plan/{plan_id}/')
        assert response.status_code == status.HTTP_200_OK

        found = self._find_indicateur(response.data, indic.id_indicateur)
        assert found is not None
        assert found['global_score_override'] is None

    def test_upsert_accepts_indetermine_override(self, api_client, enjeu_test_data):
        """#519 — score_override = 0 (« indéterminé ») est accepté et résolu
        comme une surcharge effective (rond gris du tableau de bord)."""
        indic = self._indicateur_on_plan(enjeu_test_data)
        api_client.force_authenticate(user=enjeu_test_data['super_admin'])

        resp = api_client.post(
            '/api/plans/indicateur-mesures/upsert/',
            {'id_indicateur': indic.id_indicateur, 'annee': 2024, 'score_override': 0},
            format='json',
        )
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['score_override'] == 0

        resolved = api_client.get(
            '/api/plans/indicateur-mesures/resolved/',
            {'id_indicateur': indic.id_indicateur, 'annee': 2024},
        )
        assert resolved.status_code == status.HTTP_200_OK
        assert resolved.data['is_overridden'] is True
        assert resolved.data['score_override'] == 0
        assert resolved.data['score_effective'] == 0

    @staticmethod
    def _find_indicateur(payload, indic_id):
        for enjeu in [*payload.get('enjeux', []), *payload.get('fcr', [])]:
            for olt in enjeu.get('objectifs_long_terme', []):
                for ne in olt.get('niveaux_exigence', []):
                    for ind in ne.get('indicateurs', []):
                        if ind['id_indicateur'] == indic_id:
                            return ind
        return None
