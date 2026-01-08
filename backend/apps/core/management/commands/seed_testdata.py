"""
Commande Django pour creer des donnees de test.

Usage:
    python manage.py seed_testdata           # Cree toutes les donnees de test
    python manage.py seed_testdata --reset   # Supprime les donnees de test
    python manage.py seed_testdata --dry-run # Affiche ce qui serait cree

Donnees creees:
    - 5 Organismes
    - 7 Sites (avec types de nomenclature)
    - 10 Utilisateurs (7 actifs + 3 inactifs)
    - 8 Plans de gestion (5 actifs + 3 archives)
    - Groupes Django avec permissions
    - Nomenclatures (types de site, evaluation, redacteur)
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import Group, Permission
from django.db import transaction

from apps.users.models import Role, BibOrganismes, Site, CorRoleSite, CorOgSite
from apps.core.models import TypeNomenclature, Nomenclature
from apps.plans.models import PlanGestion, CorSitePg


DEFAULT_PASSWORD = 'Test123!'


class Command(BaseCommand):
    help = 'Cree ou supprime les donnees de test pour le developpement'

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

        nomenclatures = self._create_nomenclatures()
        groups = self._create_groups()
        organismes = self._create_organismes()
        sites = self._create_sites(organismes)
        users = self._create_users(organismes, sites, groups)
        plans = self._create_plans(users, sites)

        self._print_summary()

    @transaction.atomic
    def reset_test_data(self):
        """Supprime toutes les donnees de test."""
        self.stdout.write(self.style.MIGRATE_HEADING('\n=== Suppression des donnees de test ==='))

        if self.dry_run:
            self.stdout.write('Plans de gestion: tous seraient supprimes')
            self.stdout.write('Utilisateurs de test: 7 seraient supprimes')
            self.stdout.write('Sites: tous seraient supprimes')
            self.stdout.write('Organismes de test: 5 seraient supprimes')
            return

        # Supprimer les plans
        plans_deleted = PlanGestion.objects.all().delete()[0]
        self.stdout.write(f'  Plans de gestion supprimes: {plans_deleted}')

        # Supprimer les utilisateurs de test (garder le superuser original)
        test_emails = [
            'admin@test.fr', 'admin.rnf@test.fr', 'admin.cen@test.fr',
            'referent.camargue@test.fr', 'referent.vercors@test.fr',
            'user.rnf@test.fr', 'user.cen@test.fr',
            # Utilisateurs inactifs
            'ancien.rnf@test.fr', 'ancien.cen@test.fr', 'stagiaire.dreal@test.fr'
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

        self.stdout.write(self.style.SUCCESS('\nDonnees de test supprimees avec succes!'))

    def _show_dry_run_summary(self):
        """Affiche un resume des donnees qui seraient creees."""
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

    def _create_nomenclatures(self):
        """Cree les nomenclatures necessaires."""
        self.stdout.write('\n--- Creation des nomenclatures ---')

        # Type de site
        type_site, _ = TypeNomenclature.objects.get_or_create(
            id_type=1,
            defaults={'mnemonique': 'TYPE_SITE', 'label': 'Type de site'}
        )

        # Type d'evaluation
        type_eval, _ = TypeNomenclature.objects.get_or_create(
            id_type=2,
            defaults={'mnemonique': 'TYPE_EVALUATION', 'label': "Type d'evaluation"}
        )

        # Type de redacteur
        type_redac, _ = TypeNomenclature.objects.get_or_create(
            id_type=3,
            defaults={'mnemonique': 'TYPE_REDACTEUR', 'label': 'Type de redacteur'}
        )

        # Nomenclatures de type de site
        site_types = [
            {'id': 42, 'cd': 'RNN', 'mnemonique': 'TYPE_SITE_RNN', 'label': 'Reserve Naturelle Nationale'},
            {'id': 43, 'cd': 'RNR', 'mnemonique': 'TYPE_SITE_RNR', 'label': 'Reserve Naturelle Regionale'},
            {'id': 44, 'cd': 'PNR', 'mnemonique': 'TYPE_SITE_PNR', 'label': 'Parc Naturel Regional'},
            {'id': 45, 'cd': 'ENS', 'mnemonique': 'TYPE_SITE_ENS', 'label': 'Espace Naturel Sensible'},
            {'id': 46, 'cd': 'APB', 'mnemonique': 'TYPE_SITE_APB', 'label': 'Arrete de Protection de Biotope'},
        ]

        for st in site_types:
            Nomenclature.objects.update_or_create(
                id_nomenclature=st['id'],
                defaults={
                    'id_type': type_site,
                    'cd_nomenclature': st['cd'],
                    'mnemonique': st['mnemonique'],
                    'label': st['label'],
                    'actif': True
                }
            )
            if self.verbosity >= 2:
                self.stdout.write(f"  Type de site: {st['label']} (cd: {st['cd']})")

        # Nomenclatures d'evaluation
        eval_types = [
            {'id': 50, 'cd': 'EVAL_INT', 'mnemonique': 'EVALUATION_INTERMEDIAIRE', 'label': 'Evaluation intermediaire'},
            {'id': 51, 'cd': 'EVAL_FIN', 'mnemonique': 'EVALUATION_FINALE', 'label': 'Evaluation finale'},
            {'id': 52, 'cd': 'EVAL_EX', 'mnemonique': 'EVALUATION_EX_POST', 'label': 'Evaluation ex-post'},
        ]

        for et in eval_types:
            Nomenclature.objects.update_or_create(
                id_nomenclature=et['id'],
                defaults={
                    'id_type': type_eval,
                    'cd_nomenclature': et['cd'],
                    'mnemonique': et['mnemonique'],
                    'label': et['label'],
                    'actif': True
                }
            )
            if self.verbosity >= 2:
                self.stdout.write(f"  Type evaluation: {et['label']} (cd: {et['cd']})")

        # Nomenclatures de redacteur
        redac_types = [
            {'id': 60, 'cd': 'REDAC_GEST', 'mnemonique': 'REDACTEUR_GESTIONNAIRE', 'label': 'Gestionnaire'},
            {'id': 61, 'cd': 'REDAC_BE', 'mnemonique': 'REDACTEUR_BUREAU_ETUDE', 'label': "Bureau d'etude"},
            {'id': 62, 'cd': 'REDAC_AUTRE', 'mnemonique': 'REDACTEUR_AUTRE', 'label': 'Autre'},
        ]

        for rt in redac_types:
            Nomenclature.objects.update_or_create(
                id_nomenclature=rt['id'],
                defaults={
                    'id_type': type_redac,
                    'cd_nomenclature': rt['cd'],
                    'mnemonique': rt['mnemonique'],
                    'label': rt['label'],
                    'actif': True
                }
            )
            if self.verbosity >= 2:
                self.stdout.write(f"  Type redacteur: {rt['label']} (cd: {rt['cd']})")

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

    def _create_sites(self, organismes):
        """Cree les sites de test."""
        self.stdout.write('\n--- Creation des sites ---')

        # Recuperer les types de site par cd_nomenclature
        type_rnn = Nomenclature.objects.filter(cd_nomenclature='RNN').first()
        type_rnr = Nomenclature.objects.filter(cd_nomenclature='RNR').first()
        type_pnr = Nomenclature.objects.filter(cd_nomenclature='PNR').first()
        type_ens = Nomenclature.objects.filter(cd_nomenclature='ENS').first()

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
            site, created = Site.objects.get_or_create(
                nom_site=site_data['nom_site'],
                defaults=site_data
            )
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

        users_data = [
            {
                'email': 'admin@test.fr',
                'nom_role': 'Admin',
                'prenom_role': 'Super',
                'identifiant': 'super_admin',
                'role_level': 'super_admin',
                'is_staff': True,
                'is_superuser': True,
                'id_organisme': None,
                'groups': ['Super Administrateurs'],
                'sites_referent': []
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
                'role_level': 'referent',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Referents'],
                'sites_referent': [sites[0]]  # Camargue
            },
            {
                'email': 'referent.vercors@test.fr',
                'nom_role': 'Petit',
                'prenom_role': 'Lucas',
                'identifiant': 'ref_vercors',
                'role_level': 'referent',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[1],  # CEN AURA
                'groups': ['Referents'],
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
                'role_level': 'referent',
                'is_staff': False,
                'is_superuser': False,
                'id_organisme': organismes[0],  # RNF
                'groups': ['Referents'],
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
        ]

        users = []
        for user_data in users_data:
            user_groups = user_data.pop('groups')
            sites_referent = user_data.pop('sites_referent')
            is_active = user_data.pop('active', True)  # Valeur par defaut: True

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

        # Recuperer les nomenclatures par cd_nomenclature
        eval_int = Nomenclature.objects.filter(cd_nomenclature='EVAL_INT').first()
        eval_fin = Nomenclature.objects.filter(cd_nomenclature='EVAL_FIN').first()
        redac_gest = Nomenclature.objects.filter(cd_nomenclature='REDAC_GEST').first()
        redac_be = Nomenclature.objects.filter(cd_nomenclature='REDAC_BE').first()

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

    def _print_summary(self):
        """Affiche un resume des donnees creees."""
        self.stdout.write('\n' + '=' * 70)
        self.stdout.write(self.style.SUCCESS('DONNEES DE TEST CREEES AVEC SUCCES'))
        self.stdout.write('=' * 70)

        users_actifs = Role.objects.filter(active=True).count()
        users_inactifs = Role.objects.filter(active=False).count()
        plans_archives = PlanGestion.objects.filter(statut='archive').count()
        plans_actifs = PlanGestion.objects.exclude(statut='archive').count()

        self.stdout.write(f'\n  Organismes:        {BibOrganismes.objects.count()}')
        self.stdout.write(f'  Sites:             {Site.objects.count()}')
        self.stdout.write(f'  Utilisateurs:      {Role.objects.count()} ({users_actifs} actifs, {users_inactifs} inactifs)')
        self.stdout.write(f'  Plans de gestion:  {PlanGestion.objects.count()} ({plans_actifs} actifs, {plans_archives} archives)')
        self.stdout.write(f'  Groupes Django:    {Group.objects.count()}')
        self.stdout.write(f'  Nomenclatures:     {Nomenclature.objects.count()}')

        self.stdout.write('\n' + '-' * 70)
        self.stdout.write('UTILISATEURS DE TEST ACTIFS')
        self.stdout.write('-' * 70)
        self.stdout.write(f'\n  Mot de passe pour tous: {DEFAULT_PASSWORD}')
        self.stdout.write('''
  | Identifiant     | Email                      | Role            | Organisme   |
  |-----------------|----------------------------|-----------------|-------------|
  | super_admin     | admin@test.fr              | Super Admin     | -           |
  | admin_rnf       | admin.rnf@test.fr          | Admin Organisme | RNF         |
  | admin_cen       | admin.cen@test.fr          | Admin Organisme | CEN AURA    |
  | ref_camargue    | referent.camargue@test.fr  | Referent        | RNF         |
  | ref_vercors     | referent.vercors@test.fr   | Referent        | CEN AURA    |
  | user_rnf        | user.rnf@test.fr           | Utilisateur     | RNF         |
  | user_cen        | user.cen@test.fr           | Utilisateur     | CEN AURA    |
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
        self.stdout.write('URLs UTILES')
        self.stdout.write('-' * 70)
        self.stdout.write('''
  Frontend:           http://localhost:4200/auth/login
  Admin Django:       http://localhost:8000/admin/
  API Auth Login:     POST http://localhost:8000/api/auth/login/
        ''')
