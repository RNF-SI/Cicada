"""
Unit tests for users app models.
Tests Role, BibOrganismes, Site, CorRoleSite, CorOgSite models.
"""
import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.users.models import Role, BibOrganismes, Site, CorRoleSite, CorOgSite
from tests.factories.users import (
    RoleFactory, UserFactory, SuperAdminFactory, AdminOrganismeFactory,
    ReferentFactory, OrganismeFactory, SiteFactory, CorRoleSiteFactory,
    CorOgSiteFactory
)


@pytest.mark.django_db
@pytest.mark.unit
class TestRoleModel:
    """Tests for the Role (User) model."""

    def test_create_user(self):
        """Test creating a basic user."""
        user = RoleFactory()
        assert user.id_role is not None
        assert user.email is not None
        assert user.is_active
        assert not user.is_superuser
        assert user.role_level == 'utilisateur'

    def test_create_user_with_email(self):
        """Test creating user with specific email."""
        user = RoleFactory(email='specific@test.fr')
        assert user.email == 'specific@test.fr'

    def test_user_email_unique(self):
        """Test that email must be unique."""
        RoleFactory(email='unique@test.fr')
        with pytest.raises(IntegrityError):
            RoleFactory(email='unique@test.fr')

    def test_user_str_method_with_names(self):
        """Test User __str__ method with first and last name."""
        user = RoleFactory(nom_role='Dupont', prenom_role='Jean')
        assert str(user) == 'Jean Dupont'

    def test_user_str_method_without_names(self):
        """Test User __str__ method falls back to email."""
        user = RoleFactory(nom_role=None, prenom_role=None, email='fallback@test.fr')
        assert str(user) == 'fallback@test.fr'

    def test_get_full_name_with_names(self):
        """Test get_full_name method with names."""
        user = RoleFactory(nom_role='Martin', prenom_role='Marie')
        assert user.get_full_name() == 'Marie Martin'

    def test_get_full_name_without_names(self):
        """Test get_full_name falls back to email."""
        user = RoleFactory(nom_role=None, prenom_role=None, email='test@test.fr')
        assert user.get_full_name() == 'test@test.fr'

    def test_get_short_name_with_prenom(self):
        """Test get_short_name returns first name."""
        user = RoleFactory(prenom_role='Pierre')
        assert user.get_short_name() == 'Pierre'

    def test_get_short_name_without_prenom(self):
        """Test get_short_name falls back to email."""
        user = RoleFactory(prenom_role=None, email='short@test.fr')
        assert user.get_short_name() == 'short@test.fr'

    def test_user_password_is_hashed(self):
        """Test that password is properly hashed."""
        user = RoleFactory(password='MySecretPassword123!')
        # Password should not be stored in plain text
        assert user.password != 'MySecretPassword123!'
        # But should validate with check_password
        assert user.check_password('MySecretPassword123!')

    def test_user_uuid_is_generated(self):
        """Test that uuid_role is automatically generated."""
        user = RoleFactory()
        assert user.uuid_role is not None

    def test_user_dates_auto_set(self):
        """Test that date_insert and date_update are auto-set."""
        user = RoleFactory()
        assert user.date_insert is not None
        assert user.date_update is not None


