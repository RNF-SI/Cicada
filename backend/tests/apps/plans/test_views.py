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

    def test_list_regular_user_sees_empty(self, api_client):
        """Test regular users see an empty list (filtered by get_queryset)."""
        user = RoleFactory()  # Regular utilisateur
        PlanGestionFactory(nom='Draft Plan', statut='draft')
        PlanGestionFactory(nom='Valid Plan', statut='valide')

        api_client.force_authenticate(user=user)
        response = api_client.get('/api/plans/plans/')

        # Regular users get 200 but see no plans (filtered out by get_queryset)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['pagination']['count'] == 0

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


@pytest.fixture
def plan_revise_nomenclature(db):
    """Create the PLAN_REVISE nomenclature needed for create-next-rang."""
    from apps.core.models import Nomenclature, TypeNomenclature
    ntype, _ = TypeNomenclature.objects.get_or_create(
        mnemonique='TYPE_DOCUMENT_PLAN',
        defaults={'label': 'Type de document plan'},
    )
    nomenclature, _ = Nomenclature.objects.get_or_create(
        mnemonique='PLAN_REVISE',
        defaults={
            'id_type': ntype,
            'label': 'Plan révisé',
            'cd_nomenclature': 'REVISE',
        },
    )
    return nomenclature


# ==================== Phase 2: change-status tests ====================


