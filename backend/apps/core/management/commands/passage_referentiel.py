"""
Passage d'un référentiel à une nouvelle version (#779) : PressRef, TaxRef, HabRef
(et types d'action, délégués à `passage_types_action`).

    python manage.py passage_referentiel taxref taxref_v19              # simulation
    python manage.py passage_referentiel taxref taxref_v19 --appliquer  # applique + notifie
    python manage.py passage_referentiel taxref taxref_v19 --annuler

Voir `nomenclatures_data/referentiels_versions/README.md`.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.plans.referentiels import moteur


class Command(BaseCommand):
    help = "Passe les objets des plans à une nouvelle version d'un référentiel."

    def add_arguments(self, parser):
        parser.add_argument('referentiel', help="pressref, taxref, habref ou types_action")
        parser.add_argument('version', help="Dossier de la version")
        mode = parser.add_mutually_exclusive_group()
        mode.add_argument('--appliquer', action='store_true')
        mode.add_argument('--annuler', action='store_true')
        parser.add_argument('--sans-email', action='store_true')

    def handle(self, *args, **opts):
        if opts['referentiel'].lower() in ('types_action', 'type_action', 'gestref'):
            extra = [a for a, on in (('--appliquer', opts['appliquer']), ('--annuler', opts['annuler']),
                                     ('--sans-email', opts['sans_email'])) if on]
            call_command('passage_types_action', opts['version'], *extra, stdout=self.stdout)
            return
        try:
            ref = moteur.referentiel(opts['referentiel'])
            d = moteur.charger(ref, opts['version'])
            if opts['annuler']:
                p = moteur.annuler(ref, d)
                self.stdout.write(self.style.SUCCESS(
                    f"✓ Passage {p} annulé : version en service « {p.source.libelle} »."))
                return
            r = moteur.simuler(ref, d)
            self._rapport(r)
            if not opts['appliquer']:
                self.stdout.write(self.style.WARNING("\nSimulation : rien n'a été modifié. Relancer avec --appliquer."))
                return
            p = moteur.appliquer(ref, d, envoyer_email=not opts['sans_email'])
        except moteur.ReferentielErreur as e:
            raise CommandError(str(e)) from e
        self.stdout.write(self.style.SUCCESS(f"\n✓ Passage {p} appliqué (n° {p.pk}) : {p.resume}."))

    def _rapport(self, r):
        w = self.stdout.write
        w(self.style.MIGRATE_HEADING(f"=== {r['referentiel']} : {r['depuis']} → {r['vers']} ==="))
        if r.get('sans_table'):
            w(self.style.WARNING(
                f"⚠ Cette instance est en {r['en_service']}, pas en {r['depuis']} : elle est en retard "
                "de plusieurs versions. Aucune correspondance automatique ne sera proposée : chaque "
                "élément concerné sera à actualiser à la main par les référents."))
        o = r['objets']
        w(f"Objets : sûre {o.get('sure', 0)}  probable {o.get('probable', 0)}  "
          f"à arbitrer (ancien code conservé) {o.get('a_arbitrer', 0)}")
        for cible, c in r['par_cible'].items():
            w(f"  {cible} : {c}")
        if r['a_arbitrer_par_code']:
            w("Codes à arbitrer : " + ', '.join(f"{c} ({n})" for c, n in r['a_arbitrer_par_code']))
        w("\nPar plan (sûre / probable / à arbitrer) :")
        for p in r['plans']:
            w(f"  {p['plan'] or '(hors plan)'} [{p['statut'] or '—'}] : "
              f"{p.get('sure', 0)} / {p.get('probable', 0)} / {p.get('a_arbitrer', 0)}")
        if r['plans_sans_destinataire']:
            w(self.style.WARNING("Plans sans référent ni administrateur : " + ', '.join(r['plans_sans_destinataire'])))
