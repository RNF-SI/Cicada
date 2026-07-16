/**
 * Composant pour afficher la liste des Enjeux et FCR d'un plan.
 * - Sans enjeu sélectionné : liste plate de cartes accordéon
 * - Avec enjeu sélectionné (route :enjeuId) : vue détail avec 3 onglets
 */
import { Component, OnInit, OnDestroy, DestroyRef, inject, signal, computed, ElementRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule, FormControl, ReactiveFormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { forkJoin, Observable, of, switchMap } from 'rxjs';
import { PlanStatut } from '../../../../core/models/admin.model';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatRadioModule } from '@angular/material/radio';
import { CheckboxComponent } from '../../../../shared/components/checkbox/checkbox.component';
import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { CdkDragDrop, DragDropModule, moveItemInArray, transferArrayItem } from '@angular/cdk/drag-drop';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AuthService } from '../../../../core/services/auth.service';
import { ReorderService, ReorderEntity } from '../../../../core/services/reorder.service';
import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import {
  AccessRequestDialogComponent,
  AccessRequestDialogData,
} from '../../../../shared/components/access-request-dialog/access-request-dialog.component';
import {
  DuplicateIndicateurDialogComponent,
  DuplicateIndicateurDialogData,
  DuplicateIndicateurDialogResult,
  DuplicateIndicateurTargetNe,
  DuplicateIndicateurTargetRa,
} from '../../../../shared/components/modals/duplicate-indicateur-dialog/duplicate-indicateur-dialog.component';
import { LinkOperationDialogComponent, LinkOperationDialogData, LinkOperationDialogResult } from '../../../../shared/components/modals';
import { DeleteOperationDialogComponent, DeleteOperationDialogResult } from '../../../../shared/components/modals';
import {
  ShareElementDialogComponent,
  ShareElementDialogData,
  ShareElementDialogResult,
  ShareEnjeuTarget,
  SharePressionTarget,
} from '../../../../shared/components/modals';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import {
  Enjeu, FacteurInfluence, Pression, PlanEnjeuxResponse,
  ObjectifLongTerme, NiveauExigence, Indicateur, Metrique, MetriqueRef,
  MetriqueFormData, MetriqueCreatePayload, Operation, OperationAnnee,
  ObjectifOperationnel, ResultatAttendu
} from '../../../../core/models/enjeu.model';
import { EnjeuAccordionComponent } from '../enjeu-accordion/enjeu-accordion.component';
import { SectionTitleComponent } from '../../../../shared/components/section-title/section-title.component';
import { HabitatChipComponent } from '../../../../shared/components/habitat-chip/habitat-chip.component';
import { TagComponent } from '../../../../shared/components/tag/tag.component';
import { getPrioriteTag, TagAppearance } from '../../../../shared/utils/tag-icons';
import { MetriqueFormComponent } from '../../../../shared/components/metrique-form/metrique-form.component';
import {
  NomenclatureOption,
  NomenclatureGroup,
  buildNomenclatureGroups,
  getNomenclatureDepth,
  displayNomenclatureFn,
  parseNomenclatureDefinition,
} from '../../../../shared/utils/nomenclature-autocomplete.utils';

type TabType = 'detail' | 'olt' | 'operations';

@Component({
  selector: 'app-enjeux-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    ReactiveFormsModule,
    MatProgressSpinnerModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatMenuModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatRadioModule,
    CheckboxComponent,
    FormFieldComponent,
    MatButtonToggleModule,
    MatTooltipModule,
    MatDialogModule,
    MatSnackBarModule,
    TranslateModule,
    HeaderComponent,
    PlanSidebarComponent,
    EnjeuAccordionComponent,
    SectionTitleComponent,
    MetriqueFormComponent,
    DragDropModule,
    HabitatChipComponent,
    TagComponent
  ],
  templateUrl: './enjeux-list.component.html',
  styleUrl: './enjeux-list.component.scss'
})
export class EnjeuxListComponent implements OnInit, OnDestroy {
  private readonly elRef = inject(ElementRef);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly enjeuService = inject(EnjeuService);
  private readonly adminService = inject(AdminService);
  private readonly translate = inject(TranslateService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);
  private readonly authService = inject(AuthService);
  private readonly reorderService = inject(ReorderService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  planAnneeDebut = signal<number | null>(null);
  planAnneeFin = signal<number | null>(null);
  planReferentIds = signal<number[]>([]);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  /** Statut du plan courant — exposé par l'endpoint by-plan, utilisé pour
   *  verrouiller l'édition hors brouillon (#248).
   *  #277 — Inclut les statuts CSRPN intermédiaires (verrouillage identique). */
  planStatut = signal<PlanStatut | null>(null);

  /** Plan en brouillon : seul état autorisant l'édition de contenu (#248).
   *  L'extension de durée (#250) est un attribut indépendant du statut et
   *  ne débloque PAS l'édition. */
  isPlanDraft = computed(() => {
    return this.planStatut() === 'draft';
  });

  // Permissions édition: super_admin, redacteur_principal, admin_og, ou référent du plan
  // ET le plan doit être en brouillon (#248).
  canEditPlan = computed(() => {
    if (!this.isPlanDraft()) return false;
    if (this.authService.isSuperAdmin() || this.authService.isRedacteurPrincipal() || this.authService.isAdminOrganisme()) {
      return true;
    }
    const currentUser = this.authService.currentUser();
    if (!currentUser) return false;
    return this.planReferentIds().includes(currentUser.id);
  });

  /** Gestionnaire du plan : admin/super/RP ou référent du plan (indépendant du
   *  statut brouillon). Sert à distinguer un simple consultant non référent,
   *  à qui l'on propose de demander à devenir référent. */
  isPlanManager = computed(() => {
    if (this.authService.isSuperAdmin() || this.authService.isRedacteurPrincipal() || this.authService.isAdminOrganisme()) {
      return true;
    }
    const currentUser = this.authService.currentUser();
    if (!currentUser) return false;
    return this.planReferentIds().includes(currentUser.id);
  });

  planEnjeuxData = signal<PlanEnjeuxResponse | null>(null);

  // Onglet actif (vue détail uniquement)
  activeTab = signal<TabType>('detail');

  // Enjeu sélectionné (via route :enjeuSlug)
  selectedEnjeuId = signal<number | null>(null);
  selectedEnjeuSlug = signal<string | null>(null);

  // Expand/collapse state pour la vue détail
  enjeuDetailExpanded = signal(true);
  expandedFcrIds = signal<Set<number>>(new Set());
  showDetailTaxonList = signal(false);
  showDetailHabitatList = signal(false);
  showDetailGeologyList = signal(false);

  // Facteurs d'influence / Pressions state
  expandedFacteurIds = signal<Set<number>>(new Set());
  expandedPressionIds = signal<Set<number>>(new Set());
  addingFacteurInfluence = signal(false);
  addingPressionForFacteur = signal<number | null>(null);
  newFacteurLibelle = '';
  newFacteurDescription = '';
  newPressionLibelle = '';
  newPressionDescription = '';
  editingFacteurId = signal<number | null>(null);
  editFacteurLibelle = '';
  editFacteurDescription = '';
  editingPressionId = signal<number | null>(null);
  editPressionLibelle = '';
  editPressionDescription = '';

  // PressRef autocomplete state
  pressrefOptions = signal<NomenclatureOption[]>([]);
  pressrefSearchCtrl = new FormControl('');
  pressrefSearchText = signal('');
  selectedPressref = signal<NomenclatureOption | null>(null);
  pressrefGroups = computed<NomenclatureGroup[]>(() => {
    return buildNomenclatureGroups(this.pressrefOptions(), this.pressrefSearchText(), { searchInDefinition: true });
  });
  displayPressrefFn = displayNomenclatureFn;
  getPressrefDepth = getNomenclatureDepth;
  // Edit mode PressRef
  editPressrefSearchCtrl = new FormControl('');
  editPressrefSearchText = signal('');
  editSelectedPressref = signal<NomenclatureOption | null>(null);
  editPressrefGroups = computed<NomenclatureGroup[]>(() => {
    return buildNomenclatureGroups(this.pressrefOptions(), this.editPressrefSearchText(), { searchInDefinition: true });
  });

  // OLT / Niveaux d'exigence state
  expandedOltIds = signal<Set<number>>(new Set());
  addingOlt = signal(false);
  addingNeForOlt = signal<number | null>(null);
  editingOltId = signal<number | null>(null);
  editingNeId = signal<number | null>(null);
  newOltLibelle = '';
  newOltDescription = '';
  newNeLibelle = '';
  newNeDescription = '';
  editOltLibelle = '';
  editOltDescription = '';
  // #442 — Numéro fixé manuellement de l'OLL en édition (null = automatique).
  editOltNumero: number | null = null;
  editNeLibelle = '';
  editNeDescription = '';

  // Opérations expand/collapse
  expandedOperationIds = signal<Set<number>>(new Set());
  // Résultats Attendus expand/collapse (vision opérationnelle, revue design Amandine)
  expandedRaIds = signal<Set<number>>(new Set());
  // Pending scroll to a specific operation after data loads
  pendingScrollToOperation = signal<number | null>(null);
  // Pending scroll to a specific métrique after data loads (retour depuis form action annulé)
  pendingScrollToMetrique = signal<number | null>(null);
  // Pending scroll to a typed anchor `<type>-<id>` (depuis le tableau d'arborescence #257)
  pendingScrollToAnchor = signal<string | null>(null);

  // Indicateurs state
  expandedIndicateurIds = signal<Set<number>>(new Set());
  addingIndicateurForNe = signal<number | null>(null);
  editingIndicateurId = signal<number | null>(null);
  newIndicateurNom = '';
  newIndicateurType: number | null = null;
  newIndicateurStandardise = false;
  newIndicateurDescription = '';
  editIndicateurNom = '';
  editIndicateurType: number | null = null;
  editIndicateurStandardise = false;
  editIndicateurDescription = '';

  // Unified indicateur form state (indicateur + inline metriques)
  indicateurFormMetriques: MetriqueFormData[] = [];
  // Edit indicateur: metriques inline editing
  editIndicateurMetriques: MetriqueFormData[] = [];
  typeMetriqueOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);
  isSavingIndicateur = signal(false);

  // Standalone metrique add (outside indicateur edit form)
  addingMetriqueForIndicateur = signal<number | null>(null);
  standaloneMetriqueForm: MetriqueFormData | null = null;
  isSavingStandaloneMetrique = signal(false);

  // OO (Objectifs Opérationnels) state
  expandedOoIds = signal<Set<number>>(new Set());
  addingOo = signal(false);
  editingOoId = signal<number | null>(null);
  newOoLibelle = '';
  newOoDescription = '';
  newOoPressionIds: number[] = [];
  editOoLibelle = '';
  editOoDescription = '';
  // #526 — Numéro fixé manuellement de l'OO en édition (null = automatique).
  editOoNumero: number | null = null;
  editOoPressionIds: number[] = [];

  // Résultat Attendu state
  addingRaForOo = signal<number | null>(null);
  editingRaId = signal<number | null>(null);
  newRaLibelle = '';
  newRaDescription = '';
  editRaLibelle = '';
  editRaDescription = '';

  // Indicateurs pression (for OO tab)
  addingIndicateurForRa = signal<number | null>(null);
  editingOoIndicateurId = signal<number | null>(null);

  /**
   * #559 — Un formulaire d'édition inline est-il ouvert quelque part dans
   * l'arborescence ? Tant qu'une modification n'est pas enregistrée ou
   * annulée, le drag-and-drop de tous les éléments du PG est verrouillé pour
   * éviter de déplacer un élément en cours d'édition. (La création est déjà
   * bloquée : le formulaire d'ajout remplace la card, il n'y a rien à glisser.)
   */
  readonly isAnyInlineEditActive = computed(() =>
    this.editingFacteurId() !== null ||
    this.editingPressionId() !== null ||
    this.editingOltId() !== null ||
    this.editingNeId() !== null ||
    this.editingIndicateurId() !== null ||
    this.editingOoId() !== null ||
    this.editingRaId() !== null ||
    this.editingOoIndicateurId() !== null,
  );
  newOoIndicateurNom = '';
  newOoIndicateurType: number | null = null;
  newOoIndicateurStandardise = false;
  newOoIndicateurDescription = '';
  editOoIndicateurNom = '';
  editOoIndicateurType: number | null = null;
  editOoIndicateurStandardise = false;
  editOoIndicateurDescription = '';
  ooIndicateurFormMetriques: MetriqueFormData[] = [];
  editOoIndicateurMetriques: MetriqueFormData[] = [];
  isSavingOoIndicateur = signal(false);
  expandedOoIndicateurIds = signal<Set<number>>(new Set());
  expandedOoOperationIds = signal<Set<number>>(new Set());

  // Enjeux et FCR séparés.
  // #228 — Tri explicite par `ordre` puis `id_enjeu` après chaque accès :
  // moveItemInArray dans applyReorder mute `item.ordre` sur les objets
  // partagés ; le re-render dépend du tri canonique pour refléter le DnD.
  private static _byOrdreId<T extends { ordre?: number; id_enjeu: number }>(a: T, b: T): number {
    const oa = a.ordre ?? 0;
    const ob = b.ordre ?? 0;
    if (oa !== ob) return oa - ob;
    return a.id_enjeu - b.id_enjeu;
  }

  enjeux = computed(() => {
    const data = this.planEnjeuxData();
    if (!data) return [];
    return [...(data.enjeux || [])].sort(EnjeuxListComponent._byOrdreId);
  });

  fcr = computed(() => {
    const data = this.planEnjeuxData();
    if (!data) return [];
    return [...(data.fcr || [])].sort(EnjeuxListComponent._byOrdreId);
  });

  /**
   * #526 / #442 — Construit une map id_enjeu → numéro affiché pour une liste
   * ordonnée (enjeux ou FCR), sur le même principe que l'OLT/OO : un
   * `numero_manuel` est réservé et l'auto-numérotation des autres saute cet
   * indice. La numérotation est locale à la liste (les enjeux et les FCR sont
   * numérotés indépendamment).
   */
  private static _buildManualRankMap(list: Enjeu[]): Map<number, number> {
    const reserved = new Set<number>();
    for (const e of list) {
      if (e.numero_manuel != null) reserved.add(e.numero_manuel);
    }
    const map = new Map<number, number>();
    let auto = 0;
    for (const e of list) {
      if (e.numero_manuel != null) {
        map.set(e.id_enjeu, e.numero_manuel);
      } else {
        auto += 1;
        while (reserved.has(auto)) auto += 1;
        map.set(e.id_enjeu, auto);
      }
    }
    return map;
  }

  enjeuDisplayRank = computed(() => EnjeuxListComponent._buildManualRankMap(this.enjeux()));
  fcrDisplayRank = computed(() => EnjeuxListComponent._buildManualRankMap(this.fcr()));

  /** Numéro affiché d'un enjeu/FCR (fixé ou automatique). */
  getEnjeuDisplayNumber(enjeu: Enjeu, isFcr: boolean, fallbackIdx: number): number {
    const map = isFcr ? this.fcrDisplayRank() : this.enjeuDisplayRank();
    return map.get(enjeu.id_enjeu) ?? fallbackIdx + 1;
  }

  /**
   * #229 / #442 — Numérotation globale des OLT à travers tous les enjeux du
   * plan, dans l'ordre de tri des enjeux (`ordre`, puis `id_enjeu`).
   *
   * Exemple : enjeu 1 a 2 OLT → OLT 1 et OLT 2 ; enjeu 2 a 2 OLT → OLT 3
   * et OLT 4. Permet aux gestionnaires de désigner un OLT par son numéro
   * sans ambiguïté.
   *
   * #442 — Un OLT peut fixer son numéro manuellement (`numero_manuel`). Ce
   * numéro est alors réservé et l'auto-numérotation des autres OLT le saute
   * (le calcul automatique se refait sans l'indice occupé).
   */
  oltGlobalRank = computed<Map<number, number>>(() => {
    // Collecte tous les OLT dans l'ordre global (enjeux puis FCR).
    const olts: ObjectifLongTerme[] = [];
    for (const enjeu of this.enjeux()) {
      for (const olt of enjeu.objectifs_long_terme || []) olts.push(olt);
    }
    // Les FCR n'ont en principe pas d'OLT, mais on les inclut pour cohérence
    // au cas où un FCR en porterait (le numérotage global continue).
    for (const enjeu of this.fcr()) {
      for (const olt of enjeu.objectifs_long_terme || []) olts.push(olt);
    }

    // Indices réservés par les OLT à numéro fixé manuellement.
    const reserved = new Set<number>();
    for (const olt of olts) {
      if (olt.numero_manuel != null) reserved.add(olt.numero_manuel);
    }

    const map = new Map<number, number>();
    let auto = 0;
    for (const olt of olts) {
      if (olt.numero_manuel != null) {
        map.set(olt.id_olt, olt.numero_manuel);
      } else {
        // Prochain indice automatique libre (non réservé).
        auto += 1;
        while (reserved.has(auto)) auto += 1;
        map.set(olt.id_olt, auto);
      }
    }
    return map;
  });

  /** #229 — Retourne le numéro global d'un OLT (1-based) ou null si inconnu. */
  getOltGlobalNumber(oltId: number | undefined): number | null {
    if (oltId === undefined) return null;
    return this.oltGlobalRank().get(oltId) ?? null;
  }

  // Compteur total
  totalCount = computed(() => {
    const data = this.planEnjeuxData();
    return data ? data.total_enjeux + data.total_fcr : 0;
  });

  hasData = computed(() => this.totalCount() > 0);

  // Enjeu sélectionné
  selectedEnjeu = computed(() => {
    const slug = this.selectedEnjeuSlug();
    if (!slug) return null;

    const enjeu = this.enjeux().find(e => e.slug === slug);
    if (enjeu) return enjeu;

    const fcrItem = this.fcr().find(f => f.slug === slug);
    return fcrItem || null;
  });

  // Computed helpers pour la vue détail de l'enjeu sélectionné
  isSelectedFcr = computed(() => {
    return this.selectedEnjeu()?.categorie_mnemonique === 'FCR';
  });

  selectedCategoryLabel = computed(() => {
    const enjeu = this.selectedEnjeu();
    if (!enjeu) return '';
    if (enjeu.categorie_ecologique === true) {
      return this.translate.instant('enjeux.enjeuForm.ecologique');
    } else if (enjeu.categorie_ecologique === false) {
      return this.translate.instant('enjeux.enjeuForm.socioEconomique');
    }
    return '';
  });

  selectedTypeLabels = computed(() => {
    const enjeu = this.selectedEnjeu();
    if (!enjeu) return [];
    const labels: string[] = [];
    // Écologique
    if (enjeu.habitat) labels.push(this.translate.instant('enjeux.enjeuForm.habitat'));
    if (enjeu.espece) labels.push(this.translate.instant('enjeux.enjeuForm.espece'));
    if (enjeu.patrimoine_geologique) labels.push(this.translate.instant('enjeux.enjeuForm.patrimoineGeologique'));
    if (enjeu.fonctionnalite_ecosysteme) labels.push(this.translate.instant('enjeux.enjeuForm.fonctionnaliteEcosysteme'));
    if (enjeu.autre_ecologique) labels.push(this.translate.instant('enjeux.enjeuForm.autreEcologique'));
    // Socio-économique
    if (enjeu.valeur_paysagere) labels.push(this.translate.instant('enjeux.enjeuForm.valeurPaysagere'));
    if (enjeu.patrimoine_culturel) labels.push(this.translate.instant('enjeux.enjeuForm.patrimoineCulturel'));
    if (enjeu.developpement_durable) labels.push(this.translate.instant('enjeux.enjeuForm.developpementDurable'));
    if (enjeu.usages) labels.push(this.translate.instant('enjeux.enjeuForm.usages'));
    if (enjeu.valeur_ajoutee) labels.push(this.translate.instant('enjeux.enjeuForm.valeurAjoutee'));
    if (enjeu.autre_socioeco) labels.push(this.translate.instant('enjeux.enjeuForm.autreSocioEco'));
    return labels;
  });

  selectedHasTaxons = computed(() => {
    const enjeu = this.selectedEnjeu();
    return (enjeu?.taxons?.length || 0) > 0 || (enjeu?.nb_taxons || 0) > 0;
  });

  selectedHasHabitats = computed(() => {
    const enjeu = this.selectedEnjeu();
    return (enjeu?.habitats?.length || 0) > 0 || (enjeu?.nb_habitats || 0) > 0;
  });

  selectedHasGeologies = computed(() => {
    const enjeu = this.selectedEnjeu();
    return (enjeu?.geologies?.length || 0) > 0 || (enjeu?.nb_geologies || 0) > 0;
  });

  selectedFcrCategoryLabel = computed(() => {
    return this.selectedEnjeu()?.categorie_fcr_label || '';
  });

  // Index d'affichage de l'enjeu sélectionné (1-based)
  selectedDisplayIndex = computed(() => {
    const slug = this.selectedEnjeuSlug();
    if (!slug) return 0;
    const idx = this.enjeux().findIndex(e => e.slug === slug);
    if (idx >= 0) return idx + 1;
    const fcrIdx = this.fcr().findIndex(f => f.slug === slug);
    if (fcrIdx >= 0) return fcrIdx + 1;
    return 0;
  });

