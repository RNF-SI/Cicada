import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { MetriqueRef, Operation } from '../../../../core/models/enjeu.model';
import { LeafletMapEditComponent } from '../../../../shared/components/leaflet-map-edit/leaflet-map-edit.component';
import { MetriqueGridDisplayComponent } from '../../../../shared/components/metrique-grid-display/metrique-grid-display.component';
import { CheckboxComponent } from '../../../../shared/components/checkbox/checkbox.component';

/**
 * #354 — Fiche synthétique d'une action (opération).
 *
 * Vue condensée et imprimable/exportable des informations essentielles d'une
 * action : identité, contexte CT88, temporalité, acteurs (opérateurs /
 * partenaires / financeurs), indicateurs liés et réalisation. Le bouton
 * « Imprimer / Exporter » s'appuie sur `window.print()` + un CSS d'impression
 * (export PDF via le navigateur) pour incorporation dans les plans de gestion.
 */
@Component({
  selector: 'app-operation-fiche',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule, LeafletMapEditComponent, MetriqueGridDisplayComponent, CheckboxComponent],
  templateUrl: './operation-fiche.component.html',
  styleUrl: './operation-fiche.component.scss',
})
export class OperationFicheComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly enjeuService = inject(EnjeuService);

  operation = signal<Operation | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);
  planSlug = signal<string | null>(null);

  /**
   * #532 — Sections facultatives que l'utilisateur peut masquer avant
   * l'impression/export, pour personnaliser le document produit. L'en-tête
   * (identité de l'action) reste toujours affiché.
   */
  readonly toggleableSections = [
    { key: 'description', labelKey: 'plans.suivis.actions.fiche.description' },
    { key: 'temporalite', labelKey: 'plans.suivis.actions.fiche.temporalite' },
    { key: 'acteurs', labelKey: 'plans.suivis.actions.fiche.acteurs' },
    { key: 'programmation', labelKey: 'plans.suivis.actions.fiche.programmation' },
    { key: 'indicateursReponse', labelKey: 'plans.suivis.actions.fiche.indicateursReponse' },
    { key: 'indicateursAutres', labelKey: 'plans.suivis.actions.fiche.indicateursAutres' },
    { key: 'emprise', labelKey: 'plans.suivis.actions.fiche.emprise' },
    { key: 'realisation', labelKey: 'plans.suivis.actions.fiche.realisation' },
  ] as const;

  /** Visibilité par section (toutes cochées/affichées par défaut). */
  readonly sectionVisibility = signal<Record<string, boolean>>(
    Object.fromEntries(this.toggleableSections.map(s => [s.key, true])),
  );

  /** Panneau de choix des sections (replié par défaut, non imprimé). */
  showSectionPicker = signal(false);

  toggleSectionPicker(): void { this.showSectionPicker.update(v => !v); }

  /** Une section est affichée sauf si elle a été explicitement décochée. */
  sectionVisible(key: string): boolean { return this.sectionVisibility()[key] !== false; }

  setSectionVisible(key: string, visible: boolean): void {
    this.sectionVisibility.update(cur => ({ ...cur, [key]: visible }));
  }

  /** Indicateurs liés, dérivés des métriques de l'action, dédupliqués. */
  readonly indicateursLies = computed(() => {
    const metriques = this.operation()?.metriques ?? [];
    const byInd = new Map<number, { id: number; nom: string; type?: string | null; metriques: string[]; metriqueRefs: MetriqueRef[] }>();
    for (const m of metriques) {
      const entry = byInd.get(m.indicateur_id) ?? { id: m.indicateur_id, nom: m.indicateur_nom, type: m.indicateur_type, metriques: [], metriqueRefs: [] };
      if (m.nom_metrique) entry.metriques.push(m.nom_metrique);
      entry.metriqueRefs.push(m);
      byInd.set(m.indicateur_id, entry);
    }
    return [...byInd.values()];
  });

  /** Indicateurs de réponse (l'action y contribue), mis en avant. */
  readonly indicateursReponse = computed(() =>
    this.indicateursLies().filter(i => (i.type ?? '').toUpperCase() === 'REPONSE')
  );

  /** Autres indicateurs liés (état / pression), pour rappel. */
  readonly indicateursEtatPression = computed(() =>
    this.indicateursLies().filter(i => (i.type ?? '').toUpperCase() !== 'REPONSE')
  );

  /** Programmation annuelle : années planifiées avec budget / ETP. */
  readonly programmation = computed(() =>
    [...(this.operation()?.operation_annees ?? [])]
      .sort((a, b) => a.annee - b.annee)
      .map(oa => ({
        annee: oa.annee,
        periodicite: oa.periodicite,
        budget: oa.budget,
        etp: oa.etp,
      }))
  );

  /** Total budget programmé (somme des budgets annuels renseignés). */
  readonly totalBudget = computed(() => {
    const vals = this.programmation().map(p => p.budget).filter((v): v is number => v != null);
    return vals.length ? vals.reduce((a, b) => a + Number(b), 0) : null;
  });

  /** Total ETP programmé (somme des ETP annuels renseignés). */
  readonly totalEtp = computed(() => {
    const vals = this.programmation().map(p => p.etp).filter((v): v is number => v != null);
    return vals.length ? vals.reduce((a, b) => a + Number(b), 0) : null;
  });

  /** Sources de financement de l'action. */
  readonly financements = computed(() => this.operation()?.finances ?? []);

  /** #326 — Emprise spatiale de l'action (geom), affichée en carte lecture seule. */
  readonly empriseGeom = computed<any>(() => {
    const op = this.operation();
    return op?.geom_geojson ?? op?.geom ?? null;
  });

  /** Période lisible (annee_min – annee_max). */
  readonly periode = computed(() => {
    const op = this.operation();
    if (op?.annee_min && op?.annee_max) return `${op.annee_min} – ${op.annee_max}`;
    if (op?.annee_min) return `${op.annee_min}`;
    return '—';
  });

  ngOnInit(): void {
    this.planSlug.set(this.findRouteParam('slug'));
    const opIdStr = this.route.snapshot.paramMap.get('operationId');
    const opId = opIdStr ? Number(opIdStr) : null;
    if (!opId) {
      this.errorMessage.set('Action introuvable.');
      this.isLoading.set(false);
      return;
    }
    this.enjeuService.getOperation(opId).subscribe({
      next: (op) => {
        this.operation.set(op);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set('Action introuvable.');
        this.isLoading.set(false);
      },
    });
  }

  /** Remonte l'arbre des routes pour trouver un paramètre (ex. le slug du plan). */
  private findRouteParam(name: string): string | null {
    let r: ActivatedRoute | null = this.route;
    while (r) {
      const v = r.snapshot.paramMap.get(name);
      if (v) return v;
      r = r.parent;
    }
    return null;
  }

  /** #354 — export : impression navigateur (→ PDF). */
  print(): void {
    window.print();
  }

  /**
   * #529 — Retourne à la page d'origine. La fiche s'ouvrant dans un nouvel
   * onglet (#455), on ne peut pas s'appuyer sur l'historique du navigateur :
   * l'origine est transmise via le query param `from` (`enjeux` = liste des
   * actions du plan, sinon le suivi des actions par défaut).
   *
   * Cas `enjeux` : on revient à la POSITION de l'action dans l'architecture du
   * plan (#531). On passe le query param `expandOperation`, que la liste des
   * enjeux décode pour ouvrir le bon onglet (OLT ou Opérations), déplier toute
   * la chaîne parente (OO/OLT → indicateur → action) et scroller/surligner
   * l'action ciblée. (L'ancien fragment `operation-<id>` n'ouvrait pas l'OLT/OO :
   * `prepareUiForAnchor` ne gère pas le type `operation`.)
   */
  goBack(): void {
    const slug = this.planSlug();
    if (!slug) {
      this.router.navigate(['/plans']);
      return;
    }
    const qp = this.route.snapshot.queryParamMap;
    const from = qp.get('from');
    if (from === 'enjeux') {
      const enjeuSlug = qp.get('fromEnjeu');
      const opId = this.operation()?.id_operation;
      if (enjeuSlug) {
        this.router.navigate(['/plans', slug, 'enjeux', enjeuSlug], {
          queryParams: opId ? { expandOperation: opId } : undefined,
        });
      } else {
        this.router.navigate(['/plans', slug, 'enjeux']);
      }
    } else {
      this.router.navigate(['/plans', slug, 'suivi-actions']);
    }
  }

  goEdit(): void {
    const slug = this.planSlug();
    const op = this.operation();
    if (slug && op) {
      this.router.navigate(['/plans', slug, 'enjeux', 'operations', op.id_operation, 'modifier']);
    }
  }

  /**
   * #531 — Va directement à la POSITION de l'action dans l'architecture du plan,
   * indépendamment du bouton « Retour ». Utile quand la fiche a été ouverte
   * depuis le suivi des actions (où « Retour » ramène au suivi). On s'appuie sur
   * l'enjeu parent (`enjeu_slug`, résolu côté backend via les métriques) et sur
   * le query param `expandOperation` que la liste des enjeux décode pour ouvrir
   * le bon onglet (OLT/Opérations), déplier la chaîne et scroller vers l'action.
   */
  goToArchitecture(): void {
    const slug = this.planSlug();
    const op = this.operation();
    const enjeuSlug = op?.enjeu_slug;
    if (slug && op && enjeuSlug) {
      this.router.navigate(['/plans', slug, 'enjeux', enjeuSlug], {
        queryParams: { expandOperation: op.id_operation },
      });
    }
  }

  /** #521 — Lien vers la page de suivi (vue globale) de cette action. */
  goToSuivi(): void {
    const slug = this.planSlug();
    const op = this.operation();
    if (slug && op) {
      this.router.navigate(['/plans', slug, 'suivi-actions', 'action', op.id_operation]);
    }
  }
}
