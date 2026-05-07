"""
Commande Django pour creer des donnees de test.

Usage:
    python manage.py seed_testdata           # Cree toutes les donnees de test
    python manage.py seed_testdata --reset   # Supprime les donnees de test
    python manage.py seed_testdata --dry-run # Affiche ce qui serait cree
    python manage.py seed_testdata --only=users,plans  # Seeding selectif

Donnees creees:
    - 4 Modules applicatifs (plans, sites, inventaires, zonages)
    - 5 Organismes
    - 7 Sites (avec types de nomenclature)
    - 14 Utilisateurs (7 actifs + 3 inactifs + 2 en attente + 2 RGPD)
    - 8 Plans de gestion (6 actifs + 2 archives)
    - Groupes Django avec permissions
    - 3 Utilisateurs en attente d'inscription (PendingUser)
    - 22+ Demandes de validation (differents types et statuts)
    - 21+ Notifications (differents types)
    - 8 Logs d'erreur
    - 25+ Logs d'activite
"""
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from apps.users.models import Role, BibOrganismes, Site
from apps.core.models import Module, Nomenclature, ErrorLog, ActivityLog
from apps.plans.models import PlanGestion
from apps.plans.models_enjeux import (
    Enjeu, FacteurInfluence, Pression, Responsabilite,
    ObjectifLongTerme, NiveauExigence, ObjectifOperationnel, ResultatAttendu,
    CorEnjeuTaxon, CorEnjeuHabitat, CorEnjeuGeologie,
    CorResponsabiliteTaxon, CorResponsabiliteHabitat, CorResponsabiliteGeologie,
    CorResponsabiliteEnjeu
)
from apps.plans.models_indicateurs import (
    Indicateur, CorIndicateurTaxon, CorIndicateurHabitat,
    CorIndicateurGeologie, Metrique, Mesure
)
from apps.plans.models_operations import (
    Protocole, SuiviInventaire, Operation,
    CorOperationSite, OperationAnnee, FinanceOperation
)
from apps.notifications.models import Notification, ValidationRequest, PendingUser

from .seeders import (
    SEEDER_CLASSES,
    SeederContext,
    signals_disabled,
    validate_dependencies,
    get_seeders_with_dependencies,
)


DEFAULT_PASSWORD = 'Test123!'

# Schemas requis pour l'architecture multi-schema Cicada
REQUIRED_SCHEMAS = [
    'utilisateurs',
    'referentiels',
    'ref_nomenclatures',
    'ref_geo',
    'general',
    'fichiers',
    'ccd_commons',
    'ccd_notifications',
]


