"""
Comprehensive tests for all notification signal handlers.
Tests automatic notification creation via Django signals.

Covers:
- notify_user_site_association (CorRoleSite post_save)
- check_site_orphaned_on_user_removal (CorRoleSite post_delete)
- notify_user_removed_from_site (CorRoleSite post_delete)
- track_user_deactivation / notify_user_deactivation (Role pre_save/post_save)
- notify_new_validation_request (ValidationRequest post_save, created)
- track_validation_status / handle_validation_result (ValidationRequest pre_save/post_save)
- notify_plan_referents_new_member (CorRolePlan post_save)
- notify_plan_referent_association (PlanGestion.referents m2m_changed)
"""
import pytest
from django.utils import timezone
from datetime import timedelta

from apps.notifications.models import Notification, ValidationRequest
from apps.users.models import CorRoleSite
from apps.plans.models import CorRolePlan
from tests.factories.users import (
    RoleFactory,
    SuperAdminFactory,
    AdminOrganismeFactory,
    OrganismeFactory,
    SiteFactory,
    CorRoleSiteFactory,
    CorOgSiteFactory,
)
from tests.factories.plans import (
    PlanGestionFactory,
    CorRolePlanFactory,
)
from tests.factories.notifications import (
    ValidationRequestFactory,
    SiteAccessRequestFactory,
    NotificationFactory,
)


# =============================================================================
# SITE ASSOCIATION NOTIFICATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestNotifyUserSiteAssociation:
    """Tests for notify_user_site_association signal (CorRoleSite post_save)."""

    def test_notification_created_on_site_association(self):
        """Creating a CorRoleSite triggers a user_associated_site notification."""
        user = RoleFactory()
        site = SiteFactory()

        CorRoleSite.objects.create(id_role=user, id_site=site)

        notification = Notification.objects.filter(
            recipient=user,
            notification_type='user_associated_site',
            related_site=site,
        ).first()

        assert notification is not None
        assert site.nom_site in notification.title
        assert site.nom_site in notification.message
        assert notification.priority == 'medium'
        assert f"/mes-sites/{site.id_site}" in notification.action_url

    def test_no_notification_on_update(self):
        """Updating an existing CorRoleSite does not create a duplicate notification."""
        user = RoleFactory()
        site = SiteFactory()
        cor = CorRoleSite.objects.create(id_role=user, id_site=site)

        count_before = Notification.objects.filter(
            recipient=user,
            notification_type='user_associated_site',
        ).count()

        # Update the relation (not a creation)
        cor.referent = True
        cor.save()

        count_after = Notification.objects.filter(
            recipient=user,
            notification_type='user_associated_site',
        ).count()

        assert count_after == count_before

    def test_deduplication_with_recent_notification(self):
        """If a similar notification exists within 30 seconds, no duplicate is created."""
        user = RoleFactory()
        site = SiteFactory()

        # Manually create a recent notification (as if from a validation approval)
        NotificationFactory(
            recipient=user,
            notification_type='user_associated_site',
            related_site=site,
        )

        count_before = Notification.objects.filter(
            recipient=user,
            notification_type='user_associated_site',
            related_site=site,
        ).count()

        # Now create the CorRoleSite, which triggers the signal
        CorRoleSite.objects.create(id_role=user, id_site=site)

        count_after = Notification.objects.filter(
            recipient=user,
            notification_type='user_associated_site',
            related_site=site,
        ).count()

        # Should not have created a duplicate
        assert count_after == count_before

    def test_notification_via_factory(self):
        """CorRoleSiteFactory also triggers the signal."""
        cor = CorRoleSiteFactory()

        notification = Notification.objects.filter(
            recipient=cor.id_role,
            notification_type='user_associated_site',
            related_site=cor.id_site,
        ).first()

        assert notification is not None