@pytest.mark.django_db
@pytest.mark.unit
class TestRolePermissionMethods:
    """Tests for Role permission methods (is_super_admin, is_admin_organisme, etc.)."""

    def test_is_super_admin_for_super_admin(self):
        """Test is_super_admin returns True for super_admin role."""
        admin = SuperAdminFactory()
        assert admin.is_super_admin() is True

    def test_is_super_admin_for_superuser(self):
        """Test is_super_admin returns True for is_superuser=True."""
        user = RoleFactory(is_superuser=True, role_level='utilisateur')
        assert user.is_super_admin() is True

    def test_is_super_admin_for_regular_user(self):
        """Test is_super_admin returns False for regular users."""
        user = RoleFactory()
        assert user.is_super_admin() is False

    def test_is_super_admin_for_admin_og(self):
        """Test is_super_admin returns False for admin_og."""
        admin_og = AdminOrganismeFactory()
        assert admin_og.is_super_admin() is False

    def test_is_admin_organisme_for_admin_og(self):
        """Test is_admin_organisme returns True for admin_og role."""
        admin_og = AdminOrganismeFactory()
        assert admin_og.is_admin_organisme() is True

    def test_is_admin_organisme_for_super_admin(self):
        """Test is_admin_organisme returns True for super_admin (hierarchy)."""
        admin = SuperAdminFactory()
        assert admin.is_admin_organisme() is True

    def test_is_admin_organisme_for_referent(self):
        """Test is_admin_organisme returns False for referent."""
        referent = ReferentFactory()
        assert referent.is_admin_organisme() is False

    def test_is_admin_organisme_for_regular_user(self):
        """Test is_admin_organisme returns False for regular users."""
        user = RoleFactory()
        assert user.is_admin_organisme() is False

    def test_is_referent_for_site_referent(self):
        """Test is_referent returns True for user who is site referent."""
        user = RoleFactory()
        site = SiteFactory()
        # Create a validated site referent assignment
        CorRoleSite.objects.create(
            id_role=user,
            id_site=site,
            referent=True,
            referent_valid=True
        )
        assert user.is_referent() is True

    def test_is_referent_for_unvalidated_site_referent(self):
        """Test is_referent returns False for unvalidated site referent."""
        user = RoleFactory()
        site = SiteFactory()
        # Create an unvalidated site referent assignment
        CorRoleSite.objects.create(
            id_role=user,
            id_site=site,
            referent=True,
            referent_valid=False
        )
        assert user.is_referent() is False

    def test_is_referent_for_admin_og(self):
        """Test is_referent returns True for admin_og (hierarchy)."""
        admin_og = AdminOrganismeFactory()
        assert admin_og.is_referent() is True

    def test_is_referent_for_super_admin(self):
        """Test is_referent returns True for super_admin (hierarchy)."""
        admin = SuperAdminFactory()
        assert admin.is_referent() is True

    def test_is_referent_for_regular_user(self):
        """Test is_referent returns False for regular users."""
        user = RoleFactory()
        assert user.is_referent() is False


@pytest.mark.django_db
@pytest.mark.unit
class TestCanManageOrganisme:
    """Tests for can_manage_organisme method."""

    def test_super_admin_can_manage_any_organisme(self):
        """Test super admin can manage any organisme."""
        admin = SuperAdminFactory()
        organisme = OrganismeFactory()
        assert admin.can_manage_organisme(organisme) is True

    def test_admin_og_can_manage_own_organisme(self):
        """Test admin_og can manage their own organisme."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        assert admin_og.can_manage_organisme(organisme) is True

    def test_admin_og_cannot_manage_other_organisme(self):
        """Test admin_og cannot manage another organisme."""
        organisme1 = OrganismeFactory()
        organisme2 = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme1)
        assert admin_og.can_manage_organisme(organisme2) is False

    def test_referent_cannot_manage_organisme(self):
        """Test referent cannot manage any organisme."""
        organisme = OrganismeFactory()
        referent = ReferentFactory(id_organisme=organisme)
        assert referent.can_manage_organisme(organisme) is False

    def test_regular_user_cannot_manage_organisme(self):
        """Test regular user cannot manage any organisme."""
        organisme = OrganismeFactory()
        user = RoleFactory()
        assert user.can_manage_organisme(organisme) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestCanManageSite:
    """Tests for can_manage_site method."""

    def test_super_admin_can_manage_any_site(self):
        """Test super admin can manage any site."""
        admin = SuperAdminFactory()
        site = SiteFactory()
        assert admin.can_manage_site(site) is True

    def test_referent_can_manage_assigned_site(self):
        """Test referent can manage sites they're assigned to as validated referent."""
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(
            id_role=referent,
            id_site=site,
            referent=True,
            referent_valid=True
        )
        assert referent.can_manage_site(site) is True

    def test_referent_cannot_manage_unvalidated_site(self):
        """Test referent cannot manage site if not validated."""
        referent = ReferentFactory()
        site = SiteFactory()
        CorRoleSiteFactory(
            id_role=referent,
            id_site=site,
            referent=True,
            referent_valid=False  # Not validated
        )
        assert referent.can_manage_site(site) is False

    def test_referent_cannot_manage_unassigned_site(self):
        """Test referent cannot manage site they're not assigned to."""
        referent = ReferentFactory()
        site = SiteFactory()
        # No CorRoleSite created
        assert referent.can_manage_site(site) is False

    def test_admin_og_can_manage_site_via_organisme(self):
        """Test admin_og can manage site linked to their organisme."""
        organisme = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)
        assert admin_og.can_manage_site(site) is True

    def test_admin_og_cannot_manage_unlinked_site(self):
        """Test admin_og cannot manage site not linked to their organisme."""
        organisme1 = OrganismeFactory()
        organisme2 = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=organisme1)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme2)  # Different organisme
        assert admin_og.can_manage_site(site) is False

    def test_regular_user_cannot_manage_site(self):
        """Test regular user cannot manage any site."""
        user = RoleFactory()
        site = SiteFactory()
        assert user.can_manage_site(site) is False


