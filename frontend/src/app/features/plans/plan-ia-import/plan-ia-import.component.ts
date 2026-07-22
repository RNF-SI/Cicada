import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AdminService } from '../../../core/services/admin.service';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { AdminPlan, ParsedData, ParsedRow } from '../../../core/models/admin.model';

/**
 * Module d'import IA d'un plan de gestion.
 *
 * Liste les plans **pré-remplis par l'IA en attente de relecture**. Le
 * gestionnaire en ouvre un, navigue **enjeu par enjeu** (onglets), voit
 * l'arborescence extraite dans un **arbre éditable et réorganisable** (lue
 * depuis la base), inspecte chaque élément dans un **panneau de détail**,
 * corrige, puis **valide** : l'arborescence est réécrite et le plan sort de la
 * file d'attente.
 */

interface TreeNode {
  sheet: string;
  row: ParsedRow;
  children: TreeNode[];
  parent: TreeNode | null;
}

/** Espèce (TaxRef) ou habitat (HabRef) rattaché à une cible (enjeu / indicateur). */
interface BioRef {
  code: string; // cd_nom (taxon) ou cd_hab (habitat)
  nom: string;
}

const HIERARCHY: Record<string, { sheet: string; via: string; multi?: boolean }[]> = {
  enjeux: [
    { sheet: 'olt', via: 'enjeu' },
    { sheet: 'facteurs', via: 'enjeux', multi: true },
  ],
  olt: [{ sheet: 'ne', via: 'olt' }],
  ne: [{ sheet: 'indicateurs', via: 'parent' }],
  facteurs: [{ sheet: 'pressions', via: 'facteur' }],
  pressions: [{ sheet: 'oo', via: 'pressions', multi: true }],
  oo: [{ sheet: 'ra', via: 'oo' }],
  ra: [{ sheet: 'indicateurs', via: 'parent' }],
  indicateurs: [{ sheet: 'metriques', via: 'indicateur' }],
  metriques: [],
};
const LABEL_FIELD: Record<string, string> = {
  enjeux: 'libelle', olt: 'libelle', ne: 'libelle', facteurs: 'libelle',
  pressions: 'libelle', oo: 'libelle', ra: 'libelle',
  indicateurs: 'nom_indicateur', metriques: 'nom_metrique',
};
const SHEET_LABEL: Record<string, string> = {
  enjeux: 'Enjeu', olt: 'Objectif à long terme', ne: "Niveau d'exigence",
  facteurs: "Facteur d'influence", pressions: 'Pression', oo: 'Objectif opérationnel',
  ra: 'Résultat attendu', indicateurs: 'Indicateur', metriques: 'Métrique',
};

/**
 * Champs détaillés affichés (et éditables en texte) dans le panneau, par
 * feuille. `select` = champ non-texte (catégorie, type PressRef) rendu en
 * lecture seule pour l'instant — l'édition par sélecteur arrive au commit
 * suivant. `readonly` = valeur dérivée non modifiable ici.
 */
interface DetailField {
  key: string;
  label: string;
  kind?: 'text' | 'textarea' | 'select' | 'readonly';
}
const DETAIL_FIELDS: Record<string, DetailField[]> = {
  enjeux: [
    { key: 'categorie', label: 'Catégorie', kind: 'select' },
    { key: 'categorie_fcr', label: 'Catégorie FCR', kind: 'select' },
    { key: 'importance', label: 'Importance', kind: 'readonly' },
    { key: 'rang', label: 'Priorité', kind: 'readonly' },
    { key: 'categorie_ecologique', label: 'Conservation du patrimoine naturel', kind: 'readonly' },
    { key: 'types_ecologiques', label: 'Types écologiques', kind: 'readonly' },
    { key: 'types_socioeco', label: 'Types socio-économiques', kind: 'readonly' },
    { key: 'etat_enjeu', label: "État de l'enjeu", kind: 'textarea' },
    { key: 'description', label: 'Détails / commentaires', kind: 'textarea' },
  ],
  olt: [{ key: 'description', label: 'Description', kind: 'textarea' }],
  ne: [{ key: 'description', label: 'Description', kind: 'textarea' }],
  facteurs: [{ key: 'description', label: 'Détails / commentaires', kind: 'textarea' }],
  pressions: [
    { key: 'type_pression', label: 'Type de pression (PressRef CARET)', kind: 'select' },
    { key: 'description', label: 'Détails / commentaires', kind: 'textarea' },
  ],
  oo: [{ key: 'description', label: 'Description', kind: 'textarea' }],
  ra: [{ key: 'description', label: 'Description', kind: 'textarea' }],
  indicateurs: [
    { key: 'type', label: "Type d'indicateur", kind: 'readonly' },
    { key: 'unité', label: 'Unité', kind: 'text' },
    { key: 'description', label: 'Description', kind: 'textarea' },
  ],
  metriques: [
    { key: 'type', label: 'Type de métrique', kind: 'readonly' },
    { key: 'unité', label: 'Unité', kind: 'text' },
    { key: 'description', label: 'Description', kind: 'textarea' },
  ],
};

