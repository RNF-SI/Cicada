"""
Tests d'intégration pour l'API REST Objectifs Opérationnels (OO) et Résultats Attendus (RA).
"""
import pytest
from rest_framework import status

from apps.plans.models_enjeux import ObjectifOperationnel, ResultatAttendu
from apps.plans.models_indicateurs import Indicateur
from tests.factories.enjeux import (
    EnjeuFactory, FacteurInfluenceFactory, PressionFactory,
    ObjectifOperationnelFactory, ResultatAttenduFactory,
    IndicateurPressionFactory, MetriqueFactory,
    NomenclatureEnjeuFactory, NomenclatureTypeIndicateurFactory,
    NomenclatureTypeMetriqueFactory,
)
from tests.factories.plans import PlanGestionFactory, CorSitePgFactory
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, SiteFactory, OrganismeFactory,
    CorRoleSiteFactory, CorOgSiteFactory,
)


@pytest.fixture
def oo_test_data(db):
    """Fixture providing test data for OO and RA tests."""
    organisme = OrganismeFactory()
    site = SiteFactory()
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionFactory(nom='Plan OO Test', statut='valide')
    CorSitePgFactory(plan_de_gestion=plan, site=site)

    super_admin = SuperAdminFactory()
    admin_og = AdminOrganismeFactory(id_organisme=organisme)
    referent = ReferentFactory(id_organisme=organisme)
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    plan.referents.add(referent)
    user = RoleFactory()

    cat_enjeu = NomenclatureEnjeuFactory()
    enjeu = EnjeuFactory(
        id_pg=plan, id_categorie=cat_enjeu, libelle='Enjeu OO Test',
        id_utilisateur_ajout=referent
    )
    facteur = FacteurInfluenceFactory(
        id_enjeu=enjeu, libelle='Facteur Urbanisation',
        id_utilisateur_ajout=referent
    )
    facteur2 = FacteurInfluenceFactory(
        id_enjeu=enjeu, libelle='Facteur Climat',
        id_utilisateur_ajout=referent
    )
    pression1 = PressionFactory(
        id_facteur_influence=facteur, libelle='Pression Urbaine',
        id_utilisateur_ajout=referent
    )
    pression2 = PressionFactory(
        id_facteur_influence=facteur2, libelle='Pression Climatique',
        id_utilisateur_ajout=referent
    )
    oo1 = ObjectifOperationnelFactory(
        libelle='OO Réduire pressions',
        description='Réduire les pressions anthropiques',
        id_utilisateur_ajout=referent,
        pressions=[pression1]
    )
    oo2 = ObjectifOperationnelFactory(
        libelle='OO Restaurer habitats',
        id_utilisateur_ajout=referent,
        pressions=[pression2]
    )
    ra1 = ResultatAttenduFactory(
        id_oo=oo1, libelle='RA Surface restaurée',
        description='100 ha de surface restaurée',
        id_utilisateur_ajout=referent
    )
    ra2 = ResultatAttenduFactory(
        id_oo=oo1, libelle='RA Qualité eau',
        id_utilisateur_ajout=referent
    )

    type_ind = NomenclatureTypeIndicateurFactory()
    type_met = NomenclatureTypeMetriqueFactory()

    indicateur_pression = IndicateurPressionFactory(
        id_resultat_attendu=ra1,
        nom_indicateur='Indicateur Pression Test',
        type_indicateur=type_ind,
        id_utilisateur_ajout=referent
    )
    metrique_pression = MetriqueFactory(
        id_indicateur=indicateur_pression,
        nom_metrique='Métrique Pression Test',
        type_metrique=type_met, unite='ha',
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
        'facteur': facteur,
        'facteur2': facteur2,
        'pression1': pression1,
        'pression2': pression2,
        'oo1': oo1,
        'oo2': oo2,
        'ra1': ra1,
        'ra2': ra2,
        'type_ind': type_ind,
        'type_met': type_met,
        'indicateur_pression': indicateur_pression,
        'metrique_pression': metrique_pression,
    }


