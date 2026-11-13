"""
Reconstruit l'index de recherche du contenu des plans de gestion.

À lancer après une reprise de données, une évolution des extracteurs, ou pour
rattraper un plan dont l'indexation automatique aurait échoué. La commande est
idempotente : chaque plan est réécrit intégralement.

Usage :
    python manage.py rebuild_search_index                # tous les plans indexables
    python manage.py rebuild_search_index --plan 12      # un plan (répétable)
    python manage.py rebuild_search_index --purge        # vide l'index d'abord
    python manage.py rebuild_search_index --if-stale     # au démarrage : rebâtit
                                                         # si l'index date d'une
                                                         # version antérieure,
                                                         # sans le vider d'abord ;
                                                         # reprise si interrompu (#839)
"""

import logging

from django.core.management.base import BaseCommand, CommandError

from apps.plans.models import PlanGestion
from apps.search.indexing import (
    INDEX_VERSION, INDEXED_STATUSES, index_est_perime, index_plan,
)
from apps.search.models import ContenuIndexe

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Reconstruit l'index de recherche du contenu des plans de gestion"

    def add_arguments(self, parser):
        parser.add_argument(
            '--plan', type=int, action='append', dest='plans',
            help="Identifiant d'un plan à réindexer (répétable)",
        )
        parser.add_argument(
            '--purge', action='store_true',
            help="Vide entièrement l'index avant de le reconstruire",
        )
        parser.add_argument(
            '--if-empty', action='store_true',
            help=(
                "Ne fait rien si l'index contient déjà des lignes. Utilisé au "
                "démarrage pour amorcer l'index d'une base existante."
            ),
        )
        parser.add_argument(
            '--if-stale', action='store_true',
            help=(
                "Reconstruit l'index seulement s'il est vide ou s'il a été "
                "produit par une version antérieure des extracteurs "
                "(`indexing.INDEX_VERSION`). C'est le mode utilisé au "
                "démarrage : une mise à jour qui enrichit l'indexation prend "
                "effet sur les plans déjà validés, sans intervention."
            ),
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            '=== RECONSTRUCTION DE L\'INDEX DE RECHERCHE ==='
        ))

        if options['if_empty'] and ContenuIndexe.objects.exists():
            self.stdout.write(self.style.SUCCESS(
                '  Index déjà peuplé, rien à faire.'
            ))
            return

        if options['if_stale']:
            if not index_est_perime():
                self.stdout.write(self.style.SUCCESS(
                    f'  Index à jour (version {INDEX_VERSION}), rien à faire.'
                ))
                return
            self.stdout.write(
                f'  Index absent ou périmé → reconstruction complète '
                f'(version {INDEX_VERSION})'
            )
            # #839 — pas de purge d'abord : l'index reste interrogeable pendant
            # la reconstruction, et une reconstruction interrompue laisse des
            # lignes de l'ancienne version (l'index reste « périmé », le
            # démarrage suivant reprend). Le ménage se fait à la fin.
            options['menage'] = True

        if options['purge']:
            supprimees, _ = ContenuIndexe.objects.all().delete()
            self.stdout.write(f'  Index vidé ({supprimees} lignes)')

        plans = PlanGestion.objects.filter(statut__in=INDEXED_STATUSES)
        if options['plans']:
            plans = plans.filter(pk__in=options['plans'])

        # Les plans non indexables explicitement demandés sont désindexés,
        # pour que `--plan` serve aussi à corriger un plan indexé à tort.
        if options['plans']:
            ContenuIndexe.objects.filter(id_pg__in=options['plans']).exclude(
                id_pg__statut__in=INDEXED_STATUSES
            ).delete()

        total_plans = total_objets = 0
        echecs = []
        for plan in plans.iterator():
            # #839 — un plan en échec n'arrête pas les autres ; chaque plan est
            # réécrit en une transaction (index_plan), ses anciennes lignes
            # restent tant qu'il n'a pas réussi.
            try:
                nb = index_plan(plan)
            except Exception as erreur:  # noqa: BLE001
                logger.exception("Indexation du plan %s en échec", plan.pk)
                echecs.append(f'{plan.pk} ({type(erreur).__name__})')
                continue
            total_plans += 1
            total_objets += nb
            self.stdout.write(f'  {plan.nom[:60]:62s} {nb:5d} objets')

        if options.get('menage') and not echecs:
            # Lignes d'une version antérieure : plans devenus non indexables
            # (aucun n'a pu les réécrire). Seulement si tout a réussi : sinon,
            # elles gardent l'index « périmé » et le démarrage suivant reprend.
            restes, _ = ContenuIndexe.objects.exclude(index_version=INDEX_VERSION).delete()
            hors, _ = ContenuIndexe.objects.exclude(id_pg__statut__in=INDEXED_STATUSES).delete()
            if restes or hors:
                self.stdout.write(f'  {restes + hors} lignes obsolètes retirées')

        self.stdout.write(self.style.SUCCESS(
            f'  {total_objets} objets indexés sur {total_plans} plans'
        ))
        if echecs:
            raise CommandError(
                f"Indexation en échec pour {len(echecs)} plan(s) : {', '.join(echecs)}. "
                f"Ils gardent leurs lignes précédentes ; la reconstruction sera "
                f"reprise au prochain démarrage."
            )
