"""
Dépose l'index de cette instance sur le hub d'exploration (#636).

Une publication se fait en trois temps — ouvrir un lot, déposer N pages,
basculer — parce que le hub purge à la bascule ce qui n'a pas été revu. Purger
au fil de l'eau viderait le hub de tout ce qui n'est pas encore arrivé si le
réseau tombe en milieu d'envoi.

**En cas d'échec, le lot est abandonné plutôt que basculé.** Un état partiel
basculé dépublierait du contenu parfaitement valide ; un lot abandonné ne
détruit rien et laisse en place la publication précédente, un peu vieille mais
complète. Entre « incomplet » et « périmé », c'est périmé qui est récupérable.

Usage :
    python manage.py push_federation                  # publie tout
    python manage.py push_federation --dry-run        # construit sans envoyer
    python manage.py push_federation --page-size 5    # pages plus petites
    python manage.py push_federation --sans-fiche     # index seul, sans fiches
"""

import json

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.search.push import (
    FORMAT_VERSION, charge_utile, partage_active, plans_a_publier,
)
from apps.search.serializers import prefetch_sites

#: Petit par défaut : chaque plan emporte sa fiche rendue, qui mobilise plusieurs
#: centaines d'objets. Une page de 500 comme pour un index nu produirait des
#: charges utiles de plusieurs dizaines de mégaoctets.
TAILLE_PAGE = 10

#: Une publication complète peut être longue ; le hub, lui, n'a qu'à écrire.
DELAI = 120


