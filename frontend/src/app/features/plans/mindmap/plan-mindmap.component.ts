import {
  Component, OnInit, OnDestroy, AfterViewInit,
  inject, signal, ElementRef, ViewChild, ChangeDetectorRef
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { Subscription, fromEvent, forkJoin } from 'rxjs';
import { debounceTime } from 'rxjs/operators';
import * as d3 from 'd3';

import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../core/services/admin.service';
import { EnjeuService } from '../../../core/services/enjeu.service';
import {
  MindmapNode, MindmapEntityType,
  MINDMAP_COLORS, MINDMAP_LABELS
} from '../../../core/models/mindmap.model';

interface IcicleNode extends d3.HierarchyRectangularNode<MindmapNode> {
  target?: { x0: number; x1: number; y0: number; y1: number };
}

@Component({
  selector: 'app-plan-mindmap',
  standalone: true,
  imports: [
    CommonModule, RouterModule, TranslateModule,
    MatProgressSpinnerModule, MatButtonModule,
    HeaderComponent, PlanSidebarComponent
  ],
  templateUrl: './plan-mindmap.component.html',
  styleUrl: './plan-mindmap.component.scss'
})
export class PlanMindmapComponent implements OnInit, AfterViewInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);
  private readonly enjeuService = inject(EnjeuService);
  private readonly cdr = inject(ChangeDetectorRef);

  @ViewChild('icicleContainer', { static: false }) icicleContainerRef!: ElementRef<HTMLDivElement>;
  @ViewChild('icicleInverseContainer', { static: false }) icicleInverseContainerRef!: ElementRef<HTMLDivElement>;

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

  // Icicle view state (normal)
  private icicleRoot!: IcicleNode;
  private icicleFocus!: IcicleNode;
  private icicleWidth = 0;
  private icicleHeight = 0;

  // Icicle view state (inverse)
  private icicleInverseRoot!: IcicleNode;
  private icicleInverseFocus!: IcicleNode;
  private icicleInverseWidth = 0;
  private icicleInverseHeight = 0;

  // D3 element references for programmatic focus
  private icicleSvg!: d3.Selection<SVGSVGElement, unknown, null, undefined>;
  private icicleCell!: d3.Selection<SVGGElement, IcicleNode, SVGSVGElement, unknown>;
  private icicleRect!: d3.Selection<SVGRectElement, IcicleNode, SVGGElement, unknown>;
  private icicleDefs!: d3.Selection<SVGDefsElement, unknown, null, undefined>;
  private icicleTypeText!: d3.Selection<SVGTextElement, IcicleNode, SVGGElement, unknown>;
  private icicleNameText!: d3.Selection<SVGTextElement, IcicleNode, SVGGElement, unknown>;
  private icicleViewWidth = 0;
  private icicleViewHeight = 0;

  // Same for inverse
  private icicleInverseSvg!: d3.Selection<SVGSVGElement, unknown, null, undefined>;
  private icicleInverseCell!: d3.Selection<SVGGElement, IcicleNode, SVGSVGElement, unknown>;
  private icicleInverseRect!: d3.Selection<SVGRectElement, IcicleNode, SVGGElement, unknown>;
  private icicleInverseDefs!: d3.Selection<SVGDefsElement, unknown, null, undefined>;
  private icicleInverseTypeText!: d3.Selection<SVGTextElement, IcicleNode, SVGGElement, unknown>;
  private icicleInverseNameText!: d3.Selection<SVGTextElement, IcicleNode, SVGGElement, unknown>;
  private icicleInverseViewWidth = 0;
  private icicleInverseViewHeight = 0;

  private resizeSub?: Subscription;
  private dataReady = false;
  private viewReady = false;

  constructor() {
    const legendTypes: MindmapEntityType[] = [
      'plan', 'enjeu', 'fcr', 'facteur', 'pression',
      'olt', 'etat_actuel', 'niveau_exigence',
      'oo', 'resultat_attendu',
      'indicateur', 'metrique', 'mesure',
      'operation', 'suivi', 'protocole'
    ];
    this.legendItems = legendTypes.map(t => ({
      type: t,
      color: MINDMAP_COLORS[t],
      label: MINDMAP_LABELS[t]
    }));
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

  ngAfterViewInit(): void {
    this.viewReady = true;
    if (this.dataReady) {
      requestAnimationFrame(() => this.initCurrentView());
    }

    this.resizeSub = fromEvent(window, 'resize')
      .pipe(debounceTime(200))
      .subscribe(() => this.initCurrentView());
  }

  ngOnDestroy(): void {
    this.resizeSub?.unsubscribe();
  }

  private loadData(planId: number): void {
    forkJoin({
      normal: this.enjeuService.getMindmapData(planId),
      inverse: this.enjeuService.getMindmapInverseData(planId),
    }).subscribe({
      next: ({ normal, inverse }) => {
        this.treeData.set(normal);
        this.inverseTreeData.set(inverse);
        this.loading.set(false);
        this.dataReady = true;
        this.cdr.detectChanges();
        requestAnimationFrame(() => {
          this.initCurrentView();
        });
      },
      error: () => {
        this.loading.set(false);
        this.error.set("Impossible de charger les données du tableau d'arborescence.");
      }
    });
  }

  switchView(mode: 'enjeux' | 'actions'): void {
    if (this.viewMode() === mode) return;
    this.viewMode.set(mode);
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.initCurrentView());
  }

  private initCurrentView(): void {
    if (this.viewMode() === 'enjeux') {
      this.initIcicle();
    } else {
      this.initIcicleInverse();
    }
  }

  // ========== SHARED ICICLE BUILDER ==========

  private buildIcicle(
    container: HTMLDivElement,
    data: MindmapNode,
    clipPrefix: string,
    filterChildren?: (children: MindmapNode[]) => MindmapNode[]
  ): {
    root: IcicleNode;
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
    cell: d3.Selection<SVGGElement, IcicleNode, SVGSVGElement, unknown>;
    rect: d3.Selection<SVGRectElement, IcicleNode, SVGGElement, unknown>;
    defs: d3.Selection<SVGDefsElement, unknown, null, undefined>;
    typeText: d3.Selection<SVGTextElement, IcicleNode, SVGGElement, unknown>;
    nameText: d3.Selection<SVGTextElement, IcicleNode, SVGGElement, unknown>;
    width: number;
    height: number;
  } {
    d3.select(container).selectAll('*').remove();

    const width = container.clientWidth;
    const height = container.clientHeight;

    const filteredData: MindmapNode = filterChildren
      ? { ...data, children: filterChildren(data.children || []) }
      : data;

    const hierarchy = d3.hierarchy(filteredData)
      .sum(d => (!d.children || d.children.length === 0) ? 1 : 0);

    hierarchy.eachAfter(d => {
      if (d.children && d.children.length > 0) {
        const total = d.children.reduce((s, c) => s + (c.value || 1), 0);
        if (d.children.length > 1) {
          const minVal = Math.max(1, Math.round(total / d.children.length * 0.4));
          for (const child of d.children) {
            if ((child.value || 0) < minVal) {
              (child as any).value = minVal;
            }
          }
        }
        (d as any).value = d.children.reduce((s, c) => s + (c.value || 0), 0);
      }
    });

    hierarchy.sort((a, b) => (b.value ?? 0) - (a.value ?? 0));

    let maxDepth = 0;
    hierarchy.each(d => { if (d.depth > maxDepth) maxDepth = d.depth; });
    const initialVisibleCols = 2;
    const columnWidth = width / initialVisibleCols;

    const root = d3.partition<MindmapNode>()
      .size([height, (maxDepth + 1) * columnWidth])
      .padding(1)(hierarchy) as IcicleNode;

    const svg = d3.select(container)
      .append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('width', width)
      .attr('height', height)
      .style('font-family', "'Nunito', sans-serif");

    const defs = svg.append('defs');

    const cell = svg.selectAll<SVGGElement, IcicleNode>('g')
      .data(root.descendants())
      .join('g')
      .attr('transform', d => `translate(${d.y0},${d.x0})`);

    cell.each(function(d, i) {
      defs.append('clipPath')
        .attr('id', `${clipPrefix}-${i}`)
        .append('rect')
        .attr('width', d.y1 - d.y0 - 1)
        .attr('height', d.x1 - d.x0);
    });

    const rect = cell.append('rect')
      .attr('width', d => d.y1 - d.y0 - 1)
      .attr('height', d => this.icicleRectHeight(d))
      .attr('fill', d => MINDMAP_COLORS[d.data.entityType] || '#555')
      .attr('fill-opacity', 0.85)
      .style('cursor', 'pointer');

    const textGroup = cell.append('g')
      .attr('clip-path', (_d, i) => `url(#${clipPrefix}-${i})`);

    const typeText = textGroup.append('text')
      .attr('class', 'icicle-type')
      .attr('x', 6)
      .attr('y', 14)
      .attr('fill', d => this.getTextColor(MINDMAP_COLORS[d.data.entityType] || '#555'))
      .attr('fill-opacity', d => this.typeVisible(d, width) ? 1 : 0)
      .text(d => MINDMAP_LABELS[d.data.entityType] || d.data.entityType);

    const nameText = textGroup.append('text')
      .attr('class', 'icicle-name')
      .attr('x', 6)
      .attr('y', d => this.typeVisible(d, width) ? 28 : 13)
      .attr('fill', d => this.getTextColor(MINDMAP_COLORS[d.data.entityType] || '#555'))
      .attr('fill-opacity', d => this.nameVisible(d, width) ? 1 : 0)
      .text(d => d.data.name);

    cell.append('title')
      .text(d => `${MINDMAP_LABELS[d.data.entityType] || d.data.entityType}\n${d.data.name}`);

    return { root, svg, cell, rect, defs, typeText, nameText, width, height };
  }

  private setupClickHandler(
    root: IcicleNode,
    getFocus: () => IcicleNode,
    setFocus: (n: IcicleNode) => void,
    getRoot: () => IcicleNode,
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
    cell: d3.Selection<SVGGElement, IcicleNode, SVGSVGElement, unknown>,
    rect: d3.Selection<SVGRectElement, IcicleNode, SVGGElement, unknown>,
    defs: d3.Selection<SVGDefsElement, unknown, null, undefined>,
    typeText: d3.Selection<SVGTextElement, IcicleNode, SVGGElement, unknown>,
    nameText: d3.Selection<SVGTextElement, IcicleNode, SVGGElement, unknown>,
    viewWidth: number,
    viewHeight: number
  ): void {
    cell.on('click', (_event, p) => {
      const currentFocus = getFocus();
      const focus = (currentFocus === p)
        ? (p.parent as IcicleNode || getRoot())
        : p;
      setFocus(focus);
      this.animateToFocus(focus, getRoot(), root, svg, cell, rect, defs, typeText, nameText, viewWidth, viewHeight);
    });
  }

  private animateToFocus(
    focus: IcicleNode,
    rootNode: IcicleNode,
    partitionRoot: IcicleNode,
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>,
    cell: d3.Selection<SVGGElement, IcicleNode, SVGSVGElement, unknown>,
    rect: d3.Selection<SVGRectElement, IcicleNode, SVGGElement, unknown>,
    defs: d3.Selection<SVGDefsElement, unknown, null, undefined>,
    typeText: d3.Selection<SVGTextElement, IcicleNode, SVGGElement, unknown>,
    nameText: d3.Selection<SVGTextElement, IcicleNode, SVGGElement, unknown>,
    viewWidth: number,
    viewHeight: number
  ): void {
    let maxDescY1 = focus.y1;
    focus.each((d: any) => { if (d.y1 > maxDescY1) maxDescY1 = d.y1; });

    const ySpan = maxDescY1 - focus.y0;
    const yScale = (focus === rootNode) ? 1 : (ySpan > 0 ? viewWidth / ySpan : 1);

    partitionRoot.each((d: any) => {
      d.target = {
        x0: ((d.x0 as number) - focus.x0) / (focus.x1 - focus.x0) * viewHeight,
        x1: ((d.x1 as number) - focus.x0) / (focus.x1 - focus.x0) * viewHeight,
        y0: ((d.y0 as number) - focus.y0) * yScale,
        y1: ((d.y1 as number) - focus.y0) * yScale
      };
    });

    const t = svg.transition().duration(750) as any;

    cell.transition(t)
      .attr('transform', (d: any) => `translate(${d.target.y0},${d.target.x0})`);

    rect.transition(t)
      .attr('width', (d: any) => Math.max(0, d.target.y1 - d.target.y0 - 1))
      .attr('height', (d: any) => this.icicleRectHeight(d.target));

    const descendants = partitionRoot.descendants();
    defs.selectAll<SVGRectElement, unknown>('clipPath rect').each(function(_d, i) {
      const node = descendants[i] as any;
      if (node?.target) {
        d3.select(this).transition(t)
          .attr('width', Math.max(0, node.target.y1 - node.target.y0 - 1))
          .attr('height', node.target.x1 - node.target.x0);
      }
    });

    typeText.transition(t)
      .attr('fill-opacity', (d: any) => this.typeVisible(d.target, viewWidth) ? 1 : 0);

    nameText.transition(t)
      .attr('y', (d: any) => this.typeVisible(d.target, viewWidth) ? 28 : 13)
      .attr('fill-opacity', (d: any) => this.nameVisible(d.target, viewWidth) ? 1 : 0);
  }

  // ========== NORMAL ICICLE (Enjeux view) ==========

  private initIcicle(): void {
    const data = this.treeData();
    const container = this.icicleContainerRef?.nativeElement;
    if (!data || !container) return;

    const result = this.buildIcicle(container, data, 'clip', children =>
      children.filter(c => c.entityType === 'enjeu' || c.entityType === 'fcr')
    );

    this.icicleRoot = result.root;
    this.icicleFocus = result.root;
    this.icicleWidth = result.width;
    this.icicleHeight = result.height;
    this.icicleSvg = result.svg;
    this.icicleCell = result.cell;
    this.icicleRect = result.rect;
    this.icicleDefs = result.defs;
    this.icicleTypeText = result.typeText;
    this.icicleNameText = result.nameText;
    this.icicleViewWidth = result.width;
    this.icicleViewHeight = result.height;

    this.setupClickHandler(
      result.root,
      () => this.icicleFocus,
      (n) => { this.icicleFocus = n; },
      () => this.icicleRoot,
      result.svg, result.cell, result.rect, result.defs,
      result.typeText, result.nameText,
      result.width, result.height
    );
  }

  resetIcicle(): void {
    if (!this.icicleRoot) return;
    this.icicleFocus = this.icicleRoot;
    this.animateToFocus(
      this.icicleRoot, this.icicleRoot, this.icicleRoot,
      this.icicleSvg, this.icicleCell, this.icicleRect, this.icicleDefs,
      this.icicleTypeText, this.icicleNameText,
      this.icicleViewWidth, this.icicleViewHeight
    );
  }

  focusOnEnjeu(): void {
    if (!this.icicleRoot) return;
    // Find the first enjeu or fcr child of the root
    const firstEnjeu = this.icicleRoot.children?.find(
      c => c.data.entityType === 'enjeu' || c.data.entityType === 'fcr'
    ) as IcicleNode | undefined;
    if (!firstEnjeu) return;
    this.icicleFocus = firstEnjeu;
    this.animateToFocus(
      firstEnjeu, this.icicleRoot, this.icicleRoot,
      this.icicleSvg, this.icicleCell, this.icicleRect, this.icicleDefs,
      this.icicleTypeText, this.icicleNameText,
      this.icicleViewWidth, this.icicleViewHeight
    );
  }

  // ========== INVERSE ICICLE (Actions view) ==========

  private initIcicleInverse(): void {
    const data = this.inverseTreeData();
    const container = this.icicleInverseContainerRef?.nativeElement;
    if (!data || !container) return;

    const result = this.buildIcicle(container, data, 'clip-inv');

    this.icicleInverseRoot = result.root;
    this.icicleInverseFocus = result.root;
    this.icicleInverseWidth = result.width;
    this.icicleInverseHeight = result.height;
    this.icicleInverseSvg = result.svg;
    this.icicleInverseCell = result.cell;
    this.icicleInverseRect = result.rect;
    this.icicleInverseDefs = result.defs;
    this.icicleInverseTypeText = result.typeText;
    this.icicleInverseNameText = result.nameText;
    this.icicleInverseViewWidth = result.width;
    this.icicleInverseViewHeight = result.height;

    this.setupClickHandler(
      result.root,
      () => this.icicleInverseFocus,
      (n) => { this.icicleInverseFocus = n; },
      () => this.icicleInverseRoot,
      result.svg, result.cell, result.rect, result.defs,
      result.typeText, result.nameText,
      result.width, result.height
    );
  }

  resetIcicleInverse(): void {
    if (!this.icicleInverseRoot) return;
    this.icicleInverseFocus = this.icicleInverseRoot;
    this.animateToFocus(
      this.icicleInverseRoot, this.icicleInverseRoot, this.icicleInverseRoot,
      this.icicleInverseSvg, this.icicleInverseCell, this.icicleInverseRect, this.icicleInverseDefs,
      this.icicleInverseTypeText, this.icicleInverseNameText,
      this.icicleInverseViewWidth, this.icicleInverseViewHeight
    );
  }

  focusOnOperation(): void {
    if (!this.icicleInverseRoot) return;
    const firstOp = this.icicleInverseRoot.children?.find(
      c => c.data.entityType === 'operation'
    ) as IcicleNode | undefined;
    if (!firstOp) return;
    this.icicleInverseFocus = firstOp;
    this.animateToFocus(
      firstOp, this.icicleInverseRoot, this.icicleInverseRoot,
      this.icicleInverseSvg, this.icicleInverseCell, this.icicleInverseRect, this.icicleInverseDefs,
      this.icicleInverseTypeText, this.icicleInverseNameText,
      this.icicleInverseViewWidth, this.icicleInverseViewHeight
    );
  }

  // ========== SHARED UTILITIES ==========

  private icicleRectHeight(d: { x0: number; x1: number }): number {
    return d.x1 - d.x0 - Math.min(1, (d.x1 - d.x0) / 2);
  }

  private typeVisible(d: { y0: number; y1: number; x0: number; x1: number }, viewWidth: number): boolean {
    return d.y1 <= viewWidth && d.y0 >= 0 && (d.x1 - d.x0) > 26;
  }

  private nameVisible(d: { y0: number; y1: number; x0: number; x1: number }, viewWidth: number): boolean {
    return d.y1 <= viewWidth && d.y0 >= 0 && (d.x1 - d.x0) > 13;
  }

  private getTextColor(hexColor: string): string {
    const hex = hexColor.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? '#343433' : '#ffffff';
  }
}
