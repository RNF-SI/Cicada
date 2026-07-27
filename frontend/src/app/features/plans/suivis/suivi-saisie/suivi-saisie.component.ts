/**
 * Page de saisie d'un suivi de réalisation (Phase 2 - Suivis).
 *
 * Route : /plans/:slug/suivis/saisie/:operation_id/:annee
 *
 * Modes de ventilation gérés :
 *   - 'none'        : budget + ETP saisis au niveau de l'année (un seul jeu de champs)
 *   - 'by_type'     : split fonctionnement / investissement au niveau de l'année
 *   - 'by_org'      : un sous-tableau par organisme, budget total par organisme
 *   - 'by_org_type' : un sous-tableau par organisme avec fonct + invest
 * Dans les deux modes ventilés par organisme, une ligne TOTAL agrège les organismes.
 *
 * La carte SIG et les indicateurs de réponse seront ajoutés en itération suivante.
 */
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import {
  AbstractControl, FormArray, FormBuilder, FormGroup, FormsModule, ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin, of } from 'rxjs';

import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';
import { EmpriseEditorComponent } from '../../../../shared/components/emprise-editor/emprise-editor.component';
import { AdminService } from '../../../../core/services/admin.service';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { RealisationService } from '../../../../core/services/realisation.service';
import { RhService } from '../../../../core/services/rh.service';
import { Poste, OperationRHLigne, CategorieDepense } from '../../../../core/models/rh.model';
import { Mesure, MesureCreatePayload } from '../../../../core/models/enjeu.model';
import {
  Operation,
  OperationAnnee,
  OperationAnneeOrganisme,
  RealisationUpsertPayload,
  RealisationOrganismeUpsertPayload,
} from '../../../../core/models/enjeu.model';
import { formatScoreRange, computeMetriqueScore, computeCombinedScore, scoreLevelName, formatBlockFormula } from '../metrique-seuils.util';

interface Niveau {
  id_nomenclature: number;
  mnemonique: string;
  label: string;
}

/** Mêmes statuts que plan-suivi-actions, partagés pour cohérence visuelle. */
type ActionStatus = 'planned' | 'planned-realized' | 'planned-partial' | 'realized-unplanned' | 'partial-unplanned';

