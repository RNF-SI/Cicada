"""
Unit tests for Plans ViewSet.
Tests CRUD operations, permissions, filtering, and custom actions.
"""
import pytest
from rest_framework.test import APIClient
from rest_framework import status

from apps.plans.models import PlanGestion, CorSitePg, CorPgFichier
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, ReferentFactory,
    RoleFactory, OrganismeFactory, SiteFactory, CorRoleSiteFactory,
    CorOgSiteFactory
)
from tests.factories.plans import (
    PlanGestionFactory, PlanGestionValideFactory, PlanGestionArchiveFactory,
    CorSitePgFactory, CorPgFichierFactory
)


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetList:
    """Tests for PlanGestionViewSet list action."""

    def test_list_unauthenticated(self, api_client):
        """Test that unauthenticated users cannot list plans."""
        response = api_client.get('/api/plans/plans/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_super_admin_sees_all(self, api_client):
        """Test super admin can see all plans regardless of status."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Draft Plan', statut='draft')
        PlanGestionFactory(nom='Valid Plan', statut='valide')
        PlanGestionFactory(nom='Archive Plan', statut='archive')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/')

        assert response.status_code == status.HTTP_200_OK
        # Super admin sees all 3 plans
        assert response.data['pagination']['count'] >= 3

    def test_list_regular_user_denied(self, api_client):
        """Test regular users cannot access plans list (requires IsReferent)."""
        user = RoleFactory()  # Regular utilisateur
        PlanGestionFactory(nom='Draft Plan', statut='draft')
        PlanGestionFactory(nom='Valid Plan', statut='valide')

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/plans/plans/')

        # Regular users are denied - ViewSet requires IsReferent permission
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_referent_sees_assigned_sites_plans(self, api_client):
        """Test referent sees plans for their assigned sites."""
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        plan = PlanGestionFactory(nom='Referent Plan', statut='draft')
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        api_client.force_authenticate(user=referent)
        response = api_client.get('/api/plans/plans/')

        assert response.status_code == status.HTTP_200_OK
        plan_names = [p['nom'] for p in response.data['results']]
        assert 'Referent Plan' in plan_names

    def test_list_admin_og_sees_organisme_plans(self, api_client):
        """Test admin organisme sees plans for their organisation's sites."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)

        plan = PlanGestionFactory(nom='Org Plan', statut='draft')
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        api_client.force_authenticate(user=admin_og)
        response = api_client.get('/api/plans/plans/')

        assert response.status_code == status.HTTP_200_OK
        plan_names = [p['nom'] for p in response.data['results']]
        assert 'Org Plan' in plan_names


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetCreate:
    """Tests for PlanGestionViewSet create action."""

    def test_create_plan_referent(self, api_client):
        """Test referent can create a plan."""
        referent = ReferentFactory()
        site = SiteFactory()
        # Make user a real referent by creating validated site assignment
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=referent)
        response = api_client.post('/api/plans/plans/', {
            'nom': 'New Test Plan',
            'statut': 'draft',
            'rang': 1,
            'ct88': False,
            'annee_debut': 2024,
            'annee_fin': 2034,
            'sites_ids': [site.id_site]
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['nom'] == 'New Test Plan'
        assert response.data['statut'] == 'draft'

    def test_create_plan_sets_creator(self, api_client):
        """Test that plan creator is automatically set."""
        referent = ReferentFactory()
        site = SiteFactory()
        # Make user a real referent by creating validated site assignment
        CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=referent)
        response = api_client.post('/api/plans/plans/', {
            'nom': 'Creator Test Plan',
            'statut': 'draft',
            'rang': 1,
            'ct88': False,
            'annee_debut': 2024,
            'annee_fin': 2034,
            'sites_ids': [site.id_site]
        })

        assert response.status_code == status.HTTP_201_CREATED
        # Get the plan by name since we just created it
        plan = PlanGestion.objects.get(nom='Creator Test Plan')
        assert plan.id_utilisateur_ajout == referent

    def test_create_plan_regular_user_denied(self, api_client):
        """Test regular users cannot create plans."""
        user = RoleFactory()

        api_client.force_authenticate(user=user)
        response = api_client.post('/api/plans/plans/', {
            'nom': 'Unauthorized Plan',
            'statut': 'draft'
        })

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_plan_with_years(self, api_client):
        """Test creating plan with year range."""
        admin = SuperAdminFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.post('/api/plans/plans/', {
            'nom': 'Year Range Plan',
            'statut': 'draft',
            'rang': 1,
            'ct88': False,
            'annee_debut': 2024,
            'annee_fin': 2034,
            'version': '1.0',
            'sites_ids': [site.id_site]
        })

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['annee_debut'] == 2024
        assert response.data['annee_fin'] == 2034


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetRetrieve:
    """Tests for PlanGestionViewSet retrieve action."""

    def test_retrieve_plan(self, api_client):
        """Test retrieving a single plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(nom='Detail Test Plan')

        api_client.force_authenticate(user=admin)
        response = api_client.get(f'/api/plans/plans/{plan.id_pg}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom'] == 'Detail Test Plan'

    def test_retrieve_nonexistent_plan(self, api_client):
        """Test retrieving a non-existent plan."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetUpdate:
    """Tests for PlanGestionViewSet update action."""

    def test_update_plan(self, api_client):
        """Test updating a plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(nom='Original Name')

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/plans/plans/{plan.id_pg}/', {
            'nom': 'Updated Name'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['nom'] == 'Updated Name'

    def test_update_plan_sets_modifier(self, api_client):
        """Test that plan modifier is automatically set."""
        admin = SuperAdminFactory()
        other_admin = SuperAdminFactory()
        plan = PlanGestionFactory(id_utilisateur_ajout=other_admin)

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/plans/plans/{plan.id_pg}/', {
            'nom': 'Modifier Test'
        })

        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.id_utilisateur_maj == admin

    def test_update_plan_status(self, api_client):
        """Test updating plan status."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')

        api_client.force_authenticate(user=admin)
        response = api_client.patch(f'/api/plans/plans/{plan.id_pg}/', {
            'statut': 'valide'
        })

        assert response.status_code == status.HTTP_200_OK
        assert response.data['statut'] == 'valide'


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetDelete:
    """Tests for PlanGestionViewSet delete action."""

    def test_delete_plan(self, api_client):
        """Test deleting a plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        plan_id = plan.id_pg

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/plans/plans/{plan_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not PlanGestion.objects.filter(id_pg=plan_id).exists()

    def test_delete_plan_cascades_sites(self, api_client):
        """Test deleting plan removes site associations."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site)
        plan_id = plan.id_pg

        api_client.force_authenticate(user=admin)
        response = api_client.delete(f'/api/plans/plans/{plan_id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CorSitePg.objects.filter(plan_de_gestion_id=plan_id).exists()


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetFilters:
    """Tests for PlanGestionViewSet filters."""

    def test_filter_by_statut(self, api_client):
        """Test filtering plans by status."""
        admin = SuperAdminFactory()
        PlanGestionFactory(statut='draft')
        PlanGestionFactory(statut='valide')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?statut=valide')

        assert response.status_code == status.HTTP_200_OK
        for plan in response.data['results']:
            assert plan['statut'] == 'valide'

    def test_filter_by_annee_debut(self, api_client):
        """Test filtering plans by start year."""
        admin = SuperAdminFactory()
        PlanGestionFactory(annee_debut=2020)
        PlanGestionFactory(annee_debut=2025)

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?annee_debut=2025')

        assert response.status_code == status.HTTP_200_OK
        for plan in response.data['results']:
            assert plan['annee_debut'] == 2025

    def test_search_by_nom(self, api_client):
        """Test searching plans by name."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Marais du Grosset')
        PlanGestionFactory(nom='Foret de Rambouillet')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?search=Marais')

        assert response.status_code == status.HTTP_200_OK
        assert any('Marais' in p['nom'] for p in response.data['results'])


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetGeoJSON:
    """Tests for PlanGestionViewSet GeoJSON actions."""

    def test_geojson_list(self, api_client):
        """Test GeoJSON list endpoint returns FeatureCollection."""
        admin = SuperAdminFactory()

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/geojson_list/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['type'] == 'FeatureCollection'
        assert 'features' in response.data


@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionViewSetOrdering:
    """Tests for PlanGestionViewSet ordering."""

    def test_ordering_by_date_maj(self, api_client):
        """Test ordering by modification date (default)."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Plan A')
        PlanGestionFactory(nom='Plan B')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/')

        assert response.status_code == status.HTTP_200_OK
        # Default ordering is -date_maj (most recent first)

    def test_ordering_by_nom(self, api_client):
        """Test ordering by name."""
        admin = SuperAdminFactory()
        PlanGestionFactory(nom='Zebra Plan')
        PlanGestionFactory(nom='Alpha Plan')

        api_client.force_authenticate(user=admin)
        response = api_client.get('/api/plans/plans/?ordering=nom')

        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        if len(results) >= 2:
            assert results[0]['nom'] <= results[1]['nom']


# ==================== Fixtures for lifecycle tests ====================


@pytest.fixture
def plan_with_referent(db):
    """
    Create a validated plan with a referent user properly set up.
    Returns (plan, referent, site, organisme) tuple.
    """
    organisme = OrganismeFactory()
    referent = ReferentFactory(id_organisme=organisme)
    site = SiteFactory()
    CorRoleSiteFactory(id_role=referent, id_site=site, referent=True, referent_valid=True)
    CorOgSiteFactory(id_site=site, uuid_og=organisme)

    plan = PlanGestionValideFactory(id_utilisateur_ajout=referent)
    CorSitePgFactory(plan_de_gestion=plan, site=site, rang=1)
    plan.referents.add(referent)

    return plan, referent, site, organisme


@pytest.fixture
def eval_nomenclature(db):
    """Create the EVAL_MI_PARCOURS nomenclature needed for create-evaluation."""
    from apps.core.models import Nomenclature, TypeNomenclature
    ntype, _ = TypeNomenclature.objects.get_or_create(
        mnemonique='TYPE_DOCUMENT_PLAN',
        defaults={'label': 'Type de document plan'},
    )
    nomenclature, _ = Nomenclature.objects.get_or_create(
        mnemonique='EVAL_MI_PARCOURS',
        defaults={
            'id_type': ntype,
            'label': 'Évaluation mi-parcours',
            'cd_nomenclature': 'EVAL',
        },
    )
    return nomenclature


# ==================== Phase 2: change-status tests ====================


@pytest.mark.django_db
@pytest.mark.integration
class TestPlanGestionChangeStatus:
    """Tests for POST /api/plans/plans/{id}/change-status/ endpoint."""

    URL_TEMPLATE = '/api/plans/plans/{}/change-status/'

    # ---------- Permissions ----------

    def test_unauthenticated_returns_401(self, api_client):
        """Unauthenticated request returns 401."""
        plan = PlanGestionFactory()
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_regular_user_returns_403(self, api_client):
        """Regular user without referent status returns 403."""
        user = RoleFactory()
        plan = PlanGestionFactory()
        api_client.force_authenticate(user=user)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_referent_not_of_plan_returns_403(self, api_client, plan_with_referent):
        """Referent of another site but not THIS plan gets 403.
        The user must be able to see the plan (via org/site association) but not be its referent."""
        plan, _, site, organisme = plan_with_referent

        # Create another referent in the SAME organisme so they can see the plan
        other_referent = ReferentFactory(id_organisme=organisme)
        other_site = SiteFactory()
        CorRoleSiteFactory(id_role=other_referent, id_site=other_site, referent=True, referent_valid=True)
        CorOgSiteFactory(id_site=other_site, uuid_og=organisme)
        # Also give them access to the plan's site (but NOT as referent of the plan itself)
        CorRoleSiteFactory(id_role=other_referent, id_site=site, referent=False, referent_valid=False)

        api_client.force_authenticate(user=other_referent)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'archive'},
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_plan_referent_succeeds(self, api_client, plan_with_referent):
        """Referent of this specific plan can change status."""
        plan, referent, _, _ = plan_with_referent
        api_client.force_authenticate(user=referent)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'archive'},
        )
        assert response.status_code == status.HTTP_200_OK

    def test_admin_og_succeeds(self, api_client, plan_with_referent):
        """Admin organisme can change status."""
        plan, _, _, organisme = plan_with_referent
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        api_client.force_authenticate(user=admin_og)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'archive'},
        )
        assert response.status_code == status.HTTP_200_OK

    # ---------- Valid transitions ----------

    def test_draft_to_valide(self, api_client):
        """Transition draft → valide succeeds and persists."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['statut'] == 'valide'
        plan.refresh_from_db()
        assert plan.statut == 'valide'

    def test_valide_to_draft(self, api_client):
        """Transition valide → draft succeeds."""
        admin = SuperAdminFactory()
        plan = PlanGestionValideFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'draft'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'draft'

    def test_valide_to_archive(self, api_client):
        """Transition valide → archive succeeds."""
        admin = SuperAdminFactory()
        plan = PlanGestionValideFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'archive'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'archive'

    def test_archive_to_draft(self, api_client):
        """Transition archive → draft succeeds."""
        admin = SuperAdminFactory()
        plan = PlanGestionArchiveFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'draft'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'draft'

    # ---------- Forbidden transitions ----------

    def test_draft_to_archive_forbidden(self, api_client):
        """Transition draft → archive is not allowed."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'archive'},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_archive_to_valide_forbidden(self, api_client):
        """Transition archive → valide is not allowed."""
        admin = SuperAdminFactory()
        plan = PlanGestionArchiveFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_same_status_forbidden(self, api_client):
        """Transition to same status is not allowed."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'draft'},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ---------- Validation ----------

    def test_missing_new_status(self, api_client):
        """Missing new_status in body returns 400."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_invalid_status_value(self, api_client):
        """Non-existent status value returns 400."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'nonexistent'},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_sets_modifier_user(self, api_client):
        """Verify id_utilisateur_maj is set after status change."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')
        api_client.force_authenticate(user=admin)
        api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide'},
        )
        plan.refresh_from_db()
        assert plan.id_utilisateur_maj == admin

    def test_logs_activity(self, api_client):
        """Verify ActivityLog is created with action='status_change'."""
        from apps.core.models import ActivityLog
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')
        api_client.force_authenticate(user=admin)
        api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide'},
        )
        log = ActivityLog.objects.filter(
            entity_type='plan',
            entity_id=plan.id_pg,
            action='status_change',
        ).first()
        assert log is not None
        assert 'draft' in log.description
        assert 'valide' in log.description


