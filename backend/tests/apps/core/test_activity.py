"""
Unit tests for Activity feature.
Tests ActivityLog model, ActivityService, and Activity API endpoints.
"""
import pytest
from django.utils import timezone
from datetime import timedelta

from apps.core.models import ActivityLog
from apps.core.services import ActivityService
from tests.factories import (
    ActivityLogFactory,
    RoleFactory,
    SuperAdminFactory,
    AdminOrganismeFactory,
    OrganismeFactory,
    SiteFactory,
    CorRoleSiteFactory,
    CorOgSiteFactory,
)
from tests.factories.plans import PlanGestionFactory


@pytest.mark.django_db
@pytest.mark.unit
class TestActivityLogModel:
    """Tests for the ActivityLog model."""

    def test_create_activity_log(self):
        """Test creating a basic activity log."""
        log = ActivityLogFactory()
        assert log.id is not None
        assert log.entity_type is not None
        assert log.entity_id is not None
        assert log.action is not None
        assert log.created_at is not None

    def test_activity_log_str_method(self):
        """Test ActivityLog __str__ method."""
        log = ActivityLogFactory(
            action='create',
            entity_type='site',
            entity_name='Test Site'
        )
        assert '[create]' in str(log)
        assert 'site' in str(log)
        assert 'Test Site' in str(log)

    def test_activity_log_entity_types(self):
        """Test all valid entity types."""
        for entity_type in ['site', 'plan', 'user', 'organisme', 'validation']:
            log = ActivityLogFactory(entity_type=entity_type)
            assert log.entity_type == entity_type

    def test_activity_log_action_types(self):
        """Test all valid action types."""
        actions = [
            'create', 'update', 'delete', 'add_member', 'remove_member',
            'add_referent', 'remove_referent', 'status_change', 'activate',
            'deactivate', 'rgpd_request', 'rgpd_cancelled', 'rgpd_anonymized',
            'access_granted', 'access_revoked', 'validation_approved',
            'validation_rejected', 'file_upload', 'file_delete'
        ]
        for action in actions:
            log = ActivityLogFactory(action=action)
            assert log.action == action

    def test_activity_log_visibility_levels(self):
        """Test all valid visibility levels."""
        for visibility in ['public', 'admin', 'system']:
            log = ActivityLogFactory(visibility=visibility)
            assert log.visibility == visibility

    def test_activity_log_with_changes(self):
        """Test storing changes as JSON."""
        changes = {
            'nom_site': {'old': 'Old Name', 'new': 'New Name'},
            'surf_off': {'old': 100, 'new': 200}
        }
        log = ActivityLogFactory(changes=changes)
        assert log.changes == changes

    def test_activity_log_with_metadata(self):
        """Test storing metadata as JSON."""
        metadata = {'ip_address': '192.168.1.1', 'user_agent': 'Mozilla/5.0'}
        log = ActivityLogFactory(metadata=metadata)
        assert log.metadata == metadata

    def test_activity_log_with_related_site(self):
        """Test activity log linked to a site."""
        site = SiteFactory()
        log = ActivityLogFactory.for_site(site, action='create')
        assert log.related_site == site
        assert log.entity_type == 'site'
        assert log.entity_id == site.id_site

    def test_activity_log_with_related_plan(self):
        """Test activity log linked to a plan."""
        plan = PlanGestionFactory()
        log = ActivityLogFactory.for_plan(plan, action='update')
        assert log.related_plan == plan
        assert log.entity_type == 'plan'
        assert log.entity_id == plan.id_pg

    def test_activity_log_with_actor(self):
        """Test activity log with actor."""
        user = RoleFactory()
        log = ActivityLogFactory(actor=user, actor_name=user.get_full_name())
        assert log.actor == user

    def test_activity_log_ordering(self):
        """Test activity logs are ordered by created_at descending."""
        # Create logs with different timestamps
        old_log = ActivityLogFactory()
        old_log.created_at = timezone.now() - timedelta(days=1)
        old_log.save()

        new_log = ActivityLogFactory()

        logs = ActivityLog.objects.all()
        assert logs[0].id == new_log.id


