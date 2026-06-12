import {
  Component, OnInit, OnDestroy, inject, signal, computed, effect,
  ViewChild, ElementRef, HostListener
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatTooltipModule } from '@angular/material/tooltip';
import { forkJoin } from 'rxjs';

import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../core/services/admin.service';
import { EnjeuService } from '../../../core/services/enjeu.service';
import {
  MindmapNode, MindmapEntityType,
  MINDMAP_COLORS, MINDMAP_LABELS
} from '../../../core/models/mindmap.model';

/**
 * Tableau d'arborescence (#362) — rendu HTML/CSS natif.
 *
 * Historique : ce composant affichait un diagramme « icicle » D3 (partition SVG)
 * avec zoom-au-clic. Les colonnes se comprimaient pour remplir l'écran, ce qui
 * rognait le texte (le wrap était calculé une seule fois sur des colonnes larges
 * et jamais recalculé au zoom) et réduisait les opérations/facteurs à de fines
 * bandes à peine cliquables. On a remplacé tout cela par un arbre en colonnes
 * de largeur fixe, défilable : le navigateur gère le retour à la ligne nativement
 * (uniforme partout), chaque case est un vrai élément DOM cliquable avec une
 * hauteur minimale, et le défilement remplace le zoom.
 *
 * Le rendu est récursif (cf. template) : chaque nœud = `[case | pile des enfants]`.
 * Comme chaque case ancêtre a une largeur fixe, les nœuds d'une même profondeur
 * s'alignent automatiquement en colonnes.
 */