@pytest.mark.django_db
@pytest.mark.unit
class TestBibOrganismesModel:
    """Tests for the BibOrganismes model."""

    def test_create_organisme(self):
        """Test creating an organisme."""
        organisme = OrganismeFactory()
        assert organisme.id_organisme is not None
        assert organisme.uuid_organisme is not None

    def test_organisme_str_method(self):
        """Test Organisme __str__ method."""
        organisme = OrganismeFactory(nom_organisme='RNF Test')
        assert str(organisme) == 'RNF Test'

    def test_organisme_str_method_without_name(self):
        """Test Organisme __str__ fallback."""
        organisme = OrganismeFactory(nom_organisme=None, email_organisme='test@test.fr')
        assert str(organisme) == f'Organisme {organisme.id_organisme}'

    def test_organisme_parent_relationship(self):
        """Test parent organisme relationship."""
        parent = OrganismeFactory(nom_organisme='Parent Org')
        child = OrganismeFactory(nom_organisme='Child Org', id_parent=parent)
        assert child.id_parent == parent
        assert child.id_parent.nom_organisme == 'Parent Org'

    def test_organisme_dates_auto_set(self):
        """Test that meta_create_date and meta_update_date are auto-set."""
        organisme = OrganismeFactory()
        assert organisme.meta_create_date is not None
        assert organisme.meta_update_date is not None


@pytest.mark.django_db
@pytest.mark.unit
class TestSiteModel:
    """Tests for the Site model."""

    def test_create_site(self):
        """Test creating a site."""
        site = SiteFactory()
        assert site.id_site is not None
        assert site.nom_site is not None

    def test_site_str_method(self):
        """Test Site __str__ method."""
        site = SiteFactory(nom_site='Réserve Naturelle Test')
        assert str(site) == 'Réserve Naturelle Test'

    def test_site_with_geometry(self):
        """Test site with PostGIS geometry."""
        site = SiteFactory()
        assert site.geom is not None
        assert site.geom_pt is not None
        # Check SRID
        assert site.geom.srid == 4326
        assert site.geom_pt.srid == 4326

    def test_site_default_values(self):
        """Test site default values."""
        site = SiteFactory()
        assert site.active is True
        assert site.marin is False
        assert site.outre_mer is False


@pytest.mark.django_db
@pytest.mark.unit
class TestCorRoleSiteModel:
    """Tests for the CorRoleSite model."""

    def test_create_cor_role_site(self):
        """Test creating a user-site relationship."""
        user = RoleFactory()
        site = SiteFactory()
        cor = CorRoleSiteFactory(id_role=user, id_site=site)
        assert cor.id_role == user
        assert cor.id_site == site

    def test_cor_role_site_str_method(self):
        """Test CorRoleSite __str__ method."""
        user = RoleFactory(nom_role='Test', prenom_role='User')
        site = SiteFactory(nom_site='Test Site')
        cor = CorRoleSiteFactory(id_role=user, id_site=site)
        assert str(cor) == 'User Test - Test Site'

    def test_cor_role_site_unique_constraint(self):
        """Test unique constraint on user-site pair."""
        user = RoleFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site)
        with pytest.raises(IntegrityError):
            CorRoleSiteFactory(id_role=user, id_site=site)

    def test_cor_role_site_referent_flags(self):
        """Test referent and conservateur flags."""
        cor = CorRoleSiteFactory(referent=True, referent_valid=True, conservateur=True)
        assert cor.referent is True
        assert cor.referent_valid is True
        assert cor.conservateur is True


@pytest.mark.django_db
@pytest.mark.unit
class TestCorOgSiteModel:
    """Tests for the CorOgSite model."""

    def test_create_cor_og_site(self):
        """Test creating an organisme-site relationship."""
        organisme = OrganismeFactory()
        site = SiteFactory()
        cor = CorOgSiteFactory(uuid_og=organisme, id_site=site)
        assert cor.uuid_og == organisme
        assert cor.id_site == site

    def test_cor_og_site_str_method(self):
        """Test CorOgSite __str__ method."""
        organisme = OrganismeFactory(nom_organisme='Test Org')
        site = SiteFactory(nom_site='Test Site')
        cor = CorOgSiteFactory(uuid_og=organisme, id_site=site)
        assert str(cor) == 'Test Site - Test Org'

    def test_cor_og_site_principal_flag(self):
        """Test principal gestionnaire flag."""
        cor = CorOgSiteFactory(principal=True)
        assert cor.principal is True
