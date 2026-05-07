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
import { forkJoin, Observable } from 'rxjs';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatRadioModule } from '@angular/material/radio';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AuthService } from '../../../../core/services/auth.service';
import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import {
  DuplicateIndicateurDialogComponent,
  DuplicateIndicateurDialogData,
  DuplicateIndicateurDialogResult,
  DuplicateIndicateurTargetNe,
  DuplicateIndicateurTargetRa,
} from '../../../../shared/components/modals/duplicate-indicateur-dialog/duplicate-indicateur-dialog.component';
import { LinkOperationDialogComponent, LinkOperationDialogData, LinkOperationDialogResult } from '../../../../shared/components/modals';
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
    MatCheckboxModule,
    MatButtonToggleModule,
    MatDialogModule,
    MatSnackBarModule,
    TranslateModule,
    HeaderComponent,
    PlanSidebarComponent,
    EnjeuAccordionComponent,
    SectionTitleComponent
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

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  planAnneeDebut = signal<number | null>(null);
  planAnneeFin = signal<number | null>(null);
  planReferentIds = signal<number[]>([]);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  /** Statut du plan courant — exposé par l'endpoint by-plan, utilisé pour
   *  verrouiller l'édition hors brouillon (#248). */
  planStatut = signal<'draft' | 'valide' | 'archive' | null>(null);

  /** Plan en brouillon : seul état autorisant l'édition de contenu (#248). */
  isPlanDraft = computed(() => this.planStatut() === 'draft');

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
  editNeLibelle = '';
  editNeDescription = '';

  // Opérations expand/collapse
  expandedOperationIds = signal<Set<number>>(new Set());
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

  // Enjeux et FCR séparés
  enjeux = computed(() => {
    const data = this.planEnjeuxData();
    return data?.enjeux || [];
  });

  fcr = computed(() => {
    const data = this.planEnjeuxData();
    return data?.fcr || [];
  });

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
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('anchor-highlight');
        setTimeout(() => el.classList.remove('anchor-highlight'), 2000);
      } else if (attempts >= maxAttempts) {
        clearInterval(interval);
      }
    }, 100);
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

  // Computed pour le nombre d'OLT de l'enjeu sélectionné
  totalOltCount = computed(() => {
    return this.selectedEnjeu()?.objectifs_long_terme?.length || 0;
  });

  // Computed pour les pressions de l'enjeu sélectionné (via facteurs d'influence)
  selectedPressions = computed(() => {
    const enjeu = this.selectedEnjeu();
    if (!enjeu) return [];
    return (enjeu.facteurs_influence || []).flatMap(fi => fi.pressions || []);
  });

  // Computed pour les OOs de l'enjeu sélectionné (via facteurs → pressions, dédupliqués)
  selectedOos = computed(() => {
    const seen = new Set<number>();
    return this.selectedPressions()
      .flatMap(p => p.objectifs_operationnels || [])
      .filter(oo => {
        if (seen.has(oo.id_oo)) return false;
        seen.add(oo.id_oo);
        return true;
      });
  });

  totalOoCount = computed(() => {
    return this.selectedOos().length;
  });

  // Event handlers pour les accordéons
  onEnjeuDelete(enjeu: Enjeu): void {
    const isFcr = enjeu.categorie_mnemonique === 'FCR';
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: isFcr
          ? this.translate.instant('enjeux.messages.fcrDeleteConfirmTitle')
          : this.translate.instant('enjeux.messages.enjeuDeleteConfirmTitle'),
        message: isFcr
          ? this.translate.instant('enjeux.messages.fcrDeleteConfirm')
          : this.translate.instant('enjeux.messages.enjeuDeleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
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
  }

  cancelEditOlt(): void {
    this.editingOltId.set(null);
    this.editOltLibelle = '';
    this.editOltDescription = '';
  }

  saveEditOlt(olt: ObjectifLongTerme): void {
    if (!this.editOltLibelle.trim()) return;
    const newLibelle = this.editOltLibelle.trim();
    const newDescription = this.editOltDescription.trim() || undefined;

    this.enjeuService.updateObjectifLongTerme(olt.id_olt, {
      libelle: newLibelle,
      description: newDescription
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
                ? { ...o, libelle: newLibelle, description: newDescription }
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

  metriqueToFormData(met: Metrique): MetriqueFormData {
    const sensVariation = met.sens_variation || 'CROISSANT';

    const c = (v: number | null | undefined) => this.cleanNum(v);
    return {
      id_metrique: met.id_metrique,
      nom_metrique: met.nom_metrique,
      type_metrique: met.type_metrique || null,
      unite: met.unite || '',
      ponderation: met.ponderation ?? null,
      etat_reference: met.etat_reference || '',
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
      has_score1_optional_bound: met.has_borne_score1 ?? false,
      has_score5_optional_bound: met.has_borne_score5 ?? false,
    };
  }

  addMetriqueToForm(): void {
    this.indicateurFormMetriques = [...this.indicateurFormMetriques, this.createEmptyMetrique()];
  }

  removeMetriqueFromForm(index: number): void {
    this.indicateurFormMetriques = this.indicateurFormMetriques.filter((_, i) => i !== index);
  }

  getMetriqueTypeMnemonique(typeMetriqueId: number | null): string {
    if (!typeMetriqueId) return 'NUMERIQUE';
    const opt = this.typeMetriqueOptions().find(o => o.id_nomenclature === typeMetriqueId);
    return opt?.mnemonique || 'NUMERIQUE';
  }

  buildMetriquePayload(indicateurId: number, met: MetriqueFormData): MetriqueCreatePayload {
    const payload: MetriqueCreatePayload = {
      id_indicateur: indicateurId,
      nom_metrique: met.nom_metrique.trim(),
    };
    if (met.type_metrique) payload.type_metrique = met.type_metrique;
    if (met.unite.trim()) payload.unite = met.unite.trim();
    if (met.ponderation != null) payload.ponderation = met.ponderation;
    if (met.etat_reference.trim()) payload.etat_reference = met.etat_reference.trim();

    const mnemonique = this.getMetriqueTypeMnemonique(met.type_metrique);
    for (let level = 1; level <= 5; level++) {
      const s = met.scores[level];
      if (mnemonique === 'CHIFFRE') {
        if (s?.val != null) (payload as any)[`score_${level}_val`] = s.val;
      } else if (mnemonique === 'TEXTE') {
        if (s?.label?.trim()) (payload as any)[`score_${level}_label`] = s.label.trim();
      } else {
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

    // Direction, inclusivité et bornes extrêmes (NUMERIQUE only)
    if (mnemonique === 'NUMERIQUE') {
      payload.sens_variation = met.sens_variation;
      payload.score_1_sup_inclusive = met.score_1_sup_inclusive;
      payload.score_2_sup_inclusive = met.score_2_sup_inclusive;
      payload.score_3_sup_inclusive = met.score_3_sup_inclusive;
      payload.score_4_sup_inclusive = met.score_4_sup_inclusive;
      payload.has_borne_score1 = met.has_score1_optional_bound;
      payload.has_borne_score5 = met.has_score5_optional_bound;
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

  saveIndicateur(ne: any): void {
    if (!this.newIndicateurNom.trim()) return;
    this.isSavingIndicateur.set(true);

    const payload: any = {
      id_ne: ne.id_ne,
      nom_indicateur: this.newIndicateurNom.trim(),
      est_standardise: this.newIndicateurStandardise,
    };
    if (this.newIndicateurType) payload.type_indicateur = this.newIndicateurType;
    if (this.newIndicateurDescription.trim()) payload.description = this.newIndicateurDescription.trim();

    // Filter metriques that have a name
    const validMetriques = this.indicateurFormMetriques.filter(m => m.nom_metrique.trim());

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
    if (!this.standaloneMetriqueForm || !this.standaloneMetriqueForm.nom_metrique.trim()) return;
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

  startEditIndicateur(ind: any): void {
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
  }

  cancelEditIndicateur(): void {
    this.editingIndicateurId.set(null);
    this.editIndicateurMetriques = [];
  }

  addMetriqueToEdit(): void {
    this.editIndicateurMetriques = [...this.editIndicateurMetriques, this.createEmptyMetrique()];
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
    return parseFloat(val.toFixed(2)).toString();
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
      const val = met[`score_${level}_val`];
      return val != null ? this.formatNum(Number(val)) : '-';
    }
    if (mnemonique === 'TEXTE') {
      const label = met[`score_${level}_label`];
      return label?.trim() || '-';
    }
    // NUMERIQUE
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
                    // Expand the whole chain: OO → indicateur → operation
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
    const extras = Object.keys(queryParams).length > 0 ? { queryParams } : {};
    this.router.navigate(['/plans', slug, 'enjeux', 'operations', 'nouveau'], extras);
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

  navigateToEditOperation(operationId: number): void {
    const slug = this.planSlug();
    if (!slug) return;
    this.lastScrollAnchor = { type: 'operation', id: operationId };
    const enjeuSlug = this.selectedEnjeuSlug();
    this.router.navigate(
      ['/plans', slug, 'enjeux', 'operations', operationId, 'modifier'],
      { queryParams: enjeuSlug ? { returnEnjeu: enjeuSlug } : {} }
    );
  }

  /** Ouvre la fiche action en lecture seule (page dédiée, partageable via URL) */
  navigateToViewOperation(operationId: number): void {
    const slug = this.planSlug();
    if (!slug) return;
    this.lastScrollAnchor = { type: 'operation', id: operationId };
    this.router.navigate(['/plans', slug, 'enjeux', 'operations', operationId]);
  }

  deleteOperation(operation: Operation): void {
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
    });
  }

  getPrioriteClass(op: Operation): string {
    if (!op.priorite_label) return '';
    if (op.priorite_label.includes('1')) return '1';
    if (op.priorite_label.includes('2')) return '2';
    if (op.priorite_label.includes('3')) return '3';
    return '';
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
    if (!enjeu || !this.newOoLibelle.trim() || this.newOoPressionIds.length === 0) return;

    this.enjeuService.createObjectifOperationnel({
      pression_ids: this.newOoPressionIds,
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
    this.editOoPressionIds = [...(oo.pression_ids || [])];
  }

  cancelEditOo(): void {
    this.editingOoId.set(null);
    this.editOoLibelle = '';
    this.editOoDescription = '';
    this.editOoPressionIds = [];
  }

  saveEditOo(oo: ObjectifOperationnel): void {
    if (!this.editOoLibelle.trim() || this.editOoPressionIds.length === 0) return;

    this.enjeuService.updateObjectifOperationnel(oo.id_oo, {
      pression_ids: this.editOoPressionIds,
      libelle: this.editOoLibelle.trim(),
      description: this.editOoDescription.trim() || undefined,
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
    this.ooIndicateurFormMetriques.push(this.createEmptyMetrique());
  }

  removeOoMetriqueRow(index: number): void {
    this.ooIndicateurFormMetriques.splice(index, 1);
  }

  saveIndicateurForRa(ra: ResultatAttendu): void {
    if (!this.newOoIndicateurNom.trim()) return;

    this.isSavingOoIndicateur.set(true);
    this.enjeuService.createIndicateur({
      id_resultat_attendu: ra.id_ra,
      nom_indicateur: this.newOoIndicateurNom.trim(),
      description: this.newOoIndicateurDescription.trim() || undefined,
      type_indicateur: this.newOoIndicateurType || undefined,
      est_standardise: this.newOoIndicateurStandardise
    }).subscribe({
      next: (indicateur) => {
        // Create metriques if any
        const metriquesToCreate = this.ooIndicateurFormMetriques.filter(m => m.nom_metrique.trim());
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
              this.isSavingOoIndicateur.set(false);
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

  startEditOoIndicateur(indicateur: Indicateur): void {
    this.editingOoIndicateurId.set(indicateur.id_indicateur);
    this.editOoIndicateurNom = indicateur.nom_indicateur;
    this.editOoIndicateurType = indicateur.type_indicateur || null;
    this.editOoIndicateurStandardise = indicateur.est_standardise;
    this.editOoIndicateurDescription = indicateur.description || '';
    this.loadTypeMetriqueOptions();
    this.editOoIndicateurMetriques = (indicateur.metriques || []).map(m =>
      this.metriqueToFormData(m)
    );
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
    this.editOoIndicateurMetriques = [...this.editOoIndicateurMetriques, this.createEmptyMetrique()];
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