@Component({
  selector: 'app-plan-mindmap',
  standalone: true,
  imports: [
    CommonModule, RouterModule, TranslateModule,
    MatProgressSpinnerModule, MatButtonModule, MatTooltipModule,
    HeaderComponent, PlanSidebarComponent
  ],
  templateUrl: './plan-mindmap.component.html',
  styleUrl: './plan-mindmap.component.scss'
})
export class PlanMindmapComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly adminService = inject(AdminService);
  private readonly enjeuService = inject(EnjeuService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  loading = signal(true);
  error = signal<string | null>(null);
  treeData = signal<MindmapNode | null>(null);
  inverseTreeData = signal<MindmapNode | null>(null);

  // View mode: 'enjeux' (normal) or 'actions' (inverted)
  viewMode = signal<'enjeux' | 'actions'>('enjeux');

  legendItems: { type: MindmapEntityType; color: string; label: string }[] = [];

  // Custom tooltip (#257) — surface le nom complet d'une cellule au survol
  // (le texte de la case est tronqué à quelques lignes quand il est trop long).
  tooltipNode = signal<MindmapNode | null>(null);
  tooltipX = signal(0);
  tooltipY = signal(0);

  // Nœuds dont le sous-arbre est replié (set de références MindmapNode).
  collapsed = signal<Set<MindmapNode>>(new Set());

  // Nœud sur lequel on a « zoomé » : l'arbre n'affiche plus que son sous-arbre,
  // et la largeur des colonnes est recalculée pour tenir dans la largeur visible
  // (pas de défilement horizontal). null = vue d'ensemble (toutes les racines).
  focusNode = signal<MindmapNode | null>(null);

  // Largeur d'une colonne (px), recalculée pour faire tenir le sous-arbre
  // affiché dans la largeur du conteneur. Appliquée via --col-w sur .tree-scroll.
  colWidth = signal(240);

  @ViewChild('treeScroll') private treeScrollRef?: ElementRef<HTMLDivElement>;

  // Timer pour distinguer simple-clic (zoom) du double-clic (ouvrir la fiche).
  private clickTimer: ReturnType<typeof setTimeout> | null = null;

  // Map enfant → parent, construite au chargement, pour remonter aux ancêtres
  // dans openEntity() (le template récursif ne fournit pas la chaîne d'ancêtres).
  private parentMap = new Map<MindmapNode, MindmapNode>();

  /**
   * Racines à afficher. Si on a zoomé sur un nœud, on n'affiche que celui-ci
   * (son sous-arbre). Sinon, on saute le nœud « Plan » (déjà rappelé dans le
   * breadcrumb et l'en-tête) : l'arbre démarre aux enjeux/FCR (vue normale) ou
   * aux opérations (vue inverse).
   */
  displayRoots = computed<MindmapNode[]>(() => {
    const focus = this.focusNode();
    if (focus) {
      return [focus];
    }
    const mode = this.viewMode();
    const data = mode === 'enjeux' ? this.treeData() : this.inverseTreeData();
    const children = data?.children ?? [];
    if (mode === 'enjeux') {
      return children.filter(c => c.entityType === 'enjeu' || c.entityType === 'fcr');
    }
    return children.filter(c => c.entityType === 'operation');
  });

  getEntityLabel(type: MindmapEntityType | undefined): string {
    return type ? (MINDMAP_LABELS[type] || type) : '';
  }

  getEntityColor(type: MindmapEntityType | undefined): string {
    return type ? (MINDMAP_COLORS[type] || '#555') : '#555';
  }

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug');
    if (slug) {
      this.planSlug.set(slug);
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planNom.set(plan.nom);
          this.loadData(plan.id_pg);
        },
        error: () => {
          this.loading.set(false);
          this.error.set('Impossible de charger le plan.');
        }
      });
    }
  }

  private loadData(planId: number): void {
    forkJoin({
      normal: this.enjeuService.getMindmapData(planId),
      inverse: this.enjeuService.getMindmapInverseData(planId),
    }).subscribe({
      next: ({ normal, inverse }) => {
        this.treeData.set(normal);
        this.inverseTreeData.set(inverse);
        this.parentMap.clear();
        this.buildParentMap(normal);
        this.buildParentMap(inverse);
        this.loading.set(false);
      },
      error: (err) => {
        console.error('[mindmap] Erreur chargement données:', err);
        this.loading.set(false);
        this.error.set("Impossible de charger les données du tableau d'arborescence.");
      }
    });
  }

  private buildParentMap(node: MindmapNode): void {
    for (const child of node.children ?? []) {
      this.parentMap.set(child, node);
      this.buildParentMap(child);
    }
  }

  switchView(mode: 'enjeux' | 'actions'): void {
    if (this.viewMode() === mode) return;
    this.viewMode.set(mode);
    // Les références repliées/focus appartiennent à l'autre arbre : on repart
    // d'une vue d'ensemble dépliée.
    this.collapsed.set(new Set());
    this.focusNode.set(null);
  }

  ngOnDestroy(): void {
    if (this.clickTimer !== null) {
      clearTimeout(this.clickTimer);
    }
  }

  // ========== ARBRE ==========

  hasChildren(node: MindmapNode): boolean {
    return !!node.children && node.children.length > 0;
  }

  isCollapsed(node: MindmapNode): boolean {
    return this.collapsed().has(node);
  }

  toggleCollapse(node: MindmapNode, event: Event): void {
    event.stopPropagation();
    const next = new Set(this.collapsed());
    if (next.has(node)) {
      next.delete(node);
    } else {
      next.add(node);
    }
    this.collapsed.set(next);
  }

  /** « Tout replier » : ne garder visibles que les racines (enjeux/opérations). */
  collapseAll(): void {
    this.collapsed.set(new Set(this.displayRoots()));
  }

  /** « Tout déplier ». */
  expandAll(): void {
    this.collapsed.set(new Set());
  }

  // ========== ZOOM / FOCUS ==========
  //
  // Simple-clic = zoomer sur le nœud (n'afficher que son sous-arbre, colonnes
  // recalculées pour tenir dans la largeur). Re-cliquer le nœud focalisé
  // dézoome vers son parent. Double-clic = ouvrir la fiche détail.
  // On diffère le simple-clic pour ne pas le déclencher lors d'un double-clic.

  onCellClick(node: MindmapNode): void {
    if (this.clickTimer !== null) {
      clearTimeout(this.clickTimer);
    }
    this.clickTimer = setTimeout(() => {
      this.clickTimer = null;
      this.handleSingleClick(node);
    }, 220);
  }

  onCellDblClick(node: MindmapNode, event: Event): void {
    if (this.clickTimer !== null) {
      clearTimeout(this.clickTimer);
      this.clickTimer = null;
    }
    event.preventDefault();
    this.openEntity(node);
  }

  private handleSingleClick(node: MindmapNode): void {
    if (this.focusNode() === node) {
      this.zoomOut();
    } else if (this.hasChildren(node)) {
      this.setFocus(node);
    }
  }

  private setFocus(node: MindmapNode | null): void {
    this.focusNode.set(node);
  }

  /** Dézoome d'un cran : vers le parent du nœud focalisé, ou la vue d'ensemble. */
  zoomOut(): void {
    const current = this.focusNode();
    if (!current) return;
    const parent = this.parentMap.get(current);
    this.setFocus(parent && parent.entityType !== 'plan' ? parent : null);
  }

  /** Revient à la vue d'ensemble (toutes les racines). */
  resetFocus(): void {
    this.setFocus(null);
  }

  @HostListener('window:resize')
  onResize(): void {
    requestAnimationFrame(() => this.recomputeColWidth());
  }

  /** Profondeur du sous-arbre (0 pour une feuille). */
  private subtreeDepth(node: MindmapNode): number {
    const children = node.children;
    if (!children || children.length === 0) return 0;
    let max = 0;
    for (const child of children) {
      const d = this.subtreeDepth(child);
      if (d > max) max = d;
    }
    return max + 1;
  }

  private recomputeColWidth(): void {
    const roots = this.displayRoots();
    if (!roots.length) return;
    const columns = Math.max(...roots.map(r => this.subtreeDepth(r))) + 1;
    const avail = this.treeScrollRef?.nativeElement?.clientWidth ?? 0;
    if (avail > 0 && columns > 0) {
      const w = Math.floor((avail - 4) / columns);
      // Clamp : on réduit la largeur pour tenir, sans descendre sous un seuil
      // lisible ni dépasser une largeur confortable.
      this.colWidth.set(Math.min(260, Math.max(150, w)));
    } else {
      this.colWidth.set(240);
    }
  }

  onCellEnter(node: MindmapNode, event: MouseEvent): void {
    this.tooltipNode.set(node);
    this.tooltipX.set(event.clientX);
    this.tooltipY.set(event.clientY);
  }

  onCellMove(event: MouseEvent): void {
    this.tooltipX.set(event.clientX);
    this.tooltipY.set(event.clientY);
  }

  onCellLeave(): void {
    this.tooltipNode.set(null);
  }

  /**
   * Navigue vers la fiche détail d'un nœud (#257).
   *
   * - `operation` → fiche dédiée (`/enjeux/operations/<id>`).
   * - `enjeu` / `fcr` → page détail de l'enjeu (`/enjeux/<enjeuSlug>`).
   * - Sous-entités (OLT, NE, OO, RA, indicateur, métrique, mesure, facteur,
   *   pression, etat_enjeu) → page détail de l'enjeu ancêtre, avec un fragment
   *   `<type>-<id>` que `enjeux-list` utilise pour scroller jusqu'à l'élément
   *   précis (et déplier l'accordéon parent au passage).
   */
  private openEntity(data: MindmapNode): void {
    const slug = this.planSlug();
    if (!slug || !data.id) return;

    if (data.entityType === 'operation') {
      this.router.navigate(['/plans', slug, 'enjeux', 'operations', data.id]);
      return;
    }
    if (data.entityType === 'plan') {
      this.router.navigate(['/plans', slug]);
      return;
    }

    // Pour enjeu/fcr, navigue directement vers la page détail.
    if ((data.entityType === 'enjeu' || data.entityType === 'fcr') && data.slug) {
      this.router.navigate(['/plans', slug, 'enjeux', data.slug]);
      return;
    }

    // Sous-entité : remonter aux ancêtres pour trouver l'enjeu/FCR parent.
    let enjeuAncestor: MindmapNode | undefined;
    let cursor = this.parentMap.get(data);
    while (cursor) {
      if ((cursor.entityType === 'enjeu' || cursor.entityType === 'fcr') && cursor.slug) {
        enjeuAncestor = cursor;
        break;
      }
      cursor = this.parentMap.get(cursor);
    }

    const fragment = `${data.entityType}-${data.id}`;
    if (enjeuAncestor && enjeuAncestor.slug) {
      this.router.navigate(
        ['/plans', slug, 'enjeux', enjeuAncestor.slug],
        { fragment },
      );
      return;
    }

    // Fallback : page enjeux du plan avec fragment générique.
    this.router.navigate(['/plans', slug, 'enjeux'], { fragment });
  }

  getTextColor(hexColor: string): string {
    const hex = hexColor.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? '#343433' : '#ffffff';
  }

  constructor() {
    const legendTypes: MindmapEntityType[] = [
      'plan', 'enjeu', 'fcr', 'facteur', 'pression',
      'olt', 'etat_enjeu', 'niveau_exigence',
      'oo', 'resultat_attendu',
      'indicateur', 'metrique', 'mesure',
      'operation', 'suivi', 'protocole'
    ];
    this.legendItems = legendTypes.map(t => ({
      type: t,
      color: MINDMAP_COLORS[t],
      label: MINDMAP_LABELS[t]
    }));

    // Recalcule la largeur des colonnes dès que l'ensemble affiché change
    // (chargement initial, bascule de vue, zoom/dézoom). On mesure dans un
    // requestAnimationFrame pour que le conteneur soit mis en page au préalable.
    effect(() => {
      this.displayRoots(); // dépendance réactive
      requestAnimationFrame(() => this.recomputeColWidth());
    });
  }
}