  ngOnInit(): void {
    // Charger les nomenclatures PressRef
    this.adminService.getNomenclaturesByType('TYPE_PRESSION').subscribe({
      next: (options) => this.pressrefOptions.set(options),
      error: () => this.pressrefOptions.set([])
    });

    // Initialiser les subscriptions autocomplete PressRef
    this.pressrefSearchCtrl.valueChanges.subscribe(val => {
      if (typeof val === 'string') this.pressrefSearchText.set(val);
    });
    this.editPressrefSearchCtrl.valueChanges.subscribe(val => {
      if (typeof val === 'string') this.editPressrefSearchText.set(val);
    });

    // Récupérer le slug du plan depuis les paramètres parent
    const parentParams = this.route.parent?.snapshot.paramMap;
    const slug = parentParams?.get('slug');

    if (slug) {
      this.planSlug.set(slug);
      this.loadPlanData();

      // Fragment URL : peut être un slug d'enjeu (retour depuis formulaire)
      // ou un fragment typé `<entityType>-<id>` posté par le tableau
      // d'arborescence (#257) pour cibler une sous-entité précise.
      this.route.fragment.pipe(
        takeUntilDestroyed(this.destroyRef)
      ).subscribe(fragment => {
        if (!fragment) return;
        this.handleFragmentNavigation(fragment);
      });
    } else {
      this.errorMessage.set('Slug du plan non trouvé');
      this.isLoading.set(false);
    }

    // Écouter les changements de l'enjeuSlug dans la route
    this.route.params.pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(params => {
      const enjeuSlug = params['enjeuSlug'];
      if (enjeuSlug) {
        const previousEnjeuSlug = this.selectedEnjeuSlug();
        // Si on change d'enjeu sans démonter le composant, sauver l'état du précédent
        // et réinitialiser pour que le restore se fasse pour le nouvel enjeu.
        if (previousEnjeuSlug && previousEnjeuSlug !== enjeuSlug) {
          this.saveUiState();
          this.resetExpansionState();
          this.hasRestoredUiState = false;
        }
        this.selectedEnjeuSlug.set(enjeuSlug);
        this.enjeuDetailExpanded.set(true);
        // Reset list toggle state on enjeu change
        this.showDetailTaxonList.set(false);
        this.showDetailHabitatList.set(false);
        this.showDetailGeologyList.set(false);

        // Check query params for tab, expandOo, expandOperation
        const qp = this.route.snapshot.queryParamMap;
        const tab = qp.get('tab');
        if (tab === 'operations' || tab === 'olt') {
          this.activeTab.set(tab as TabType);
        } else {
          this.activeTab.set('detail');
        }
        const expandOo = qp.get('expandOo');
        if (expandOo) {
          const ooId = parseInt(expandOo, 10);
          if (!isNaN(ooId)) {
            this.expandedOoIds.update(s => { const ns = new Set(s); ns.add(ooId); return ns; });
          }
        }
        const expandOperation = qp.get('expandOperation');
        if (expandOperation) {
          const opId = parseInt(expandOperation, 10);
          if (!isNaN(opId)) {
            this.pendingScrollToOperation.set(opId);
          }
        }
        const expandMetrique = qp.get('expandMetrique');
        if (expandMetrique) {
          const metId = parseInt(expandMetrique, 10);
          if (!isNaN(metId)) {
            this.pendingScrollToMetrique.set(metId);
          }
        }
        // Nettoyer uniquement les params éphémères (expand*) — on garde "tab"
        // pour que Location.back() restaure le bon onglet.
        if (expandOo || expandOperation || expandMetrique) {
          this.router.navigate([], {
            relativeTo: this.route,
            queryParams: { expandOo: null, expandOperation: null, expandMetrique: null },
            queryParamsHandling: 'merge',
            replaceUrl: true,
          });
        }

        // Sur changement d'enjeu (pas le tout premier load), restaurer l'état
        // sauvegardé pour le nouvel enjeu. Au premier load, applyPostLoadNavigation
        // s'en occupera après le chargement des données.
        if (previousEnjeuSlug && previousEnjeuSlug !== enjeuSlug) {
          const hasUrlScrollTarget = !!this.pendingScrollToOperation() || !!this.pendingScrollToMetrique();
          this.restoreUiState(hasUrlScrollTarget);
          this.hasRestoredUiState = true;
        }
      } else {
        this.selectedEnjeuSlug.set(null);
      }
    });
  }

  /**
   * Recharge les données du plan.
   * @param silent Si true, ne déclenche pas le spinner global (DOM préservé → scroll conservé).
   *               À utiliser après une saisie pour éviter le retour en haut de page.
   */
  loadPlanData(silent: boolean = false): void {
    const slug = this.planSlug();
    if (!slug) return;

    if (!silent) {
      this.isLoading.set(true);
      this.errorMessage.set(null);
    }

    const existingPlanId = this.planId();

    // Si on a déjà le planId, skip getPlanBySlug et charger directement les enjeux
    if (existingPlanId) {
      this.enjeuService.getPlanEnjeux(existingPlanId, true).subscribe({
        next: (response) => {
          this.planEnjeuxData.set(response);
          if (response.plan_statut) {
            this.planStatut.set(response.plan_statut);
          }
          if (!silent) this.isLoading.set(false);
          this.applyPostLoadNavigation();
        },
        error: () => {
          if (!silent) {
            this.errorMessage.set(this.translate.instant('enjeux.messages.loadError'));
            this.isLoading.set(false);
          }
        }
      });
      return;
    }

    // Premier chargement : résoudre le slug → planId
    this.adminService.getPlanBySlug(slug).subscribe({
      next: (plan) => {
        this.planId.set(plan.id_pg);
        this.planNom.set(plan.nom);
        this.planAnneeDebut.set(plan.annee_debut || null);
        this.planAnneeFin.set(plan.annee_fin || null);
        this.planReferentIds.set((plan.referents || []).map(r => r.id_role));
        this.planStatut.set(plan.statut);

        this.enjeuService.getPlanEnjeux(plan.id_pg, true).subscribe({
          next: (response) => {
            this.planEnjeuxData.set(response);
            if (response.plan_statut) {
              this.planStatut.set(response.plan_statut);
            }
            if (!silent) this.isLoading.set(false);
            this.applyPostLoadNavigation();
          },
          error: () => {
            if (!silent) {
              this.errorMessage.set(this.translate.instant('enjeux.messages.loadError'));
              this.isLoading.set(false);
            }
          }
        });
      },
      error: () => {
        this.errorMessage.set('Plan non trouvé');
        if (!silent) this.isLoading.set(false);
      }
    });
  }

  /** Vrai après le premier restoreUiState — empêche les loadPlanData(silent=true) post-CRUD d'écraser l'état actuel. */
  private hasRestoredUiState = false;

  /** Dernier élément avec lequel l'utilisateur a interagi avant de quitter la page (clic sur une action,
   *  une métrique, etc.). Utilisé au retour pour scroller jusqu'à cet élément précis (plus fiable que
   *  window.scrollTo qui peut clamper si la hauteur du document n'est pas encore stabilisée). */
  private lastScrollAnchor: { type: 'operation' | 'metrique'; id: number } | null = null;

  /**
   * Après chargement des données, restaure l'état UI sauvegardé (expansions + scroll)
   * une seule fois, puis applique les éventuels deep-links (expand* URL — création d'action).
   */
  private applyPostLoadNavigation(): void {
    if (!this.hasRestoredUiState) {
      const hasUrlScrollTarget = !!this.pendingScrollToOperation()
        || !!this.pendingScrollToMetrique()
        || !!this.pendingScrollToAnchor();
      this.restoreUiState(hasUrlScrollTarget);
      this.hasRestoredUiState = true;
    }
    // Au premier chargement, déplier tous les RA par défaut (revue design Amandine)
    if (this.expandedRaIds().size === 0) {
      const allRaIds = new Set<number>();
      for (const enjeu of this.planEnjeuxData()?.enjeux || []) {
        for (const fi of enjeu.facteurs_influence || []) {
          for (const pression of fi.pressions || []) {
            for (const oo of pression.objectifs_operationnels || []) {
              for (const ra of oo.resultats_attendus || []) {
                allRaIds.add(ra.id_ra);
              }
            }
          }
        }
      }
      if (allRaIds.size > 0) this.expandedRaIds.set(allRaIds);
    }
    this.expandAndScrollToOperation();
    this.expandAndScrollToMetrique();
    this.expandAndScrollToAnchor();
  }

  /**
   * Décode un fragment d'URL et planifie le scroll/expansion approprié.
   * Formats supportés :
   *   - `<entityType>-<id>` : posé par le tableau d'arborescence (#257) pour
   *     viser une sous-entité précise (olt-12, niveau_exigence-3, indicateur-7,
   *     metrique-15, mesure-2, oo-8, resultat_attendu-4, facteur-9, pression-5,
   *     etat_enjeu-12, operation-N, enjeu-N, fcr-N).
   *   - `<slug-d-enjeu>` (legacy) : ancien comportement, équivaut à sélectionner
   *     l'enjeu correspondant.
   */
  private handleFragmentNavigation(fragment: string): void {
    const typedMatch = fragment.match(/^([a-z_]+)-(\d+)$/);
    if (typedMatch) {
      this.pendingScrollToAnchor.set(fragment);
      // Si la donnée est déjà chargée, déclencher le scroll immédiatement.
      if (this.planEnjeuxData()) {
        this.expandAndScrollToAnchor();
      }
      return;
    }
    // Legacy : fragment = slug d'enjeu
    this.selectedEnjeuSlug.set(fragment);
    this.enjeuDetailExpanded.set(true);
    setTimeout(() => {
      const el = this.elRef.nativeElement.querySelector(`[data-enjeu-slug="${fragment}"]`);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 500);
  }

  /**
   * Scroll vers l'élément ciblé par un fragment typé `<type>-<id>` après le
   * chargement des données. Marche en 2 temps :
   *   1. Walk de l'arbre `selectedEnjeu()` pour trouver l'élément, déterminer
   *      le tab (detail/olt/operations) et déplier les accordéons parents.
   *   2. Scroll-into-view avec polling pour gérer les rendus Angular en
   *      cascade (`@if` imbriqués) puis highlight bref.
   */
  private expandAndScrollToAnchor(): void {
    const anchor = this.pendingScrollToAnchor();
    if (!anchor) return;
    this.pendingScrollToAnchor.set(null);

    const match = anchor.match(/^([a-z_]+)-(\d+)$/);
    if (!match) return;
    const type = match[1];
    const id = parseInt(match[2], 10);

    // Préparer le contexte (tab + accordéons à déplier) en parcourant l'arbre.
    this.prepareUiForAnchor(type, id);

    // Polling jusqu'à ce que le DOM rende l'élément (peut prendre quelques
    // cycles de change-detection à cause des @if imbriqués).
    let attempts = 0;
    const maxAttempts = 30;
    const interval = setInterval(() => {
      attempts++;
      const el = this.elRef.nativeElement.querySelector(`#${CSS.escape(anchor)}`);
      if (el) {
        clearInterval(interval);
        this.scrollToAnchorWhenStable(el as HTMLElement);
      } else if (attempts >= maxAttempts) {
        clearInterval(interval);
      }
    }, 100);
  }

  /**
   * #420 — Scrolle vers l'élément une fois sa position **stabilisée**. Les
   * accordéons parents se déplient en cascade (plusieurs cycles de rendu) :
   * scroller dès l'apparition viserait une position périmée, d'où un scroll
   * inexact. On attend deux mesures consécutives identiques de `top` avant de
   * lancer un unique scroll fluide (garde-fou à 1,5 s).
   */
  private scrollToAnchorWhenStable(el: HTMLElement): void {
    let lastTop = NaN;
    let stableCount = 0;
    const doScroll = () => {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      el.classList.add('anchor-highlight');
      setTimeout(() => el.classList.remove('anchor-highlight'), 2000);
    };
    const poll = setInterval(() => {
      const top = el.getBoundingClientRect().top;
      stableCount = Math.abs(top - lastTop) < 1 ? stableCount + 1 : 0;
      lastTop = top;
      if (stableCount >= 2) {
        clearInterval(poll);
        clearTimeout(guard);
        doScroll();
      }
    }, 80);
    const guard = setTimeout(() => { clearInterval(poll); doScroll(); }, 1500);
  }

  /**
   * Marche l'arbre `selectedEnjeu()` pour localiser une entité par type+id et
   * déplie les accordéons + sélectionne l'onglet pour la rendre visible.
   * Couvre toutes les entités exposées par le tableau d'arborescence.
   */
  private prepareUiForAnchor(type: string, id: number): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu) return;

    // Helpers pour ajouter à un set signal
    const expandFacteur = (fid: number) =>
      this.expandedFacteurIds.update(s => { const ns = new Set(s); ns.add(fid); return ns; });
    const expandPression = (pid: number) =>
      this.expandedPressionIds.update(s => { const ns = new Set(s); ns.add(pid); return ns; });
    const expandOlt = (oltId: number) =>
      this.expandedOltIds.update(s => { const ns = new Set(s); ns.add(oltId); return ns; });
    const expandIndicateur = (iid: number) =>
      this.expandedIndicateurIds.update(s => { const ns = new Set(s); ns.add(iid); return ns; });
    const expandOo = (ooId: number) =>
      this.expandedOoIds.update(s => { const ns = new Set(s); ns.add(ooId); return ns; });
    const expandOoIndicateur = (iid: number) =>
      this.expandedOoIndicateurIds.update(s => { const ns = new Set(s); ns.add(iid); return ns; });

    // === Branche détail (facteur / pression) ===
    if (type === 'facteur') {
      const fi = (enjeu.facteurs_influence || []).find(f => f.id_facteur_influence === id);
      if (fi) {
        this.activeTab.set('detail');
        expandFacteur(fi.id_facteur_influence);
      }
      return;
    }
    if (type === 'pression') {
      for (const fi of enjeu.facteurs_influence || []) {
        const p = (fi.pressions || []).find(pp => pp.id_pression === id);
        if (p) {
          this.activeTab.set('detail');
          expandFacteur(fi.id_facteur_influence);
          expandPression(p.id_pression);
          return;
        }
      }
      return;
    }

    // === Branche OLT (etat_enjeu / olt / niveau_exigence) ===
    if (type === 'etat_enjeu' || type === 'olt') {
      this.activeTab.set('olt');
      if (type === 'olt') expandOlt(id);
      return;
    }
    if (type === 'niveau_exigence') {
      for (const olt of enjeu.objectifs_long_terme || []) {
        const ne = (olt.niveaux_exigence || []).find(n => n.id_ne === id);
        if (ne) {
          this.activeTab.set('olt');
          expandOlt(olt.id_olt);
          return;
        }
      }
      return;
    }

    // === Branche OO (oo / resultat_attendu) ===
    if (type === 'oo') {
      this.activeTab.set('operations');
      expandOo(id);
      return;
    }
    if (type === 'resultat_attendu') {
      for (const fi of enjeu.facteurs_influence || []) {
        for (const p of fi.pressions || []) {
          for (const oo of p.objectifs_operationnels || []) {
            const ra = (oo.resultats_attendus || []).find(r => r.id_ra === id);
            if (ra) {
              this.activeTab.set('operations');
              expandOo(oo.id_oo);
              return;
            }
          }
        }
      }
      return;
    }