@Component({
  selector: 'app-suivi-saisie',
  standalone: true,
  imports: [
    CommonModule, RouterModule, FormsModule, ReactiveFormsModule,
    MatButtonModule, MatProgressSpinnerModule, MatSnackBarModule,
    MatSelectModule,
    TranslateModule,
    MatTooltipModule,
    HeaderComponent, PlanSidebarComponent, FormFieldComponent,
    EmpriseEditorComponent,
  ],
  templateUrl: './suivi-saisie.component.html',
  styleUrl: './suivi-saisie.component.scss',
})
export class SuiviSaisieComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly snack = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly adminService = inject(AdminService);
  private readonly enjeuService = inject(EnjeuService);
  private readonly realisationService = inject(RealisationService);
  private readonly rhService = inject(RhService);

  // -------- Routing / context --------
  planSlug = signal<string | null>(null);
  planId = signal<number | null>(null);
  planNom = signal<string>('');
  planStatut = signal<string | null>(null);
  // #418 — plage d'années du PLAN (et non de l'action) : permet la saisie d'un
  // suivi sur une année où l'action n'était pas programmée (« réalisée non prévue »).
  planYearStart = signal<number | null>(null);
  planYearEnd = signal<number | null>(null);
  operationId = signal<number | null>(null);
  selectedYear = signal<number>(new Date().getFullYear());

  // #379 — la saisie n'est possible qu'une fois le plan validé. Sinon, la page
  // reste consultable mais le formulaire est désactivé (source d'erreurs sinon).
  private readonly VALIDATED_STATUSES = ['valide', 'modifie', 'mi_parcours', 'archive'];
  planNotValidated = computed(() => {
    const s = this.planStatut();
    return !!s && !this.VALIDATED_STATUSES.includes(s);
  });

  // -------- Data --------
  operation = signal<Operation | null>(null);
  niveaux = signal<Niveau[]>([]);

  // #379 — Le formulaire ne propose que 3 niveaux : Réalisée / Partiellement
  // réalisée / Non réalisée (les autres mnémoniques restent en base pour les
  // données historiques et le statut global).
  private readonly NIVEAU_SAISIE: { mnemonique: string; labelKey: string }[] = [
    { mnemonique: 'TERMINE', labelKey: 'plans.suivis.saisie.niveau.realisee' },
    { mnemonique: 'PARTIEL', labelKey: 'plans.suivis.saisie.niveau.partielle' },
    { mnemonique: 'NON_REALISE', labelKey: 'plans.suivis.saisie.niveau.nonRealisee' },
  ];
  niveauSaisieOptions = computed<{ id: number; labelKey: string }[]>(() => {
    const byMnem = new Map(this.niveaux().map(n => [n.mnemonique, n]));
    return this.NIVEAU_SAISIE
      .map(o => {
        const n = byMnem.get(o.mnemonique);
        return n ? { id: n.id_nomenclature, labelKey: o.labelKey } : null;
      })
      .filter((x): x is { id: number; labelKey: string } => x !== null);
  });
  isLoading = signal(true);
  isSaving = signal(false);
  errorMessage = signal<string | null>(null);

  /** #609 — affiche l'erreur « niveau obligatoire » après une tentative d'enregistrement. */
  showNiveauError = signal(false);

  /** Mnémonique d'un niveau de réalisation depuis son id (ou null). */
  private niveauMnemo(id: number | null | undefined): string | null {
    if (id == null) return null;
    return this.niveaux().find(n => n.id_nomenclature === id)?.mnemonique ?? null;
  }

  /**
   * #609 — Périodicité réalisée dérivée du niveau : « réalisé » (TERMINE) ou
   * « partiellement réalisé » (PARTIEL) ⇒ cochée ; sinon décochée.
   */
  private periodiciteFromNiveau(niveauId: number | null | undefined): boolean {
    const m = this.niveauMnemo(niveauId);
    return m === 'TERMINE' || m === 'PARTIEL';
  }

  /**
   * Mode édition de l'emprise réalisée. Quand `true`, on remplace la
   * `app-leaflet-map` (lecture seule) par `app-leaflet-map-edit`
   * (avec outils de dessin Leaflet-Draw). L'emprise prévue de l'opération
   * reste affichée en arrière-plan (pointillés terra-cotta) comme repère.
   */
  isEditingGeom = signal(false);

  /**
   * Emprise réalisée en cours d'édition (avant sauvegarde).
   * `undefined` = pas de modification locale, on utilise la valeur serveur.
   * `null` = l'utilisateur a effacé la géométrie.
   */
  pendingGeomRealisee = signal<any | undefined>(undefined);

  // -------- Form --------
  form: FormGroup = this.fb.group({
    // #609 — le niveau de réalisation est obligatoire pour enregistrer un suivi.
    id_niveau_realisation: [null, Validators.required],
    // #609 — la périodicité réalisée n'est plus saisie : elle est dérivée du
    // niveau (réalisé / partiel → cochée, non réalisé → décochée). Conservée dans
    // le form pour la rétro-compat des données existantes.
    periodicite_realisee: [false],
    budget_realise: [null],
    budget_fonctionnement_realise: [null],
    budget_investissement_realise: [null],
    etp_realise: [null],
    // #541 — opérateur(s)/financeur(s) réalisés (par année).
    operateurs_realises: [''],
    financeurs_realises: [''],
    commentaires: [''],
    /** Une ligne par organisme quand ventilation_mode ∈ {by_org, by_org_type}. */
    organismes: this.fb.array<FormGroup>([]),
    /** Une ligne par métrique liée à l'opération (indicateurs de réponse). */
    indicateurs: this.fb.array<FormGroup>([]),
    /** #560 — une ligne par temps de travail réalisé (poste/organisme). */
    rhLignes: this.fb.array<FormGroup>([]),
  });

  /** Helper d'accès typé aux FormArrays. */
  get organismesFA(): FormArray<FormGroup> {
    return this.form.get('organismes') as FormArray<FormGroup>;
  }
  get indicateursFA(): FormArray<FormGroup> {
    return this.form.get('indicateurs') as FormArray<FormGroup>;
  }
  get rhLignesFA(): FormArray<FormGroup> {
    return this.form.get('rhLignes') as FormArray<FormGroup>;
  }

  // #560 — postes du PG, cibles possibles du temps de travail réalisé.
  postes = signal<Poste[]>([]);

  /**
   * Ce que le tableau RH cible, aligné sur le mode de saisie de l'action :
   * ses postes si elle est déclinée, sinon les organismes de la ventilation
   * budgétaire, sinon un temps total sans cible (#580 — mode global).
   */
  rhMode = computed<'postes' | 'organismes' | 'global'>(() => {
    const op = this.operation();
    if (op?.declinaison_par_poste) return 'postes';
    const mode = op?.ventilation_mode;
    return mode === 'by_org' || mode === 'by_org_type' ? 'organismes' : 'global';
  });

  /** Organismes de la ventilation de l'action (cibles en mode organisme). */
  rhOrganismes = computed<{ id_organisme: number; nom_organisme: string }[]>(() => {
    const map = new Map<number, { id_organisme: number; nom_organisme: string }>();
    for (const oa of this.operation()?.operation_annees ?? []) {
      for (const oao of oa.organismes ?? []) {
        if (oao.id_organisme != null && !map.has(oao.id_organisme)) {
          map.set(oao.id_organisme, {
            id_organisme: oao.id_organisme,
            nom_organisme: oao.organisme_nom ?? '',
          });
        }
      }
    }
    return Array.from(map.values()).sort((a, b) =>
      a.nom_organisme.localeCompare(b.nom_organisme),
    );
  });

  /** Mesures existantes par metrique_id, pré-chargées au load. */
  private mesuresByMetrique = new Map<number, Mesure[]>();

  // -------- Computed --------
  ventilationMode = computed<
    'none' | 'by_org' | 'by_type' | 'by_org_type' | 'by_type_poste' | 'by_org_type_poste'
  >(() => {
    return this.operation()?.ventilation_mode ?? 'none';
  });

  /** Mode supporté par le MVP : pas de ventilation par organisme (#600 inclus). */
  isOrgVentilation = computed(() => {
    const mode = this.ventilationMode();
    return mode === 'by_org' || mode === 'by_org_type' || mode === 'by_org_type_poste';
  });

  /** Affiche la décomposition fonctionnement/investissement. */
  isByType = computed(() => {
    const m = this.ventilationMode();
    return m === 'by_type' || m === 'by_type_poste';
  });

  /**
   * #608 — ventilation maximale : le tableau de réalisation détaille les coûts
   * (salarial auto + prestataire + autres) par organisme et par type de budget.
   */
  isMaxVentilation = computed(() => this.ventilationMode() === 'by_org_type_poste');

  // ---- #608 — coûts salariaux RÉALISÉS calculés (jours réalisés × coût jour) --

  /**
   * Coût salarial réalisé d'un organisme pour une année et une catégorie de
   * dépense (fonctionnement / investissement). Pour l'année active, on lit les
   * lignes RH en cours d'édition (form) ; pour les autres années, les lignes
   * réalisées enregistrées côté serveur.
   */
  realCoutSalarial(year: number, orgId: number, categorie: 'fonctionnement' | 'investissement'): number {
    const posteById = (id: number | null | undefined) =>
      id == null ? undefined : this.postes().find(p => p.id_poste === id);

    if (year === this.selectedYear()) {
      let total = 0;
      for (const c of this.rhLignesFA.controls) {
        const poste = posteById(c.get('id_poste')?.value);
        if (!poste || poste.id_organisme !== orgId) continue;
        if ((c.get('categorie_depense')?.value ?? 'fonctionnement') !== categorie) continue;
        total += (Number(c.get('jours')?.value) || 0) * (Number(poste.cout_jour ?? 0) || 0);
      }
      return total;
    }

    const oa = this.getOaForYear(year);
    let total = 0;
    for (const r of oa?.realisation?.rh_lignes ?? []) {
      const poste = posteById(r.id_poste);
      if (!poste || poste.id_organisme !== orgId) continue;
      if ((r.categorie_depense ?? 'fonctionnement') !== categorie) continue;
      total += (Number(r.jours) || 0) * (Number(poste.cout_jour ?? 0) || 0);
    }
    return total;
  }

  /** Valeur d'un champ coût réalisé d'un organisme pour une année (form si active, sinon serveur). */
  private realOrgCost(year: number, orgId: number, field:
    'cout_stage_realise' | 'cout_prestataire_realise' | 'autre_cout_realise'
    | 'cout_prestataire_invest_realise' | 'autre_cout_invest_realise'): number {
    if (year === this.selectedYear()) {
      const grp = this.organismesFA.controls.find(c => c.get('id_organisme')?.value === orgId);
      return Number(grp?.get(field)?.value) || 0;
    }
    const oao = this.getOaoForYearOrg(year, orgId);
    return Number((oao?.realisation as any)?.[field]) || 0;
  }

  /** Total fonctionnement réalisé d'un organisme/année (salarial + stage + prestataire + autres). */
  realOrgFonctTotal(year: number, orgId: number): number {
    return this.realCoutSalarial(year, orgId, 'fonctionnement')
      + this.realOrgCost(year, orgId, 'cout_stage_realise')
      + this.realOrgCost(year, orgId, 'cout_prestataire_realise')
      + this.realOrgCost(year, orgId, 'autre_cout_realise');
  }

  /** Total investissement réalisé d'un organisme/année. */
  realOrgInvestTotal(year: number, orgId: number): number {
    return this.realCoutSalarial(year, orgId, 'investissement')
      + this.realOrgCost(year, orgId, 'cout_prestataire_invest_realise')
      + this.realOrgCost(year, orgId, 'autre_cout_invest_realise');
  }

  /** Budget total réalisé d'un organisme/année (fonct + invest). */
  realOrgTotal(year: number, orgId: number): number {
    return this.realOrgFonctTotal(year, orgId) + this.realOrgInvestTotal(year, orgId);
  }

  /** Cumuls inter-organismes réalisés (mode ventilation maximale). */
  realYearFonctTotal(year: number): number {
    return this.organismesList().reduce((s, o) => s + this.realOrgFonctTotal(year, o.id_organisme), 0);
  }
  realYearInvestTotal(year: number): number {
    return this.organismesList().reduce((s, o) => s + this.realOrgInvestTotal(year, o.id_organisme), 0);
  }
  realYearTotal(year: number): number {
    return this.realYearFonctTotal(year) + this.realYearInvestTotal(year);
  }

  /**
   * Années affichées en onglets. #418 — on couvre toute la plage du PLAN (et non
   * la seule plage de l'action), afin de permettre la saisie d'un suivi sur une
   * année où l'action n'était pas programmée (« réalisée non prévue »). Repli sur
   * la plage de l'action si la plage du plan est inconnue. L'année sélectionnée
   * (depuis l'URL) est toujours incluse par sécurité.
   */
  years = computed<number[]>(() => {
    const op = this.operation();
    let start = this.planYearStart();
    let end = this.planYearEnd();
    if (start == null || end == null) {
      // Repli : plage de l'action
      start = op?.annee_min ?? null;
      end = op?.annee_max ?? null;
    }
    const set = new Set<number>();
    if (start != null && end != null) {
      for (let y = start; y <= end; y++) set.add(y);
    }
    // Inclure l'année ciblée par l'URL même si hors plage connue.
    const sel = this.selectedYear();
    if (sel) set.add(sel);
    return [...set].sort((a, b) => a - b);
  });

  /** Programmation de l'année active (prévisionnel). */
  currentOperationAnnee = computed<OperationAnnee | null>(() => {
    const op = this.operation();
    const year = this.selectedYear();
    return op?.operation_annees?.find(oa => oa.annee === year) ?? null;
  });

  /** Emprise prévue (operation.geom). Affichée en arrière-plan/repère. */
  plannedGeom = computed<any>(() => this.operation()?.geom_geojson ?? null);

  /**
   * Emprise réalisée à afficher/éditer : priorité aux modifications locales
   * (`pendingGeomRealisee`), sinon valeur du serveur pour l'année active.
   */
  realisedGeom = computed<any>(() => {
    const pending = this.pendingGeomRealisee();
    if (pending !== undefined) return pending;
    return this.currentOperationAnnee()?.realisation?.geom_realisee ?? null;
  });

  // (Plus de FeatureCollection : on partage le même composant
  // `app-leaflet-map-edit` entre lecture et écriture, ce qui permet
  // d'utiliser `backgroundGeometry` pour l'emprise prévue dans les deux
  // modes — pas besoin d'aplatir en FeatureCollection.)

  /** Capture les modifications de l'éditeur d'emprise. */
  onGeomRealiseeChange(geom: any): void {
    this.pendingGeomRealisee.set(geom);
  }

  /** Vrai s'il existe une emprise prévue (emprise de l'action) à copier (#434). */
  hasPlannedGeom = computed<boolean>(() => this.plannedGeom() != null);

  /**
   * #511 — Instantané de l'état de l'emprise réalisée juste AVANT une copie de
   * l'emprise prévue, pour pouvoir revenir en arrière si on s'est trompé.
   * `null` = aucune copie annulable en cours.
   */
  private empriseSnapshot = signal<{ geom: any | undefined; editing: boolean } | null>(null);

  /** Vrai si une copie de l'emprise prévue peut être annulée (#511). */
  canUndoCopyEmprise = computed<boolean>(() => this.empriseSnapshot() != null);

  /**
   * #434 — Copie l'emprise prévue (emprise de l'action) comme emprise réalisée
   * et bascule en mode édition pour pouvoir l'ajuster. La carte se recharge via
   * le binding `[geometry]="realisedGeom()"` (qui lit `pendingGeomRealisee`).
   * #511 — Mémorise l'état précédent pour permettre un retour en arrière.
   */
  copyPlannedEmprise(): void {
    const planned = this.plannedGeom();
    if (planned == null) return;
    // Mémoriser l'état courant avant écrasement (pour l'annulation #511).
    this.empriseSnapshot.set({
      geom: this.pendingGeomRealisee(),
      editing: this.isEditingGeom(),
    });
    // Clone pour éviter de partager la référence avec l'emprise prévue affichée
    // en arrière-plan.
    this.pendingGeomRealisee.set(structuredClone(planned));
    this.isEditingGeom.set(true);
  }

  /**
   * #511 — Annule la dernière copie de l'emprise prévue et restaure l'emprise
   * réalisée telle qu'elle était avant la copie.
   */
  undoCopyPlannedEmprise(): void {
    const snapshot = this.empriseSnapshot();
    if (snapshot == null) return;
    this.pendingGeomRealisee.set(snapshot.geom);
    this.isEditingGeom.set(snapshot.editing);
    this.empriseSnapshot.set(null);
  }

  /** Retourne l'OperationAnnee pour une année donnée (ou null). */
  getOaForYear(year: number): OperationAnnee | null {
    return this.operation()?.operation_annees?.find(oa => oa.annee === year) ?? null;
  }

  /** #418 — vrai si l'action était PROGRAMMÉE cette année (périodicité prévue).
   *  Sert à distinguer visuellement les onglets « prévu » / « non prévu ». */
  isYearPlanned(year: number): boolean {
    return !!this.getOaForYear(year)?.periodicite;
  }

  /** Liste des organismes ventilés pour le mode by_org/by_org_type (déduplication entre années). */
  organismesList = computed<{ id_organisme: number; nom: string }[]>(() => {
    if (!this.isOrgVentilation()) return [];
    const op = this.operation();
    const seen = new Map<number, string>();
    for (const oa of op?.operation_annees || []) {
      for (const oao of oa.organismes || []) {
        if (!seen.has(oao.id_organisme)) {
          seen.set(oao.id_organisme, oao.organisme_nom || `Org #${oao.id_organisme}`);
        }
      }
    }
    return [...seen.entries()].map(([id_organisme, nom]) => ({ id_organisme, nom }));
  });

  /** Retourne l'OperationAnneeOrganisme pour un (year, organisme_id). */
  getOaoForYearOrg(year: number, orgId: number) {
    const oa = this.getOaForYear(year);
    return oa?.organismes?.find(o => o.id_organisme === orgId) ?? null;
  }

  // -------- Icônes statut programmation (mêmes que plan-suivi-actions) --------
  private readonly actionIconMap: Record<ActionStatus, string> = {
    'planned': 'assets/images/icons/prevu.png',
    'planned-realized': 'assets/images/icons/prevu-realise.png',
    'planned-partial': 'assets/images/icons/prevu-partiellement-realise.png',
    'realized-unplanned': 'assets/images/icons/realise.png',
    'partial-unplanned': 'assets/images/icons/partiellement-realise.png',
  };

  /** Statut d'une cellule (operation, année). Utilise les mêmes règles que plan-suivi-actions. */
  getCellStatus(oa: OperationAnnee | null): ActionStatus | null {
    if (!oa) return null;
    const prevu = !!oa.periodicite;
    const niveau = oa.realisation?.niveau_realisation_mnemonique ?? null;
    const realiseTotal = niveau === 'TERMINE';
    const realisePartiel = niveau === 'PARTIEL';
    if (prevu) {
      if (realiseTotal) return 'planned-realized';
      if (realisePartiel) return 'planned-partial';
      return 'planned';
    }
    if (realiseTotal) return 'realized-unplanned';
    if (realisePartiel) return 'partial-unplanned';
    return null;
  }

  /** URL de l'icône pour un statut donné (ou chaîne vide si null). */
  getCellIcon(oa: OperationAnnee | null): string {
    const st = this.getCellStatus(oa);
    return st ? this.actionIconMap[st] : '';
  }

  /** Helper d'affichage pour les cellules numériques (€/jours). */
  formatNumber(value: any, suffix: string = ''): string {
    if (value === null || value === undefined || value === '') return '—';
    const num = typeof value === 'number' ? value : parseFloat(value);
    if (isNaN(num)) return '—';
    return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 2 }).format(num) + suffix;
  }

  /** Totaux ventilés par année — pour ligne TOTAL en mode by_org/by_org_type. */
  getTotalForYear(year: number, key: 'prev_fonct' | 'prev_invest' | 'prev_etp'
                                  | 'real_fonct' | 'real_invest' | 'real_etp'): number {
    const oa = this.getOaForYear(year);
    if (!oa) return 0;
    let sum = 0;
    for (const oao of oa.organismes || []) {
      switch (key) {
        case 'prev_fonct':  sum += Number(oao.budget_fonctionnement || 0); break;
        case 'prev_invest': sum += Number(oao.budget_investissement || 0); break;
        case 'prev_etp':    sum += Number(oao.etp || 0); break;
        case 'real_fonct':  sum += Number(oao.realisation?.budget_fonctionnement_realise || 0); break;
        case 'real_invest': sum += Number(oao.realisation?.budget_investissement_realise || 0); break;
        case 'real_etp':    sum += Number(oao.realisation?.etp_realise || 0); break;
      }
    }
    return sum;
  }

  ngOnInit(): void {
    // #356 — fragment d'URL (ex. depuis la page globale d'action) pour scroller
    // automatiquement vers une section (les indicateurs de réponse, en bas).
    this.requestedFragment = this.route.snapshot.fragment;

    this.route.paramMap.subscribe(params => {
      const slug = params.get('slug');
      const opId = params.get('operation_id');
      const annee = params.get('annee');

      this.planSlug.set(slug);
      if (opId) this.operationId.set(Number(opId));
      if (annee) this.selectedYear.set(Number(annee));

      this.loadData();
    });
  }

  /** Fragment cible (#indicateurs-reponse) à scroller une fois la page chargée. */
  private requestedFragment: string | null = null;

  /** Scrolle vers le fragment demandé (une seule fois), après rendu de la section. */
  private scrollToRequestedFragment(): void {
    const frag = this.requestedFragment;
    if (!frag) return;
    this.requestedFragment = null;
    setTimeout(() => {
      document.getElementById(frag)?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 400);
  }

  private loadData(): void {
    const slug = this.planSlug();
    const opId = this.operationId();
    if (!slug || !opId) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    // Plan (pour breadcrumb + sidebar) — slug → plan via AdminService
    this.adminService.getPlanBySlug(slug).subscribe({
      next: (plan) => {
        this.planId.set(plan.id_pg);
        this.planNom.set(plan.nom);
        this.planStatut.set(plan.statut ?? null);
        this.planYearStart.set(plan.annee_debut ?? null);
        this.planYearEnd.set(plan.annee_fin ?? null);
        // #560 — postes du PG, pour la saisie / ré-attribution du RH réalisé.
        this.rhService.getPostesByPlan(plan.id_pg).subscribe(
          (list) => this.postes.set(list),
        );
        this.applyReadOnlyLock();
      },
      error: (err) => {
        this.errorMessage.set(this.translate.instant('plans.suivis.saisie.errors.planNotFound'));
        this.isLoading.set(false);
      },
    });

    // Nomenclature niveaux de réalisation
    this.adminService.getNomenclaturesByType('NIVEAU_REALISATION').subscribe({
      next: (list) => this.niveaux.set(list),
      error: () => this.niveaux.set([]),
    });

    // Opération + sa programmation annuelle et ses réalisations
    this.enjeuService.getOperation(opId).subscribe({
      next: (op) => {
        this.operation.set(op);
        this.loadMesuresForMetriques(op);
        this.hydrateFormFromCurrentYear();
        this.isLoading.set(false);
        this.scrollToRequestedFragment();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('plans.suivis.saisie.errors.operationNotFound'));
        this.isLoading.set(false);
      },
    });
  }

  /**
   * #542 — Métriques des seuls indicateurs de RÉPONSE de l'action. La page de
   * saisie du suivi ne concerne que les indicateurs de réponse ; sans ce filtre,
   * toutes les métriques d'état/pression liées à l'action remontaient aussi dans
   * la section « Indicateurs de réponse ». Miroir de `action-global`.
   */
  private responseMetriques(op: Operation): any[] {
    return (op.metriques || []).filter(
      (m: any) => (m.indicateur_type || '').toString().toUpperCase() === 'REPONSE',
    );
  }

  /** Charge les Mesures existantes pour chaque métrique de l'opération. */
  private loadMesuresForMetriques(op: Operation): void {
    this.mesuresByMetrique.clear();
    const metriques = this.responseMetriques(op);
    if (!metriques.length) {
      this.hydrateIndicateursArray();
      return;
    }
    let remaining = metriques.length;
    for (const m of metriques) {
      this.enjeuService.getMesuresByMetrique(m.id_metrique).subscribe({
        next: (list) => this.mesuresByMetrique.set(m.id_metrique, list),
        error: () => this.mesuresByMetrique.set(m.id_metrique, []),
        complete: () => {
          if (--remaining === 0) this.hydrateIndicateursArray();
        },
      });
    }
  }

  /**
   * Mesure retenue pour une année : la PLUS RÉCENTE (date_mesure, puis date_ajout).
   * Une métrique peut avoir plusieurs mesures la même année ; on choisit
   * déterministiquement la dernière, pour être cohérent avec la page globale
   * de l'action et la page globale de l'indicateur.
   */
  private latestMesureForYear(mesures: Mesure[], year: number): Mesure | undefined {
    return mesures
      .filter(mm => mm.date_mesure && new Date(mm.date_mesure).getFullYear() === year)
      .sort((a, b) => {
        const da = new Date(a.date_mesure!).getTime();
        const db = new Date(b.date_mesure!).getTime();
        if (db !== da) return db - da;
        return new Date(b.date_ajout ?? 0).getTime() - new Date(a.date_ajout ?? 0).getTime();
      })[0];
  }

  /** Reconstruit le FormArray des indicateurs depuis les métriques liées. */
  private hydrateIndicateursArray(): void {
    const fa = this.indicateursFA;
    while (fa.length) fa.removeAt(0);

    const op = this.operation();
    const year = this.selectedYear();
    if (!op?.metriques?.length) return;

    // #542 — n'hydrater que les métriques des indicateurs de réponse.
    for (const met of this.responseMetriques(op)) {
      const mesures = this.mesuresByMetrique.get(met.id_metrique) ?? [];
      const existing = this.latestMesureForYear(mesures, year);

      const grp = this.fb.group({
        id_metrique: [met.id_metrique],
        nom_metrique: [met.nom_metrique],
        indicateur_nom: [met.indicateur_nom],
        // « Valeur cible » stockée dans etat_reference côté Metrique
        // (cf. operation-form, accordéon « Indicateur(s) de réponse »).
        valeur_cible: [met.etat_reference ?? ''],
        id_mesure: [existing?.id_mesure ?? null],
        valeur: [existing?.valeur ?? ''],
        // #452/#464/#465 — métadonnées de format/grille pour une saisie type-aware
        // (select des libellés TEXTE, valeurs CHIFFRE, input numérique NUMERIQUE).
        format_mnemo: [met.format_metrique_mnemonique ?? null],
        type_mnemo: [met.type_metrique_mnemonique ?? null],
        meta: [met],
      });
      // #247 — un contrôle par bloc complémentaire (métrique multi-blocs),
      // restauré depuis la mesure existante (valeurs_blocs indexé par position).
      const vb = existing?.valeurs_blocs || {};
      for (const b of ((met as any).score_blocks || [])) {
        (grp as FormGroup).addControl(`bloc_${b.position}`, this.fb.control(vb[String(b.position)] ?? ''));
      }
      fa.push(grp);
    }
    this.applyReadOnlyLock();
  }

  /**
   * #452/#464/#465 — Mode de saisie d'un indicateur de réponse selon son format
   * (SIMPLE / GRILLE) et son type (TEXTE / CHIFFRE / NUMERIQUE) :
   *  - `text-select`   : grille TEXTE → select des libellés (#464)
   *  - `chiffre-select`: grille CHIFFRE → select des valeurs discrètes
   *  - `number`        : CHIFFRE/NUMERIQUE sans grille de libellés → input numérique (#465)
   *  - `text`          : valeur libre (comportement historique)
   */
  saisieMode(ctrl: AbstractControl): 'text-select' | 'chiffre-select' | 'number' | 'text' {
    const v = ctrl.value;
    const type = v?.type_mnemo;
    // #464/#465 — une métrique TEXTE/CHIFFRE se saisit en choisissant une des
    // options de sa grille (libellés / valeurs), qu'elle soit un indicateur de
    // réponse en grille OU une métrique d'état/pression associée. Seul le cas
    // « réponse SIMPLE » (saisie libre, sans grille) reste un champ libre.
    const isSimpleResponse = v?.format_mnemo === 'SIMPLE';
    if (!isSimpleResponse && (type === 'TEXTE' || type === 'CHIFFRE') && this.gridOptions(ctrl).length > 0) {
      return type === 'TEXTE' ? 'text-select' : 'chiffre-select';
    }
    if (type === 'CHIFFRE' || type === 'NUMERIQUE') return 'number';
    return 'text';
  }

  /** Libellés (TEXTE) ou valeurs (CHIFFRE) sélectionnables, issus de la grille
   *  de la métrique (niveaux actifs uniquement). */
  gridOptions(ctrl: AbstractControl): string[] {
    const meta: any = ctrl.value?.meta;
    if (!meta) return [];
    const inactive: number[] = Array.isArray(meta.inactive_levels) ? meta.inactive_levels : [];
    const type = ctrl.value?.type_mnemo;
    const out: string[] = [];
    for (let lvl = 1; lvl <= 5; lvl++) {
      if (inactive.includes(lvl)) continue;
      if (type === 'TEXTE') {
        const label = (meta[`score_${lvl}_label`] ?? '').toString().trim();
        if (label) out.push(label);
      } else if (type === 'CHIFFRE') {
        const val = meta[`score_${lvl}_val`];
        if (val !== null && val !== undefined) out.push(String(val));
      }
    }
    return out;
  }

  /** #452 — Vrai si l'indicateur de réponse utilise une grille de scoring : on
   *  rappelle alors la grille (5 niveaux) sous le champ de saisie. */
  isGrille(ctrl: AbstractControl): boolean {
    return ctrl.value?.format_mnemo === 'GRILLE';
  }

  /**
   * #452 — Rappel de la grille d'évaluation d'un indicateur de réponse : les 5
   * niveaux avec leur libellé/valeur/intervalle (cf. saisie d'un indicateur
   * d'état/pression). Le niveau correspondant à la valeur saisie est marqué
   * `active`. Les niveaux désactivés sont marqués `inactive`.
   */
  gridLevels(ctrl: AbstractControl): { level: number; name: string; text: string; inactive: boolean; active: boolean }[] {
    const meta: any = ctrl.value?.meta;
    return this.buildGridLevels(meta, ctrl.value?.valeur);
  }

  /** Rappel de grille (5 niveaux) pour une métrique/bloc donné + valeur saisie. */
  private buildGridLevels(meta: any, value: any): { level: number; name: string; text: string; inactive: boolean; active: boolean }[] {
    if (!meta) return [];
    const inactive: number[] = Array.isArray(meta.inactive_levels) ? meta.inactive_levels : [];
    const activeLevel = computeMetriqueScore(meta, value);
    const out: { level: number; name: string; text: string; inactive: boolean; active: boolean }[] = [];
    for (let lvl = 1; lvl <= 5; lvl++) {
      out.push({
        level: lvl,
        name: scoreLevelName(lvl),
        text: formatScoreRange(meta, lvl),
        inactive: inactive.includes(lvl),
        active: activeLevel === lvl,
      });
    }
    return out;
  }

  // #247 — Saisie multi-blocs d'un indicateur de réponse (une valeur par bloc).

  /** Vrai si la métrique de réponse a des blocs complémentaires. */
  isMultiBlock(ctrl: AbstractControl): boolean {
    return (ctrl.value?.meta?.score_blocks?.length ?? 0) > 0;
  }

  private blockLabelText(intitule?: string | null, unite?: string | null, fallback = ''): string {
    const i = (intitule ?? '').trim();
    const u = (unite ?? '').trim();
    if (!i) return fallback;
    return u ? `${i} (${u})` : i;
  }

  /** Descripteurs des champs par bloc : principal (`valeur`) + `bloc_{position}`.
   *  #247 — chaque bloc porte sa propre unité (les blocs peuvent en avoir des différentes). */
  blockInputs(ctrl: AbstractControl): { ctrl: string; label: string; unite: string; meta: any }[] {
    const meta: any = ctrl.value?.meta;
    const blocks: any[] = meta?.score_blocks || [];
    const out = [{
      ctrl: 'valeur',
      label: this.blockLabelText(meta?.bloc_intitule, meta?.unite, meta?.nom_metrique),
      unite: (meta?.unite ?? '').trim(),
      meta,
    }];
    blocks.forEach((b, idx) => {
      out.push({
        ctrl: `bloc_${b.position}`,
        label: this.blockLabelText(b.intitule, b.unite, `Bloc ${idx + 2}`),
        unite: (b.unite ?? '').trim(),
        meta: { ...b, type_metrique_mnemonique: 'NUMERIQUE' },
      });
    });
    return out;
  }

  /** Pondération de la métrique de réponse (défaut 1). */
  ponderation(ctrl: AbstractControl): number {
    const p = ctrl.value?.meta?.ponderation;
    return p == null || p === '' ? 1 : Number(p);
  }

  /** Formule ET/OU des blocs (rappel des liens) — vide si mono-bloc. */
  blockFormula(ctrl: AbstractControl): string {
    return formatBlockFormula(ctrl.value?.meta);
  }

  /** Rappel de grille d'un bloc donné (input `bloc_{position}` ou `valeur`). */
  blockGridLevels(ctrl: AbstractControl, controlName: string, meta: any) {
    return this.buildGridLevels(meta, ctrl.get(controlName)?.value);
  }

  /** Score combiné 1-5 (formule ET/OU) de la métrique multi-blocs. */
  combinedScore(ctrl: AbstractControl): number | null {
    const meta: any = ctrl.value?.meta;
    if (!meta) return null;
    const blockValues: Record<string, any> = {};
    for (const b of (meta.score_blocks || [])) {
      blockValues[String(b.position)] = ctrl.get(`bloc_${b.position}`)?.value;
    }
    return computeCombinedScore(meta, ctrl.get('valeur')?.value, blockValues);
  }

  /** Nom de badge (very-bad…very-good) du score combiné, ou null. */
  combinedScoreName(ctrl: AbstractControl): string | null {
    const s = this.combinedScore(ctrl);
    return s == null ? null : scoreLevelName(s);
  }

  /**
   * #379 — Verrou lecture seule : si le plan n'est pas validé, on désactive
   * tout le formulaire (y compris les contrôles ajoutés dynamiquement aux
   * FormArrays). À rappeler après chaque (ré)hydratation.
   */
  private applyReadOnlyLock(): void {
    if (this.planNotValidated()) {
      this.form.disable({ emitEvent: false });
    }
  }

  private hydrateFormFromCurrentYear(): void {
    const oa = this.currentOperationAnnee();
    const r = oa?.realisation;
    this.form.patchValue({
      id_niveau_realisation: r?.id_niveau_realisation ?? null,
      periodicite_realisee: r?.periodicite_realisee ?? false,
      budget_realise: r?.budget_realise ?? null,
      budget_fonctionnement_realise: r?.budget_fonctionnement_realise ?? null,
      budget_investissement_realise: r?.budget_investissement_realise ?? null,
      etp_realise: r?.etp_realise ?? null,
      operateurs_realises: r?.operateurs_realises ?? '',
      financeurs_realises: r?.financeurs_realises ?? '',
      commentaires: r?.commentaires ?? '',
    });
    this.hydrateOrganismesArray(oa);
    this.hydrateRhArray(oa);
    this.applyReadOnlyLock();
  }

  /**
   * #560 — Reconstruit le FormArray RH de l'année active.
   *
   * On part des lignes RH **prévisionnelles** de l'année (qui était prévu, et
   * combien de jours), et on y fusionne le **réalisé** déjà saisi, apparié via
   * la FK `id_operation_annee_rh` portée par la ligne réelle. C'est ce lien —
   * et non un rapprochement sur (cible, financé) — qui permet de ré-attribuer
   * le temps au moment du suivi (« en fait c'est ce poste-là qui l'a fait »)
   * sans que le prévu et le réel se dissocient en deux lignes.
   *
   * Les lignes réelles sans lien (`id_operation_annee_rh` NULL) sont du temps
   * réalisé non prévu : elles s'ajoutent à la suite, sans référence de prévu.
   */
  private hydrateRhArray(oa: OperationAnnee | null): void {
    const fa = this.rhLignesFA;
    while (fa.length) fa.removeAt(0);
    if (!oa) return;

    const reelles = oa.realisation?.rh_lignes ?? [];
    const reelParPrevu = new Map<number, OperationRHLigne>();
    for (const r of reelles) {
      if (r.id_operation_annee_rh != null) reelParPrevu.set(r.id_operation_annee_rh, r);
    }

    for (const prev of oa.rh_lignes ?? []) {
      const reel = prev.id_operation_annee_rh != null
        ? reelParPrevu.get(prev.id_operation_annee_rh)
        : undefined;
      // La cible affichée est celle du réel dès qu'il existe (le suivi peut
      // l'avoir ré-attribuée) ; sinon on propose celle du prévisionnel.
      const source = reel ?? prev;
      fa.push(this.fb.group({
        id_operation_annee_rh: [prev.id_operation_annee_rh ?? null],
        id_poste: [source.id_poste ?? null],
        id_organisme: [source.id_organisme ?? null],
        finance: [!!source.finance],
        // #608 — catégorie de dépense : sert au calcul du coût salarial réalisé
        // séparé fonctionnement / investissement.
        // #615 — désormais saisissable au suivi : la valeur du RÉALISÉ prime,
        // sinon on hérite du prévisionnel (et à défaut de son financement).
        categorie_depense: [this.rhCategorie(reel) ?? this.rhCategorie(prev)
          ?? this.categorieFromFinance(!!source.finance)],
        /** Prévu (lecture seule, référence affichée). */
        plan_jours: [prev.jours ?? null],
        /**
         * Financement du PRÉVU, distinct de `finance` : une ré-attribution au
         * suivi (prévu = garde financé, réel = bénévole) ne doit pas
         * reclasser rétroactivement le prévisionnel dans les sous-totaux.
         */
        plan_finance: [!!prev.finance],
        /** Réalisé (éditable). */
        jours: [reel?.jours ?? null],
      }));
    }

    for (const reel of reelles) {
      if (reel.id_operation_annee_rh != null) continue;
      fa.push(this.fb.group({
        id_operation_annee_rh: [null],
        id_poste: [reel.id_poste ?? null],
        id_organisme: [reel.id_organisme ?? null],
        finance: [!!reel.finance],
        categorie_depense: [this.rhCategorie(reel) ?? this.categorieFromFinance(!!reel.finance)],
        plan_jours: [null],
        plan_finance: [!!reel.finance],
        jours: [reel.jours ?? null],
      }));
    }
  }

  /** Catégorie de dépense portée par une ligne RH, ou null si absente (données
   *  antérieures à #597, où seul le booléen `finance` existait). */
  private rhCategorie(ligne: OperationRHLigne | null | undefined): CategorieDepense | null {
    return ligne?.categorie_depense ?? null;
  }

  /** #560 — ajoute une ligne RH réalisée (temps non prévu). */
  addRhLigne(): void {
    this.rhLignesFA.push(this.fb.group({
      id_operation_annee_rh: [null],
      id_poste: [null],
      id_organisme: [null],
      finance: [true],
      categorie_depense: ['fonctionnement'],
      plan_jours: [null],
      plan_finance: [true],
      jours: [null],
    }));
  }

  removeRhLigne(index: number): void {
    this.rhLignesFA.removeAt(index);
  }

  /** Cible d'une ligne RH : id du poste ou de l'organisme, null si aucune. */
  rhTargetValue(ctrl: AbstractControl): number | null {
    return ctrl.get('id_poste')?.value ?? ctrl.get('id_organisme')?.value ?? null;
  }

  setRhTarget(ctrl: AbstractControl, id: number | null): void {
    if (this.rhMode() === 'postes') {
      ctrl.get('id_poste')?.setValue(id);
      ctrl.get('id_organisme')?.setValue(null);
      // Défaut financé/non financé porté par les fonctions du poste.
      const poste = this.postes().find((p) => p.id_poste === id);
      if (poste) {
        const finance = poste.finance_par_defaut ?? true;
        ctrl.get('finance')?.setValue(finance);
        // #615 — la catégorie suit le défaut du poste (bénévolat si non financé).
        ctrl.get('categorie_depense')?.setValue(this.categorieFromFinance(finance));
      }
    } else {
      ctrl.get('id_organisme')?.setValue(id);
      ctrl.get('id_poste')?.setValue(null);
    }
  }

  /**
   * #615 — Options de la colonne « Catégorie de dépense » du temps de travail,
   * identiques à celles de la saisie de l'action (`operation-form`).
   */
  readonly categorieDepenseOptions: CategorieDepense[] = [
    'fonctionnement', 'investissement', 'benevolat_partenariat',
  ];

  /** Financé = tout sauf « bénévolat partenariat » (#597). */
  private financeFromCategorie(cat: CategorieDepense): boolean {
    return cat !== 'benevolat_partenariat';
  }

  /** Catégorie par défaut dérivée du booléen financé (compat / valeur initiale). */
  private categorieFromFinance(finance: boolean): CategorieDepense {
    return finance ? 'fonctionnement' : 'benevolat_partenariat';
  }

  /**
   * #615 — Change la catégorie de dépense d'une ligne RH réalisée et
   * resynchronise `finance`, qui reste la clé des sous-totaux financé /
   * non financé et n'est plus saisi directement.
   */
  setRhCategorie(ctrl: AbstractControl, cat: CategorieDepense): void {
    ctrl.get('categorie_depense')?.setValue(cat);
    ctrl.get('finance')?.setValue(this.financeFromCategorie(cat));
  }

  /** Libellé de la cible d'une ligne RH (poste ou organisme). */
  rhLineLabel(ctrl: AbstractControl): string {
    const posteId = ctrl.get('id_poste')?.value;
    if (posteId != null) {
      const poste = this.postes().find((p) => p.id_poste === posteId);
      return poste?.libelle || this.translate.instant('plans.postes.untitled');
    }
    const orgId = ctrl.get('id_organisme')?.value;
    if (orgId != null) {
      return this.rhOrganismes().find((o) => o.id_organisme === orgId)?.nom_organisme || '';
    }
    return '';
  }

  /** Organisme du poste, affiché sous son libellé. */
  rhLineSubLabel(ctrl: AbstractControl): string {
    const posteId = ctrl.get('id_poste')?.value;
    if (posteId == null) return '';
    return this.postes().find((p) => p.id_poste === posteId)?.organisme_nom || '';
  }

  /**
   * Total RH de l'année pour une colonne (prévu ou réalisé), éventuellement
   * restreint au financé (`true`) ou au non financé (`false`).
   *
   * Chaque colonne est ventilée selon SON propre financement : le prévu suit
   * `plan_finance`, le réalisé suit `finance`. Sans quoi ré-attribuer une
   * ligne au suivi (garde financé → bénévole) basculerait aussi le
   * prévisionnel du côté non financé.
   */
  sumRh(field: 'plan_jours' | 'jours', finance?: boolean): number {
    const financeField = field === 'plan_jours' ? 'plan_finance' : 'finance';
    return this.rhLignesFA.controls.reduce((sum, c) => {
      if (finance !== undefined && !!c.get(financeField)?.value !== finance) return sum;
      return sum + (Number(c.get(field)?.value) || 0);
    }, 0);
  }

  /** Reconstruit le FormArray des organismes à partir de l'OperationAnnee active. */
  private hydrateOrganismesArray(oa: OperationAnnee | null): void {
    const fa = this.organismesFA;
    while (fa.length) fa.removeAt(0);

    if (!this.isOrgVentilation() || !oa?.organismes?.length) return;

    for (const oao of oa.organismes) {
      const r = oao.realisation;
      fa.push(this.fb.group({
        id_operation_annee_organisme: [oao.id_operation_annee_organisme],
        id_organisme: [oao.id_organisme],
        organisme_nom: [oao.organisme_nom ?? ''],
        // Planifié (lecture seule, exposé au template)
        plan_budget_fonctionnement: [oao.budget_fonctionnement],
        plan_budget_investissement: [oao.budget_investissement],
        plan_etp: [oao.etp],
        // Réalisé (éditable)
        budget_fonctionnement_realise: [r?.budget_fonctionnement_realise ?? null],
        budget_investissement_realise: [r?.budget_investissement_realise ?? null],
        etp_realise: [r?.etp_realise ?? null],
        // #600 Q2b — coût stage réalisé (fonctionnement).
        cout_stage_realise: [r?.cout_stage_realise ?? null],
        // #608 — détail des coûts réalisés (mode ventilation maximale).
        cout_prestataire_realise: [r?.cout_prestataire_realise ?? null],
        autre_cout_realise: [r?.autre_cout_realise ?? null],
        autre_cout_commentaire_realise: [r?.autre_cout_commentaire_realise ?? ''],
        cout_prestataire_invest_realise: [r?.cout_prestataire_invest_realise ?? null],
        autre_cout_invest_realise: [r?.autre_cout_invest_realise ?? null],
        autre_cout_invest_commentaire_realise: [r?.autre_cout_invest_commentaire_realise ?? ''],
      }));
    }
  }

  // --- Totaux calculés pour le tableau ventilé (figma écran 05) ---

  totalPlanFonct = computed<number>(() => this.sumOrg('plan_budget_fonctionnement'));
  totalPlanInvest = computed<number>(() => this.sumOrg('plan_budget_investissement'));
  totalPlanEtp = computed<number>(() => this.sumOrg('plan_etp'));
  totalRealFonct = computed<number>(() => this.sumOrg('budget_fonctionnement_realise'));
  totalRealInvest = computed<number>(() => this.sumOrg('budget_investissement_realise'));
  totalRealEtp = computed<number>(() => this.sumOrg('etp_realise'));

  private sumOrg(controlName: string): number {
    return this.organismesFA.controls
      .map(c => Number(c.get(controlName)?.value || 0))
      .reduce((a, b) => a + b, 0);
  }

  selectYear(year: number): void {
    this.selectedYear.set(year);
    this.hydrateFormFromCurrentYear();
    // Les indicateurs de réponse sont saisis par année : recharger la mesure
    // correspondant à la nouvelle année. On PATCHE les contrôles existants
    // (sans reconstruire le FormArray) car le `@for (track id_metrique)` du
    // template réutiliserait les inputs sans les relier aux nouveaux contrôles.
    this.refreshIndicateursForYear();
    // Réinitialiser l'emprise en cours d'édition (chaque année a sa propre
    // emprise réalisée).
    this.pendingGeomRealisee.set(undefined);
    this.isEditingGeom.set(false);
    this.empriseSnapshot.set(null);
  }

  /**
   * Met à jour, sur place, la valeur réalisée + l'id_mesure de chaque
   * indicateur de réponse pour l'année sélectionnée. Les mesures sont déjà
   * en cache (mesuresByMetrique), donc aucun appel API.
   */
  private refreshIndicateursForYear(): void {
    const year = this.selectedYear();
    for (const ctrl of this.indicateursFA.controls) {
      const metId = ctrl.get('id_metrique')?.value;
      const mesures = this.mesuresByMetrique.get(metId) ?? [];
      const existing = this.latestMesureForYear(mesures, year);
      ctrl.patchValue(
        { id_mesure: existing?.id_mesure ?? null, valeur: existing?.valeur ?? '' },
        { emitEvent: false },
      );
    }
    this.applyReadOnlyLock();
  }

  goBack(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'suivi-actions']);
    } else {
      this.router.navigate(['/plans']);
    }
  }

  submit(quit = false): void {
    // #379 — interdire toute sauvegarde si le plan n'est pas validé.
    if (this.planNotValidated()) {
      return;
    }
    // #609 — le niveau de réalisation est obligatoire pour enregistrer.
    if (!this.form.get('id_niveau_realisation')?.value) {
      this.showNiveauError.set(true);
      this.snack.open(
        this.translate.instant('plans.suivis.saisie.errors.niveauRequired'),
        this.translate.instant('common.actions.close'),
        { duration: 4000 },
      );
      return;
    }
    this.showNiveauError.set(false);
    const oa = this.currentOperationAnnee();
    const v = this.form.value;
    const orgVentilation = this.isOrgVentilation();

    // 1) Payload annuel : niveau, périodicité, commentaires toujours.
    //    Budget/ETP au niveau année uniquement si pas de ventilation par org.
    // #418 — si l'année n'était pas programmée (pas d'OperationAnnee), on
    // transmet (id_operation, annee) : le backend crée l'année à la volée
    // (réalisée non prévue). Sinon on cible l'OperationAnnee existante.
    const annualPayload: RealisationUpsertPayload = {
      ...(oa?.id_operation_annee
        ? { id_operation_annee: oa.id_operation_annee }
        : { id_operation: this.operationId() ?? undefined, annee: this.selectedYear() }),
      id_niveau_realisation: v.id_niveau_realisation || null,
      // #609 — périodicité dérivée du niveau (le backend la recalcule aussi).
      periodicite_realisee: this.periodiciteFromNiveau(v.id_niveau_realisation),
      commentaires: v.commentaires || null,
      // #541 — opérateur(s)/financeur(s) réalisés (niveau année, tous modes).
      operateurs_realises: v.operateurs_realises || '',
      financeurs_realises: v.financeurs_realises || '',
    };
    if (!orgVentilation) {
      annualPayload.etp_realise = v.etp_realise ?? null;
      if (this.isByType()) {
        annualPayload.budget_fonctionnement_realise = v.budget_fonctionnement_realise ?? null;
        annualPayload.budget_investissement_realise = v.budget_investissement_realise ?? null;
      } else {
        annualPayload.budget_realise = v.budget_realise ?? null;
      }
    }
    // #560 — temps de travail réalisé : lignes RH (poste/organisme × jours ×
    // financé). Indépendant de la ventilation budgétaire par organisme, d'où
    // la position hors du bloc ci-dessus. Sémantique « replace-all » côté API :
    // on envoie l'état complet de l'année, les lignes vides sont écartées.
    annualPayload.rh_lignes = this.rhLignesFA.controls
      .map(c => {
        const val = c.value as any;
        return {
          id_operation_annee_rh: val.id_operation_annee_rh ?? null,
          id_poste: val.id_poste ?? null,
          id_organisme: val.id_organisme ?? null,
          jours: val.jours ?? null,
          finance: !!val.finance,
          // #608 — conserver la catégorie pour le calcul du coût salarial réalisé.
          categorie_depense: val.categorie_depense ?? 'fonctionnement',
        };
      })
      // Une ligne sans cible reste valide (« temps non affecté »). Seul le
      // nombre de jours est discriminant : les lignes laissées vides ne sont
      // pas enregistrées.
      .filter(l => l.jours != null);

    // Emprise réalisée : on n'inclut le champ dans le payload que si
    // l'utilisateur l'a modifié localement (sinon on ne touche pas au
    // serveur). `null` est une valeur valide (effacement explicite).
    const pendingGeom = this.pendingGeomRealisee();
    if (pendingGeom !== undefined) {
      annualPayload.geom_realisee = pendingGeom;
    }

    // 2) Payloads par organisme (mode by_org / by_org_type).
    const orgPayloads: RealisationOrganismeUpsertPayload[] = orgVentilation
      ? this.organismesFA.controls
          .filter(c => c.get('id_operation_annee_organisme')?.value)
          .map(c => {
            const val = c.value as any;
            const p: RealisationOrganismeUpsertPayload = {
              id_operation_annee_organisme: val.id_operation_annee_organisme,
              budget_fonctionnement_realise: val.budget_fonctionnement_realise ?? null,
              etp_realise: val.etp_realise ?? null,
            };
            if (this.ventilationMode() === 'by_org_type') {
              p.budget_investissement_realise = val.budget_investissement_realise ?? null;
            }
            // #608 — ventilation maximale : détail des coûts réalisés. Les budgets
            // fonct/invest restent calculés (salarial auto + prestataire + autres),
            // on ne stocke donc que les composants saisis.
            if (this.isMaxVentilation()) {
              p.budget_fonctionnement_realise = null;
              p.budget_investissement_realise = null;
              // #600 Q2b — coût stage réalisé (fonctionnement).
              p.cout_stage_realise = val.cout_stage_realise ?? null;
              p.cout_prestataire_realise = val.cout_prestataire_realise ?? null;
              p.autre_cout_realise = val.autre_cout_realise ?? null;
              p.autre_cout_commentaire_realise = val.autre_cout_commentaire_realise ?? '';
              p.cout_prestataire_invest_realise = val.cout_prestataire_invest_realise ?? null;
              p.autre_cout_invest_realise = val.autre_cout_invest_realise ?? null;
              p.autre_cout_invest_commentaire_realise = val.autre_cout_invest_commentaire_realise ?? '';
            }
            return p;
          })
      : [];

    // 3) Mesures (Indicateurs de réponse) : créer/mettre à jour pour l'année active.
    // #247 — métrique multi-blocs : `valeur` = bloc principal, `valeurs_blocs` = { position: valeur }.
    const yearActive = this.selectedYear();
    const notEmpty = (x: any) => (x ?? '').toString().trim() !== '';
    const measureCalls = this.indicateursFA.controls
      .map(c => c.value as any)
      .map(v => {
        const blocks: any[] = v.meta?.score_blocks || [];
        const valeurs_blocs: Record<string, string> = {};
        for (const b of blocks) {
          const bv = v[`bloc_${b.position}`];
          if (notEmpty(bv)) valeurs_blocs[String(b.position)] = String(bv);
        }
        const hasPrincipal = notEmpty(v.valeur);
        if (!hasPrincipal && Object.keys(valeurs_blocs).length === 0) return null;
        const payload: MesureCreatePayload = {
          id_metrique: v.id_metrique,
          valeur: hasPrincipal ? String(v.valeur) : '',
          valeurs_blocs,
          date_mesure: `${yearActive}-12-31`,
        };
        return v.id_mesure
          ? this.enjeuService.updateMesure(v.id_mesure, payload)
          : this.enjeuService.createMesure(payload);
      })
      .filter((call): call is NonNullable<typeof call> => call !== null);

    this.isSaving.set(true);
    const annualCall = this.realisationService.upsert(annualPayload);
    const orgCalls = orgPayloads.length
      ? forkJoin(orgPayloads.map(p => this.realisationService.upsertOrganisme(p)))
      : of([]);
    const mesureCallsObs = measureCalls.length ? forkJoin(measureCalls) : of([]);

    forkJoin([annualCall, orgCalls, mesureCallsObs]).subscribe({
      next: ([savedAnnual, savedOrgs, savedMesures]) => {
        this.isSaving.set(false);
        // #542 — réinjecter les mesures renvoyées par le serveur dans le cache et
        // les contrôles : sans ça, `id_mesure` restait null (ré-enregistrement =
        // doublon) et `refreshIndicateursForYear` relisait un cache périmé, faisant
        // « disparaître » la valeur réalisée au changement d'année / rechargement.
        for (const m of (savedMesures as Mesure[]) ?? []) {
          const list = this.mesuresByMetrique.get(m.id_metrique) ?? [];
          const i = list.findIndex(x => x.id_mesure === m.id_mesure);
          if (i >= 0) list[i] = m; else list.push(m);
          this.mesuresByMetrique.set(m.id_metrique, list);
          this.indicateursFA.controls
            .find(c => c.get('id_metrique')?.value === m.id_metrique)
            ?.get('id_mesure')?.setValue(m.id_mesure, { emitEvent: false });
        }
        this.snack.open(
          this.translate.instant('plans.suivis.saisie.messages.saved'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 },
        );
        // Synchroniser le signal `operation` avec les réponses serveur.
        const op = this.operation();
        if (op?.operation_annees) {
          const idx = op.operation_annees.findIndex(
            o => o.id_operation_annee === savedAnnual.id_operation_annee,
          );
          if (idx >= 0) {
            const target = op.operation_annees[idx];
            target.realisation = savedAnnual;
            if (target.organismes && (savedOrgs as any[])?.length) {
              for (const so of savedOrgs as any[]) {
                const idxOrg = target.organismes.findIndex(
                  (oao: OperationAnneeOrganisme) =>
                    oao.id_operation_annee_organisme === so.id_operation_annee_organisme,
                );
                if (idxOrg >= 0) target.organismes[idxOrg].realisation = so;
              }
            }
            this.operation.set({ ...op });
          } else {
            // #418 — année non planifiée créée à la volée : on l'ajoute
            // localement pour refléter immédiatement la saisie.
            op.operation_annees.push({
              id_operation_annee: savedAnnual.id_operation_annee,
              annee: this.selectedYear(),
              periodicite: false,
              organismes: [],
              realisation: savedAnnual,
            } as unknown as OperationAnnee);
            this.operation.set({ ...op });
          }
        }
        // Emprise sauvegardée : on revient en lecture seule et on purge le
        // brouillon (le serveur fait foi maintenant).
        this.pendingGeomRealisee.set(undefined);
        this.isEditingGeom.set(false);
        this.empriseSnapshot.set(null);
        // « Enregistrer et quitter » : retour à la liste de suivi des actions.
        if (quit) this.goBack();
      },
      error: () => {
        this.isSaving.set(false);
        this.snack.open(
          this.translate.instant('plans.suivis.saisie.errors.saveFailed'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 },
        );
      },
    });
  }
}
