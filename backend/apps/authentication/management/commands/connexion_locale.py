"""
Secours (#769) : revenir aux comptes CICADA quand la connexion GeoNature,
activée depuis les paramètres, enferme tout le monde dehors (base UsersHub
injoignable, profil retiré…).

    python manage.py connexion_locale

Remet le mode réglé à l'écran sur « Comptes CICADA » : il prime sur
AUTH_PROVIDER. Les réglages de la base UsersHub sont conservés. Les comptes
créés par GeoNature n'ont pas de mot de passe CICADA : « Mot de passe
oublié », ou `python manage.py changepassword <email>`.
"""
from django.core.management.base import BaseCommand

from apps.authentication import reglages


class Command(BaseCommand):
    help = "Revient à la connexion par comptes CICADA (email + mot de passe) — secours de la connexion GeoNature"

    def handle(self, *args, **options):
        enregistrement = reglages.ligne()
        enregistrement.mode = reglages.LOCAL
        enregistrement.save()
        reglages._journaliser(None, 'deactivate', "Retour aux comptes CICADA (commande connexion_locale)", {})
        self.stdout.write("Connexion par comptes CICADA rétablie (sans redémarrage). Les réglages UsersHub "
                          "sont conservés : la connexion GeoNature se réactive depuis Administration > Paramètres.")
