"""
Ingestion des documents publiés par une autre instance CICADA (#636).

Synchronisation par **état**, pas par événement : chaque exécution récupère
l'intégralité de l'index publié par la source, puis supprime les documents de
cette instance qui n'ont pas été revus. C'est ce qui rend la dépublication
fiable — un plan repassé en brouillon, supprimé, ou une instance décommissionnée
disparaissent du portail sans qu'aucun message de retrait n'ait à être reçu.

Un index qui se contenterait de rejouer des événements finirait immanquablement
par garder visible un plan que son gestionnaire a dépublié : c'est un incident,
pas une gêne.
"""

import json
import urllib.error
import urllib.request

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.search.federation import FORMAT_VERSION, contenu_depuis_document
from apps.search.models import ContenuIndexe


class Command(BaseCommand):
    help = (
        "Récupère l'index d'exploration publié par une autre instance CICADA "
        "et l'intègre à l'index local (exploration centralisée, #636)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--source', required=True,
            help="URL de base de l'instance émettrice (ex. http://web:8000).",
        )
        parser.add_argument(
            '--token',
            help=(
                "Jeton de fédération de la source. À défaut, "
                "CICADA_FEDERATION_TOKEN de cette instance est utilisé."
            ),
        )
        parser.add_argument(
            '--page-size', type=int, default=500,
            help="Taille des pages demandées à la source (défaut : 500).",
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Récupère et compte, sans rien écrire.",
        )

    def handle(self, *args, **options):
        source = options['source'].rstrip('/')
        jeton = options['token'] or settings.CICADA_FEDERATION_TOKEN
        if not jeton:
            raise CommandError(
                "Aucun jeton de fédération : passez --token ou définissez "
                "CICADA_FEDERATION_TOKEN."
            )

        instance_source, documents = self._recuperer(source, jeton, options['page_size'])

        if instance_source == settings.CICADA_INSTANCE_ID:
            raise CommandError(
                f"La source se déclare comme « {instance_source} », qui est "
                f"l'identifiant de cette instance. Deux instances ne peuvent pas "
                f"partager le même CICADA_INSTANCE_ID : leurs documents "
                f"s'écraseraient mutuellement."
            )

        self.stdout.write(
            f"{len(documents)} document(s) reçu(s) de « {instance_source} »."
        )
        if options['dry_run']:
            self.stdout.write(self.style.WARNING("--dry-run : rien n'a été écrit."))
            return

        crees, supprimes = self._integrer(instance_source, documents)
        self.stdout.write(self.style.SUCCESS(
            f"Index à jour pour « {instance_source} » : {crees} document(s) "
            f"écrit(s), {supprimes} document(s) obsolète(s) retiré(s)."
        ))

    # ------------------------------------------------------------------ #

    def _recuperer(self, source, jeton, page_size):
        """Parcourt toutes les pages de l'endpoint de publication."""
        documents = []
        instance_source = None
        url = f"{source}/api/exploration/federation/documents/?page_size={page_size}"

        while url:
            corps = self._get(url, jeton)

            version = corps.get('format_version')
            if version != FORMAT_VERSION:
                raise CommandError(
                    f"Format d'échange incompatible : la source publie en "
                    f"version {version}, cette instance lit la version "
                    f"{FORMAT_VERSION}. Les instances étant mises à jour "
                    f"indépendamment, l'ingestion s'arrête plutôt que d'écrire "
                    f"des documents à moitié compris."
                )

            instance_source = corps.get('instance_id')
            if not instance_source:
                raise CommandError("La source ne déclare pas son instance_id.")

            documents += corps.get('results', [])
            url = (corps.get('links') or {}).get('next')

        return instance_source, documents

    def _get(self, url, jeton):
        requete = urllib.request.Request(url, headers={'X-Federation-Token': jeton})
        try:
            with urllib.request.urlopen(requete, timeout=60) as reponse:
                return json.loads(reponse.read().decode('utf-8'))
        except urllib.error.HTTPError as erreur:
            raise CommandError(
                f"{erreur.code} sur {url} — "
                f"{'jeton refusé' if erreur.code in (401, 403) else erreur.reason}"
            ) from erreur
        except urllib.error.URLError as erreur:
            raise CommandError(f"Source injoignable ({url}) : {erreur.reason}") from erreur

    @transaction.atomic
    def _integrer(self, instance_source, documents):
        """
        Remplace intégralement les documents de cette source.

        Le remplacement est atomique et porte sur le périmètre de la seule
        instance source : les documents locaux et ceux des autres instances ne
        sont jamais touchés.
        """
        supprimes, _ = (
            ContenuIndexe.objects.filter(instance_id=instance_source).delete()
        )
        lignes = [
            contenu_depuis_document(document, instance_source)
            for document in documents
        ]
        ContenuIndexe.objects.bulk_create(lignes, batch_size=500)
        return len(lignes), supprimes