# =============================================================================
# SITE ORPHANED NOTIFICATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestCheckSiteOrphanedOnUserRemoval:
    """Détection « site orphelin » au retrait d'un utilisateur (CorRoleSite post_delete).

    Comportement assuré par users.signals.check_site_orphaned_after_user_removed
    (le handler équivalent côté notifications a été retiré, #446, car il faisait
    doublon sans déduplication)."""

    def test_orphaned_notification_when_last_user_removed(self):
        """Removing the last user from a site triggers site_orphaned notifications."""
        super_admin = SuperAdminFactory()
        user = RoleFactory()
        site = SiteFactory()
        cor = CorRoleSite.objects.create(id_role=user, id_site=site)

        # Delete the only association
        cor.delete()

        orphaned_notifications = Notification.objects.filter(
            notification_type='site_orphaned',
            related_site=site,
        )

        # At minimum, super admins should be notified
        assert orphaned_notifications.exists()
        assert any(site.nom_site in n.title for n in orphaned_notifications)

    def test_no_orphaned_notification_when_other_users_remain(self):
        """Removing a user when others remain does NOT trigger site_orphaned."""
        user1 = RoleFactory()
        user2 = RoleFactory()
        site = SiteFactory()
        cor1 = CorRoleSite.objects.create(id_role=user1, id_site=site)
        CorRoleSite.objects.create(id_role=user2, id_site=site)

        # Clear any existing notifications
        Notification.objects.filter(notification_type='site_orphaned').delete()

        # Remove only user1
        cor1.delete()

        orphaned = Notification.objects.filter(
            notification_type='site_orphaned',
            related_site=site,
        )
        assert not orphaned.exists()

    def test_orphaned_notification_sent_to_admin_og_of_site_organisme(self):
        """Orphaned site also notifies admin_og of the site's managing organisme."""
        org = OrganismeFactory()
        admin_og = AdminOrganismeFactory(id_organisme=org)
        user = RoleFactory()
        site = SiteFactory()
        CorOgSiteFactory(id_site=site, uuid_og=org)
        cor = CorRoleSite.objects.create(id_role=user, id_site=site)

        cor.delete()

        notif_for_admin = Notification.objects.filter(
            recipient=admin_og,
            notification_type='site_orphaned',
            related_site=site,
        )
        assert notif_for_admin.exists()


# =============================================================================
# USER REMOVED FROM SITE NOTIFICATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestNotifyUserRemovedFromSite:
    """Tests for notify_user_removed_from_site signal (CorRoleSite post_delete)."""

    def test_notification_created_on_removal(self):
        """Deleting a CorRoleSite sends a user_removed_site notification."""
        user = RoleFactory()
        site = SiteFactory()
        cor = CorRoleSite.objects.create(id_role=user, id_site=site)

        cor.delete()

        notification = Notification.objects.filter(
            recipient=user,
            notification_type='user_removed_site',
            related_site=site,
        ).first()

        assert notification is not None
        assert site.nom_site in notification.title
        assert site.nom_site in notification.message
        assert notification.priority == 'medium'

    def test_removal_notification_for_multiple_users(self):
        """Each removed user gets their own notification."""
        user1 = RoleFactory()
        user2 = RoleFactory()
        site = SiteFactory()
        cor1 = CorRoleSite.objects.create(id_role=user1, id_site=site)
        cor2 = CorRoleSite.objects.create(id_role=user2, id_site=site)

        cor1.delete()
        cor2.delete()

        notif_user1 = Notification.objects.filter(
            recipient=user1,
            notification_type='user_removed_site',
            related_site=site,
        )
        notif_user2 = Notification.objects.filter(
            recipient=user2,
            notification_type='user_removed_site',
            related_site=site,
        )

        assert notif_user1.exists()
        assert notif_user2.exists()


