import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { MetriqueRef, Operation, Protocole } from '../../../../core/models/enjeu.model';
import { CategorieDepense } from '../../../../core/models/rh.model';
import {
  fonctDetailPrev, investDetailPrev, salarialCost, yearBudgetPrev, yearJoursPrev,
} from '../../../../shared/utils/operation-budget';
import { LeafletMapEditComponent } from '../../../../shared/components/leaflet-map-edit/leaflet-map-edit.component';
import { MetriqueGridDisplayComponent } from '../../../../shared/components/metrique-grid-display/metrique-grid-display.component';
import { PriorityBadgeComponent } from '../../../../shared/components/priority-badge/priority-badge.component';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ProtocoleCampanuleDialogComponent } from '../../../../shared/components/modals/protocole-campanule-dialog/protocole-campanule-dialog.component';
import {
  ExportFicheActionDialogComponent,
  ExportFicheActionDialogData,
  ExportFicheActionDialogResult,
} from '../../../../shared/components/modals/export-fiche-action-dialog/export-fiche-action-dialog.component';

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
  imports: [CommonModule, RouterModule, TranslateModule, LeafletMapEditComponent, MetriqueGridDisplayComponent, PriorityBadgeComponent],
  templateUrl: './operation-fiche.component.html',
  styleUrl: './operation-fiche.component.scss',
})
export class OperationFicheComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly enjeuService = inject(EnjeuService);
  private readonly translate = inject(TranslateService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

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
    { key: 'protocole', labelKey: 'plans.suivis.actions.fiche.protocole' },
    { key: 'temporalite', labelKey: 'plans.suivis.actions.fiche.temporalite' },
    { key: 'acteurs', labelKey: 'plans.suivis.actions.fiche.acteurs' },
    { key: 'programmation', labelKey: 'plans.suivis.actions.fiche.programmation' },
    { key: 'indicateursReponse', labelKey: 'plans.suivis.actions.fiche.indicateursReponse' },
    { key: 'emprise', labelKey: 'plans.suivis.actions.fiche.emprise' },
    { key: 'realisation', labelKey: 'plans.suivis.actions.fiche.realisation' },
  ] as const;

  /** Visibilité par section (toutes cochées/affichées par défaut). */
  readonly sectionVisibility = signal<Record<string, boolean>>(
    Object.fromEntries(this.toggleableSections.map(s => [s.key, true])),
  );

  /** #642 — export Excel en cours (désactive le bouton le temps du téléchargement). */
  readonly isExporting = signal(false);

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

  /**
   * #613 — Cadre indicateurs affiché en tête de fiche : simple LISTE d'intitulés
   * (indicateurs d'état/pression + métriques avec unité), sans la grille de
   * scoring, « pour réduire la taille ». Le libellé s'adapte au type.
   */
  readonly cadreIndicateurs = computed(() => {
    const inds = this.indicateursEtatPression();
    if (!inds.length) return null;
    const isEtat = inds.some(i => (i.type ?? '').toUpperCase() === 'ETAT');
    const noms: string[] = [];
    const metriques: string[] = [];
    const seenN = new Set<string>();
    const seenM = new Set<string>();
    for (const i of inds) {
      const n = (i.nom ?? '').trim();
      if (n && !seenN.has(n)) { seenN.add(n); noms.push(n); }
      for (const m of i.metriqueRefs) {
        const nom = (m.nom_metrique ?? '').trim();
        if (!nom) continue;
        const label = m.unite ? `${nom} (${m.unite})` : nom;
        if (!seenM.has(label)) { seenM.add(label); metriques.push(label); }
      }
    }
    return {
      labelKey: isEtat
        ? 'plans.suivis.actions.fiche.cadreIndicateurEtat'
        : 'plans.suivis.actions.fiche.cadreIndicateurPression',
      indicateurs: noms.join(' ; '),
      metriques: metriques.join(' ; '),
    };
  });

  /**
   * #556 — Programmation annuelle, restituée « telle que saisie » : budget
   * ventilé par type (fonctionnement / investissement) et travail exprimé en
   * nombre de jours. Chaque année agrège, si nécessaire, la ventilation par
   * organisme gestionnaire (`organismes`) au niveau année.
   *
   * #560 — le travail vient des lignes RH (poste / organisme × financé), et
   * non plus du champ `etp` déprécié.
   */
  readonly programmation = computed(() => {
    const op = this.operation();
    if (!op) return [];
    return [...(op.operation_annees ?? [])]
      .sort((a, b) => a.annee - b.annee)
      .map(oa => {
        // #613 — le budget est DÉRIVÉ des composants réellement saisis (détail
        // des coûts + coût salarial des lignes RH) : dans les modes « + type de
        // poste », les enveloppes `budget_fonctionnement` / `_investissement`
        // ne sont pas stockées et la fiche affichait 0 €.
        const { fonctionnement, investissement, total } = yearBudgetPrev(op, oa);
        return {
          annee: oa.annee,
          periodicite: oa.periodicite,
          fonctionnement,
          investissement,
          budget: total,
          jours: yearJoursPrev(oa),
        };
      });
  });

  /**
   * #613 — Détail des coûts, cumulé sur toutes les années : la fiche doit être
   * « aussi précise que ce qui est saisi ». Une ligne par composant
   * (coût salarial calculé, stage, prestataire, autres coûts), ventilée
   * fonctionnement / investissement. Masqué si l'action n'en porte aucun.
   */
  readonly coutDetail = computed(() => {
    const op = this.operation();
    if (!op) return { rows: [], totalFonct: 0, totalInvest: 0 };
    const annees = op.operation_annees ?? [];
    const fonct = { salarial: 0, stage: 0, prestataire: 0, autres: 0 };
    const invest = { salarial: 0, stage: 0, prestataire: 0, autres: 0 };
    for (const oa of annees) {
      const f = fonctDetailPrev(op, oa);
      const i = investDetailPrev(op, oa);
      // #613 — le coût salarial (jours × coût/jour) est TOUJOURS valorisé dès
      // qu'un poste porte un coût/jour, quel que soit le mode. C'est un
      // affichage : il n'entre PAS dans le budget total (yearBudgetPrev), pour ne
      // pas doubler une enveloppe ni écraser un total saisi.
      fonct.salarial += salarialCost(oa.rh_lignes, 'fonctionnement');
      invest.salarial += salarialCost(oa.rh_lignes, 'investissement');
      // Composants hors salarial (déjà exposés séparément par les helpers).
      fonct.stage += f.stage; fonct.prestataire += f.prestataire; fonct.autres += f.autres;
      invest.stage += i.stage; invest.prestataire += i.prestataire; invest.autres += i.autres;
    }
    const totalFonct = fonct.salarial + fonct.stage + fonct.prestataire + fonct.autres;
    const totalInvest = invest.salarial + invest.stage + invest.prestataire + invest.autres;
    const rows = [
      { key: 'coutSalarial', fonct: fonct.salarial, invest: invest.salarial },
      { key: 'coutStage', fonct: fonct.stage, invest: invest.stage },
      { key: 'coutPrestataire', fonct: fonct.prestataire, invest: invest.prestataire },
      { key: 'autresCouts', fonct: fonct.autres, invest: invest.autres },
    ].filter(r => r.fonct !== 0 || r.invest !== 0);
    return { rows, totalFonct, totalInvest };
  });

  /** Vrai si au moins un composant de coût est renseigné (#613). */
  readonly hasCoutDetail = computed(() => this.coutDetail().rows.length > 0);

  /** Vrai si au moins une année distingue fonctionnement / investissement (#556). */
  readonly hasBudgetTypes = computed(() =>
    this.programmation().some(p => p.fonctionnement != null || p.investissement != null)
  );

  /**
   * #556 — Répartition du budget/travail par organisme gestionnaire, cumulée sur
   * toutes les années. Affichée uniquement si une ventilation a été saisie.
   */
  readonly organismeBreakdown = computed(() => {
    interface OrgRow { nom: string; fonctionnement: number; investissement: number; }
    const byOrg = new Map<number, OrgRow>();
    const ensure = (id: number, nom: string): OrgRow => {
      let e = byOrg.get(id);
      if (!e) { e = { nom, fonctionnement: 0, investissement: 0 }; byOrg.set(id, e); }
      return e;
    };
    for (const oa of this.operation()?.operation_annees ?? []) {
      for (const org of oa.organismes ?? []) {
        const e = ensure(org.id_organisme, org.organisme_nom || '—');
        // Fonctionnement = budget saisi (mode « par organisme + type ») OU somme des
        // coûts (mode « + type de poste » : stage + prestataire + autres) — #600/#602.
        e.fonctionnement += (this.toNum(org.budget_fonctionnement) ?? 0)
          + (this.toNum(org.cout_stage) ?? 0)
          + (this.toNum(org.cout_prestataire) ?? 0)
          + (this.toNum(org.autre_cout) ?? 0);
        e.investissement += (this.toNum(org.budget_investissement) ?? 0)
          + (this.toNum(org.cout_prestataire_invest) ?? 0)
          + (this.toNum(org.autre_cout_invest) ?? 0);
      }
      // Coût salarial = jours × coût jour, attribué à l'organisme du poste, ventilé
      // par catégorie de dépense de la ligne RH (#597/#602).
      for (const l of oa.rh_lignes ?? []) {
        const orgId = l.poste_id_organisme;
        const coutJour = this.toNum(l.poste_cout_jour);
        if (orgId == null || coutJour == null) continue;
        const e = byOrg.get(orgId);
        if (!e) continue;
        const categorie = l.categorie_depense ?? (l.finance ? 'fonctionnement' : 'benevolat_partenariat');
        // #613 — le temps « bénévolat partenariat » est valorisé en JOURS, pas
        // en euros : il ne pèse sur aucune des deux enveloppes (même convention
        // qu'à l'export, cf. `services_export_finance`).
        if (categorie === 'benevolat_partenariat') continue;
        const montant = Number(l.jours ?? 0) * coutJour;
        if (categorie === 'investissement') e.investissement += montant;
        else e.fonctionnement += montant;
      }
    }
    return [...byOrg.values()].map(e => ({ ...e, budget: e.fonctionnement + e.investissement }));
  });

  /**
   * #560 — Temps de travail cumulé sur toutes les années, par cible (poste ou
   * organisme selon le mode de saisie de l'action) et par financement. Une même
   * cible peut porter deux lots (financé / non financé) : ils restent
   * distincts, c'est tout l'objet de la valorisation du temps non financé.
   */
  readonly rhBreakdown = computed(() => {
    const rows = new Map<string, {
      libelle: string; organisme: string; finance: boolean;
      categorie: CategorieDepense; jours: number;
    }>();
    for (const oa of this.operation()?.operation_annees ?? []) {
      for (const l of oa.rh_lignes ?? []) {
        const categorie: CategorieDepense =
          l.categorie_depense ?? (l.finance ? 'fonctionnement' : 'benevolat_partenariat');
        const key = `${l.id_poste ?? ''}|${l.id_organisme ?? ''}|${categorie}`;
        // #580 — une ligne sans cible (poste ou organisme) est un temps de
        // travail total, saisi sans déclinaison ni ventilation par organisme.
        const globalLabel = this.translate.instant('enjeux.operations.rh.globalRowLabel');
        const entry = rows.get(key) ?? {
          libelle: l.poste_libelle || l.organisme_nom || globalLabel,
          organisme: l.id_poste != null ? (l.poste_organisme_nom || '') : '',
          finance: categorie !== 'benevolat_partenariat',
          categorie,
          jours: 0,
        };
        entry.jours += Number(l.jours ?? 0);
        rows.set(key, entry);
      }
    }
    return [...rows.values()].sort((a, b) => a.libelle.localeCompare(b.libelle));
  });

  /** Vrai si l'action porte du temps non financé (bénévoles, écovolontaires…). */
  readonly hasRhNonFinance = computed(() =>
    this.rhBreakdown().some(r => !r.finance && r.jours > 0)
  );

  /** Total du temps de travail, ventilé financé / non financé (#560). */
  readonly totalJoursFinance = computed(() =>
    this.rhBreakdown().filter(r => r.finance).reduce((a, r) => a + r.jours, 0)
  );
  readonly totalJoursNonFinance = computed(() =>
    this.rhBreakdown().filter(r => !r.finance).reduce((a, r) => a + r.jours, 0)
  );

  /**
   * #581 — Coercition d'un décimal DRF (souvent une chaîne "500.00") en nombre.
   * Renvoie `null` pour null/undefined/vide/non numérique afin de préserver la
   * distinction « pas de valeur » (→ `—`) de « valeur nulle ».
   */
  private toNum(v: number | string | null | undefined): number | null {
    if (v == null || v === '') return null;
    const n = Number(v);
    return Number.isNaN(n) ? null : n;
  }

  /** Somme d'une colonne de la programmation (null si aucune valeur). */
  private sumProg(key: 'fonctionnement' | 'investissement' | 'budget' | 'jours'): number | null {
    const vals = this.programmation().map(p => p[key]).filter((v): v is number => v != null);
    return vals.length ? vals.reduce((a, b) => a + Number(b), 0) : null;
  }

  readonly totalFonctionnement = computed(() => this.sumProg('fonctionnement'));
  readonly totalInvestissement = computed(() => this.sumProg('investissement'));
  /** Total budget programmé (somme des budgets annuels renseignés). */
  readonly totalBudget = computed(() => this.sumProg('budget'));
  /** Total du travail programmé, en nombre de jours (#556). */
  readonly totalJours = computed(() => this.sumProg('jours'));

  /** Sources de financement de l'action. */
  readonly financements = computed(() => this.operation()?.finances ?? []);

  /**
   * #557 — Suivi/inventaire et protocole associés (actions de type « CS »).
   * Le protocole et ses objectifs/cibles n'étaient pas restitués dans la fiche.
   */
  readonly suiviInventaire = computed(() => this.operation()?.suivi_inventaire ?? null);

  /**
   * Protocoles du suivi (#252). Repli sur `protocole` singulier pour les
   * réponses d'API antérieures.
   */
  readonly protocoles = computed(() => {
    const s = this.suiviInventaire();
    if (s?.protocoles?.length) return s.protocoles;
    return s?.protocole ? [s.protocole] : [];
  });

  /** Premier protocole — sert au détail quand il n'y en a qu'un. */
  readonly protocole = computed<Protocole | null>(() => this.protocoles()[0] ?? null);

  /**
   * Nom des protocoles, compacté sur une ligne (#252, réponse 5 de l'issue :
   * « il faut que les protocoles soient compactés dans la visualisation »).
   */
  readonly protocoleNom = computed(() => {
    const noms = this.protocoles()
      .map((p) => p.nom_protocole || p.protocole_campanule_nom)
      .filter((n): n is string => !!n);
    return noms.length ? noms.join(' · ') : null;
  });

  /** Le détail (description, objectif) n'est affiché que pour un protocole unique. */
  readonly showProtocoleDetail = computed(() => this.protocoles().length === 1);

  /** Libellé compact d'un protocole (nom CAMPanule sinon nom libre). */
  protocoleLabel(p: Protocole): string {
    return p.protocole_campanule_nom?.trim() || p.nom_protocole?.trim() || '';
  }

  /**
   * #593 — Ouvre la fiche CAMPanule d'un protocole depuis la fiche action, pour
   * consulter son détail sans quitter la page.
   */
  consulterProtocole(p: Protocole): void {
    if (!p.cd_protocole_campanule) return;
    this.dialog.open(ProtocoleCampanuleDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { cdProtocole: p.cd_protocole_campanule },
    });
  }

  /** Vrai dès qu'une information de protocole/suivi est renseignée. */
  readonly hasProtocoleSection = computed(() => {
    const s = this.suiviInventaire();
    const p = this.protocole();
    return !!(this.protocoleNom() || p?.description_protocole || p?.objectif_protocole
      || s?.objectif_principal || s?.objectif_secondaire
      || s?.cibles_principales || s?.cible_secondaire);
  });

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
   * #642 — Point d'entrée unique « Exporter ou imprimer » de la barre d'actions.
   *
   * La modale porte le choix du format (impression / PDF, ou classeur Excel au
   * modèle CICADA) et, pour l'impression seulement, le choix des sections à
   * inclure (#532 — auparavant un bouton distinct, qui chargeait la barre).
   */
  openExportDialog(): void {
    const op = this.operation();
    const ref = this.dialog.open(ExportFicheActionDialogComponent, {
      width: '640px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        actionLabel: op
          ? `${op.code_affichage || op.code_prefix || ''} ${op.libelle}`.trim()
          : '',
        sections: this.toggleableSections,
        sectionVisibility: this.sectionVisibility(),
      } satisfies ExportFicheActionDialogData,
    });
    ref.afterClosed().subscribe((result?: ExportFicheActionDialogResult) => {
      if (!result) return;
      this.sectionVisibility.set({ ...result.sections });
      if (result.format === 'xlsx') {
        this.exportXlsx();
        return;
      }
      // Laisse Angular appliquer le choix des sections AVANT d'ouvrir la
      // fenêtre d'impression : sinon le document imprimé est celui d'avant.
      setTimeout(() => this.print(), 0);
    });
  }

  /** #642 — télécharge la fiche au format Excel (un onglet, modèle CICADA). */
  private exportXlsx(): void {
    const op = this.operation();
    if (!op || this.isExporting()) return;
    this.isExporting.set(true);
    this.enjeuService.downloadOperationFicheXlsx(op.id_operation).subscribe({
      next: (blob) => {
        this.isExporting.set(false);
        const code = op.code_affichage || op.code_prefix || `action-${op.id_operation}`;
        this.triggerBlobDownload(blob, `fiche-action-${code}.xlsx`);
      },
      error: (err: { status?: number }) => {
        this.isExporting.set(false);
        // Les exports sont réservés aux référents du plan / gestionnaires : on
        // le dit explicitement plutôt que de laisser un échec silencieux.
        const key = err?.status === 403
          ? 'plans.exports.noPermission'
          : 'plans.exports.downloadError';
        this.snackBar.open(
          this.translate.instant(key),
          this.translate.instant('common.actions.close'),
          { duration: 6000 },
        );
      },
    });
  }

  private triggerBlobDownload(blob: Blob, filename: string): void {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
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
