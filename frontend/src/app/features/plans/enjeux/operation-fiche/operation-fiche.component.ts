import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { MetriqueRef, Operation } from '../../../../core/models/enjeu.model';
import { LeafletMapEditComponent } from '../../../../shared/components/leaflet-map-edit/leaflet-map-edit.component';
import { MetriqueGridDisplayComponent } from '../../../../shared/components/metrique-grid-display/metrique-grid-display.component';
import { CheckboxComponent } from '../../../../shared/components/checkbox/checkbox.component';
import { TagComponent } from '../../../../shared/components/tag/tag.component';
import { getPrioriteTag, TagAppearance } from '../../../../shared/utils/tag-icons';

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
  imports: [CommonModule, RouterModule, TranslateModule, LeafletMapEditComponent, MetriqueGridDisplayComponent, CheckboxComponent, TagComponent],
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

  /** #566 — apparence du tag de priorité (palette scores), ou null si aucune. */
  prioriteTag(op: Operation): TagAppearance | null {
    return getPrioriteTag(op.priorite_label);
  }

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

  /**
   * #556 — Programmation annuelle, restituée « telle que saisie » : budget
   * ventilé par type (fonctionnement / investissement) et travail exprimé en
   * nombre de jours. Chaque année agrège, si nécessaire, la ventilation par
   * organisme gestionnaire (`organismes`) au niveau année.
   *
   * #560 — le travail vient des lignes RH (poste / organisme × financé), et
   * non plus du champ `etp` déprécié.
   */
  readonly programmation = computed(() =>
    [...(this.operation()?.operation_annees ?? [])]
      .sort((a, b) => a.annee - b.annee)
      .map(oa => {
        const orgs = oa.organismes ?? [];
        const sumOrg = (key: 'budget_fonctionnement' | 'budget_investissement'): number | null =>
          orgs.length ? orgs.reduce((acc, o) => acc + (o[key] ?? 0), 0) : null;
        const fonctionnement = oa.budget_fonctionnement ?? sumOrg('budget_fonctionnement');
        const investissement = oa.budget_investissement ?? sumOrg('budget_investissement');
        const rh = oa.rh_lignes ?? [];
        const jours = rh.length
          ? rh.reduce((acc, l) => acc + Number(l.jours ?? 0), 0)
          : null;
        const budget = (fonctionnement != null || investissement != null)
          ? (fonctionnement ?? 0) + (investissement ?? 0)
          : oa.budget;
        return { annee: oa.annee, periodicite: oa.periodicite, fonctionnement, investissement, budget, jours };
      })
  );

  /** Vrai si au moins une année distingue fonctionnement / investissement (#556). */
  readonly hasBudgetTypes = computed(() =>
    this.programmation().some(p => p.fonctionnement != null || p.investissement != null)
  );

  /**
   * #556 — Répartition du budget/travail par organisme gestionnaire, cumulée sur
   * toutes les années. Affichée uniquement si une ventilation a été saisie.
   */
  readonly organismeBreakdown = computed(() => {
    const byOrg = new Map<number, { nom: string; fonctionnement: number; investissement: number }>();
    for (const oa of this.operation()?.operation_annees ?? []) {
      for (const org of oa.organismes ?? []) {
        const entry = byOrg.get(org.id_organisme)
          ?? { nom: org.organisme_nom || '—', fonctionnement: 0, investissement: 0 };
        entry.fonctionnement += org.budget_fonctionnement ?? 0;
        entry.investissement += org.budget_investissement ?? 0;
        byOrg.set(org.id_organisme, entry);
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
      libelle: string; organisme: string; finance: boolean; jours: number;
    }>();
    for (const oa of this.operation()?.operation_annees ?? []) {
      for (const l of oa.rh_lignes ?? []) {
        const key = `${l.id_poste ?? ''}|${l.id_organisme ?? ''}|${l.finance}`;
        const entry = rows.get(key) ?? {
          libelle: l.poste_libelle || l.organisme_nom || '—',
          organisme: l.id_poste != null ? (l.poste_organisme_nom || '') : '',
          finance: !!l.finance,
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
  readonly protocole = computed(() => this.suiviInventaire()?.protocole ?? null);

  /** Nom du protocole (saisi librement ou repris du catalogue CAMPanule). */
  readonly protocoleNom = computed(() => {
    const p = this.protocole();
    return p?.nom_protocole || p?.protocole_campanule_nom || null;
  });

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