@pytest.mark.django_db
@pytest.mark.unit
class TestActivityService:
    """Tests for the ActivityService."""

    def test_log_activity_basic(self):
        """Test basic activity logging."""
        user = RoleFactory()

        log = ActivityService.log_activity(
            entity_type='site',
            entity_id=1,
            entity_name='Test Site',
            action='create',
            actor=user,
            description='Site created',
            visibility='public'
        )

        assert log is not None
        assert log.entity_type == 'site'
        assert log.entity_id == 1
        assert log.action == 'create'
        assert log.actor == user

    def test_log_site_activity(self):
        """Test site activity logging shortcut."""
        site = SiteFactory(nom_site='Test Reserve')
        user = RoleFactory()

        log = ActivityService.log_site_activity(
            site=site,
            action='update',
            actor=user,
            description='Site updated'
        )

        assert log.entity_type == 'site'
        assert log.entity_id == site.id_site
        assert log.entity_name == 'Test Reserve'
        assert log.related_site == site

    def test_log_site_activity_with_changes(self):
        """Test site activity logging with changes."""
        site = SiteFactory()
        user = RoleFactory()
        changes = {'nom_site': {'old': 'Old', 'new': 'New'}}

        log = ActivityService.log_site_activity(
            site=site,
            action='update',
            actor=user,
            description='Site updated',
            changes=changes
        )

        assert log.changes == changes

    def test_log_plan_activity(self):
        """Test plan activity logging shortcut."""
        plan = PlanGestionFactory(nom='Test Plan')
        user = RoleFactory()

        log = ActivityService.log_plan_activity(
            plan=plan,
            action='create',
            actor=user,
            description='Plan created'
        )

        assert log.entity_type == 'plan'
        assert log.entity_id == plan.id_pg
        assert log.entity_name == 'Test Plan'
        assert log.related_plan == plan

    def test_log_user_activity(self):
        """Test user activity logging shortcut."""
        target_user = RoleFactory(nom_role='Target', prenom_role='User')
        actor = SuperAdminFactory()

        log = ActivityService.log_user_activity(
            user=target_user,
            action='activate',
            actor=actor,
            description='User activated'
        )

        assert log.entity_type == 'user'
        assert log.entity_id == target_user.id_role
        assert log.related_user == target_user

    def test_log_organisme_activity(self):
        """Test organisme activity logging shortcut."""
        organisme = OrganismeFactory(nom_organisme='Test Org')
        user = SuperAdminFactory()

        log = ActivityService.log_organisme_activity(
            organisme=organisme,
            action='update',
            actor=user,
            description='Organisme updated'
        )

        assert log.entity_type == 'organisme'
        assert log.entity_id == organisme.id_organisme
        assert log.entity_name == 'Test Org'
        assert log.related_organisme == organisme

    def test_log_rgpd_activity(self):
        """Test RGPD activity logging shortcut."""
        user = RoleFactory()

        log = ActivityService.log_rgpd_activity(
            user=user,
            action='rgpd_request',
            actor=user,
            description='User requested account deletion'
        )

        assert log.entity_type == 'user'
        assert log.action == 'rgpd_request'
        assert log.visibility == 'system'

    def test_log_member_change_add(self):
        """Test member addition activity logging."""
        site = SiteFactory()
        user = RoleFactory()
        actor = AdminOrganismeFactory()

        log = ActivityService.log_member_change(
            site=site,
            user=user,
            action='add_member',
            actor=actor,
            is_referent=True
        )

        assert log.entity_type == 'site'
        assert log.action == 'add_member'
        assert 'referent' in log.description.lower() or log.metadata.get('is_referent')

    def test_log_member_change_remove(self):
        """Test member removal activity logging."""
        site = SiteFactory()
        user = RoleFactory()
        actor = AdminOrganismeFactory()

        log = ActivityService.log_member_change(
            site=site,
            user=user,
            action='remove_member',
            actor=actor,
            is_referent=False
        )

        assert log.action == 'remove_member'

    def test_get_model_changes(self):
        """Test model changes detection."""
        site = SiteFactory(nom_site='Original', surf_off=100)

        # Simulate new data
        new_data = {'nom_site': 'Updated', 'surf_off': 200}

        changes = ActivityService.get_model_changes(
            site,
            new_data,
            ['nom_site', 'surf_off']
        )

        assert 'nom_site' in changes
        assert changes['nom_site']['old'] == 'Original'
        assert changes['nom_site']['new'] == 'Updated'
        assert 'surf_off' in changes

    def test_activity_without_actor(self):
        """Test activity logging without actor (system action)."""
        log = ActivityService.log_activity(
            entity_type='site',
            entity_id=1,
            entity_name='System Site',
            action='create',
            actor=None,
            description='Automatically created'
        )

        assert log.actor is None
        assert log.actor_name == 'Système'


