"""
Retire de l'exploration nationale tout ce que cette instance y a publié (#636).

**Commande distincte de `push_federation`, et c'est délibéré.** La publication
refuse de déposer un lot vide : un index qui se trouverait momentanément vide —
identité mal configurée, réindexation en cours, base restaurée — effacerait sinon
tout le travail de la structure sur le hub, sans que personne ne l'ait demandé.

Retirer ses données est pourtant un droit, et il doit être simple à exercer. La
distinction n'est donc pas entre « autorisé » et « interdit » mais entre
**accidentel** et **voulu** : un dépôt vide est un accident, un retrait est une
décision. Elles méritent deux commandes.

Le retrait est **immédiat côté hub** : le lot vide bascule, et tous les plans de
cette instance disparaissent de l'exploration nationale, contenu et fiches
compris. Il ne touche pas à l'index local : l'instance continue d'explorer ses
propres plans. Il retire aussi l'**accès** à l'exploration nationale : le hub
ne sert que les instances qui y ont des plans publiés.

Décocher le partage dans Administration > Paramètres produit le même retrait
(`raccordement.retirer_du_hub()`, partagé avec cette commande) ; la commande
reste l'outil de l'exploitant, et ne modifie pas le consentement.

Usage :
    python manage.py retrait_federation --confirmer
"""

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.search.push import partage_active
from apps.search.raccordement import ErreurRaccordement, hub_url, jeton_depot, retirer_du_hub


class Command(BaseCommand):
    help = "Retire de l'exploration nationale les données publiées par cette instance"

    def add_arguments(self, parser):
        parser.add_argument('--hub', help="URL du hub (défaut : CICADA_HUB_URL, sinon celle de l'adhésion)")
        parser.add_argument('--token', help="Jeton de dépôt de cette instance")
        parser.add_argument(
            '--confirmer', action='store_true',
            help="Confirme le retrait. Sans lui, la commande n'écrit rien.",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"=== RETRAIT DE L'EXPLORATION NATIONALE — « "
            f"{settings.CICADA_INSTANCE_ID} » ==="
        ))

        hub = (options['hub'] or hub_url()).rstrip('/')
        jeton = options['token'] or jeton_depot()
        if not hub or not jeton:
            raise CommandError(
                "Hub ou jeton manquant : renseignez CICADA_HUB_URL et "
                "CICADA_HUB_PUSH_TOKEN, ou --hub et --token (ou faites accepter "
                "l'adhésion de l'instance)."
            )

        if not options['confirmer']:
            self.stdout.write(self.style.WARNING(
                "  Aucune écriture. Cette commande retirerait TOUS les plans de "
                "cette instance de l'exploration nationale.\n"
                "  Relancer avec --confirmer pour l'exécuter."
            ))
            return

        # Même service que le décochage du partage dans l'interface : un lot
        # vide ouvert puis basculé, consigné dans l'historique (#698).
        try:
            purges = retirer_du_hub(hub=hub, jeton=jeton)
        except ErreurRaccordement as erreur:
            raise CommandError(erreur.message) from erreur

        self.stdout.write(self.style.SUCCESS(
            f"  {purges} plan(s) retiré(s) de l'exploration "
            f"nationale. L'index local n'est pas affecté."
        ))
        if partage_active():
            # La commande ne touche pas au consentement : c'est une décision de
            # la structure, prise dans l'interface. Mais le dire évite de croire
            # le retrait définitif quand la nuit suivante republiera tout.
            self.stdout.write(self.style.WARNING(
                "  Le partage reste activé dans les paramètres : la prochaine "
                "publication republiera les plans. Décochez-le dans "
                "Administration > Paramètres pour un retrait durable."
            ))
