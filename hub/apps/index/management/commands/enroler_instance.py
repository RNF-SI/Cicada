"""
Enrôle une instance CICADA auprès de ce hub, ou renouvelle ses jetons (#636).

    python manage.py enroler_instance rnf --libelle "Réserves Naturelles de France"
    python manage.py enroler_instance rnf --renouveler depot
    python manage.py enroler_instance rnf --desactiver
    python manage.py enroler_instance --lister

Les jetons ne sont affichés **qu'une fois**, à leur création : le hub n'en garde
que l'empreinte. Les reperdre n'est pas grave — un renouvellement coûte une
commande et une ligne à changer côté instance — mais aller les rechercher en
base est impossible, et c'est voulu.
"""

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.index.models import Instance, PlanIndexe


class Command(BaseCommand):
    help = "Enrôle une instance dans la fédération ou renouvelle ses jetons"

    def add_arguments(self, parser):
        parser.add_argument(
            'instance_id', nargs='?',
            help="Identifiant de l'instance (ex. « rnf », « cen-aura »)",
        )
        parser.add_argument('--libelle', help="Nom affiché de la structure")
        parser.add_argument('--url', help="URL publique de l'instance")
        parser.add_argument(
            '--renouveler', choices=['depot', 'lecture', 'tout'],
            help="Renouvelle un jeton existant (l'ancien cesse aussitôt d'être accepté)",
        )
        parser.add_argument(
            '--desactiver', action='store_true',
            help="Refuse les jetons de cette instance sans rien effacer",
        )
        parser.add_argument(
            '--reactiver', action='store_true',
            help="Réadmet une instance désactivée, avec ses jetons existants",
        )
        parser.add_argument(
            '--lister', action='store_true',
            help="Affiche le registre et l'état de publication de chacun",
        )

    def handle(self, *args, **options):
        if options['lister']:
            return self._lister()

        identifiant = options['instance_id']
        if not identifiant:
            raise CommandError(
                "Indiquez un identifiant d'instance, ou « --lister » pour voir "
                "le registre."
            )

        instance = Instance.objects.filter(pk=identifiant).first()
        nouvelle = instance is None
        if nouvelle:
            instance = Instance(instance_id=identifiant)

        if options['libelle'] is not None:
            instance.libelle = options['libelle']
        if options['url'] is not None:
            instance.url_publique = options['url']
        if options['desactiver']:
            instance.active = False
        if options['reactiver']:
            instance.active = True

        # À l'enrôlement, les deux jetons sont tirés : une instance qui publie
        # sans pouvoir lire, ou l'inverse, n'a pas d'usage — et devoir revenir
        # une seconde fois pour le second jeton se solderait par un oubli.
        renouvellement = options['renouveler'] or ('tout' if nouvelle else None)
        jetons = {}
        if renouvellement in ('depot', 'tout'):
            jetons['dépôt'] = instance.poser_jeton(Instance.USAGE_DEPOT)
        if renouvellement in ('lecture', 'tout'):
            jetons['lecture'] = instance.poser_jeton(Instance.USAGE_LECTURE)

        try:
            instance.full_clean()
        except ValidationError as erreur:
            raise CommandError(
                "; ".join(
                    f"{champ} : {' '.join(messages)}"
                    for champ, messages in erreur.message_dict.items()
                )
            ) from erreur
        instance.save()

        verbe = "enrôlée" if nouvelle else "mise à jour"
        self.stdout.write(self.style.SUCCESS(
            f"Instance « {instance.instance_id} » {verbe}."
        ))
        if instance.libelle:
            self.stdout.write(f"  Nom      : {instance.libelle}")
        self.stdout.write(f"  Active   : {'oui' if instance.active else 'non'}")

        if jetons:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "  Jetons affichés une seule fois — le hub n'en garde que "
                "l'empreinte :"
            ))
            for usage, jeton in jetons.items():
                self.stdout.write(f"    {usage:<8} : {jeton}")
            self.stdout.write("")
            self.stdout.write(
                "  À reporter côté instance dans son .env :\n"
                "    CICADA_INSTANCE_ID=" + instance.instance_id + "\n"
                + ("    CICADA_HUB_PUSH_TOKEN=<jeton de dépôt>\n"
                   if 'dépôt' in jetons else "")
                + ("    CICADA_HUB_READ_TOKEN=<jeton de lecture>\n"
                   if 'lecture' in jetons else "")
            )
            if options['renouveler']:
                self.stdout.write(self.style.WARNING(
                    "  L'ancien jeton n'est plus accepté : l'instance ne "
                    "publiera plus tant qu'elle n'aura pas le nouveau."
                ))

        if nouvelle and PlanIndexe.objects.filter(instance_id=identifiant).exists():
            # Cas courant de la migration depuis les jetons d'environnement :
            # l'instance publiait déjà, elle est seulement formalisée ici.
            self.stdout.write(self.style.NOTICE(
                "  Note : cette instance avait déjà publié (jeton "
                "d'environnement). Son index reste en place ; seul le jeton "
                "change."
            ))

    def _lister(self):
        instances = Instance.objects.all()
        publies = set(PlanIndexe.objects.values_list('instance_id', flat=True))

        if not instances and not publies:
            self.stdout.write("Aucune instance enrôlée, aucun index publié.")
            return

        self.stdout.write(self.style.MIGRATE_HEADING("=== Registre des instances ==="))
        for instance in instances:
            nb = PlanIndexe.objects.filter(instance_id=instance.instance_id).count()
            etat = "active" if instance.active else "DÉSACTIVÉE"
            self.stdout.write(
                f"  {instance.instance_id:<20} {etat:<12} {nb:>6} plan(s)   "
                f"{instance.libelle}"
            )

        # Une instance qui publie sans être enrôlée passe par un jeton
        # d'environnement : c'est exactement ce qu'il reste à migrer.
        orphelines = publies - {i.instance_id for i in instances}
        if orphelines:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "  Publient sans être enrôlées (jeton d'environnement) :"
            ))
            for identifiant in sorted(orphelines):
                nb = PlanIndexe.objects.filter(instance_id=identifiant).count()
                self.stdout.write(f"    {identifiant:<20} {nb:>6} plan(s)")