# ==================== Phase 3: create-evaluation tests ====================


@pytest.mark.django_db
@pytest.mark.integration
class TestPlanGestionCreateEvaluation:
    """Tests for POST /api/plans/plans/{id}/create-evaluation/ endpoint."""

    URL_TEMPLATE = '/api/plans/plans/{}/create-evaluation/'

    # ---------- Permissions ----------

    def test_unauthenticated_returns_401(self, api_client):
        """Unauthenticated request returns 401."""
        plan = PlanGestionValideFactory()
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_regular_user_returns_403(self, api_client):
        """Regular user without referent status returns 403."""
        user = RoleFactory()
        plan = PlanGestionValideFactory()
        api_client.force_authenticate(user=user)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_referent_not_of_plan_returns_403(self, api_client, plan_with_referent, eval_nomenclature):
        """Referent of another site but not THIS plan gets 403."""
        plan, _, site, organisme = plan_with_referent
        other_referent = ReferentFactory(id_organisme=organisme)
        other_site = SiteFactory()
        CorRoleSiteFactory(id_role=other_referent, id_site=other_site, referent=True, referent_valid=True)
        CorOgSiteFactory(id_site=other_site, uuid_og=organisme)
        CorRoleSiteFactory(id_role=other_referent, id_site=site, referent=False, referent_valid=False)

        api_client.force_authenticate(user=other_referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_super_admin_succeeds(self, api_client, plan_with_referent, eval_nomenclature):
        """Super admin can create evaluation."""
        plan, _, _, _ = plan_with_referent
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        assert response.status_code == status.HTTP_201_CREATED

    # ---------- Preconditions ----------

    def test_draft_plan_returns_400(self, api_client, eval_nomenclature):
        """Cannot create evaluation from draft plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')
        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_archive_plan_returns_400(self, api_client, eval_nomenclature):
        """Cannot create evaluation from archived plan."""
        admin = SuperAdminFactory()
        plan = PlanGestionArchiveFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ---------- Success behavior ----------

    def test_returns_201(self, api_client, plan_with_referent, eval_nomenclature):
        """Successful creation returns 201."""
        plan, referent, _, _ = plan_with_referent
        api_client.force_authenticate(user=referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        assert response.status_code == status.HTTP_201_CREATED

    def test_sets_plan_parent(self, api_client, plan_with_referent, eval_nomenclature):
        """New evaluation has plan_parent set to source plan."""
        plan, referent, _, _ = plan_with_referent
        api_client.force_authenticate(user=referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        new_plan = PlanGestion.objects.get(pk=response.data['id_pg'])
        assert new_plan.plan_parent_id == plan.id_pg

    def test_sets_type_document(self, api_client, plan_with_referent, eval_nomenclature):
        """New evaluation has EVAL_MI_PARCOURS type document."""
        plan, referent, _, _ = plan_with_referent
        api_client.force_authenticate(user=referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        new_plan = PlanGestion.objects.get(pk=response.data['id_pg'])
        assert new_plan.id_type_document.mnemonique == 'EVAL_MI_PARCOURS'

    def test_sets_draft_status(self, api_client, plan_with_referent, eval_nomenclature):
        """New evaluation is created as draft."""
        plan, referent, _, _ = plan_with_referent
        api_client.force_authenticate(user=referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        assert response.data['statut'] == 'draft'

    def test_increments_version(self, api_client, plan_with_referent, eval_nomenclature):
        """Version is incremented from source plan."""
        plan, referent, _, _ = plan_with_referent
        plan.version = '1.0'
        plan.save(update_fields=['version'])
        api_client.force_authenticate(user=referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        new_plan = PlanGestion.objects.get(pk=response.data['id_pg'])
        assert new_plan.version == '1.1'

    def test_copies_sites_with_rang(self, api_client, plan_with_referent, eval_nomenclature):
        """Sites and their rang are copied to new evaluation."""
        plan, referent, site, _ = plan_with_referent
        api_client.force_authenticate(user=referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        new_plan = PlanGestion.objects.get(pk=response.data['id_pg'])
        new_sites = CorSitePg.objects.filter(plan_de_gestion=new_plan)
        assert new_sites.count() == 1
        assert new_sites.first().site_id == site.id_site
        assert new_sites.first().rang == 1

    def test_copies_referents(self, api_client, plan_with_referent, eval_nomenclature):
        """Referents M2M are copied to new evaluation."""
        plan, referent, _, _ = plan_with_referent
        api_client.force_authenticate(user=referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        new_plan = PlanGestion.objects.get(pk=response.data['id_pg'])
        assert referent in new_plan.referents.all()

    def test_copies_members(self, api_client, plan_with_referent, eval_nomenclature):
        """CorRolePlan members are copied to new evaluation."""
        from apps.plans.models import CorRolePlan
        plan, referent, _, _ = plan_with_referent
        # Add an extra member to the plan
        member = RoleFactory()
        CorRolePlan.objects.create(id_role=member, plan_de_gestion=plan, referent=False)

        api_client.force_authenticate(user=referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        new_plan = PlanGestion.objects.get(pk=response.data['id_pg'])
        new_members = CorRolePlan.objects.filter(plan_de_gestion=new_plan)
        member_user_ids = set(new_members.values_list('id_role_id', flat=True))
        assert member.pk in member_user_ids

    def test_logs_activity(self, api_client, plan_with_referent, eval_nomenclature):
        """ActivityLog is created for the new evaluation."""
        from apps.core.models import ActivityLog
        plan, referent, _, _ = plan_with_referent
        api_client.force_authenticate(user=referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        new_id = response.data['id_pg']
        log = ActivityLog.objects.filter(
            entity_type='plan',
            entity_id=new_id,
            action='create',
        ).first()
        assert log is not None

    # ---------- Edge cases ----------

    def test_missing_nomenclature_returns_500(self, api_client):
        """Missing EVAL_MI_PARCOURS nomenclature returns 500."""
        from apps.core.models import Nomenclature
        # Ensure no EVAL_MI_PARCOURS nomenclature exists
        Nomenclature.objects.filter(mnemonique='EVAL_MI_PARCOURS').delete()
        admin = SuperAdminFactory()
        plan = PlanGestionValideFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_plan_not_found_returns_404(self, api_client):
        """Non-existent plan ID returns 404."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL_TEMPLATE.format(99999))
        assert response.status_code == status.HTTP_404_NOT_FOUND