@pytest.mark.django_db
@pytest.mark.integration
class TestPlanGestionChangeStatus:
    """Tests for POST /api/plans/plans/{id}/change-status/ endpoint.

    Depuis #277 (refactor) : le workflow CSRPN est sur l'endpoint dédié
    `csrpn-step/` (cf. {@link CSRPN_STEP_URL_TEMPLATE}).
    """

    URL_TEMPLATE = '/api/plans/plans/{}/change-status/'
    CSRPN_STEP_URL_TEMPLATE = '/api/plans/plans/{}/csrpn-step/'

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

    def test_revert_to_draft_preserves_csrpn_info(self, api_client, plan_with_referent):
        """#347 — repasser un plan validé en brouillon ne doit PAS effacer les
        informations CSRPN (dates avis/comité/arrêté + numéro d'arrêté)."""
        plan, referent, _, _ = plan_with_referent
        # Plan validé avec des infos CSRPN renseignées.
        plan.statut = 'valide'
        plan.date_avis_csrpn = '2026-03-10'
        plan.date_validation_comite = '2026-04-15'
        plan.date_arrete_pref = '2026-05-20'
        plan.numero_arrete_pref = 'AP-2026-042'
        plan.save()

        api_client.force_authenticate(user=referent)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'draft'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

        plan.refresh_from_db()
        assert plan.statut == 'draft'
        # Les métadonnées CSRPN sont conservées.
        assert str(plan.date_avis_csrpn) == '2026-03-10'
        assert str(plan.date_validation_comite) == '2026-04-15'
        assert str(plan.date_arrete_pref) == '2026-05-20'
        assert plan.numero_arrete_pref == 'AP-2026-042'
        # #347 — l'étape CSRPN atteinte est restaurée (reprise du workflow).
        assert plan.validation_step == 'arrete_pref'

    def test_revert_to_draft_resumes_earlier_csrpn_step(self, api_client, plan_with_referent):
        """#347 — si seule la date d'avis CSRPN est saisie, on reprend à `avis_csrpn`."""
        plan, referent, _, _ = plan_with_referent
        plan.statut = 'valide'
        plan.date_avis_csrpn = '2026-03-10'
        plan.save()

        api_client.force_authenticate(user=referent)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'draft'}, format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.validation_step == 'avis_csrpn'

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
        """Transition valide → draft succeeds (feuille de chaîne)."""
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

    def test_valide_to_draft_blocked_when_has_children(self, api_client):
        """Règle 2 — toDraft refusé si le plan a des descendants."""
        admin = SuperAdminFactory()
        parent = PlanGestionValideFactory()
        PlanGestionFactory(statut='draft', plan_parent=parent)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(parent.id_pg),
            {'new_status': 'draft'},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        parent.refresh_from_db()
        assert parent.statut == 'valide'

    def test_validation_cascades_to_draft_parent(self, api_client):
        """Règle 3 — valider un brouillon valide aussi son parent en draft."""
        admin = SuperAdminFactory()
        # Setup direct via ORM (bypasse les règles à la création) :
        # parent en draft, enfant en draft.
        parent = PlanGestionFactory(statut='draft')
        child = PlanGestionFactory(statut='draft', plan_parent=parent)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(child.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        parent.refresh_from_db()
        # Le parent en draft est automatiquement validé
        assert parent.statut == 'valide'

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

    def test_archive_to_valide(self, api_client):
        """Transition archive → valide succeeds (réactivation)."""
        admin = SuperAdminFactory()
        plan = PlanGestionArchiveFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'valide'

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

    def test_archive_to_draft_forbidden(self, api_client):
        """Transition archive → draft is not allowed."""
        admin = SuperAdminFactory()
        plan = PlanGestionArchiveFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'draft'},
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

    # ---------- #278 — en_revision attribut orthogonal ----------

    def test_start_revision_on_valide(self, api_client):
        """Lancer la révision d'un plan validé via start-revision (#278)."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='valide')
        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/start-revision/')
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'valide'  # statut inchangé
        assert plan.en_revision is True

    def test_start_revision_with_next_rang_plan(self, api_client):
        """Lien explicite vers le plan du rang suivant."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='valide')
        next_plan = PlanGestionFactory(statut='draft', plan_parent=plan)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            f'/api/plans/plans/{plan.id_pg}/start-revision/',
            {'next_rang_plan_id': next_plan.id_pg},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.en_revision is True
        assert plan.next_rang_plan_id == next_plan.id_pg

    def test_end_revision(self, api_client):
        """Arrêter la révision via end-revision."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='valide', en_revision=True)
        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/end-revision/')
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'valide'  # statut inchangé
        assert plan.en_revision is False
        assert plan.next_rang_plan is None

    def test_start_revision_on_draft_forbidden(self, api_client):
        """Impossible de lancer une révision sur un brouillon."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')
        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/start-revision/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_start_revision_already_in_revision(self, api_client):
        """Un plan déjà en révision ne peut pas être remis en révision."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='valide', en_revision=True)
        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/start-revision/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_valide_en_revision_etendu_combined(self, api_client):
        """Un plan validé peut être à la fois étendu ET en cours de révision."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='valide', annees_extension=2, en_revision=True)
        api_client.force_authenticate(user=admin)
        # Le plan reste verrouillé en lecture seule via le verrou #248
        # (testé ailleurs) ; on s'assure ici que les attributs cohabitent.
        plan.refresh_from_db()
        assert plan.statut == 'valide'
        assert plan.annees_extension == 2
        assert plan.en_revision is True
        assert plan.is_extended()
        assert plan.is_in_revision()

    def test_create_next_rang(self, api_client, plan_revise_nomenclature):
        """create-next-rang crée un brouillon enfant rang+1 du plan source."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(
            statut='valide', rang=1, annee_debut=2014, annee_fin=2024,
        )
        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/create-next-rang/')
        assert response.status_code == status.HTTP_201_CREATED
        new_id = response.data['id_pg']
        from apps.plans.models import PlanGestion as PG
        new_plan = PG.objects.get(pk=new_id)
        assert new_plan.statut == 'draft'
        assert new_plan.plan_parent_id == plan.id_pg
        assert new_plan.rang == 2
        assert new_plan.annee_debut == 2025  # plan.annee_fin + 1
        assert new_plan.annee_fin == 2034    # plan.annee_fin + 10

    def test_create_next_rang_on_draft_forbidden(self, api_client, plan_revise_nomenclature):
        """create-next-rang refuse si le plan source est un brouillon."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')
        api_client.force_authenticate(user=admin)
        response = api_client.post(f'/api/plans/plans/{plan.id_pg}/create-next-rang/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ---------- #275 — routage draft → modifie pour les modifications ----------

    def test_draft_with_validated_parent_becomes_modifie(self, api_client):
        """Validation d'un brouillon enfant d'un plan validé → statut `modifie`."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(nom='Parent', statut='valide')
        child = PlanGestionFactory(nom='Child', statut='draft', plan_parent=parent)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(child.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        child.refresh_from_db()
        assert child.statut == 'modifie'

    def test_draft_without_parent_stays_valide(self, api_client):
        """Validation d'un brouillon sans parent → statut `valide` (original)."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft', plan_parent=None)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'valide'

    def test_draft_with_archived_parent_becomes_modifie(self, api_client):
        """Un parent `archive` compte aussi comme déjà validé → enfant → `modifie`."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(nom='Parent', statut='archive', rang=1)
        child = PlanGestionFactory(nom='Child', statut='draft', plan_parent=parent, rang=1)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(child.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        child.refresh_from_db()
        assert child.statut == 'modifie'

    def test_draft_with_different_rang_stays_valide(self, api_client):
        """Un brouillon de rang N+1 enfant d'un plan validé de rang N → `valide`
        (pas `modifie`) : un changement de rang est un nouveau plan, pas une
        modification du précédent."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(nom='Parent', statut='archive', rang=1)
        child = PlanGestionFactory(nom='Child', statut='draft', plan_parent=parent, rang=2)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(child.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        child.refresh_from_db()
        assert child.statut == 'valide'

    def test_draft_with_draft_parent_becomes_valide(self, api_client):
        """Un parent encore en `draft` (jamais validé) → enfant reste `valide`."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(nom='Parent', statut='draft')
        child = PlanGestionFactory(nom='Child', statut='draft', plan_parent=parent)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(child.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        child.refresh_from_db()
        assert child.statut == 'valide'

    def test_modifie_to_draft_reversible(self, api_client):
        """Un plan `modifie` peut repasser en brouillon comme un `valide`."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(nom='Parent', statut='valide')
        plan = PlanGestionFactory(nom='Child', statut='modifie', plan_parent=parent)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'draft'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'draft'

    def test_modifie_to_archive(self, api_client):
        """Un plan `modifie` peut être archivé."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(nom='Parent', statut='valide')
        plan = PlanGestionFactory(nom='Child', statut='modifie', plan_parent=parent)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'archive'},
        )
        assert response.status_code == status.HTTP_200_OK

    # ---------- #276 — flag is_mi_parcours ----------

    def test_draft_with_is_mi_parcours_becomes_modifie_with_flag(self, api_client):
        """Brouillon enfant validé avec is_mi_parcours=True → statut `modifie` + drapeau."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(nom='Parent', statut='valide')
        child = PlanGestionFactory(nom='Child', statut='draft', plan_parent=parent)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(child.id_pg),
            {'new_status': 'valide', 'is_mi_parcours': True},
        )
        assert response.status_code == status.HTTP_200_OK
        child.refresh_from_db()
        # Depuis #276 (refonte) : mi_parcours n'est plus un statut mais un flag
        assert child.statut == 'modifie'
        assert child.is_mi_parcours is True

    def test_is_mi_parcours_rejected_when_chain_already_has_one(self, api_client):
        """Une seule version is_mi_parcours par chaîne plan_parent autorisée."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(nom='V1', statut='valide')
        already_mp = PlanGestionFactory(
            nom='V2', statut='modifie', is_mi_parcours=True, plan_parent=parent,
        )
        new_mod = PlanGestionFactory(nom='V3', statut='draft', plan_parent=already_mp)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(new_mod.id_pg),
            {'new_status': 'valide', 'is_mi_parcours': True},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        new_mod.refresh_from_db()
        assert new_mod.statut == 'draft'
        assert new_mod.is_mi_parcours is False

    def test_is_mi_parcours_rejected_on_original_plan(self, api_client):
        """is_mi_parcours sur un plan sans parent → 400 (flag inapplicable)."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft', plan_parent=None)
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide', 'is_mi_parcours': True},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_is_mi_parcours_rejected_on_non_validation_transition(self, api_client):
        """Le flag is_mi_parcours n'a de sens qu'à la validation, pas ailleurs."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='valide')
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'archive', 'is_mi_parcours': True},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ---------- #277 — workflow CSRPN ----------

    def _make_typed_site(self, mnemonique: str):
        """Helper : crée un site avec id_type_site = nomenclature(mnemonique)."""
        from apps.core.models import TypeNomenclature, Nomenclature
        ntype, _ = TypeNomenclature.objects.get_or_create(
            mnemonique='TYPE_SITE',
            defaults={'label': 'Type de site'},
        )
        nomenc, _ = Nomenclature.objects.get_or_create(
            id_type=ntype,
            mnemonique=mnemonique,
            defaults={'label': mnemonique, 'cd_nomenclature': mnemonique},
        )
        site = SiteFactory()
        site.id_type_site = nomenc
        site.save(update_fields=['id_type_site'])
        return site

    def test_draft_to_avis_csrpn(self, api_client):
        """`csrpn-step/` : draft + step=null → step=avis_csrpn (lancement workflow)."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft')
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.CSRPN_STEP_URL_TEMPLATE.format(plan.id_pg),
            {'step': 'avis_csrpn'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'draft'
        assert plan.validation_step == 'avis_csrpn'

    def test_avis_csrpn_to_comite_with_date(self, api_client):
        """`csrpn-step/` : avis_csrpn → comite_consultatif enregistre la date d'avis."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft', validation_step='avis_csrpn')
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.CSRPN_STEP_URL_TEMPLATE.format(plan.id_pg),
            {'step': 'comite_consultatif', 'date_avis_csrpn': '2026-03-15'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.validation_step == 'comite_consultatif'
        assert str(plan.date_avis_csrpn) == '2026-03-15'

    def test_comite_to_arrete_pref_only_for_rnn(self, api_client):
        """`csrpn-step/` : comite → arrete_pref autorisé uniquement pour les RNN."""
        admin = SuperAdminFactory()
        rnn_site = self._make_typed_site('RNN')
        plan = PlanGestionFactory(statut='draft', validation_step='comite_consultatif', sites=[rnn_site])
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.CSRPN_STEP_URL_TEMPLATE.format(plan.id_pg),
            {'step': 'arrete_pref'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.validation_step == 'arrete_pref'

    def test_comite_to_arrete_pref_rejected_for_non_rnn(self, api_client):
        """Un plan PNR ne passe pas par `arrete_pref` (ne concerne que les RNN)."""
        admin = SuperAdminFactory()
        pnr_site = self._make_typed_site('PNR')
        plan = PlanGestionFactory(statut='draft', validation_step='comite_consultatif', sites=[pnr_site])
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.CSRPN_STEP_URL_TEMPLATE.format(plan.id_pg),
            {'step': 'arrete_pref'},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_comite_to_valide_for_non_rnn(self, api_client):
        """Pour un plan PNR, `change-status` valide depuis draft+comite_consultatif
        sort directement du workflow (validation_step → NULL)."""
        admin = SuperAdminFactory()
        pnr_site = self._make_typed_site('PNR')
        plan = PlanGestionFactory(statut='draft', validation_step='comite_consultatif', sites=[pnr_site])
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'valide'
        assert plan.validation_step is None

    def test_arrete_pref_to_valide_clears_validation_step(self, api_client):
        """`change-status` depuis draft+arrete_pref → valide remet
        validation_step à NULL."""
        admin = SuperAdminFactory()
        rnn_site = self._make_typed_site('RNN')
        plan = PlanGestionFactory(statut='draft', validation_step='arrete_pref', sites=[rnn_site])
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'valide'
        assert plan.validation_step is None

    def test_csrpn_back_to_draft(self, api_client):
        """`csrpn-step/` : step=null annule le workflow (validation_step → NULL)."""
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft', validation_step='avis_csrpn')
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.CSRPN_STEP_URL_TEMPLATE.format(plan.id_pg),
            {'step': None},
        )
        assert response.status_code == status.HTTP_200_OK
        plan.refresh_from_db()
        assert plan.statut == 'draft'
        assert plan.validation_step is None

    def test_csrpn_validation_routes_modification_to_modifie(self, api_client):
        """`change-status` depuis brouillon en workflow CSRPN d'un enfant de
        plan validé → `modifie` (validation_step remis à NULL)."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(statut='valide')
        rnn_site = self._make_typed_site('RNN')
        child = PlanGestionFactory(
            statut='draft',
            validation_step='arrete_pref',
            plan_parent=parent,
            sites=[rnn_site],
        )
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(child.id_pg),
            {'new_status': 'valide'},
        )
        assert response.status_code == status.HTTP_200_OK
        child.refresh_from_db()
        assert child.statut == 'modifie'
        assert child.validation_step is None

    def test_csrpn_validation_with_is_mi_parcours(self, api_client):
        """Validation finale + is_mi_parcours sur un enfant en workflow CSRPN →
        `modifie` + drapeau is_mi_parcours."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(statut='valide')
        pnr_site = self._make_typed_site('PNR')
        child = PlanGestionFactory(
            statut='draft',
            validation_step='comite_consultatif',
            plan_parent=parent,
            sites=[pnr_site],
        )
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(child.id_pg),
            {'new_status': 'valide', 'is_mi_parcours': True},
        )
        assert response.status_code == status.HTTP_200_OK
        child.refresh_from_db()
        # Depuis #276 (refonte) : mi_parcours n'est plus un statut mais un flag
        assert child.statut == 'modifie'
        assert child.is_mi_parcours is True

    def test_field_rename_date_validation_cspn_removed(self, api_client):
        """`date_validation_cspn` n'existe plus, `date_avis_csrpn` à la place."""
        plan = PlanGestionFactory()
        assert hasattr(plan, 'date_avis_csrpn')
        assert not hasattr(plan, 'date_validation_cspn')

    def test_csrpn_transition_notifies_referents(self, api_client):
        """Une transition `csrpn-step` notifie les référents (sauf déclencheur)."""
        from apps.notifications.models import Notification
        admin = SuperAdminFactory()
        referent = ReferentFactory()
        other_admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='draft', referents=[referent, other_admin])
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.CSRPN_STEP_URL_TEMPLATE.format(plan.id_pg),
            {'step': 'avis_csrpn'},
        )
        assert response.status_code == status.HTTP_200_OK
        # Le déclencheur (admin) ne reçoit pas de notif ; les 2 référents oui.
        notifs = Notification.objects.filter(
            related_plan=plan, notification_type='plan_csrpn_transition'
        )
        recipients = set(notifs.values_list('recipient_id', flat=True))
        assert referent.id_role in recipients
        assert other_admin.id_role in recipients
        assert admin.id_role not in recipients

    def test_non_csrpn_transition_does_not_notify(self, api_client):
        """Les transitions hors workflow CSRPN ne déclenchent pas la notif `plan_csrpn_transition`."""
        from apps.notifications.models import Notification
        admin = SuperAdminFactory()
        plan = PlanGestionFactory(statut='valide')
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.URL_TEMPLATE.format(plan.id_pg),
            {'new_status': 'archive'},
        )
        assert response.status_code == status.HTTP_200_OK
        assert not Notification.objects.filter(
            related_plan=plan, notification_type='plan_csrpn_transition'
        ).exists()

    def test_csrpn_to_valide_notifies(self, api_client):
        """L'annulation du workflow via `csrpn-step` step=null notifie aussi."""
        from apps.notifications.models import Notification
        admin = SuperAdminFactory()
        referent = ReferentFactory()
        rnn_site = self._make_typed_site('RNN')
        plan = PlanGestionFactory(
            statut='draft',
            validation_step='arrete_pref',
            sites=[rnn_site],
            referents=[referent],
        )
        api_client.force_authenticate(user=admin)
        response = api_client.post(
            self.CSRPN_STEP_URL_TEMPLATE.format(plan.id_pg),
            {'step': None},
        )
        assert response.status_code == status.HTTP_200_OK
        assert Notification.objects.filter(
            recipient=referent,
            related_plan=plan,
            notification_type='plan_csrpn_transition',
        ).exists()

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

    def test_archive_plan_returns_201(self, api_client, eval_nomenclature):
        """Archive (validé dans le passé) accepted as parent for evaluation."""
        admin = SuperAdminFactory()
        plan = PlanGestionArchiveFactory()
        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        assert response.status_code == status.HTTP_201_CREATED

    def test_returns_400_if_has_draft_child(self, api_client, eval_nomenclature):
        """Règle « 1 brouillon max par parent » : refuser si déjà un brouillon enfant."""
        admin = SuperAdminFactory()
        parent = PlanGestionFactory(statut='valide')
        PlanGestionFactory(statut='draft', plan_parent=parent)
        api_client.force_authenticate(user=admin)
        response = api_client.post(self.URL_TEMPLATE.format(parent.id_pg))
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
        plan.version = '1'
        plan.save(update_fields=['version'])
        api_client.force_authenticate(user=referent)
        response = api_client.post(self.URL_TEMPLATE.format(plan.id_pg))
        new_plan = PlanGestion.objects.get(pk=response.data['id_pg'])
        assert new_plan.version == '2'

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