class Command(BaseCommand):
    help = 'Cree ou supprime les donnees de test pour le developpement'

    def _verify_schemas(self):
        """
        Verifie que tous les schemas requis existent dans la base de donnees.

        Raises:
            CommandError: Si un ou plusieurs schemas sont manquants.
        """
        self.stdout.write('\n--- Verification des schemas ---')

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name = ANY(%s)
            """, [REQUIRED_SCHEMAS])
            existing_schemas = {row[0] for row in cursor.fetchall()}

        missing_schemas = set(REQUIRED_SCHEMAS) - existing_schemas

        if missing_schemas:
            raise CommandError(
                f"Schemas manquants: {', '.join(sorted(missing_schemas))}. "
                f"Executez 'python manage.py migrate' pour creer les schemas."
            )

        self.stdout.write(self.style.SUCCESS(
            f'  {len(existing_schemas)} schemas verifies: {", ".join(sorted(existing_schemas))}'
        ))

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Supprime toutes les donnees de test au lieu de les creer',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Affiche ce qui serait cree/supprime sans effectuer les modifications',
        )
        parser.add_argument(
            '--only',
            type=str,
            help='Liste des seeders a executer (separes par des virgules). '
                 'Ex: --only=users,plans. Les dependances sont incluses automatiquement.',
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbosity = options['verbosity']
        self.only = options.get('only')

        if self.dry_run:
            self.stdout.write(self.style.WARNING('Mode dry-run: aucune modification ne sera effectuee'))

        # Verifier les dependances des seeders
        validate_dependencies()

        # Verifier que les schemas existent avant de continuer
        self._verify_schemas()

        try:
            if options['reset']:
                self.reset_test_data()
            else:
                self.create_test_data()
        except Exception as e:
            raise CommandError(f"Erreur lors de l'execution: {e}")

    def _get_seeders_to_run(self):
        """
        Retourne la liste des seeders a executer.

        Returns:
            Liste des classes de seeders
        """
        if self.only:
            names = [n.strip() for n in self.only.split(',')]
            return get_seeders_with_dependencies(names)
        return SEEDER_CLASSES

    @transaction.atomic
    def create_test_data(self):
        """Cree toutes les donnees de test."""
        if self.dry_run:
            self.stdout.write('\n=== Donnees qui seraient creees ===')
            self._show_dry_run_summary()
            return

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Creation des donnees de test ==='))

        context = SeederContext()
        seeders_to_run = self._get_seeders_to_run()

        if self.only:
            seeder_names = [s.name for s in seeders_to_run]
            self.stdout.write(f"Seeders a executer: {', '.join(seeder_names)}")

        for seeder_class in seeders_to_run:
            seeder = seeder_class(
                stdout=self.stdout,
                style=self.style,
                context=context,
                verbosity=self.verbosity,
                dry_run=self.dry_run
            )
            seeder.seed()

        self._print_summary()

    @transaction.atomic
    def reset_test_data(self):
        """Supprime toutes les donnees de test."""
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Suppression des donnees de test ==='))

        if self.dry_run:
            self._show_reset_dry_run_summary()
            return

        # Desactiver les signaux pendant la suppression
        with signals_disabled(self.stdout):
            # Supprimer dans l'ordre inverse des dependances
            self._delete_activity_logs()
            self._delete_error_logs()
            self._delete_notifications()
            self._delete_pending_users()
            self._delete_validation_requests()
            self._delete_enjeux()  # Doit etre avant plans et users car FK vers Role
            self._delete_plans()
            self._delete_users()
            self._delete_sites()
            self._delete_organismes()

        self.stdout.write(self.style.SUCCESS('\nDonnees de test supprimees avec succes!'))

    def _delete_activity_logs(self):
        """Supprime les logs d'activite."""
        count = ActivityLog.objects.all().delete()[0]
        self.stdout.write(f"  Logs d'activite supprimes: {count}")

    def _delete_error_logs(self):
        """Supprime les logs d'erreur."""
        count = ErrorLog.objects.all().delete()[0]
        self.stdout.write(f"  Logs d'erreur supprimes: {count}")

    def _delete_notifications(self):
        """Supprime les notifications."""
        count = Notification.objects.all().delete()[0]
        self.stdout.write(f'  Notifications supprimees: {count}')

    def _delete_pending_users(self):
        """Supprime les utilisateurs en attente."""
        count = PendingUser.objects.all().delete()[0]
        self.stdout.write(f'  Utilisateurs en attente supprimes: {count}')

    def _delete_validation_requests(self):
        """Supprime les demandes de validation."""
        count = ValidationRequest.objects.all().delete()[0]
        self.stdout.write(f'  Demandes de validation supprimees: {count}')

    def _delete_enjeux(self):
        """Supprime les enjeux, FCR, responsabilites, indicateurs, operations et leurs correlations."""
        count = 0
        # Operations et dépendances
        count += FinanceOperation.objects.all().delete()[0]
        count += OperationAnnee.objects.all().delete()[0]
        count += CorOperationSite.objects.all().delete()[0]
        count += Operation.objects.all().delete()[0]
        count += SuiviInventaire.objects.all().delete()[0]
        count += Protocole.objects.all().delete()[0]
        # Indicateurs et dépendances
        count += Mesure.objects.all().delete()[0]
        count += Metrique.objects.all().delete()[0]
        count += CorIndicateurTaxon.objects.all().delete()[0]
        count += CorIndicateurHabitat.objects.all().delete()[0]
        count += CorIndicateurGeologie.objects.all().delete()[0]
        count += Indicateur.objects.all().delete()[0]
        # Enjeux sous-entités
        count += NiveauExigence.objects.all().delete()[0]
        count += ObjectifLongTerme.objects.all().delete()[0]
        # OO et RA sont liés aux Pressions via M2M (cascade libère le lien
        # mais laisse les OO/RA orphelins, qui bloquent la suppression des
        # Roles via leur FK PROTECT id_utilisateur_ajout)
        count += ResultatAttendu.objects.all().delete()[0]
        count += ObjectifOperationnel.objects.all().delete()[0]
        count += Pression.objects.all().delete()[0]
        count += FacteurInfluence.objects.all().delete()[0]
        # Corrélations
        count += CorResponsabiliteEnjeu.objects.all().delete()[0]
        count += CorResponsabiliteTaxon.objects.all().delete()[0]
        count += CorResponsabiliteHabitat.objects.all().delete()[0]
        count += CorEnjeuTaxon.objects.all().delete()[0]
        count += CorEnjeuHabitat.objects.all().delete()[0]
        count += CorEnjeuGeologie.objects.all().delete()[0]
        count += Responsabilite.objects.all().delete()[0]
        count += Enjeu.objects.all().delete()[0]
        self.stdout.write(f'  Enjeux, indicateurs et operations supprimes: {count}')

    def _delete_plans(self):
        """Supprime les plans de gestion."""
        count = PlanGestion.objects.all().delete()[0]
        self.stdout.write(f'  Plans de gestion supprimes: {count}')

    def _delete_users(self):
        """Supprime les utilisateurs de test."""
        test_emails = [
            'admin@test.fr', 'admin.rnf@test.fr', 'admin.cen@test.fr',
            'referent.camargue@test.fr', 'referent.vercors@test.fr',
            'user.rnf@test.fr', 'user.cen@test.fr',
            'ancien.rnf@test.fr', 'ancien.cen@test.fr', 'stagiaire.dreal@test.fr',
            'pending.rnf@test.fr', 'pending.cen@test.fr',
            'deletion.recent@test.fr', 'deletion.old@test.fr',
        ]
        count = Role.objects.filter(email__in=test_emails).delete()[0]
        self.stdout.write(f'  Utilisateurs supprimes: {count}')

    def _delete_sites(self):
        """Supprime les sites de test."""
        count = Site.objects.all().delete()[0]
        self.stdout.write(f'  Sites supprimes: {count}')

    def _delete_organismes(self):
        """Supprime les organismes de test."""
        # Liste incluant les noms actuels (accentués) et les anciens noms ASCII
        # afin de nettoyer les bases qui n'ont pas encore été migrées.
        test_organismes = [
            'Réserves Naturelles de France',
            'CEN Auvergne-Rhône-Alpes',
            'DREAL Nouvelle-Aquitaine',
            'Parc National des Écrins',
            'Office Français de la Biodiversité',
            # Anciennes variantes ASCII
            'Reserves Naturelles de France',
            'CEN Auvergne-Rhone-Alpes',
            'Parc National des Ecrins',
            'Office Francais de la Biodiversite',
        ]
        count = BibOrganismes.objects.filter(nom_organisme__in=test_organismes).delete()[0]
        self.stdout.write(f'  Organismes supprimés: {count}')

    def _show_dry_run_summary(self):
        """Affiche un resume des donnees qui seraient creees."""
        context = SeederContext()
        seeders_to_run = self._get_seeders_to_run()

        for seeder_class in seeders_to_run:
            seeder = seeder_class(
                stdout=self.stdout,
                style=self.style,
                context=context,
                verbosity=self.verbosity,
                dry_run=True
            )
            seeder.print_dry_run_summary()

        # Afficher les informations de permissions
        self.stdout.write('\nHierarchie des permissions de validation:')
        self.stdout.write('  super_admin > admin_og > referent > utilisateur')
        self.stdout.write('  - super_admin: peut valider TOUTES les demandes')
        self.stdout.write('  - admin_og: demandes liees a son organisme')
        self.stdout.write('  - referent: demandes sur ses sites')

    def _show_reset_dry_run_summary(self):
        """Affiche un resume des donnees qui seraient supprimees."""
        self.stdout.write("Logs d'activite: tous seraient supprimes")
        self.stdout.write("Logs d'erreur: tous seraient supprimes")
        self.stdout.write('Notifications: toutes seraient supprimees')
        self.stdout.write('Demandes de validation: toutes seraient supprimees')
        self.stdout.write('Utilisateurs en attente: tous seraient supprimes')
        self.stdout.write('Enjeux et responsabilites: tous seraient supprimes')
        self.stdout.write('Plans de gestion: tous seraient supprimes')
        self.stdout.write('Utilisateurs de test: 14 seraient supprimes')
        self.stdout.write('Sites: tous seraient supprimes')
        self.stdout.write('Organismes de test: 5 seraient supprimes')

    def _print_summary(self):
        """Affiche un resume des donnees creees."""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('DONNEES DE TEST CREEES AVEC SUCCES'))
        self.stdout.write('=' * 70)

        users_actifs = Role.objects.filter(active=True, pending_validation=False).count()
        users_pending = Role.objects.filter(pending_validation=True).count()
        users_inactifs = Role.objects.filter(active=False).count()
        plans_archives = PlanGestion.objects.filter(statut='archive').count()
        plans_actifs = PlanGestion.objects.exclude(statut='archive').count()
        pending_users_count = PendingUser.objects.count()
        validation_requests_pending = ValidationRequest.objects.filter(status='pending').count()
        notifications_unread = Notification.objects.filter(read=False).count()

        enjeux_count = Enjeu.objects.filter(id_categorie__mnemonique='ENJEU').count()
        fcr_count = Enjeu.objects.filter(id_categorie__mnemonique='FCR').count()
        responsabilites_count = Responsabilite.objects.count()

        self.stdout.write(f'\n  Modules:              {Module.objects.count()}')
        self.stdout.write(f'  Organismes:           {BibOrganismes.objects.count()}')
        self.stdout.write(f'  Sites:                {Site.objects.count()}')
        self.stdout.write(f'  Utilisateurs:         {Role.objects.count()} ({users_actifs} actifs, {users_pending} en attente, {users_inactifs} inactifs)')
        self.stdout.write(f'  Plans de gestion:     {PlanGestion.objects.count()} ({plans_actifs} actifs, {plans_archives} archives)')
        self.stdout.write(f'  Enjeux/FCR:           {Enjeu.objects.count()} ({enjeux_count} enjeux, {fcr_count} FCR)')
        self.stdout.write(f'  Responsabilites:      {responsabilites_count}')
        self.stdout.write(f'  Groupes Django:       {Group.objects.count()}')
        self.stdout.write(f'  Nomenclatures:        {Nomenclature.objects.count()}')
        self.stdout.write(f'  Inscriptions attente: {pending_users_count}')
        self.stdout.write(f'  Validations:          {ValidationRequest.objects.count()} ({validation_requests_pending} en attente)')
        self.stdout.write(f'  Notifications:        {Notification.objects.count()} ({notifications_unread} non lues)')
        error_logs_unack = ErrorLog.objects.filter(acknowledged=False).count()
        self.stdout.write(f"  Logs d'erreur:        {ErrorLog.objects.count()} ({error_logs_unack} non acquittes)")
        activity_logs_system = ActivityLog.objects.filter(visibility='system').count()
        activity_logs_admin = ActivityLog.objects.filter(visibility='admin').count()
        activity_logs_public = ActivityLog.objects.filter(visibility='public').count()
        self.stdout.write(f"  Logs d'activite:      {ActivityLog.objects.count()} ({activity_logs_public} publics, {activity_logs_admin} admin, {activity_logs_system} systeme)")

        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('UTILISATEURS DE TEST ACTIFS')
        self.stdout.write('-' * 70)
        self.stdout.write(f'\n  Mot de passe pour tous: {DEFAULT_PASSWORD}')
        self.stdout.write('''
  | Identifiant     | Email                      | Role            | Organisme   |
  |-----------------|----------------------------|-----------------|-------------|
  | super_admin     | admin@test.fr              | Super Admin     | RNF         |
  | admin_rnf       | admin.rnf@test.fr          | Admin Organisme | RNF         |
  | admin_cen       | admin.cen@test.fr          | Admin Organisme | CEN AURA    |
  | ref_camargue    | referent.camargue@test.fr  | Referent        | RNF         |
  | ref_vercors     | referent.vercors@test.fr   | Referent        | CEN AURA    |
  | user_rnf        | user.rnf@test.fr           | Utilisateur     | RNF         |
  | user_cen        | user.cen@test.fr           | Utilisateur     | CEN AURA    |
        ''')

        self.stdout.write('-' * 70)
        self.stdout.write('UTILISATEURS EN ATTENTE DE VALIDATION')
        self.stdout.write('-' * 70)
        self.stdout.write('''
  | Identifiant     | Email                      | Role            | Organisme   |
  |-----------------|----------------------------|-----------------|-------------|
  | pending_rnf     | pending.rnf@test.fr        | Utilisateur     | RNF         |
  | pending_cen     | pending.cen@test.fr        | Utilisateur     | CEN AURA    |
        ''')

        self.stdout.write('-' * 70)
        self.stdout.write('UTILISATEURS DE TEST INACTIFS')
        self.stdout.write('-' * 70)
        self.stdout.write('''
  | Identifiant     | Email                      | Role            | Organisme   |
  |-----------------|----------------------------|-----------------|-------------|
  | ancien_rnf      | ancien.rnf@test.fr         | Referent        | RNF         |
  | ancien_cen      | ancien.cen@test.fr         | Admin Organisme | CEN AURA    |
  | stagiaire_dreal | stagiaire.dreal@test.fr    | Utilisateur     | DREAL       |
        ''')

        self.stdout.write('-' * 70)
        self.stdout.write("INSCRIPTIONS EN ATTENTE (PendingUser)")
        self.stdout.write('-' * 70)
        self.stdout.write('''
  | Email                  | Nom             | Organisme   | Validable par                    |
  |------------------------|-----------------|-------------|----------------------------------|
  | nouveau.user1@test.fr  | Marc Lefebvre   | RNF         | admin@test.fr, admin.rnf@test.fr |
  | nouveau.user2@test.fr  | Lea Simon       | CEN AURA    | admin@test.fr, admin.cen@test.fr |
  | nouveau.user3@test.fr  | Paul Michel     | DREAL       | admin@test.fr                    |
        ''')

        self.stdout.write('-' * 70)
        self.stdout.write('HIERARCHIE DES PERMISSIONS')
        self.stdout.write('-' * 70)
        self.stdout.write('''
  super_admin > admin_og > referent > utilisateur

  Qui peut valider quoi:
  - user_registration  : super_admin, admin_og de l'organisme demande
  - site_access        : super_admin, admin_og gestionnaire, referent du site
  - plan_access        : super_admin, admin_og, referent du plan
  - referent_validation: super_admin, admin_og gestionnaire du site
  - admin_deactivation : super_admin uniquement
        ''')

        self.stdout.write('-' * 70)
        self.stdout.write('NOTIFICATIONS DE TEST')
        self.stdout.write('-' * 70)
        self.stdout.write('''
  Repartition par utilisateur:
    - admin@test.fr:              2 notifications (1 non lue)
    - admin.rnf@test.fr:          4 notifications (2 non lues)
    - admin.cen@test.fr:          3 notifications (2 non lues)
    - referent.camargue@test.fr:  2 notifications (2 non lues)
    - referent.vercors@test.fr:   2 notifications (0 non lues)
    - user.rnf@test.fr:           4 notifications (2 non lues)
    - user.cen@test.fr:           2 notifications (0 non lues)
        ''')

        self.stdout.write('-' * 70)
        self.stdout.write('URLs UTILES')
        self.stdout.write('-' * 70)
        self.stdout.write('''
  Frontend:           http://localhost:4200/auth/login
  Admin Django:       http://localhost:8000/admin/
  API Auth Login:     POST http://localhost:8000/api/auth/login/
  API Notifications:  GET http://localhost:8000/api/notifications/
  API Validations:    GET http://localhost:8000/api/notifications/validations/
        ''')