@Component({
  selector: 'app-plan-ia-import',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule, FormsModule, MatButtonModule, MatProgressSpinnerModule,
    TranslateModule, HeaderComponent,
  ],
  templateUrl: './plan-ia-import.component.html',
  styleUrls: ['./plan-ia-import.component.scss'],
})
export class PlanIaImportComponent {
  private readonly adminService = inject(AdminService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly view = signal<'list' | 'review'>('list');
  readonly pending = signal<AdminPlan[]>([]);
  readonly loadingList = signal(true);
  readonly loadingTree = signal(false);
  readonly validating = signal(false);
  readonly error = signal<string | null>(null);

  readonly selected = signal<AdminPlan | null>(null);
  readonly roots = signal<TreeNode[]>([]);
  /** Données brutes par feuille (pour taxons/habitats non arborescents). */
  private readonly rawData = signal<ParsedData>({});
  /** Index de l'enjeu (onglet) actif. */
  readonly activeEnjeu = signal(0);
  /** Nœud sélectionné pour le panneau de détail. */
  readonly detailNode = signal<TreeNode | null>(null);

  readonly SHEET_LABEL = SHEET_LABEL;

  /** Enjeu (racine) actuellement affiché. */
  readonly activeRoot = computed<TreeNode | null>(() => {
    const r = this.roots();
    const i = this.activeEnjeu();
    return r.length ? r[Math.min(i, r.length - 1)] : null;
  });

  readonly countLabel = computed(() => {
    const n = this.countNodes(this.roots());
    return `${n} élément${n > 1 ? 's' : ''}`;
  });

  /** Champs de détail du nœud sélectionné. */
  readonly detailFields = computed<DetailField[]>(() => {
    const node = this.detailNode();
    return node ? (DETAIL_FIELDS[node.sheet] ?? []) : [];
  });

  constructor() {
    this.loadPending();
  }

  // --- Liste des plans en attente ----------------------------------------

  private loadPending(): void {
    this.loadingList.set(true);
    this.adminService.getIaPendingPlans().subscribe({
      next: plans => { this.pending.set(plans); this.loadingList.set(false); },
      error: () => {
        this.loadingList.set(false);
        this.error.set(this.translate.instant('plans.import.validateError'));
      },
    });
  }

  open(plan: AdminPlan): void {
    this.error.set(null);
    this.loadingTree.set(true);
    this.selected.set(plan);
    this.detailNode.set(null);
    this.activeEnjeu.set(0);
    this.view.set('review');
    this.adminService.getCurrentArborescence(plan.id_pg).subscribe({
      next: ({ data }) => {
        this.rawData.set(data ?? {});
        this.roots.set(this.buildTree(data));
        this.loadingTree.set(false);
      },
      error: () => {
        this.loadingTree.set(false);
        this.error.set('Impossible de charger l\'arborescence de ce plan.');
      },
    });
  }

  backToList(): void {
    this.view.set('list');
    this.roots.set([]);
    this.rawData.set({});
    this.selected.set(null);
    this.detailNode.set(null);
    this.error.set(null);
  }

  // --- Navigation par onglet / détail ------------------------------------

  selectEnjeu(i: number): void {
    this.activeEnjeu.set(i);
    this.detailNode.set(null);
  }

  showDetail(node: TreeNode): void {
    this.detailNode.set(node);
  }

  closeDetail(): void {
    this.detailNode.set(null);
  }

  /** Libellé court d'un onglet enjeu (préfixé Enjeu / FCR). */
  tabLabel(node: TreeNode, index: number): string {
    const short = String(node.row['intitule_court'] ?? '').trim();
    const full = String(node.row['libelle'] ?? '').trim();
    const text = short || full || `Enjeu ${index + 1}`;
    return text.length > 38 ? text.slice(0, 37) + '…' : text;
  }

  /** True si l'enjeu est en réalité un FCR (catégorie « Facteur Clé de Réussite »). */
  isFcr(node: TreeNode): boolean {
    if (node.sheet !== 'enjeux') return false;
    return /r[ée]ussite/i.test(String(node.row['categorie'] ?? ''));
  }

  /** Type PressRef d'une pression (affiché en chip). */
  pressRef(node: TreeNode): string {
    return node.sheet === 'pressions' ? String(node.row['type_pression'] ?? '').trim() : '';
  }

  /** Habitats / espèces rattachés à un enjeu (via le code de la cible). */
  bioForEnjeu(node: TreeNode, sheet: 'taxons' | 'habitats'): BioRef[] {
    if (node.sheet !== 'enjeux') return [];
    const code = String(node.row['code'] ?? '').trim();
    if (!code) return [];
    const keyField = sheet === 'taxons' ? 'cd_nom' : 'cd_hab';
    return ((this.rawData()[sheet] as ParsedRow[]) ?? [])
      .filter(r => String(r['cible'] ?? '').trim() === code)
      .map(r => ({ code: String(r[keyField] ?? ''), nom: String(r['nom'] ?? '') }));
  }

  // --- Construction / aplatissement de l'arbre ---------------------------

  private buildTree(data: ParsedData): TreeNode[] {
    const bySheet = (s: string): ParsedRow[] => (data[s] as ParsedRow[]) ?? [];
    const build = (sheet: string, row: ParsedRow, parent: TreeNode | null): TreeNode => {
      const node: TreeNode = { sheet, row, children: [], parent };
      for (const rel of HIERARCHY[sheet] ?? []) {
        for (const child of bySheet(rel.sheet)) {
          if (this.matches(child[rel.via], row['code'], rel.multi)) {
            node.children.push(build(rel.sheet, child, node));
          }
        }
      }
      return node;
    };
    return bySheet('enjeux').map(e => build('enjeux', e, null));
  }

  private matches(ref: unknown, code: unknown, multi?: boolean): boolean {
    const c = String(code ?? '').trim();
    const r = String(ref ?? '').trim();
    if (!c || !r) return false;
    return multi ? r.split(',').map(x => x.trim()).includes(c) : r === c;
  }

  private flatten(): ParsedData {
    const out: ParsedData = {};
    const seen: Record<string, Set<string>> = {};
    const walk = (node: TreeNode) => {
      const bucket = (out[node.sheet] ??= []) as ParsedRow[];
      const code = String(node.row['code'] ?? '');
      seen[node.sheet] ??= new Set();
      if (!code || !seen[node.sheet].has(code)) {
        if (code) seen[node.sheet].add(code);
        bucket.push(node.row);
      }
      node.children.forEach(walk);
    };
    this.roots().forEach(walk);
    // Réinjecte les feuilles bio (taxons/habitats) en ne gardant que celles dont
    // la cible existe encore dans l'arbre après réorganisation/suppression.
    const codes = new Set<string>();
    for (const rows of Object.values(out)) {
      for (const r of rows as ParsedRow[]) {
        const c = String(r['code'] ?? '').trim();
        if (c) codes.add(c);
      }
    }
    for (const sheet of ['taxons', 'habitats'] as const) {
      const kept = ((this.rawData()[sheet] as ParsedRow[]) ?? [])
        .filter(r => codes.has(String(r['cible'] ?? '').trim()));
      if (kept.length) out[sheet] = kept;
    }
    return out;
  }

  private countNodes(nodes: TreeNode[]): number {
    return nodes.reduce((n, node) => n + 1 + this.countNodes(node.children), 0);
  }

  // --- Édition / réorganisation ------------------------------------------

  label(node: TreeNode): string {
    return String(node.row[LABEL_FIELD[node.sheet]] ?? '');
  }
  setLabel(node: TreeNode, value: string): void {
    node.row[LABEL_FIELD[node.sheet]] = value;
  }

  /** Valeur d'un champ de détail. */
  fieldValue(node: TreeNode, key: string): string {
    return String(node.row[key] ?? '');
  }
  setFieldValue(node: TreeNode, key: string, value: string): void {
    node.row[key] = value;
  }

  private siblings(node: TreeNode): TreeNode[] {
    return node.parent ? node.parent.children : this.roots();
  }
  canMoveUp(node: TreeNode): boolean { return this.siblings(node).indexOf(node) > 0; }
  canMoveDown(node: TreeNode): boolean {
    const s = this.siblings(node);
    return s.indexOf(node) < s.length - 1;
  }
  move(node: TreeNode, delta: number): void {
    const s = this.siblings(node);
    const i = s.indexOf(node);
    const j = i + delta;
    if (j < 0 || j >= s.length) return;
    [s[i], s[j]] = [s[j], s[i]];
    this.roots.set([...this.roots()]);
  }
  remove(node: TreeNode): void {
    const s = this.siblings(node);
    const i = s.indexOf(node);
    if (i >= 0) s.splice(i, 1);
    if (this.detailNode() === node) this.detailNode.set(null);
    // Si on supprime l'enjeu actif, recaler l'onglet.
    if (node.sheet === 'enjeux' && this.activeEnjeu() >= this.roots().length - 1) {
      this.activeEnjeu.set(Math.max(0, this.roots().length - 2));
    }
    this.roots.set([...this.roots()]);
  }

  // --- Validation ---------------------------------------------------------

  validate(): void {
    const plan = this.selected();
    if (!plan) return;
    this.validating.set(true);
    this.error.set(null);
    // Réécrit l'arborescence (mode remplacement), puis sort de la file d'attente.
    this.adminService.importArborescenceData(plan.id_pg, this.flatten(), 'replace').subscribe({
      next: () => {
        this.adminService.markIaReviewed(plan.id_pg).subscribe({
          next: () => {
            this.validating.set(false);
            this.snackBar.open(
              'Plan relu et validé. Il n\'est plus en attente.',
              this.translate.instant('common.actions.close'),
              { duration: 4000 },
            );
            this.pending.set(this.pending().filter(p => p.id_pg !== plan.id_pg));
            this.backToList();
          },
          error: () => { this.validating.set(false); this.error.set('Réécriture faite, mais le marquage a échoué.'); },
        });
      },
      error: err => {
        this.validating.set(false);
        const body = err?.error as { issues?: { level: string; message: string }[] } | undefined;
        const first = body?.issues?.find(i => i.level === 'error')?.message;
        this.error.set(first || err?.message || 'Échec de la validation.');
      },
    });
  }
}