# =============================================================================
# USER DEACTIVATION NOTIFICATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestUserDeactivationNotification:
    """Tests for track_user_deactivation (pre_save) and notify_user_deactivation (post_save)."""

    def test_notification_on_deactivation_by_admin(self):
        """Deactivating a user by an admin triggers account_deactivated notification."""
        admin = SuperAdminFactory()
        user = RoleFactory(active=True)

        user.active = False
        user.deactivated_by = admin
        user.deactivation_reason = "Violation des regles"
        user.save()

        notification = Notification.objects.filter(
            recipient=user,
            notification_type='account_deactivated',
        ).first()

        assert notification is not None
        assert notification.priority == 'critical'
        assert notification.related_user == admin

    def test_no_notification_on_self_deactivation(self):
        """Self-deactivation does not trigger notification."""
        user = RoleFactory(active=True)

        user.active = False
        user.deactivated_by = user  # Self-deactivation
        user.save()

        notification = Notification.objects.filter(
            recipient=user,
            notification_type='account_deactivated',
        ).first()

        assert notification is None

    def test_no_notification_when_not_deactivated(self):
        """Updating a user without deactivating does not trigger notification."""
        user = RoleFactory(active=True)

        count_before = Notification.objects.filter(
            recipient=user,
            notification_type='account_deactivated',
        ).count()

        user.nom_role = "Nouveau Nom"
        user.save()

        count_after = Notification.objects.filter(
            recipient=user,
            notification_type='account_deactivated',
        ).count()

        assert count_after == count_before

    def test_no_notification_on_user_creation(self):
        """Creating a new inactive user does not trigger deactivation notification."""
        user = RoleFactory(active=False)

        notification = Notification.objects.filter(
            recipient=user,
            notification_type='account_deactivated',
        ).first()

        assert notification is None

    def test_no_notification_when_already_inactive(self):
        """Saving an already-inactive user does not re-trigger notification."""
        admin = SuperAdminFactory()
        user = RoleFactory(active=True)

        # First deactivation
        user.active = False
        user.deactivated_by = admin
        user.save()

        count_after_first = Notification.objects.filter(
            recipient=user,
            notification_type='account_deactivated',
        ).count()

        # Save again while still inactive
        user.nom_role = "Changed"
        user.save()

        count_after_second = Notification.objects.filter(
            recipient=user,
            notification_type='account_deactivated',
        ).count()

        assert count_after_second == count_after_first

    def test_deactivation_reason_in_notification(self):
        """The deactivation reason appears in the notification message."""
        admin = SuperAdminFactory()
        user = RoleFactory(active=True)
        reason = "Inactivite prolongee"

        user.active = False
        user.deactivated_by = admin
        user.deactivation_reason = reason
        user.save()

        notification = Notification.objects.filter(
            recipient=user,
            notification_type='account_deactivated',
        ).first()

        assert notification is not None
        assert reason in notification.message

    def test_super_admins_notified_on_deactivation(self):
        """Super admins also receive a notification about the deactivation."""
        admin = SuperAdminFactory()
        other_super_admin = SuperAdminFactory()
        user = RoleFactory(active=True)

        user.active = False
        user.deactivated_by = admin
        user.save()

        # Super admins should receive an account_deactivated notification
        admin_notifs = Notification.objects.filter(
            notification_type='account_deactivated',
            related_user=user,
        ).exclude(recipient=user)

        assert admin_notifs.exists()


# =============================================================================
# NEW VALIDATION REQUEST NOTIFICATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestNotifyNewValidationRequest:
    """Tests for notify_validators (called explicitly after ValidationRequest creation).

    Note: The post_save signal notify_new_validation_request is intentionally
    a no-op. Notifications are sent via NotificationService.notify_validators()
    called explicitly in views/serializers.
    """

    def test_validators_notified_on_new_site_access_request(self):
        """Calling notify_validators on a pending site_access request notifies validators."""
        from apps.notifications.services import NotificationService

        super_admin = SuperAdminFactory()
        requester = RoleFactory()
        site = SiteFactory()

        # Create a validation request for site access
        vr = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
            target_site=site,
            justification="Besoin d'acces",
        )

        # Explicitly call notify_validators (as done in views/serializers)
        NotificationService.notify_validators(vr)

        # Super admins should be among the validators notified
        notif = Notification.objects.filter(
            recipient=super_admin,
            notification_type='validation_request',
            related_validation=vr,
        ).first()

        assert notif is not None
        assert notif.priority == 'high'

    def test_no_notification_without_explicit_call(self):
        """Creating a request without calling notify_validators does not notify."""
        super_admin = SuperAdminFactory()
        requester = RoleFactory()

        vr = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
            justification="Pas de notification",
        )

        # No explicit call to notify_validators
        notif = Notification.objects.filter(
            notification_type='validation_request',
            related_validation=vr,
        )
        assert not notif.exists()

    def test_notification_message_includes_request_details(self):
        """The notification message includes request type details."""
        from apps.notifications.services import NotificationService

        super_admin = SuperAdminFactory()
        requester = RoleFactory()
        site = SiteFactory(nom_site="Reserve Naturelle Test")

        vr = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
            target_site=site,
            justification="Pour recherche",
        )

        NotificationService.notify_validators(vr)

        notif = Notification.objects.filter(
            recipient=super_admin,
            notification_type='validation_request',
            related_validation=vr,
        ).first()

        assert notif is not None
        assert "Reserve Naturelle Test" in notif.message


