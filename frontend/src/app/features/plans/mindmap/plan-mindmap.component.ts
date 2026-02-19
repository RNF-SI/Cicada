import {
  Component, OnInit, OnDestroy, AfterViewInit,
  inject, signal, ElementRef, ViewChild, ChangeDetectorRef
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { Subscription, fromEvent } from 'rxjs';
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

interface D3Node extends d3.HierarchyPointNode<MindmapNode> {
  x0?: number;
  y0?: number;
  _children?: D3Node[] | null;
}

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

  @ViewChild('svgContainer', { static: false }) svgContainerRef!: ElementRef<HTMLDivElement>;
  @ViewChild('icicleContainer', { static: false }) icicleContainerRef!: ElementRef<HTMLDivElement>;

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  loading = signal(true);
  error = signal<string | null>(null);
  treeData = signal<MindmapNode | null>(null);
  viewMode = signal<'mindmap' | 'icicle'>('icicle');

  legendItems: { type: MindmapEntityType; color: string; label: string }[] = [];

  // Tree view state
  private svg!: d3.Selection<SVGSVGElement, unknown, null, undefined>;
  private svgGroup!: d3.Selection<SVGGElement, unknown, null, undefined>;
  private treeLayout!: d3.TreeLayout<MindmapNode>;
  private root!: D3Node;
  private zoomBehavior!: d3.ZoomBehavior<SVGSVGElement, unknown>;
  private tooltip!: d3.Selection<HTMLDivElement, unknown, null, undefined>;
  private nodeIdCounter = 0;
  private resizeSub?: Subscription;
  private dataReady = false;
  private viewReady = false;

  // Icicle view state
  private icicleRoot!: IcicleNode;
  private icicleFocus!: IcicleNode;
  private icicleWidth = 0;
  private icicleHeight = 0;

  // Layout constants
  private readonly nodeVSpacing = 28;
  private readonly nodeHSpacing = 260;
  private readonly transitionDuration = 400;

  constructor() {
    // Build legend from unique entity types we care about
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
          this.loadMindmapData(plan.id_pg);
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
    this.tooltip?.remove();
  }

  switchView(mode: 'mindmap' | 'icicle'): void {
    if (this.viewMode() === mode) return;
    this.viewMode.set(mode);
    this.cdr.detectChanges();
    requestAnimationFrame(() => this.initCurrentView());
  }

  private initCurrentView(): void {
    if (this.viewMode() === 'mindmap') {
      this.initD3();
    } else {
      this.initIcicle();
    }
  }

  private loadMindmapData(planId: number): void {
    this.enjeuService.getMindmapData(planId).subscribe({
      next: (data) => {
        this.treeData.set(data);
        this.loading.set(false);
        this.dataReady = true;
        this.cdr.detectChanges();
        requestAnimationFrame(() => {
          this.initCurrentView();
        });
      },
      error: () => {
        this.loading.set(false);
        this.error.set('Impossible de charger les données de la mind map.');
      }
    });
  }

  private initD3(): void {
    const data = this.treeData();
    const container = this.svgContainerRef?.nativeElement;
    if (!data || !container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    // Clear previous
    d3.select(container).selectAll('*').remove();

    // Create tooltip
    this.tooltip = d3.select(container)
      .append('div')
      .attr('class', 'tooltip-box')
      .style('display', 'none');

    // Create SVG
    this.svg = d3.select(container)
      .append('svg')
      .attr('width', width)
      .attr('height', height);

    // Zoom behavior
    this.zoomBehavior = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 3])
      .on('zoom', (event) => {
        this.svgGroup.attr('transform', event.transform);
      });

    this.svg.call(this.zoomBehavior);

    this.svgGroup = this.svg.append('g');

    // Tree layout - horizontal (swap x/y)
    this.treeLayout = d3.tree<MindmapNode>()
      .nodeSize([this.nodeVSpacing, this.nodeHSpacing]);

    // Create hierarchy
    this.root = d3.hierarchy(data) as D3Node;
    this.root.x0 = 0;
    this.root.y0 = 0;

    // Collapse children at depth > 1
    if (this.root.children) {
      this.root.children.forEach(child => this.collapseNode(child as D3Node));
    }

    this.update(this.root);

    // Center the root
    const initialScale = 0.85;
    const initialX = width * 0.15;
    const initialY = height / 2;
    this.svg.call(
      this.zoomBehavior.transform,
      d3.zoomIdentity.translate(initialX, initialY).scale(initialScale)
    );
  }

  private collapseNode(node: D3Node): void {
    if (node.children) {
      (node as any)._children = node.children;
      (node as any)._children.forEach((c: D3Node) => this.collapseNode(c));
      (node as any).children = null;
    }
  }

  private expandNode(node: D3Node): void {
    if ((node as any)._children) {
      node.children = (node as any)._children;
      (node as any)._children = null;
      if (node.children) {
        node.children.forEach((c: D3Node) => this.expandNode(c));
      }
    }
  }

  private update(source: D3Node): void {
    // Compute new tree layout
    this.treeLayout(this.root);

    const nodes = this.root.descendants() as D3Node[];
    const links = this.root.links() as d3.HierarchyPointLink<MindmapNode>[];

    // Assign unique IDs
    nodes.forEach(d => {
      if (!(d as any).id) {
        (d as any).id = ++this.nodeIdCounter;
      }
    });

    // ========== LINKS ==========
    const linkSelection = this.svgGroup.selectAll<SVGPathElement, d3.HierarchyPointLink<MindmapNode>>('path.link')
      .data(links, (d: any) => (d.target as any).id);

    // ENTER
    const linkEnter = linkSelection.enter()
      .insert('path', 'g')
      .attr('class', 'link')
      .attr('d', () => {
        const o = { x: source.x0 ?? 0, y: source.y0 ?? 0 };
        return this.diagonal(o, o);
      })
      .attr('stroke', d => {
        const color = MINDMAP_COLORS[d.target.data.entityType] || '#555';
        return color + '40'; // 25% opacity
      });

    // UPDATE
    const linkUpdate = linkEnter.merge(linkSelection);
    linkUpdate.transition()
      .duration(this.transitionDuration)
      .attr('d', d => this.diagonal(d.source as any, d.target as any));

    // EXIT
    linkSelection.exit()
      .transition()
      .duration(this.transitionDuration)
      .attr('d', () => {
        const o = { x: source.x ?? 0, y: source.y ?? 0 };
        return this.diagonal(o, o);
      })
      .remove();

    // ========== NODES ==========
    const nodeSelection = this.svgGroup.selectAll<SVGGElement, D3Node>('g.node')
      .data(nodes, (d: any) => d.id);

    // ENTER
    const nodeEnter = nodeSelection.enter()
      .append('g')
      .attr('class', 'node')
      .attr('transform', () => `translate(${source.y0 ?? 0},${source.x0 ?? 0})`)
      .on('click', (_event, d) => this.toggleNode(d))
      .on('mouseenter', (event, d) => this.showTooltip(event, d))
      .on('mouseleave', () => this.hideTooltip());

    // Circle
    nodeEnter.append('circle')
      .attr('r', 1e-6)
      .attr('fill', d => MINDMAP_COLORS[d.data.entityType] || '#555');

    // Label
    nodeEnter.append('text')
      .attr('dy', '0.35em')
      .attr('x', d => this.hasChildren(d) ? -14 : 14)
      .attr('text-anchor', d => this.hasChildren(d) ? 'end' : 'start')
      .text(d => this.truncateLabel(d.data.name, d.depth))
      .style('font-size', d => this.getFontSize(d.depth));

    // Collapsed count text (inside circle)
    nodeEnter.append('text')
      .attr('class', 'node-count')
      .text(d => this.getCollapsedCount(d));

    // UPDATE
    const nodeUpdate = nodeEnter.merge(nodeSelection);
    nodeUpdate.transition()
      .duration(this.transitionDuration)
      .attr('transform', d => `translate(${d.y},${d.x})`);

    nodeUpdate.select('circle')
      .attr('r', d => this.getNodeRadius(d.depth))
      .attr('fill', d => MINDMAP_COLORS[d.data.entityType] || '#555');

    nodeUpdate.select('text:not(.node-count)')
      .attr('x', d => this.hasChildren(d) ? -(this.getNodeRadius(d.depth) + 6) : (this.getNodeRadius(d.depth) + 6))
      .attr('text-anchor', d => this.hasChildren(d) ? 'end' : 'start');

    nodeUpdate.select('.node-count')
      .text(d => this.getCollapsedCount(d));

    // EXIT
    const nodeExit = nodeSelection.exit()
      .transition()
      .duration(this.transitionDuration)
      .attr('transform', () => `translate(${source.y},${source.x})`)
      .remove();

    nodeExit.select('circle').attr('r', 1e-6);
    nodeExit.select('text').style('fill-opacity', 1e-6);

    // Store positions for next transition
    nodes.forEach(d => {
      d.x0 = d.x;
      d.y0 = d.y;
    });
  }

  private diagonal(s: { x: number; y: number }, d: { x: number; y: number }): string {
    return `M ${s.y} ${s.x}
            C ${(s.y + d.y) / 2} ${s.x},
              ${(s.y + d.y) / 2} ${d.x},
              ${d.y} ${d.x}`;
  }

  private toggleNode(d: D3Node): void {
    if (d.children) {
      (d as any)._children = d.children;
      (d as any).children = null;
    } else if ((d as any)._children) {
      d.children = (d as any)._children;
      (d as any)._children = null;
    }
    this.update(d);
  }

  private hasChildren(d: D3Node): boolean {
    return !!(d.children && d.children.length > 0) || !!((d as any)._children && (d as any)._children.length > 0);
  }

  private getCollapsedCount(d: D3Node): string {
    const collapsed = (d as any)._children;
    if (collapsed && collapsed.length > 0) {
      return `+${collapsed.length}`;
    }
    return '';
  }

  private getNodeRadius(depth: number): number {
    if (depth === 0) return 12;
    if (depth === 1) return 8;
    return 6;
  }

  private getFontSize(depth: number): string {
    if (depth === 0) return '14px';
    if (depth <= 2) return '12px';
    return '11px';
  }

  private truncateLabel(name: string, depth: number): string {
    const maxLen = depth === 0 ? 60 : depth <= 2 ? 40 : 30;
    if (name.length > maxLen) {
      return name.substring(0, maxLen - 1) + '\u2026';
    }
    return name;
  }

  private showTooltip(event: MouseEvent, d: D3Node): void {
    const container = this.svgContainerRef?.nativeElement;
    if (!container || !this.tooltip) return;

    const rect = container.getBoundingClientRect();
    const x = event.clientX - rect.left + 12;
    const y = event.clientY - rect.top - 10;

    const label = MINDMAP_LABELS[d.data.entityType] || d.data.entityType;

    this.tooltip
      .style('display', 'block')
      .style('left', `${x}px`)
      .style('top', `${y}px`)
      .html(`<div class="tooltip-type">${label}</div><div class="tooltip-name">${d.data.name}</div>`);
  }

  private hideTooltip(): void {
    this.tooltip?.style('display', 'none');
  }

  // ========== ICICLE VIEW ==========

  private initIcicle(): void {
    const data = this.treeData();
    const container = this.icicleContainerRef?.nativeElement;
    if (!data || !container) return;

    // Clear previous
    d3.select(container).selectAll('*').remove();

    const width = container.clientWidth;
    const height = container.clientHeight;
    this.icicleWidth = width;
    this.icicleHeight = height;

    // Filter root children to only show enjeux and FCR at the first layer
    const filteredData: MindmapNode = {
      ...data,
      children: (data.children || []).filter(
        c => c.entityType === 'enjeu' || c.entityType === 'fcr'
      )
    };

    // Build hierarchy - count leaves, then clamp minimum proportions
    // so small siblings (état actuel, opération…) stay readable
    const hierarchy = d3.hierarchy(filteredData)
      .sum(d => (!d.children || d.children.length === 0) ? 1 : 0);

    // Bottom-up pass: ensure each child gets at least 40% of the average
    // sibling value, so leaf nodes are never squeezed to invisible slivers
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

    // Compute max depth for column sizing
    // Initial view: 2 columns visible (Plan + Enjeux)
    let maxDepth = 0;
    hierarchy.each(d => { if (d.depth > maxDepth) maxDepth = d.depth; });
    const initialVisibleCols = 2;
    const columnWidth = width / initialVisibleCols;

    // Partition layout: x-axis = vertical (rows), y-axis = horizontal (columns)
    // Total width spans ALL depth levels, but only 2 columns visible initially
    const root = d3.partition<MindmapNode>()
      .size([height, (maxDepth + 1) * columnWidth])
      .padding(1)(hierarchy) as IcicleNode;

    this.icicleRoot = root;
    this.icicleFocus = root;

    const svg = d3.select(container)
      .append('svg')
      .attr('viewBox', `0 0 ${width} ${height}`)
      .attr('width', width)
      .attr('height', height)
      .style('font-family', "'Nunito', sans-serif");

    // Defs for clip paths
    const defs = svg.append('defs');

    const cell = svg.selectAll<SVGGElement, IcicleNode>('g')
      .data(root.descendants())
      .join('g')
      .attr('transform', d => `translate(${d.y0},${d.x0})`);

    // One clipPath per cell to prevent text overflow
    cell.each(function(d, i) {
      defs.append('clipPath')
        .attr('id', `clip-${i}`)
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

    // Text group clipped to cell bounds
    const textGroup = cell.append('g')
      .attr('clip-path', (_d, i) => `url(#clip-${i})`);

    // Entity type label (small, bold, uppercase) — visible when height >= 26
    const typeText = textGroup.append('text')
      .attr('class', 'icicle-type')
      .attr('x', 6)
      .attr('y', 14)
      .attr('fill', d => this.getTextColor(MINDMAP_COLORS[d.data.entityType] || '#555'))
      .attr('fill-opacity', d => this.icicleTypeVisible(d) ? 1 : 0)
      .text(d => MINDMAP_LABELS[d.data.entityType] || d.data.entityType);

    // Name label — visible when height >= 13, moves up when type is hidden
    const nameText = textGroup.append('text')
      .attr('class', 'icicle-name')
      .attr('x', 6)
      .attr('y', d => this.icicleTypeVisible(d) ? 28 : 13)
      .attr('fill', d => this.getTextColor(MINDMAP_COLORS[d.data.entityType] || '#555'))
      .attr('fill-opacity', d => this.icicleNameVisible(d) ? 1 : 0)
      .text(d => d.data.name);

    // Click handler — rescales both axes so all descendant columns fit
    cell.on('click', (_event, p) => {
      const focus = (this.icicleFocus === p)
        ? (p.parent as IcicleNode || this.icicleRoot)
        : p;
      this.icicleFocus = focus;

      // Compute the max y extent among all descendants of the focused node
      let maxDescY1 = focus.y1;
      focus.each((d: any) => { if (d.y1 > maxDescY1) maxDescY1 = d.y1; });

      // y-scale: fit all descendant columns into the viewport width
      // For root: use 1 (no rescale, keeps initial 2-column view)
      const ySpan = maxDescY1 - focus.y0;
      const yScale = (focus === this.icicleRoot) ? 1 : (ySpan > 0 ? width / ySpan : 1);

      root.each((d: any) => {
        d.target = {
          x0: ((d.x0 as number) - focus.x0) / (focus.x1 - focus.x0) * height,
          x1: ((d.x1 as number) - focus.x0) / (focus.x1 - focus.x0) * height,
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

      // Update clip rects to match new cell dimensions
      const descendants = root.descendants();
      defs.selectAll<SVGRectElement, unknown>('clipPath rect').each(function(_d, i) {
        const node = descendants[i] as any;
        if (node?.target) {
          d3.select(this).transition(t)
            .attr('width', Math.max(0, node.target.y1 - node.target.y0 - 1))
            .attr('height', node.target.x1 - node.target.x0);
        }
      });

      typeText.transition(t)
        .attr('fill-opacity', (d: any) => this.icicleTypeVisible(d.target) ? 1 : 0);

      nameText.transition(t)
        .attr('y', (d: any) => this.icicleTypeVisible(d.target) ? 28 : 13)
        .attr('fill-opacity', (d: any) => this.icicleNameVisible(d.target) ? 1 : 0);
    });

    // Hover title
    cell.append('title')
      .text(d => `${MINDMAP_LABELS[d.data.entityType] || d.data.entityType}\n${d.data.name}`);
  }

  private icicleRectHeight(d: { x0: number; x1: number }): number {
    return d.x1 - d.x0 - Math.min(1, (d.x1 - d.x0) / 2);
  }

  /** Type label visible when cell is tall enough for 2 lines (type + name) */
  private icicleTypeVisible(d: { y0: number; y1: number; x0: number; x1: number }): boolean {
    return d.y1 <= this.icicleWidth && d.y0 >= 0 && (d.x1 - d.x0) > 26;
  }

  /** Name label visible when cell has room for at least 1 line of text */
  private icicleNameVisible(d: { y0: number; y1: number; x0: number; x1: number }): boolean {
    return d.y1 <= this.icicleWidth && d.y0 >= 0 && (d.x1 - d.x0) > 13;
  }

  private getTextColor(hexColor: string): string {
    const hex = hexColor.replace('#', '');
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminance > 0.5 ? '#343433' : '#ffffff';
  }

  resetIcicle(): void {
    if (!this.icicleRoot) return;
    this.icicleFocus = this.icicleRoot;
    // Re-init from scratch to reset zoom state cleanly
    this.initIcicle();
  }

  // ========== PUBLIC CONTROLS ==========

  expandAll(): void {
    if (!this.root) return;
    this.expandNode(this.root);
    this.update(this.root);
  }

  collapseAll(): void {
    if (!this.root || !this.root.children) return;
    this.root.children.forEach(child => this.collapseNode(child as D3Node));
    this.update(this.root);
  }

  resetZoom(): void {
    if (!this.svg || !this.zoomBehavior) return;
    const container = this.svgContainerRef?.nativeElement;
    if (!container) return;
    const width = container.clientWidth;
    const height = container.clientHeight;
    const scale = 0.85;
    this.svg.transition()
      .duration(this.transitionDuration)
      .call(
        this.zoomBehavior.transform,
        d3.zoomIdentity.translate(width * 0.15, height / 2).scale(scale)
      );
  }
}
