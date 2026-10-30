"""
#788 — Remet en état les catégories d'action réserve (CT88) après un passage
du référentiel des types d'action appliqué avant la correction.

    python manage.py reparer_categories_reserve               # simulation
    python manage.py reparer_categories_reserve --appliquer   # réparation

Sans option, rien n'est écrit. Voir `apps/plans/categories_reserve.py`.
"""
from django.core.management.base import BaseCommand

from apps.plans import categories_reserve


class Command(BaseCommand):
    help = "Rétablit les 9 catégories d'action réserve et la catégorie des actions après un passage Gestref."

    def add_arguments(self, parser):
        parser.add_argument('--appliquer', action='store_true', help="Écrit les corrections")

    def handle(self, *args, **opts):
        r = categories_reserve.reparer(appliquer=opts['appliquer'])
        w = self.stdout.write
        w(self.style.MIGRATE_HEADING("=== Catégories d'action réserve (CT88) ==="))
        w(f"Catégories à réactiver / renommer : {', '.join(r['categories_restaurees']) or 'aucune'}")
        if r['categories_absentes']:
            w(self.style.WARNING(
                f"Absentes de la base (lancer import_nomenclatures) : {', '.join(r['categories_absentes'])}"))
        w(f"Catégories de passage à désactiver : {', '.join(r['categories_desactivees']) or 'aucune'}")
        w(f"Actions qui reprennent leur catégorie d'avant le passage : {r['actions_corrigees']}")
        for code, n in sorted(r['actions_corrigees_par_categorie'].items()):
            w(f"  {code} : {n}")
        w(f"Actions dont la catégorie a été changée à la main depuis (laissées) : "
          f"{r['actions_modifiees_depuis']}")
        sans_trace = r['actions_sans_trace']
        w(f"Actions sans trace, avec une catégorie de passage (à reprendre à la main) : {len(sans_trace)}")
        for a in sans_trace:
            w(f"  #{a['id']} [{a['categorie']}] {a['libelle']}")
        w(f"Actions sans type ni catégorie, hors journal : {r['actions_sans_type_ni_categorie']} "
          "(une catégorie a pu y être effacée sans trace : à comparer avec une sauvegarde "
          "antérieure au passage)")
        if opts['appliquer']:
            w(self.style.SUCCESS("\n✓ Réparation appliquée."))
        else:
            w(self.style.WARNING("\nSimulation : rien n'a été modifié. Relancer avec --appliquer."))