    // === Indicateur / métrique : peut être sous OLT (NE) OU OO (RA). On essaie OLT d'abord. ===
    if (type === 'indicateur' || type === 'metrique') {
      // Branche OLT
      for (const olt of enjeu.objectifs_long_terme || []) {
        for (const ne of olt.niveaux_exigence || []) {
          for (const ind of ne.indicateurs || []) {
            const isInd = type === 'indicateur' && ind.id_indicateur === id;
            const isMet = type === 'metrique' && (ind.metriques || []).some(m => m.id_metrique === id);
            if (isInd || isMet) {
              this.activeTab.set('olt');
              expandOlt(olt.id_olt);
              expandIndicateur(ind.id_indicateur);
              return;
            }
          }
        }
      }
      // Branche OO/RA
      for (const fi of enjeu.facteurs_influence || []) {
        for (const p of fi.pressions || []) {
          for (const oo of p.objectifs_operationnels || []) {
            for (const ra of oo.resultats_attendus || []) {
              for (const ind of ra.indicateurs || []) {
                const isInd = type === 'indicateur' && ind.id_indicateur === id;
                const isMet = type === 'metrique' && (ind.metriques || []).some(m => m.id_metrique === id);
                if (isInd || isMet) {
                  this.activeTab.set('operations');
                  expandOo(oo.id_oo);
                  expandOoIndicateur(ind.id_indicateur);
                  return;
                }
              }
            }
          }
        }
      }
    }
  }

  // ============================================
  // Sauvegarde / restauration de l'état UI (sessionStorage)
  // Permet de retrouver les nœuds dépliés et la position de scroll au retour
  // depuis un formulaire (création/édition action, enjeu, FCR…).
  // ============================================

  private uiStateKey(): string {
    return `enjeux-ui-state:${this.planSlug()}:${this.selectedEnjeuSlug() || ''}`;
  }

  private saveUiState(): void {
    if (!this.planSlug() || !this.selectedEnjeuSlug()) return;
    const state = {
      activeTab: this.activeTab(),
      enjeuDetailExpanded: this.enjeuDetailExpanded(),
      expandedFcrIds: Array.from(this.expandedFcrIds()),
      expandedFacteurIds: Array.from(this.expandedFacteurIds()),
      expandedPressionIds: Array.from(this.expandedPressionIds()),
      expandedOltIds: Array.from(this.expandedOltIds()),
      expandedIndicateurIds: Array.from(this.expandedIndicateurIds()),
      expandedOperationIds: Array.from(this.expandedOperationIds()),
      expandedOoIds: Array.from(this.expandedOoIds()),
      expandedOoIndicateurIds: Array.from(this.expandedOoIndicateurIds()),
      expandedOoOperationIds: Array.from(this.expandedOoOperationIds()),
      expandedRaIds: Array.from(this.expandedRaIds()),
      scrollY: window.scrollY,
      anchor: this.lastScrollAnchor,
    };
    try {
      sessionStorage.setItem(this.uiStateKey(), JSON.stringify(state));
    } catch {
      // QuotaExceeded ou sessionStorage indisponible — on ignore silencieusement
    }
  }

  private restoreUiState(skipScroll: boolean): void {
    if (!this.selectedEnjeuSlug()) return;
    let raw: string | null = null;
    try {
      raw = sessionStorage.getItem(this.uiStateKey());
    } catch {
      return;
    }
    if (!raw) return;
    try {
      const state = JSON.parse(raw) as Partial<{
        activeTab: TabType;
        enjeuDetailExpanded: boolean;
        expandedFcrIds: number[];
        expandedFacteurIds: number[];
        expandedPressionIds: number[];
        expandedOltIds: number[];
        expandedIndicateurIds: number[];
        expandedOperationIds: number[];
        expandedOoIds: number[];
        expandedOoIndicateurIds: number[];
        expandedOoOperationIds: number[];
        expandedRaIds: number[];
        scrollY: number;
        anchor: { type: 'operation' | 'metrique'; id: number } | null;
      }>;
      if (state.activeTab === 'detail' || state.activeTab === 'olt' || state.activeTab === 'operations') {
        // Ne pas écraser si la query string a déjà fixé un onglet plus pertinent
        const urlTab = this.route.snapshot.queryParamMap.get('tab');
        if (!urlTab) this.activeTab.set(state.activeTab);
      }
      if (typeof state.enjeuDetailExpanded === 'boolean') this.enjeuDetailExpanded.set(state.enjeuDetailExpanded);
      this.expandedFcrIds.set(new Set<number>(state.expandedFcrIds ?? []));
      this.expandedFacteurIds.set(new Set<number>(state.expandedFacteurIds ?? []));
      this.expandedPressionIds.set(new Set<number>(state.expandedPressionIds ?? []));
      this.expandedOltIds.set(new Set<number>(state.expandedOltIds ?? []));
      this.expandedIndicateurIds.set(new Set<number>(state.expandedIndicateurIds ?? []));
      this.expandedOperationIds.set(new Set<number>(state.expandedOperationIds ?? []));
      this.expandedOoIds.set(new Set<number>(state.expandedOoIds ?? []));
      this.expandedOoIndicateurIds.set(new Set<number>(state.expandedOoIndicateurIds ?? []));
      this.expandedOoOperationIds.set(new Set<number>(state.expandedOoOperationIds ?? []));
      this.expandedRaIds.set(new Set<number>(state.expandedRaIds ?? []));
      if (!skipScroll) {
        // Priorité à l'ancre élément (plus fiable que window.scrollTo qui peut clamper
        // si la hauteur du document n'est pas encore stabilisée).
        if (state.anchor) {
          this.lastScrollAnchor = state.anchor;
          const elementId = `${state.anchor.type}-${state.anchor.id}`;
          // scrollToElement poll le DOM jusqu'à 2s (le temps que les @if dépliés rendent)
          setTimeout(() => this.scrollToElement(elementId), 50);
        } else if (typeof state.scrollY === 'number') {
          const targetY = state.scrollY;
          setTimeout(() => window.scrollTo({ top: targetY, behavior: 'instant' as ScrollBehavior }), 50);
        }
      }
    } catch {
      // JSON corrompu — ignorer
    }
  }

  /** Réinitialise tous les sets d'expansion + l'ancre de scroll. Utilisé lors d'un changement
   *  d'enjeu pour éviter que les IDs dépliés du précédent enjeu ne restent dans les signaux. */
  private resetExpansionState(): void {
    this.expandedFcrIds.set(new Set());
    this.expandedFacteurIds.set(new Set());
    this.expandedPressionIds.set(new Set());
    this.expandedOltIds.set(new Set());
    this.expandedIndicateurIds.set(new Set());
    this.expandedOperationIds.set(new Set());
    this.expandedOoIds.set(new Set());
    this.expandedOoIndicateurIds.set(new Set());
    this.expandedOoOperationIds.set(new Set());
    this.expandedRaIds.set(new Set());
    this.lastScrollAnchor = null;
  }

  ngOnDestroy(): void {
    this.saveUiState();
  }

  // ============================================
  // Optimistic local update helpers
  // ============================================

  private patchPlanEnjeuxData(mapper: (data: PlanEnjeuxResponse) => PlanEnjeuxResponse): void {
    const current = this.planEnjeuxData();
    if (!current) return;
    const updated = mapper(current);
    this.planEnjeuxData.set(updated);
    this.enjeuService.updatePlanEnjeuxCache(updated);
  }

  private mapEnjeuInResponse(
    data: PlanEnjeuxResponse,
    enjeuId: number,
    transform: (enjeu: Enjeu) => Enjeu
  ): PlanEnjeuxResponse {
    return {
      ...data,
      enjeux: data.enjeux.map(e => e.id_enjeu === enjeuId ? transform(e) : e),
      fcr: data.fcr.map(e => e.id_enjeu === enjeuId ? transform(e) : e),
    };
  }

  /**
   * Met à jour les opérations d'une métrique dans l'arbre local des enjeux.
   * Parcourt les deux branches (NE et OO) pour trouver la métrique cible.
   */
  private updateMetriqueOperations(
    metriqueId: number,
    updater: (ops: Operation[]) => Operation[]
  ): void {
    this.patchPlanEnjeuxData(data => {
      const mapMetriques = (metriques: any[]): any[] =>
        metriques.map(met =>
          met.id_metrique === metriqueId
            ? { ...met, operations: updater(met.operations || []) }
            : met
        );

      const mapEnjeu = (enjeu: Enjeu): Enjeu => ({
        ...enjeu,
        // Branche NE
        objectifs_long_terme: (enjeu.objectifs_long_terme || []).map(olt => ({
          ...olt,
          niveaux_exigence: (olt.niveaux_exigence || []).map(ne => ({
            ...ne,
            indicateurs: (ne.indicateurs || []).map(ind => ({
              ...ind,
              metriques: mapMetriques(ind.metriques || []),
            })),
          })),
        })),
        // Branche OO
        facteurs_influence: (enjeu.facteurs_influence || []).map(fi => ({
          ...fi,
          pressions: (fi.pressions || []).map(pr => ({
            ...pr,
            objectifs_operationnels: (pr.objectifs_operationnels || []).map(oo => ({
              ...oo,
              resultats_attendus: (oo.resultats_attendus || []).map(ra => ({
                ...ra,
                indicateurs: (ra.indicateurs || []).map(ind => ({
                  ...ind,
                  metriques: mapMetriques(ind.metriques || []),
                })),
              })),
            })),
          })),
        })),
      });

      return {
        ...data,
        enjeux: data.enjeux.map(mapEnjeu),
        fcr: data.fcr.map(mapEnjeu),
      };
    });
  }

  // Navigation
  navigateToArborescence(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'tableau-d-arborescence']);
    }
  }

  navigateToNewEnjeu(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'enjeux', 'nouveau']);
    }
  }

  navigateToMindmap(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'tableau-d-arborescence']);
    }
  }

  navigateToNewFcr(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'enjeux', 'fcr', 'nouveau']);
    }
  }

  navigateToEdit(item: Enjeu): void {
    const slug = this.planSlug();
    if (!slug) return;

    if (item.categorie_mnemonique === 'FCR') {
      this.router.navigate(['/plans', slug, 'enjeux', 'fcr', item.id_enjeu, 'modifier']);
    } else {
      this.router.navigate(['/plans', slug, 'enjeux', item.slug, 'modifier']);
    }
  }

  // Onglets (vue détail)
  setActiveTab(tab: TabType): void {
    this.activeTab.set(tab);
    // Synchroniser l'onglet à l'URL pour que back/refresh restaurent le bon onglet
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { tab: tab === 'detail' ? null : tab },
      queryParamsHandling: 'merge',
      replaceUrl: true,
    });
  }

  // Toggle detail card expand/collapse
  toggleEnjeuDetail(): void {
    this.enjeuDetailExpanded.update(v => !v);
  }

  // Toggle FCR card expand/collapse
  toggleFcr(id: number): void {
    this.expandedFcrIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isFcrExpanded(id: number): boolean {
    return this.expandedFcrIds().has(id);
  }

  // Computed pour les facteurs d'influence de l'enjeu sélectionné
  selectedFacteurs = computed(() => {
    return this.selectedEnjeu()?.facteurs_influence || [];
  });

  // #474 — pressions proposées (de façon FACULTATIVE) au rattachement d'un OO de
  // FCR, groupées par « enjeu › facteur d'influence » pour le sélecteur.
  // Retour 02/07/2026 : un FCR PEUT porter ses propres pressions ; on les
  // affiche donc EN PREMIER (premier plan), suivies des pressions des enjeux
  // ÉCOLOGIQUES du plan.
  ecologicalPressionGroups = computed(() => {
    const data = this.planEnjeuxData();
    if (!data) return [] as { label: string; pressions: { id_pression: number; libelle: string }[] }[];
    const groups: { label: string; pressions: { id_pression: number; libelle: string }[] }[] = [];

    const pushGroups = (enjeu: Enjeu) => {
      const enjeuLibelle = enjeu.intitule_court || enjeu.libelle;
      for (const fi of enjeu.facteurs_influence || []) {
        const pressions = (fi.pressions || []).map(p => ({ id_pression: p.id_pression, libelle: p.libelle }));
        if (pressions.length) {
          groups.push({ label: `${enjeuLibelle} › ${fi.libelle}`, pressions });
        }
      }
    };

    // 1. Pressions propres au FCR sélectionné → en premier plan (#474 retour 02/07).
    const selected = this.selectedEnjeu();
    if (selected && this.isSelectedFcr()) {
      pushGroups(selected);
    }

    // 2. Pressions des enjeux écologiques du plan.
    for (const enjeu of data.enjeux || []) {
      pushGroups(enjeu);
    }

    return groups;
  });

  // Computed pour le nombre d'OLT de l'enjeu sélectionné
  totalOltCount = computed(() => {
    return this.selectedEnjeu()?.objectifs_long_terme?.length || 0;
  });

  // Computed pour les pressions de l'enjeu sélectionné (via facteurs d'influence).
  // #228 — Dépendance explicite sur `planEnjeuxData()` pour que les mutations
  // in-place (DnD) déclenchent un re-render. Sans ça, `selectedEnjeu` peut
  // retourner la même référence après update et bloquer la propagation.
  selectedPressions = computed(() => {
    this.planEnjeuxData();  // force dep on root signal
    const enjeu = this.selectedEnjeu();
    if (!enjeu) return [];
    return (enjeu.facteurs_influence || []).flatMap(fi => fi.pressions || []);
  });

  // Computed pour les OOs de l'enjeu sélectionné (via facteurs → pressions, dédupliqués).
  // #228 — Dépendance explicite sur planEnjeuxData + tri final par `ordre`.
  // Le tri rend visible un DnD inter-OO (les OO partagés par M2M ont leur
  // ordre propagé par propagateOrdresToDuplicates, donc tous les exemplaires
  // ont le bon `ordre` au moment où on les lit ici).
  selectedOos = computed(() => {
    this.planEnjeuxData();  // force dep on root signal
    // #337 — un FCR n'a pas de pression : ses OO sont rattachés directement à
    // l'enjeu et exposés via `objectifs_operationnels`.
    const enjeu = this.selectedEnjeu();
    const source = this.isSelectedFcr()
      ? (enjeu?.objectifs_operationnels || [])
      : this.selectedPressions().flatMap(p => p.objectifs_operationnels || []);
    const seen = new Set<number>();
    const unique = source.filter(oo => {
      if (seen.has(oo.id_oo)) return false;
      seen.add(oo.id_oo);
      return true;
    });
    // #552 — l'ordre d'un OO est propre à l'enjeu affiché : on applique la
    // surcharge `oo_ordre` de l'enjeu (portée par CorOoEnjeu côté back), et on
    // retombe sur l'ordre global de l'OO s'il n'y a pas de surcharge.
    const overrides = enjeu?.oo_ordre || {};
    const ordreOf = (oo: ObjectifOperationnel) =>
      overrides[oo.id_oo] ?? (oo as any).ordre ?? 0;
    return [...unique].sort((a, b) => {
      const ordreA = ordreOf(a);
      const ordreB = ordreOf(b);
      if (ordreA !== ordreB) return ordreA - ordreB;
      return a.id_oo - b.id_oo;
    });
  });

  totalOoCount = computed(() => {
    return this.selectedOos().length;
  });

  /**
   * #526 / #442 — Numérotation des OO du parent affiché (dérivée de l'ordre
   * d'affichage), avec possibilité de fixer un numéro manuellement
   * (`numero_manuel`), sur le même principe que l'OLT. Un numéro fixé est
   * réservé et l'auto-numérotation des autres OO le saute.
   */
  ooLocalRank = computed<Map<number, number>>(() => {
    const oos = this.selectedOos();
    const map = new Map<number, number>();

    // #552 — Numéro plan-wide fourni par le back (`numero_affichage`) :
    // identique sous tous les enjeux où l'OO est partagé. On l'utilise dès
    // qu'il est présent ; sinon (réponse plate sans by-plan) on retombe sur
    // l'ancienne numérotation par enjeu.
    if (oos.some(oo => oo.numero_affichage != null)) {
      for (const oo of oos) {
        if (oo.numero_affichage != null) map.set(oo.id_oo, oo.numero_affichage);
      }
      return map;
    }

    // Repli — numérotation par enjeu (indices manuels réservés).
    const reserved = new Set<number>();
    for (const oo of oos) {
      if (oo.numero_manuel != null) reserved.add(oo.numero_manuel);
    }
    let auto = 0;
    for (const oo of oos) {
      if (oo.numero_manuel != null) {
        map.set(oo.id_oo, oo.numero_manuel);
      } else {
        // Prochain indice automatique libre (non réservé).
        auto += 1;
        while (reserved.has(auto)) auto += 1;
        map.set(oo.id_oo, auto);
      }
    }
    return map;
  });

  /** Numéro affiché d'un OO (fixé ou automatique). Null si inconnu. */
  getOoNumber(ooId: number | undefined): number | null {
    if (ooId == null) return null;
    return this.ooLocalRank().get(ooId) ?? null;
  }

  /** Ouvre la modale de demande d'accès au plan, option « Référent » présélectionnée. */
  requestBecomeReferent(): void {
    const id = this.planId();
    if (!id) return;
    this.dialog.open(AccessRequestDialogComponent, {
      width: '500px',
      data: {
        type: 'plan',
        targetId: id,
        targetName: this.planNom(),
        hasAccessViaSite: true,
        defaultAsReferent: true,
      } as AccessRequestDialogData,
    });
  }

  // Event handlers pour les accordéons
  onEnjeuDelete(enjeu: Enjeu): void {
    const isFcr = enjeu.categorie_mnemonique === 'FCR';

    // Calcul de l'impact cascade (revue design Amandine — afficher explicitement
    // les entités qui seront supprimées avec l'enjeu)
    const impactList: { label: string; count: number; icon?: string }[] = [];
    if (!isFcr) {
      let nbFacteurs = 0, nbPressions = 0, nbOlts = 0, nbNes = 0, nbOos = 0, nbRas = 0, nbIndicateurs = 0;
      for (const fi of enjeu.facteurs_influence || []) {
        nbFacteurs++;
        for (const p of fi.pressions || []) {
          nbPressions++;
          for (const oo of p.objectifs_operationnels || []) {
            nbOos++;
            for (const ra of oo.resultats_attendus || []) {
              nbRas++;
              nbIndicateurs += (ra.indicateurs || []).length;
            }
          }
        }
      }
      for (const olt of enjeu.objectifs_long_terme || []) {
        nbOlts++;
        for (const ne of olt.niveaux_exigence || []) {
          nbNes++;
          nbIndicateurs += (ne.indicateurs || []).length;
        }
      }
      if (nbFacteurs) impactList.push({ label: this.translate.instant('enjeux.cascade.facteurs', { count: nbFacteurs }), count: nbFacteurs, icon: 'fi-rr-chart-tree' });
      if (nbPressions) impactList.push({ label: this.translate.instant('enjeux.cascade.pressions', { count: nbPressions }), count: nbPressions, icon: 'fi-rr-triangle-warning' });
      if (nbOlts) impactList.push({ label: this.translate.instant('enjeux.cascade.olt', { count: nbOlts }), count: nbOlts, icon: 'fi-rr-bullseye-arrow' });
      if (nbNes) impactList.push({ label: this.translate.instant('enjeux.cascade.ne', { count: nbNes }), count: nbNes, icon: 'fi-rr-target' });
      if (nbOos) impactList.push({ label: this.translate.instant('enjeux.cascade.oo', { count: nbOos }), count: nbOos, icon: 'fi-rr-edit' });
      if (nbRas) impactList.push({ label: this.translate.instant('enjeux.cascade.ra', { count: nbRas }), count: nbRas, icon: 'fi-rr-check' });
      if (nbIndicateurs) impactList.push({ label: this.translate.instant('enjeux.cascade.indicateurs', { count: nbIndicateurs }), count: nbIndicateurs, icon: 'fi-rr-chart-line-up' });
    }

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '520px',
      data: {
        title: isFcr
          ? this.translate.instant('enjeux.messages.fcrDeleteConfirmTitle')
          : this.translate.instant('enjeux.messages.enjeuDeleteConfirmTitle'),
        message: isFcr
          ? this.translate.instant('enjeux.messages.fcrDeleteConfirm')
          : this.translate.instant('enjeux.messages.enjeuDeleteConfirm'),
        impactList: impactList.length > 0 ? impactList : undefined,
        warningText: impactList.length > 0 ? this.translate.instant('common.cascadeDelete.warning') : undefined,
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        destructive: true
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteEnjeu(enjeu.id_enjeu).subscribe({
          next: () => {
            // Si l'enjeu supprimé était sélectionné, retourner à la liste
            if (this.selectedEnjeu()?.id_enjeu === enjeu.id_enjeu) {
              const slug = this.planSlug();
              if (slug) {
                this.router.navigate(['/plans', slug, 'enjeux']);
              }
            }
            this.loadPlanData(true);
          },
          error: () => {
            this.errorMessage.set(
              this.translate.instant('enjeux.messages.deleteError')
            );
          }
        });
      }
    });
  }

  // Navigation vers le détail depuis l'accordéon
  navigateToEnjeuDetail(enjeu: Enjeu): void {
    const slug = this.planSlug();
    if (slug && enjeu.slug) {
      this.router.navigate(['/plans', slug, 'enjeux', enjeu.slug]);
    }
  }

  // ============================================
  // Facteurs d'Influence
  // ============================================

  toggleFacteur(id: number): void {
    this.expandedFacteurIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isFacteurExpanded(id: number): boolean {
    return this.expandedFacteurIds().has(id);
  }

  startAddFacteur(): void {
    this.addingFacteurInfluence.set(true);
    this.newFacteurLibelle = '';
    this.newFacteurDescription = '';
  }

  cancelAddFacteur(): void {
    this.addingFacteurInfluence.set(false);
    this.newFacteurLibelle = '';
    this.newFacteurDescription = '';
  }

  saveFacteurInfluence(): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu || !this.newFacteurLibelle.trim()) return;

    this.enjeuService.createFacteurInfluence({
      id_enjeu: enjeu.id_enjeu,
      libelle: this.newFacteurLibelle.trim(),
      description: this.newFacteurDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.facteurInfluence.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddFacteur();
        this.loadPlanData(true);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  // ============================================
  // Boutons « Je n'ai pas de … » (#523)
  // Crée un élément placeholder « Non défini » sans passer par le formulaire,
  // puis rappelle qu'il est préconisé de le renseigner. Aucune modification du modèle.
  // ============================================

  /** Libellé placeholder « Non défini » commun. */
  private get undefinedLabel(): string {
    return this.translate.instant('enjeux.undefined.label');
  }

  /** Souscrit à la création d'un placeholder et affiche la préconisation. */
  private createUndefinedElement(request$: Observable<any>): void {
    request$.subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.undefined.recommendation'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
        this.loadPlanData(true);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  createUndefinedFacteur(): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu) return;
    this.createUndefinedElement(
      this.enjeuService.createFacteurInfluence({
        id_enjeu: enjeu.id_enjeu,
        libelle: this.undefinedLabel
      })
    );
  }

  createUndefinedPression(facteur: FacteurInfluence): void {
    this.createUndefinedElement(
      this.enjeuService.createPression({
        id_facteur_influence: facteur.id_facteur_influence,
        libelle: this.undefinedLabel
      })
    );
  }

  createUndefinedNe(olt: ObjectifLongTerme): void {
    this.createUndefinedElement(
      this.enjeuService.createNiveauExigence({
        id_olt: olt.id_olt,
        libelle: this.undefinedLabel
      })
    );
  }

  createUndefinedRa(oo: ObjectifOperationnel): void {
    this.createUndefinedElement(
      this.enjeuService.createResultatAttendu({
        id_oo: oo.id_oo,
        libelle: this.undefinedLabel
      })
    );
  }

  createUndefinedIndicateur(ne: NiveauExigence): void {
    this.createUndefinedElement(
      this.enjeuService.createIndicateur({
        id_ne: ne.id_ne,
        nom_indicateur: this.undefinedLabel,
        est_standardise: false
      })
    );
  }

  createUndefinedIndicateurForRa(ra: ResultatAttendu): void {
    this.createUndefinedElement(
      this.enjeuService.createIndicateur({
        id_resultat_attendu: ra.id_ra,
        nom_indicateur: this.undefinedLabel,
        est_standardise: false
      })
    );
  }

  deleteFacteur(facteur: FacteurInfluence): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.facteurInfluence.deleteTitle'),
        message: this.translate.instant('enjeux.facteurInfluence.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteFacteurInfluence(facteur.id_facteur_influence).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.facteurInfluence.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData(true);
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Pressions
  // ============================================

  togglePression(id: number): void {
    this.expandedPressionIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isPressionExpanded(id: number): boolean {
    return this.expandedPressionIds().has(id);
  }

  startAddPression(facteurId: number): void {
    this.addingPressionForFacteur.set(facteurId);
    this.newPressionLibelle = '';
    this.newPressionDescription = '';
    this.selectedPressref.set(null);
    this.pressrefSearchCtrl.setValue('', { emitEvent: false });
    this.pressrefSearchText.set('');
  }

  cancelAddPression(): void {
    this.addingPressionForFacteur.set(null);
    this.newPressionLibelle = '';
    this.newPressionDescription = '';
    this.selectedPressref.set(null);
    this.pressrefSearchCtrl.setValue('', { emitEvent: false });
    this.pressrefSearchText.set('');
  }

  onPressrefSelected(option: NomenclatureOption): void {
    this.selectedPressref.set(option);
    // Pré-remplir l'intitulé seulement s'il est vide
    if (!this.newPressionLibelle.trim()) {
      this.newPressionLibelle = option.label;
    }
  }

  clearPressref(): void {
    this.selectedPressref.set(null);
    this.pressrefSearchCtrl.setValue('');
    this.pressrefSearchText.set('');
  }

  onEditPressrefSelected(option: NomenclatureOption): void {
    this.editSelectedPressref.set(option);
  }

  clearEditPressref(): void {
    this.editSelectedPressref.set(null);
    this.editPressrefSearchCtrl.setValue('');
    this.editPressrefSearchText.set('');
  }

  parsePressrefDefinition = parseNomenclatureDefinition;

  savePression(facteur: FacteurInfluence): void {
    if (!this.newPressionLibelle.trim()) return;

    this.enjeuService.createPression({
      id_facteur_influence: facteur.id_facteur_influence,
      id_type_pression: this.selectedPressref()?.id_nomenclature || undefined,
      libelle: this.newPressionLibelle.trim(),
      description: this.newPressionDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.pression.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddPression();
        this.loadPlanData(true);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  deletePression(pression: Pression): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.pression.deleteTitle'),
        message: this.translate.instant('enjeux.pression.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deletePression(pression.id_pression).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.pression.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData(true);
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Facteurs d'influence — édition inline
  // ============================================

  /** Tous les enjeux et FCR du plan (source des cibles de partage/copie). */
  private allEnjeuxAndFcr(): Enjeu[] {
    return [...this.enjeux(), ...this.fcr()];
  }

  /** #552 — Enjeux sous lesquels un facteur est déjà présent (partage M2M). */
  facteurEnjeuIds(facteur: FacteurInfluence): number[] {
    return facteur.enjeu_ids?.length ? facteur.enjeu_ids : [facteur.id_enjeu];
  }

  /** #552 — Vrai si le facteur est partagé entre plusieurs enjeux. */
  isFacteurShared(facteur: FacteurInfluence): boolean {
    return this.facteurEnjeuIds(facteur).length > 1;
  }

  /** #552 — Vrai si l'OO est partagé entre plusieurs enjeux. */
  isOoShared(oo: ObjectifOperationnel): boolean {
    return (oo.shared_enjeu_ids?.length ?? 0) > 1;
  }

  /**
   * #552 — Ouvre le dialogue « Lier / Copier » pour partager un facteur vers un
   * autre enjeu (élément unique) ou en créer une copie indépendante.
   */
  openShareFacteur(facteur: FacteurInfluence, mode: 'link' | 'copy'): void {
    if (!this.canEditPlan()) return;
    const currentEnjeuIds = new Set(this.facteurEnjeuIds(facteur));
    const targets: ShareEnjeuTarget[] = this.allEnjeuxAndFcr()
      .filter((e) => !currentEnjeuIds.has(e.id_enjeu))
      .map((e) => ({ id_enjeu: e.id_enjeu, libelle: e.libelle }));

    const dialogRef = this.dialog.open(ShareElementDialogComponent, {
      width: '640px', maxWidth: '95vw', maxHeight: '90vh',
      data: {
        elementType: 'facteur',
        elementLabel: facteur.libelle,
        mode,
        enjeux: targets,
      } as ShareElementDialogData,
    });

    dialogRef.afterClosed().pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result: ShareElementDialogResult | null) => {
        if (!result || result.targetEnjeuId == null) return;
        const isCopy = result.mode === 'copy';
        const call$ = isCopy
          ? this.enjeuService.copyFacteurToEnjeu(facteur.id_facteur_influence, result.targetEnjeuId)
          : this.enjeuService.linkFacteurToEnjeu(facteur.id_facteur_influence, result.targetEnjeuId);
        this.runShareCall(call$, isCopy ? 'enjeux.share.facteur.copySuccess' : 'enjeux.share.facteur.linkSuccess',
          isCopy ? 'enjeux.share.facteur.copyError' : 'enjeux.share.facteur.linkError');
      });
  }

  /**
   * #552 — Ouvre le dialogue « Lier / Copier » pour partager un OO vers une
   * pression d'un autre enjeu (élément unique) ou en créer une copie
   * indépendante.
   */
  openShareOo(oo: ObjectifOperationnel, mode: 'link' | 'copy'): void {
    if (!this.canEditPlan()) return;
    const linkedPressionIds = new Set(oo.pression_ids || []);
    const targets: ShareEnjeuTarget[] = [];
    for (const e of this.allEnjeuxAndFcr()) {
      const pressions: SharePressionTarget[] = [];
      for (const fi of e.facteurs_influence || []) {
        for (const pr of fi.pressions || []) {
          if (linkedPressionIds.has(pr.id_pression)) continue;
          pressions.push({ id_pression: pr.id_pression, libelle: pr.libelle, facteurLibelle: fi.libelle });
        }
      }
      if (pressions.length) {
        targets.push({ id_enjeu: e.id_enjeu, libelle: e.libelle, pressions });
      }
    }

    const dialogRef = this.dialog.open(ShareElementDialogComponent, {
      width: '640px', maxWidth: '95vw', maxHeight: '90vh',
      data: {
        elementType: 'oo',
        elementLabel: oo.libelle,
        mode,
        enjeux: targets,
      } as ShareElementDialogData,
    });

    dialogRef.afterClosed().pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result: ShareElementDialogResult | null) => {
        if (!result || result.targetPressionId == null) return;
        const isCopy = result.mode === 'copy';
        const call$ = isCopy
          ? this.enjeuService.copyOo(oo.id_oo, { pressionId: result.targetPressionId })
          : this.enjeuService.linkOoToPression(oo.id_oo, result.targetPressionId);
        this.runShareCall(call$, isCopy ? 'enjeux.share.oo.copySuccess' : 'enjeux.share.oo.linkSuccess',
          isCopy ? 'enjeux.share.oo.copyError' : 'enjeux.share.oo.linkError');
      });
  }

  /** Exécute un appel de partage/copie et rafraîchit la vue avec feedback. */
  private runShareCall(call$: Observable<unknown>, okKey: string, errKey: string): void {
    call$.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant(okKey),
          this.translate.instant('common.actions.close'),
          { duration: 3000 },
        );
        this.loadPlanData(true);
      },
      error: () => {
        this.snackBar.open(
          this.translate.instant(errKey),
          this.translate.instant('common.actions.close'),
          { duration: 3000 },
        );
      },
    });
  }

  startEditFacteur(facteur: FacteurInfluence): void {
    this.editingFacteurId.set(facteur.id_facteur_influence);
    this.editFacteurLibelle = facteur.libelle;
    this.editFacteurDescription = facteur.description || '';
  }

  cancelEditFacteur(): void {
    this.editingFacteurId.set(null);
    this.editFacteurLibelle = '';
    this.editFacteurDescription = '';
  }

  saveEditFacteur(facteur: FacteurInfluence): void {
    if (!this.editFacteurLibelle.trim()) return;
    const newLibelle = this.editFacteurLibelle.trim();
    const newDescription = this.editFacteurDescription.trim() || undefined;

    this.enjeuService.updateFacteurInfluence(facteur.id_facteur_influence, {
      libelle: newLibelle,
      description: newDescription
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.facteurInfluence.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditFacteur();
        const enjeu = this.selectedEnjeu();
        if (enjeu) {
          this.patchPlanEnjeuxData(data => this.mapEnjeuInResponse(data, enjeu.id_enjeu, e => ({
            ...e,
            facteurs_influence: (e.facteurs_influence || []).map(f =>
              f.id_facteur_influence === facteur.id_facteur_influence
                ? { ...f, libelle: newLibelle, description: newDescription }
                : f
            ),
          })));
        }
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  // ============================================
  // Pressions — édition inline
  // ============================================

  startEditPression(pression: Pression): void {
    this.editingPressionId.set(pression.id_pression);
    this.editPressionLibelle = pression.libelle;
    this.editPressionDescription = pression.description || '';
    // Restaurer la sélection PressRef si elle existe
    if (pression.id_type_pression) {
      const match = this.pressrefOptions().find(o => o.id_nomenclature === pression.id_type_pression);
      if (match) {
        this.editSelectedPressref.set(match);
        this.editPressrefSearchCtrl.setValue(displayNomenclatureFn(match), { emitEvent: false });
      } else {
        this.editSelectedPressref.set(null);
        this.editPressrefSearchCtrl.setValue('', { emitEvent: false });
      }
    } else {
      this.editSelectedPressref.set(null);
      this.editPressrefSearchCtrl.setValue('', { emitEvent: false });
    }
    this.editPressrefSearchText.set('');
  }

  cancelEditPression(): void {
    this.editingPressionId.set(null);
    this.editPressionLibelle = '';
    this.editPressionDescription = '';
    this.editSelectedPressref.set(null);
    this.editPressrefSearchCtrl.setValue('', { emitEvent: false });
    this.editPressrefSearchText.set('');
  }

  saveEditPression(pression: Pression): void {
    if (!this.editPressionLibelle.trim()) return;
    const newLibelle = this.editPressionLibelle.trim();
    const newDescription = this.editPressionDescription.trim() || undefined;
    const newTypePression = this.editSelectedPressref()?.id_nomenclature || null;

    this.enjeuService.updatePression(pression.id_pression, {
      id_type_pression: newTypePression as any,
      libelle: newLibelle,
      description: newDescription
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.pression.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditPression();
        this.loadPlanData(true);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  // ============================================
  // Objectifs à Long Terme (OLT)
  // ============================================

  toggleOlt(id: number): void {
    this.expandedOltIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isOltExpanded(id: number): boolean {
    return this.expandedOltIds().has(id);
  }

  // ============================================
  // Résultats Attendus (RA) — déplier/replier indicateurs (revue design Amandine)
  // ============================================

  toggleRa(id: number): void {
    this.expandedRaIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isRaExpanded(id: number): boolean {
    return this.expandedRaIds().has(id);
  }

  // #344 — Repli des niveaux d'exigence (vue OLT). Le set contient les NE
  // REPLIÉES ; vide = toutes dépliées (comportement par défaut).
  collapsedNeIds = signal<Set<number>>(new Set());

  toggleNe(id: number): void {
    this.collapsedNeIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isNeExpanded(id: number): boolean {
    return !this.collapsedNeIds().has(id);
  }

  startAddOlt(): void {
    if (this.totalOltCount() > 0) {
      const dialogRef = this.dialog.open(ConfirmDialogComponent, {
        width: '500px',
        data: {
          title: this.translate.instant('enjeux.olt.alreadyExistsTitle'),
          message: this.translate.instant('enjeux.olt.alreadyExistsMessage'),
          confirmText: this.translate.instant('enjeux.olt.alreadyExistsConfirm'),
          cancelText: this.translate.instant('common.actions.cancel'),
          confirmColor: 'primary'
        }
      });

      dialogRef.afterClosed().subscribe(confirmed => {
        if (confirmed) {
          this.addingOlt.set(true);
          this.newOltLibelle = '';
          this.newOltDescription = '';
        }
      });
    } else {
      this.addingOlt.set(true);
      this.newOltLibelle = '';
      this.newOltDescription = '';
    }
  }

  cancelAddOlt(): void {
    this.addingOlt.set(false);
    this.newOltLibelle = '';
    this.newOltDescription = '';
  }

  saveOlt(): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu || !this.newOltLibelle.trim()) return;

    this.enjeuService.createObjectifLongTerme({
      id_enjeu: enjeu.id_enjeu,
      libelle: this.newOltLibelle.trim(),
      description: this.newOltDescription.trim() || undefined
    }).subscribe({
      next: (newOlt) => {
        this.snackBar.open(
          this.translate.instant('enjeux.olt.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddOlt();
        const createdOlt: ObjectifLongTerme = {
          id_olt: newOlt.id_olt,
          id_enjeu: enjeu.id_enjeu,
          libelle: newOlt.libelle,
          description: newOlt.description,
          niveaux_exigence: [],
          date_ajout: newOlt.date_ajout || new Date().toISOString(),
          date_maj: newOlt.date_maj || new Date().toISOString(),
        };
        this.patchPlanEnjeuxData(data => this.mapEnjeuInResponse(data, enjeu.id_enjeu, e => ({
          ...e,
          objectifs_long_terme: [...(e.objectifs_long_terme || []), createdOlt],
          nb_objectifs_long_terme: (e.nb_objectifs_long_terme || 0) + 1,
        })));
        // Déplier le nouvel OLT par défaut (revue design #316)
        this.expandedOltIds.update(s => {
          const ns = new Set(s);
          ns.add(createdOlt.id_olt);
          return ns;
        });
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  startEditOlt(olt: ObjectifLongTerme): void {
    this.editingOltId.set(olt.id_olt);
    this.editOltLibelle = olt.libelle;
    this.editOltDescription = olt.description || '';
    this.editOltNumero = olt.numero_manuel ?? null;
  }

  cancelEditOlt(): void {
    this.editingOltId.set(null);
    this.editOltLibelle = '';
    this.editOltDescription = '';
    this.editOltNumero = null;
  }

  saveEditOlt(olt: ObjectifLongTerme): void {
    if (!this.editOltLibelle.trim()) return;
    const newLibelle = this.editOltLibelle.trim();
    const newDescription = this.editOltDescription.trim() || undefined;
    // #442 — Vide/0/invalide → numérotation automatique (null).
    const rawNumero = this.editOltNumero;
    const newNumero = rawNumero != null && rawNumero > 0 ? Math.floor(rawNumero) : null;

    this.enjeuService.updateObjectifLongTerme(olt.id_olt, {
      libelle: newLibelle,
      description: newDescription,
      numero_manuel: newNumero
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.olt.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditOlt();
        const enjeu = this.selectedEnjeu();
        if (enjeu) {
          this.patchPlanEnjeuxData(data => this.mapEnjeuInResponse(data, enjeu.id_enjeu, e => ({
            ...e,
            objectifs_long_terme: (e.objectifs_long_terme || []).map(o =>
              o.id_olt === olt.id_olt
                ? { ...o, libelle: newLibelle, description: newDescription, numero_manuel: newNumero }
                : o
            ),
          })));
        }
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  deleteOlt(olt: ObjectifLongTerme): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.olt.deleteTitle'),
        message: this.translate.instant('enjeux.olt.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteObjectifLongTerme(olt.id_olt).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.olt.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            const enjeu = this.selectedEnjeu();
            if (enjeu) {
              this.patchPlanEnjeuxData(data => this.mapEnjeuInResponse(data, enjeu.id_enjeu, e => ({
                ...e,
                objectifs_long_terme: (e.objectifs_long_terme || []).filter(o => o.id_olt !== olt.id_olt),
                nb_objectifs_long_terme: Math.max((e.nb_objectifs_long_terme || 1) - 1, 0),
              })));
            }
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Niveaux d'Exigence
  // ============================================

  startAddNe(oltId: number): void {
    this.addingNeForOlt.set(oltId);
    this.newNeLibelle = '';
    this.newNeDescription = '';
  }

  cancelAddNe(): void {
    this.addingNeForOlt.set(null);
    this.newNeLibelle = '';
    this.newNeDescription = '';
  }

  saveNe(olt: ObjectifLongTerme): void {
    if (!this.newNeLibelle.trim()) return;

    this.enjeuService.createNiveauExigence({
      id_olt: olt.id_olt,
      libelle: this.newNeLibelle.trim(),
      description: this.newNeDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.niveauExigence.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddNe();
        this.loadPlanData(true);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  startEditNe(ne: NiveauExigence): void {
    this.editingNeId.set(ne.id_ne);
    this.editNeLibelle = ne.libelle;
    this.editNeDescription = ne.description || '';
  }

  cancelEditNe(): void {
    this.editingNeId.set(null);
    this.editNeLibelle = '';
    this.editNeDescription = '';
  }

  saveEditNe(ne: NiveauExigence): void {
    if (!this.editNeLibelle.trim()) return;

    this.enjeuService.updateNiveauExigence(ne.id_ne, {
      libelle: this.editNeLibelle.trim(),
      description: this.editNeDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.niveauExigence.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditNe();
        this.loadPlanData(true);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  deleteNe(ne: NiveauExigence): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.niveauExigence.deleteTitle'),
        message: this.translate.instant('enjeux.niveauExigence.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteNiveauExigence(ne.id_ne).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.niveauExigence.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData(true);
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Indicateurs CRUD
  // ============================================

  toggleIndicateur(id: number): void {
    const expanded = new Set(this.expandedIndicateurIds());
    if (expanded.has(id)) {
      expanded.delete(id);
    } else {
      expanded.add(id);
    }
    this.expandedIndicateurIds.set(expanded);
  }

  isIndicateurExpanded(id: number): boolean {
    return this.expandedIndicateurIds().has(id);
  }

  startAddIndicateur(neId: number): void {
    this.addingIndicateurForNe.set(neId);
    this.newIndicateurNom = '';
    this.newIndicateurType = null;
    this.newIndicateurStandardise = false;
    this.newIndicateurDescription = '';
    this.indicateurFormMetriques = [];
    this.loadTypeMetriqueOptions();
  }

  cancelAddIndicateur(): void {
    this.addingIndicateurForNe.set(null);
    this.indicateurFormMetriques = [];
  }

  loadTypeMetriqueOptions(): void {
    if (this.typeMetriqueOptions().length > 0) return;
    this.adminService.getNomenclaturesByType('TYPE_METRIQUE').subscribe({
      next: (options) => this.typeMetriqueOptions.set(options),
      error: () => this.typeMetriqueOptions.set([])
    });
  }

  createEmptyMetrique(): MetriqueFormData {
    return {
      nom_metrique: '',
      type_metrique: null,
      unite: '',
      bloc_intitule: '',
      ponderation: null,
      etat_reference: '',
      scores: {
        1: { inf: null, sup: null, val: null, label: '' },
        2: { inf: null, sup: null, val: null, label: '' },
        3: { inf: null, sup: null, val: null, label: '' },
        4: { inf: null, sup: null, val: null, label: '' },
        5: { inf: null, sup: null, val: null, label: '' }
      },
      sens_variation: 'CROISSANT',
      score_1_sup_inclusive: true,
      score_2_sup_inclusive: true,
      score_3_sup_inclusive: true,
      score_4_sup_inclusive: true,
      has_score1_optional_bound: false,
      has_score5_optional_bound: false,
      _letter: 'A',
    };
  }

  /**
   * Convert a Metrique API object to a MetriqueFormData for editing.
   */
  /**
   * Clean a numeric value: strip trailing decimal zeros (40.0000 → 40, 20.50 → 20.5).
   */
  private cleanNum(val: number | null | undefined): number | null {
    if (val == null) return null;
    return parseFloat(Number(val).toPrecision(12));
  }

  /**
   * Convertit un index 0-based en lettre stable : 0→A, 1→B, …, 25→Z, 26→AA…
   * Utilisé pour étiqueter chaque bloc d'une métrique. La lettre reste
   * attachée au bloc à travers les drag-and-drop (réassignée seulement au
   * chargement, depuis l'ordre courant).
   */
  indexToBlockLetter(idx: number): string {
    let result = '';
    let n = idx;
    while (n >= 0) {
      result = String.fromCharCode(65 + (n % 26)) + result;
      n = Math.floor(n / 26) - 1;
    }
    return result;
  }

  /**
   * Libellé d'affichage d'un bloc : « intitulé (unité) » (ex: « hauteur (m) »),
   * ou juste « intitulé » si l'unité est vide. À défaut d'intitulé, retombe sur
   * « Bloc <lettre> » (compatibilité). `idx` = 0 → bloc principal (intitulé =
   * `bloc_intitule`, unité = `unite` de la métrique), idx ≥ 1 → bloc
   * complémentaire `score_blocks[idx-1]`.
   */
  metriqueBlockLabel(met: any, idx: number): string {
    let intitule: string | null | undefined;
    let unite: string | null | undefined;
    if (idx === 0) {
      intitule = met.bloc_intitule;
      unite = met.unite;
    } else {
      const block = (met.score_blocks || [])[idx - 1];
      intitule = block?.intitule;
      unite = block?.unite;
    }
    const label = (intitule ?? '').trim();
    if (label) {
      const u = (unite ?? '').trim();
      return u ? `${label} (${u})` : label;
    }
    // Fallback historique : « Bloc A », « Bloc B »…
    return this.translate.instant('enjeux.metriques.blockLabel') + ' ' + this.indexToBlockLetter(idx);
  }

  metriqueToFormData(met: Metrique): MetriqueFormData {
    const sensVariation = met.sens_variation || 'CROISSANT';

    const c = (v: number | null | undefined) => this.cleanNum(v);
    return {
      id_metrique: met.id_metrique,
      nom_metrique: met.nom_metrique,
      type_metrique: met.type_metrique || null,
      unite: met.unite || '',
      bloc_intitule: met.bloc_intitule || '',
      ponderation: met.ponderation ?? null,
      etat_reference: met.etat_reference || '',
      ordre: met.ordre ?? 0,
      scores: {
        1: { inf: c(met.score_1_inf), sup: c(met.score_1_sup), val: c(met.score_1_val), label: met.score_1_label || '' },
        2: { inf: c(met.score_2_inf), sup: c(met.score_2_sup), val: c(met.score_2_val), label: met.score_2_label || '' },
        3: { inf: c(met.score_3_inf), sup: c(met.score_3_sup), val: c(met.score_3_val), label: met.score_3_label || '' },
        4: { inf: c(met.score_4_inf), sup: c(met.score_4_sup), val: c(met.score_4_val), label: met.score_4_label || '' },
        5: { inf: c(met.score_5_inf), sup: c(met.score_5_sup), val: c(met.score_5_val), label: met.score_5_label || '' },
      },
      sens_variation: sensVariation,
      score_1_sup_inclusive: met.score_1_sup_inclusive ?? true,
      score_2_sup_inclusive: met.score_2_sup_inclusive ?? true,
      score_3_sup_inclusive: met.score_3_sup_inclusive ?? true,
      score_4_sup_inclusive: met.score_4_sup_inclusive ?? true,
      score_5_sup_inclusive: met.score_5_sup_inclusive ?? true,
      has_score1_optional_bound: met.has_borne_score1 ?? false,
      has_score5_optional_bound: met.has_borne_score5 ?? false,
      // Restituer les paliers marqués comme inactifs (bug feedback : la
      // sélection « non utilisé » n'était pas restaurée à la réouverture).
      _inactiveLevels: Array.isArray(met.inactive_levels) ? [...met.inactive_levels] : [],
      // Parenthésage du bloc principal (#247 — symétrie avec les complémentaires).
      group_open: met.group_open ?? 0,
      group_close: met.group_close ?? 0,
      // Lettre stable du principal (A) — réassignée à chaque chargement.
      _letter: this.indexToBlockLetter(0),
      // #247 — blocs de scoring complémentaires (recopie pour édition).
      // Le serializer remplace la liste complète côté serveur.
      score_blocks: (met.score_blocks || []).map((b, i) => ({
        id_score_block: b.id_score_block,
        position: b.position,
        intitule: b.intitule || '',
        unite: b.unite || '',
        logical_op: b.logical_op,
        group_open: b.group_open,
        group_close: b.group_close,
        sens_variation: b.sens_variation,
        score_1_inf: c(b.score_1_inf as any), score_1_sup: c(b.score_1_sup as any),
        score_2_inf: c(b.score_2_inf as any), score_2_sup: c(b.score_2_sup as any),
        score_3_inf: c(b.score_3_inf as any), score_3_sup: c(b.score_3_sup as any),
        score_4_inf: c(b.score_4_inf as any), score_4_sup: c(b.score_4_sup as any),
        score_5_inf: c(b.score_5_inf as any), score_5_sup: c(b.score_5_sup as any),
        score_1_sup_inclusive: b.score_1_sup_inclusive,
        score_2_sup_inclusive: b.score_2_sup_inclusive,
        score_3_sup_inclusive: b.score_3_sup_inclusive,
        score_4_sup_inclusive: b.score_4_sup_inclusive,
        score_5_sup_inclusive: b.score_5_sup_inclusive,
        has_borne_score1: b.has_borne_score1,
        has_borne_score5: b.has_borne_score5,
        inactive_levels: Array.isArray(b.inactive_levels) ? [...b.inactive_levels] : [],
        // Lettre stable : B, C, D, … (le principal = A).
        _letter: this.indexToBlockLetter(i + 1),
      })),
    };
  }

  addMetriqueToForm(): void {
    // #2 — Nouvelle métrique ouverte par défaut pour saisie immédiate
    this.indicateurFormMetriques = [
      ...this.indicateurFormMetriques,
      { ...this.createEmptyMetrique(), _expanded: true },
    ];
  }

  removeMetriqueFromForm(index: number): void {
    this.indicateurFormMetriques = this.indicateurFormMetriques.filter((_, i) => i !== index);
  }

  getMetriqueTypeMnemonique(typeMetriqueId: number | null | undefined): string {
    if (!typeMetriqueId) return 'NUMERIQUE';
    const opt = this.typeMetriqueOptions().find(o => o.id_nomenclature === typeMetriqueId);
    return opt?.mnemonique || 'NUMERIQUE';
  }

  /**
   * #400 — Résout le type d'une métrique pour construire le payload, de façon
   * robuste à une course de chargement. `getMetriqueTypeMnemonique` dépend des
   * options de nomenclature chargées en asynchrone : si l'utilisateur enregistre
   * avant la fin du chargement, le type retombait sur NUMERIQUE et les valeurs
   * CHIFFRE/TEXTE n'étaient pas envoyées (métrique enregistrée vide). En repli,
   * on infère le type à partir des données saisies (comme l'affichage).
   */
  private resolveFormMnemonique(met: MetriqueFormData): string {
    const byType = this.getMetriqueTypeMnemonique(met.type_metrique);
    // Options chargées + type sélectionné → la nomenclature fait foi.
    if (this.typeMetriqueOptions().length > 0 && met.type_metrique) {
      return byType;
    }
    // Repli : inférence à partir des champs renseignés.
    const levels = [1, 2, 3, 4, 5];
    const hasVal = levels.some(l => met.scores[l]?.val != null);
    const hasLabel = levels.some(l => (met.scores[l]?.label || '').trim());
    const hasBounds = levels.some(l => met.scores[l]?.inf != null || met.scores[l]?.sup != null);
    if (hasVal && !hasBounds) return 'CHIFFRE';
    if (hasLabel && !hasBounds) return 'TEXTE';
    return byType;
  }

  buildMetriquePayload(indicateurId: number, met: MetriqueFormData): MetriqueCreatePayload {
    const payload: MetriqueCreatePayload = {
      id_indicateur: indicateurId,
      nom_metrique: met.nom_metrique.trim(),
    };
    if (met.type_metrique) payload.type_metrique = met.type_metrique;
    // Unité optionnelle au niveau métrique : envoyer null explicite si vidée pour effacer en base.
    payload.unite = met.unite.trim() || null;
    // Intitulé du bloc principal (pertinent en multi-blocs ; inoffensif sinon).
    payload.bloc_intitule = met.bloc_intitule?.trim() || null;
    if (met.ponderation != null) payload.ponderation = met.ponderation;
    if (met.etat_reference.trim()) payload.etat_reference = met.etat_reference.trim();
    if (met.ordre != null) payload.ordre = met.ordre;

    const mnemonique = this.resolveFormMnemonique(met);
    for (let level = 1; level <= 5; level++) {
      const s = met.scores[level];
      if (mnemonique === 'CHIFFRE') {
        if (s?.val != null) (payload as any)[`score_${level}_val`] = s.val;
      } else if (mnemonique === 'TEXTE') {
        if (s?.label?.trim()) (payload as any)[`score_${level}_label`] = s.label.trim();
      } else {
        // NUMERIQUE: niveau « non utilisé » → bornes effacées (null explicite)
        // pour ne pas laisser de données fantômes (tableau + scoring auto).
        if ((met._inactiveLevels || []).includes(level)) {
          (payload as any)[`score_${level}_inf`] = null;
          (payload as any)[`score_${level}_sup`] = null;
          continue;
        }
        // NUMERIQUE: handle optional extreme bounds
        const isOptionalInf = this.isOptionalBound(met, level, 'inf');
        const isOptionalSup = this.isOptionalBound(met, level, 'sup');

        if (isOptionalInf) {
          const hasOptional = level === 1 ? met.has_score1_optional_bound : met.has_score5_optional_bound;
          // Envoyer explicitement null si checkbox décochée (pour effacer en base)
          (payload as any)[`score_${level}_inf`] = (hasOptional && s?.inf != null) ? s.inf : null;
        } else {
          if (s?.inf != null) (payload as any)[`score_${level}_inf`] = s.inf;
        }

        if (isOptionalSup) {
          const hasOptional = level === 5 ? met.has_score5_optional_bound : met.has_score1_optional_bound;
          (payload as any)[`score_${level}_sup`] = (hasOptional && s?.sup != null) ? s.sup : null;
        } else {
          if (s?.sup != null) (payload as any)[`score_${level}_sup`] = s.sup;
        }
      }
    }

    // #359 — niveaux désactivés (« non utilisé ») pour les grilles simples Chiffre / Texte.
    if (mnemonique === 'CHIFFRE' || mnemonique === 'TEXTE') {
      payload.inactive_levels = Array.isArray(met._inactiveLevels) ? [...met._inactiveLevels] : [];
    }

    // Direction, inclusivité et bornes extrêmes (NUMERIQUE only)
    if (mnemonique === 'NUMERIQUE') {
      payload.sens_variation = met.sens_variation;
      payload.score_1_sup_inclusive = met.score_1_sup_inclusive;
      payload.score_2_sup_inclusive = met.score_2_sup_inclusive;
      payload.score_3_sup_inclusive = met.score_3_sup_inclusive;
      payload.score_4_sup_inclusive = met.score_4_sup_inclusive;
      payload.score_5_sup_inclusive = met.score_5_sup_inclusive;
      payload.has_borne_score1 = met.has_score1_optional_bound;
      payload.has_borne_score5 = met.has_score5_optional_bound;
      // Persistance des paliers désactivés (sinon l'état est perdu au rechargement).
      payload.inactive_levels = Array.isArray(met._inactiveLevels) ? [...met._inactiveLevels] : [];
      // Parenthésage du bloc principal
      payload.group_open = met.group_open ?? 0;
      payload.group_close = met.group_close ?? 0;

      // #247 — blocs de scoring complémentaires. Envoyés intégralement à
      // chaque sauvegarde : le serializer remplace l'ensemble (delete + recréation).
      if (met.score_blocks !== undefined) {
        payload.score_blocks = (met.score_blocks || []).map(b => {
          const inactive = Array.isArray(b.inactive_levels) ? [...b.inactive_levels] : [];
          const block: any = {
            position: b.position,
            intitule: b.intitule?.trim() || null,
            unite: b.unite?.trim() || null,
            logical_op: b.logical_op,
            group_open: b.group_open,
            group_close: b.group_close,
            sens_variation: b.sens_variation,
            score_1_inf: b.score_1_inf, score_1_sup: b.score_1_sup,
            score_2_inf: b.score_2_inf, score_2_sup: b.score_2_sup,
            score_3_inf: b.score_3_inf, score_3_sup: b.score_3_sup,
            score_4_inf: b.score_4_inf, score_4_sup: b.score_4_sup,
            score_5_inf: b.score_5_inf, score_5_sup: b.score_5_sup,
            score_1_sup_inclusive: b.score_1_sup_inclusive,
            score_2_sup_inclusive: b.score_2_sup_inclusive,
            score_3_sup_inclusive: b.score_3_sup_inclusive,
            score_4_sup_inclusive: b.score_4_sup_inclusive,
            score_5_sup_inclusive: b.score_5_sup_inclusive,
            has_borne_score1: b.has_borne_score1,
            has_borne_score5: b.has_borne_score5,
            inactive_levels: inactive,
          };
          // Niveau « non utilisé » → bornes effacées (cohérent avec le principal).
          for (const lvl of inactive) {
            block[`score_${lvl}_inf`] = null;
            block[`score_${lvl}_sup`] = null;
          }
          return block;
        });
      }
    }

    // #575 — la base stocke au plus 4 décimales : normaliser les bornes
    // numériques (principal + blocs) à 4 décimales avant l'envoi, pour qu'une
    // saisie plus précise (ou un artefact flottant) ne soit pas rejetée par le
    // backend (« pas plus de 4 chiffres après la virgule »).
    const round4 = (v: any) => {
      if (v == null || v === '') return v;
      const n = Number(v);
      return Number.isFinite(n) ? parseFloat(n.toFixed(4)) : v;
    };
    const isSeuilKey = (k: string) => /^score_\d_(inf|sup|val)$/.test(k);
    for (const k of Object.keys(payload)) {
      if (isSeuilKey(k)) (payload as any)[k] = round4((payload as any)[k]);
    }
    if (Array.isArray(payload.score_blocks)) {
      for (const b of payload.score_blocks) {
        for (const k of Object.keys(b)) {
          if (isSeuilKey(k)) (b as any)[k] = round4((b as any)[k]);
        }
      }
    }

    return payload;
  }

  /**
   * Determine if a bound field is the optional extreme bound for a given level/direction.
   * Returns true if this is the outer bound that can be toggled off via checkbox.
   */
  isOptionalBound(met: MetriqueFormData, level: number, field: 'inf' | 'sup'): boolean {
    if (met.sens_variation === 'CROISSANT') {
      return (level === 1 && field === 'inf') || (level === 5 && field === 'sup');
    } else {
      return (level === 1 && field === 'sup') || (level === 5 && field === 'inf');
    }
  }

  /**
   * Auto-fill adjacent boundary when a boundary value changes.
   * Ascending: changing SUP of level N → auto-fills INF of level N+1
   * Descending: changing INF of level N → auto-fills SUP of level N+1
   */
  onScoreBoundaryChange(met: MetriqueFormData, level: number, field: 'inf' | 'sup'): void {
    if (met.sens_variation === 'CROISSANT' && field === 'sup' && level < 5) {
      met.scores[level + 1].inf = met.scores[level].sup;
    } else if (met.sens_variation === 'DECROISSANT' && field === 'inf' && level < 5) {
      met.scores[level + 1].sup = met.scores[level].inf;
    }
  }

  /**
   * Check if a score field should be disabled (auto-filled or optional unchecked).
   */
  isScoreFieldDisabled(met: MetriqueFormData, level: number, field: 'inf' | 'sup'): boolean {
    // Optional extreme bound: disabled if checkbox unchecked
    if (this.isOptionalBound(met, level, field)) {
      return level === 1 ? !met.has_score1_optional_bound : !met.has_score5_optional_bound;
    }
    // Auto-filled fields: INF of levels 2-5 (ascending) or SUP of levels 2-5 (descending)
    if (met.sens_variation === 'CROISSANT' && field === 'inf' && level > 1) return true;
    if (met.sens_variation === 'DECROISSANT' && field === 'sup' && level > 1) return true;
    return false;
  }

  /**
   * Handle direction change: reset auto-filled values and recalculate optional bounds.
   */
  onDirectionChange(met: MetriqueFormData): void {
    // Mirror score values: swap 1↔5, 2↔4, 3 stays
    const swap = (a: number, b: number) => {
      const tmp = { ...met.scores[a] };
      met.scores[a] = { ...met.scores[b] };
      met.scores[b] = tmp;
    };
    swap(1, 5);
    swap(2, 4);

    // Swap inclusivity toggles (boundary 1-2 ↔ 4-5, boundary 2-3 ↔ 3-4)
    const tmpIncl1 = met.score_1_sup_inclusive;
    met.score_1_sup_inclusive = met.score_4_sup_inclusive;
    met.score_4_sup_inclusive = tmpIncl1;
    const tmpIncl2 = met.score_2_sup_inclusive;
    met.score_2_sup_inclusive = met.score_3_sup_inclusive;
    met.score_3_sup_inclusive = tmpIncl2;

    // Swap optional bound checkboxes
    const tmpOpt = met.has_score1_optional_bound;
    met.has_score1_optional_bound = met.has_score5_optional_bound;
    met.has_score5_optional_bound = tmpOpt;
  }

  /**
   * Toggle inclusivity for a boundary between level N and N+1.
   */
  toggleBoundaryInclusive(met: MetriqueFormData, boundaryLevel: number): void {
    const key = `score_${boundaryLevel}_sup_inclusive` as keyof MetriqueFormData;
    (met as any)[key] = !(met as any)[key];
  }

  /**
   * Handle optional bound checkbox change: clear value when unchecked.
   */
  onOptionalBoundToggle(met: MetriqueFormData, scoreLevel: 1 | 5): void {
    const hasOptional = scoreLevel === 1 ? met.has_score1_optional_bound : met.has_score5_optional_bound;
    if (!hasOptional) {
      // Clear the optional field value
      if (met.sens_variation === 'CROISSANT') {
        if (scoreLevel === 1) met.scores[1].inf = null;
        else met.scores[5].sup = null;
      } else {
        if (scoreLevel === 1) met.scores[1].sup = null;
        else met.scores[5].inf = null;
      }
    }
  }

  /**
   * Check if a boundary's upper bound is inclusive (for template use).
   */
  isSupInclusive(met: MetriqueFormData, level: number): boolean {
    return (met as any)[`score_${level}_sup_inclusive`] ?? true;
  }

  /**
   * Get the label for the optional extreme bound checkbox.
   */
  getOptionalBoundLabel(met: MetriqueFormData, level: number): string {
    if (met.sens_variation === 'CROISSANT') {
      return level === 1
        ? this.translate.instant('enjeux.metriques.borneMin')
        : this.translate.instant('enjeux.metriques.borneMax');
    } else {
      return level === 1
        ? this.translate.instant('enjeux.metriques.borneMax')
        : this.translate.instant('enjeux.metriques.borneMin');
    }
  }

  /**
   * Vérifie que les niveaux ACTIFS (non grisés) d'une métrique « Chiffre » ou
   * « Texte » ont bien une valeur saisie. Retourne un message d'erreur (avec le
   * nom de la métrique) si un niveau actif est vide, sinon null.
   *
   * Pour les autres types (NUMERIQUE, INDETERMINE), aucune contrainte ici.
   */
  private metriqueActiveLevelsError(met: MetriqueFormData): string | null {
    const mnemo = this.getMetriqueTypeMnemonique(met.type_metrique);
    if (mnemo !== 'CHIFFRE' && mnemo !== 'TEXTE') return null;
    const inactive = met._inactiveLevels || [];
    for (let lvl = 1; lvl <= 5; lvl++) {
      if (inactive.includes(lvl)) continue;
      const s = met.scores?.[lvl];
      const empty = mnemo === 'CHIFFRE' ? (s?.val == null) : !(s?.label?.trim());
      if (empty) {
        const name = met.nom_metrique?.trim() || this.translate.instant('enjeux.metriques.unnamed');
        return this.translate.instant('enjeux.metriques.activeLevelRequired', { name });
      }
    }
    return null;
  }

  /**
   * Valide une liste de métriques avant sauvegarde : si un niveau actif est vide
   * (Chiffre / Texte), affiche un snackbar et retourne false (sauvegarde bloquée).
   * Les métriques marquées supprimées sont ignorées.
   */
  private validateMetriquesActiveLevels(metriques: MetriqueFormData[]): boolean {
    for (const met of metriques) {
      if (met._deleted) continue;
      const err = this.metriqueActiveLevelsError(met);
      if (err) {
        this.snackBar.open(err, this.translate.instant('common.actions.close'), { duration: 4000 });
        return false;
      }
    }
    return true;
  }

  saveIndicateur(ne: any): void {
    if (!this.newIndicateurNom.trim()) return;

    // Filter metriques that have a name (#339 : les métriques de type
    // « Indéterminé » sont conservées même sans intitulé).
    const validMetriques = this.indicateurFormMetriques.filter(m =>
      m.nom_metrique.trim() || this.getMetriqueTypeMnemonique(m.type_metrique) === 'INDETERMINE'
    );
    // Niveaux actifs (Chiffre / Texte) : saisie obligatoire.
    if (!this.validateMetriquesActiveLevels(validMetriques)) return;

    this.isSavingIndicateur.set(true);

    const payload: any = {
      id_ne: ne.id_ne,
      nom_indicateur: this.newIndicateurNom.trim(),
      est_standardise: this.newIndicateurStandardise,
    };
    if (this.newIndicateurType) payload.type_indicateur = this.newIndicateurType;
    if (this.newIndicateurDescription.trim()) payload.description = this.newIndicateurDescription.trim();

    this.enjeuService.createIndicateur(payload).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (createdIndicateur: any) => {
        const indicateurId = createdIndicateur.id_indicateur;

        if (validMetriques.length === 0) {
          // No metriques to create
          this.snackBar.open(
            this.translate.instant('enjeux.indicateurs.createSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.addingIndicateurForNe.set(null);
          this.indicateurFormMetriques = [];
          this.isSavingIndicateur.set(false);
          this.loadPlanData(true);
          return;
        }

        // Create all metriques in parallel
        const metriqueRequests = validMetriques.map(met =>
          this.enjeuService.createMetrique(this.buildMetriquePayload(indicateurId, met))
        );

        forkJoin(metriqueRequests).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.indicateurs.createSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.addingIndicateurForNe.set(null);
            this.indicateurFormMetriques = [];
            this.isSavingIndicateur.set(false);
            this.loadPlanData(true);
          },
          error: () => {
            // Partial success: indicateur created but some metriques failed
            this.snackBar.open(
              this.translate.instant('enjeux.metriques.partialError'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
            this.addingIndicateurForNe.set(null);
            this.indicateurFormMetriques = [];
            this.isSavingIndicateur.set(false);
            this.loadPlanData(true);
          }
        });
      },
      error: () => {
        this.isSavingIndicateur.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.createError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  // --- Standalone metrique add ---
  startAddStandaloneMetrique(indicateurId: number): void {
    this.addingMetriqueForIndicateur.set(indicateurId);
    this.standaloneMetriqueForm = this.createEmptyMetrique();
    this.loadTypeMetriqueOptions();
  }

  cancelAddStandaloneMetrique(): void {
    this.addingMetriqueForIndicateur.set(null);
    this.standaloneMetriqueForm = null;
  }

  saveStandaloneMetrique(indicateurId: number): void {
    // #339 : l'intitulé n'est requis que si le type n'est pas « Indéterminé ».
    if (!this.standaloneMetriqueForm) return;
    // #401 — le type de métrique est obligatoire.
    if (this.standaloneMetriqueForm.type_metrique == null) {
      this.snackBar.open(
        this.translate.instant('enjeux.metriques.typeRequired'),
        this.translate.instant('common.actions.close'),
        { duration: 3000 }
      );
      return;
    }
    const isIndetermine = this.getMetriqueTypeMnemonique(this.standaloneMetriqueForm.type_metrique) === 'INDETERMINE';
    if (!isIndetermine && !this.standaloneMetriqueForm.nom_metrique.trim()) return;
    if (!this.validateMetriquesActiveLevels([this.standaloneMetriqueForm])) return;
    this.isSavingStandaloneMetrique.set(true);
    const payload = this.buildMetriquePayload(indicateurId, this.standaloneMetriqueForm);
    this.enjeuService.createMetrique(payload).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.metriques.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.addingMetriqueForIndicateur.set(null);
        this.standaloneMetriqueForm = null;
        this.isSavingStandaloneMetrique.set(false);
        this.loadPlanData(true);
      },
      error: () => {
        this.isSavingStandaloneMetrique.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.createError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  startEditIndicateur(ind: any, expandMetriqueId?: number): void {
    this.editingIndicateurId.set(ind.id_indicateur);
    this.editIndicateurNom = ind.nom_indicateur;
    this.editIndicateurType = ind.type_indicateur || null;
    this.editIndicateurStandardise = ind.est_standardise;
    this.editIndicateurDescription = ind.description || '';
    this.loadTypeMetriqueOptions();

    // Load existing metriques into edit form
    this.editIndicateurMetriques = (ind.metriques || []).map((met: Metrique) =>
      this.metriqueToFormData(met)
    );

    // #411 — édition d'une métrique précise : la déplier directement
    if (expandMetriqueId != null) {
      const target = this.editIndicateurMetriques.find(
        (m) => m.id_metrique === expandMetriqueId
      );
      if (target) target._expanded = true;
    }
  }

  cancelEditIndicateur(): void {
    this.editingIndicateurId.set(null);
    this.editIndicateurMetriques = [];
  }

  addMetriqueToEdit(): void {
    // Nouvelle métrique → dépliée pour saisie immédiate (#2)
    this.editIndicateurMetriques = [
      ...this.editIndicateurMetriques,
      { ...this.createEmptyMetrique(), _expanded: true },
    ];
  }

  /** #2 — Bascule l'affichage d'une métrique entre vue compacte et dépliée. */
  toggleMetriqueExpanded(metrics: MetriqueFormData[], idx: number): void {
    if (!metrics[idx]) return;
    metrics[idx]._expanded = !metrics[idx]._expanded;
  }

  /**
   * #2 — Déplace une métrique vers le haut / le bas dans la liste.
   * `dir = -1` pour monter, `dir = +1` pour descendre.
   */
  moveMetrique(metrics: MetriqueFormData[], idx: number, dir: -1 | 1): void {
    const newIdx = idx + dir;
    if (newIdx < 0 || newIdx >= metrics.length) return;
    const [m] = metrics.splice(idx, 1);
    metrics.splice(newIdx, 0, m);
    this.renumberMetriquesOrdre(metrics);
  }

  /** #4 — Drag-and-drop pour réordonner les métriques d'un indicateur. */
  onMetriquesDrop(metrics: MetriqueFormData[], event: CdkDragDrop<MetriqueFormData[]>): void {
    moveItemInArray(metrics, event.previousIndex, event.currentIndex);
    this.renumberMetriquesOrdre(metrics);
  }

  /** Réassigne le champ `ordre` (0..N) selon la position courante. */
  private renumberMetriquesOrdre(metrics: MetriqueFormData[]): void {
    metrics.forEach((m, i) => { m.ordre = i; });
  }

  // ===========================================================================
  // #249 / #261 — Drag-and-drop pour réordonner les entités d'un plan
  // (enjeux/FCR, facteurs, pressions, OLT, NE, indicateurs NE, OO, RA,
  // indicateurs RA). Pattern : optimistic update + rollback via reload serveur.
  // ===========================================================================

  /**
   * Helper générique de réordonnancement avec optimistic update + rollback.
   * Mute la liste en place (moveItemInArray + champ `ordre`) puis envoie la
   * requête au backend. En cas d'échec, recharge les données du plan.
   */
  private applyReorder(
    entity: ReorderEntity,
    parentId: number,
    list: Array<Record<string, any>>,
    fromIndex: number,
    toIndex: number,
    idKey: string,
    extra?: { parent_type: 'ne' | 'ra' | 'indicateur' },
  ): void {
    if (fromIndex === toIndex) return;
    moveItemInArray(list, fromIndex, toIndex);
    list.forEach((item, i) => { item['ordre'] = i; });
    const ordered_ids = list
      .map(item => item[idKey] as number)
      .filter(id => id != null);
    // #228 (2026-05-12) — Les OO (M2M Pressions) et Operations (M2M
    // Métriques) peuvent exister en plusieurs copies JS dans le payload
    // by-plan (chaque pression/métrique a sa propre instance JSON).
    // moveItemInArray ne mute que les références présentes dans `list` ;
    // les copies dans d'autres branches gardent leur ancien `ordre` et
    // le dédoublonnage côté UI peut alors retenir une copie obsolète.
    // On propage les nouveaux ordres à TOUTES les copies de l'arbre.
    this.propagateOrdresToDuplicates(entity, idKey, ordered_ids);
    const payload = extra
      ? { parent_id: parentId, ordered_ids, ...extra }
      : { parent_id: parentId, ordered_ids };
    this.reorderService.reorder(entity, payload).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.dnd.reorderSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 2000 },
        );
        // #228 — Au lieu de recharger tout l'arbre via by-plan/, on :
        // 1) force le re-render des computed (l'ordre local est déjà à jour
        //    via moveItemInArray sur la liste passée en référence)
        // 2) ne re-fetch que les codes calculés des actions (endpoint léger).
        this.refreshUiAndCodes();
      },
      error: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.dnd.reorderError'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 },
        );
        // Rollback : recharge depuis le serveur pour restaurer l'ordre.
        this.loadPlanData(true);
      },
    });
  }

  /**
   * Walk l'arbre `planEnjeuxData` et met à jour `item.ordre` sur TOUTES les
   * copies JS partagées par M2M (OO ↔ Pressions, Operation ↔ Métriques)
   * dont l'`id` est dans `ordered_ids`. Indispensable pour que le tri par
   * ordre dans les computed reflète le DnD (#228).
   */
  private propagateOrdresToDuplicates(
    entity: ReorderEntity,
    idKey: string,
    ordered_ids: number[],
  ): void {
    const rankById = new Map<number, number>();
    ordered_ids.forEach((id, idx) => rankById.set(id, idx));
    const data = this.planEnjeuxData();
    if (!data) return;

    const updateIfMatch = (obj: any) => {
      const id = obj?.[idKey];
      if (id != null && rankById.has(id)) {
        obj.ordre = rankById.get(id);
      }
    };

    const allEnjeux = [...(data.enjeux || []), ...(data.fcr || [])];

    if (entity === 'objectifs-operationnels') {
      for (const enjeu of allEnjeux) {
        for (const fi of (enjeu.facteurs_influence || [])) {
          for (const pression of (fi.pressions || [])) {
            for (const oo of ((pression as any).objectifs_operationnels || [])) {
              updateIfMatch(oo);
            }
          }
        }
      }
    } else if (entity === 'operations') {
      for (const enjeu of allEnjeux) {
        for (const olt of (enjeu.objectifs_long_terme || [])) {
          for (const ne of (olt.niveaux_exigence || [])) {
            for (const ind of (ne.indicateurs || [])) {
              for (const met of (ind.metriques || [])) {
                for (const op of ((met as any).operations || [])) updateIfMatch(op);
              }
            }
          }
        }
        for (const fi of (enjeu.facteurs_influence || [])) {
          for (const pression of (fi.pressions || [])) {
            for (const oo of ((pression as any).objectifs_operationnels || [])) {
              for (const ra of (oo.resultats_attendus || [])) {
                for (const ind of (ra.indicateurs || [])) {
                  for (const met of (ind.metriques || [])) {
                    for (const op of ((met as any).operations || [])) updateIfMatch(op);
                  }
                }
              }
            }
          }
        }
      }
    }
    // Les autres entités (Enjeu, Facteur, Pression, OLT, NE, RA,
    // Indicateur) n'ont pas de duplicats : leurs FK sont 1:N, donc
    // la mutation faite dans applyReorder suffit.
  }

  /**
   * Force un re-render des computed liés à planEnjeuxData (les mutations
   * sur les sous-listes ne notifient pas le signal d'elles-mêmes), puis
   * fetch les codes d'actions à jour et les patche en place. Beaucoup plus
   * léger qu'un `loadPlanData(true)` complet (#228, retour utilisateur du
   * 2026-05-12 : « l'actualisation des numéros prend un peu de temps »).
   */
  private refreshUiAndCodes(): void {
    // 1) Trigger le re-render en remplaçant l'objet racine (clé `_uiRev`
    //    suffit : Angular signals comparent par référence).
    this.planEnjeuxData.update(d => d ? { ...d } : d);

    // 2) Synchroniser le signal partagé du service pour que la sidebar
    //    (et tout autre consommateur de `currentPlanEnjeux`) reflète
    //    les nouveaux ordres (retour utilisateur 2026-05-12).
    const fresh = this.planEnjeuxData();
    if (fresh) this.enjeuService.updatePlanEnjeuxCache(fresh);

    // 3) Fetch les codes calculés et les patche dans chaque opération.
    const planId = this.planId();
    if (!planId) return;
    this.reorderService.getOperationCodes(planId).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (codes) => this.applyCodesInPlace(codes),
      error: () => { /* silencieux : les codes seront re-calculés au prochain reload */ },
    });
  }

  /**
   * Walk l'arbre `planEnjeuxData` et met à jour `op.code_affichage` à partir
   * du dict {id_operation: code} reçu du backend.
   */
  private applyCodesInPlace(codes: Record<number, string>): void {
    const data = this.planEnjeuxData();
    if (!data) return;
    const patchOp = (op: any) => {
      const code = codes[op.id_operation];
      if (code !== undefined) op.code_affichage = code;
    };
    const walkIndicateur = (ind: any) => {
      for (const met of (ind.metriques || [])) {
        for (const op of (met.operations || [])) patchOp(op);
      }
    };
    const walkEnjeu = (enjeu: any) => {
      for (const olt of (enjeu.objectifs_long_terme || [])) {
        for (const ne of (olt.niveaux_exigence || [])) {
          for (const ind of (ne.indicateurs || [])) walkIndicateur(ind);
        }
      }
      for (const fi of (enjeu.facteurs_influence || [])) {
        for (const pression of (fi.pressions || [])) {
          for (const oo of (pression.objectifs_operationnels || [])) {
            for (const ra of (oo.resultats_attendus || [])) {
              for (const ind of (ra.indicateurs || [])) walkIndicateur(ind);
            }
          }
        }
      }
    };
    for (const enjeu of (data.enjeux || [])) walkEnjeu(enjeu);
    for (const fcr of (data.fcr || [])) walkEnjeu(fcr);
    // Forcer le re-render après mutation in-place.
    this.planEnjeuxData.update(d => d ? { ...d } : d);
    // Synchroniser aussi le signal partagé du service (sidebar).
    const fresh = this.planEnjeuxData();
    if (fresh) this.enjeuService.updatePlanEnjeuxCache(fresh);
  }

  /** Drag-and-drop : réordonne les enjeux du plan. */
  onEnjeuDrop(event: CdkDragDrop<any[]>): void {
    const planId = this.planId();
    if (!planId) return;
    const list = [...this.enjeux()];
    this.applyReorder('enjeux', planId, list, event.previousIndex, event.currentIndex, 'id_enjeu');
  }

  /** Drag-and-drop : réordonne les FCR du plan (même endpoint que les enjeux). */
  onFcrDrop(event: CdkDragDrop<any[]>): void {
    const planId = this.planId();
    if (!planId) return;
    const list = [...this.fcr()];
    this.applyReorder('enjeux', planId, list, event.previousIndex, event.currentIndex, 'id_enjeu');
  }

  /** Drag-and-drop : réordonne les facteurs d'influence d'un enjeu. */
  onFacteurDrop(event: CdkDragDrop<any[]>): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu?.id_enjeu) return;
    const list = enjeu.facteurs_influence || [];
    this.applyReorder('facteurs-influence', enjeu.id_enjeu, list, event.previousIndex, event.currentIndex, 'id_facteur_influence');
  }

  /**
   * Drag-and-drop : réordonne ou déplace une pression (#472).
   * - Intra-facteur (`previousContainer === container`) : réordonnancement.
   * - Inter-facteur (`previousContainer !== container`) : déplacement vers un
   *   autre facteur d'influence via l'endpoint `move`.
   */
  onPressionDrop(event: CdkDragDrop<any[]>, facteur: FacteurInfluence): void {
    if (!facteur?.id_facteur_influence) return;
    if (event.previousContainer === event.container) {
      const list = facteur.pressions || [];
      this.applyReorder('pressions', facteur.id_facteur_influence, list, event.previousIndex, event.currentIndex, 'id_pression');
    } else {
      this.applyMovePression(event, facteur.id_facteur_influence);
    }
  }

  /**
   * Liste des IDs des droplists de pressions des autres facteurs d'influence
   * de l'enjeu courant — utilisé par `cdkDropListConnectedTo` pour activer le
   * DnD inter-facteur (#472).
   */
  connectedPressionDroplistIds(currentFacteurId: number): string[] {
    return this.selectedFacteurs()
      .filter(f => f.id_facteur_influence !== currentFacteurId)
      .map(f => `pressions-droplist-${f.id_facteur_influence}`);
  }

  /**
   * Déplacement d'une pression vers un autre facteur d'influence via
   * l'endpoint `move` (#472). Transfert optimiste côté UI + appel API ;
   * rollback (reload) si erreur.
   */
  private applyMovePression(event: CdkDragDrop<any[]>, newFacteurId: number): void {
    const pression = event.previousContainer.data[event.previousIndex];
    const pressionId = pression?.id_pression;
    if (!pressionId) return;

    // Optimistic transfer
    transferArrayItem(
      event.previousContainer.data,
      event.container.data,
      event.previousIndex,
      event.currentIndex,
    );
    event.container.data.forEach((item: Record<string, any>, i: number) => {
      item['ordre'] = i;
    });

    this.reorderService.movePression(pressionId, {
      new_facteur_id: newFacteurId,
      position: event.currentIndex,
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.dnd.moveSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 2000 },
        );
      },
      error: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.dnd.moveError'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 },
        );
        // Rollback : recharge depuis le serveur.
        this.loadPlanData(true);
      },
    });
  }

  /** Drag-and-drop : réordonne les OLT d'un enjeu. */
  onOltDrop(event: CdkDragDrop<any[]>): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu?.id_enjeu) return;
    const list = enjeu.objectifs_long_terme || [];
    this.applyReorder('objectifs-long-terme', enjeu.id_enjeu, list, event.previousIndex, event.currentIndex, 'id_olt');
  }

  /** Drag-and-drop : réordonne les NE d'un OLT. */
  onNeDrop(event: CdkDragDrop<any[]>, olt: ObjectifLongTerme): void {
    if (!olt?.id_olt) return;
    const list = olt.niveaux_exigence || [];
    this.applyReorder('niveaux-exigence', olt.id_olt, list, event.previousIndex, event.currentIndex, 'id_ne');
  }

  /**
   * Drag-and-drop : réordonne ou déplace un indicateur (NE).
   * - Intra-NE (`previousContainer === container`) : réordonnancement via reorder.
   * - Inter-NE (`previousContainer !== container`) : déplacement via move (#261).
   */
  onIndicateurNeDrop(event: CdkDragDrop<any[]>, ne: NiveauExigence): void {
    if (!ne?.id_ne) return;
    if (event.previousContainer === event.container) {
      const list = ne.indicateurs || [];
      this.applyReorder('indicateurs', ne.id_ne, list, event.previousIndex, event.currentIndex, 'id_indicateur', { parent_type: 'ne' });
    } else {
      this.applyMoveIndicateur(event, 'ne', ne.id_ne);
    }
  }

  /** Drag-and-drop : réordonne les OO d'un enjeu. */
  onOoDrop(event: CdkDragDrop<any[]>): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu?.id_enjeu) return;
    const list = [...this.selectedOos()];
    this.applyReorder('objectifs-operationnels', enjeu.id_enjeu, list, event.previousIndex, event.currentIndex, 'id_oo');
  }

  /** Drag-and-drop : réordonne les RA d'un OO. */
  onRaDrop(event: CdkDragDrop<any[]>, oo: ObjectifOperationnel): void {
    if (!oo?.id_oo) return;
    const list = oo.resultats_attendus || [];
    this.applyReorder('resultats-attendus', oo.id_oo, list, event.previousIndex, event.currentIndex, 'id_ra');
  }

  /**
   * #236 — Extrait les libellés uniques des facteurs d'influence rattachés
   * aux pressions d'un OO. Préserve l'ordre d'apparition (premier rencontré
   * = premier affiché).
   */
  uniqueFacteursFromOO(oo: ObjectifOperationnel): string[] {
    const seen = new Set<string>();
    const out: string[] = [];
    for (const p of (oo.pressions || [])) {
      const lib = (p as any).facteur_influence_libelle;
      if (lib && !seen.has(lib)) {
        seen.add(lib);
        out.push(lib);
      }
    }
    return out;
  }

  /**
   * Drag-and-drop : réordonne les actions/opérations affichées sous un
   * indicateur (#544). Depuis #367 les actions sont listées une seule fois au
   * niveau de l'indicateur (`ind.operations`), qu'elles soient rattachées
   * directement ou via une métrique — l'ordre porte donc sur l'indicateur.
   * Le code calculé (CS1, IP2, ...) se met à jour automatiquement après la
   * recharge — le rang est plan-wide, donc déplacer une action peut
   * renuméroter les autres du même préfixe.
   */
  onOperationDrop(event: CdkDragDrop<any[]>, ind: { id_indicateur?: number; operations?: any[] }): void {
    if (!ind?.id_indicateur) return;
    const list = ind.operations || [];
    this.applyReorder(
      'operations', ind.id_indicateur, list,
      event.previousIndex, event.currentIndex, 'id_operation',
      { parent_type: 'indicateur' },
    );
  }

  /**
   * Drag-and-drop : réordonne ou déplace un indicateur (RA).
   * - Intra-RA : reorder. Inter-RA : move (#261).
   */
  onIndicateurRaDrop(event: CdkDragDrop<any[]>, ra: ResultatAttendu): void {
    if (!ra?.id_ra) return;
    if (event.previousContainer === event.container) {
      const list = ra.indicateurs || [];
      this.applyReorder('indicateurs', ra.id_ra, list, event.previousIndex, event.currentIndex, 'id_indicateur', { parent_type: 'ra' });
    } else {
      this.applyMoveIndicateur(event, 'ra', ra.id_ra);
    }
  }

  /**
   * Liste des IDs des droplists d'indicateurs des autres NE de l'enjeu courant
   * — utilisé par `cdkDropListConnectedTo` pour activer le DnD inter-NE (#261).
   */
  connectedIndicateurNeDroplistIds(currentNeId: number): string[] {
    const enjeu = this.selectedEnjeu();
    if (!enjeu?.objectifs_long_terme) return [];
    const ids: string[] = [];
    for (const olt of enjeu.objectifs_long_terme) {
      for (const ne of (olt.niveaux_exigence || [])) {
        if (ne.id_ne !== currentNeId) {
          ids.push(`indicateurs-droplist-ne-${ne.id_ne}`);
        }
      }
    }
    return ids;
  }

  /**
   * Liste des IDs des droplists d'indicateurs des autres RA de l'enjeu courant
   * — utilisé par `cdkDropListConnectedTo` pour activer le DnD inter-RA (#261).
   */
  connectedIndicateurRaDroplistIds(currentRaId: number): string[] {
    const ids: string[] = [];
    const oos = this.selectedOos() || [];
    for (const oo of oos) {
      for (const ra of (oo.resultats_attendus || [])) {
        if (ra.id_ra !== currentRaId) {
          ids.push(`indicateurs-droplist-ra-${ra.id_ra}`);
        }
      }
    }
    return ids;
  }

  /**
   * Déplacement d'un indicateur entre NE / RA via l'endpoint `move` (#261).
   * Optimistic transfer côté UI + appel API ; rollback si erreur.
   */
  private applyMoveIndicateur(
    event: CdkDragDrop<any[]>,
    newParentType: 'ne' | 'ra',
    newParentId: number,
  ): void {
    const indicateur = event.previousContainer.data[event.previousIndex];
    const indicateurId = indicateur?.id_indicateur;
    if (!indicateurId) return;

    // Optimistic transfer
    transferArrayItem(
      event.previousContainer.data,
      event.container.data,
      event.previousIndex,
      event.currentIndex,
    );
    event.container.data.forEach((item: Record<string, any>, i: number) => {
      item['ordre'] = i;
    });

    this.reorderService.moveIndicateur(indicateurId, {
      new_parent_type: newParentType,
      new_parent_id: newParentId,
      position: event.currentIndex,
    }).pipe(
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.dnd.moveSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 2000 },
        );
        // Pas de reload sur succès : l'optimistic transfer a déjà déplacé
        // l'indicateur dans la bonne liste côté UI. Reload silencieux
        // déclenche une race avec le cdkDropList qui peut casser le drop
        // suivant (#261, retour utilisateur du 2026-05-12).
      },
      error: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.dnd.moveError'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 },
        );
        // Rollback : recharge depuis le serveur.
        this.loadPlanData(true);
      },
    });
  }

  removeMetriqueFromEdit(index: number): void {
    const met = this.editIndicateurMetriques[index];
    if (met.id_metrique) {
      // Mark existing metrique for deletion
      this.editIndicateurMetriques = this.editIndicateurMetriques.map((m, i) =>
        i === index ? { ...m, _deleted: true } : m
      );
    } else {
      // Remove new metrique entirely
      this.editIndicateurMetriques = this.editIndicateurMetriques.filter((_, i) => i !== index);
    }
  }

  saveEditIndicateur(ind: any): void {
    if (!this.editIndicateurNom.trim()) return;
    if (!this.validateMetriquesActiveLevels(this.editIndicateurMetriques)) return;
    this.isSavingIndicateur.set(true);

    const payload: any = {
      nom_indicateur: this.editIndicateurNom.trim(),
      est_standardise: this.editIndicateurStandardise,
    };
    if (this.editIndicateurType) payload.type_indicateur = this.editIndicateurType;
    if (this.editIndicateurDescription.trim()) payload.description = this.editIndicateurDescription.trim();

    this.enjeuService.updateIndicateur(ind.id_indicateur, payload).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        // Process metriques: create new, update existing, delete removed
        const metriqueOps: Observable<any>[] = [];

        for (const met of this.editIndicateurMetriques) {
          if (met._deleted && met.id_metrique) {
            // Delete existing metrique
            metriqueOps.push(this.enjeuService.deleteMetrique(met.id_metrique));
          } else if (!met._deleted && met.nom_metrique.trim()) {
            if (met.id_metrique) {
              // Update existing metrique
              metriqueOps.push(this.enjeuService.updateMetrique(met.id_metrique, this.buildMetriquePayload(ind.id_indicateur, met)));
            } else {
              // Create new metrique
              metriqueOps.push(this.enjeuService.createMetrique(this.buildMetriquePayload(ind.id_indicateur, met)));
            }
          }
        }

        if (metriqueOps.length === 0) {
          this.snackBar.open(
            this.translate.instant('enjeux.indicateurs.updateSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.editingIndicateurId.set(null);
          this.editIndicateurMetriques = [];
          this.isSavingIndicateur.set(false);
          this.loadPlanData(true);
          return;
        }

        forkJoin(metriqueOps).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.indicateurs.updateSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.editingIndicateurId.set(null);
            this.editIndicateurMetriques = [];
            this.isSavingIndicateur.set(false);
            this.loadPlanData(true);
          },
          error: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.metriques.partialError'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
            this.editingIndicateurId.set(null);
            this.editIndicateurMetriques = [];
            this.isSavingIndicateur.set(false);
            this.loadPlanData(true);
          }
        });
      },
      error: () => {
        this.isSavingIndicateur.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.updateError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  deleteIndicateur(ind: any): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translate.instant('common.actions.delete'),
        message: this.translate.instant('enjeux.indicateurs.deleteConfirm'),
        confirmLabel: this.translate.instant('common.actions.delete')
      }
    });

    dialogRef.afterClosed().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(result => {
      if (result) {
        this.enjeuService.deleteIndicateur(ind.id_indicateur).pipe(
          takeUntilDestroyed(this.destroyRef)
        ).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.indicateurs.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData(true);
          },
          // Sans ce handler, toute erreur (403 plan verrouillé, contrainte, etc.)
          // échouait silencieusement → la suppression semblait « sans effet » (#444).
          error: (err) => {
            const detail = err?.error?.detail;
            this.snackBar.open(
              detail || this.translate.instant('enjeux.indicateurs.deleteError'),
              this.translate.instant('common.actions.close'),
              { duration: 6000, panelClass: 'snackbar-error' }
            );
          }
        });
      }
    });
  }

  /**
   * Ouvre la modale de duplication pour cet indicateur (#262). Liste les
   * NE et RA candidats du plan en excluant le parent actuel pour ne pas
   * dupliquer en place. Sur confirmation, appelle l'API duplicate puis
   * recharge les données.
   */
  duplicateIndicateur(ind: any): void {
    const data = this.planEnjeuxData();
    if (!data) return;

    const targetsNe: DuplicateIndicateurTargetNe[] = [];
    const targetsRa: DuplicateIndicateurTargetRa[] = [];

    // Walk the data tree to collect targets across all enjeux of the plan.
    const allEnjeux = [...(data.enjeux || []), ...(data.fcr || [])];
    for (const enjeu of allEnjeux) {
      // Branche OLT → NE
      for (const olt of enjeu.objectifs_long_terme || []) {
        for (const ne of olt.niveaux_exigence || []) {
          targetsNe.push({
            id_ne: ne.id_ne,
            libelle: ne.libelle,
            enjeu_libelle: enjeu.intitule_court || enjeu.libelle,
            olt_libelle: olt.libelle,
          });
        }
      }
      // Branche OO → RA
      for (const fi of enjeu.facteurs_influence || []) {
        for (const p of fi.pressions || []) {
          for (const oo of p.objectifs_operationnels || []) {
            for (const ra of oo.resultats_attendus || []) {
              targetsRa.push({
                id_ra: ra.id_ra,
                libelle: ra.libelle,
                enjeu_libelle: enjeu.intitule_court || enjeu.libelle,
                oo_libelle: oo.libelle,
              });
            }
          }
        }
      }
    }

    const dialogRef = this.dialog.open<
      DuplicateIndicateurDialogComponent,
      DuplicateIndicateurDialogData,
      DuplicateIndicateurDialogResult | null
    >(DuplicateIndicateurDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        sourceName: ind.nom_indicateur,
        currentNeId: ind.id_ne ?? null,
        currentRaId: ind.id_resultat_attendu ?? null,
        availableNe: targetsNe,
        availableRa: targetsRa,
      },
    });

    dialogRef.afterClosed().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(result => {
      if (!result) return;
      this.enjeuService.duplicateIndicateur(ind.id_indicateur, {
        ne_ids: result.ne_ids,
        ra_ids: result.ra_ids,
      }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (resp) => {
          this.snackBar.open(
            this.translate.instant('enjeux.indicateurs.duplicate.success', { count: resp.count }),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.loadPlanData(true);
        },
        error: (err) => {
          const detail = err?.error?.error || err?.error?.detail || this.translate.instant('enjeux.indicateurs.duplicate.error');
          this.snackBar.open(detail,
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
        }
      });
    });
  }

  // ============================================
  // Métriques CRUD
  // ============================================

  readonly scoreLevels = [1, 2, 3, 4, 5];

  deleteMetrique(met: any): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.metriques.deleteTitle'),
        message: this.translate.instant('enjeux.metriques.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteMetrique(met.id_metrique).pipe(
          takeUntilDestroyed(this.destroyRef)
        ).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.metriques.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData(true);
          }
        });
      }
    });
  }

  getScoreLevelLabel(level: number): string {
    const labels: Record<number, string> = {
      1: this.translate.instant('enjeux.metriques.scores.tresMauvais'),
      2: this.translate.instant('enjeux.metriques.scores.mauvais'),
      3: this.translate.instant('enjeux.metriques.scores.moyen'),
      4: this.translate.instant('enjeux.metriques.scores.bon'),
      5: this.translate.instant('enjeux.metriques.scores.tresBon'),
    };
    return labels[level] || '';
  }

  getScoreInf(met: any, level: number): string {
    const val = met[`score_${level}_inf`];
    return val != null ? val.toString() : '-';
  }

  getScoreSup(met: any, level: number): string {
    const val = met[`score_${level}_sup`];
    return val != null ? val.toString() : '-';
  }

  private formatNum(val: number): string {
    // #575 — la base stocke jusqu'à 4 décimales : ne pas tronquer l'affichage à
    // 2 (un seuil 4,111 s'affichait « 4.11 »). Cohérent avec metrique-seuils.util
    // et metrique-grid-display. Les zéros terminaux restent supprimés.
    return parseFloat(val.toFixed(4)).toString();
  }

  getScoreRange(met: any, level: number): string {
    // Fallback intelligent si le type_metrique n'est pas renseigné :
    // on détecte le type d'après les données présentes sur la métrique
    let mnemonique = met.type_metrique_mnemonique;
    if (!mnemonique) {
      const hasLabels = [1, 2, 3, 4, 5].some(l => met[`score_${l}_label`]?.toString().trim());
      const hasVals = [1, 2, 3, 4, 5].some(l => met[`score_${l}_val`] != null);
      const hasBounds = [1, 2, 3, 4, 5].some(l => met[`score_${l}_inf`] != null || met[`score_${l}_sup`] != null);
      if (hasLabels && !hasBounds) mnemonique = 'TEXTE';
      else if (hasVals && !hasBounds) mnemonique = 'CHIFFRE';
      else mnemonique = 'NUMERIQUE';
    }

    if (mnemonique === 'CHIFFRE') {
      // #359 — niveau « non utilisé » : masqué (cellule vide) à la lecture.
      if ((met.inactive_levels || []).includes(level)) return '-';
      const val = met[`score_${level}_val`];
      return val != null ? this.formatNum(Number(val)) : '-';
    }
    if (mnemonique === 'TEXTE') {
      if ((met.inactive_levels || []).includes(level)) return '-';
      const label = met[`score_${level}_label`];
      return label?.trim() || '-';
    }
    // NUMERIQUE — #359 : niveau « non utilisé » masqué (cohérent Chiffre/Texte
    // et robuste aux données déjà enregistrées avec des bornes résiduelles).
    if ((met.inactive_levels || []).includes(level)) return '- - -';

    const inf = met[`score_${level}_inf`];
    const sup = met[`score_${level}_sup`];

    if (inf == null && sup == null) return '- - -';

    // Determine inclusivity for the inf side (from previous level's boundary)
    let infInclusive = true; // level 1: inclusive by default
    if (level > 1) {
      const prevSupInclusive = met[`score_${level - 1}_sup_inclusive`];
      // If prev sup is inclusive (≤), this level's inf is exclusive (>)
      infInclusive = !(prevSupInclusive === true || prevSupInclusive == null);
    }

    // Determine inclusivity for the sup side
    let supInclusive = true; // level 5: inclusive by default
    if (level < 5) {
      const si = met[`score_${level}_sup_inclusive`];
      supInclusive = (si === true || si == null);
    }

    // Open interval: only one bound → compact notation (< 10, > 10, ≤ 10, ≥ 10)
    if (inf != null && sup == null) {
      const op = infInclusive ? '≥' : '>';
      return `${op}\u00A0${this.formatNum(Number(inf))}`;
    }
    if (inf == null && sup != null) {
      const op = supInclusive ? '≤' : '<';
      return `${op}\u00A0${this.formatNum(Number(sup))}`;
    }

    // Both bounds: bracket notation [0 ; 20], ]20 ; 40[
    const leftBracket = infInclusive ? '[' : ']';
    const rightBracket = supInclusive ? ']' : '[';
    return `${leftBracket}${this.formatNum(Number(inf))}\u00A0;\u00A0${this.formatNum(Number(sup))}${rightBracket}`;
  }

  /**
   * D\u00E9tecte les niveaux de score adjacents qui partagent exactement la m\u00EAme
   * valeur/borne/label et les fusionne visuellement en cellules avec
   * `colspan` > 1 (#256). Permet \u00E0 l'utilisateur de simuler une grille \u00E0
   * 3 niveaux (ex. diminution/maintien/augmentation) en remplissant les
   * m\u00EAmes valeurs sur 1+2 et 4+5 \u2014 l'affichage compresse automatiquement.
   *
   * Retourne la liste des groupes ordonn\u00E9s gauche\u2192droite, chacun avec
   * `levels` (les niveaux concern\u00E9s), `colspan` et la valeur format\u00E9e.
   */
  /**
   * #247 — Lignes affichées dans une cellule de palier en lecture.
   *
   * Pour une métrique avec un seul bloc (principal) : retourne 1 entrée.
   * Pour une métrique avec N blocs complémentaires : retourne 1 + N entrées,
   * chacune avec son opérateur (OR/AND) et ses parenthèses.
   */
  getCellLines(met: any, level: number): Array<{
    text: string;
    blockLabel: string;
    op?: 'OR' | 'AND';
    openParen?: boolean;
    closeParen?: boolean;
  }> {
    const lines: Array<any> = [];

    // Libellés des blocs : « intitulé (unité) » (ex: « hauteur (m) »), avec
    // repli sur « Bloc A/B » si l'intitulé est vide (cf. metriqueBlockLabel).

    // Bloc principal.
    const mainText = this.getScoreRange(met, level);
    if (mainText && mainText !== '-' && mainText !== '- - -') {
      lines.push({
        text: mainText,
        blockLabel: this.metriqueBlockLabel(met, 0),
        openParen: (met.group_open ?? 0) > 0,
        closeParen: (met.group_close ?? 0) > 0,
      });
    }

    // Blocs complémentaires.
    const blocks = met.score_blocks || [];
    blocks.forEach((block: any, idx: number) => {
      const text = this.getScoreRange({ ...block, type_metrique_mnemonique: 'NUMERIQUE' }, level);
      if (!text || text === '-' || text === '- - -') return;
      lines.push({
        text,
        blockLabel: this.metriqueBlockLabel(met, idx + 1),
        op: block.logical_op,
        openParen: (block.group_open ?? 0) > 0,
        closeParen: (block.group_close ?? 0) > 0,
      });
    });

    return lines;
  }

  /** Vrai si la métrique a au moins un bloc complémentaire (désactive la fusion). */
  hasExtraBlocks(met: any): boolean {
    return (met.score_blocks?.length ?? 0) > 0;
  }

  getScoreGroups(met: any): Array<{ levels: number[]; colspan: number; value: string; primaryLevel: number }> {
    const values = [1, 2, 3, 4, 5].map(l => this.getScoreRange(met, l));
    const groups: Array<{ levels: number[]; colspan: number; value: string; primaryLevel: number }> = [];
    const isEmpty = (v: string) => v === '-' || v === '- - -' || !v;
    let i = 0;
    while (i < 5) {
      const level = i + 1;
      const value = values[i];
      // Empty cells never merge \u2014 chacune reste seule pour pr\u00E9server le
      // signal visuel "niveau non renseign\u00E9".
      if (isEmpty(value)) {
        groups.push({ levels: [level], colspan: 1, value, primaryLevel: level });
        i++;
        continue;
      }
      // Cellules pleines : on \u00E9tend le groupe tant que les voisines ont
      // la m\u00EAme valeur.
      const mergedLevels = [level];
      let j = i + 1;
      while (j < 5 && values[j] === value) {
        mergedLevels.push(j + 1);
        j++;
      }
      groups.push({ levels: mergedLevels, colspan: mergedLevels.length, value, primaryLevel: level });
      i = j;
    }
    return groups;
  }

  /**
   * After data is loaded, if a pending operation scroll target exists,
   * walk the enjeu tree to find it, expand all parent nodes, then scroll.
   */
  private expandAndScrollToOperation(): void {
    const opId = this.pendingScrollToOperation();
    if (!opId) return;
    this.pendingScrollToOperation.set(null);

    const enjeu = this.selectedEnjeu();
    if (!enjeu) return;

    // Search in OO path (operations tab): FI → Pression → OO → RA → Indicateur → Métrique → Opération
    for (const fi of enjeu.facteurs_influence || []) {
      for (const pression of fi.pressions || []) {
        for (const oo of pression.objectifs_operationnels || []) {
          for (const ra of oo.resultats_attendus || []) {
            for (const ind of ra.indicateurs || []) {
              for (const met of ind.metriques || []) {
                for (const op of met.operations || []) {
                  if (op.id_operation === opId) {
                    // Expand the whole chain: OO → indicateur → operation.
                    // On force aussi l'onglet « operations » pour que le nœud soit
                    // rendu même quand l'appelant n'a pas transmis `tab` (retour
                    // depuis la fiche action, #531).
                    this.activeTab.set('operations');
                    this.expandedOoIds.update(s => { const ns = new Set(s); ns.add(oo.id_oo); return ns; });
                    this.expandedOoIndicateurIds.update(s => { const ns = new Set(s); ns.add(ind.id_indicateur); return ns; });
                    this.expandedOoOperationIds.update(s => { const ns = new Set(s); ns.add(opId); return ns; });
                    this.scrollToElement(`operation-${opId}`);
                    return;
                  }
                }
              }
            }
          }
        }
      }
    }

    // Search in NE path (olt tab): OLT → NE → Indicateur → Métrique → Opération
    for (const olt of enjeu.objectifs_long_terme || []) {
      for (const ne of olt.niveaux_exigence || []) {
        for (const ind of ne.indicateurs || []) {
          for (const met of ind.metriques || []) {
            for (const op of met.operations || []) {
              if (op.id_operation === opId) {
                this.activeTab.set('olt');
                this.expandedOltIds.update(s => { const ns = new Set(s); ns.add(olt.id_olt); return ns; });
                this.expandedIndicateurIds.update(s => { const ns = new Set(s); ns.add(ind.id_indicateur); return ns; });
                this.expandedOperationIds.update(s => { const ns = new Set(s); ns.add(opId); return ns; });
                this.scrollToElement(`operation-${opId}`);
                return;
              }
            }
          }
        }
      }
    }
  }

  /**
   * After data is loaded, if a pending métrique scroll target exists,
   * walk the enjeu tree to find it, expand its parent OO/OLT/indicateur, then scroll.
   * Utilisé pour ramener l'utilisateur à proximité de l'endroit d'où il a ouvert
   * le formulaire d'action quand celui-ci est annulé (pas d'opération créée).
   */
  private expandAndScrollToMetrique(): void {
    const metId = this.pendingScrollToMetrique();
    if (!metId) return;
    this.pendingScrollToMetrique.set(null);

    const enjeu = this.selectedEnjeu();
    if (!enjeu) return;

    // Branche OO (onglet operations)
    for (const fi of enjeu.facteurs_influence || []) {
      for (const pression of fi.pressions || []) {
        for (const oo of pression.objectifs_operationnels || []) {
          for (const ra of oo.resultats_attendus || []) {
            for (const ind of ra.indicateurs || []) {
              for (const met of ind.metriques || []) {
                if (met.id_metrique === metId) {
                  this.activeTab.set('operations');
                  this.expandedOoIds.update(s => { const ns = new Set(s); ns.add(oo.id_oo); return ns; });
                  this.expandedOoIndicateurIds.update(s => { const ns = new Set(s); ns.add(ind.id_indicateur); return ns; });
                  this.scrollToElement(`metrique-${metId}`);
                  return;
                }
              }
            }
          }
        }
      }
    }

    // Branche NE (onglet olt)
    for (const olt of enjeu.objectifs_long_terme || []) {
      for (const ne of olt.niveaux_exigence || []) {
        for (const ind of ne.indicateurs || []) {
          for (const met of ind.metriques || []) {
            if (met.id_metrique === metId) {
              this.activeTab.set('olt');
              this.expandedOltIds.update(s => { const ns = new Set(s); ns.add(olt.id_olt); return ns; });
              this.expandedIndicateurIds.update(s => { const ns = new Set(s); ns.add(ind.id_indicateur); return ns; });
              this.scrollToElement(`metrique-${metId}`);
              return;
            }
          }
        }
      }
    }
  }

  private scrollToElement(id: string): void {
    // Poll until the element exists in the DOM (Angular needs multiple
    // change-detection cycles to render the cascade of @if blocks).
    let attempts = 0;
    const maxAttempts = 20;
    const interval = setInterval(() => {
      attempts++;
      const el = this.elRef.nativeElement.querySelector(`#${id}`);
      if (el) {
        clearInterval(interval);
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else if (attempts >= maxAttempts) {
        clearInterval(interval);
      }
    }, 100);
  }

  // ============================================
  // Operations (Actions) - Expand/collapse + helpers
  // ============================================

  toggleOperation(id: number): void {
    this.expandedOperationIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isOperationExpanded(id: number): boolean {
    return this.expandedOperationIds().has(id);
  }

  /**
   * Get the plan's full year range for the programmation table.
   * All operations use the same columns (plan years).
   */
  getPlanYears(): number[] {
    const debut = this.planAnneeDebut();
    const fin = this.planAnneeFin();
    if (!debut || !fin) return [];
    const years: number[] = [];
    for (let y = debut; y <= fin; y++) {
      years.push(y);
    }
    return years;
  }

  /**
   * Get sorted year range for the programmation table (operation-specific fallback).
   */
  getOperationYears(op: Operation): number[] {
    if (op.operation_annees && op.operation_annees.length > 0) {
      return op.operation_annees
        .map(a => a.annee)
        .sort((a, b) => a - b);
    }
    // Fallback to annee_min/annee_max
    if (op.annee_min && op.annee_max) {
      const years: number[] = [];
      for (let y = op.annee_min; y <= op.annee_max; y++) {
        years.push(y);
      }
      return years;
    }
    return [];
  }

  /**
   * Get OperationAnnee for a given year, or null.
   */
  getOperationAnnee(op: Operation, year: number): OperationAnnee | null {
    if (!op.operation_annees) return null;
    return op.operation_annees.find(a => a.annee === year) || null;
  }

  /**
   * Check if an operation year is planned (annual periodicite checkbox only).
   * The monthly template is shared across all years and indicates WHICH months
   * within a planned year, not WHETHER a year is planned.
   */
  isYearPlanned(op: Operation, year: number): boolean {
    const annee = this.getOperationAnnee(op, year);
    if (!annee) return false;
    return !!annee.periodicite;
  }

  /**
   * Check if any year of the operation has monthly planning details.
   */
  hasAnyMonthlyPlanning(op: Operation): boolean {
    if (!op.operation_annees) return false;
    return op.operation_annees.some(a =>
      a.periodicite_mensuelle && Object.values(a.periodicite_mensuelle).some(v => v === true)
    );
  }

  private readonly monthNames = [
    'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
    'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'
  ];

  /**
   * Get list of planned month names for a given year.
   */
  getPlannedMonths(op: Operation, year: number): string[] {
    const annee = this.getOperationAnnee(op, year);
    if (!annee || !annee.periodicite_mensuelle) return [];
    const months: string[] = [];
    for (let m = 1; m <= 12; m++) {
      if (annee.periodicite_mensuelle[m.toString()] === true) {
        months.push(this.monthNames[m - 1]);
      }
    }
    return months;
  }

  /**
   * Get the planned months for the entire operation (same for all years).
   * Takes the monthly planning from the first year that has it.
   */
  getPlannedMonthsForOperation(op: Operation): string[] {
    if (!op.operation_annees) return [];
    const anneeWithMonths = op.operation_annees.find(a =>
      a.periodicite_mensuelle && Object.values(a.periodicite_mensuelle).some(v => v === true)
    );
    if (!anneeWithMonths || !anneeWithMonths.periodicite_mensuelle) return [];
    const months: string[] = [];
    for (let m = 1; m <= 12; m++) {
      if (anneeWithMonths.periodicite_mensuelle[m.toString()] === true) {
        months.push(this.monthNames[m - 1]);
      }
    }
    return months;
  }

  /**
   * Check if an operation uses by_type ventilation (fonctionnement/investissement without organismes).
   */
  isTypeBudgetMode(op: Operation): boolean {
    return op.ventilation_mode === 'by_type';
  }

  /**
   * Check if an operation has per-organisme data in any of its annees.
   */
  hasOrganismeData(op: Operation): boolean {
    if (!op.operation_annees) return false;
    return op.operation_annees.some(a => a.organismes && a.organismes.length > 0);
  }

  /**
   * Get unique organismes across all annees of an operation.
   */
  getOperationOrganismes(op: Operation): { id_organisme: number; organisme_nom: string }[] {
    if (!op.operation_annees) return [];
    const map = new Map<number, string>();
    for (const a of op.operation_annees) {
      for (const org of a.organismes || []) {
        if (!map.has(org.id_organisme)) {
          map.set(org.id_organisme, org.organisme_nom || '');
        }
      }
    }
    return Array.from(map.entries())
      .map(([id, nom]) => ({ id_organisme: id, organisme_nom: nom }))
      .sort((a, b) => a.organisme_nom.localeCompare(b.organisme_nom));
  }

  /**
   * Get organisme budget/etp for a specific year.
   */
  getOrgAnnee(op: Operation, year: number, orgId: number): { fonct: number | null; invest: number | null; etp: number | null } {
    const annee = this.getOperationAnnee(op, year);
    if (!annee?.organismes) return { fonct: null, invest: null, etp: null };
    const org = annee.organismes.find(o => o.id_organisme === orgId);
    if (!org) return { fonct: null, invest: null, etp: null };
    return {
      fonct: org.budget_fonctionnement != null ? parseFloat(String(org.budget_fonctionnement)) : null,
      invest: org.budget_investissement != null ? parseFloat(String(org.budget_investissement)) : null,
      etp: org.etp != null ? parseFloat(String(org.etp)) : null
    };
  }

  formatOrgBudgetTotal(op: Operation, year: number, orgId: number): string {
    const d = this.getOrgAnnee(op, year, orgId);
    const total = (d.fonct || 0) + (d.invest || 0);
    return total ? total.toLocaleString('fr-FR') + '€' : '-';
  }

  /**
   * Format budget value for display.
   */
  formatBudget(value: number | string | null | undefined): string {
    if (value == null) return '-';
    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) return '-';
    return num.toLocaleString('fr-FR') + '€';
  }

  /**
   * Format ETP/travail value for display.
   */
  formatTravail(value: number | string | null | undefined): string {
    if (value == null) return '-';
    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) return '-';
    return num.toString();
  }

  /**
   * Format frequency display.
   */
  private readonly frequenceLabels: Record<string, string> = {
    'jour': 'jour', 'semaine': 'semaine', 'mois': 'mois', 'an': 'an',
    'trimestre': 'trimestre', 'semestre': 'semestre',
    '2_ans': '2 ans', '5_ans': '5 ans', '10_ans': '10 ans', 'autre': 'autre'
  };

  getFrequenceDisplay(op: Operation): string {
    if (!op.frequence_nombre || !op.frequence_unite) return '';
    const unite = this.frequenceLabels[op.frequence_unite.toLowerCase()] || op.frequence_unite;
    return `${op.frequence_nombre} ${this.translate.instant('enjeux.operations.foisPar')} ${unite}`;
  }

  // ============================================
  // Operations (Actions) - Navigation vers page dédiée
  // ============================================

  navigateToOperationForm(metriqueId?: number): void {
    const slug = this.planSlug();
    if (!slug) return;
    if (metriqueId) {
      this.lastScrollAnchor = { type: 'metrique', id: metriqueId };
    }
    const queryParams: any = {};
    if (metriqueId) queryParams.metriqueId = metriqueId;
    const enjeuSlug = this.selectedEnjeuSlug();
    if (enjeuSlug) queryParams.returnEnjeu = enjeuSlug;
    queryParams.returnTab = this.activeTab();
    const extras = Object.keys(queryParams).length > 0 ? { queryParams } : {};
    this.router.navigate(['/plans', slug, 'enjeux', 'operations', 'nouveau'], extras);
  }

  /**
   * #1 — Ouvre le dialogue d'ajout d'action au niveau indicateur.
   * L'action sera liée par défaut à TOUTES les métriques de l'indicateur.
   */
  openAddActionForIndicateur(ind: any): void {
    const metriques = (ind.metriques || []).filter((m: any) => !m._deleted);
    if (metriques.length === 0) {
      // #367/#539 — pas de métrique : on propose de créer une action rattachée
      // directement à l'indicateur OU de lier une action existante à cet
      // indicateur (sans passer par une métrique).
      this.openLinkActionForIndicateur(ind.id_indicateur, ind.nom_indicateur || '');
      return;
    }
    const metriqueIds: number[] = metriques.map((m: any) => m.id_metrique).filter(Boolean);
    const indicateurNom: string = ind.nom_indicateur || '';
    this.openAddActionDialogForIds(metriqueIds, indicateurNom);
  }

  /**
   * #539 — Ouvre le dialogue « créer ou lier » au niveau d'un indicateur sans
   * métrique. À la création : form d'action rattaché à l'indicateur. À la
   * liaison : rattache l'action existante directement à l'indicateur
   * (id_indicateur), pour que les indicateurs sans métrique puissent aussi
   * porter des actions.
   */
  openLinkActionForIndicateur(indicateurId: number, indicateurNom: string): void {
    const planId = this.planId();
    if (!planId || !indicateurId) return;

    const dialogRef = this.dialog.open(LinkOperationDialogComponent, {
      width: '700px', maxWidth: '95vw', maxHeight: '90vh',
      data: {
        planId,
        indicateurId,
        indicateurNom,
      } as LinkOperationDialogData,
    });

    dialogRef.afterClosed().pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result: LinkOperationDialogResult | undefined) => {
        if (!result || result.action === 'cancel') return;

        if (result.action === 'create') {
          this.navigateToOperationFormForIndicateur(indicateurId);
        } else if (result.action === 'link' && result.operationId) {
          this.enjeuService.updateOperation(result.operationId, { id_indicateur: indicateurId }).pipe(
            takeUntilDestroyed(this.destroyRef)
          ).subscribe({
            next: () => {
              this.snackBar.open(
                this.translate.instant('enjeux.operations.linkSuccess'),
                this.translate.instant('common.actions.close'),
                { duration: 3000 }
              );
              this.loadPlanData(true);
            },
            error: () => {
              this.snackBar.open(
                this.translate.instant('enjeux.operations.linkError'),
                this.translate.instant('common.actions.close'),
                { duration: 3000 }
              );
            },
          });
        } else if (result.action === 'copy' && result.operationId) {
          this.copyOperationTo(result.operationId, { indicateurId });
        }
      });
  }

  /**
   * #552 — Copie une action existante vers une cible (métrique ou indicateur) et
   * rafraîchit la vue. Duplicata indépendant, contrairement au lien.
   */
  private copyOperationTo(operationId: number, target: { metriqueId?: number; indicateurId?: number }): void {
    this.enjeuService.copyOperation(operationId, target).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.operations.copySuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadPlanData(true);
      },
      error: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.operations.copyError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      },
    });
  }

  /** #367 — Navigation vers le form d'action rattachée directement à un indicateur (sans métrique). */
  private navigateToOperationFormForIndicateur(indicateurId: number): void {
    const slug = this.planSlug();
    if (!slug || !indicateurId) return;
    const queryParams: any = { indicateurId };
    const enjeuSlug = this.selectedEnjeuSlug();
    if (enjeuSlug) queryParams.returnEnjeu = enjeuSlug;
    queryParams.returnTab = this.activeTab();
    this.router.navigate(['/plans', slug, 'enjeux', 'operations', 'nouveau'], { queryParams });
  }

  /**
   * Variante de `openAddActionDialog` qui accepte plusieurs métriques.
   * À la création : ouvre le form d'opération en pré-liant à toutes.
   * À la liaison d'une opération existante : boucle les appels API.
   */
  openAddActionDialogForIds(metriqueIds: number[], label: string): void {
    const planId = this.planId();
    if (!planId || metriqueIds.length === 0) return;

    const dialogRef = this.dialog.open(LinkOperationDialogComponent, {
      width: '700px', maxWidth: '95vw', maxHeight: '90vh',
      data: {
        planId,
        metriqueId: metriqueIds[0],  // pour compatibilité avec le dialog existant
        metriqueNom: label,
      } as LinkOperationDialogData,
    });

    dialogRef.afterClosed().pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((result: LinkOperationDialogResult | undefined) => {
        if (!result || result.action === 'cancel') return;

        if (result.action === 'create') {
          this.navigateToOperationFormForMetriques(metriqueIds);
        } else if (result.action === 'link' && result.operationId) {
          // Lier l'opération existante à TOUTES les métriques cibles
          const opId = result.operationId;
          const links$ = metriqueIds.map(id =>
            this.enjeuService.addMetriqueToOperation(opId, id)
          );
          forkJoin(links$).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
            next: () => {
              this.snackBar.open(
                this.translate.instant('enjeux.operations.linkSuccess'),
                this.translate.instant('common.actions.close'),
                { duration: 3000 }
              );
              this.loadPlanData(true);
            },
            error: () => {
              this.snackBar.open(
                this.translate.instant('enjeux.operations.linkError'),
                this.translate.instant('common.actions.close'),
                { duration: 3000 }
              );
            },
          });
        } else if (result.action === 'copy' && result.operationId) {
          // Copie indépendante rattachée à la 1re métrique, puis liée aux autres.
          const [first, ...rest] = metriqueIds;
          this.enjeuService.copyOperation(result.operationId, { metriqueId: first }).pipe(
            switchMap((newOp) =>
              rest.length
                ? forkJoin(rest.map(id => this.enjeuService.addMetriqueToOperation(newOp.id_operation, id)))
                : of(newOp)
            ),
            takeUntilDestroyed(this.destroyRef)
          ).subscribe({
            next: () => {
              this.snackBar.open(
                this.translate.instant('enjeux.operations.copySuccess'),
                this.translate.instant('common.actions.close'),
                { duration: 3000 }
              );
              this.loadPlanData(true);
            },
            error: () => {
              this.snackBar.open(
                this.translate.instant('enjeux.operations.copyError'),
                this.translate.instant('common.actions.close'),
                { duration: 3000 }
              );
            },
          });
        }
      });
  }

  /** Navigation vers le form d'opération en pré-liant à plusieurs métriques (CSV). */
  private navigateToOperationFormForMetriques(metriqueIds: number[]): void {
    const slug = this.planSlug();
    if (!slug) return;
    const queryParams: any = { metriqueIds: metriqueIds.join(',') };
    const enjeuSlug = this.selectedEnjeuSlug();
    if (enjeuSlug) queryParams.returnEnjeu = enjeuSlug;
    queryParams.returnTab = this.activeTab();
    this.router.navigate(['/plans', slug, 'enjeux', 'operations', 'nouveau'], { queryParams });
  }

  openAddActionDialog(metriqueId: number, metriqueNom: string): void {
    const planId = this.planId();
    if (!planId) return;

    const dialogRef = this.dialog.open(LinkOperationDialogComponent, {
      width: '700px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        planId,
        metriqueId,
        metriqueNom,
      } as LinkOperationDialogData,
    });

    dialogRef.afterClosed().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe((result: LinkOperationDialogResult | undefined) => {
      if (!result || result.action === 'cancel') return;

      if (result.action === 'create') {
        this.navigateToOperationForm(metriqueId);
      } else if (result.action === 'link' && result.operationId) {
        this.enjeuService.addMetriqueToOperation(result.operationId, metriqueId).pipe(
          takeUntilDestroyed(this.destroyRef)
        ).subscribe({
          next: (updatedOp) => {
            this.snackBar.open(
              this.translate.instant('enjeux.operations.linkSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            // Mise à jour locale : ajouter l'opération à la métrique
            this.updateMetriqueOperations(metriqueId, ops => {
              if (ops.some(o => o.id_operation === updatedOp.id_operation)) return ops;
              return [...ops, updatedOp];
            });
          },
          error: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.operations.linkError'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
          }
        });
      } else if (result.action === 'copy' && result.operationId) {
        this.copyOperationTo(result.operationId, { metriqueId });
      }
    });
  }

  unlinkOperation(operation: Operation, metriqueId: number): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.operations.unlinkTitle'),
        message: this.translate.instant('enjeux.operations.unlinkConfirm'),
        confirmText: this.translate.instant('enjeux.operations.unlinkTitle'),
        cancelText: this.translate.instant('common.actions.cancel'),
      }
    });

    dialogRef.afterClosed().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.removeMetriqueFromOperation(operation.id_operation, metriqueId).pipe(
          takeUntilDestroyed(this.destroyRef)
        ).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.operations.unlinkSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            // Mise à jour locale : retirer l'opération de cette métrique
            this.updateMetriqueOperations(metriqueId, ops =>
              ops.filter(o => o.id_operation !== operation.id_operation)
            );
          },
          error: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.operations.unlinkError'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
          }
        });
      }
    });
  }

  getOtherMetriques(op: Operation, currentMetriqueId: number): MetriqueRef[] {
    if (!op.metriques) return [];
    return op.metriques.filter(m => m.id_metrique !== currentMetriqueId);
  }

  /** Métriques affichables en chips sous une action : uniquement les métriques
   *  liées à l'action (indicateurs d'État/Pression). On exclut les indicateurs de
   *  réponse (type REPONSE) — propres à l'action — qui ne doivent pas apparaître
   *  en tête, ainsi que les métriques sans nom (#398). */
  visibleMetriques(op: Operation): MetriqueRef[] {
    return (op.metriques || []).filter(m =>
      m.indicateur_type !== 'REPONSE' && (m.nom_metrique || '').trim().length > 0,
    );
  }

  navigateToEditOperation(operationId: number): void {
    const slug = this.planSlug();
    if (!slug) return;
    this.lastScrollAnchor = { type: 'operation', id: operationId };
    const enjeuSlug = this.selectedEnjeuSlug();
    // #576 — transmettre l'onglet courant (OLT / Opérations) : sans lui, le
    // formulaire retombe sur `returnTab='operations'` par défaut et renvoie
    // l'utilisateur « sur les OO » après enregistrement, même si l'action était
    // affichée dans l'onglet OLT.
    const queryParams: Record<string, string> = { returnTab: this.activeTab() };
    if (enjeuSlug) queryParams['returnEnjeu'] = enjeuSlug;
    this.router.navigate(
      ['/plans', slug, 'enjeux', 'operations', operationId, 'modifier'],
      { queryParams }
    );
  }

  /**
   * #494 — Ouvre la fiche synthétique de l'action (page dédiée `/fiche`),
   * et non le formulaire en lecture seule.
   * #455 — Ouverture dans un nouvel onglet pour ne pas perdre l'arborescence en cours.
   */
  navigateToViewOperation(operationId: number): void {
    const slug = this.planSlug();
    if (!slug) return;
    // #529 — on transmet l'enjeu ouvert pour que le bouton retour de la fiche
    // revienne à l'action ciblée dans le bon enjeu (fragment `operation-<id>`),
    // et pas seulement à la page des enjeux.
    const fromEnjeu = this.selectedEnjeuSlug();
    const url = this.router.serializeUrl(
      this.router.createUrlTree(['/plans', slug, 'enjeux', 'operations', operationId, 'fiche'], {
        queryParams: { from: 'enjeux', ...(fromEnjeu ? { fromEnjeu } : {}) },
      })
    );
    window.open(url, '_blank', 'noopener');
  }

  deleteOperation(operation: Operation): void {
    // #457 — Quand l'action est liée à plusieurs métriques, proposer le choix
    // entre supprimer l'action dans sa globalité ou retirer uniquement le lien
    // à une métrique. Sinon, simple confirmation de suppression.
    const linkedMetriques = this.visibleMetriques(operation);
    if (linkedMetriques.length > 1) {
      const dialogRef = this.dialog.open(DeleteOperationDialogComponent, {
        width: '480px',
        data: {
          libelle: operation.libelle,
          metriques: linkedMetriques.map(m => ({
            id_metrique: m.id_metrique,
            nom_metrique: m.nom_metrique,
          })),
        },
      });

      dialogRef.afterClosed().pipe(
        takeUntilDestroyed(this.destroyRef)
      ).subscribe((result: DeleteOperationDialogResult | undefined) => {
        if (!result || result.action === 'cancel') return;
        if (result.action === 'unlink' && result.metriqueIds?.length) {
          this.removeOperationMetriqueLinks(operation, result.metriqueIds);
        } else if (result.action === 'delete') {
          this.performDeleteOperation(operation);
        }
      });
      return;
    }

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.operations.deleteTitle'),
        message: this.translate.instant('enjeux.operations.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(confirmed => {
      if (confirmed) {
        this.performDeleteOperation(operation);
      }
    });
  }

  /** #457 — Suppression complète de l'action (DELETE), avec reload du plan. */
  private performDeleteOperation(operation: Operation): void {
    this.enjeuService.deleteOperation(operation.id_operation).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.operations.deleteSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadPlanData(true);
      },
      error: (err) => {
        const detail = err?.error?.detail || this.translate.instant('enjeux.messages.deleteError');
        this.snackBar.open(
          detail,
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      }
    });
  }

  /** #457/#538 — Retrait des liens action ↔ métrique(s) (l'action reste
   *  accessible depuis les autres métriques). Plusieurs métriques peuvent être
   *  déliées en une passe. Recharge le plan pour rafraîchir les chips. */
  private removeOperationMetriqueLinks(operation: Operation, metriqueIds: number[]): void {
    const calls$ = metriqueIds.map(id =>
      this.enjeuService.removeMetriqueFromOperation(operation.id_operation, id)
    );
    forkJoin(calls$).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.operations.unlinkSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadPlanData(true);
      },
      error: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.operations.unlinkError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  /** #566 — apparence du tag de priorité (palette scores), ou null si aucune. */
  prioriteTag(op: Operation): TagAppearance | null {
    return getPrioriteTag(op.priorite_label);
  }

  // ============================================
  // Objectifs Opérationnels (OO)
  // ============================================

  toggleOo(id: number): void {
    this.expandedOoIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isOoExpanded(id: number): boolean {
    return this.expandedOoIds().has(id);
  }

  startAddOo(): void {
    this.addingOo.set(true);
    this.newOoLibelle = '';
    this.newOoDescription = '';
    this.newOoPressionIds = [];
  }

  cancelAddOo(): void {
    this.addingOo.set(false);
    this.newOoLibelle = '';
    this.newOoDescription = '';
    this.newOoPressionIds = [];
  }

  saveOo(): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu || !this.newOoLibelle.trim()) return;
    const isFcr = this.isSelectedFcr();
    // Règle de rattachement d'un OO selon la catégorie du parent :
    //  - FCR  : l'OO est rattaché directement au FCR via id_enjeu. Le lien vers
    //           des pressions (issues des enjeux écologiques) est FACULTATIF (#474) :
    //           on envoie aussi pression_ids si l'utilisateur en a choisi.
    //  - Enjeu : l'OO descend obligatoirement d'au moins une pression
    //           (chaîne Facteur → Pression → OO). On bloque si rien n'est sélectionné.
    if (!isFcr && this.newOoPressionIds.length === 0) return;

    this.enjeuService.createObjectifOperationnel({
      ...(isFcr
        ? { id_enjeu: enjeu.id_enjeu, ...(this.newOoPressionIds.length ? { pression_ids: this.newOoPressionIds } : {}) }
        : { pression_ids: this.newOoPressionIds }),
      libelle: this.newOoLibelle.trim(),
      description: this.newOoDescription.trim() || undefined,
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.oo.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddOo();
        this.loadPlanData(true);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  startEditOo(oo: ObjectifOperationnel): void {
    this.editingOoId.set(oo.id_oo);
    this.editOoLibelle = oo.libelle;
    this.editOoDescription = oo.description || '';
    this.editOoNumero = oo.numero_manuel ?? null;
    this.editOoPressionIds = [...(oo.pression_ids || [])];
  }

  cancelEditOo(): void {
    this.editingOoId.set(null);
    this.editOoLibelle = '';
    this.editOoDescription = '';
    this.editOoNumero = null;
    this.editOoPressionIds = [];
  }

  saveEditOo(oo: ObjectifOperationnel): void {
    if (!this.editOoLibelle.trim()) return;
    // #474 — un OO de FCR est rattaché directement au FCR ; son lien vers des
    // pressions est facultatif et éditable. On envoie donc toujours pression_ids
    // (liste éventuellement vide = aucun lien). Pour un enjeu classique, au moins
    // une pression reste obligatoire.
    const isFcr = this.isSelectedFcr();
    if (!isFcr && this.editOoPressionIds.length === 0) return;

    // #526 — Vide/0/invalide → numérotation automatique (null).
    const rawNumero = this.editOoNumero;
    const newNumero = rawNumero != null && rawNumero > 0 ? Math.floor(rawNumero) : null;

    this.enjeuService.updateObjectifOperationnel(oo.id_oo, {
      pression_ids: this.editOoPressionIds,
      libelle: this.editOoLibelle.trim(),
      description: this.editOoDescription.trim() || undefined,
      numero_manuel: newNumero,
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.oo.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditOo();
        this.loadPlanData(true);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  deleteOo(oo: ObjectifOperationnel): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.oo.deleteTitle'),
        message: this.translate.instant('enjeux.oo.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteObjectifOperationnel(oo.id_oo).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.oo.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData(true);
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Résultats Attendus
  // ============================================

  startAddRa(ooId: number): void {
    this.addingRaForOo.set(ooId);
    this.newRaLibelle = '';
    this.newRaDescription = '';
  }

  cancelAddRa(): void {
    this.addingRaForOo.set(null);
    this.newRaLibelle = '';
    this.newRaDescription = '';
  }

  saveRa(oo: ObjectifOperationnel): void {
    if (!this.newRaLibelle.trim()) return;

    this.enjeuService.createResultatAttendu({
      id_oo: oo.id_oo,
      libelle: this.newRaLibelle.trim(),
      description: this.newRaDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.resultatAttendu.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddRa();
        this.loadPlanData(true);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  startEditRa(ra: ResultatAttendu): void {
    this.editingRaId.set(ra.id_ra);
    this.editRaLibelle = ra.libelle;
    this.editRaDescription = ra.description || '';
  }

  cancelEditRa(): void {
    this.editingRaId.set(null);
    this.editRaLibelle = '';
    this.editRaDescription = '';
  }

  saveEditRa(ra: ResultatAttendu): void {
    if (!this.editRaLibelle.trim()) return;

    this.enjeuService.updateResultatAttendu(ra.id_ra, {
      libelle: this.editRaLibelle.trim(),
      description: this.editRaDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.resultatAttendu.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditRa();
        this.loadPlanData(true);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  deleteRa(ra: ResultatAttendu): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.resultatAttendu.deleteTitle'),
        message: this.translate.instant('enjeux.resultatAttendu.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteResultatAttendu(ra.id_ra).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.resultatAttendu.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData(true);
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Indicateurs de pression (OO tab)
  // ============================================

  toggleOoIndicateur(id: number): void {
    this.expandedOoIndicateurIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) { newIds.delete(id); } else { newIds.add(id); }
      return newIds;
    });
  }

  isOoIndicateurExpanded(id: number): boolean {
    return this.expandedOoIndicateurIds().has(id);
  }

  toggleOoOperation(id: number): void {
    this.expandedOoOperationIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) { newIds.delete(id); } else { newIds.add(id); }
      return newIds;
    });
  }

  isOoOperationExpanded(id: number): boolean {
    return this.expandedOoOperationIds().has(id);
  }

  startAddIndicateurForRa(raId: number): void {
    this.addingIndicateurForRa.set(raId);
    this.newOoIndicateurNom = '';
    this.newOoIndicateurType = null;
    this.newOoIndicateurStandardise = false;
    this.newOoIndicateurDescription = '';
    this.ooIndicateurFormMetriques = [];
    this.loadTypeMetriqueOptions();
  }

  cancelAddIndicateurForRa(): void {
    this.addingIndicateurForRa.set(null);
    this.newOoIndicateurNom = '';
    this.newOoIndicateurType = null;
    this.newOoIndicateurStandardise = false;
    this.newOoIndicateurDescription = '';
    this.ooIndicateurFormMetriques = [];
  }

  addOoMetriqueRow(): void {
    this.ooIndicateurFormMetriques.push({ ...this.createEmptyMetrique(), _expanded: true });
  }

  removeOoMetriqueRow(index: number): void {
    this.ooIndicateurFormMetriques.splice(index, 1);
  }

  saveIndicateurForRa(ra: ResultatAttendu): void {
    if (!this.newOoIndicateurNom.trim()) return;
    if (!this.validateMetriquesActiveLevels(this.ooIndicateurFormMetriques)) return;

    this.isSavingOoIndicateur.set(true);
    this.enjeuService.createIndicateur({
      id_resultat_attendu: ra.id_ra,
      nom_indicateur: this.newOoIndicateurNom.trim(),
      description: this.newOoIndicateurDescription.trim() || undefined,
      type_indicateur: this.newOoIndicateurType || undefined,
      est_standardise: this.newOoIndicateurStandardise
    }).subscribe({
      next: (indicateur) => {
        // Create metriques if any.
        // #574 — aligner sur le flux NE (saveIndicateur) : conserver les
        // métriques « Indéterminé » même sans intitulé (sinon elles étaient
        // silencieusement supprimées), et signaler un échec partiel (l'ancien
        // code avalait l'erreur sans aucun message → « la métrique ne se
        // sauvegarde pas » sans explication).
        const metriquesToCreate = this.ooIndicateurFormMetriques.filter(m =>
          m.nom_metrique.trim() || this.getMetriqueTypeMnemonique(m.type_metrique) === 'INDETERMINE'
        );
        if (metriquesToCreate.length > 0) {
          const metriqueRequests: Observable<any>[] = metriquesToCreate.map(m =>
            this.enjeuService.createMetrique(this.buildMetriquePayload(indicateur.id_indicateur, m))
          );

          forkJoin(metriqueRequests).subscribe({
            next: () => {
              this.isSavingOoIndicateur.set(false);
              this.snackBar.open(
                this.translate.instant('enjeux.indicateur.createSuccess'),
                this.translate.instant('common.actions.close'),
                { duration: 3000 }
              );
              this.cancelAddIndicateurForRa();
              this.loadPlanData(true);
            },
            error: () => {
              // Indicateur créé mais au moins une métrique a échoué : prévenir
              // l'utilisateur (auparavant : échec silencieux).
              this.isSavingOoIndicateur.set(false);
              this.snackBar.open(
                this.translate.instant('enjeux.metriques.partialError'),
                this.translate.instant('common.actions.close'),
                { duration: 5000 }
              );
              this.cancelAddIndicateurForRa();
              this.loadPlanData(true);
            }
          });
        } else {
          this.isSavingOoIndicateur.set(false);
          this.snackBar.open(
            this.translate.instant('enjeux.indicateur.createSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.cancelAddIndicateurForRa();
          this.loadPlanData(true);
        }
      },
      error: () => {
        this.isSavingOoIndicateur.set(false);
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  startEditOoIndicateur(indicateur: Indicateur, expandMetriqueId?: number): void {
    this.editingOoIndicateurId.set(indicateur.id_indicateur);
    this.editOoIndicateurNom = indicateur.nom_indicateur;
    this.editOoIndicateurType = indicateur.type_indicateur || null;
    this.editOoIndicateurStandardise = indicateur.est_standardise;
    this.editOoIndicateurDescription = indicateur.description || '';
    this.loadTypeMetriqueOptions();
    this.editOoIndicateurMetriques = (indicateur.metriques || []).map(m =>
      this.metriqueToFormData(m)
    );

    // #411 — édition d'une métrique précise : la déplier directement
    if (expandMetriqueId != null) {
      const target = this.editOoIndicateurMetriques.find(
        m => m.id_metrique === expandMetriqueId
      );
      if (target) target._expanded = true;
    }
  }

  cancelEditOoIndicateur(): void {
    this.editingOoIndicateurId.set(null);
    this.editOoIndicateurNom = '';
    this.editOoIndicateurType = null;
    this.editOoIndicateurStandardise = false;
    this.editOoIndicateurDescription = '';
    this.editOoIndicateurMetriques = [];
  }

  addOoMetriqueToEdit(): void {
    this.editOoIndicateurMetriques = [...this.editOoIndicateurMetriques, { ...this.createEmptyMetrique(), _expanded: true }];
  }

  removeOoMetriqueFromEdit(index: number): void {
    const met = this.editOoIndicateurMetriques[index];
    if (met.id_metrique) {
      this.editOoIndicateurMetriques = this.editOoIndicateurMetriques.map((m, i) =>
        i === index ? { ...m, _deleted: true } : m
      );
    } else {
      this.editOoIndicateurMetriques = this.editOoIndicateurMetriques.filter((_, i) => i !== index);
    }
  }

  saveEditOoIndicateur(ind: Indicateur): void {
    if (!this.editOoIndicateurNom.trim()) return;
    if (!this.validateMetriquesActiveLevels(this.editOoIndicateurMetriques)) return;
    this.isSavingOoIndicateur.set(true);

    const payload: any = {
      nom_indicateur: this.editOoIndicateurNom.trim(),
      est_standardise: this.editOoIndicateurStandardise,
    };
    if (this.editOoIndicateurType) payload.type_indicateur = this.editOoIndicateurType;
    if (this.editOoIndicateurDescription.trim()) payload.description = this.editOoIndicateurDescription.trim();

    this.enjeuService.updateIndicateur(ind.id_indicateur, payload).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        const metriqueOps: Observable<any>[] = [];

        for (const met of this.editOoIndicateurMetriques) {
          if (met._deleted && met.id_metrique) {
            metriqueOps.push(this.enjeuService.deleteMetrique(met.id_metrique));
          } else if (!met._deleted && met.nom_metrique.trim()) {
            if (met.id_metrique) {
              metriqueOps.push(this.enjeuService.updateMetrique(met.id_metrique, this.buildMetriquePayload(ind.id_indicateur, met)));
            } else {
              metriqueOps.push(this.enjeuService.createMetrique(this.buildMetriquePayload(ind.id_indicateur, met)));
            }
          }
        }

        if (metriqueOps.length === 0) {
          this.snackBar.open(
            this.translate.instant('enjeux.indicateurs.updateSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.editingOoIndicateurId.set(null);
          this.editOoIndicateurMetriques = [];
          this.isSavingOoIndicateur.set(false);
          this.loadPlanData(true);
          return;
        }

        forkJoin(metriqueOps).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.indicateurs.updateSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.editingOoIndicateurId.set(null);
            this.editOoIndicateurMetriques = [];
            this.isSavingOoIndicateur.set(false);
            this.loadPlanData(true);
          },
          error: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.metriques.partialError'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
            this.editingOoIndicateurId.set(null);
            this.editOoIndicateurMetriques = [];
            this.isSavingOoIndicateur.set(false);
            this.loadPlanData(true);
          }
        });
      },
      error: () => {
        this.isSavingOoIndicateur.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.updateError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  deleteOoIndicateur(indicateur: Indicateur): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.indicateur.deleteTitle'),
        message: this.translate.instant('enjeux.indicateur.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteIndicateur(indicateur.id_indicateur).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.indicateur.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData(true);
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }
}
