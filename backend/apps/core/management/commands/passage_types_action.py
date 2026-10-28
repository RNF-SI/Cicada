"""
Passage du référentiel des types d'action à une nouvelle version (#751).

    python manage.py passage_types_action gestref_v1              # simulation
    python manage.py passage_types_action gestref_v1 --appliquer  # applique + notifie
    python manage.py passage_types_action gestref_v1 --annuler    # revient en arrière

Sans option, rien n'est écrit : la commande décrit ce que ferait le passage.
Voir `apps/plans/referentiel_actions.py` et
`nomenclatures_data/referentiels_types_action/README.md`.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.plans import referentiel_actions as ref


class Command(BaseCommand):
    help = "Passe les actions et suivis à une nouvelle version du référentiel des types d'action."

    def add_arguments(self, parser):
        parser.add_argument('version', help="Dossier de la version (ex. gestref_v1)")
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--appliquer', action='store_true',
                          help="Applique le passage et prévient les référents")
        mode.add_argument('--annuler', action='store_true',
                          help="Restaure les types de la version de départ")
        parser.add_argument('--sans-email', action='store_true',
                            help="Notifications dans l'application seulement")

    def handle(self, *args, **opts):
        try:
            definition = ref.charger_version(opts['version'])
            if opts['annuler']:
                passage = ref.annuler(definition)
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Passage {passage} annulé : version en service « {passage.source.libelle} »."))
                return
            rapport = ref.simuler(definition)
            self._rapport(rapport)
            if not opts['appliquer']:
                self.stdout.write(self.style.WARNING(
                    "\nSimulation : rien n'a été modifié. Relancer avec --appliquer."))
                return
            passage = ref.appliquer(definition, envoyer_email=not opts['sans_email'])
        except ref.ReferentielErreur as e:
            raise CommandError(str(e)) from e
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Passage {passage} appliqué (n° {passage.pk}) : {passage.resume}."))

    def _rapport(self, r):
        w = self.stdout.write
        w(self.style.MIGRATE_HEADING(f"=== {r['depuis']} → {r['vers']} ==="))
        w(f"Référentiel : {r['types']} types, catégories {', '.join(r['categories'])}"
          + (f" (écartées : {', '.join(r['exclues'])})" if r['exclues'] else ''))
        a = r['actions']
        w(f"Actions : {a['total']} dont {a['sans_type']} sans type")
        w(f"  sûre : {a.get('sure', 0)}  probable : {a.get('probable', 0)}  "
          f"à arbitrer (ancien type conservé) : {a.get('a_arbitrer', 0)}")
        s = r['suivis']
        w(f"Suivis : sûre {s.get('sure', 0)}  probable {s.get('probable', 0)}  "
          f"à arbitrer {s.get('a_arbitrer', 0)}")
        w(f"Actions qui deviennent CS : {r['devient_cs']['total']} "
          f"(dont {r['devient_cs']['sans_suivi']} sans suivi)")
        if r['a_arbitrer_par_code']:
            w("Codes à arbitrer : " + ', '.join(f"{c} ({n})" for c, n in r['a_arbitrer_par_code']))
        w("\nPar plan (sûre / probable / à arbitrer) :")
        for p in r['plans']:
            w(f"  {p['plan'] or '(sans plan)'} [{p['statut'] or '—'}] : "
              f"{p.get('sure', 0)} / {p.get('probable', 0)} / {p.get('a_arbitrer', 0)}")
        if r['plans_sans_destinataire']:
            w(self.style.WARNING("Plans sans référent ni administrateur à prévenir : "
                                 + ', '.join(r['plans_sans_destinataire'])))
        if r['sans_plan']:
            w(self.style.WARNING(f"Actions rattachées à aucun plan : {r['sans_plan']}"))