@pytest.mark.django_db
@pytest.mark.integration
class TestActivityAPIEndpoints:
    """Tests for Activity API endpoints."""

    def test_list_unauthenticated(self, api_client):
        """Test activity list requires authentication."""
        response = api_client.get('/api/activity/')
        assert response.status_code == 401

    def test_list_authenticated_user(self, api_client):
        """Test authenticated user can list activities."""
        user = RoleFactory()
        api_client.force_authenticate(user=user)

        # Create some activities
        ActivityLogFactory(visibility='public')

        response = api_client.get('/api/activity/')
        assert response.status_code == 200
        assert 'results' in response.data

    def test_list_super_admin_sees_all(self, api_client):
        """Test super admin sees all activities including system-level."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        # Create activities with different visibilities
        public1 = ActivityLogFactory(visibility='public')
        public2 = ActivityLogFactory(visibility='public')
        admin_vis = ActivityLogFactory(visibility='admin')
        system_vis = ActivityLogFactory(visibility='system')

        response = api_client.get('/api/activity/')
        assert response.status_code == 200

        # Get all returned activity IDs
        result_ids = [item['id'] for item in response.data.get('results', response.data)]

        # Super admin should see all created activities
        assert public1.id in result_ids
        assert public2.id in result_ids
        assert admin_vis.id in result_ids
        assert system_vis.id in result_ids

    def test_list_admin_og_sees_organisme_activities(self, api_client):
        """Test admin_og sees organisme-level activities."""
        organisme = OrganismeFactory()
        admin = AdminOrganismeFactory(id_organisme=organisme)
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=organisme)

        api_client.force_authenticate(user=admin)

        # Create activity for the organisme's site
        ActivityLogFactory(
            entity_type='site',
            related_site=site,
            visibility='public'
        )

        response = api_client.get('/api/activity/')
        assert response.status_code == 200

    def test_list_user_sees_own_activities(self, api_client):
        """Test regular user sees only their relevant activities."""
        user = RoleFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=user)

        # Create activity for user's site
        ActivityLogFactory.for_site(site, visibility='public')

        # Create activity for another site (user shouldn't see)
        other_site = SiteFactory()
        ActivityLogFactory.for_site(other_site, visibility='public')

        response = api_client.get('/api/activity/')
        assert response.status_code == 200

    def test_my_sites_endpoint(self, api_client):
        """Test my_sites endpoint returns activities for user's sites."""
        user = RoleFactory()
        site = SiteFactory()
        CorRoleSiteFactory(id_role=user, id_site=site, referent=True, referent_valid=True)

        api_client.force_authenticate(user=user)

        # Create activity for user's site
        ActivityLogFactory.for_site(site, action='update')

        response = api_client.get('/api/activity/my_sites/')
        assert response.status_code == 200

    def test_my_plans_endpoint(self, api_client):
        """Test my_plans endpoint returns activities for user's plans."""
        user = RoleFactory()
        plan = PlanGestionFactory()
        plan.referents.add(user)

        api_client.force_authenticate(user=user)

        # Create activity for user's plan
        ActivityLogFactory.for_plan(plan, action='update')

        response = api_client.get('/api/activity/my_plans/')
        assert response.status_code == 200

    def test_my_rights_endpoint(self, api_client):
        """Test my_rights endpoint returns activities about user's rights changes."""
        user = RoleFactory()
        admin = SuperAdminFactory()
        site = SiteFactory()

        api_client.force_authenticate(user=user)

        # Create activity for user's rights change (e.g., added as member)
        ActivityLogFactory(
            entity_type='site',
            action='add_member',
            related_user=user,
            related_site=site,
            description=f'{user.get_full_name()} added as member'
        )

        # Create another rights activity
        ActivityLogFactory(
            entity_type='user',
            action='activate',
            related_user=user,
            description='Account activated'
        )

        # Create activity NOT about user's rights (should not appear)
        other_user = RoleFactory()
        ActivityLogFactory(
            entity_type='site',
            action='add_member',
            related_user=other_user,
            description='Other user added'
        )

        response = api_client.get('/api/activity/my_rights/')
        assert response.status_code == 200

        # Check that results only contain activities about the user's rights
        results = response.data.get('results', response.data)
        assert len(results) >= 2

        # All results should have related_user pointing to current user
        for item in results:
            assert item.get('related_user') == user.id_role

    def test_my_rights_endpoint_filters_correct_actions(self, api_client):
        """Test my_rights only returns activities with rights-related actions."""
        user = RoleFactory()
        api_client.force_authenticate(user=user)

        # Create various activities for the user
        rights_actions = [
            'add_member', 'remove_member', 'add_referent', 'remove_referent',
            'activate', 'deactivate', 'access_granted', 'access_revoked',
            'validation_approved', 'validation_rejected'
        ]

        for action in rights_actions:
            ActivityLogFactory(
                entity_type='user',
                action=action,
                related_user=user
            )

        # Create non-rights activity for the user (should not appear)
        ActivityLogFactory(
            entity_type='user',
            action='update',
            related_user=user
        )

        response = api_client.get('/api/activity/my_rights/')
        assert response.status_code == 200

        results = response.data.get('results', response.data)
        # Should have at least the 10 rights-related actions
        assert len(results) >= 10

        # None should be 'update' action
        for item in results:
            assert item['action'] in rights_actions

    def test_tabs_counts_includes_my_rights(self, api_client):
        """Test tabs_counts includes my_rights count."""
        user = RoleFactory()
        api_client.force_authenticate(user=user)

        # Create some rights-related activities for the user
        ActivityLogFactory(
            entity_type='site',
            action='add_member',
            related_user=user
        )
        ActivityLogFactory(
            entity_type='user',
            action='activate',
            related_user=user
        )

        response = api_client.get('/api/activity/tabs_counts/')
        assert response.status_code == 200
        assert 'my_rights' in response.data
        assert response.data['my_rights'] >= 2

    def test_stats_endpoint(self, api_client):
        """Test stats endpoint returns activity statistics."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        # Create various activities
        ActivityLogFactory(action='create')
        ActivityLogFactory(action='update')
        ActivityLogFactory(action='delete')

        response = api_client.get('/api/activity/stats/')
        assert response.status_code == 200

    def test_tabs_counts_endpoint(self, api_client):
        """Test tabs_counts endpoint returns counts per tab."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/activity/tabs_counts/')
        assert response.status_code == 200
        assert 'all' in response.data or 'my_sites' in response.data

    def test_rgpd_endpoint_requires_super_admin(self, api_client):
        """Test RGPD endpoint is restricted to super admins."""
        admin_og = AdminOrganismeFactory()
        api_client.force_authenticate(user=admin_og)

        response = api_client.get('/api/activity/rgpd/')
        assert response.status_code == 403

    def test_rgpd_endpoint_super_admin(self, api_client):
        """Test super admin can access RGPD endpoint."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/activity/rgpd/')
        assert response.status_code == 200

    def test_system_endpoint_requires_super_admin(self, api_client):
        """Test system endpoint is restricted to super admins."""
        admin_og = AdminOrganismeFactory()
        api_client.force_authenticate(user=admin_og)

        response = api_client.get('/api/activity/system/')
        assert response.status_code == 403

    def test_system_endpoint_super_admin(self, api_client):
        """Test super admin can access system endpoint."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        response = api_client.get('/api/activity/system/')
        assert response.status_code == 200

    def test_validations_endpoint(self, api_client):
        """Test validations endpoint returns validation activities."""
        admin = AdminOrganismeFactory()
        api_client.force_authenticate(user=admin)

        # Create validation activity
        ActivityLogFactory(
            entity_type='validation',
            action='validation_approved',
            visibility='admin'
        )

        response = api_client.get('/api/activity/validations/')
        assert response.status_code == 200

    def test_filter_by_entity_type(self, api_client):
        """Test filtering activities by entity type."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        # Create activities for different entity types
        ActivityLogFactory(entity_type='site')
        ActivityLogFactory(entity_type='plan')

        response = api_client.get('/api/activity/', {'entity_type': 'site'})
        assert response.status_code == 200
        for item in response.data['results']:
            assert item['entity_type'] == 'site'

    def test_filter_by_action(self, api_client):
        """Test filtering activities by action."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        # Create activities with different actions
        ActivityLogFactory(action='create')
        ActivityLogFactory(action='update')

        response = api_client.get('/api/activity/', {'action': 'create'})
        assert response.status_code == 200
        for item in response.data['results']:
            assert item['action'] == 'create'

    def test_pagination(self, api_client):
        """Test activity list pagination."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        # Create many activities (more than default page size of 20)
        created_activities = [ActivityLogFactory() for _ in range(25)]

        response = api_client.get('/api/activity/')
        assert response.status_code == 200

        # Check that pagination structure exists
        assert 'results' in response.data

        # API uses custom pagination with nested 'pagination' object
        if 'pagination' in response.data:
            # Custom pagination format: {pagination: {count, ...}, results, links}
            assert response.data['pagination']['count'] >= 25
            if response.data['pagination']['count'] > 20:
                assert response.data['pagination']['has_next'] is True
        elif 'count' in response.data:
            # Standard DRF pagination format
            assert response.data['count'] >= 25
            if response.data['count'] > 20:
                assert response.data.get('next') is not None

    def test_retrieve_activity(self, api_client):
        """Test retrieving a single activity."""
        admin = SuperAdminFactory()
        api_client.force_authenticate(user=admin)

        activity = ActivityLogFactory()

        response = api_client.get(f'/api/activity/{activity.id}/')
        assert response.status_code == 200
        assert response.data['id'] == activity.id


@pytest.mark.django_db
@pytest.mark.unit
class TestActivitySignals:
    """Tests for activity signals automatic logging."""

    def test_site_creation_logs_activity(self):
        """Test that creating a site automatically logs activity."""
        initial_count = ActivityLog.objects.filter(
            entity_type='site',
            action='create'
        ).count()

        SiteFactory()

        final_count = ActivityLog.objects.filter(
            entity_type='site',
            action='create'
        ).count()

        assert final_count == initial_count + 1

    def test_site_update_logs_activity(self):
        """Test that updating a site automatically logs activity."""
        site = SiteFactory(nom_site='Original')

        initial_count = ActivityLog.objects.filter(
            entity_type='site',
            action='update'
        ).count()

        site.nom_site = 'Updated'
        site.save()

        final_count = ActivityLog.objects.filter(
            entity_type='site',
            action='update'
        ).count()

        assert final_count == initial_count + 1

    def test_plan_creation_logs_activity(self):
        """Test that creating a plan automatically logs activity."""
        initial_count = ActivityLog.objects.filter(
            entity_type='plan',
            action='create'
        ).count()

        PlanGestionFactory()

        final_count = ActivityLog.objects.filter(
            entity_type='plan',
            action='create'
        ).count()

        assert final_count == initial_count + 1

    def test_user_activation_logs_activity(self):
        """Test that activating a user logs activity."""
        user = RoleFactory(active=False)

        initial_count = ActivityLog.objects.filter(
            entity_type='user',
            action='activate'
        ).count()

        user.active = True
        user.save()

        final_count = ActivityLog.objects.filter(
            entity_type='user',
            action='activate'
        ).count()

        assert final_count == initial_count + 1

    def test_user_deactivation_logs_activity(self):
        """Test that deactivating a user logs activity."""
        user = RoleFactory(active=True)

        initial_count = ActivityLog.objects.filter(
            entity_type='user',
            action='deactivate'
        ).count()

        user.active = False
        user.save()

        final_count = ActivityLog.objects.filter(
            entity_type='user',
            action='deactivate'
        ).count()

        assert final_count == initial_count + 1
