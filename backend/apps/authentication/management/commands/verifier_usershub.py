"""
Avant de passer une instance en connexion GeoNature (#764) — ou de la mettre à
jour depuis l'ancienne vérification par l'API GeoNature, retirée : qui, parmi
les comptes CICADA actifs, pourra se connecter ?

L'API GeoNature ne contrôlait pas le droit sur CICADA (et rien du tout avec
pypnusershub <= 3.2) : des comptes sont donc entrés sans profil sur
l'application. Ils seront refusés (403). Cette commande les liste, sans rien
modifier, pour leur donner le profil dans UsersHub avant.

Elle lit la base UsersHub avec les réglages USERSHUB_DB_* et
GEONATURE_AUTH_CODE_APPLICATION, quel que soit le mode de connexion en service.

Usage :
    python manage.py verifier_usershub          # bilan + comptes refusés
    python manage.py verifier_usershub --tous   # + comptes autorisés

Code retour : 0 si aucun compte actif ne serait refusé, 1 sinon, 2 si la base
UsersHub est injoignable ou non configurée.
"""
from django.core.management.base import BaseCommand

from apps.authentication import reglages
from apps.authentication.providers import usershub_base
from apps.authentication.providers.usershub import UsersHubIndisponible

MOTIFS = {
    'absent': "aucun compte UsersHub (ni par son id, ni par son email)",
    'inactif': "compte UsersHub désactivé",
    'sans_droit': "pas de profil sur l'application",
}


class Command(BaseCommand):
    help = "Liste les comptes CICADA actifs qui seraient refusés en connexion par la base UsersHub (#764)"

    def add_arguments(self, parser):
        parser.add_argument('--tous', action='store_true', help='Afficher aussi les comptes autorisés')

    def handle(self, *args, **options):
        r = reglages.actuels()
        if not r.est_configuree():
            self.stderr.write("Réglages manquants : code de l'application, hôte, base et compte de lecture "
                              "(Administration > Paramètres > Connexion, ou GEONATURE_AUTH_CODE_APPLICATION "
                              "et USERSHUB_DB_* dans le .env).")
            raise SystemExit(2)
        try:
            bilan = usershub_base.bilan_des_comptes(r)
        except UsersHubIndisponible:
            self.stderr.write(f"Base UsersHub injoignable ou lecture refusée ({r.db_host}) : "
                              "voir le journal (« Vérification UsersHub »), ou le bouton « Tester » des paramètres.")
            raise SystemExit(2)

        self.stdout.write(f"Application « {r.code_application} » — {bilan['total']} compte(s) CICADA actif(s) : "
                          f"{bilan['autorises']} pourront se connecter, {bilan['refuses']} seraient refusés.")
        self.stdout.write(f"Super-utilisateurs qui pourront se connecter : {bilan['super_admins_autorises']}.")
        refuses = [c for c in bilan['comptes'] if c['motif']]
        if refuses:
            self.stdout.write("\nSeraient refusés :")
            for compte in refuses:
                self.stdout.write(f"  {compte['email']} — {MOTIFS[compte['motif']]}")
        autorises = [c for c in bilan['comptes'] if not c['motif']]
        if options['tous'] and autorises:
            self.stdout.write("\nAutorisés :")
            for compte in autorises:
                self.stdout.write(f"  {compte['email']}")
        if refuses:
            raise SystemExit(1)
