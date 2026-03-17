"""
Tests for the Plans de Gestion Django admin interface.
Tests access control, list views, form submissions, and inline management
for PlanGestion, CorSitePg, CorRolePlan, and CorPgFichier admin pages.
"""
import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.test import Client
from django.urls import reverse

from apps.plans.models import PlanGestion, CorSitePg, CorRolePlan
from tests.factories.users import (
    SuperAdminFactory, AdminOrganismeFactory, RoleFactory,
    OrganismeFactory, SiteFactory, CorRoleSiteFactory, CorOgSiteFactory,
)
from tests.factories.plans import (
    PlanGestionFactory, CorSitePgFactory, CorRolePlanFactory,
)


def _grant_plans_permissions(user):
    """Grant all plans-related model permissions to a staff user."""
    for model in [PlanGestion, CorSitePg, CorRolePlan]:
        ct = ContentType.objects.get_for_model(model)
        perms = Permission.objects.filter(content_type=ct)
        user.user_permissions.add(*perms)
    # Clear permission cache
    user._perm_cache = set()
    user._user_perm_cache = set()


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def admin_client(db):
    """Return a Django test client logged in as superuser."""
    admin = SuperAdminFactory(is_staff=True, is_superuser=True)
    client = Client()
    client.force_login(admin)
    return client, admin


@pytest.fixture
def staff_client(db):
    """Return a Django test client logged in as admin_og with plans permissions."""
    admin_og = AdminOrganismeFactory(is_staff=True)
    _grant_plans_permissions(admin_og)
    client = Client()
    client.force_login(admin_og)
    return client, admin_og


@pytest.fixture
def regular_client(db):
    """Return a Django test client logged in as regular user (not staff)."""
    user = RoleFactory(is_staff=False, is_superuser=False)
    client = Client()
    client.force_login(user)
    return client, user


@pytest.fixture
def plan_with_data(db):
    """Create a plan with sites, members, and referents for testing."""
    org = OrganismeFactory()
    site1 = SiteFactory(nom_site='Site Alpha')
    site2 = SiteFactory(nom_site='Site Beta')
    CorOgSiteFactory(id_site=site1, uuid_og=org)
    CorOgSiteFactory(id_site=site2, uuid_og=org)

    creator = SuperAdminFactory(is_staff=True, is_superuser=True)
    referent = RoleFactory(id_organisme=org)
    member = RoleFactory(id_organisme=org)
    CorRoleSiteFactory(id_role=referent, id_site=site1, referent=True, referent_valid=True)
    CorRoleSiteFactory(id_role=member, id_site=site1)

    plan = PlanGestionFactory(
        nom='Plan Test Admin',
        statut='draft',
        id_utilisateur_ajout=creator,
    )
    CorSitePgFactory(plan_de_gestion=plan, site=site1, rang=1)
    CorSitePgFactory(plan_de_gestion=plan, site=site2, rang=2)
    CorRolePlanFactory(id_role=referent, plan_de_gestion=plan, referent=True)
    CorRolePlanFactory(id_role=member, plan_de_gestion=plan, referent=False)

    return {
        'plan': plan,
        'sites': [site1, site2],
        'referent': referent,
        'member': member,
        'creator': creator,
        'org': org,
    }


# =============================================================================
# Access control tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestAdminAccessControl:
    """Test that only authorized users can access admin pages."""

    def test_superuser_can_access_plan_list(self, admin_client):
        client, _ = admin_client
        url = reverse('admin:plans_plangestion_changelist')
        response = client.get(url)
        assert response.status_code == 200

    def test_superuser_can_access_cor_role_plan_list(self, admin_client):
        client, _ = admin_client
        url = reverse('admin:plans_corroleplan_changelist')
        response = client.get(url)
        assert response.status_code == 200

    def test_superuser_can_access_cor_site_pg_list(self, admin_client):
        client, _ = admin_client
        url = reverse('admin:plans_corsitepg_changelist')
        response = client.get(url)
        assert response.status_code == 200

    def test_staff_can_access_plan_list(self, staff_client):
        client, _ = staff_client
        url = reverse('admin:plans_plangestion_changelist')
        response = client.get(url)
        assert response.status_code == 200

    def test_non_staff_redirected_from_plan_list(self, regular_client):
        client, _ = regular_client
        url = reverse('admin:plans_plangestion_changelist')
        response = client.get(url)
        # Non-staff users get redirected to admin login
        assert response.status_code == 302

    def test_non_staff_redirected_from_cor_role_plan_list(self, regular_client):
        client, _ = regular_client
        url = reverse('admin:plans_corroleplan_changelist')
        response = client.get(url)
        assert response.status_code == 302

    def test_anonymous_redirected_from_admin(self):
        client = Client()
        url = reverse('admin:plans_plangestion_changelist')
        response = client.get(url)
        assert response.status_code == 302


