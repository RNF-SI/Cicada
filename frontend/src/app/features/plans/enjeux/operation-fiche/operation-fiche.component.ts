import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { Operation } from '../../../../core/models/enjeu.model';
import { LeafletMapEditComponent } from '../../../../shared/components/leaflet-map-edit/leaflet-map-edit.component';

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
  imports: [CommonModule, RouterModule, TranslateModule, LeafletMapEditComponent],
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

  /** Indicateurs liés, dérivés des métriques de l'action, dédupliqués. */
  readonly indicateursLies = computed(() => {
    const metriques = this.operation()?.metriques ?? [];
    const byInd = new Map<number, { id: number; nom: string; type?: string | null; metriques: string[] }>();
    for (const m of metriques) {
      const entry = byInd.get(m.indicateur_id) ?? { id: m.indicateur_id, nom: m.indicateur_nom, type: m.indicateur_type, metriques: [] };
      if (m.nom_metrique) entry.metriques.push(m.nom_metrique);
      byInd.set(m.indicateur_id, entry);
    }
    return [...byInd.values()];
  });

  /** Années où l'action est programmée (périodicité). */
  readonly anneesProgrammees = computed(() =>
    (this.operation()?.operation_annees ?? [])
      .filter(oa => oa.periodicite)
      .map(oa => oa.annee)
      .sort((a, b) => a - b)
  );

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

  goBack(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'suivi-actions']);
    } else {
      this.router.navigate(['/plans']);
    }
  }

  goEdit(): void {
    const slug = this.planSlug();
    const op = this.operation();
    if (slug && op) {
      this.router.navigate(['/plans', slug, 'enjeux', 'operations', op.id_operation, 'modifier']);
    }
  }
}
