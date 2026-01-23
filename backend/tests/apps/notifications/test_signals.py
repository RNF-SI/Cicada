"""
Unit tests for notifications app signals.
Tests automatic notification creation via Django signals.
"""
import pytest

from apps.notifications.models import Notification
from tests.factories.users import (
    RoleFactory, OrganismeFactory
)


# =============================================================================
# ORGANISME CHANGE NOTIFICATION TESTS
# =============================================================================

@pytest.mark.django_db
@pytest.mark.unit
class TestOrganismeChangeNotification:
    """Tests for notify_user_organisme_changed signal."""

    def test_notification_created_on_organisme_change(self):
        """Test notification is created when user's organisme changes."""
        org1 = OrganismeFactory(nom_organisme="Organisme A")
        org2 = OrganismeFactory(nom_organisme="Organisme B")
        user = RoleFactory(id_organisme=org1)

        # Count notifications before
        count_before = Notification.objects.filter(
            recipient=user,
            notification_type='organisme_changed'
        ).count()

        # Change organisme
        user.id_organisme = org2
        user.save()

        # Check notification was created
        count_after = Notification.objects.filter(
            recipient=user,
            notification_type='organisme_changed'
        ).count()

        assert count_after == count_before + 1

        # Verify notification content
        notification = Notification.objects.filter(
            recipient=user,
            notification_type='organisme_changed'
        ).order_by('-created_at').first()

        assert notification is not None
        assert notification.title == "Votre organisme a été modifié"
        assert "Organisme A" in notification.message
        assert "Organisme B" in notification.message
        assert notification.priority == 'high'
        assert notification.related_organisme == org2
        assert notification.action_url == "/profile"

    def test_no_notification_when_organisme_unchanged(self):
        """Test no notification is created when organisme doesn't change."""
        org = OrganismeFactory()
        user = RoleFactory(id_organisme=org)

        # Count notifications before
        count_before = Notification.objects.filter(
            recipient=user,
            notification_type='organisme_changed'
        ).count()

        # Update user without changing organisme
        user.nom_role = "Nouveau Nom"
        user.save()

        # Check no notification was created
        count_after = Notification.objects.filter(
            recipient=user,
            notification_type='organisme_changed'
        ).count()

        assert count_after == count_before

    def test_notification_when_organisme_set_to_none(self):
        """Test notification is created when organisme is removed."""
        org = OrganismeFactory(nom_organisme="Mon Organisme")
        user = RoleFactory(id_organisme=org)

        # Remove organisme
        user.id_organisme = None
        user.save()

        # Check notification was created
        notification = Notification.objects.filter(
            recipient=user,
            notification_type='organisme_changed'
        ).order_by('-created_at').first()

        assert notification is not None
        assert "Mon Organisme" in notification.message
        assert "Aucun" in notification.message

    def test_notification_when_organisme_set_from_none(self):
        """Test notification is created when organisme is set from None."""
        org = OrganismeFactory(nom_organisme="Nouvel Organisme")
        user = RoleFactory(id_organisme=None)

        # Set organisme
        user.id_organisme = org
        user.save()

        # Check notification was created
        notification = Notification.objects.filter(
            recipient=user,
            notification_type='organisme_changed'
        ).order_by('-created_at').first()

        assert notification is not None
        assert "Aucun" in notification.message
        assert "Nouvel Organisme" in notification.message

    def test_no_notification_on_user_creation(self):
        """Test no organisme_changed notification on new user creation."""
        org = OrganismeFactory()

        # Create new user with organisme
        user = RoleFactory(id_organisme=org)

        # Should not have organisme_changed notification (only for updates)
        notification = Notification.objects.filter(
            recipient=user,
            notification_type='organisme_changed'
        ).first()

        assert notification is None
