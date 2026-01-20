"""
Commande Django pour creer des donnees de test.

Usage:
    python manage.py seed_testdata           # Cree toutes les donnees de test
    python manage.py seed_testdata --reset   # Supprime les donnees de test
    python manage.py seed_testdata --dry-run # Affiche ce qui serait cree

Donnees creees:
    - 4 Modules applicatifs (plans, sites, inventaires, zonages)
    - 5 Organismes
    - 7 Sites (avec types de nomenclature)
    - 12 Utilisateurs (7 actifs + 3 inactifs + 2 en attente validation)
    - 8 Plans de gestion (5 actifs + 3 archives)
    - Groupes Django avec permissions
    - Nomenclatures (types de site, evaluation, redacteur)
    - 3 Utilisateurs en attente d'inscription (PendingUser)
    - 10+ Demandes de validation (differents types et statuts)
      - Inclut 3 demandes d'acces module (module_access)
    - 15+ Notifications (differents types)
"""
from datetime import timedelta

from django.contrib.auth.hashers import make_password
from django.contrib.gis.geos import Point, MultiPolygon, Polygon
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.db import connection, transaction
from django.utils import timezone

from apps.users.models import Role, BibOrganismes, Site, CorRoleSite, CorOgSite
from apps.core.models import TypeNomenclature, Nomenclature, Module, ErrorLog
from apps.plans.models import PlanGestion, CorSitePg
from apps.notifications.models import Notification, ValidationRequest, PendingUser


DEFAULT_PASSWORD = 'Test123!'