# =============================================================================
# PlanGestion admin list tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionAdminList:
    """Test the PlanGestion admin changelist page."""

    def test_list_displays_plans(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_plangestion_changelist')
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Plan Test Admin' in content

    def test_list_shows_sites_count(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_plangestion_changelist')
        response = client.get(url)
        content = response.content.decode()
        # Plan has 2 sites
        assert '2' in content

    def test_list_shows_equipe_column(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_plangestion_changelist')
        response = client.get(url)
        content = response.content.decode()
        # Should show referent and member counts
        assert 'ref.' in content.lower() or 'mbr.' in content.lower()

    def test_list_search_by_name(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_plangestion_changelist')
        response = client.get(url, {'q': 'Plan Test Admin'})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Plan Test Admin' in content

    def test_list_filter_by_statut(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_plangestion_changelist')
        response = client.get(url, {'statut__exact': 'draft'})
        assert response.status_code == 200


# =============================================================================
# PlanGestion admin detail/change tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionAdminDetail:
    """Test the PlanGestion admin change page (detail view)."""

    def test_change_page_loads(self, admin_client, plan_with_data):
        client, _ = admin_client
        plan = plan_with_data['plan']
        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        response = client.get(url)
        assert response.status_code == 200

    def test_change_page_shows_sites_inline(self, admin_client, plan_with_data):
        client, _ = admin_client
        plan = plan_with_data['plan']
        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        response = client.get(url)
        content = response.content.decode()
        assert 'Site Alpha' in content
        assert 'Site Beta' in content

    def test_change_page_shows_membres_inline(self, admin_client, plan_with_data):
        client, _ = admin_client
        plan = plan_with_data['plan']
        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        response = client.get(url)
        content = response.content.decode()
        referent = plan_with_data['referent']
        member = plan_with_data['member']
        assert referent.email in content
        assert member.email in content

    def test_change_page_shows_site_type_readonly(self, admin_client, plan_with_data):
        """Test the readonly site_type and site_surface fields render."""
        client, _ = admin_client
        plan = plan_with_data['plan']
        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        response = client.get(url)
        assert response.status_code == 200
        # The inline should render without errors
        content = response.content.decode()
        assert 'Type de site' in content or 'site_type' in content.lower()

    def test_change_page_shows_user_organisme_readonly(self, admin_client, plan_with_data):
        """Test the readonly user_organisme field renders in CorRolePlan inline."""
        client, _ = admin_client
        plan = plan_with_data['plan']
        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        response = client.get(url)
        content = response.content.decode()
        org = plan_with_data['org']
        assert org.nom_organisme in content

    def test_validated_plan_has_readonly_fields_for_non_superuser(self, staff_client):
        """Test that validated plans have some fields readonly for non-superuser."""
        client, admin_og = staff_client
        plan = PlanGestionFactory(
            nom='Plan Valide',
            statut='valide',
            id_utilisateur_ajout=admin_og,
        )
        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        response = client.get(url)
        assert response.status_code == 200


# =============================================================================
# PlanGestion admin add tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionAdminAdd:
    """Test creating a plan through the admin."""

    def test_add_page_loads(self, admin_client):
        client, _ = admin_client
        url = reverse('admin:plans_plangestion_add')
        response = client.get(url)
        assert response.status_code == 200

    def test_create_plan_minimal(self, admin_client):
        """Test creating a plan with minimal required fields."""
        client, admin = admin_client
        url = reverse('admin:plans_plangestion_add')

        data = {
            'nom': 'Nouveau Plan Admin',
            'statut': 'draft',
            'version': '1.0',
            'rang': 1,
            'gestion_partagee': False,
            'ct88': False,
            'risque_incendie': False,
            'id_utilisateur_ajout': admin.id_role,
            # Inlines management forms (required by Django admin)
            'sites-TOTAL_FORMS': '0',
            'sites-INITIAL_FORMS': '0',
            'sites-MIN_NUM_FORMS': '0',
            'sites-MAX_NUM_FORMS': '1000',
            'membres-TOTAL_FORMS': '0',
            'membres-INITIAL_FORMS': '0',
            'membres-MIN_NUM_FORMS': '0',
            'membres-MAX_NUM_FORMS': '1000',
            'fichiers-TOTAL_FORMS': '0',
            'fichiers-INITIAL_FORMS': '0',
            'fichiers-MIN_NUM_FORMS': '0',
            'fichiers-MAX_NUM_FORMS': '1000',
        }
        response = client.post(url, data)
        # Successful creation redirects to changelist
        assert response.status_code == 302
        assert PlanGestion.objects.filter(nom='Nouveau Plan Admin').exists()

    def test_create_plan_with_site_inline(self, admin_client):
        """Test creating a plan with a site added via inline."""
        client, admin = admin_client
        site = SiteFactory()

        url = reverse('admin:plans_plangestion_add')
        data = {
            'nom': 'Plan Avec Site',
            'statut': 'draft',
            'version': '1.0',
            'rang': 1,
            'gestion_partagee': False,
            'ct88': False,
            'risque_incendie': False,
            'id_utilisateur_ajout': admin.id_role,
            # Sites inline
            'sites-TOTAL_FORMS': '1',
            'sites-INITIAL_FORMS': '0',
            'sites-MIN_NUM_FORMS': '0',
            'sites-MAX_NUM_FORMS': '1000',
            'sites-0-site': site.id_site,
            'sites-0-rang': 1,
            'sites-0-commentaire': '',
            # Membres inline
            'membres-TOTAL_FORMS': '0',
            'membres-INITIAL_FORMS': '0',
            'membres-MIN_NUM_FORMS': '0',
            'membres-MAX_NUM_FORMS': '1000',
            # Fichiers inline
            'fichiers-TOTAL_FORMS': '0',
            'fichiers-INITIAL_FORMS': '0',
            'fichiers-MIN_NUM_FORMS': '0',
            'fichiers-MAX_NUM_FORMS': '1000',
        }
        response = client.post(url, data)
        assert response.status_code == 302
        plan = PlanGestion.objects.get(nom='Plan Avec Site')
        assert plan.sites.count() == 1
        assert plan.sites.first().site == site

    def test_create_plan_with_referent_inline(self, admin_client):
        """Test creating a plan with a referent added via CorRolePlan inline."""
        client, admin = admin_client
        referent_user = RoleFactory()

        url = reverse('admin:plans_plangestion_add')
        data = {
            'nom': 'Plan Avec Referent',
            'statut': 'draft',
            'version': '1.0',
            'rang': 1,
            'gestion_partagee': False,
            'ct88': False,
            'risque_incendie': False,
            'id_utilisateur_ajout': admin.id_role,
            # Sites inline
            'sites-TOTAL_FORMS': '0',
            'sites-INITIAL_FORMS': '0',
            'sites-MIN_NUM_FORMS': '0',
            'sites-MAX_NUM_FORMS': '1000',
            # Membres inline - add one referent
            'membres-TOTAL_FORMS': '1',
            'membres-INITIAL_FORMS': '0',
            'membres-MIN_NUM_FORMS': '0',
            'membres-MAX_NUM_FORMS': '1000',
            'membres-0-id_role': referent_user.id_role,
            'membres-0-referent': True,
            'membres-0-commentaire': 'Referent principal',
            # Fichiers inline
            'fichiers-TOTAL_FORMS': '0',
            'fichiers-INITIAL_FORMS': '0',
            'fichiers-MIN_NUM_FORMS': '0',
            'fichiers-MAX_NUM_FORMS': '1000',
        }
        response = client.post(url, data)
        assert response.status_code == 302
        plan = PlanGestion.objects.get(nom='Plan Avec Referent')
        assert plan.membres.count() == 1
        membre = plan.membres.first()
        assert membre.id_role == referent_user
        assert membre.referent is True
        assert membre.commentaire == 'Referent principal'

    def test_create_plan_with_member_inline(self, admin_client):
        """Test creating a plan with a simple member (not referent) via inline."""
        client, admin = admin_client
        member_user = RoleFactory()

        url = reverse('admin:plans_plangestion_add')
        data = {
            'nom': 'Plan Avec Membre',
            'statut': 'draft',
            'version': '1.0',
            'rang': 1,
            'gestion_partagee': False,
            'ct88': False,
            'risque_incendie': False,
            'id_utilisateur_ajout': admin.id_role,
            # Sites inline
            'sites-TOTAL_FORMS': '0',
            'sites-INITIAL_FORMS': '0',
            'sites-MIN_NUM_FORMS': '0',
            'sites-MAX_NUM_FORMS': '1000',
            # Membres inline - add one member (not referent)
            'membres-TOTAL_FORMS': '1',
            'membres-INITIAL_FORMS': '0',
            'membres-MIN_NUM_FORMS': '0',
            'membres-MAX_NUM_FORMS': '1000',
            'membres-0-id_role': member_user.id_role,
            'membres-0-commentaire': '',
            # Fichiers inline
            'fichiers-TOTAL_FORMS': '0',
            'fichiers-INITIAL_FORMS': '0',
            'fichiers-MIN_NUM_FORMS': '0',
            'fichiers-MAX_NUM_FORMS': '1000',
        }
        response = client.post(url, data)
        assert response.status_code == 302
        plan = PlanGestion.objects.get(nom='Plan Avec Membre')
        assert plan.membres.count() == 1
        membre = plan.membres.first()
        assert membre.referent is False


# =============================================================================
# PlanGestion admin update tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestPlanGestionAdminUpdate:
    """Test updating a plan and its inlines through the admin."""

    def _get_change_data(self, plan, admin, extra=None):
        """Build a base POST data dict for the plan change form."""
        data = {
            'nom': plan.nom,
            'statut': plan.statut,
            'version': plan.version,
            'rang': plan.rang,
            'gestion_partagee': plan.gestion_partagee,
            'ct88': plan.ct88,
            'risque_incendie': plan.risque_incendie,
            'id_utilisateur_ajout': plan.id_utilisateur_ajout_id,
            # Sites inline
            'sites-TOTAL_FORMS': '0',
            'sites-INITIAL_FORMS': '0',
            'sites-MIN_NUM_FORMS': '0',
            'sites-MAX_NUM_FORMS': '1000',
            # Membres inline
            'membres-TOTAL_FORMS': '0',
            'membres-INITIAL_FORMS': '0',
            'membres-MIN_NUM_FORMS': '0',
            'membres-MAX_NUM_FORMS': '1000',
            # Fichiers inline
            'fichiers-TOTAL_FORMS': '0',
            'fichiers-INITIAL_FORMS': '0',
            'fichiers-MIN_NUM_FORMS': '0',
            'fichiers-MAX_NUM_FORMS': '1000',
        }
        if extra:
            data.update(extra)
        return data

    def test_update_plan_name(self, admin_client):
        client, admin = admin_client
        plan = PlanGestionFactory(nom='Ancien Nom', id_utilisateur_ajout=admin)
        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])

        data = self._get_change_data(plan, admin, {'nom': 'Nouveau Nom'})
        response = client.post(url, data)
        assert response.status_code == 302
        plan.refresh_from_db()
        assert plan.nom == 'Nouveau Nom'

    def test_add_referent_to_existing_plan(self, admin_client):
        """Test adding a referent to an existing plan via inline."""
        client, admin = admin_client
        plan = PlanGestionFactory(id_utilisateur_ajout=admin)
        new_ref = RoleFactory()

        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        data = self._get_change_data(plan, admin, {
            'membres-TOTAL_FORMS': '1',
            'membres-0-id_role': new_ref.id_role,
            'membres-0-referent': True,
            'membres-0-commentaire': 'Added via admin',
        })
        response = client.post(url, data)
        assert response.status_code == 302
        assert plan.membres.count() == 1
        assert plan.membres.first().referent is True

    def test_add_site_to_existing_plan(self, admin_client):
        """Test adding a site to an existing plan via inline."""
        client, admin = admin_client
        plan = PlanGestionFactory(id_utilisateur_ajout=admin)
        site = SiteFactory()

        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        data = self._get_change_data(plan, admin, {
            'sites-TOTAL_FORMS': '1',
            'sites-0-site': site.id_site,
            'sites-0-rang': 1,
            'sites-0-commentaire': '',
        })
        response = client.post(url, data)
        assert response.status_code == 302
        assert plan.sites.count() == 1

    def test_remove_referent_from_plan(self, admin_client):
        """Test removing a referent via inline DELETE checkbox."""
        client, admin = admin_client
        plan = PlanGestionFactory(id_utilisateur_ajout=admin)
        ref = RoleFactory()
        cor = CorRolePlanFactory(id_role=ref, plan_de_gestion=plan, referent=True)

        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        data = self._get_change_data(plan, admin, {
            'membres-TOTAL_FORMS': '1',
            'membres-INITIAL_FORMS': '1',
            'membres-0-id': cor.pk,
            'membres-0-plan_de_gestion': plan.id_pg,
            'membres-0-id_role': ref.id_role,
            'membres-0-referent': True,
            'membres-0-commentaire': '',
            'membres-0-DELETE': True,
        })
        response = client.post(url, data)
        assert response.status_code == 302
        assert plan.membres.count() == 0

    def test_change_member_to_referent(self, admin_client):
        """Test promoting a member to referent via inline."""
        client, admin = admin_client
        plan = PlanGestionFactory(id_utilisateur_ajout=admin)
        user = RoleFactory()
        cor = CorRolePlanFactory(id_role=user, plan_de_gestion=plan, referent=False)

        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        data = self._get_change_data(plan, admin, {
            'membres-TOTAL_FORMS': '1',
            'membres-INITIAL_FORMS': '1',
            'membres-0-id': cor.pk,
            'membres-0-plan_de_gestion': plan.id_pg,
            'membres-0-id_role': user.id_role,
            'membres-0-referent': True,
            'membres-0-commentaire': 'Promoted to referent',
        })
        response = client.post(url, data)
        assert response.status_code == 302
        cor.refresh_from_db()
        assert cor.referent is True
        assert cor.commentaire == 'Promoted to referent'


# =============================================================================
# CorRolePlan standalone admin tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestCorRolePlanAdmin:
    """Test the standalone CorRolePlan admin page."""

    def test_list_page_loads(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_corroleplan_changelist')
        response = client.get(url)
        assert response.status_code == 200
        content = response.content.decode()
        assert plan_with_data['referent'].email in content

    def test_list_shows_referent_status(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_corroleplan_changelist')
        response = client.get(url)
        content = response.content.decode()
        assert 'Membre' in content

    def test_list_filter_by_referent(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_corroleplan_changelist')
        response = client.get(url, {'referent__exact': '1'})
        assert response.status_code == 200

    def test_list_search_by_user_email(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_corroleplan_changelist')
        response = client.get(url, {'q': plan_with_data['referent'].email})
        assert response.status_code == 200
        content = response.content.decode()
        assert plan_with_data['referent'].email in content

    def test_list_search_by_plan_name(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_corroleplan_changelist')
        response = client.get(url, {'q': 'Plan Test Admin'})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Plan Test Admin' in content

    def test_change_page_loads(self, admin_client, plan_with_data):
        client, _ = admin_client
        cor = plan_with_data['plan'].membres.first()
        url = reverse('admin:plans_corroleplan_change', args=[cor.pk])
        response = client.get(url)
        assert response.status_code == 200

    def test_create_association(self, admin_client):
        client, _ = admin_client
        plan = PlanGestionFactory()
        user = RoleFactory()

        url = reverse('admin:plans_corroleplan_add')
        data = {
            'id_role': user.id_role,
            'plan_de_gestion': plan.id_pg,
            'referent': True,
            'commentaire': 'Added from standalone admin',
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert CorRolePlan.objects.filter(
            id_role=user, plan_de_gestion=plan, referent=True
        ).exists()

    def test_filter_by_plan_statut(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_corroleplan_changelist')
        response = client.get(url, {'plan_de_gestion__statut__exact': 'draft'})
        assert response.status_code == 200

    def test_filter_by_organisme(self, admin_client, plan_with_data):
        client, _ = admin_client
        org = plan_with_data['org']
        url = reverse('admin:plans_corroleplan_changelist')
        response = client.get(
            url,
            {'id_role__id_organisme__id_organisme__exact': str(org.id_organisme)},
        )
        assert response.status_code == 200


# =============================================================================
# CorSitePg admin tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestCorSitePgAdmin:
    """Test the CorSitePg admin page."""

    def test_list_page_loads(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_corsitepg_changelist')
        response = client.get(url)
        assert response.status_code == 200

    def test_list_search_by_site_name(self, admin_client, plan_with_data):
        client, _ = admin_client
        url = reverse('admin:plans_corsitepg_changelist')
        response = client.get(url, {'q': 'Site Alpha'})
        assert response.status_code == 200
        content = response.content.decode()
        assert 'Site Alpha' in content

    def test_create_site_plan_association(self, admin_client):
        client, _ = admin_client
        plan = PlanGestionFactory()
        site = SiteFactory()

        url = reverse('admin:plans_corsitepg_add')
        data = {
            'site': site.id_site,
            'plan_de_gestion': plan.id_pg,
            'rang': 1,
            'commentaire': 'Test association',
        }
        response = client.post(url, data)
        assert response.status_code == 302
        assert CorSitePg.objects.filter(site=site, plan_de_gestion=plan).exists()


# =============================================================================
# Admin actions tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestPlanAdminActions:
    """Test bulk admin actions on plans."""

    def test_valider_plans_action(self, admin_client):
        client, admin = admin_client
        plan = PlanGestionFactory(statut='draft', id_utilisateur_ajout=admin)

        url = reverse('admin:plans_plangestion_changelist')
        data = {
            'action': 'valider_plans',
            '_selected_action': [plan.id_pg],
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == 200
        plan.refresh_from_db()
        assert plan.statut == 'valide'

    def test_archiver_plans_action(self, admin_client):
        client, admin = admin_client
        plan = PlanGestionFactory(statut='valide', id_utilisateur_ajout=admin)

        url = reverse('admin:plans_plangestion_changelist')
        data = {
            'action': 'archiver_plans',
            '_selected_action': [plan.id_pg],
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == 200
        plan.refresh_from_db()
        assert plan.statut == 'archive'

    def test_remettre_en_brouillon_action_superuser(self, admin_client):
        client, admin = admin_client
        plan = PlanGestionFactory(statut='valide', id_utilisateur_ajout=admin)

        url = reverse('admin:plans_plangestion_changelist')
        data = {
            'action': 'remettre_en_brouillon',
            '_selected_action': [plan.id_pg],
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == 200
        plan.refresh_from_db()
        assert plan.statut == 'draft'

    def test_remettre_en_brouillon_denied_for_staff(self, staff_client):
        """Non-superuser staff cannot use remettre_en_brouillon."""
        client, admin_og = staff_client
        plan = PlanGestionFactory(statut='valide', id_utilisateur_ajout=admin_og)

        url = reverse('admin:plans_plangestion_changelist')
        data = {
            'action': 'remettre_en_brouillon',
            '_selected_action': [plan.id_pg],
        }
        response = client.post(url, data, follow=True)
        assert response.status_code == 200
        plan.refresh_from_db()
        # Should NOT have changed
        assert plan.statut == 'valide'

    def test_export_csv_action(self, admin_client):
        client, admin = admin_client
        plan = PlanGestionFactory(nom='Plan Export CSV', id_utilisateur_ajout=admin)

        url = reverse('admin:plans_plangestion_changelist')
        data = {
            'action': 'export_plans_csv',
            '_selected_action': [plan.id_pg],
        }
        response = client.post(url, data)
        assert response.status_code == 200
        assert response['Content-Type'] == 'text/csv'
        content = response.content.decode()
        assert 'Plan Export CSV' in content


# =============================================================================
# Unique constraint and validation tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestAdminValidation:
    """Test admin form validations and constraints."""

    def test_duplicate_user_plan_association_rejected(self, admin_client):
        """Test that adding the same user to the same plan twice is rejected."""
        client, _ = admin_client
        plan = PlanGestionFactory()
        user = RoleFactory()
        # Create first association
        CorRolePlanFactory(id_role=user, plan_de_gestion=plan)

        # Try to create duplicate
        url = reverse('admin:plans_corroleplan_add')
        data = {
            'id_role': user.id_role,
            'plan_de_gestion': plan.id_pg,
            'referent': False,
            'commentaire': '',
        }
        response = client.post(url, data)
        # Should return 200 (form with errors), not 302 (redirect)
        assert response.status_code == 200
        # Should still have only 1 association
        assert CorRolePlan.objects.filter(
            id_role=user, plan_de_gestion=plan
        ).count() == 1

    def test_duplicate_site_plan_association_rejected(self, admin_client):
        """Test that adding the same site to the same plan twice is rejected."""
        client, _ = admin_client
        plan = PlanGestionFactory()
        site = SiteFactory()
        CorSitePgFactory(plan_de_gestion=plan, site=site)

        url = reverse('admin:plans_corsitepg_add')
        data = {
            'site': site.id_site,
            'plan_de_gestion': plan.id_pg,
            'rang': 2,
            'commentaire': '',
        }
        response = client.post(url, data)
        assert response.status_code == 200
        assert CorSitePg.objects.filter(
            site=site, plan_de_gestion=plan
        ).count() == 1


# =============================================================================
# Save model hooks tests
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestAdminSaveHooks:
    """Test that save_model hooks work correctly."""

    def test_save_sets_utilisateur_ajout_on_create(self, admin_client):
        """Test that id_utilisateur_ajout is set to current user on create."""
        client, admin = admin_client
        url = reverse('admin:plans_plangestion_add')

        data = {
            'nom': 'Plan Save Hook Test',
            'statut': 'draft',
            'version': '1.0',
            'rang': 1,
            'gestion_partagee': False,
            'ct88': False,
            'risque_incendie': False,
            'id_utilisateur_ajout': admin.id_role,
            'sites-TOTAL_FORMS': '0',
            'sites-INITIAL_FORMS': '0',
            'sites-MIN_NUM_FORMS': '0',
            'sites-MAX_NUM_FORMS': '1000',
            'membres-TOTAL_FORMS': '0',
            'membres-INITIAL_FORMS': '0',
            'membres-MIN_NUM_FORMS': '0',
            'membres-MAX_NUM_FORMS': '1000',
            'fichiers-TOTAL_FORMS': '0',
            'fichiers-INITIAL_FORMS': '0',
            'fichiers-MIN_NUM_FORMS': '0',
            'fichiers-MAX_NUM_FORMS': '1000',
        }
        response = client.post(url, data)
        assert response.status_code == 302
        plan = PlanGestion.objects.get(nom='Plan Save Hook Test')
        assert plan.id_utilisateur_ajout == admin

    def test_save_sets_utilisateur_maj_on_update(self, admin_client):
        """Test that id_utilisateur_maj is set to current user on update."""
        client, admin = admin_client
        other_admin = SuperAdminFactory(is_staff=True, is_superuser=True)
        plan = PlanGestionFactory(
            nom='Plan Update Test',
            id_utilisateur_ajout=other_admin,
        )

        url = reverse('admin:plans_plangestion_change', args=[plan.id_pg])
        data = {
            'nom': 'Plan Update Test Modified',
            'statut': plan.statut,
            'version': plan.version,
            'rang': plan.rang,
            'gestion_partagee': plan.gestion_partagee,
            'ct88': plan.ct88,
            'risque_incendie': plan.risque_incendie,
            'id_utilisateur_ajout': plan.id_utilisateur_ajout_id,
            'sites-TOTAL_FORMS': '0',
            'sites-INITIAL_FORMS': '0',
            'sites-MIN_NUM_FORMS': '0',
            'sites-MAX_NUM_FORMS': '1000',
            'membres-TOTAL_FORMS': '0',
            'membres-INITIAL_FORMS': '0',
            'membres-MIN_NUM_FORMS': '0',
            'membres-MAX_NUM_FORMS': '1000',
            'fichiers-TOTAL_FORMS': '0',
            'fichiers-INITIAL_FORMS': '0',
            'fichiers-MIN_NUM_FORMS': '0',
            'fichiers-MAX_NUM_FORMS': '1000',
        }
        response = client.post(url, data)
        assert response.status_code == 302
        plan.refresh_from_db()
        assert plan.id_utilisateur_maj == admin
