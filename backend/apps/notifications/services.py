"""
Services metier pour les notifications et validations.
"""
from django.db.models import Q
from django.utils import timezone

from apps.users.models import Role, BibOrganismes, Site, CorRoleSite, CorOgSite


class NotificationService:
    """Service pour la gestion des notifications."""

    @staticmethod
    def create_notification(
        recipient,
        notification_type,
        title,
        message,
        priority='medium',
        related_user=None,
        related_site=None,
        related_plan=None,
        related_organisme=None,
        related_validation=None,
        action_url=None,
        send_email=False
    ):
        """
        Cree une nouvelle notification.

        Args:
            recipient: Role destinataire
            notification_type: Type de notification
            title: Titre
            message: Message
            priority: Priorite (low, medium, high, critical)
            related_*: Objets lies optionnels
            action_url: URL d'action frontend
            send_email: Envoyer un email en plus

        Returns:
            Notification creee
        """
        from .models import Notification

        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            priority=priority,
            related_user=related_user,
            related_site=related_site,
            related_plan=related_plan,
            related_organisme=related_organisme,
            related_validation=related_validation,
            action_url=action_url,
        )

        # Envoyer email si demande et priorite haute/critique
        if send_email or priority in ['high', 'critical']:
            try:
                from .tasks import send_notification_email
                send_notification_email.delay(notification.id)
            except Exception as e:
                # Celery non disponible - log et continue sans bloquer
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Impossible d'envoyer l'email (Celery indisponible): {e}")

        return notification

    @staticmethod
    def notify_validators(validation_request):
        """
        Notifie tous les validateurs potentiels d'une nouvelle demande.

        Args:
            validation_request: ValidationRequest
        """
        validators = ValidationService.get_validators_for_request(validation_request)

        for validator in validators:
            NotificationService.create_notification(
                recipient=validator,
                notification_type='validation_request',
                title=f"Nouvelle demande: {validation_request.get_request_type_display()}",
                message=NotificationService._build_validation_message(validation_request),
                priority='high',
                related_validation=validation_request,
                action_url=f"/administration/validations?open={validation_request.id}",
                send_email=True
            )

    @staticmethod
    def _build_validation_message(validation_request):
        """Construit le message de notification pour une demande de validation."""
        requester_name = str(validation_request.requester) if validation_request.requester else "Nouvel utilisateur"

        if validation_request.request_type == 'user_registration':
            pending_user = getattr(validation_request, 'pending_user', None)
            if pending_user:
                return f"{pending_user.get_full_name()} ({pending_user.email}) demande a s'inscrire."
            return "Une nouvelle demande d'inscription est en attente."

        elif validation_request.request_type == 'site_access':
            site_name = validation_request.target_site.nom_site if validation_request.target_site else "un site"
            return f"{requester_name} demande l'acces au site {site_name}."

        elif validation_request.request_type == 'plan_access':
            plan_name = validation_request.target_plan.nom if validation_request.target_plan else "un plan"
            return f"{requester_name} demande l'acces au plan de gestion {plan_name}."

        elif validation_request.request_type == 'admin_deactivation':
            target_name = str(validation_request.target_user) if validation_request.target_user else "un administrateur"
            return f"{requester_name} demande la désactivation de {target_name}."

        elif validation_request.request_type == 'admin_promotion':
            target_name = str(validation_request.target_user) if validation_request.target_user else "un utilisateur"
            return f"{requester_name} demande la promotion de {target_name} en administrateur."

        elif validation_request.request_type == 'admin_demotion':
            target_name = str(validation_request.target_user) if validation_request.target_user else "un administrateur"
            return f"{requester_name} demande la retrogradation de {target_name} en utilisateur simple."

        elif validation_request.request_type == 'site_org_link':
            site_name = validation_request.target_site.nom_site if validation_request.target_site else "un site"
            org_name = validation_request.requested_organisme.nom_organisme if validation_request.requested_organisme else "l'organisme"
            return f"{requester_name} demande a lier le site {site_name} a {org_name}."

        elif validation_request.request_type == 'site_org_unlink':
            site_name = validation_request.target_site.nom_site if validation_request.target_site else "un site"
            org_name = validation_request.requested_organisme.nom_organisme if validation_request.requested_organisme else "l'organisme"
            return f"{requester_name} demande a retirer {org_name} du site {site_name}."

        elif validation_request.request_type == 'site_creation':
            site_name = validation_request.target_site.nom_site if validation_request.target_site else "un nouveau site"
            return f"{requester_name} a cree le site {site_name} et demande sa validation."

        elif validation_request.request_type == 'referent_validation':
            site_name = validation_request.target_site.nom_site if validation_request.target_site else "un site"
            return f"{requester_name} demande a devenir referent du site {site_name}."

        elif validation_request.request_type == 'invite_org_to_site':
            site_name = validation_request.target_site.nom_site if validation_request.target_site else "un site"
            org_name = validation_request.requested_organisme.nom_organisme if validation_request.requested_organisme else "votre organisme"
            return f"{requester_name} invite {org_name} a rejoindre le site {site_name}."

        elif validation_request.request_type == 'invite_user_to_site':
            site_name = validation_request.target_site.nom_site if validation_request.target_site else "un site"
            target_user_name = str(validation_request.target_user) if validation_request.target_user else "un utilisateur"
            return f"{requester_name} invite {target_user_name} a rejoindre le site {site_name}."

        elif validation_request.request_type == 'plan_site_link':
            plan_name = validation_request.target_plan.nom if validation_request.target_plan else "un plan"
            site_name = validation_request.target_site.nom_site if validation_request.target_site else "un site"
            return f"{requester_name} demande a lier le site {site_name} au plan de gestion {plan_name}."

        return f"Nouvelle demande de {requester_name}."

    @staticmethod
    def notify_validation_result(validation_request, approved=True):
        """
        Notifie le demandeur du resultat de sa demande.

        Args:
            validation_request: ValidationRequest
            approved: True si approuve, False si rejete
        """
        if not validation_request.requester:
            # Pour les inscriptions, pas de destinataire Role
            return

        notification_type = 'validation_approved' if approved else 'validation_rejected'
        title = "Demande approuvée" if approved else "Demande rejetée"

        if approved:
            message = f"Votre demande de {validation_request.get_request_type_display().lower()} a été approuvée."
        else:
            message = f"Votre demande de {validation_request.get_request_type_display().lower()} a été rejetée."
            if validation_request.validation_comment:
                message += f" Motif : {validation_request.validation_comment}"

        NotificationService.create_notification(
            recipient=validation_request.requester,
            notification_type=notification_type,
            title=title,
            message=message,
            priority='high',
            related_validation=validation_request,
            send_email=True
        )

    @staticmethod
    def notify_other_validators(validation_request, processed_by, approved=True):
        """
        Notifie les autres validateurs qu'une demande a ete traitee par quelqu'un d'autre.

        Args:
            validation_request: ValidationRequest traitee
            processed_by: Role qui a traite la demande
            approved: True si approuvee, False si rejetee
        """
        from .models import Notification

        # Obtenir tous les validateurs potentiels
        validators = ValidationService.get_validators_for_request(validation_request)

        # Exclure celui qui a traite la demande ET le demandeur (deja notifie via notify_validation_result)
        requester_id = validation_request.requester.id_role if validation_request.requester else None
        other_validators = [
            v for v in validators
            if v.id_role != processed_by.id_role and v.id_role != requester_id
        ]

        if not other_validators:
            return

        processor_name = f"{processed_by.prenom_role or ''} {processed_by.nom_role or ''}".strip() or processed_by.email
        status_text = "approuvée" if approved else "rejetée"
        request_type_display = validation_request.get_request_type_display().lower()

        # Construire le message avec details du demandeur
        if validation_request.request_type == 'user_registration':
            pending_user = getattr(validation_request, 'pending_user', None)
            if pending_user:
                requester_info = f"{pending_user.get_full_name()} ({pending_user.email})"
            else:
                # Si approuvée, PendingUser a été supprimé, chercher dans le message original
                requester_info = "un nouvel utilisateur"
        elif validation_request.requester:
            requester_info = str(validation_request.requester)
        else:
            requester_info = "un utilisateur"

        title = f"Demande déjà {status_text}"
        message = (
            f"La demande de {request_type_display} de {requester_info} "
            f"a été {status_text} par {processor_name}."
        )

        for validator in other_validators:
            # Marquer les anciennes notifications de cette validation comme lues
            Notification.objects.filter(
                recipient=validator,
                related_validation=validation_request,
                notification_type='validation_request',
                read=False
            ).update(read=True)

            # Creer une notification informative
            NotificationService.create_notification(
                recipient=validator,
                notification_type='info',
                title=title,
                message=message,
                priority='low',
                related_validation=validation_request,
                related_user=processed_by,
                send_email=False  # Pas besoin d'email pour cette info
            )

    @staticmethod
    def _notify_other_validators_registration(validation_request, processed_by, requester_info, approved=True):
        """
        Notifie les autres validateurs pour une inscription (cas special car PendingUser est supprime).

        Args:
            validation_request: ValidationRequest traitee
            processed_by: Role qui a traite la demande
            requester_info: String avec les infos du demandeur (sauvegarde avant suppression)
            approved: True si approuvee, False si rejetee
        """
        from .models import Notification

        # Obtenir tous les validateurs potentiels
        validators = ValidationService.get_validators_for_request(validation_request)

        # Exclure celui qui a traite la demande
        other_validators = [v for v in validators if v.id_role != processed_by.id_role]

        if not other_validators:
            return

        processor_name = f"{processed_by.prenom_role or ''} {processed_by.nom_role or ''}".strip() or processed_by.email
        status_text = "approuvée" if approved else "rejetée"

        title = f"Demande déjà {status_text}"
        message = (
            f"La demande d'inscription de {requester_info} "
            f"a été {status_text} par {processor_name}."
        )

        for validator in other_validators:
            # Marquer les anciennes notifications de cette validation comme lues
            Notification.objects.filter(
                recipient=validator,
                related_validation=validation_request,
                notification_type='validation_request',
                read=False
            ).update(read=True)

            # Creer une notification informative
            NotificationService.create_notification(
                recipient=validator,
                notification_type='info',
                title=title,
                message=message,
                priority='low',
                related_validation=validation_request,
                related_user=processed_by,
                send_email=False
            )

    @staticmethod
    def notify_super_admins(notification_type, title, message, **kwargs):
        """
        Notifie tous les super admins.

        Args:
            notification_type: Type de notification
            title: Titre
            message: Message
            **kwargs: Arguments additionnels pour create_notification
        """
        super_admins = Role.objects.filter(
            role_level='super_admin',
            active=True
        )

        for admin in super_admins:
            NotificationService.create_notification(
                recipient=admin,
                notification_type=notification_type,
                title=title,
                message=message,
                **kwargs
            )

    @staticmethod
    def notify_site_orphaned(site):
        """Notifie les admins qu'un site n'a plus d'utilisateurs."""
        title = f"Site orphelin: {site.nom_site}"
        message = f"Le site {site.nom_site} n'a plus aucun utilisateur associe."

        NotificationService.notify_super_admins(
            notification_type='site_orphaned',
            title=title,
            message=message,
            priority='high',
            related_site=site,
            action_url=f"/administration/sites/{site.id_site}",
            send_email=True
        )

        # Notifier aussi les admin_og des organismes gestionnaires
        for cor_og in CorOgSite.objects.filter(id_site=site):
            admin_ogs = Role.objects.filter(
                id_organisme=cor_og.uuid_og,
                role_level='admin_og',
                active=True
            )
            for admin in admin_ogs:
                NotificationService.create_notification(
                    recipient=admin,
                    notification_type='site_orphaned',
                    title=title,
                    message=message,
                    priority='high',
                    related_site=site,
                    action_url=f"/administration/sites/{site.id_site}",
                    send_email=True
                )

    @staticmethod
    def notify_organisme_no_admin(organisme):
        """Notifie les super admins qu'un organisme n'a plus d'admin_og."""
        title = f"Organisme sans administrateur: {organisme.nom_organisme}"
        message = f"L'organisme {organisme.nom_organisme} n'a plus d'administrateur (admin_og)."

        NotificationService.notify_super_admins(
            notification_type='organisme_no_admin',
            title=title,
            message=message,
            priority='critical',
            related_organisme=organisme,
            action_url=f"/administration/organismes/{organisme.id_organisme}",
            send_email=True
        )

    @staticmethod
    def notify_site_deleted(site_name, site_id, deleted_by, referent_ids, org_ids):
        """
        Notifie les acteurs liés lors de la suppression d'un site.

        - Référents du site (directs)
        - Admin_og des organismes liés
        - Super admins

        Args:
            site_name: Nom du site supprimé
            site_id: ID du site supprimé (pour référence, le site n'existe plus)
            deleted_by: Role qui a effectué la suppression
            referent_ids: Liste des IDs des référents du site
            org_ids: Liste des UUID des organismes liés
        """
        from apps.users.models import Role, BibOrganismes

        deleted_by_name = str(deleted_by) if deleted_by else "Système"
        title = f"Site supprimé : {site_name}"
        message = (
            f"Le site \"{site_name}\" a été supprimé par {deleted_by_name}. "
            "Les plans de gestion qui étaient liés à ce site restent conservés "
            "mais pourraient se retrouver sans site associé."
        )

        recipients = set()

        # Référents du site
        for uid in referent_ids:
            if uid != deleted_by.id_role:
                recipients.add(uid)

        # Admin_og des organismes liés
        admin_og_ids = Role.objects.filter(
            id_organisme__in=org_ids,
            role_level='admin_og',
            active=True,
        ).exclude(id_role=deleted_by.id_role).values_list('id_role', flat=True)
        recipients.update(admin_og_ids)

        # Super admins
        super_admin_ids = Role.objects.filter(
            role_level='super_admin',
            active=True,
        ).exclude(id_role=deleted_by.id_role).values_list('id_role', flat=True)
        recipients.update(super_admin_ids)

        # Envoi
        for uid in recipients:
            try:
                user = Role.objects.get(id_role=uid)
            except Role.DoesNotExist:
                continue
            NotificationService.create_notification(
                recipient=user,
                notification_type='site_deleted',
                title=title,
                message=message,
                priority='high',
                send_email=True,
            )

    @staticmethod
    def notify_plan_deleted(plan_name, plan_id, deleted_by, referent_ids, org_ids, member_ids=None):
        """
        Notifie les acteurs liés lors de la suppression d'un plan de gestion.

        - Référents du plan
        - Membres du plan (CorRolePlan)
        - Admin_og des organismes rédacteurs
        - Super admins

        Args:
            plan_name: Nom du plan supprimé
            plan_id: ID du plan supprimé (pour référence, le plan n'existe plus)
            deleted_by: Role qui a effectué la suppression
            referent_ids: Liste des IDs des référents du plan
            org_ids: Liste des UUID des organismes rédacteurs
            member_ids: Liste des IDs des membres CorRolePlan (optionnel)
        """
        from apps.users.models import Role

        deleted_by_name = str(deleted_by) if deleted_by else "Système"
        deleted_by_id = deleted_by.id_role if deleted_by else None
        title = f"Plan de gestion supprimé : {plan_name}"
        message = (
            f"Le plan de gestion \"{plan_name}\" a été supprimé par {deleted_by_name}. "
            "Toutes les données associées (sites liés, enjeux, opérations, fichiers) "
            "ont été retirées."
        )

        recipients = set()

        # Référents et membres du plan
        for uid in referent_ids or []:
            if uid != deleted_by_id:
                recipients.add(uid)
        for uid in member_ids or []:
            if uid != deleted_by_id:
                recipients.add(uid)

        # Admin_og des organismes rédacteurs
        if org_ids:
            admin_og_ids = Role.objects.filter(
                id_organisme__in=org_ids,
                role_level='admin_og',
                active=True,
            ).exclude(id_role=deleted_by_id).values_list('id_role', flat=True)
            recipients.update(admin_og_ids)

        # Super admins
        super_admin_ids = Role.objects.filter(
            role_level='super_admin',
            active=True,
        ).exclude(id_role=deleted_by_id).values_list('id_role', flat=True)
        recipients.update(super_admin_ids)

        # Envoi
        for uid in recipients:
            try:
                user = Role.objects.get(id_role=uid)
            except Role.DoesNotExist:
                continue
            NotificationService.create_notification(
                recipient=user,
                notification_type='plan_deleted',
                title=title,
                message=message,
                priority='high',
                send_email=True,
            )

    @staticmethod
    def notify_orphaned_sites_summary(sites):
        """
        Envoie un email recapitulatif unique pour tous les sites orphelins.
        Une seule notification + un seul email par destinataire.

        Args:
            sites: Liste de Site sans utilisateurs
        """
        import logging
        logger = logging.getLogger(__name__)

        count = len(sites)
        site_names = [s.nom_site for s in sites]
        sites_list_text = "\n".join(f"- {name}" for name in site_names)

        title = f"Audit hebdomadaire : {count} site(s) sans utilisateur"
        message = (
            f"{count} site(s) actif(s) n'ont aucun utilisateur associe :\n\n"
            f"{sites_list_text}"
        )

        # Une seule notification par super admin
        super_admins = Role.objects.filter(role_level='super_admin', active=True)
        for admin in super_admins:
            notification = NotificationService.create_notification(
                recipient=admin,
                notification_type='site_orphaned',
                title=title,
                message=message,
                priority='high',
                action_url="/administration/sites",
            )
            # Envoyer l'email recapitulatif
            NotificationService._send_audit_summary_email(
                recipient=admin,
                subject=title,
                intro=f"{count} site(s) actif(s) n'ont aucun utilisateur associe.",
                items=site_names,
                action_url="/administration/sites",
                action_label="Voir les sites",
            )

        # Notifier les admin_og concernes (regroupes par admin)
        admin_og_sites = {}
        for site in sites:
            for cor_og in CorOgSite.objects.filter(id_site=site):
                admin_ogs = Role.objects.filter(
                    id_organisme=cor_og.uuid_og,
                    role_level='admin_og',
                    active=True
                )
                for admin in admin_ogs:
                    admin_og_sites.setdefault(admin.pk, {
                        'admin': admin,
                        'sites': []
                    })['sites'].append(site.nom_site)

        for data in admin_og_sites.values():
            admin = data['admin']
            admin_site_names = data['sites']
            admin_count = len(admin_site_names)
            admin_title = f"Audit hebdomadaire : {admin_count} site(s) sans utilisateur"
            admin_message = (
                f"{admin_count} site(s) de votre organisme n'ont aucun utilisateur associe :\n\n"
                + "\n".join(f"- {name}" for name in admin_site_names)
            )
            NotificationService.create_notification(
                recipient=admin,
                notification_type='site_orphaned',
                title=admin_title,
                message=admin_message,
                priority='high',
                action_url="/administration/sites",
            )
            NotificationService._send_audit_summary_email(
                recipient=admin,
                subject=admin_title,
                intro=f"{admin_count} site(s) de votre organisme n'ont aucun utilisateur associe.",
                items=admin_site_names,
                action_url="/administration/sites",
                action_label="Voir les sites",
            )

        logger.info(f"Orphaned sites summary sent: {count} sites")

    @staticmethod
    def notify_orphaned_plans_summary(plans):
        """
        Envoie un email recapitulatif unique pour tous les plans orphelins
        (plans sans site associe suite a la suppression de leurs sites).

        Une seule notification + un seul email par super admin.

        Args:
            plans: Liste de PlanGestion sans site associe
        """
        from apps.users.models import Role

        count = len(plans)
        plan_names = [p.nom for p in plans]

        title = f"Audit hebdomadaire : {count} plan(s) de gestion sans site"
        intro = f"{count} plan(s) de gestion n'ont aucun site associe suite a la suppression de leurs sites."
        message = (
            f"{count} plan(s) de gestion orphelins :\n\n"
            + "\n".join(f"- {name}" for name in plan_names)
        )

        super_admins = Role.objects.filter(role_level='super_admin', active=True)
        for admin in super_admins:
            NotificationService.create_notification(
                recipient=admin,
                notification_type='plans_orphaned_summary',
                title=title,
                message=message,
                priority='high',
                action_url="/administration/plans",
            )
            NotificationService._send_audit_summary_email(
                recipient=admin,
                subject=title,
                intro=intro,
                items=plan_names,
                action_url="/administration/plans",
                action_label="Voir les plans",
            )

        logger.info(f"Orphaned plans summary sent: {count} plans")

    @staticmethod
    def notify_organismes_no_admin_summary(organismes):
        """
        Envoie un email recapitulatif unique pour tous les organismes sans admin.
        Une seule notification + un seul email par super admin.

        Args:
            organismes: Liste de BibOrganismes sans admin_og
        """
        import logging
        logger = logging.getLogger(__name__)

        count = len(organismes)
        org_names = [o.nom_organisme for o in organismes]

        title = f"Audit hebdomadaire : {count} organisme(s) sans administrateur"
        message = (
            f"{count} organisme(s) n'ont aucun administrateur actif :\n\n"
            + "\n".join(f"- {name}" for name in org_names)
        )

        super_admins = Role.objects.filter(role_level='super_admin', active=True)
        for admin in super_admins:
            NotificationService.create_notification(
                recipient=admin,
                notification_type='organisme_no_admin',
                title=title,
                message=message,
                priority='critical',
                action_url="/administration/organismes",
            )
            NotificationService._send_audit_summary_email(
                recipient=admin,
                subject=title,
                intro=f"{count} organisme(s) n'ont aucun administrateur actif.",
                items=org_names,
                action_url="/administration/organismes",
                action_label="Voir les organismes",
            )

        logger.info(f"Organismes without admin summary sent: {count} organismes")

    @staticmethod
    def _send_audit_summary_email(recipient, subject, intro, items, action_url, action_label):
        """
        Envoie un email recapitulatif d'audit.

        Args:
            recipient: Role destinataire
            subject: Sujet de l'email
            intro: Phrase d'introduction
            items: Liste de noms a afficher
            action_url: URL relative du bouton d'action
            action_label: Libelle du bouton d'action
        """
        from django.conf import settings
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.utils.html import strip_tags
        import logging
        logger = logging.getLogger(__name__)

        if not recipient.email:
            return

        site_url = getattr(settings, 'SITE_URL', 'http://localhost:4200')
        context = {
            'recipient': recipient,
            'intro': intro,
            'items': items,
            'item_count': len(items),
            'action_url': f"{site_url}{action_url}",
            'action_label': action_label,
            'site_url': site_url,
        }

        try:
            html_message = render_to_string('emails/audit_summary.html', context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            logger.warning(f"Failed to send audit summary email to {recipient.email}: {e}")

    @staticmethod
    def notify_plans_need_reassignment(site, organisme=None):
        """
        Notifie les admins que des plans liés à un site rejeté doivent être réassignés.

        Args:
            site: Le site qui a été rejeté/supprimé
            organisme: L'organisme concerné (optionnel, pour cibler les admin_og)
        """
        from apps.plans.models import CorSitePg, PlanGestion

        # Trouver tous les plans liés à ce site
        plans_linked = PlanGestion.objects.filter(sites__site=site).distinct()

        if not plans_linked.exists():
            return  # Pas de plans liés, rien à faire

        plan_count = plans_linked.count()
        plan_names = ", ".join([p.nom for p in plans_linked[:3]])
        if plan_count > 3:
            plan_names += f" et {plan_count - 3} autre(s)"

        title = f"Plans à réassigner: site {site.nom_site}"
        message = (
            f"Le site '{site.nom_site}' a été rejeté ou supprimé. "
            f"{plan_count} plan(s) de gestion doi(ven)t être réassigné(s) à un autre site: {plan_names}. "
            f"Un plan de gestion doit toujours être lié à au moins un site valide."
        )

        notified_users = set()

        # Notifier les admin_og de l'organisme concerné
        if organisme:
            admin_ogs = Role.objects.filter(
                id_organisme=organisme,
                role_level='admin_og',
                active=True
            )
            for admin in admin_ogs:
                if admin.id_role not in notified_users:
                    for plan in plans_linked:
                        NotificationService.create_notification(
                            recipient=admin,
                            notification_type='plan_needs_reassignment',
                            title=title,
                            message=message,
                            priority='high',
                            related_site=site,
                            related_plan=plan,
                            action_url=f"/plans/{plan.id_pg}",
                            send_email=True
                        )
                    notified_users.add(admin.id_role)

        # Notifier aussi les référents des plans concernés
        for plan in plans_linked:
            for referent in plan.referents.filter(active=True):
                if referent.id_role not in notified_users:
                    NotificationService.create_notification(
                        recipient=referent,
                        notification_type='plan_needs_reassignment',
                        title=title,
                        message=message,
                        priority='high',
                        related_site=site,
                        related_plan=plan,
                        action_url=f"/plans/{plan.id_pg}",
                        send_email=True
                    )
                    notified_users.add(referent.id_role)

        # Notifier les super admins
        NotificationService.notify_super_admins(
            notification_type='plan_needs_reassignment',
            title=title,
            message=message,
            priority='high',
            related_site=site,
            action_url=f"/administration/plans?site_invalide={site.id_site}",
            send_email=True
        )

    @staticmethod
    def notify_site_invitation_done(site, inviter, invited_organisme=None, invited_user=None):
        """
        Notifie les parties prenantes qu'un referent a directement ajoute
        un organisme ou un utilisateur a un site (sans demande de validation).

        Args:
            site: Le site concerne
            inviter: Role qui a fait l'invitation (referent)
            invited_organisme: BibOrganismes invite (si invitation d'organisme)
            invited_user: Role de l'utilisateur invite (si invitation d'utilisateur)
        """
        inviter_name = inviter.get_full_name() or inviter.email

        if invited_organisme:
            title = f"Organisme ajoute au site {site.nom_site}"
            message = f"{inviter_name} a ajoute l'organisme {invited_organisme.nom_organisme} au site {site.nom_site}."
        else:
            invited_user_name = invited_user.get_full_name() or invited_user.email if invited_user else "un utilisateur"
            title = f"Utilisateur ajoute au site {site.nom_site}"
            message = f"{inviter_name} a ajoute {invited_user_name} au site {site.nom_site}."

        notified_ids = set()
        # Ne pas notifier l'inviter lui-meme
        notified_ids.add(inviter.id_role)

        # 1. Admin_og de l'organisme de l'inviter
        if inviter.id_organisme:
            admin_ogs = Role.objects.filter(
                id_organisme=inviter.id_organisme,
                role_level='admin_og',
                active=True
            )
            for admin in admin_ogs:
                if admin.id_role not in notified_ids:
                    NotificationService.create_notification(
                        recipient=admin,
                        notification_type='info',
                        title=title,
                        message=message,
                        priority='medium',
                        related_site=site,
                        action_url=f'/sites/{site.id_site}',
                    )
                    notified_ids.add(admin.id_role)

        # 2. Admin_og de l'organisme invite (pour organisme) ou de l'utilisateur invite (pour user)
        if invited_organisme:
            admin_ogs = Role.objects.filter(
                id_organisme=invited_organisme,
                role_level='admin_og',
                active=True
            )
            for admin in admin_ogs:
                if admin.id_role not in notified_ids:
                    NotificationService.create_notification(
                        recipient=admin,
                        notification_type='info',
                        title=title,
                        message=message,
                        priority='medium',
                        related_site=site,
                        action_url=f'/sites/{site.id_site}',
                    )
                    notified_ids.add(admin.id_role)
        elif invited_user and invited_user.id_organisme:
            admin_ogs = Role.objects.filter(
                id_organisme=invited_user.id_organisme,
                role_level='admin_og',
                active=True
            )
            for admin in admin_ogs:
                if admin.id_role not in notified_ids:
                    NotificationService.create_notification(
                        recipient=admin,
                        notification_type='info',
                        title=title,
                        message=message,
                        priority='medium',
                        related_site=site,
                        action_url=f'/sites/{site.id_site}',
                    )
                    notified_ids.add(admin.id_role)

        # 3. Referents du site (sauf l'inviter)
        referent_roles = CorRoleSite.objects.filter(
            id_site=site,
            referent=True,
            referent_valid=True
        ).values_list('id_role', flat=True)
        for referent in Role.objects.filter(id_role__in=referent_roles, active=True):
            if referent.id_role not in notified_ids:
                NotificationService.create_notification(
                    recipient=referent,
                    notification_type='info',
                    title=title,
                    message=message,
                    priority='medium',
                    related_site=site,
                    action_url=f'/sites/{site.id_site}',
                )
                notified_ids.add(referent.id_role)

        # 4. Super admins
        super_admins = Role.objects.filter(
            role_level='super_admin',
            active=True
        )
        for admin in super_admins:
            if admin.id_role not in notified_ids:
                NotificationService.create_notification(
                    recipient=admin,
                    notification_type='info',
                    title=title,
                    message=message,
                    priority='low',
                    related_site=site,
                    action_url=f'/sites/{site.id_site}',
                )
                notified_ids.add(admin.id_role)

        # 5. L'utilisateur invite lui-meme (si invitation d'utilisateur)
        # Note: Pour les utilisateurs, le signal post_save de CorRoleSite
        # cree deja une notification user_associated_site automatiquement.
        # On ne cree donc pas de doublon ici.

    @staticmethod
    def notify_user_deactivated(user, deactivated_by, reason=None):
        """Notifie de la desactivation d'un compte."""
        # Notifier l'utilisateur desactive
        title = "Votre compte a ete desactive"
        message = "Votre compte a ete desactive par un administrateur."
        if reason:
            message += f" Motif: {reason}"

        NotificationService.create_notification(
            recipient=user,
            notification_type='account_deactivated',
            title=title,
            message=message,
            priority='critical',
            related_user=deactivated_by,
            send_email=True
        )

        # Notifier les super admins
        NotificationService.notify_super_admins(
            notification_type='account_deactivated',
            title=f"Compte desactive: {user}",
            message=f"Le compte de {user} a ete desactive par {deactivated_by}.",
            priority='high',
            related_user=user,
            send_email=True
        )


class ValidationService:
    """Service pour la gestion des validations."""

    @staticmethod
    def get_validators_for_request(validation_request):
        """
        Determine les utilisateurs qui peuvent valider une demande.

        Args:
            validation_request: ValidationRequest

        Returns:
            QuerySet de Role pouvant valider
        """
        validators = set()

        if validation_request.request_type == 'user_registration':
            validators = ValidationService._get_registration_validators(validation_request)

        elif validation_request.request_type == 'site_access':
            validators = ValidationService._get_site_access_validators(validation_request)

        elif validation_request.request_type == 'plan_access':
            validators = ValidationService._get_plan_access_validators(validation_request)

        elif validation_request.request_type == 'admin_deactivation':
            # Seuls les super_admin peuvent valider
            validators = set(Role.objects.filter(
                role_level='super_admin',
                active=True
            ))

        elif validation_request.request_type == 'admin_promotion':
            # Seuls les super_admin peuvent valider
            validators = set(Role.objects.filter(
                role_level='super_admin',
                active=True
            ))

        elif validation_request.request_type == 'admin_demotion':
            # Seuls les super_admin peuvent valider
            validators = set(Role.objects.filter(
                role_level='super_admin',
                active=True
            ))

        elif validation_request.request_type == 'referent_validation':
            validators = ValidationService._get_site_access_validators(validation_request)

        elif validation_request.request_type == 'site_creation':
            validators = ValidationService._get_site_creation_validators(validation_request)

        elif validation_request.request_type == 'site_org_link':
            # Validateurs: admin_og de l'organisme demandeur
            validators = ValidationService._get_org_link_validators(validation_request)

        elif validation_request.request_type == 'site_org_unlink':
            # Validateurs: admin_og de l'organisme a retirer
            validators = ValidationService._get_org_unlink_validators(validation_request)

        elif validation_request.request_type == 'invite_org_to_site':
            # Validateurs: admin_og de l'organisme invite
            validators = ValidationService._get_invite_org_validators(validation_request)

        elif validation_request.request_type == 'invite_user_to_site':
            # Validateurs: admin_og de l'organisme de l'utilisateur invite
            validators = ValidationService._get_invite_user_validators(validation_request)

        elif validation_request.request_type == 'plan_site_link':
            # Validateurs: referents du site + admin_og des organismes du site
            validators = ValidationService._get_plan_site_link_validators(validation_request)

        # Fallback: si aucun validateur trouve, super_admin
        if not validators:
            validators = set(Role.objects.filter(
                role_level='super_admin',
                active=True
            ))

        return validators

    @staticmethod
    def _get_registration_validators(validation_request):
        """Validateurs pour une inscription."""
        validators = set()

        if validation_request.requested_organisme:
            # admin_og de l'organisme demande
            admin_ogs = Role.objects.filter(
                id_organisme=validation_request.requested_organisme,
                role_level='admin_og',
                active=True
            )
            validators.update(admin_ogs)

        # Si pas d'admin_og, super_admin
        if not validators:
            validators.update(Role.objects.filter(
                role_level='super_admin',
                active=True
            ))

        return validators

    @staticmethod
    def _get_org_link_validators(validation_request):
        """Validateurs pour un lien site-organisme."""
        validators = set()

        # Valide par l'admin_og de l'organisme demandeur
        if validation_request.requested_organisme:
            admin_ogs = Role.objects.filter(
                id_organisme=validation_request.requested_organisme,
                role_level='admin_og',
                active=True
            )
            validators.update(admin_ogs)

        # Toujours notifier les super_admins
        validators.update(Role.objects.filter(
            role_level='super_admin',
            active=True
        ))

        return validators

    @staticmethod
    def _get_org_unlink_validators(validation_request):
        """
        Validateurs pour un retrait site-organisme.
        Valide par l'admin_og de l'organisme a retirer.
        """
        validators = set()

        # L'organisme a retirer est dans requested_organisme
        if validation_request.requested_organisme:
            admin_ogs = Role.objects.filter(
                id_organisme=validation_request.requested_organisme,
                role_level='admin_og',
                active=True
            )
            validators.update(admin_ogs)

        # Si pas d'admin_og, super_admin
        if not validators:
            validators.update(Role.objects.filter(
                role_level='super_admin',
                active=True
            ))

        return validators

    @staticmethod
    def _get_invite_org_validators(validation_request):
        """
        Validateurs pour une invitation d'organisme vers un site.
        Valide par l'admin_og de l'organisme invite.
        """
        validators = set()

        # L'organisme invite est dans requested_organisme
        if validation_request.requested_organisme:
            admin_ogs = Role.objects.filter(
                id_organisme=validation_request.requested_organisme,
                role_level='admin_og',
                active=True
            )
            validators.update(admin_ogs)

        # Si pas d'admin_og, super_admin
        if not validators:
            validators.update(Role.objects.filter(
                role_level='super_admin',
                active=True
            ))

        return validators

    @staticmethod
    def _get_invite_user_validators(validation_request):
        """
        Validateurs pour une invitation d'utilisateur vers un site.
        Valide par l'admin_og de l'organisme de l'utilisateur invite.
        """
        validators = set()

        # L'utilisateur invite est dans target_user
        if validation_request.target_user and validation_request.target_user.id_organisme:
            admin_ogs = Role.objects.filter(
                id_organisme=validation_request.target_user.id_organisme,
                role_level='admin_og',
                active=True
            )
            validators.update(admin_ogs)

        # Si pas d'admin_og, super_admin
        if not validators:
            validators.update(Role.objects.filter(
                role_level='super_admin',
                active=True
            ))

        return validators

    @staticmethod
    def _get_plan_site_link_validators(validation_request):
        """
        Validateurs pour un lien plan-site.

        Deux cas:
        - Si le demandeur est referent du plan: valide par les referents du site
          + admin_og des organismes du site (le plan est ok, il faut l'accord du site)
        - Si le demandeur est simple membre du plan: valide par les referents du plan
          + super_admin (il faut l'accord du plan)
        """
        validators = set()
        plan = validation_request.target_plan
        site = validation_request.target_site
        requester = validation_request.requester

        # Verifier si le demandeur est referent du plan
        is_plan_referent = plan and plan.referents.filter(pk=requester.pk).exists() if requester else False

        if is_plan_referent:
            # Referent du plan → besoin de l'accord du site
            if site:
                referent_roles = CorRoleSite.objects.filter(
                    id_site=site,
                    referent=True,
                    referent_valid=True
                ).values_list('id_role', flat=True)
                validators.update(Role.objects.filter(
                    id_role__in=referent_roles,
                    active=True
                ))

                for cor_og in CorOgSite.objects.filter(id_site=site):
                    admin_ogs = Role.objects.filter(
                        id_organisme=cor_og.uuid_og,
                        role_level='admin_og',
                        active=True
                    )
                    validators.update(admin_ogs)
        else:
            # Simple membre du plan → besoin de l'accord du plan
            if plan:
                validators.update(plan.referents.filter(active=True))

        return validators

    @staticmethod
    def _get_site_creation_validators(validation_request):
        """
        Validateurs pour une creation de site.
        Valide par l'admin_og de l'organisme du createur + super_admin.
        """
        validators = set()

        # Admin_og de l'organisme du createur
        if validation_request.requester and validation_request.requester.id_organisme:
            admin_ogs = Role.objects.filter(
                id_organisme=validation_request.requester.id_organisme,
                role_level='admin_og',
                active=True
            )
            validators.update(admin_ogs)

        # Toujours ajouter les super_admin (ils peuvent valider aussi)
        validators.update(Role.objects.filter(
            role_level='super_admin',
            active=True
        ))

        return validators

    @staticmethod
    def _get_site_access_validators(validation_request):
        """Validateurs pour un acces site."""
        validators = set()
        site = validation_request.target_site

        if not site:
            return validators

        # Referents valides du site
        referent_roles = CorRoleSite.objects.filter(
            id_site=site,
            referent=True,
            referent_valid=True
        ).values_list('id_role', flat=True)
        validators.update(Role.objects.filter(
            id_role__in=referent_roles,
            active=True
        ))

        # admin_og des organismes gestionnaires du site
        for cor_og in CorOgSite.objects.filter(id_site=site):
            admin_ogs = Role.objects.filter(
                id_organisme=cor_og.uuid_og,
                role_level='admin_og',
                active=True
            )
            validators.update(admin_ogs)

        return validators

    @staticmethod
    def _get_plan_access_validators(validation_request):
        """Validateurs pour un acces plan."""
        validators = set()
        plan = validation_request.target_plan

        if not plan:
            return validators

        # Referents du plan
        validators.update(plan.referents.filter(active=True))

        # Referents des sites du plan
        for cor_site_pg in plan.sites.all():
            site = cor_site_pg.site
            referent_roles = CorRoleSite.objects.filter(
                id_site=site,
                referent=True,
                referent_valid=True
            ).values_list('id_role', flat=True)
            validators.update(Role.objects.filter(
                id_role__in=referent_roles,
                active=True
            ))

            # admin_og des organismes gestionnaires
            for cor_og in CorOgSite.objects.filter(id_site=site):
                admin_ogs = Role.objects.filter(
                    id_organisme=cor_og.uuid_og,
                    role_level='admin_og',
                    active=True
                )
                validators.update(admin_ogs)

        return validators

    @staticmethod
    def can_validate_request(user, validation_request):
        """
        Verifie si un utilisateur peut valider une demande.

        Args:
            user: Role
            validation_request: ValidationRequest

        Returns:
            bool
        """
        # Super admin peut tout valider
        if user.is_super_admin():
            return True

        validators = ValidationService.get_validators_for_request(validation_request)
        return user in validators

    @staticmethod
    def get_pending_requests_for_user(user):
        """
        Retourne les demandes en attente qu'un utilisateur peut valider.

        Args:
            user: Role

        Returns:
            QuerySet de ValidationRequest
        """
        from .models import ValidationRequest

        pending = ValidationRequest.objects.filter(status='pending')

        if user.is_super_admin():
            return pending

        # Filtrer selon le role
        result_ids = []
        for request in pending:
            if ValidationService.can_validate_request(user, request):
                result_ids.append(request.id)

        return ValidationRequest.objects.filter(id__in=result_ids)

    @staticmethod
    def get_all_requests_for_user(user):
        """
        Retourne toutes les demandes qu'un utilisateur peut voir (en attente ou traitees).

        Inclut:
        - Les demandes en attente que l'utilisateur peut valider
        - Les demandes que l'utilisateur a validees
        - Les demandes liees a l'organisme de l'utilisateur (si admin_og)

        Args:
            user: Role

        Returns:
            QuerySet de ValidationRequest
        """
        from .models import ValidationRequest
        from django.db.models import Q

        if user.is_super_admin():
            return ValidationRequest.objects.all()

        result_ids = set()

        # 1. Demandes que l'utilisateur a validees
        validated_by_user = ValidationRequest.objects.filter(validator=user)
        result_ids.update(validated_by_user.values_list('id', flat=True))

        # 2. Pour admin_og: toutes les demandes liees a son organisme
        if user.role_level == 'admin_og' and user.id_organisme:
            org_requests = ValidationRequest.objects.filter(
                requested_organisme=user.id_organisme
            )
            result_ids.update(org_requests.values_list('id', flat=True))

        # 3. Demandes en attente que l'utilisateur peut encore valider
        pending = ValidationRequest.objects.filter(status='pending')
        for request in pending:
            if ValidationService.can_validate_request(user, request):
                result_ids.add(request.id)

        return ValidationRequest.objects.filter(id__in=result_ids)

    @staticmethod
    def approve_registration(validation_request, validator, comment=None, organisme_override=None):
        """
        Approuve une inscription et cree le compte utilisateur.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve
            comment: Commentaire optionnel
            organisme_override: BibOrganismes a utiliser si la demande n'en a pas
                (cas ou l'organisme initial a ete supprime entre temps)

        Returns:
            Role cree
        """
        from django.contrib.auth.hashers import check_password
        from apps.users.models import BibOrganismes

        if validation_request.request_type != 'user_registration':
            raise ValueError("Cette demande n'est pas une inscription")

        if not hasattr(validation_request, 'pending_user'):
            raise ValueError("Pas de donnees d'inscription trouvees")

        pending = validation_request.pending_user

        # Determiner l'organisme final (pending OU override fourni par l'admin)
        final_organisme = pending.requested_organisme or organisme_override
        if final_organisme is None:
            raise ValueError(
                "Cette demande d'inscription n'a pas d'organisme associe "
                "(probablement supprime depuis). Veuillez fournir 'organisme_id_override' "
                "pour attribuer manuellement un organisme."
            )

        # Sauvegarder les infos du demandeur avant suppression (pour notifier les autres validateurs)
        requester_info_for_notification = f"{pending.get_full_name()} ({pending.email})"

        # Verifier si un utilisateur avec cet email existe deja
        existing_user = Role.objects.filter(email__iexact=pending.email).first()
        if existing_user:
            # L'utilisateur existe deja - peut arriver si seed_testdata est relance apres une approbation
            # Si l'utilisateur existant n'a pas d'organisme, on lui attribue celui de la demande
            if not existing_user.id_organisme:
                existing_user.id_organisme = final_organisme
                existing_user.save(update_fields=['id_organisme'])
            # Lier la ValidationRequest a l'utilisateur existant pour conserver la reference
            validation_request.requester = existing_user
            validation_request.approve(validator, comment)
            pending.delete()

            # Notifier les autres validateurs que la demande a ete traitee
            NotificationService._notify_other_validators_registration(
                validation_request, validator, requester_info_for_notification, approved=True
            )

            # Retourner l'utilisateur existant (le compte existait deja)
            return existing_user

        # Creer le Role
        user = Role.objects.create(
            email=pending.email,
            identifiant=pending.identifiant,
            nom_role=pending.nom_role,
            prenom_role=pending.prenom_role,
            id_organisme=final_organisme,
            role_level='utilisateur',
            active=True,
            pending_validation=False,
        )
        # Le mot de passe est deja hashe
        user.password = pending.password_hash
        user.save()

        # Lier la ValidationRequest au nouveau Role (Option B)
        # Ceci permet d'acceder au nom du demandeur via validation_request.requester
        validation_request.requester = user

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Supprimer PendingUser (les donnees sont maintenant dans Role)
        pending.delete()

        # Construire le message de bienvenue detaille
        validator_name = f"{validator.prenom_role or ''} {validator.nom_role or ''}".strip() or validator.email
        organisme_info = ""
        if user.id_organisme:
            organisme_info = f" au sein de {user.id_organisme.nom_organisme}"

        # Notification de bienvenue
        NotificationService.create_notification(
            recipient=user,
            notification_type='welcome',
            title="Bienvenue sur la plateforme !",
            message=f"Votre compte a ete cree avec succes{organisme_info}. "
                    "Vous pouvez maintenant explorer l'application et acceder a vos espaces de travail.",
            priority='high',
            action_url='/accueil',
            send_email=True
        )

        # Notification d'approbation avec details
        NotificationService.create_notification(
            recipient=user,
            notification_type='validation_approved',
            title="Inscription approuvée",
            message=f"Votre demande d'inscription a été approuvée par {validator_name}.",
            priority='medium',
            related_user=validator,
            related_validation=validation_request,
        )

        # Notifier les autres validateurs que la demande a ete traitee
        # On passe les infos sauvegardees car PendingUser a ete supprime
        NotificationService._notify_other_validators_registration(
            validation_request, validator, requester_info_for_notification, approved=True
        )

        return user

    # ==================== Auto-approval helper ====================

    # Request types qui supportent l'auto-approbation par un role privilegie
    AUTO_APPROVABLE_TYPES = frozenset({
        'site_access',
        'referent_validation',
        'site_org_link',
        'site_org_unlink',
        'plan_site_link',
    })

    @staticmethod
    def _can_auto_approve(requester, validation_request):
        """
        Determine si le demandeur peut auto-approuver sa propre demande selon son role
        et le scope de l'organisme pour un admin_og.
        - super_admin / redacteur_principal : toujours
        - admin_og : uniquement si la demande concerne son organisme (scope check par type)
        - utilisateur : jamais
        """
        if validation_request.request_type not in ValidationService.AUTO_APPROVABLE_TYPES:
            return False

        if requester.is_super_admin() or requester.is_redacteur_principal():
            return True

        if not requester.is_admin_organisme():
            return False

        admin_org = requester.id_organisme
        if not admin_org:
            return False

        rtype = validation_request.request_type
        site = validation_request.target_site

        if rtype in ('site_access', 'referent_validation', 'plan_site_link'):
            # admin_og peut auto-approuver si son organisme est lie au site cible
            if not site:
                return False
            return CorOgSite.objects.filter(uuid_og=admin_org, id_site=site).exists()

        if rtype in ('site_org_link', 'site_org_unlink'):
            # admin_og peut auto-approuver si la liaison concerne son organisme
            return validation_request.requested_organisme_id == admin_org.id_organisme

        return False

    @staticmethod
    def try_auto_approve(validation_request, requester):
        """
        Auto-approuve la demande si le requester en a les droits.
        La demande reste dans la queue avec status='approved' et validator=requester.

        Returns:
            bool: True si auto-approuve, False sinon
        """
        if not ValidationService._can_auto_approve(requester, validation_request):
            return False

        rtype = validation_request.request_type
        if rtype == 'site_access':
            ValidationService.approve_site_access(validation_request, requester)
        elif rtype == 'referent_validation':
            ValidationService.approve_referent_validation(validation_request, requester)
        elif rtype == 'site_org_link':
            ValidationService.approve_site_org_link(validation_request, requester)
        elif rtype == 'site_org_unlink':
            ValidationService.approve_site_org_unlink(validation_request, requester)
        elif rtype == 'plan_site_link':
            ValidationService.approve_plan_site_link(validation_request, requester)
        else:
            return False
        return True

    @staticmethod
    def approve_site_access(validation_request, validator, comment=None, override_referent=None):
        """
        Approuve un acces site et cree la liaison.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve
            comment: Commentaire optionnel
            override_referent: Si defini, surcharge request_as_referent (bool)
        """
        if validation_request.request_type != 'site_access':
            raise ValueError("Cette demande n'est pas un acces site")

        # Determiner si l'utilisateur devient referent
        if override_referent is not None:
            is_referent = override_referent
        else:
            is_referent = validation_request.request_as_referent

        # Creer ou mettre a jour CorRoleSite
        CorRoleSite.objects.update_or_create(
            id_site=validation_request.target_site,
            id_role=validation_request.requester,
            defaults={
                'referent': is_referent,
                'referent_valid': is_referent,  # Valide automatiquement si approuve
                'conservateur': False,
            }
        )

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier le demandeur
        NotificationService.notify_validation_result(validation_request, approved=True)

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def approve_plan_access(validation_request, validator, comment=None):
        """
        Approuve un acces plan et cree la liaison membre (CorRolePlan).

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve
            comment: Commentaire optionnel
        """
        from apps.plans.models import PlanGestion, CorRolePlan

        if validation_request.request_type != 'plan_access':
            raise ValueError("Cette demande n'est pas un acces plan")

        plan = validation_request.target_plan
        requester = validation_request.requester
        is_referent = validation_request.request_as_referent

        # Creer CorRolePlan (membre ou referent selon la demande)
        cor, created = CorRolePlan.objects.get_or_create(
            id_role=requester,
            plan_de_gestion=plan,
            defaults={'referent': is_referent}
        )
        if not created and is_referent and not cor.referent:
            cor.referent = True
            cor.save(update_fields=['referent'])

        # Garder plan.referents M2M pour compatibilite (utilise dans get_queryset)
        if is_referent:
            plan.referents.add(requester)

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier le demandeur
        NotificationService.notify_validation_result(validation_request, approved=True)

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def approve_plan_site_link(validation_request, validator, comment=None):
        """
        Approuve un lien plan-site et cree la liaison CorSitePg.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve
            comment: Commentaire optionnel
        """
        from apps.plans.models import CorSitePg

        if validation_request.request_type != 'plan_site_link':
            raise ValueError("Cette demande n'est pas un lien plan-site")

        plan = validation_request.target_plan
        site = validation_request.target_site

        if not plan or not site:
            raise ValueError("Plan ou site manquant dans la demande")

        # Creer le lien plan-site
        CorSitePg.objects.get_or_create(
            site=site,
            plan_de_gestion=plan,
            defaults={'rang': 0}
        )

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier le demandeur
        NotificationService.notify_validation_result(validation_request, approved=True)

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

        # Notifier les referents du plan que le site a ete lie
        requester = validation_request.requester
        for referent in plan.referents.filter(active=True):
            # Ne pas notifier le validateur (il sait deja) ni le demandeur (notifie ci-dessus)
            if referent.pk == validator.pk or (requester and referent.pk == requester.pk):
                continue
            NotificationService.create_notification(
                recipient=referent,
                notification_type='info',
                title=f"Site lié au plan {plan.nom}",
                message=f"Le site {site.nom_site} a été lié au plan de gestion {plan.nom}.",
                priority='medium',
                related_plan=plan,
                related_site=site,
                action_url=f"/plans/{plan.slug or plan.id_pg}",
            )

    @staticmethod
    def approve_site_org_link(validation_request, validator, comment=None):
        """
        Approuve un lien site-organisme et cree la liaison.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve
            comment: Commentaire optionnel
        """
        if validation_request.request_type != 'site_org_link':
            raise ValueError("Cette demande n'est pas un lien site-organisme")

        # Creer le lien CorOgSite (non principal par defaut)
        CorOgSite.objects.get_or_create(
            id_site=validation_request.target_site,
            uuid_og=validation_request.requested_organisme,
            defaults={
                'principal': False,
            }
        )

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier le demandeur
        NotificationService.notify_validation_result(validation_request, approved=True)

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def approve_site_org_unlink(validation_request, validator, comment=None):
        """
        Approuve un retrait site-organisme et supprime la liaison.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve
            comment: Commentaire optionnel
        """
        if validation_request.request_type != 'site_org_unlink':
            raise ValueError("Cette demande n'est pas un retrait site-organisme")

        site = validation_request.target_site
        organisme = validation_request.requested_organisme

        if not site or not organisme:
            raise ValueError("Site ou organisme manquant")

        # Supprimer le lien CorOgSite
        try:
            cor_og_site = CorOgSite.objects.get(id_site=site, uuid_og=organisme)
            cor_og_site.delete()
        except CorOgSite.DoesNotExist:
            # Le lien n'existe plus, on continue quand meme
            pass

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier le demandeur
        NotificationService.notify_validation_result(validation_request, approved=True)

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def approve_referent_validation(validation_request, validator, comment=None):
        """
        Approuve une demande de devenir referent et met a jour la liaison.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve
            comment: Commentaire optionnel
        """
        if validation_request.request_type != 'referent_validation':
            raise ValueError("Cette demande n'est pas une demande de referent")

        site = validation_request.target_site
        requester = validation_request.requester

        if not site or not requester:
            raise ValueError("Site ou demandeur manquant")

        # Verifier que l'utilisateur est bien lie au site
        try:
            cor_role_site = CorRoleSite.objects.get(id_site=site, id_role=requester)
        except CorRoleSite.DoesNotExist:
            raise ValueError("L'utilisateur n'est pas lie a ce site")

        # Mettre a jour le statut referent
        cor_role_site.referent = True
        cor_role_site.referent_valid = True
        cor_role_site.save()

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier le demandeur
        NotificationService.notify_validation_result(validation_request, approved=True)

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def approve_invite_org_to_site(validation_request, validator, comment=None):
        """
        Approuve une invitation d'organisme vers un site et cree la liaison.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve
            comment: Commentaire optionnel
        """
        if validation_request.request_type != 'invite_org_to_site':
            raise ValueError("Cette demande n'est pas une invitation d'organisme")

        site = validation_request.target_site
        organisme = validation_request.requested_organisme

        if not site or not organisme:
            raise ValueError("Site ou organisme manquant")

        # Creer le lien CorOgSite (non principal par defaut)
        CorOgSite.objects.get_or_create(
            id_site=site,
            uuid_og=organisme,
            defaults={
                'principal': False,
            }
        )

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier le demandeur
        NotificationService.notify_validation_result(validation_request, approved=True)

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def approve_invite_user_to_site(validation_request, validator, comment=None):
        """
        Approuve une invitation d'utilisateur vers un site et cree la liaison.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve
            comment: Commentaire optionnel
        """
        if validation_request.request_type != 'invite_user_to_site':
            raise ValueError("Cette demande n'est pas une invitation d'utilisateur")

        site = validation_request.target_site
        user = validation_request.target_user

        if not site or not user:
            raise ValueError("Site ou utilisateur manquant")

        # Creer le lien CorRoleSite (non referent par defaut)
        # Note: Le signal post_save sur CorRoleSite notifiera automatiquement l'utilisateur
        CorRoleSite.objects.get_or_create(
            id_site=site,
            id_role=user,
            defaults={
                'referent': False,
                'referent_valid': False,
                'conservateur': False,
            }
        )

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier le demandeur (l'admin qui a cree l'invitation)
        NotificationService.notify_validation_result(validation_request, approved=True)

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def approve_site_creation(validation_request, validator, comment=None, override_referent=None):
        """
        Approuve une creation de site et active le site.
        Le createur devient referent ou simple utilisateur selon request_as_referent.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve
            comment: Commentaire optionnel
            override_referent: Si defini, surcharge request_as_referent (bool)
        """
        if validation_request.request_type != 'site_creation':
            raise ValueError("Cette demande n'est pas une creation de site")

        site = validation_request.target_site
        requester = validation_request.requester

        if not site or not requester:
            raise ValueError("Site ou createur manquant")

        # Determiner si l'utilisateur devient referent
        if override_referent is not None:
            is_referent = override_referent
        else:
            is_referent = validation_request.request_as_referent

        # Activer le site
        site.active = True
        site.save(update_fields=['active'])

        # Creer ou mettre a jour CorRoleSite avec le createur
        CorRoleSite.objects.update_or_create(
            id_site=site,
            id_role=requester,
            defaults={
                'referent': is_referent,
                'referent_valid': is_referent,
                'conservateur': False,
            }
        )

        # Lier l'organisme du createur au site si pas deja fait
        if requester.id_organisme:
            # Verifier si un organisme principal existe deja
            has_principal = CorOgSite.objects.filter(id_site=site, principal=True).exists()
            CorOgSite.objects.get_or_create(
                id_site=site,
                uuid_og=requester.id_organisme,
                defaults={
                    'principal': not has_principal,  # Premier organisme = principal
                }
            )

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier le createur
        if is_referent:
            message = f"Votre site \"{site.nom_site}\" a ete valide. Vous en etes maintenant le referent."
        else:
            message = f"Votre site \"{site.nom_site}\" a ete valide. Vous avez acces au site en tant qu'utilisateur."

        NotificationService.create_notification(
            recipient=requester,
            notification_type='validation_approved',
            title="Site valide",
            message=message,
            priority='high',
            related_site=site,
            action_url=f'/sites/{site.id_site}',
            send_email=True
        )

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def approve_admin_deactivation(validation_request, validator, comment=None):
        """
        Approuve une demande de desactivation d'admin_og et desactive l'utilisateur.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve (doit etre super_admin)
            comment: Commentaire optionnel
        """
        if validation_request.request_type != 'admin_deactivation':
            raise ValueError("Cette demande n'est pas une desactivation d'admin")

        target_user = validation_request.target_user
        if not target_user:
            raise ValueError("Utilisateur cible manquant")

        # Verifier que le validateur est super_admin
        if not validator.is_super_admin():
            raise ValueError("Seul un super administrateur peut approuver cette demande")

        # Desactiver l'utilisateur cible
        target_user.active = False
        target_user.save(update_fields=['active'])

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier l'utilisateur desactive
        NotificationService.create_notification(
            recipient=target_user,
            notification_type='account_deactivated',
            title="Votre compte a ete desactive",
            message=f"Suite a une demande de {validation_request.requester}, "
                    f"votre compte administrateur a ete desactive par un super administrateur.",
            priority='critical',
            related_user=validator,
            related_validation=validation_request,
            send_email=True
        )

        # Notifier le demandeur
        NotificationService.create_notification(
            recipient=validation_request.requester,
            notification_type='validation_approved',
            title="Demande de désactivation approuvée",
            message=f"Votre demande de désactivation de {target_user} a été approuvée.",
            priority='high',
            related_user=target_user,
            related_validation=validation_request,
            send_email=True
        )

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def approve_admin_promotion(validation_request, validator, comment=None):
        """
        Approuve une demande de promotion d'un utilisateur en admin_og.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve (doit etre super_admin)
            comment: Commentaire optionnel
        """
        if validation_request.request_type != 'admin_promotion':
            raise ValueError("Cette demande n'est pas une promotion admin_og")

        target_user = validation_request.target_user
        if not target_user:
            raise ValueError("Utilisateur cible manquant")

        # Verifier que le validateur est super_admin
        if not validator.is_super_admin():
            raise ValueError("Seul un super administrateur peut approuver cette demande")

        # Verifier que l'utilisateur est bien utilisateur simple
        if target_user.role_level != 'utilisateur':
            raise ValueError("Cet utilisateur n'est pas un utilisateur simple")

        # Promouvoir l'utilisateur en admin_og
        target_user.role_level = 'admin_og'
        target_user.save(update_fields=['role_level'])

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier l'utilisateur promu
        NotificationService.create_notification(
            recipient=target_user,
            notification_type='role_changed',
            title="Vous êtes maintenant administrateur",
            message=f"Suite à une demande de {validation_request.requester}, "
                    f"vous avez été promu administrateur de votre organisme.",
            priority='high',
            related_user=validator,
            related_validation=validation_request,
            send_email=True
        )

        # Notifier le demandeur
        NotificationService.create_notification(
            recipient=validation_request.requester,
            notification_type='validation_approved',
            title="Demande de promotion approuvée",
            message=f"Votre demande de promotion de {target_user} en administrateur a été approuvée.",
            priority='high',
            related_user=target_user,
            related_validation=validation_request,
            send_email=True
        )

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def approve_admin_demotion(validation_request, validator, comment=None):
        """
        Approuve une demande de retrogradation d'un admin_og en utilisateur simple.

        Args:
            validation_request: ValidationRequest
            validator: Role qui approuve (doit etre super_admin)
            comment: Commentaire optionnel
        """
        if validation_request.request_type != 'admin_demotion':
            raise ValueError("Cette demande n'est pas une retrogradation admin_og")

        target_user = validation_request.target_user
        if not target_user:
            raise ValueError("Utilisateur cible manquant")

        # Verifier que le validateur est super_admin
        if not validator.is_super_admin():
            raise ValueError("Seul un super administrateur peut approuver cette demande")

        # Verifier que l'utilisateur est bien admin_og
        if target_user.role_level != 'admin_og':
            raise ValueError("Cet utilisateur n'est pas un admin_og")

        # Retrograder l'utilisateur en utilisateur simple
        target_user.role_level = 'utilisateur'
        target_user.save(update_fields=['role_level'])

        # Approuver la demande
        validation_request.approve(validator, comment)

        # Notifier l'utilisateur retrograde
        NotificationService.create_notification(
            recipient=target_user,
            notification_type='role_changed',
            title="Changement de rôle",
            message=f"Suite à une demande de {validation_request.requester}, "
                    f"vous n'êtes plus administrateur de votre organisme.",
            priority='high',
            related_user=validator,
            related_validation=validation_request,
            send_email=True
        )

        # Notifier le demandeur
        NotificationService.create_notification(
            recipient=validation_request.requester,
            notification_type='validation_approved',
            title="Demande de rétrogradation approuvée",
            message=f"Votre demande de rétrogradation de {target_user} a été approuvée.",
            priority='high',
            related_user=target_user,
            related_validation=validation_request,
            send_email=True
        )

        # Notifier les autres validateurs
        NotificationService.notify_other_validators(validation_request, validator, approved=True)

    @staticmethod
    def reject_request(validation_request, validator, comment):
        """
        Rejette une demande.

        Args:
            validation_request: ValidationRequest
            validator: Role qui rejette
            comment: Commentaire (obligatoire)
        """
        # Pour les inscriptions, sauvegarder les infos pour notifier les autres validateurs
        requester_info_for_notification = None
        if validation_request.request_type == 'user_registration':
            if hasattr(validation_request, 'pending_user'):
                pending = validation_request.pending_user
                requester_info_for_notification = f"{pending.get_full_name()} ({pending.email})"

        validation_request.reject(validator, comment)

        # Pour les inscriptions rejetees
        if validation_request.request_type == 'user_registration':
            if hasattr(validation_request, 'pending_user'):
                pending = validation_request.pending_user
                # Envoyer email de rejet
                try:
                    from .tasks import send_registration_rejected_email
                    send_registration_rejected_email.delay(pending.email, comment)
                except Exception as e:
                    # Celery non disponible - log et continue
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Impossible d'envoyer l'email de rejet (Celery indisponible): {e}")

                # NOTE: On garde le PendingUser pour les rejets (pas de Role a lier)
                # Ceci permet d'acceder au nom via validation_request.pending_user

            # Notifier les autres validateurs
            if requester_info_for_notification:
                NotificationService._notify_other_validators_registration(
                    validation_request, validator, requester_info_for_notification, approved=False
                )
        else:
            # Notifier le demandeur
            NotificationService.notify_validation_result(validation_request, approved=False)

            # Notifier les autres validateurs
            NotificationService.notify_other_validators(validation_request, validator, approved=False)

            # Si c'est un rejet de création de site, vérifier les plans liés
            if validation_request.request_type == 'site_creation':
                site = validation_request.target_site
                if site:
                    # Vérifier si des plans sont liés à ce site
                    NotificationService.notify_plans_need_reassignment(
                        site=site,
                        organisme=validation_request.requested_organisme
                    )