class Command(BaseCommand):
    help = "Dépose l'index de cette instance sur le hub d'exploration"

    def add_arguments(self, parser):
        parser.add_argument(
            '--hub', help="URL du hub (défaut : settings.CICADA_HUB_URL)",
        )
        parser.add_argument(
            '--token', help="Jeton de dépôt (défaut : settings.CICADA_HUB_PUSH_TOKEN)",
        )
        parser.add_argument(
            '--page-size', type=int, default=TAILLE_PAGE,
            help=f"Nombre de plans par page (défaut : {TAILLE_PAGE})",
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Construit les charges utiles sans rien envoyer",
        )
        parser.add_argument(
            '--sans-fiche', action='store_true',
            help="N'envoie pas les fiches rendues (dépôt plus rapide, fiches "
                 "distantes indisponibles côté hub)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"=== DÉPÔT VERS LE HUB — instance « {settings.CICADA_INSTANCE_ID} » ==="
        ))

        if not partage_active():
            # Refus franc plutôt que dépôt silencieux. La commande peut être
            # appelée par une tâche planifiée : si elle publiait malgré un
            # partage désactivé, la décision de la structure serait contournée
            # par une automatisation que personne ne relit.
            raise CommandError(
                "Le partage avec l'exploration nationale est désactivé sur cette "
                "instance : rien n'est publié. Un super administrateur peut "
                "l'activer dans les paramètres. Pour retirer des données déjà "
                "publiées, utiliser « retrait_federation »."
            )

        self.hub = (options['hub'] or settings.CICADA_HUB_URL).rstrip('/')
        self.jeton = options['token'] or settings.CICADA_HUB_PUSH_TOKEN
        self.dry_run = options['dry_run']
        avec_fiche = not options['sans_fiche']

        if not self.dry_run:
            if not self.hub:
                raise CommandError(
                    "Aucun hub configuré. Renseignez CICADA_HUB_URL ou --hub."
                )
            if not self.jeton:
                raise CommandError(
                    "Aucun jeton de dépôt. Renseignez CICADA_HUB_PUSH_TOKEN "
                    "ou --token."
                )

        plans = plans_a_publier().prefetch_related(prefetch_sites())
        total = plans.count()
        self.stdout.write(f"  {total} plan(s) explorable(s) à publier.")
        if not total:
            self.stdout.write(self.style.WARNING(
                "  Rien à publier. Un dépôt vide DÉPUBLIERAIT tout ce que le hub "
                "connaît de cette instance : le lot n'est pas ouvert."
            ))
            return

        self._verifier_index(total)

        lot = None if self.dry_run else self._ouvrir()
        try:
            envoyes = self._deposer_pages(plans, options['page_size'], avec_fiche, lot)
        except Exception as erreur:
            if lot:
                self._abandonner(lot)
                self.stderr.write(self.style.ERROR(
                    f"  Lot {lot} abandonné : la publication précédente reste en "
                    f"place, complète."
                ))
            raise CommandError(f"Dépôt interrompu : {erreur}") from erreur

        if self.dry_run:
            self.stdout.write(self.style.SUCCESS(
                f"  [dry-run] {envoyes} plan(s) construits, rien envoyé."
            ))
            return

        resultat = self._basculer(lot)
        self.stdout.write(self.style.SUCCESS(
            f"  {resultat['plans_recus']} plan(s) et "
            f"{resultat['contenus_recus']} document(s) publiés, "
            f"{resultat['plans_purges']} plan(s) dépublié(s)."
        ))

    # ------------------------------------------------------------------ #

    def _verifier_index(self, total_plans):
        """
        Refuse de publier des plans dont le contenu ne serait pas trouvé.

        La charge utile ne retient que les lignes d'index portant l'identité de
        cette instance. Si l'index a été construit sous une autre — identité
        changée, ou restée vide avant d'être renseignée — la publication
        réussirait en déposant des plans **sans aucun document**. L'exploration
        les afficherait alors en mode « plan », mais aucune recherche de contenu
        ne les trouverait : un échec silencieux, et difficile à relier à sa
        cause des semaines plus tard.
        """
        from apps.search.models import ContenuIndexe

        moi = settings.CICADA_INSTANCE_ID
        if ContenuIndexe.objects.filter(instance_id=moi).exists():
            return

        autres = sorted(
            ContenuIndexe.objects
            .exclude(instance_id=moi)
            .values_list('instance_id', flat=True)
            .distinct()
        )
        if not autres:
            raise CommandError(
                f"L'index local est vide alors que {total_plans} plan(s) sont "
                f"explorables. Lancez `rebuild_search_index` avant de publier."
            )

        etiquettes = ', '.join(repr(autre) for autre in autres)
        raise CommandError(
            f"Aucun document indexé pour l'instance « {moi} », mais l'index en "
            f"contient pour : {etiquettes}. L'identité de l'instance a changé "
            f"depuis l'indexation. Lancez `rebuild_search_index --purge` pour "
            f"réindexer sous la nouvelle identité."
        )

    def _entetes(self):
        return {
            'X-Federation-Token': self.jeton,
            'Content-Type': 'application/json',
        }

    def _appel(self, methode, chemin, corps=None):
        reponse = requests.request(
            methode, f"{self.hub}{chemin}",
            headers=self._entetes(),
            data=json.dumps(corps) if corps is not None else None,
            timeout=DELAI,
        )
        if reponse.status_code >= 400:
            raise RuntimeError(
                f"{methode} {chemin} → {reponse.status_code} : {reponse.text[:500]}"
            )
        return reponse.json() if reponse.content else {}

    def _ouvrir(self):
        # L'instance se nomme à l'ouverture du lot, en plus de s'authentifier.
        # Le hub n'a autrement que l'identifiant technique à afficher devant un
        # résultat distant, et « rnf » ne dit pas à un gestionnaire de quelle
        # structure vient le plan qu'il consulte. Le libellé n'autorise rien :
        # l'émetteur reste déduit du jeton.
        corps = self._appel(
            'POST', '/api/federation/lots/', {
                'format_version': FORMAT_VERSION,
                'libelle': settings.CICADA_INSTANCE_LABEL,
                'url_publique': settings.CICADA_PUBLIC_URL,
            }
        )
        self.stdout.write(f"  Lot {corps['lot_id']} ouvert.")
        return corps['lot_id']

    def _deposer_pages(self, plans, taille, avec_fiche, lot):
        envoyes = 0
        page = []

        # `iterator()` pour ne pas charger les ~4 400 plans en mémoire, chacun
        # traînant son arborescence prefetchée.
        for plan in plans.iterator(chunk_size=taille):
            page.append(charge_utile(plan, avec_fiche=avec_fiche))
            if len(page) >= taille:
                envoyes += self._deposer(page, lot)
                page = []

        if page:
            envoyes += self._deposer(page, lot)
        return envoyes

    def _deposer(self, page, lot):
        if self.dry_run:
            self.stdout.write(f"    [dry-run] page de {len(page)} plan(s)")
            return len(page)

        corps = self._appel(
            'POST', f'/api/federation/lots/{lot}/plans/', {'plans': page}
        )
        self.stdout.write(
            f"    page de {corps['plans_recus']} plan(s), "
            f"{corps['contenus_recus']} document(s)"
        )
        return corps['plans_recus']

    def _basculer(self, lot):
        return self._appel('POST', f'/api/federation/lots/{lot}/bascule/')

    def _abandonner(self, lot):
        try:
            self._appel('DELETE', f'/api/federation/lots/{lot}/')
        except Exception as erreur:  # noqa: BLE001 — on est déjà en train d'échouer
            # Un lot non abandonné n'est pas grave : il n'a jamais été basculé,
            # donc il n'a rien purgé. Il expire.
            self.stderr.write(self.style.WARNING(
                f"  Abandon du lot {lot} impossible ({erreur}) — sans effet : "
                f"un lot non basculé ne purge rien."
            ))