# =============================================================================
# ObjectifOperationnel CRUD
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifOperationnelList:
    """Tests for GET /api/plans/objectifs-operationnels/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/objectifs-operationnels/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, oo_test_data):
        """Test super admin can see all OOs."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        response = api_client.get('/api/plans/objectifs-operationnels/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_referent_sees_own(self, api_client, oo_test_data):
        """Test referent sees OOs from their plans."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        response = api_client.get('/api/plans/objectifs-operationnels/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2


@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifOperationnelCreate:
    """Tests for POST /api/plans/objectifs-operationnels/"""

    def test_referent_creates(self, api_client, oo_test_data):
        """Test referent can create an OO."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        response = api_client.post('/api/plans/objectifs-operationnels/', {
            'pression_ids': [oo_test_data['pression1'].id_pression],
            'libelle': 'Nouvel OO',
            'description': 'Description test',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert ObjectifOperationnel.objects.filter(libelle='Nouvel OO').exists()

    def test_referent_creates_with_multiple_pressions(self, api_client, oo_test_data):
        """Test referent can create an OO linked to multiple pressions."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        p1_id = oo_test_data['pression1'].id_pression
        p2_id = oo_test_data['pression2'].id_pression
        response = api_client.post('/api/plans/objectifs-operationnels/', {
            'pression_ids': [p1_id, p2_id],
            'libelle': 'OO Multi-Pression',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        oo = ObjectifOperationnel.objects.get(libelle='OO Multi-Pression')
        assert set(oo.pressions.values_list('id_pression', flat=True)) == {p1_id, p2_id}

    def test_non_referent_denied(self, api_client, oo_test_data):
        """Test non-referent cannot create."""
        api_client.force_authenticate(user=oo_test_data['user'])
        response = api_client.post('/api/plans/objectifs-operationnels/', {
            'pression_ids': [oo_test_data['pression1'].id_pression],
            'libelle': 'Should Fail',
        }, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_audit_fields_set(self, api_client, oo_test_data):
        """Test audit fields are set on create."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        response = api_client.post('/api/plans/objectifs-operationnels/', {
            'pression_ids': [oo_test_data['pression1'].id_pression],
            'libelle': 'OO Audit',
        }, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        oo = ObjectifOperationnel.objects.get(libelle='OO Audit')
        assert oo.id_utilisateur_ajout == oo_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifOperationnelDetail:
    """Tests for GET/PATCH/DELETE /api/plans/objectifs-operationnels/{id}/"""

    def test_referent_gets_detail(self, api_client, oo_test_data):
        """Test referent can retrieve OO detail."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        oo_id = oo_test_data['oo1'].id_oo
        response = api_client.get(f'/api/plans/objectifs-operationnels/{oo_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['libelle'] == 'OO Réduire pressions'

    def test_detail_includes_resultats_attendus(self, api_client, oo_test_data):
        """Test detail includes nested resultats attendus."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        oo_id = oo_test_data['oo1'].id_oo
        response = api_client.get(f'/api/plans/objectifs-operationnels/{oo_id}/')
        assert 'resultats_attendus' in response.data
        assert len(response.data['resultats_attendus']) >= 2

    def test_detail_includes_pressions(self, api_client, oo_test_data):
        """Test detail includes pressions M2M with facteur libelle."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        oo_id = oo_test_data['oo1'].id_oo
        response = api_client.get(f'/api/plans/objectifs-operationnels/{oo_id}/')
        assert 'pressions' in response.data
        assert len(response.data['pressions']) >= 1
        assert response.data['pressions'][0]['facteur_influence_libelle'] == 'Facteur Urbanisation'
        assert 'pression_ids' in response.data
        assert oo_test_data['pression1'].id_pression in response.data['pression_ids']

    def test_nb_resultats_attendus_correct(self, api_client, oo_test_data):
        """Test nb_resultats_attendus is correct."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        oo_id = oo_test_data['oo1'].id_oo
        response = api_client.get(f'/api/plans/objectifs-operationnels/{oo_id}/')
        assert response.data['nb_resultats_attendus'] == 2

    def test_nonexistent_returns_404(self, api_client, oo_test_data):
        """Test nonexistent OO returns 404."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        response = api_client.get('/api/plans/objectifs-operationnels/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_referent_updates(self, api_client, oo_test_data):
        """Test referent can update an OO."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        oo_id = oo_test_data['oo1'].id_oo
        response = api_client.patch(f'/api/plans/objectifs-operationnels/{oo_id}/', {
            'libelle': 'OO Mis à Jour'
        })
        assert response.status_code == status.HTTP_200_OK
        oo_test_data['oo1'].refresh_from_db()
        assert oo_test_data['oo1'].libelle == 'OO Mis à Jour'

    def test_referent_deletes(self, api_client, oo_test_data):
        """Test referent can delete an OO."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        oo_id = oo_test_data['oo2'].id_oo
        response = api_client.delete(f'/api/plans/objectifs-operationnels/{oo_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ObjectifOperationnel.objects.filter(id_oo=oo_id).exists()

    def test_non_referent_delete_denied(self, api_client, oo_test_data):
        """Test non-referent cannot delete."""
        api_client.force_authenticate(user=oo_test_data['user'])
        oo_id = oo_test_data['oo1'].id_oo
        response = api_client.delete(f'/api/plans/objectifs-operationnels/{oo_id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# OO by-facteur endpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestObjectifOperationnelByPression:
    """Tests for GET /api/plans/objectifs-operationnels/by-pression/{pression_id}/"""

    def test_unauthenticated_returns_401(self, api_client, oo_test_data):
        """Test unauthenticated access returns 401."""
        pression_id = oo_test_data['pression1'].id_pression
        response = api_client.get(f'/api/plans/objectifs-operationnels/by-pression/{pression_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_referent_gets_by_pression(self, api_client, oo_test_data):
        """Test referent can get OOs by pression."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        pression_id = oo_test_data['pression1'].id_pression
        response = api_client.get(f'/api/plans/objectifs-operationnels/by-pression/{pression_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'pression_id' in response.data
        assert 'objectifs_operationnels' in response.data
        assert 'total' in response.data
        assert response.data['total'] >= 1

    def test_nonexistent_pression_returns_404(self, api_client, oo_test_data):
        """Test nonexistent pression returns 404."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        response = api_client.get('/api/plans/objectifs-operationnels/by-pression/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# ResultatAttendu CRUD
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestResultatAttenduList:
    """Tests for GET /api/plans/resultats-attendus/"""

    def test_unauthenticated_returns_401(self, api_client):
        """Test unauthenticated access returns 401."""
        response = api_client.get('/api/plans/resultats-attendus/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_super_admin_sees_all(self, api_client, oo_test_data):
        """Test super admin can see all RAs."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        response = api_client.get('/api/plans/resultats-attendus/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2

    def test_referent_sees_own(self, api_client, oo_test_data):
        """Test referent sees RAs from their plans."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        response = api_client.get('/api/plans/resultats-attendus/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 2


@pytest.mark.django_db
@pytest.mark.integration
class TestResultatAttenduCreate:
    """Tests for POST /api/plans/resultats-attendus/"""

    def test_referent_creates(self, api_client, oo_test_data):
        """Test referent can create a RA."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        response = api_client.post('/api/plans/resultats-attendus/', {
            'id_oo': oo_test_data['oo1'].id_oo,
            'libelle': 'Nouveau RA',
            'description': 'Description test',
        })
        assert response.status_code == status.HTTP_201_CREATED
        assert ResultatAttendu.objects.filter(libelle='Nouveau RA').exists()

    def test_non_referent_denied(self, api_client, oo_test_data):
        """Test non-referent cannot create."""
        api_client.force_authenticate(user=oo_test_data['user'])
        response = api_client.post('/api/plans/resultats-attendus/', {
            'id_oo': oo_test_data['oo1'].id_oo,
            'libelle': 'Should Fail',
        })
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_audit_fields_set(self, api_client, oo_test_data):
        """Test audit fields are set on create."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        response = api_client.post('/api/plans/resultats-attendus/', {
            'id_oo': oo_test_data['oo1'].id_oo,
            'libelle': 'RA Audit',
        })
        assert response.status_code == status.HTTP_201_CREATED
        ra = ResultatAttendu.objects.get(libelle='RA Audit')
        assert ra.id_utilisateur_ajout == oo_test_data['super_admin']


@pytest.mark.django_db
@pytest.mark.integration
class TestResultatAttenduDetail:
    """Tests for GET/PATCH/DELETE /api/plans/resultats-attendus/{id}/"""

    def test_referent_gets_detail(self, api_client, oo_test_data):
        """Test referent can retrieve RA detail."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        ra_id = oo_test_data['ra1'].id_ra
        response = api_client.get(f'/api/plans/resultats-attendus/{ra_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['libelle'] == 'RA Surface restaurée'

    def test_detail_includes_indicateurs(self, api_client, oo_test_data):
        """Test detail includes nested indicateurs."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        ra_id = oo_test_data['ra1'].id_ra
        response = api_client.get(f'/api/plans/resultats-attendus/{ra_id}/')
        assert 'indicateurs' in response.data
        assert len(response.data['indicateurs']) >= 1

    def test_nb_indicateurs_correct(self, api_client, oo_test_data):
        """Test nb_indicateurs is correct."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        ra_id = oo_test_data['ra1'].id_ra
        response = api_client.get(f'/api/plans/resultats-attendus/{ra_id}/')
        assert response.data['nb_indicateurs'] == 1

    def test_nonexistent_returns_404(self, api_client, oo_test_data):
        """Test nonexistent RA returns 404."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        response = api_client.get('/api/plans/resultats-attendus/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_referent_updates(self, api_client, oo_test_data):
        """Test referent can update a RA."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        ra_id = oo_test_data['ra1'].id_ra
        response = api_client.patch(f'/api/plans/resultats-attendus/{ra_id}/', {
            'libelle': 'RA Mis à Jour'
        })
        assert response.status_code == status.HTTP_200_OK
        oo_test_data['ra1'].refresh_from_db()
        assert oo_test_data['ra1'].libelle == 'RA Mis à Jour'

    def test_referent_deletes(self, api_client, oo_test_data):
        """Test referent can delete a RA."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        ra_id = oo_test_data['ra2'].id_ra
        response = api_client.delete(f'/api/plans/resultats-attendus/{ra_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ResultatAttendu.objects.filter(id_ra=ra_id).exists()

    def test_non_referent_delete_denied(self, api_client, oo_test_data):
        """Test non-referent cannot delete."""
        api_client.force_authenticate(user=oo_test_data['user'])
        ra_id = oo_test_data['ra1'].id_ra
        response = api_client.delete(f'/api/plans/resultats-attendus/{ra_id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN


# =============================================================================
# RA by-oo endpoint
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestResultatAttenduByOo:
    """Tests for GET /api/plans/resultats-attendus/by-oo/{oo_id}/"""

    def test_unauthenticated_returns_401(self, api_client, oo_test_data):
        """Test unauthenticated access returns 401."""
        oo_id = oo_test_data['oo1'].id_oo
        response = api_client.get(f'/api/plans/resultats-attendus/by-oo/{oo_id}/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_referent_gets_by_oo(self, api_client, oo_test_data):
        """Test referent can get RAs by OO."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        oo_id = oo_test_data['oo1'].id_oo
        response = api_client.get(f'/api/plans/resultats-attendus/by-oo/{oo_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'oo_id' in response.data
        assert 'resultats_attendus' in response.data
        assert 'total' in response.data
        assert response.data['total'] >= 2

    def test_empty_oo_returns_empty_list(self, api_client, oo_test_data):
        """Test OO without RAs returns empty list."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        oo_id = oo_test_data['oo2'].id_oo
        response = api_client.get(f'/api/plans/resultats-attendus/by-oo/{oo_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['total'] == 0
        assert len(response.data['resultats_attendus']) == 0

    def test_nonexistent_oo_returns_404(self, api_client, oo_test_data):
        """Test nonexistent OO returns 404."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        response = api_client.get('/api/plans/resultats-attendus/by-oo/99999/')
        assert response.status_code == status.HTTP_404_NOT_FOUND


# =============================================================================
# Indicateur de pression (via id_resultat_attendu)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestIndicateurPressionCreate:
    """Tests for creating indicateurs linked to ResultatAttendu."""

    def test_referent_creates_with_resultat_attendu(self, api_client, oo_test_data):
        """Test referent can create an indicateur linked to a RA."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        response = api_client.post('/api/plans/indicateurs/', {
            'id_resultat_attendu': oo_test_data['ra1'].id_ra,
            'nom_indicateur': 'Indicateur Pression Nouveau',
        })
        assert response.status_code == status.HTTP_201_CREATED
        ind = Indicateur.objects.get(nom_indicateur='Indicateur Pression Nouveau')
        assert ind.id_resultat_attendu == oo_test_data['ra1']
        assert ind.id_ne is None

    def test_by_ra_endpoint(self, api_client, oo_test_data):
        """Test the by-ra endpoint returns indicateurs for a RA."""
        api_client.force_authenticate(user=oo_test_data['referent'])
        ra_id = oo_test_data['ra1'].id_ra
        response = api_client.get(f'/api/plans/indicateurs/by-ra/{ra_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'ra_id' in response.data
        assert 'indicateurs' in response.data
        assert response.data['total'] >= 1


# =============================================================================
# Cascade delete
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestOoCascadeDelete:
    """Tests for cascade delete in OO hierarchy."""

    def test_delete_oo_cascades_to_ra(self, api_client, oo_test_data):
        """Test deleting an OO cascades to its RAs."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        oo_id = oo_test_data['oo1'].id_oo
        ra_id = oo_test_data['ra1'].id_ra
        response = api_client.delete(f'/api/plans/objectifs-operationnels/{oo_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not ResultatAttendu.objects.filter(id_ra=ra_id).exists()

    def test_delete_oo_cascades_to_indicateurs(self, api_client, oo_test_data):
        """Test deleting an OO cascades to indicateurs de pression."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        oo_id = oo_test_data['oo1'].id_oo
        ind_id = oo_test_data['indicateur_pression'].id_indicateur
        response = api_client.delete(f'/api/plans/objectifs-operationnels/{oo_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Indicateur.objects.filter(id_indicateur=ind_id).exists()

    def test_delete_ra_cascades_to_indicateurs(self, api_client, oo_test_data):
        """Test deleting a RA cascades to its indicateurs."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        ra_id = oo_test_data['ra1'].id_ra
        ind_id = oo_test_data['indicateur_pression'].id_indicateur
        response = api_client.delete(f'/api/plans/resultats-attendus/{ra_id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Indicateur.objects.filter(id_indicateur=ind_id).exists()

    def test_delete_oo_does_not_delete_pression(self, api_client, oo_test_data):
        """Test deleting an OO does not delete the parent pression."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        oo_id = oo_test_data['oo1'].id_oo
        pression_id = oo_test_data['pression1'].id_pression
        api_client.delete(f'/api/plans/objectifs-operationnels/{oo_id}/')
        from apps.plans.models_enjeux import Pression
        assert Pression.objects.filter(id_pression=pression_id).exists()


# =============================================================================
# Enjeu detail includes OOs (via facteurs_influence)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.integration
class TestEnjeuDetailIncludesOo:
    """Tests that enjeu detail endpoint includes OOs nested under facteurs_influence."""

    def test_enjeu_detail_includes_pressions_with_oo(self, api_client, oo_test_data):
        """Test enjeu detail includes pressions with objectifs_operationnels under facteurs."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        enjeu_id = oo_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/enjeux/{enjeu_id}/')
        assert response.status_code == status.HTTP_200_OK
        assert 'facteurs_influence' in response.data
        # Collect all OOs from all pressions under all facteurs
        all_oos = []
        for fi in response.data['facteurs_influence']:
            assert 'pressions' in fi
            for pression in fi['pressions']:
                assert 'objectifs_operationnels' in pression
                all_oos.extend(pression['objectifs_operationnels'])
        assert len(all_oos) >= 2

    def test_enjeu_detail_pression_nb_oo(self, api_client, oo_test_data):
        """Test pression includes nb_objectifs_operationnels count."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        enjeu_id = oo_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/enjeux/{enjeu_id}/')
        facteur = next(
            fi for fi in response.data['facteurs_influence']
            if fi['libelle'] == 'Facteur Urbanisation'
        )
        pression = next(
            p for p in facteur['pressions']
            if p['libelle'] == 'Pression Urbaine'
        )
        assert pression['nb_objectifs_operationnels'] == 1

    def test_enjeu_detail_oo_nested_ra(self, api_client, oo_test_data):
        """Test enjeu detail includes nested RAs in OOs under pressions."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        enjeu_id = oo_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/enjeux/{enjeu_id}/')
        # Find OO under pression under facteur Urbanisation
        facteur = next(
            fi for fi in response.data['facteurs_influence']
            if fi['libelle'] == 'Facteur Urbanisation'
        )
        pression = facteur['pressions'][0]
        oo_with_ra = next(
            oo for oo in pression['objectifs_operationnels']
            if oo['libelle'] == 'OO Réduire pressions'
        )
        assert 'resultats_attendus' in oo_with_ra
        assert len(oo_with_ra['resultats_attendus']) >= 2

    def test_enjeu_detail_ra_nested_indicateurs(self, api_client, oo_test_data):
        """Test enjeu detail includes nested indicateurs in RAs under pressions."""
        api_client.force_authenticate(user=oo_test_data['super_admin'])
        enjeu_id = oo_test_data['enjeu'].id_enjeu
        response = api_client.get(f'/api/plans/enjeux/{enjeu_id}/')
        facteur = next(
            fi for fi in response.data['facteurs_influence']
            if fi['libelle'] == 'Facteur Urbanisation'
        )
        pression = facteur['pressions'][0]
        oo_with_ra = next(
            oo for oo in pression['objectifs_operationnels']
            if oo['libelle'] == 'OO Réduire pressions'
        )
        ra_with_ind = next(
            ra for ra in oo_with_ra['resultats_attendus']
            if ra['libelle'] == 'RA Surface restaurée'
        )
        assert 'indicateurs' in ra_with_ind
        assert len(ra_with_ind['indicateurs']) >= 1