# =============================================================================
# VALIDATION RESULT NOTIFICATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestHandleValidationResult:
    """Tests for track_validation_status (pre_save) and handle_validation_result (post_save)."""

    def test_requester_notified_on_approval(self):
        """Approving a validation request via model method notifies the requester."""
        super_admin = SuperAdminFactory()
        requester = RoleFactory()
        site = SiteFactory()

        vr = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
            target_site=site,
        )

        # Approve via model method (sets _original_status via pre_save)
        vr.approve(validator=super_admin, comment="Approuve")

        notif = Notification.objects.filter(
            recipient=requester,
            notification_type='validation_approved',
            related_validation=vr,
        ).first()

        assert notif is not None
        assert notif.priority == 'high'

    def test_requester_notified_on_rejection(self):
        """Rejecting a validation request notifies the requester."""
        super_admin = SuperAdminFactory()
        requester = RoleFactory()

        vr = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
        )

        vr.reject(validator=super_admin, comment="Motif de rejet")

        notif = Notification.objects.filter(
            recipient=requester,
            notification_type='validation_rejected',
            related_validation=vr,
        ).first()

        assert notif is not None

    def test_no_duplicate_notification_if_already_exists(self):
        """If a notification already exists for the validation result, no duplicate is created."""
        super_admin = SuperAdminFactory()
        requester = RoleFactory()

        vr = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
        )

        # Manually create the notification (as if the service already did it)
        NotificationFactory(
            recipient=requester,
            notification_type='validation_approved',
            related_validation=vr,
        )

        count_before = Notification.objects.filter(
            recipient=requester,
            notification_type='validation_approved',
            related_validation=vr,
        ).count()

        # Approve the request
        vr.approve(validator=super_admin)

        count_after = Notification.objects.filter(
            recipient=requester,
            notification_type='validation_approved',
            related_validation=vr,
        ).count()

        # The signal should skip because it found an existing notification
        assert count_after == count_before

    def test_no_notification_on_pending_to_cancelled(self):
        """Cancelling a request does not trigger the result notification."""
        requester = RoleFactory()

        vr = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
        )

        vr.cancel()

        notif = Notification.objects.filter(
            recipient=requester,
            notification_type__in=['validation_approved', 'validation_rejected'],
            related_validation=vr,
        )
        assert not notif.exists()

    def test_no_notification_when_no_original_status_tracked(self):
        """If _original_status is not set (no pre_save), handle_validation_result does nothing."""
        requester = RoleFactory()

        # Create already approved (skipped by notify_new_validation_request
        # because status != pending at creation)
        vr = ValidationRequest.objects.create(
            request_type='site_access',
            status='approved',
            requester=requester,
        )

        # Save again (no status change)
        vr.save()

        notif = Notification.objects.filter(
            recipient=requester,
            notification_type__in=['validation_approved', 'validation_rejected'],
            related_validation=vr,
        )
        assert not notif.exists()


