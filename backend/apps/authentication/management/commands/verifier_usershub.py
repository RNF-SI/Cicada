"""
Avant de passer une instance en service à GEONATURE_AUTH_SOURCE=base (#764) :
qui, parmi les comptes CICADA actifs, pourra encore se connecter ?

En source « api », GeoNature ne contrôle pas le droit sur CICADA (et rien du
tout avec pypnusershub <= 3.2) : des comptes sont donc entrés sans profil sur
l'application. En source « base », ils seront refusés (403). Cette commande les
liste, sans rien modifier, pour leur donner le profil dans UsersHub AVANT la
bascule.

Elle lit la base UsersHub avec les réglages USERSHUB_DB_* et
GEONATURE_AUTH_CODE_APPLICATION, quelle que soit la source en service : on
peut les renseigner, relancer web (sans effet tant que la source reste
« api »), vérifier, puis basculer.

Usage :
    python manage.py verifier_usershub          # bilan + comptes refusés
    python manage.py verifier_usershub --tous   # + comptes autorisés

Code retour : 0 si aucun compte actif ne serait refusé, 1 sinon, 2 si la base
UsersHub est injoignable ou non configurée.
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.authentication.providers import usershub_base
from apps.authentication.providers.usershub import UsersHubIndisponible
from apps.users.models import Role

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
        code = settings.GEONATURE_AUTH_CODE_APPLICATION
        if not usershub_base.est_configuree():
            self.stderr.write("Réglages manquants : GEONATURE_AUTH_CODE_APPLICATION, USERSHUB_DB_HOST, "
                              "USERSHUB_DB_NAME, USERSHUB_DB_USER (et USERSHUB_DB_PASSWORD) dans le .env.")
            raise SystemExit(2)

        comptes = list(Role.objects.filter(is_active=True, is_anonymized=False)
                       .order_by('email').values('email', 'usershub_id_role', 'is_superuser'))
        try:
            lignes = usershub_base.acces_des_comptes(
                [c['usershub_id_role'] for c in comptes if c['usershub_id_role']],
                [c['email'] for c in comptes if not c['usershub_id_role'] and c['email']],
            )
        except UsersHubIndisponible:
            self.stderr.write(f"Base UsersHub injoignable ou lecture refusée ({settings.USERSHUB_DB_HOST}) : "
                              "voir le journal (« Vérification UsersHub »).")
            raise SystemExit(2)

        par_id = {ligne[0]: ligne for ligne in lignes}
        par_email = {}
        for ligne in lignes:
            par_email.setdefault(ligne[1], []).append(ligne)

        autorises, refuses = [], []
        admins_autorises = 0
        for compte in comptes:
            if compte['usershub_id_role']:
                trouve = par_id.get(compte['usershub_id_role'])
            else:
                # Retrouvé par email à la première connexion (compte_pour) :
                # plusieurs comptes UsersHub au même email, celui qui se
                # connecte décidera ; on retient le meilleur cas.
                candidats = par_email.get((compte['email'] or '').lower(), [])
                trouve = max(candidats, key=lambda l: (l[3], l[2]), default=None)
            if trouve is None:
                refuses.append((compte['email'], 'absent'))
            elif not trouve[2]:
                refuses.append((compte['email'], 'inactif'))
            elif not trouve[3]:
                refuses.append((compte['email'], 'sans_droit'))
            else:
                autorises.append(compte['email'])
                admins_autorises += compte['is_superuser']

        self.stdout.write(f"Application « {code} » — {len(comptes)} compte(s) CICADA actif(s) : "
                          f"{len(autorises)} pourront se connecter, {len(refuses)} seraient refusés.")
        self.stdout.write(f"Super-utilisateurs qui pourront se connecter : {admins_autorises}.")
        if refuses:
            self.stdout.write("\nRefusés en source « base » :")
            for email, motif in refuses:
                self.stdout.write(f"  {email} — {MOTIFS[motif]}")
        if options['tous'] and autorises:
            self.stdout.write("\nAutorisés :")
            for email in autorises:
                self.stdout.write(f"  {email}")
        if refuses:
            raise SystemExit(1)