# Schemas requis pour l'architecture multi-schema Cicada
REQUIRED_SCHEMAS = [
    'utilisateurs',        # Users, organisations, cor_role_ep (GeoNature)
    'referentiels',        # Sites/espaces proteges, cor_ep_og (ODASE)
    'ref_nomenclatures',   # Types de nomenclature, nomenclatures (GeoNature)
    'ref_geo',             # Referentiels geographiques (GeoNature) - futur
    'general',             # Plans de gestion, cor_ep_pg (ODASE)
    'fichiers',            # Fichiers attaches (ODASE)
    'ccd_commons',         # Modules, logs impersonation (Cicada)
    'ccd_notifications',   # Notifications, validations, pending users (Cicada)
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

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.verbosity = options['verbosity']

        if self.dry_run:
            self.stdout.write(self.style.WARNING('Mode dry-run: aucune modification ne sera effectuee'))

        # Verifier que les schemas existent avant de continuer
        self._verify_schemas()

        try:
            if options['reset']:
                self.reset_test_data()
            else:
                self.create_test_data()
        except Exception as e:
            raise CommandError(f'Erreur lors de l\'execution: {e}')

    @transaction.atomic
    def create_test_data(self):
        """Cree toutes les donnees de test."""
        if self.dry_run:
            self.stdout.write('\n=== Donnees qui seraient creees ===')
            self._show_dry_run_summary()
            return

        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Creation des donnees de test ==='))

        modules = self._create_modules()
        nomenclatures = self._create_nomenclatures()
        groups = self._create_groups()
        organismes = self._create_organismes()
        sites = self._create_sites(organismes)
        users = self._create_users(organismes, sites, groups)
        plans = self._create_plans(users, sites)
        pending_users = self._create_pending_users(organismes)
        validation_requests = self._create_validation_requests(users, sites, plans, organismes)
        notifications = self._create_notifications(users, sites, plans, validation_requests, organismes)
        error_logs = self._create_error_logs(users)

        self._print_summary()

    @transaction.atomic
    def reset_test_data(self):
        """Supprime toutes les donnees de test."""
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Suppression des donnees de test ==='))

        if self.dry_run:
            self.stdout.write('Logs d\'erreur: tous seraient supprimes')
            self.stdout.write('Notifications: toutes seraient supprimees')
            self.stdout.write('Demandes de validation: toutes seraient supprimees')
            self.stdout.write('Utilisateurs en attente: tous seraient supprimes')
            self.stdout.write('Plans de gestion: tous seraient supprimes')
            self.stdout.write('Utilisateurs de test: 10 seraient supprimes')
            self.stdout.write('Sites: tous seraient supprimes')
            self.stdout.write('Organismes de test: 5 seraient supprimes')
            return

        # Desactiver les signaux pour eviter la creation de notifications pendant la suppression
        from django.db.models.signals import post_save, post_delete, pre_save, m2m_changed
        from apps.notifications import signals as notif_signals
        from apps.users.models import CorRoleSite

        # Deconnecter tous les signaux de notifications
        post_save.disconnect(notif_signals.notify_user_site_association, sender=CorRoleSite)
        post_delete.disconnect(notif_signals.check_site_orphaned_on_user_removal, sender=CorRoleSite)
        post_delete.disconnect(notif_signals.notify_user_removed_from_site, sender=CorRoleSite)
        pre_save.disconnect(notif_signals.track_user_deactivation, sender=Role)
        post_save.disconnect(notif_signals.notify_user_deactivation, sender=Role)
        post_save.disconnect(notif_signals.notify_new_validation_request, sender=ValidationRequest)
        post_save.disconnect(notif_signals.handle_validation_result, sender=ValidationRequest)
        pre_save.disconnect(notif_signals.track_validation_status, sender=ValidationRequest)

        self.stdout.write('  Signaux de notifications desactives')

        # Supprimer les logs d'erreur
        error_logs_deleted = ErrorLog.objects.all().delete()[0]
        self.stdout.write(f'  Logs d\'erreur supprimes: {error_logs_deleted}')

        # Supprimer les notifications
        notifs_deleted = Notification.objects.all().delete()[0]
        self.stdout.write(f'  Notifications supprimees: {notifs_deleted}')

        # Supprimer les utilisateurs en attente (supprime aussi les ValidationRequest liees)
        pending_deleted = PendingUser.objects.all().delete()[0]
        self.stdout.write(f'  Utilisateurs en attente supprimes: {pending_deleted}')

        # Supprimer les demandes de validation restantes
        validation_deleted = ValidationRequest.objects.all().delete()[0]
        self.stdout.write(f'  Demandes de validation supprimees: {validation_deleted}')

        # Supprimer les plans
        plans_deleted = PlanGestion.objects.all().delete()[0]
        self.stdout.write(f'  Plans de gestion supprimes: {plans_deleted}')

        # Supprimer les utilisateurs de test (garder le superuser original)
        test_emails = [
            'admin@test.fr', 'admin.rnf@test.fr', 'admin.cen@test.fr',
            'referent.camargue@test.fr', 'referent.vercors@test.fr',
            'user.rnf@test.fr', 'user.cen@test.fr',
            # Utilisateurs inactifs
            'ancien.rnf@test.fr', 'ancien.cen@test.fr', 'stagiaire.dreal@test.fr',
            # Utilisateurs en attente de validation
            'pending.rnf@test.fr', 'pending.cen@test.fr'
        ]
        users_deleted = Role.objects.filter(email__in=test_emails).delete()[0]
        self.stdout.write(f'  Utilisateurs supprimes: {users_deleted}')

        # Supprimer les sites de test
        sites_deleted = Site.objects.all().delete()[0]
        self.stdout.write(f'  Sites supprimes: {sites_deleted}')

        # Supprimer les organismes de test
        test_organismes = [
            'Reserves Naturelles de France',
            'CEN Auvergne-Rhone-Alpes',
            'DREAL Nouvelle-Aquitaine',
            'Parc National des Ecrins',
            'Office Francais de la Biodiversite'
        ]
        orgs_deleted = BibOrganismes.objects.filter(nom_organisme__in=test_organismes).delete()[0]
        self.stdout.write(f'  Organismes supprimes: {orgs_deleted}')

        # Reconnecter les signaux
        post_save.connect(notif_signals.notify_user_site_association, sender=CorRoleSite)
        post_delete.connect(notif_signals.check_site_orphaned_on_user_removal, sender=CorRoleSite)
        post_delete.connect(notif_signals.notify_user_removed_from_site, sender=CorRoleSite)
        pre_save.connect(notif_signals.track_user_deactivation, sender=Role)
        post_save.connect(notif_signals.notify_user_deactivation, sender=Role)
        post_save.connect(notif_signals.notify_new_validation_request, sender=ValidationRequest)
        post_save.connect(notif_signals.handle_validation_result, sender=ValidationRequest)
        pre_save.connect(notif_signals.track_validation_status, sender=ValidationRequest)

        self.stdout.write('  Signaux de notifications reactives')
        self.stdout.write(self.style.SUCCESS('\nDonnees de test supprimees avec succes!'))

    def _show_dry_run_summary(self):
        """Affiche un resume des donnees qui seraient creees."""
        self.stdout.write('\nModules (4):')
        self.stdout.write('  - plans: Mes plans de gestion (primary)')
        self.stdout.write('  - sites: Mes sites (salmon)')
        self.stdout.write('  - inventaires: Mes inventaires et suivis (yellow)')
        self.stdout.write('  - zonages: Zonages reglementaires (terra-cotta) [requires_access]')

        self.stdout.write('\nNomenclatures:')
        self.stdout.write('  - 3 types de nomenclature (site, evaluation, redacteur)')
        self.stdout.write('  - 5 types de site (RNN, RNR, PNR, ENS, APB)')
        self.stdout.write('  - 3 types d\'evaluation')
        self.stdout.write('  - 3 types de redacteur')

        self.stdout.write('\nGroupes Django:')
        self.stdout.write('  - Super Administrateurs')
        self.stdout.write('  - Administrateurs Organisme')
        self.stdout.write('  - Referents')
        self.stdout.write('  - Utilisateurs')

        self.stdout.write('\nOrganismes (5):')
        self.stdout.write('  - Reserves Naturelles de France')
        self.stdout.write('  - CEN Auvergne-Rhone-Alpes')
        self.stdout.write('  - DREAL Nouvelle-Aquitaine')
        self.stdout.write('  - Parc National des Ecrins')
        self.stdout.write('  - Office Francais de la Biodiversite')

        self.stdout.write('\nSites (7) avec organismes gestionnaires:')
        self.stdout.write('  - Reserve Naturelle de la Camargue (RNN)')
        self.stdout.write('      Organismes: RNF [PRINCIPAL], OFB')
        self.stdout.write('  - Reserve Naturelle des Aiguilles Rouges (RNN)')
        self.stdout.write('      Organismes: RNF [PRINCIPAL]')
        self.stdout.write('  - Reserve Naturelle Regionale du Grand-Voyeux (RNR)')
        self.stdout.write('      Organismes: CEN AURA [PRINCIPAL]')
        self.stdout.write('  - Parc Naturel Regional du Vercors (PNR)')
        self.stdout.write('      Organismes: CEN AURA [PRINCIPAL], DREAL')
        self.stdout.write('  - Espace Naturel Sensible des Marais de Brouage (ENS)')
        self.stdout.write('      Organismes: DREAL [PRINCIPAL]')
        self.stdout.write('  - Reserve Naturelle de Scandola (RNN)')
        self.stdout.write('      Organismes: Parc Ecrins [PRINCIPAL], OFB')
        self.stdout.write('  - Reserve Naturelle du Lac de Remoray (RNN)')
        self.stdout.write('      Organismes: RNF [PRINCIPAL]')

        self.stdout.write('\nUtilisateurs actifs (7):')
        self.stdout.write(f'  Mot de passe commun: {DEFAULT_PASSWORD}')
        self.stdout.write('  - admin@test.fr (super_admin)')
        self.stdout.write('  - admin.rnf@test.fr (admin_og) - RNF')
        self.stdout.write('  - admin.cen@test.fr (admin_og) - CEN AURA')
        self.stdout.write('  - referent.camargue@test.fr (referent) - RNF')
        self.stdout.write('  - referent.vercors@test.fr (referent) - CEN AURA')
        self.stdout.write('  - user.rnf@test.fr (utilisateur) - RNF')
        self.stdout.write('  - user.cen@test.fr (utilisateur) - CEN AURA')

        self.stdout.write('\nUtilisateurs inactifs (3):')
        self.stdout.write('  - ancien.rnf@test.fr (referent) - RNF [INACTIF]')
        self.stdout.write('  - ancien.cen@test.fr (admin_og) - CEN AURA [INACTIF]')
        self.stdout.write('  - stagiaire.dreal@test.fr (utilisateur) - DREAL [INACTIF]')

        self.stdout.write('\nPlans de gestion actifs (6):')
        self.stdout.write('  - Plan 2020-2030 Camargue (valide)')
        self.stdout.write('  - Plan 2018-2028 Aiguilles Rouges (valide)')
        self.stdout.write('  - Plan 2022-2032 Grand-Voyeux (draft)')
        self.stdout.write('  - Plan inter-sites Vercors-Ecrins 2021-2031 (valide)')
        self.stdout.write('  - Plan 2019-2029 Marais de Brouage (archive)')
        self.stdout.write('  - Plan 2023-2033 Lac de Remoray (draft)')

        self.stdout.write('\nPlans de gestion archives (2):')
        self.stdout.write('  - Plan 2010-2020 Camargue ancien (archive)')
        self.stdout.write('  - Plan 2008-2018 Aiguilles Rouges ancien (archive)')

        self.stdout.write('\nUtilisateurs en attente de validation (2):')
        self.stdout.write('  - pending.rnf@test.fr - Utilisateur inscrit, en attente validation')
        self.stdout.write('  - pending.cen@test.fr - Utilisateur inscrit, en attente validation')

        self.stdout.write('\nUtilisateurs en attente d\'inscription - PendingUser (3):')
        self.stdout.write('  Chaque PendingUser a sa propre ValidationRequest unique.')
        self.stdout.write('  - nouveau.user1@test.fr - Demande RNF')
        self.stdout.write('      Validable par: admin@test.fr, admin.rnf@test.fr')
        self.stdout.write('  - nouveau.user2@test.fr - Demande CEN AURA')
        self.stdout.write('      Validable par: admin@test.fr, admin.cen@test.fr')
        self.stdout.write('  - nouveau.user3@test.fr - Demande DREAL')
        self.stdout.write('      Validable par: admin@test.fr (pas d\'admin DREAL)')

        self.stdout.write('\nHierarchie des permissions de validation:')
        self.stdout.write('  super_admin > admin_og > referent > utilisateur')
        self.stdout.write('  - super_admin: peut valider TOUTES les demandes')
        self.stdout.write('  - admin_og: demandes liees a son organisme')
        self.stdout.write('  - referent: demandes sur ses sites')

        self.stdout.write('\nDemandes de validation (13 = 3 inscriptions + 10 autres):')
        self.stdout.write('  Types: user_registration, site_access, plan_access, referent_validation, admin_deactivation, module_access')
        self.stdout.write('  Statuts: pending, approved, rejected')
        self.stdout.write('  Dates de validation variees:')
        self.stdout.write('    - site_access approved: il y a 3 jours')
        self.stdout.write('    - plan_access rejected: il y a 1 semaine')
        self.stdout.write('    - referent_validation approved: il y a 2 semaines')
        self.stdout.write('    - module_access approved (user_rnf -> zonages): il y a 5 jours')
        self.stdout.write('    - module_access rejected (referent_vercors -> zonages): il y a 10 jours')
        self.stdout.write('    - module_access pending (user_cen -> zonages): en attente')

        self.stdout.write('\nNotifications (15+):')
        self.stdout.write('  Types: validation_request, validation_approved, validation_rejected,')
        self.stdout.write('         user_associated_site, info, system_alert')
        self.stdout.write('  Priorites: low, medium, high, critical')

        self.stdout.write('\nLogs d\'erreur (8):')
        self.stdout.write('  Niveaux: WARNING, ERROR, CRITICAL')
        self.stdout.write('  - 3 WARNING (avertissements)')
        self.stdout.write('  - 3 ERROR (erreurs standards)')
        self.stdout.write('  - 2 CRITICAL (erreurs critiques)')
        self.stdout.write('  - 4 non acquittes, 4 acquittes')
        self.stdout.write('  - Dates variees sur les 7 derniers jours')

    def _create_modules(self):
        """
        Cree les modules applicatifs.

        Les modules sont normalement crees par la migration 0003_seed_modules.py,
        mais cette methode assure qu'ils existent meme apres un reset complet.
        """
        self.stdout.write('\n--- Creation des modules ---')

        modules_data = [
            {
                'code': 'plans',
                'name': 'Mes plans de gestion',
                'description': 'Gestion des plans de gestion des espaces naturels',
                'icon': 'fi-rr-document',
                'color': 'primary',
                'route': '/plans',
                'requires_access': False,
                'is_active': True,
                'display_order': 0,
            },
            {
                'code': 'sites',
                'name': 'Mes sites',
                'description': 'Gestion des sites et espaces proteges',
                'icon': 'fi-rr-map-marker',
                'color': 'salmon',
                'route': '/sites',
                'requires_access': False,
                'is_active': True,
                'display_order': 1,
            },
            {
                'code': 'inventaires',
                'name': 'Mes inventaires et suivis',
                'description': 'Gestion des inventaires et suivis naturalistes',
                'icon': 'fi-rr-test-tube',
                'color': 'yellow',
                'route': '/inventaires',
                'requires_access': False,
                'is_active': True,
                'display_order': 2,
            },
            {
                'code': 'zonages',
                'name': 'Zonages reglementaires',
                'description': 'Acces aux zonages reglementaires et leur gestion',
                'icon': 'fi-rr-map',
                'color': 'terra-cotta',
                'route': '/zonages',
                'requires_access': True,
                'is_active': True,
                'display_order': 3,
            },
        ]

        modules = []
        for module_data in modules_data:
            module, created = Module.objects.get_or_create(
                code=module_data['code'],
                defaults=module_data
            )
            modules.append(module)
            if self.verbosity >= 2:
                status = "cree" if created else "existant"
                self.stdout.write(f"  [{status.upper()}] {module.code}: {module.name}")

        self.stdout.write(self.style.SUCCESS(f'  {len(modules)} modules'))
        return modules

    def _create_nomenclatures(self):
        """
        Cree les nomenclatures necessaires.
        Aligne sur les fichiers SQL officiels (nomenclatures_data/*.sql).
        """
        self.stdout.write('\n--- Creation des nomenclatures ---')

        # Types de nomenclature (alignes sur types_inserts.sql)
        type_site, _ = TypeNomenclature.objects.get_or_create(
            id_type=1,
            defaults={'mnemonique': 'Espace naturel', 'label': "Type d'espace naturel"}
        )

        type_eval, _ = TypeNomenclature.objects.get_or_create(
            id_type=2,
            defaults={'mnemonique': 'Evaluation PG', 'label': "Niveau d'evaluation des plans de gestion"}
        )

        type_redac, _ = TypeNomenclature.objects.get_or_create(
            id_type=3,
            defaults={'mnemonique': 'Redacteur type', 'label': "Type de redacteur d'un plan de gestion"}
        )

        # Nomenclatures de type de site (alignees sur nomenclatures_inserts.sql)
        # Note: Dans les fichiers SQL, cd_nomenclature est NULL, on utilise mnemonique
        site_types = [
            {'id': 42, 'mnemonique': 'RNN', 'label': 'Reserve Naturelle Nationale'},
            {'id': 43, 'mnemonique': 'RNR', 'label': 'Reserve Naturelle Regionale'},
            {'id': 44, 'mnemonique': 'RNC', 'label': 'Reserve Naturelle de Corse'},
            {'id': 93, 'mnemonique': 'PPRN', 'label': 'Perimetre de protection de reserve naturelle'},
            {'id': 600, 'mnemonique': 'PNR', 'label': 'Parc Naturel Regional'},
            {'id': 601, 'mnemonique': 'ENS', 'label': 'Espace Naturel Sensible'},
            {'id': 602, 'mnemonique': 'APB', 'label': 'Arrete de Protection de Biotope'},
        ]

        for st in site_types:
            Nomenclature.objects.update_or_create(
                id_nomenclature=st['id'],
                defaults={
                    'id_type': type_site,
                    'cd_nomenclature': None,
                    'mnemonique': st['mnemonique'],
                    'label': st['label'],
                    'actif': True
                }
            )
            if self.verbosity >= 2:
                self.stdout.write(f"  Type de site: {st['label']} ({st['mnemonique']})")

        # Nomenclatures d'evaluation (alignees sur nomenclatures_inserts.sql)
        eval_types = [
            {'id': 45, 'mnemonique': 'Aucune', 'label': 'Aucune evaluation', 'hierarchy': '1'},
            {'id': 47, 'mnemonique': 'Intermediaire', 'label': 'Evaluation intermediaire', 'hierarchy': '2'},
            {'id': 46, 'mnemonique': 'Finale', 'label': 'Evaluation finale', 'hierarchy': '3'},
        ]

        for et in eval_types:
            Nomenclature.objects.update_or_create(
                id_nomenclature=et['id'],
                defaults={
                    'id_type': type_eval,
                    'cd_nomenclature': None,
                    'mnemonique': et['mnemonique'],
                    'label': et['label'],
                    'hierarchy': et.get('hierarchy'),
                    'actif': True
                }
            )
            if self.verbosity >= 2:
                self.stdout.write(f"  Type evaluation: {et['label']} ({et['mnemonique']})")

        # Nomenclatures de redacteur (alignees sur nomenclatures_inserts.sql)
        redac_types = [
            {'id': 48, 'mnemonique': 'OG', 'label': 'Organisme Gestionnaire'},
            {'id': 603, 'mnemonique': 'BE', 'label': "Bureau d'etudes"},
            {'id': 50, 'mnemonique': 'Autre', 'label': 'Autre'},
        ]

        for rt in redac_types:
            Nomenclature.objects.update_or_create(
                id_nomenclature=rt['id'],
                defaults={
                    'id_type': type_redac,
                    'cd_nomenclature': None,
                    'mnemonique': rt['mnemonique'],
                    'label': rt['label'],
                    'actif': True
                }
            )
            if self.verbosity >= 2:
                self.stdout.write(f"  Type redacteur: {rt['label']} ({rt['mnemonique']})")

        self.stdout.write(self.style.SUCCESS('  Nomenclatures creees'))
        return {'type_site': type_site, 'type_eval': type_eval, 'type_redac': type_redac}

    def _create_groups(self):
        """Cree les groupes Django pour les permissions."""
        self.stdout.write('\n--- Creation des groupes ---')

        groups_data = [
            {
                'name': 'Super Administrateurs',
                'permissions': [
                    'add_role', 'change_role', 'delete_role', 'view_role',
                    'add_site', 'change_site', 'delete_site', 'view_site',
                    'add_plangestion', 'change_plangestion', 'delete_plangestion', 'view_plangestion',
                    'add_biborganismes', 'change_biborganismes', 'delete_biborganismes', 'view_biborganismes'
                ]
            },
            {
                'name': 'Administrateurs Organisme',
                'permissions': [
                    'change_role', 'view_role',
                    'add_site', 'change_site', 'view_site',
                    'add_plangestion', 'change_plangestion', 'view_plangestion',
                    'view_biborganismes'
                ]
            },
            {
                'name': 'Referents',
                'permissions': [
                    'view_role',
                    'change_site', 'view_site',
                    'add_plangestion', 'change_plangestion', 'view_plangestion'
                ]
            },
            {
                'name': 'Utilisateurs',
                'permissions': ['view_site', 'view_plangestion']
            },
        ]

        groups = {}
        for group_data in groups_data:
            group, created = Group.objects.get_or_create(name=group_data['name'])
            if created:
                for perm_codename in group_data['permissions']:
                    try:
                        perm = Permission.objects.get(codename=perm_codename)
                        group.permissions.add(perm)
                    except Permission.DoesNotExist:
                        pass
                if self.verbosity >= 2:
                    self.stdout.write(f"  Groupe cree: {group.name}")
            groups[group.name] = group

        self.stdout.write(self.style.SUCCESS('  Groupes crees'))
        return groups

    def _create_organismes(self):
        """Cree les organismes de test."""
        self.stdout.write('\n--- Creation des organismes ---')

        organismes_data = [
            {
                'nom_organisme': 'Reserves Naturelles de France',
                'email_organisme': 'contact@reserves-naturelles.org',
                'ville_organisme': 'Dijon',
                'cp_organisme': '21000',
                'adresse_organisme': '6 rue de la Manutention',
                'tel_organisme': '03 80 48 91 00'
            },
            {
                'nom_organisme': 'CEN Auvergne-Rhone-Alpes',
                'email_organisme': 'contact@cen-aura.org',
                'ville_organisme': 'Lyon',
                'cp_organisme': '69007',
                'adresse_organisme': '11 Allee de Lodz',
                'tel_organisme': '04 72 31 84 50'
            },
            {
                'nom_organisme': 'DREAL Nouvelle-Aquitaine',
                'email_organisme': 'contact@nouvelle-aquitaine.gouv.fr',
                'ville_organisme': 'Bordeaux',
                'cp_organisme': '33000',
                'adresse_organisme': '15 rue Arthur Ranc',
                'tel_organisme': '05 56 24 80 80'
            },
            {
                'nom_organisme': 'Parc National des Ecrins',
                'email_organisme': 'contact@ecrins-parcnational.fr',
                'ville_organisme': 'Gap',
                'cp_organisme': '05000',
                'adresse_organisme': 'Domaine de Charance',
                'tel_organisme': '04 92 40 20 10'
            },
            {
                'nom_organisme': 'Office Francais de la Biodiversite',
                'email_organisme': 'contact@ofb.gouv.fr',
                'ville_organisme': 'Vincennes',
                'cp_organisme': '94300',
                'adresse_organisme': '12 Cours Louis Lumiere',
                'tel_organisme': '01 45 14 36 00'
            },
        ]

        # Nettoyer les doublons potentiels (variations avec/sans accents)
        # Par exemple: "CEN Auvergne-Rhône-Alpes" vs "CEN Auvergne-Rhone-Alpes"
        variations_to_clean = [
            ('CEN Auvergne-Rhône-Alpes', 'CEN Auvergne-Rhone-Alpes'),
            ('DREAL Auvergne-Rhône-Alpes', 'DREAL Auvergne-Rhone-Alpes'),
        ]
        for old_name, canonical_name in variations_to_clean:
            old_org = BibOrganismes.objects.filter(nom_organisme=old_name).first()
            if old_org:
                # Verifier si le nom canonique existe deja
                canonical_org = BibOrganismes.objects.filter(nom_organisme=canonical_name).first()
                if canonical_org:
                    # Les deux existent - fusionner: transferer les references vers le canonique
                    # et supprimer l'ancien
                    from apps.users.models import Role, CorOgSite
                    from apps.notifications.models import PendingUser, ValidationRequest
                    Role.objects.filter(id_organisme=old_org).update(id_organisme=canonical_org)
                    CorOgSite.objects.filter(uuid_og=old_org).update(uuid_og=canonical_org)
                    PendingUser.objects.filter(requested_organisme=old_org).update(requested_organisme=canonical_org)
                    ValidationRequest.objects.filter(requested_organisme=old_org).update(requested_organisme=canonical_org)
                    old_org.delete()
                    if self.verbosity >= 1:
                        self.stdout.write(f"  [FUSION] '{old_name}' -> '{canonical_name}'")
                else:
                    # Seul l'ancien existe - le renommer
                    old_org.nom_organisme = canonical_name
                    old_org.save()
                    if self.verbosity >= 1:
                        self.stdout.write(f"  [RENOMME] '{old_name}' -> '{canonical_name}'")

        organismes = []
        for org_data in organismes_data:
            org, created = BibOrganismes.objects.get_or_create(
                nom_organisme=org_data['nom_organisme'],
                defaults=org_data
            )
            organismes.append(org)
            if self.verbosity >= 2:
                status = "cree" if created else "existant"
                self.stdout.write(f"  [{status.upper()}] {org.nom_organisme}")

        self.stdout.write(self.style.SUCCESS(f'  {len(organismes)} organismes'))
        return organismes

    def _create_site_geometry(self, lon, lat, offset=0.05):
        """
        Cree une geometrie polygone et un point de reference pour un site.

        Args:
            lon: Longitude du centre (WGS84)
            lat: Latitude du centre (WGS84)
            offset: Taille approximative du polygone en degres (~5km par defaut)

        Returns:
            tuple: (MultiPolygon, Point)
        """
        # Creer un polygone rectangulaire autour du centre
        coords = [
            (lon - offset, lat - offset),
            (lon + offset, lat - offset),
            (lon + offset, lat + offset),
            (lon - offset, lat + offset),
            (lon - offset, lat - offset),  # Fermer le ring
        ]
        polygon = Polygon(coords, srid=4326)
        multipolygon = MultiPolygon(polygon, srid=4326)
        point = Point(lon, lat, srid=4326)

        return multipolygon, point

    def _create_sites(self, organismes):
        """Cree les sites de test avec geometries."""
        self.stdout.write('\n--- Creation des sites ---')

        # Recuperer les types de site par mnemonique (aligne sur fichiers SQL)
        type_rnn = Nomenclature.objects.filter(mnemonique='RNN').first()
        type_rnr = Nomenclature.objects.filter(mnemonique='RNR').first()
        type_pnr = Nomenclature.objects.filter(mnemonique='PNR').first()
        type_ens = Nomenclature.objects.filter(mnemonique='ENS').first()

        # Coordonnees reelles des sites naturels francais (lon, lat, offset)
        # Format: (longitude, latitude, offset_polygon)
        sites_coords = {
            'Reserve Naturelle de la Camargue': (4.63, 43.45, 0.15),
            'Reserve Naturelle des Aiguilles Rouges': (6.93, 45.98, 0.08),
            'Reserve Naturelle Regionale du Grand-Voyeux': (2.88, 49.02, 0.03),
            'Parc Naturel Regional du Vercors': (5.45, 44.95, 0.25),
            'Espace Naturel Sensible des Marais de Brouage': (-1.05, 45.87, 0.06),
            'Reserve Naturelle de Scandola': (8.55, 42.37, 0.05),
            'Reserve Naturelle du Lac de Remoray': (6.21, 46.77, 0.04),
        }

        sites_data = [
            {
                'nom_site': 'Reserve Naturelle de la Camargue',
                'id_local': 'RN13',
                'id_inpn': 'FR3600013',
                'id_type_site': type_rnn,
                'surf_off': 13117.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[0], organismes[4]]  # RNF + OFB
            },
            {
                'nom_site': 'Reserve Naturelle des Aiguilles Rouges',
                'id_local': 'RN1',
                'id_inpn': 'FR3600001',
                'id_type_site': type_rnn,
                'surf_off': 3279.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[0]]  # RNF
            },
            {
                'nom_site': 'Reserve Naturelle Regionale du Grand-Voyeux',
                'id_local': 'RNR145',
                'id_inpn': 'FR9300145',
                'id_type_site': type_rnr,
                'surf_off': 264.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[1]]  # CEN AURA
            },
            {
                'nom_site': 'Parc Naturel Regional du Vercors',
                'id_local': 'PNR38',
                'id_inpn': 'FR8000038',
                'id_type_site': type_pnr,
                'surf_off': 206000.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[1], organismes[2]]  # CEN AURA + DREAL
            },
            {
                'nom_site': 'Espace Naturel Sensible des Marais de Brouage',
                'id_local': 'ENS17',
                'id_inpn': 'FR5400017',
                'id_type_site': type_ens,
                'surf_off': 1250.0,
                'marin': True,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[2]]  # DREAL
            },
            {
                'nom_site': 'Reserve Naturelle de Scandola',
                'id_local': 'RN2A',
                'id_inpn': 'FR9300002',
                'id_type_site': type_rnn,
                'surf_off': 1919.0,
                'marin': True,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[3], organismes[4]]  # Parc Ecrins + OFB
            },
            {
                'nom_site': 'Reserve Naturelle du Lac de Remoray',
                'id_local': 'RN25',
                'id_inpn': 'FR3600025',
                'id_type_site': type_rnn,
                'surf_off': 430.0,
                'marin': False,
                'outre_mer': False,
                'active': True,
                'organismes': [organismes[0]]  # RNF
            },
        ]

        sites = []
        for site_data in sites_data:
            organismes_list = site_data.pop('organismes')
            site_name = site_data['nom_site']

            # Ajouter la geometrie si les coordonnees sont disponibles
            if site_name in sites_coords:
                lon, lat, offset = sites_coords[site_name]
                geom, geom_pt = self._create_site_geometry(lon, lat, offset)
                site_data['geom'] = geom
                site_data['geom_pt'] = geom_pt

            site, created = Site.objects.update_or_create(
                nom_site=site_data['nom_site'],
                defaults=site_data
            )

            if not created and self.verbosity >= 2:
                self.stdout.write(f"  [MISE A JOUR] {site_name}")

            sites.append(site)

            # Lier aux organismes (le premier de la liste est le gestionnaire principal)
            for i, org in enumerate(organismes_list):
                CorOgSite.objects.update_or_create(
                    id_site=site,
                    uuid_og=org,
                    defaults={'principal': i == 0}
                )

            if self.verbosity >= 2:
                status = "cree" if created else "existant"
                type_code = site.id_type_site.cd_nomenclature if site.id_type_site else 'N/A'
                principal_org = organismes_list[0].nom_organisme if organismes_list else 'N/A'
                self.stdout.write(f"  [{status.upper()}] {site.nom_site} ({type_code})")
                self.stdout.write(f"              Gestionnaire principal: {principal_org}")

        self.stdout.write(self.style.SUCCESS(f'  {len(sites)} sites'))
        return sites

    def _create_users(self, organismes, sites, groups):
        """Cree les utilisateurs de test avec differents roles."""
        self.stdout.write('\n--- Creation des utilisateurs ---')

        # Mettre a jour les superusers existants pour avoir role_level='super_admin'
        # Ceci corrige le probleme ou les superusers crees avant n'avaient pas role_level defini
        existing_superusers = Role.objects.filter(is_superuser=True, role_level='utilisateur')
        for su in existing_superusers:
            su.role_level = 'super_admin'
            su.save(update_fields=['role_level'])
            self.stdout.write(f"  [MISE A JOUR] {su.email}: role_level='super_admin'")

        users_data = [
            {
                'email': 'admin@test.fr',
                'nom_role': 'Admin',
                'prenom_role': 'Super',
                'identifiant': 'super_admin',
                'role_level': 'super_admin',
                'is_staff': True,
                'is_superuser': True,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Super Administrateurs'],
                'sites_referent': [sites[0]]  # Camargue
            },
            {
                'email': 'admin.rnf@test.fr',
                'nom_role': 'Dupont',
                'prenom_role': 'Marie',
                'identifiant': 'admin_rnf',
                'role_level': 'admin_og',
                'is_staff': True,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Administrateurs Organisme'],
                'sites_referent': [sites[0], sites[1]]  # Camargue, Aiguilles Rouges
            },
            {
                'email': 'admin.cen@test.fr',
                'nom_role': 'Martin',
                'prenom_role': 'Jean',
                'identifiant': 'admin_cen',
                'role_level': 'admin_og',
                'is_staff': True,
                'is_superuser': False,
                'id_organisme': organismes[1],  # CEN AURA
                'groups': ['Administrateurs Organisme'],
                'sites_referent': [sites[2], sites[3]]  # Grand-Voyeux, Vercors
            },
            {
                'email': 'referent.camargue@test.fr',
                'nom_role': 'Bernard',
                'prenom_role': 'Sophie',
                'identifiant': 'ref_camargue',
                'role_level': 'utilisateur',  # Sera referent via CorRoleSite
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Utilisateurs'],
                'sites_referent': [sites[0]]  # Camargue
            },
            {
                'email': 'referent.vercors@test.fr',
                'nom_role': 'Petit',
                'prenom_role': 'Lucas',
                'identifiant': 'ref_vercors',
                'role_level': 'utilisateur',  # Sera referent via CorRoleSite
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[1],  # CEN AURA
                'groups': ['Utilisateurs'],
                'sites_referent': [sites[3]]  # Vercors
            },
            {
                'email': 'user.rnf@test.fr',
                'nom_role': 'Durand',
                'prenom_role': 'Emma',
                'identifiant': 'user_rnf',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Utilisateurs'],
                'sites_referent': []
            },
            {
                'email': 'user.cen@test.fr',
                'nom_role': 'Leroy',
                'prenom_role': 'Thomas',
                'identifiant': 'user_cen',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[1],  # CEN AURA
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': True
            },
            # Utilisateurs inactifs (anciens collaborateurs)
            {
                'email': 'ancien.rnf@test.fr',
                'nom_role': 'Moreau',
                'prenom_role': 'Pierre',
                'identifiant': 'ancien_rnf',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': False  # Utilisateur inactif
            },
            {
                'email': 'ancien.cen@test.fr',
                'nom_role': 'Dubois',
                'prenom_role': 'Claire',
                'identifiant': 'ancien_cen',
                'role_level': 'admin_og',
                'is_staff': True,
                'is_superuser': False,
                'id_organisme': organismes[1],  # CEN AURA
                'groups': ['Administrateurs Organisme'],
                'sites_referent': [],
                'active': False  # Utilisateur inactif
            },
            {
                'email': 'stagiaire.dreal@test.fr',
                'nom_role': 'Robert',
                'prenom_role': 'Julie',
                'identifiant': 'stagiaire_dreal',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[2],  # DREAL
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': False  # Stagiaire parti
            },
            # Utilisateurs en attente de validation (inscrits mais pas encore valides)
            {
                'email': 'pending.rnf@test.fr',
                'nom_role': 'Girard',
                'prenom_role': 'Antoine',
                'identifiant': 'pending_rnf',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': True,
                'pending_validation': True  # En attente de validation
            },
            {
                'email': 'pending.cen@test.fr',
                'nom_role': 'Mercier',
                'prenom_role': 'Camille',
                'identifiant': 'pending_cen',
                'role_level': 'utilisateur',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[1],  # CEN AURA
                'groups': ['Utilisateurs'],
                'sites_referent': [],
                'active': True,
                'pending_validation': True  # En attente de validation
            },
        ]

        users = []
        for user_data in users_data:
            user_groups = user_data.pop('groups')
            sites_referent = user_data.pop('sites_referent')
            is_active = user_data.pop('active', True)  # Valeur par defaut: True
            is_pending = user_data.pop('pending_validation', False)

            user, created = Role.objects.update_or_create(
                email=user_data['email'],
                defaults={
                    'nom_role': user_data['nom_role'],
                    'prenom_role': user_data['prenom_role'],
                    'identifiant': user_data['identifiant'],
                    'role_level': user_data['role_level'],
                    'is_staff': user_data['is_staff'],
                    'is_superuser': user_data['is_superuser'],
                    'id_organisme': user_data['id_organisme'],
                    'active': is_active,
                    'pending_validation': is_pending,
                }
            )

            user.set_password(DEFAULT_PASSWORD)
            user.save()

            # Ajouter aux groupes
            for group_name in user_groups:
                if group_name in groups:
                    user.groups.add(groups[group_name])

            # Ajouter comme referent des sites
            for site in sites_referent:
                CorRoleSite.objects.get_or_create(
                    id_site=site,
                    id_role=user,
                    defaults={'referent': True, 'referent_valid': True, 'conservateur': False}
                )

            users.append(user)
            if self.verbosity >= 2:
                status = "cree" if created else "mis a jour"
                org_name = user_data['id_organisme'].nom_organisme if user_data['id_organisme'] else "N/A"
                self.stdout.write(f"  [{status.upper()}] {user.email} ({user_data['role_level']}) - {org_name}")

        self.stdout.write(self.style.SUCCESS(f'  {len(users)} utilisateurs'))
        return users

    def _create_plans(self, users, sites):
        """Cree les plans de gestion de test."""
        self.stdout.write('\n--- Creation des plans de gestion ---')

        # Recuperer les nomenclatures par mnemonique (aligne sur fichiers SQL)
        eval_int = Nomenclature.objects.filter(mnemonique='Intermediaire').first()
        eval_fin = Nomenclature.objects.filter(mnemonique='Finale').first()
        redac_gest = Nomenclature.objects.filter(mnemonique='OG').first()
        redac_be = Nomenclature.objects.filter(mnemonique='BE').first()

        # Recuperer l'admin pour la creation
        admin = users[0]

        plans_data = [
            {
                'nom': 'Plan de gestion 2020-2030 - Reserve de la Camargue',
                'annee_debut': 2020,
                'annee_fin': 2030,
                'statut': 'valide',
                'version': '2.0',
                'gestion_partagee': False,
                'ct88': True,
                'risque_incendie': True,
                'id_evaluation': eval_int,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Equipe Camargue',
                'commentaire': 'Plan de gestion valide pour la periode 2020-2030',
                'sites': [sites[0]],  # Camargue
                'referents': [users[3]]  # referent.camargue
            },
            {
                'nom': 'Plan de gestion 2018-2028 - Aiguilles Rouges',
                'annee_debut': 2018,
                'annee_fin': 2028,
                'statut': 'valide',
                'version': '1.1',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_be,
                'redacteur_nom': 'Bureau Natura 2000',
                'commentaire': 'Plan actuellement en cours de revision',
                'sites': [sites[1]],  # Aiguilles Rouges
                'referents': [users[1]]  # admin.rnf
            },
            {
                'nom': 'Plan de gestion 2022-2032 - Grand-Voyeux',
                'annee_debut': 2022,
                'annee_fin': 2032,
                'statut': 'draft',
                'version': '1.0',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': None,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'CEN Auvergne-Rhone-Alpes',
                'commentaire': 'Plan en cours de redaction',
                'sites': [sites[2]],  # Grand-Voyeux
                'referents': [users[2]]  # admin.cen
            },
            {
                'nom': 'Plan de gestion inter-sites Vercors-Ecrins 2021-2031',
                'annee_debut': 2021,
                'annee_fin': 2031,
                'statut': 'valide',
                'version': '1.0',
                'gestion_partagee': True,
                'ct88': True,
                'risque_incendie': True,
                'id_evaluation': eval_int,
                'id_redacteur_type': redac_be,
                'redacteur_nom': 'DREAL Auvergne-Rhone-Alpes',
                'commentaire': 'Plan de gestion partage entre le PNR du Vercors et le Parc des Ecrins',
                'sites': [sites[3], sites[5]],  # Vercors + Scandola
                'referents': [users[4]]  # referent.vercors
            },
            {
                'nom': 'Plan de gestion 2019-2029 - Marais de Brouage',
                'annee_debut': 2019,
                'annee_fin': 2029,
                'statut': 'archive',
                'version': '3.0',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'DREAL Nouvelle-Aquitaine',
                'commentaire': 'Plan archive - nouvelle version en preparation',
                'sites': [sites[4]],  # Marais de Brouage
                'referents': []
            },
            {
                'nom': 'Plan de gestion 2023-2033 - Lac de Remoray',
                'annee_debut': 2023,
                'annee_fin': 2033,
                'statut': 'draft',
                'version': '0.9',
                'gestion_partagee': False,
                'ct88': True,
                'risque_incendie': False,
                'id_evaluation': None,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Equipe Franche-Comte',
                'commentaire': 'Nouveau plan en cours de finalisation',
                'sites': [sites[6]],  # Lac de Remoray
                'referents': [users[1]]  # admin.rnf
            },
            # Plans de gestion archives (anciens plans remplaces)
            {
                'nom': 'Plan de gestion 2010-2020 - Camargue (ancien)',
                'annee_debut': 2010,
                'annee_fin': 2020,
                'statut': 'archive',
                'version': '1.5',
                'gestion_partagee': False,
                'ct88': True,
                'risque_incendie': True,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_gest,
                'redacteur_nom': 'RNF - Equipe Camargue',
                'commentaire': 'Ancien plan termine, remplace par le plan 2020-2030',
                'sites': [sites[0]],  # Camargue
                'referents': []
            },
            {
                'nom': 'Plan de gestion 2008-2018 - Aiguilles Rouges (ancien)',
                'annee_debut': 2008,
                'annee_fin': 2018,
                'statut': 'archive',
                'version': '2.0',
                'gestion_partagee': False,
                'ct88': False,
                'risque_incendie': False,
                'id_evaluation': eval_fin,
                'id_redacteur_type': redac_be,
                'redacteur_nom': 'Bureau Natura 2000',
                'commentaire': 'Plan archive suite a la mise en place du nouveau plan 2018-2028',
                'sites': [sites[1]],  # Aiguilles Rouges
                'referents': []
            },
        ]

        plans = []
        for plan_data in plans_data:
            plan_sites = plan_data.pop('sites')
            plan_referents = plan_data.pop('referents')

            plan, created = PlanGestion.objects.update_or_create(
                nom=plan_data['nom'],
                defaults={
                    **plan_data,
                    'id_utilisateur_ajout': admin,
                    'id_utilisateur_maj': admin
                }
            )

            # Lier aux sites
            for i, site in enumerate(plan_sites):
                CorSitePg.objects.get_or_create(
                    site=site,
                    plan_de_gestion=plan,
                    defaults={'rang': i + 1}
                )

            # Ajouter les referents
            plan.referents.set(plan_referents)

            plans.append(plan)
            if self.verbosity >= 2:
                status = "cree" if created else "mis a jour"
                sites_names = ", ".join([s.nom_site[:20] for s in plan_sites])
                self.stdout.write(f"  [{status.upper()}] {plan.nom[:50]}... ({plan.statut})")
                self.stdout.write(f"              Sites: {sites_names}")

        self.stdout.write(self.style.SUCCESS(f'  {len(plans)} plans de gestion'))
        return plans

    def _create_pending_users(self, organismes):
        """
        Cree les utilisateurs en attente d'inscription (PendingUser).

        Chaque PendingUser a sa propre ValidationRequest unique.
        Ces demandes peuvent etre validees par:
        - super_admin: toutes les demandes
        - admin_og: demandes pour leur organisme
        """
        self.stdout.write('\n--- Creation des utilisateurs en attente d\'inscription ---')

        # Corriger les demandes d'inscription approuvees sans requester lie
        # (utile si des demandes ont ete approuvees avant l'implementation de l'Option B)
        orphan_approved = ValidationRequest.objects.filter(
            request_type='user_registration',
            status='approved',
            requester__isnull=True
        )

        # Mapping emails de test -> organisme
        test_emails = {
            'nouveau.user1@test.fr': 'RNF',
            'nouveau.user2@test.fr': 'CEN Auvergne-Rhone-Alpes',
            'nouveau.user3@test.fr': 'DREAL Auvergne-Rhone-Alpes',
        }

        for vr in orphan_approved:
            # Essayer de trouver l'utilisateur correspondant
            for email, org_name in test_emails.items():
                user = Role.objects.filter(email__iexact=email).first()
                if user and vr.requested_organisme:
                    if vr.requested_organisme.nom_organisme == org_name:
                        vr.requester = user
                        vr.save(update_fields=['requester'])
                        self.stdout.write(f"  [FIX] Requester lie pour validation #{vr.id}: {user}")
                        break

        pending_users_data = [
            {
                'email': 'nouveau.user1@test.fr',
                'password': DEFAULT_PASSWORD,
                'nom_role': 'Lefebvre',
                'prenom_role': 'Marc',
                'requested_organisme': organismes[0],  # RNF
                'justification': 'Je suis naturaliste et je souhaite contribuer aux plans de gestion de RNF.',
            },
            {
                'email': 'nouveau.user2@test.fr',
                'password': DEFAULT_PASSWORD,
                'nom_role': 'Simon',
                'prenom_role': 'Lea',
                'requested_organisme': organismes[1],  # CEN AURA
                'justification': 'Nouvelle recrue au CEN AURA, en attente de validation par mon administrateur.',
            },
            {
                'email': 'nouveau.user3@test.fr',
                'password': DEFAULT_PASSWORD,
                'nom_role': 'Michel',
                'prenom_role': 'Paul',
                'requested_organisme': organismes[2],  # DREAL
                'justification': 'Agent DREAL affecte au suivi des espaces naturels.',
            },
        ]

        pending_users = []
        for pu_data in pending_users_data:
            # Verifier si le PendingUser existe deja
            existing_pending = PendingUser.objects.filter(email=pu_data['email']).first()

            if existing_pending:
                pending_users.append(existing_pending)
                if self.verbosity >= 2:
                    org_name = pu_data['requested_organisme'].nom_organisme
                    self.stdout.write(f"  [EXISTANT] {pu_data['email']} -> {org_name}")
                continue

            # Creer une ValidationRequest unique pour cette inscription
            # Note: Le super_admin peut valider toutes les demandes
            #       L'admin_og peut valider les demandes pour son organisme
            validation_request = ValidationRequest.objects.create(
                request_type='user_registration',
                requester=None,  # Pas de requester pour une inscription
                requested_organisme=pu_data['requested_organisme'],
                status='pending',
                justification=pu_data['justification'],
                expires_at=timezone.now() + timedelta(days=7),
            )

            # Creer le PendingUser lie a cette ValidationRequest
            pending_user = PendingUser.objects.create(
                email=pu_data['email'],
                password_hash=make_password(pu_data['password']),
                nom_role=pu_data['nom_role'],
                prenom_role=pu_data['prenom_role'],
                requested_organisme=pu_data['requested_organisme'],
                justification=pu_data['justification'],
                validation_request=validation_request,
                ip_address='127.0.0.1',
                user_agent='Mozilla/5.0 (Test Data)',
            )
            pending_users.append(pending_user)

            if self.verbosity >= 2:
                org_name = pu_data['requested_organisme'].nom_organisme
                self.stdout.write(f"  [CREE] {pu_data['email']} -> {org_name}")
                self.stdout.write(f"         ValidationRequest #{validation_request.id} (pending)")

        self.stdout.write(self.style.SUCCESS(f'  {len(pending_users)} utilisateurs en attente'))
        return pending_users

    def _create_validation_requests(self, users, sites, plans, organismes):
        """
        Cree des demandes de validation de test.

        Hierarchie des permissions pour la validation:
        ================================================
        super_admin > admin_og > referent > utilisateur

        - super_admin: peut valider TOUTES les demandes
        - admin_og: peut valider les demandes liees a son organisme
          (inscriptions, acces site/plan de son organisme)
        - referent: peut valider les demandes sur ses sites
        - utilisateur: ne peut pas valider

        Types de demandes et qui peut les valider:
        - user_registration: super_admin, admin_og de l'organisme demande
        - site_access: super_admin, admin_og gestionnaire, referent du site
        - plan_access: super_admin, admin_og, referent du plan
        - referent_validation: super_admin, admin_og gestionnaire
        - admin_deactivation: super_admin uniquement
        """
        self.stdout.write('\n--- Creation des demandes de validation ---')

        # Utilisateurs pour les demandes
        admin = users[0]  # super_admin
        admin_rnf = users[1]  # admin.rnf@test.fr - Admin Organisme RNF
        admin_cen = users[2]  # admin.cen@test.fr - Admin Organisme CEN AURA
        referent_camargue = users[3]  # referent site Camargue (RNF)
        referent_vercors = users[4]  # referent site Vercors (CEN AURA)
        user_rnf = users[5]  # utilisateur RNF
        user_cen = users[6]  # utilisateur CEN AURA

        validation_requests_data = [
            # =====================================================
            # DEMANDES D'ACCES SITE
            # Validable par: super_admin, admin_og gestionnaire, referent du site
            # =====================================================

            # Demande d'acces site - en attente
            # Validable par: admin@test.fr (super_admin), admin.rnf@test.fr (admin_og RNF)
            {
                'request_type': 'site_access',
                'requester': user_rnf,
                'target_site': sites[1],  # Aiguilles Rouges (gestionnaire: RNF)
                'status': 'pending',
                'justification': 'Je souhaite participer au suivi des especes vegetales de la reserve.',
            },
            # Demande d'acces site - approuvee par admin_og il y a 3 jours
            {
                'request_type': 'site_access',
                'requester': user_cen,
                'target_site': sites[3],  # Vercors (gestionnaire: CEN AURA)
                'status': 'approved',
                'justification': 'Integration equipe Vercors.',
                'validator': admin_cen,  # admin_og CEN AURA peut valider
                'validation_comment': 'Bienvenue dans l\'equipe!',
                'validated_at': timezone.now() - timedelta(days=3),
            },

            # =====================================================
            # DEMANDES D'ACCES PLAN
            # Validable par: super_admin, admin_og, referent du plan
            # =====================================================

            # Demande d'acces plan - en attente
            # Validable par: admin@test.fr, admin.rnf@test.fr, referent.camargue@test.fr
            {
                'request_type': 'plan_access',
                'requester': user_rnf,
                'target_plan': plans[0],  # Plan Camargue (RNF)
                'status': 'pending',
                'justification': 'Besoin d\'acces pour la redaction du bilan annuel.',
            },
            # Demande d'acces plan - rejetee par admin_og il y a 1 semaine
            {
                'request_type': 'plan_access',
                'requester': user_cen,
                'target_plan': plans[1],  # Plan Aiguilles Rouges (RNF)
                'status': 'rejected',
                'justification': 'Je voudrais consulter ce plan pour m\'inspirer.',
                'validator': admin_rnf,  # admin_og RNF peut rejeter
                'validation_comment': 'Ce plan est reserve aux membres de RNF.',
                'validated_at': timezone.now() - timedelta(days=7),
            },

            # =====================================================
            # VALIDATION REFERENT
            # Validable par: super_admin, admin_og gestionnaire du site
            # =====================================================

            # Demande referent - en attente
            # Validable par: admin@test.fr, admin.rnf@test.fr (RNF gere Lac de Remoray)
            {
                'request_type': 'referent_validation',
                'requester': user_rnf,
                'target_site': sites[6],  # Lac de Remoray (gestionnaire: RNF)
                'status': 'pending',
                'justification': 'Je souhaite devenir referent pour ce site proche de mon domicile.',
            },
            # Demande referent - approuvee par super_admin il y a 2 semaines
            {
                'request_type': 'referent_validation',
                'requester': referent_vercors,
                'target_site': sites[4],  # Marais de Brouage (gestionnaire: DREAL)
                'status': 'approved',
                'justification': 'Expertise zone humide.',
                'validator': admin,  # super_admin peut tout valider
                'validation_comment': 'Referent valide.',
                'validated_at': timezone.now() - timedelta(days=14),
            },

            # =====================================================
            # DESACTIVATION ADMIN
            # Validable par: super_admin UNIQUEMENT
            # =====================================================

            # Demande desactivation admin_og - en attente
            # Validable par: admin@test.fr uniquement
            {
                'request_type': 'admin_deactivation',
                'requester': admin,  # Seul super_admin peut initier
                'target_user': users[8],  # ancien.cen (admin_og CEN AURA inactif)
                'requested_organisme': organismes[1],  # CEN AURA
                'status': 'pending',
                'justification': 'Depart de l\'organisation, besoin de transferer les responsabilites.',
            },

            # =====================================================
            # DEMANDES D'ACCES MODULE
            # Validable par: super_admin UNIQUEMENT
            # =====================================================

            # Demande acces module zonages - en attente
            # Validable par: admin@test.fr uniquement
            {
                'request_type': 'module_access',
                'requester': user_cen,
                'target_module': 'zonages',
                'status': 'pending',
                'justification': 'Je travaille sur les zonages reglementaires pour le Vercors.',
            },
            # Demande acces module zonages - approuvee
            # user_rnf a maintenant acces au module zonages
            {
                'request_type': 'module_access',
                'requester': user_rnf,
                'target_module': 'zonages',
                'status': 'approved',
                'justification': 'Besoin d\'acces pour le suivi des zonages de la Camargue.',
                'validator': admin,
                'validation_comment': 'Acces accorde pour le projet Camargue.',
                'validated_at': timezone.now() - timedelta(days=5),
            },
            # Demande acces module zonages - refusee
            {
                'request_type': 'module_access',
                'requester': referent_vercors,
                'target_module': 'zonages',
                'status': 'rejected',
                'justification': 'Je souhaite consulter les zonages.',
                'validator': admin,
                'validation_comment': 'Acces refuse: formation requise avant utilisation de ce module.',
                'validated_at': timezone.now() - timedelta(days=10),
            },

            # =====================================================
            # CREATION DE SITE
            # Validable par: super_admin, admin_og
            # =====================================================

            # Demande creation site - en attente
            # Validable par: admin@test.fr, admin.cen@test.fr
            {
                'request_type': 'site_creation',
                'requester': user_cen,
                'status': 'pending',
                'justification': 'Je souhaite creer un nouveau site pour la Tourbiere du Mont Bar dans le Puy-de-Dome.',
            },
            # Demande creation site - approuvee il y a 1 mois
            {
                'request_type': 'site_creation',
                'requester': referent_vercors,
                'status': 'approved',
                'justification': 'Nouveau site ENS dans les Hautes-Alpes.',
                'validator': admin,
                'validation_comment': 'Site cree avec succes. Bienvenue!',
                'validated_at': timezone.now() - timedelta(days=30),
            },

            # =====================================================
            # LIEN SITE-ORGANISME
            # Validable par: super_admin, admin_og gestionnaire du site
            # =====================================================

            # Demande lien site-organisme - en attente
            # Validable par: admin@test.fr, admin.rnf@test.fr (RNF gere Scandola)
            {
                'request_type': 'site_org_link',
                'requester': admin_cen,
                'target_site': sites[5],  # Scandola (gestionnaire: RNF)
                'requested_organisme': organismes[1],  # CEN AURA souhaite etre lie
                'status': 'pending',
                'justification': 'Notre organisme participe a un projet de suivi inter-regional.',
            },
            # Demande lien site-organisme - approuvee il y a 2 semaines
            {
                'request_type': 'site_org_link',
                'requester': admin_rnf,
                'target_site': sites[3],  # Vercors (gestionnaire: CEN AURA)
                'requested_organisme': organismes[0],  # RNF souhaite etre lie
                'status': 'approved',
                'justification': 'Partenariat pour le suivi de la faune alpine.',
                'validator': admin_cen,
                'validation_comment': 'Partenariat valide. Bienvenue!',
                'validated_at': timezone.now() - timedelta(days=14),
            },

            # =====================================================
            # INVITATION ORGANISME VERS SITE
            # Validable par: admin_og de l'organisme invite
            # =====================================================

            # Invitation organisme - en attente
            # Validable par: admin.cen@test.fr (admin CEN AURA invite)
            {
                'request_type': 'invite_org_to_site',
                'requester': referent_camargue,  # Referent du site Camargue invite
                'target_site': sites[0],  # Camargue
                'requested_organisme': organismes[1],  # CEN AURA est invite
                'status': 'pending',
                'justification': 'Nous invitons CEN AURA a participer au projet de suivi des flamants roses.',
            },
            # Invitation organisme - acceptee il y a 3 semaines
            {
                'request_type': 'invite_org_to_site',
                'requester': admin_rnf,
                'target_site': sites[1],  # Aiguilles Rouges
                'requested_organisme': organismes[3],  # Parc Ecrins
                'status': 'approved',
                'justification': 'Invitation pour collaboration scientifique.',
                'validator': admin,  # super_admin peut aussi valider
                'validation_comment': 'Collaboration acceptee.',
                'validated_at': timezone.now() - timedelta(days=21),
            },

            # =====================================================
            # INVITATION UTILISATEUR VERS SITE
            # Validable par: l'utilisateur invite lui-meme
            # =====================================================

            # Invitation utilisateur - en attente
            # Validable par: user.cen@test.fr (l'utilisateur invite)
            {
                'request_type': 'invite_user_to_site',
                'requester': referent_camargue,  # Referent invite un utilisateur
                'target_site': sites[0],  # Camargue
                'target_user': user_cen,  # L'utilisateur CEN est invite
                'status': 'pending',
                'justification': 'Nous vous invitons a rejoindre l\'equipe du site Camargue pour le projet biodiversite.',
            },
            # Invitation utilisateur - acceptee il y a 5 jours
            {
                'request_type': 'invite_user_to_site',
                'requester': admin_rnf,
                'target_site': sites[6],  # Lac de Remoray
                'target_user': user_rnf,
                'status': 'approved',
                'justification': 'Invitation a rejoindre l\'equipe du Lac de Remoray.',
                'validator': user_rnf,  # L'utilisateur invite accepte lui-meme
                'validation_comment': 'J\'accepte avec plaisir de rejoindre cette equipe!',
                'validated_at': timezone.now() - timedelta(days=5),
            },
            # Invitation utilisateur - refusee il y a 1 semaine
            {
                'request_type': 'invite_user_to_site',
                'requester': referent_vercors,
                'target_site': sites[3],  # Vercors
                'target_user': user_rnf,
                'status': 'rejected',
                'justification': 'Invitation a participer au suivi floristique.',
                'validator': user_rnf,  # L'utilisateur decline
                'validation_comment': 'Merci pour l\'invitation mais je ne suis pas disponible actuellement.',
                'validated_at': timezone.now() - timedelta(days=7),
            },
        ]

        validation_requests = []
        for vr_data in validation_requests_data:
            validator = vr_data.pop('validator', None)
            validation_comment = vr_data.pop('validation_comment', None)
            validated_at = vr_data.pop('validated_at', None)

            # Si un validateur est fourni mais pas de date, utiliser maintenant
            if validator and not validated_at:
                validated_at = timezone.now()

            vr, created = ValidationRequest.objects.get_or_create(
                request_type=vr_data['request_type'],
                requester=vr_data.get('requester'),
                target_site=vr_data.get('target_site'),
                target_plan=vr_data.get('target_plan'),
                target_user=vr_data.get('target_user'),
                target_module=vr_data.get('target_module'),
                defaults={
                    'status': vr_data['status'],
                    'justification': vr_data.get('justification'),
                    'requested_organisme': vr_data.get('requested_organisme'),
                    'validator': validator,
                    'validation_comment': validation_comment,
                    'validated_at': validated_at,
                    'expires_at': timezone.now() + timedelta(days=14) if vr_data['status'] == 'pending' else None,
                }
            )
            validation_requests.append(vr)

            if self.verbosity >= 2:
                status_str = "cree" if created else "existant"
                validated_info = ""
                if validated_at:
                    validated_info = f" (valide le {validated_at.strftime('%d/%m/%Y')})"
                self.stdout.write(f"  [{status_str.upper()}] {vr.request_type} - {vr.status}{validated_info}")

        self.stdout.write(self.style.SUCCESS(f'  {len(validation_requests)} demandes de validation'))
        return validation_requests

    def _create_notifications(self, users, sites, plans, validation_requests, organismes):
        """Cree des notifications de test."""
        self.stdout.write('\n--- Creation des notifications ---')

        # Utilisateurs cibles
        admin = users[0]  # super_admin
        admin_rnf = users[1]  # admin.rnf
        admin_cen = users[2]  # admin.cen
        referent_camargue = users[3]
        referent_vercors = users[4]
        user_rnf = users[5]
        user_cen = users[6]

        notifications_data = [
            # Notifications pour admin_rnf (Admin Organisme RNF)
            {
                'recipient': admin_rnf,
                'notification_type': 'validation_request',
                'title': 'Nouvelle demande d\'inscription',
                'message': 'Marc Lefebvre souhaite rejoindre votre organisme RNF. Veuillez examiner sa demande.',
                'priority': 'high',
                'action_url': '/administration/validations',
                'read': False,
            },
            {
                'recipient': admin_rnf,
                'notification_type': 'validation_request',
                'title': 'Demande d\'acces au plan Camargue',
                'message': 'Emma Durand demande l\'acces au plan de gestion 2020-2030 de la Camargue.',
                'priority': 'medium',
                'related_user': user_rnf,
                'related_plan': plans[0],
                'action_url': '/administration/validations',
                'read': False,
            },
            {
                'recipient': admin_rnf,
                'notification_type': 'info',
                'title': 'Plan de gestion mis a jour',
                'message': 'Le plan Aiguilles Rouges a ete modifie par l\'equipe.',
                'priority': 'low',
                'related_plan': plans[1],
                'read': True,
            },
            {
                'recipient': admin_rnf,
                'notification_type': 'system_alert',
                'title': 'Maintenance prevue',
                'message': 'Une maintenance est prevue le 15 janvier 2026 de 2h a 4h.',
                'priority': 'medium',
                'read': True,
            },

            # Notifications pour admin_cen (Admin Organisme CEN AURA)
            {
                'recipient': admin_cen,
                'notification_type': 'validation_request',
                'title': 'Nouvelle demande d\'inscription',
                'message': 'Lea Simon souhaite rejoindre votre organisme CEN AURA.',
                'priority': 'high',
                'action_url': '/administration/validations',
                'read': False,
            },
            {
                'recipient': admin_cen,
                'notification_type': 'validation_approved',
                'title': 'Demande approuvee',
                'message': 'L\'acces de Thomas Leroy au site du Vercors a ete approuve.',
                'priority': 'low',
                'related_user': user_cen,
                'related_site': sites[3],
                'read': True,
            },
            {
                'recipient': admin_cen,
                'notification_type': 'organisme_no_admin',
                'title': 'Attention: Admin manquant',
                'message': 'Suite au depart de Claire Dubois, votre organisme n\'a plus qu\'un seul administrateur.',
                'priority': 'critical',
                'related_organisme': organismes[1],
                'read': False,
            },

            # Notifications pour referent_camargue
            {
                'recipient': referent_camargue,
                'notification_type': 'user_associated_site',
                'title': 'Nouvel utilisateur sur votre site',
                'message': 'Un nouvel utilisateur a ete ajoute au site de la Camargue.',
                'priority': 'medium',
                'related_site': sites[0],
                'read': False,
            },
            {
                'recipient': referent_camargue,
                'notification_type': 'info',
                'title': 'Rappel: Bilan annuel',
                'message': 'Le bilan annuel du plan de gestion doit etre soumis avant le 31 mars.',
                'priority': 'high',
                'related_plan': plans[0],
                'read': False,
            },

            # Notifications pour referent_vercors
            {
                'recipient': referent_vercors,
                'notification_type': 'validation_approved',
                'title': 'Vous etes referent!',
                'message': 'Votre demande pour devenir referent du Marais de Brouage a ete approuvee.',
                'priority': 'high',
                'related_site': sites[4],
                'read': True,
            },

            # Notifications pour user_rnf
            {
                'recipient': user_rnf,
                'notification_type': 'info',
                'title': 'Bienvenue!',
                'message': 'Bienvenue sur la plateforme de gestion des plans. N\'hesitez pas a explorer.',
                'priority': 'low',
                'read': True,
            },
            {
                'recipient': user_rnf,
                'notification_type': 'validation_rejected',
                'title': 'Demande refusee',
                'message': 'Votre demande d\'acces au plan Aiguilles Rouges a ete refusee. Contactez votre administrateur.',
                'priority': 'medium',
                'related_plan': plans[1],
                'read': False,
            },

            # Notifications pour user_cen
            {
                'recipient': user_cen,
                'notification_type': 'user_associated_plan',
                'title': 'Acces accorde',
                'message': 'Vous avez maintenant acces au plan de gestion du Grand-Voyeux.',
                'priority': 'medium',
                'related_plan': plans[2],
                'read': True,
            },

            # Notifications pour super_admin
            {
                'recipient': admin,
                'notification_type': 'system_alert',
                'title': 'Rapport hebdomadaire',
                'message': '5 nouvelles inscriptions cette semaine. 3 plans mis a jour.',
                'priority': 'low',
                'read': True,
            },
            {
                'recipient': admin,
                'notification_type': 'site_orphaned',
                'title': 'Site sans gestionnaire',
                'message': 'Le site de Scandola n\'a plus d\'utilisateur referent assigne.',
                'priority': 'critical',
                'related_site': sites[5],
                'read': False,
            },

            # Notifications de type 'welcome' (bienvenue apres inscription)
            {
                'recipient': user_cen,
                'notification_type': 'welcome',
                'title': 'Bienvenue sur CICADA!',
                'message': 'Votre compte a ete active. Vous pouvez maintenant acceder a toutes les fonctionnalites de la plateforme.',
                'priority': 'medium',
                'read': True,
            },

            # Notifications de type 'user_removed_site' (retrait d'un site)
            {
                'recipient': user_rnf,
                'notification_type': 'user_removed_site',
                'title': 'Acces retire',
                'message': 'Votre acces au site du Lac de Remoray a ete retire par l\'administrateur.',
                'priority': 'medium',
                'related_site': sites[6],
                'read': False,
            },

            # Notifications de type 'user_removed_plan' (retrait d'un plan)
            {
                'recipient': referent_vercors,
                'notification_type': 'user_removed_plan',
                'title': 'Retrait du plan de gestion',
                'message': 'Vous n\'etes plus referent du plan de gestion 2018-2028 des Aiguilles Rouges.',
                'priority': 'medium',
                'related_plan': plans[1],
                'read': True,
            },

            # Notifications de type 'account_deactivated' (compte desactive)
            {
                'recipient': admin_rnf,
                'notification_type': 'account_deactivated',
                'title': 'Compte utilisateur desactive',
                'message': 'Le compte de Jean Martin (ancien.rnf@test.fr) a ete desactive suite a son depart.',
                'priority': 'high',
                'read': True,
            },

            # Notifications de type 'account_activated' (compte reactive)
            {
                'recipient': admin_cen,
                'notification_type': 'account_activated',
                'title': 'Compte utilisateur reactive',
                'message': 'Le compte de Marie Dupont a ete reactive apres verification de son identite.',
                'priority': 'medium',
                'read': False,
            },
        ]

        notifications = []
        for notif_data in notifications_data:
            is_read = notif_data.pop('read', False)

            notif, created = Notification.objects.get_or_create(
                recipient=notif_data['recipient'],
                notification_type=notif_data['notification_type'],
                title=notif_data['title'],
                defaults={
                    'message': notif_data['message'],
                    'priority': notif_data['priority'],
                    'related_user': notif_data.get('related_user'),
                    'related_site': notif_data.get('related_site'),
                    'related_plan': notif_data.get('related_plan'),
                    'related_organisme': notif_data.get('related_organisme'),
                    'action_url': notif_data.get('action_url'),
                    'read': is_read,
                    'read_at': timezone.now() if is_read else None,
                    'expires_at': timezone.now() + timedelta(days=30),
                }
            )
            notifications.append(notif)

            if self.verbosity >= 2:
                status = "cree" if created else "existant"
                read_status = "[LU]" if is_read else "[NON LU]"
                self.stdout.write(f"  [{status.upper()}] {notif.notification_type} -> {notif.recipient.email} {read_status}")

        self.stdout.write(self.style.SUCCESS(f'  {len(notifications)} notifications'))
        return notifications

    def _create_error_logs(self, users):
        """
        Cree des logs d'erreur de test.

        Cree 8 logs avec differents niveaux (WARNING, ERROR, CRITICAL),
        certains acquittes, certains non, avec des dates variees.
        """
        self.stdout.write('\n--- Creation des logs d\'erreur ---')

        now = timezone.now()
        # users est une liste avec l'ordre defini dans _create_users:
        # 0: super_admin, 1: admin_rnf, 2: admin_cen, 3: ref_camargue,
        # 4: ref_vercors, 5: user_rnf, 6: user_cen, 7+: inactifs
        admin = users[0]  # super_admin
        admin_rnf = users[1]  # admin.rnf@test.fr
        user_rnf = users[5]  # user.rnf@test.fr
        user_cen = users[6]  # user.cen@test.fr

        error_logs_data = [
            # WARNING - non acquitte, recent
            {
                'level': 'WARNING',
                'message': 'Tentative de connexion avec un token expire',
                'logger_name': 'apps.authentication.views',
                'correlation_id': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
                'user': user_rnf,
                'path': '/api/auth/me/',
                'method': 'GET',
                'exception_type': None,
                'stack_trace': None,
                'context': {'token_expired_at': '2024-01-15T10:30:00Z', 'user_agent': 'Mozilla/5.0'},
                'acknowledged': False,
                'acknowledged_by': None,
                'acknowledged_at': None,
                'created_at': now - timedelta(hours=2),
            },
            # WARNING - acquitte
            {
                'level': 'WARNING',
                'message': 'Rate limit atteint pour l\'utilisateur',
                'logger_name': 'apps.core.middleware.throttling',
                'correlation_id': 'b2c3d4e5-f6a7-8901-bcde-f23456789012',
                'user': user_cen,
                'path': '/api/plans/',
                'method': 'GET',
                'exception_type': None,
                'stack_trace': None,
                'context': {'requests_count': 150, 'limit': 100, 'window': '1h'},
                'acknowledged': True,
                'acknowledged_by': admin,
                'acknowledged_at': now - timedelta(days=2),
                'created_at': now - timedelta(days=3),
            },
            # WARNING - non acquitte
            {
                'level': 'WARNING',
                'message': 'Fichier temporaire non supprime apres upload',
                'logger_name': 'apps.plans.views',
                'correlation_id': 'c3d4e5f6-a7b8-9012-cdef-345678901234',
                'user': admin_rnf,
                'path': '/api/plans/files/upload/',
                'method': 'POST',
                'exception_type': None,
                'stack_trace': None,
                'context': {'temp_file': '/tmp/upload_xyz123.pdf', 'size_bytes': 2456789},
                'acknowledged': False,
                'acknowledged_by': None,
                'acknowledged_at': None,
                'created_at': now - timedelta(days=1),
            },
            # ERROR - non acquitte, recent
            {
                'level': 'ERROR',
                'message': 'Erreur de validation lors de la creation du plan de gestion',
                'logger_name': 'apps.plans.serializers',
                'correlation_id': 'd4e5f6a7-b8c9-0123-defa-456789012345',
                'user': user_rnf,
                'path': '/api/plans/plans/',
                'method': 'POST',
                'exception_type': 'ValidationError',
                'stack_trace': '''Traceback (most recent call last):
  File "/app/apps/plans/views.py", line 145, in create
    serializer.is_valid(raise_exception=True)
  File "/usr/local/lib/python3.11/site-packages/rest_framework/serializers.py", line 235, in is_valid
    raise ValidationError(self.errors)
rest_framework.exceptions.ValidationError: {'date_fin': ['La date de fin doit etre superieure a la date de debut.']}''',
                'context': {'plan_data': {'nom': 'Plan test', 'date_debut': '2025-01-01', 'date_fin': '2024-01-01'}},
                'acknowledged': False,
                'acknowledged_by': None,
                'acknowledged_at': None,
                'created_at': now - timedelta(hours=6),
            },
            # ERROR - acquitte
            {
                'level': 'ERROR',
                'message': 'Impossible de generer le PDF du plan de gestion',
                'logger_name': 'apps.plans.pdf_generator',
                'correlation_id': 'e5f6a7b8-c9d0-1234-efab-567890123456',
                'user': admin_rnf,
                'path': '/api/plans/plans/15/export-pdf/',
                'method': 'GET',
                'exception_type': 'PDFGenerationError',
                'stack_trace': '''Traceback (most recent call last):
  File "/app/apps/plans/pdf_generator.py", line 89, in generate
    self._render_template()
  File "/app/apps/plans/pdf_generator.py", line 156, in _render_template
    raise PDFGenerationError("Template rendering failed")
apps.plans.exceptions.PDFGenerationError: Template rendering failed''',
                'context': {'plan_id': 15, 'template': 'plan_gestion_v2.html'},
                'acknowledged': True,
                'acknowledged_by': admin,
                'acknowledged_at': now - timedelta(days=1),
                'created_at': now - timedelta(days=2),
            },
            # ERROR - acquitte
            {
                'level': 'ERROR',
                'message': 'Timeout lors de la connexion au service externe INPN',
                'logger_name': 'apps.core.services.inpn',
                'correlation_id': 'f6a7b8c9-d0e1-2345-fabc-678901234567',
                'user': None,
                'path': '/api/sites/sync-inpn/',
                'method': 'POST',
                'exception_type': 'requests.exceptions.Timeout',
                'stack_trace': '''Traceback (most recent call last):
  File "/app/apps/core/services/inpn.py", line 45, in sync_sites
    response = requests.get(url, timeout=30)
  File "/usr/local/lib/python3.11/site-packages/requests/api.py", line 73, in get
    return request('get', url, **kwargs)
requests.exceptions.Timeout: HTTPSConnectionPool: Read timed out.''',
                'context': {'service_url': 'https://inpn.mnhn.fr/api/v1/sites', 'timeout': 30},
                'acknowledged': True,
                'acknowledged_by': admin,
                'acknowledged_at': now - timedelta(days=4),
                'created_at': now - timedelta(days=5),
            },
            # CRITICAL - non acquitte
            {
                'level': 'CRITICAL',
                'message': 'Echec de la connexion a la base de donnees',
                'logger_name': 'django.db.backends',
                'correlation_id': 'a7b8c9d0-e1f2-3456-abcd-789012345678',
                'user': None,
                'path': None,
                'method': None,
                'exception_type': 'psycopg2.OperationalError',
                'stack_trace': '''Traceback (most recent call last):
  File "/usr/local/lib/python3.11/site-packages/django/db/backends/base/base.py", line 289, in ensure_connection
    self.connect()
  File "/usr/local/lib/python3.11/site-packages/django/db/backends/base/base.py", line 270, in connect
    self.connection = self.get_new_connection(conn_params)
psycopg2.OperationalError: could not connect to server: Connection refused
    Is the server running on host "db" (172.18.0.2) and accepting TCP/IP connections on port 5432?''',
                'context': {'host': 'db', 'port': 5432, 'database': 'cicada'},
                'acknowledged': False,
                'acknowledged_by': None,
                'acknowledged_at': None,
                'created_at': now - timedelta(days=1, hours=5),
            },
            # CRITICAL - acquitte
            {
                'level': 'CRITICAL',
                'message': 'Espace disque insuffisant pour le stockage des fichiers',
                'logger_name': 'apps.core.storage',
                'correlation_id': 'b8c9d0e1-f2a3-4567-bcde-890123456789',
                'user': admin_rnf,
                'path': '/api/plans/files/upload/',
                'method': 'POST',
                'exception_type': 'OSError',
                'stack_trace': '''Traceback (most recent call last):
  File "/app/apps/core/storage.py", line 78, in save
    self._check_disk_space()
  File "/app/apps/core/storage.py", line 92, in _check_disk_space
    raise OSError("Insufficient disk space")
OSError: [Errno 28] No space left on device: '/app/media/plans/files/'
Disk usage: 98.5% (available: 512MB, required: 2GB)''',
                'context': {'disk_usage_percent': 98.5, 'available_mb': 512, 'required_mb': 2048},
                'acknowledged': True,
                'acknowledged_by': admin,
                'acknowledged_at': now - timedelta(days=6),
                'created_at': now - timedelta(days=7),
            },
        ]

        error_logs = []
        for log_data in error_logs_data:
            # Extraire created_at pour le definir manuellement
            created_at = log_data.pop('created_at')

            log = ErrorLog.objects.create(**log_data)
            # Mettre a jour created_at manuellement (auto_now_add empeche de le definir a la creation)
            ErrorLog.objects.filter(pk=log.pk).update(created_at=created_at)
            log.refresh_from_db()

            error_logs.append(log)

            if self.verbosity >= 2:
                ack_status = "[ACK]" if log.acknowledged else "[NON ACK]"
                self.stdout.write(f"  [CREE] {log.level} - {log.message[:50]}... {ack_status}")

        self.stdout.write(self.style.SUCCESS(f'  {len(error_logs)} logs d\'erreur'))
        return error_logs

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

        self.stdout.write(f'\n  Modules:              {Module.objects.count()}')
        self.stdout.write(f'  Organismes:           {BibOrganismes.objects.count()}')
        self.stdout.write(f'  Sites:                {Site.objects.count()}')
        self.stdout.write(f'  Utilisateurs:         {Role.objects.count()} ({users_actifs} actifs, {users_pending} en attente, {users_inactifs} inactifs)')
        self.stdout.write(f'  Plans de gestion:     {PlanGestion.objects.count()} ({plans_actifs} actifs, {plans_archives} archives)')
        self.stdout.write(f'  Groupes Django:       {Group.objects.count()}')
        self.stdout.write(f'  Nomenclatures:        {Nomenclature.objects.count()}')
        self.stdout.write(f'  Inscriptions attente: {pending_users_count}')
        self.stdout.write(f'  Validations:          {ValidationRequest.objects.count()} ({validation_requests_pending} en attente)')
        self.stdout.write(f'  Notifications:        {Notification.objects.count()} ({notifications_unread} non lues)')
        error_logs_unack = ErrorLog.objects.filter(acknowledged=False).count()
        self.stdout.write(f'  Logs d\'erreur:        {ErrorLog.objects.count()} ({error_logs_unack} non acquittes)')

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
        self.stdout.write('INSCRIPTIONS EN ATTENTE (PendingUser)')
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
    - referent.vercors@test.fr:   1 notification  (0 non lue)
    - user.rnf@test.fr:           2 notifications (1 non lue)
    - user.cen@test.fr:           1 notification  (0 non lue)
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