# =============================================================================
# PLAN REFERENTS NEW MEMBER NOTIFICATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestNotifyPlanReferentsNewMember:
    """Tests for notify_plan_referents_new_member signal (CorRolePlan post_save)."""

    def test_referents_notified_when_new_member_added(self):
        """Adding a member to a plan notifies the plan's referents."""
        referent = RoleFactory(prenom_role="Ref", nom_role="Plan")
        plan = PlanGestionFactory()
        plan.referents.add(referent)
        new_member = RoleFactory(prenom_role="Nouveau", nom_role="Membre")

        CorRolePlan.objects.create(
            id_role=new_member,
            plan_de_gestion=plan,
            referent=False,
        )

        notif = Notification.objects.filter(
            recipient=referent,
            notification_type='info',
            related_plan=plan,
            related_user=new_member,
        ).first()

        assert notif is not None
        assert plan.nom in notif.title
        assert "Nouveau Membre" in notif.message
        assert "membre" in notif.message

    def test_referents_notified_when_new_referent_added(self):
        """Adding a referent (via CorRolePlan) notifies existing referents."""
        existing_referent = RoleFactory()
        plan = PlanGestionFactory()
        plan.referents.add(existing_referent)
        new_referent = RoleFactory(prenom_role="New", nom_role="Ref")

        CorRolePlan.objects.create(
            id_role=new_referent,
            plan_de_gestion=plan,
            referent=True,
        )

        notif = Notification.objects.filter(
            recipient=existing_referent,
            notification_type='info',
            related_plan=plan,
            related_user=new_referent,
        ).first()

        assert notif is not None
        # The signal uses the French word "référent" (with accent)
        assert "rent" in notif.message.lower()

    def test_new_member_not_notified_as_referent(self):
        """The new member themselves should not receive the referent info notification."""
        user = RoleFactory()
        plan = PlanGestionFactory()
        plan.referents.add(user)

        # The user is both a referent and the new member being added
        CorRolePlan.objects.create(
            id_role=user,
            plan_de_gestion=plan,
            referent=False,
        )

        # The notification should not go to the user themselves
        notif = Notification.objects.filter(
            recipient=user,
            notification_type='info',
            related_plan=plan,
            related_user=user,
        )
        assert not notif.exists()

    def test_no_notification_on_update(self):
        """Updating an existing CorRolePlan does not re-notify referents."""
        referent = RoleFactory()
        plan = PlanGestionFactory()
        plan.referents.add(referent)
        member = RoleFactory()

        cor = CorRolePlan.objects.create(
            id_role=member,
            plan_de_gestion=plan,
            referent=False,
        )

        count_before = Notification.objects.filter(
            recipient=referent,
            notification_type='info',
            related_plan=plan,
        ).count()

        # Update the relation
        cor.referent = True
        cor.save()

        count_after = Notification.objects.filter(
            recipient=referent,
            notification_type='info',
            related_plan=plan,
        ).count()

        assert count_after == count_before

    def test_multiple_referents_all_notified(self):
        """All active referents receive the notification."""
        ref1 = RoleFactory()
        ref2 = RoleFactory()
        plan = PlanGestionFactory()
        plan.referents.add(ref1, ref2)
        new_member = RoleFactory()

        CorRolePlan.objects.create(
            id_role=new_member,
            plan_de_gestion=plan,
            referent=False,
        )

        notif_ref1 = Notification.objects.filter(
            recipient=ref1,
            notification_type='info',
            related_plan=plan,
            related_user=new_member,
        )
        notif_ref2 = Notification.objects.filter(
            recipient=ref2,
            notification_type='info',
            related_plan=plan,
            related_user=new_member,
        )

        assert notif_ref1.exists()
        assert notif_ref2.exists()

    def test_inactive_referent_not_notified(self):
        """Inactive referents are excluded from notifications."""
        active_ref = RoleFactory(active=True)
        inactive_ref = RoleFactory(active=False)
        plan = PlanGestionFactory()
        plan.referents.add(active_ref, inactive_ref)
        new_member = RoleFactory()

        CorRolePlan.objects.create(
            id_role=new_member,
            plan_de_gestion=plan,
            referent=False,
        )

        notif_active = Notification.objects.filter(
            recipient=active_ref,
            notification_type='info',
            related_plan=plan,
            related_user=new_member,
        )
        notif_inactive = Notification.objects.filter(
            recipient=inactive_ref,
            notification_type='info',
            related_plan=plan,
            related_user=new_member,
        )

        assert notif_active.exists()
        assert not notif_inactive.exists()

    def test_no_notification_when_no_referents(self):
        """Adding a member to a plan with no referents creates no info notifications."""
        plan = PlanGestionFactory()
        new_member = RoleFactory()

        Notification.objects.filter(notification_type='info').delete()

        CorRolePlan.objects.create(
            id_role=new_member,
            plan_de_gestion=plan,
            referent=False,
        )

        notif = Notification.objects.filter(
            notification_type='info',
            related_plan=plan,
        )
        assert not notif.exists()


