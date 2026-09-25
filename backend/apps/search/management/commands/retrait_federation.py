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
propres plans.

Usage :
    python manage.py retrait_federation --confirmer
"""

import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.search.push import FORMAT_VERSION

DELAI = 60


class Command(BaseCommand):
    help = "Retire de l'exploration nationale les données publiées par cette instance"

    def add_arguments(self, parser):
        parser.add_argument('--hub', help="URL du hub (défaut : settings.CICADA_HUB_URL)")
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

        hub = (options['hub'] or settings.CICADA_HUB_URL).rstrip('/')
        jeton = options['token'] or settings.CICADA_HUB_PUSH_TOKEN
        if not hub or not jeton:
            raise CommandError(
                "Hub ou jeton manquant : renseignez CICADA_HUB_URL et "
                "CICADA_HUB_PUSH_TOKEN, ou --hub et --token."
            )

        if not options['confirmer']:
            self.stdout.write(self.style.WARNING(
                "  Aucune écriture. Cette commande retirerait TOUS les plans de "
                "cette instance de l'exploration nationale.\n"
                "  Relancer avec --confirmer pour l'exécuter."
            ))
            return

        entetes = {'X-Federation-Token': jeton, 'Content-Type': 'application/json'}

        def appel(methode, chemin, corps=None):
            reponse = requests.request(
                methode, f"{hub}{chemin}", headers=entetes,
                data=json.dumps(corps) if corps is not None else None,
                timeout=DELAI,
            )
            if reponse.status_code >= 400:
                raise CommandError(
                    f"{methode} {chemin} → {reponse.status_code} : "
                    f"{reponse.text[:300]}"
                )
            return reponse.json() if reponse.content else {}

        # Un lot ouvert puis basculé sans qu'aucun plan n'y soit déposé : le hub
        # purge alors tout ce qui n'a pas été revu, c'est-à-dire tout. Aucun
        # endpoint de suppression n'est nécessaire — le mécanisme d'état s'en
        # charge, et il est déjà éprouvé.
        lot = appel(
            'POST', '/api/federation/lots/', {'format_version': FORMAT_VERSION}
        )['lot_id']
        resultat = appel('POST', f'/api/federation/lots/{lot}/bascule/')

        self.stdout.write(self.style.SUCCESS(
            f"  {resultat['plans_purges']} plan(s) retiré(s) de l'exploration "
            f"nationale. L'index local n'est pas affecté."
        ))