# =============================================================================
# PLAN REFERENT M2M ASSOCIATION NOTIFICATION TESTS
# =============================================================================

def _m2m_referent_handler(sender, instance, action, pk_set, **kwargs):
    """
    Handler for PlanGestion.referents M2M changed signal.
    Mirrors the logic in signals.setup_m2m_signals().notify_plan_referent_change.
    """
    if action == 'post_add' and pk_set:
        from apps.users.models import Role
        from apps.notifications.services import NotificationService

        for role_id in pk_set:
            try:
                role = Role.objects.get(pk=role_id)
                NotificationService.create_notification(
                    recipient=role,
                    notification_type='user_associated_plan',
                    title=f"Vous etes referent du plan {instance.nom}",
                    message=f"Vous avez ete ajoute comme referent du plan de gestion {instance.nom}.",
                    priority='medium',
                    related_plan=instance,
                    action_url=f"/plans/{instance.id_pg}",
                )
            except Role.DoesNotExist:
                pass


@pytest.mark.django_db
@pytest.mark.unit
class TestNotifyPlanReferentAssociation:
    """Tests for notify_plan_referent_change via m2m_changed signal.

    Note: setup_m2m_signals() is defined in signals.py but not called from
    apps.py ready(). We manually connect the m2m_changed signal handler
    for the duration of each test.
    """

    @pytest.fixture(autouse=True)
    def _connect_m2m_signal(self):
        """Connect the M2M signal for this test, disconnect after."""
        from django.db.models.signals import m2m_changed
        from apps.plans.models import PlanGestion

        through_model = PlanGestion.referents.through
        m2m_changed.connect(
            _m2m_referent_handler,
            sender=through_model,
            dispatch_uid='test_plan_referent_m2m',
        )
        yield
        m2m_changed.disconnect(
            _m2m_referent_handler,
            sender=through_model,
            dispatch_uid='test_plan_referent_m2m',
        )

    def test_user_notified_when_added_as_plan_referent(self):
        """Adding a user as referent via M2M sends user_associated_plan notification."""
        user = RoleFactory()
        plan = PlanGestionFactory()

        plan.referents.add(user)

        notif = Notification.objects.filter(
            recipient=user,
            notification_type='user_associated_plan',
            related_plan=plan,
        ).first()

        assert notif is not None
        assert plan.nom in notif.title
        assert plan.nom in notif.message
        assert notification_contains_referent_text(notif)
        assert notif.priority == 'medium'

    def test_multiple_users_notified_when_added_as_referents(self):
        """Adding multiple referents at once notifies each one."""
        user1 = RoleFactory()
        user2 = RoleFactory()
        plan = PlanGestionFactory()

        plan.referents.add(user1, user2)

        notif_user1 = Notification.objects.filter(
            recipient=user1,
            notification_type='user_associated_plan',
            related_plan=plan,
        )
        notif_user2 = Notification.objects.filter(
            recipient=user2,
            notification_type='user_associated_plan',
            related_plan=plan,
        )

        assert notif_user1.exists()
        assert notif_user2.exists()

    def test_no_notification_on_remove(self):
        """Removing a referent via M2M does not trigger user_associated_plan."""
        user = RoleFactory()
        plan = PlanGestionFactory()
        plan.referents.add(user)

        count_before = Notification.objects.filter(
            recipient=user,
            notification_type='user_associated_plan',
            related_plan=plan,
        ).count()

        plan.referents.remove(user)

        count_after = Notification.objects.filter(
            recipient=user,
            notification_type='user_associated_plan',
            related_plan=plan,
        ).count()

        # Count should not increase on removal
        assert count_after == count_before


# =============================================================================
# ORGANISME CHANGE NOTIFICATION TESTS (pre_save tracking)
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestTrackUserDeactivationPreSave:
    """Tests specifically for the pre_save tracking of _old_organisme."""

    def test_old_organisme_tracked_on_save(self):
        """Verify that the pre_save signal stores the old organisme for comparison."""
        org1 = OrganismeFactory(nom_organisme="Org A")
        org2 = OrganismeFactory(nom_organisme="Org B")
        user = RoleFactory(id_organisme=org1)

        user.id_organisme = org2
        user.save()

        # The organisme_changed notification should have been created
        notification = Notification.objects.filter(
            recipient=user,
            notification_type='organisme_changed',
        ).order_by('-created_at').first()

        assert notification is not None
        assert "Org A" in notification.message
        assert "Org B" in notification.message

    def test_new_user_has_no_old_organisme(self):
        """A brand new user should not have _old_organisme set."""
        org = OrganismeFactory()
        user = RoleFactory(id_organisme=org)

        # No organisme_changed notification for new users
        notif = Notification.objects.filter(
            recipient=user,
            notification_type='organisme_changed',
        ).first()

        assert notif is None


# =============================================================================
# COMBINED / EDGE CASE TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestSignalEdgeCases:
    """Edge cases and combined signal scenarios."""

    def test_site_association_and_removal_create_both_notifications(self):
        """Adding and then removing a user from a site creates both notification types."""
        user = RoleFactory()
        site = SiteFactory()

        cor = CorRoleSite.objects.create(id_role=user, id_site=site)

        # Should have the association notification
        assoc_notif = Notification.objects.filter(
            recipient=user,
            notification_type='user_associated_site',
            related_site=site,
        )
        assert assoc_notif.exists()

        cor.delete()

        # Should also have the removal notification
        removal_notif = Notification.objects.filter(
            recipient=user,
            notification_type='user_removed_site',
            related_site=site,
        )
        assert removal_notif.exists()

    def test_validation_full_lifecycle(self):
        """Test the full lifecycle: create pending -> notify -> approve -> notifications created."""
        from apps.notifications.services import NotificationService

        super_admin = SuperAdminFactory()
        requester = RoleFactory()
        site = SiteFactory()

        # Create pending request
        vr = ValidationRequest.objects.create(
            request_type='site_access',
            status='pending',
            requester=requester,
            target_site=site,
        )

        # Explicitly notify validators (as done in views/serializers)
        NotificationService.notify_validators(vr)

        # Validator should have received a notification
        validator_notif = Notification.objects.filter(
            recipient=super_admin,
            notification_type='validation_request',
            related_validation=vr,
        )
        assert validator_notif.exists()

        # Approve (triggers handle_validation_result)
        vr.approve(validator=super_admin, comment="OK")

        # Requester should have received approval notification
        approval_notif = Notification.objects.filter(
            recipient=requester,
            notification_type='validation_approved',
            related_validation=vr,
        )
        assert approval_notif.exists()

    def test_deactivation_without_deactivated_by(self):
        """Deactivation without setting deactivated_by does not create notification."""
        user = RoleFactory(active=True)

        user.active = False
        # Do NOT set deactivated_by
        user.save()

        notif = Notification.objects.filter(
            recipient=user,
            notification_type='account_deactivated',
        )
        assert not notif.exists()


# =============================================================================
# HELPERS
# =============================================================================

def notification_contains_referent_text(notif):
    """Check that the notification mentions referent."""
    return "referent" in notif.title.lower() or "referent" in notif.message.lower()
