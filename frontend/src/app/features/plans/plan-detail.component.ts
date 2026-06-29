import { Component, signal, computed, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatChipsModule } from '@angular/material/chips';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatMenuModule } from '@angular/material/menu';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subscription } from 'rxjs';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { StatusChipComponent } from '../../shared/components/status-chip/status-chip.component';
import { TagComponent } from '../../shared/components/tag/tag.component';
import { SectionTitleComponent } from '../../shared/components/section-title/section-title.component';
import { PlanSidebarComponent } from './shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { EnjeuService } from '../../core/services/enjeu.service';
import { ValidationService } from '../../core/services/validation.service';
import { ValidationRequestListItem } from '../../core/models/notification.model';
import { AdminPlan, PlanFichier, PlanMembre, PlanSite, PlanStatut, PlanVersionChainItem } from '../../core/models/admin.model';
import { PlanVersionTimelineComponent } from '../../shared/components/plan-version-timeline/plan-version-timeline.component';
import { EntityTileComponent } from '../../shared/components/entity-tile/entity-tile.component';
import { ConfirmDialogComponent } from '../../shared/components/confirm-dialog/confirm-dialog.component';
import { Enjeu } from '../../core/models/enjeu.model';
import {
  PlanFormModalComponent,
  PlanFormModalData,
} from '../../shared/components/modals/plan-form-modal/plan-form-modal.component';
import {
  UploadDocumentModalComponent,
  UploadDocumentDialogData,
} from '../../shared/components/modals/upload-document-modal/upload-document-modal.component';
import {
  AccessRequestDialogComponent,
  AccessRequestDialogData,
} from '../../shared/components/access-request-dialog/access-request-dialog.component';
import {
  LinkPlanSiteModalComponent,
  LinkPlanSiteModalData,
} from '../../shared/components/modals/link-plan-site-modal/link-plan-site-modal.component';
import {
  LinkPlanReferentModalComponent,
  LinkPlanReferentModalData,
} from '../../shared/components/modals/link-plan-referent-modal/link-plan-referent-modal.component';
import {
  ArchivePreviousPlanDialogComponent,
  ArchivePreviousPlanDialogData,
  ArchivePreviousPlanDialogResult,
  findPreviousValidatedPlan,
} from '../../shared/components/modals/archive-previous-plan-dialog/archive-previous-plan-dialog.component';
import {
  ExtendDurationDialogComponent,
  ExtendDurationDialogData,
  ExtendDurationDialogResult,
} from '../../shared/components/modals/extend-duration-dialog/extend-duration-dialog.component';
import {
  StartRevisionDialogComponent,
  StartRevisionDialogData,
  StartRevisionDialogResult,
} from '../../shared/components/modals/start-revision-dialog/start-revision-dialog.component';
import {
  StartMiParcoursDialogComponent,
  StartMiParcoursDialogData,
  StartMiParcoursDialogResult,
} from '../../shared/components/modals/start-mi-parcours-dialog/start-mi-parcours-dialog.component';
import {
  DuplicatePlanDialogComponent,
  DuplicatePlanDialogData,
  DuplicatePlanDialogResult,
} from '../../shared/components/modals/duplicate-plan-dialog/duplicate-plan-dialog.component';
import {
  MiParcoursPromptDialogComponent,
  MiParcoursPromptDialogData,
  MiParcoursPromptDialogResult,
} from '../../shared/components/modals/mi-parcours-prompt-dialog/mi-parcours-prompt-dialog.component';
import {
  CsrpnStepDialogComponent,
  CsrpnStepDialogData,
  CsrpnStepDialogResult,
  CsrpnStep,
} from '../../shared/components/modals/csrpn-step-dialog/csrpn-step-dialog.component';
import { getExtensionBadgeKey, getPlanStatusKey, getPlanStatusTooltipKey } from '../../shared/utils/plan-status.utils';

interface SyntheseAccordion {
  id: string;
  title: string;
  colorClass: 'terra-cotta' | 'orange';
  expanded: boolean;
  hasSubItems?: boolean;
  subItems?: SubAccordion[];
}

interface OperationSynthItem {
  label: string;
  enjeuSlug?: string;
  ooId?: number;
  operationId: number;
  statut?: 'draft' | 'valide';
}

interface SubAccordion {
  id: string;
  title: string;
  expanded: boolean;
  items?: OperationSynthItem[];
}

@Component({
  selector: 'app-plan-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatDialogModule,
    MatChipsModule,
    MatTooltipModule,
    MatMenuModule,
    TranslateModule,
    HeaderComponent,
    SectionTitleComponent,
    PlanSidebarComponent,
    PlanVersionTimelineComponent,
    EntityTileComponent,
    StatusChipComponent,
    TagComponent,
  ],
  templateUrl: './plan-detail.component.html',
  styleUrl: './plan-detail.component.scss'
})
export class PlanDetailComponent implements OnInit, OnDestroy {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly adminService = inject(AdminService);
  readonly authService = inject(AuthService);
  private readonly enjeuService = inject(EnjeuService);
  private readonly validationService = inject(ValidationService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  private routeSub?: Subscription;

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  // Plan data from API
  plan = signal<AdminPlan | null>(null);

  // Version chain for timeline — always return at least the current plan
  versionChain = computed(() => {
    const p = this.plan();
    const chain = (p?.version_chain || []) as PlanVersionChainItem[];
    if (chain.length > 0) return chain;
    // Fallback: build a single-item chain from the current plan
    if (p) {
      return [{
        id_pg: p.id_pg,
        nom: p.nom,
        slug: p.slug || '',
        version: p.version || '1',
        statut: p.statut,
        type_document: p.type_document_display || null,
        type_document_mnemonique: undefined,
        is_current: true,
      } as PlanVersionChainItem];
    }
    return [];
  });

  // #281 — Mnémonique du type de site principal (premier par rang) pour
  // contextualiser le badge "Étendu" affiché à côté du chip de statut.
  principalSiteTypeMnemonique = computed<string | null>(() => {
    const sites = this.plan()?.sites || [];
    if (sites.length === 0) return null;
    const principal = [...sites].sort((a, b) => (a.rang ?? 99) - (b.rang ?? 99))[0];
    return principal?.type_site_mnemonique ?? null;
  });

  // Clé i18n du statut du plan.
  statusLabelKey = computed<string>(() => {
    const p = this.plan();
    if (!p) return 'plans.status.draft';
    return getPlanStatusKey(p.statut);
  });

  // Tooltip pédagogique du chip statut (draft / valide / modifie / archive).
  statusTooltipKey = computed<string>(() => {
    const p = this.plan();
    if (!p) return 'plans.status.draftTooltip';
    return getPlanStatusTooltipKey(p.statut);
  });

  // #250 / #281 — Indique si le plan est étendu (annees_extension > 0) et
  // expose la clé i18n du badge contextualisé par type de site.
  isPlanExtended = computed<boolean>(() => {
    const p = this.plan();
    return !!(p && p.annees_extension && p.annees_extension > 0);
  });

  extensionBadgeKey = computed<string>(() =>
    getExtensionBadgeKey(this.principalSiteTypeMnemonique())
  );

  // Enjeux/FCR data for synthèse and sidebar
  enjeuxData = signal<Enjeu[]>([]);
  fcrData = signal<Enjeu[]>([]);
  enjeuxLoading = signal(false);

  // Aggregated OLT/OO across all enjeux AND FCR (#191 — les OLT créés
  // sur un FCR doivent aussi apparaître dans la synthèse).
  allOlts = computed(() => {
    const items = [...this.enjeuxData(), ...this.fcrData()];
    return items.flatMap(item =>
      (item.objectifs_long_terme || []).map(olt => ({
        ...olt,
        enjeu_libelle: item.libelle,
        enjeu_id: item.id_enjeu
      }))
    );
  });

  allOos = computed(() => {
    const seen = new Set<number>();
    const items = [...this.enjeuxData(), ...this.fcrData()];
    return items.flatMap(item =>
      (item.facteurs_influence || []).flatMap(fi =>
        (fi.pressions || []).flatMap(p =>
          (p.objectifs_operationnels || [])
            .filter(oo => {
              if (seen.has(oo.id_oo)) return false;
              seen.add(oo.id_oo);
              return true;
            })
            .map(oo => ({
              ...oo,
              enjeu_libelle: item.libelle,
              enjeu_id: item.id_enjeu
            }))
        )
      )
    );
  });

  // Unified list of plan members (referents + non-referents) sorted referents first
  planMembers = computed(() => {
    const p = this.plan();
    if (!p?.membres || p.membres.length === 0) {
      // Fallback to referents if membres not populated
      return (p?.referents || []).map(r => ({
        id_role: r.id_role,
        email: r.email,
        nom_complet: r.nom_complet,
        referent: true,
      } as PlanMembre));
    }
    return [...p.membres].sort((a, b) => {
      if (a.referent === b.referent) return 0;
      return a.referent ? -1 : 1;
    });
  });

  // Operations loading state
  operationsLoading = signal(false);

  // Pending site link requests for this plan
  pendingSiteRequests = signal<ValidationRequestListItem[]>([]);

  // Permissions cycle de vie (#346) : référent du plan, admin_og, super_admin OU rédacteur principal.
  canManageLifecycle = computed(() => {
    if (this.authService.isSuperAdmin() || this.authService.isRedacteurPrincipal() || this.authService.isAdminOrganisme()) {
      return true;
    }
    const p = this.plan();
    const currentUser = this.authService.currentUser();
    if (!p || !currentUser) return false;
    return p.referents?.some(r => r.id_role === currentUser.id) || false;
  });

  // Permissions édition: tout ce que canManageLifecycle fait + redacteur_principal,
  // ET le plan doit être en brouillon (#248). Les actions de cycle de vie restent
  // accessibles hors brouillon via canManageLifecycle.
  canEditPlan = computed(() => {
    if (!this.isPlanDraft()) return false;
    if (this.authService.isSuperAdmin() || this.authService.isRedacteurPrincipal() || this.authService.isAdminOrganisme()) {
      return true;
    }
    const p = this.plan();
    const currentUser = this.authService.currentUser();
    if (!p || !currentUser) return false;
    return p.referents?.some(r => r.id_role === currentUser.id) || false;
  });

  /**
   * Plan éditable (#248). Seul le statut `draft` autorise l'édition.
   * L'extension de durée (#250) est un attribut orthogonal au statut et
   * ne débloque PAS l'édition.
   */
  isPlanDraft = computed(() => {
    return this.plan()?.statut === 'draft';
  });

  // Accordéons de la section Synthèse
  // #191 — Tous les accordéons de la synthèse sont ouverts par défaut
  // pour que les utilisateurs voient immédiatement les OLT et OO créés
  // (sinon les utilisateurs pensent qu'ils ne s'affichent pas).
  syntheseAccordions = signal<SyntheseAccordion[]>([
    {
      id: 'enjeux',
      title: 'Enjeux et Facteurs clés de réussite',
      colorClass: 'terra-cotta',
      expanded: true
    },
    {
      id: 'objectifs-lt',
      title: 'Objectifs long terme',
      colorClass: 'terra-cotta',
      expanded: true
    },
    {
      id: 'objectifs-op',
      title: 'Objectifs opérationnels',
      colorClass: 'terra-cotta',
      expanded: true
    },
    {
      id: 'actions',
      title: 'Actions et suivis',
      colorClass: 'orange',
      expanded: true,
      hasSubItems: true,
      subItems: []
    }
  ]);

  ngOnInit(): void {
    // S'abonner aux changements de paramètre slug (gère aussi la navigation intra-composant)
    this.routeSub = this.route.paramMap.subscribe(params => {
      const slug = params.get('slug');
      if (slug && slug !== this.planSlug()) {
        this.planSlug.set(slug);
        this.loadPlan();
      }
    });

    // Handle ?edit=metadata query param (opens edit modal after duplication)
    this.route.queryParamMap.subscribe(queryParams => {
      if (queryParams.get('edit') === 'metadata') {
        // Remove query param from URL
        this.router.navigate([], {
          relativeTo: this.route,
          queryParams: {},
          replaceUrl: true,
        });
        // Open edit modal once plan is loaded
        this.openEditModalWhenReady();
      }
    });
  }

  private openEditModalWhenReady(): void {
    // Wait for plan to be loaded before opening the modal
    const interval = setInterval(() => {
      const p = this.plan();
      if (p && !this.isLoading()) {
        clearInterval(interval);
        this.openEditModal(p);
      }
    }, 200);
    // Safety timeout
    setTimeout(() => clearInterval(interval), 10000);
  }

  openEditModal(plan: AdminPlan): void {
    const data: PlanFormModalData = { plan };
    const dialogRef = this.dialog.open(PlanFormModalComponent, {
      width: '1300px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result?.success) {
        this.loadPlan();
      }
    });
  }

  ngOnDestroy(): void {
    this.routeSub?.unsubscribe();
  }

  loadPlan(): void {
    const slug = this.planSlug();
    if (!slug) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.adminService.getPlanBySlug(slug).subscribe({
      next: (plan) => {
        this.plan.set(plan);
        this.planId.set(plan.id_pg);
        this.isLoading.set(false);
        this.loadEnjeux(plan.id_pg);
        this.loadOperations(plan.id_pg);
        this.loadPendingSiteRequests(plan.id_pg);
      },
      error: (error) => {
        this.errorMessage.set(error.message || 'Erreur lors du chargement du plan');
        this.isLoading.set(false);
      }
    });
  }

  loadEnjeux(planId: number): void {
    this.enjeuxLoading.set(true);
    this.enjeuService.getPlanEnjeux(planId).subscribe({
      next: (response) => {
        this.enjeuxData.set(response.enjeux);
        this.fcrData.set(response.fcr);
        this.enjeuxLoading.set(false);
      },
      error: () => {
        this.enjeuxLoading.set(false);
      }
    });
  }

  loadOperations(planId: number): void {
    this.operationsLoading.set(true);
    this.enjeuService.getOperationsByPlan(planId).subscribe({
      next: (response) => {
        const subItems: SubAccordion[] = (response.groups || []).map((group: any, index: number) => ({
          id: `action-group-${index}`,
          title: `${group.type_action} (${group.count})`,
          expanded: index === 0,
          items: (group.operations || []).map((op: any) => {
            const code = op.code_operation ? `${op.code_operation} : ` : '';
            return {
              label: `${code}${op.libelle}`,
              enjeuSlug: op.enjeu_slug || undefined,
              ooId: op.oo_id || undefined,
              operationId: op.id_operation,
              statut: op.statut,
            } as OperationSynthItem;
          })
        }));

        this.syntheseAccordions.update(accordions =>
          accordions.map(acc => {
            if (acc.id === 'actions') {
              return { ...acc, hasSubItems: subItems.length > 0, subItems };
            }
            return acc;
          })
        );
        this.operationsLoading.set(false);
      },
      error: () => {
        this.operationsLoading.set(false);
      }
    });
  }

  loadPendingSiteRequests(planId: number): void {
    this.validationService.getValidationRequests({
      request_type: 'plan_site_link',
      status: 'pending'
    }).subscribe({
      next: (response) => {
        // Filter to only show requests for this specific plan
        const planRequests = response.results.filter(
          r => r.target_plan_id === planId
        );
        this.pendingSiteRequests.set(planRequests);
      },
      error: () => {
        // Silently fail - pending requests are not critical
        this.pendingSiteRequests.set([]);
      }
    });
  }

  navigateToEnjeux(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'enjeux']);
    }
  }

  navigateToEnjeuDetail(enjeu: Enjeu): void {
    const slug = this.planSlug();
    if (slug && enjeu.slug) {
      this.router.navigate(['/plans', slug, 'enjeux', enjeu.slug]);
    }
  }

  navigateToEnjeuByOltOo(enjeuId: number): void {
    const enjeu = this.enjeuxData().find(e => e.id_enjeu === enjeuId);
    if (enjeu) {
      this.navigateToEnjeuDetail(enjeu);
    }
  }

  /**
   * #371 — Clic sur un OLT de la vue d'ensemble : ouvrir l'enjeu sur l'onglet
   * « Vision OLT » (et non l'onglet restauré depuis l'état précédent).
   */
  navigateToOltInEnjeu(olt: { enjeu_id: number }): void {
    const enjeu = this.enjeuxData().find(e => e.id_enjeu === olt.enjeu_id);
    const slug = this.planSlug();
    if (enjeu?.slug && slug) {
      this.router.navigate(['/plans', slug, 'enjeux', enjeu.slug], { queryParams: { tab: 'olt' } });
    }
  }

  /**
   * #371 — Clic sur un OO de la vue d'ensemble : ouvrir l'enjeu sur l'onglet
   * « Stratégie opérationnelle » et déplier l'OO ciblé.
   */
  navigateToOoInEnjeu(oo: { enjeu_id: number; id_oo: number }): void {
    const enjeu = this.enjeuxData().find(e => e.id_enjeu === oo.enjeu_id);
    const slug = this.planSlug();
    if (enjeu?.slug && slug) {
      this.router.navigate(['/plans', slug, 'enjeux', enjeu.slug], { queryParams: { tab: 'operations', expandOo: oo.id_oo } });
    }
  }

  navigateToOperation(item: OperationSynthItem): void {
    const slug = this.planSlug();
    if (!slug || !item.enjeuSlug) return;
    const queryParams: Record<string, string | number> = { tab: 'operations' };
    if (item.ooId) {
      queryParams['expandOo'] = item.ooId;
    }
    queryParams['expandOperation'] = item.operationId;
    this.router.navigate(['/plans', slug, 'enjeux', item.enjeuSlug], { queryParams });
  }

  navigateToMindmap(): void {
    const slug = this.planSlug();
    if (slug) {
      this.router.navigate(['/plans', slug, 'tableau-d-arborescence']);
    }
  }

  // ==================== LIFECYCLE ACTIONS ====================

  /**
   * Ouvre une modale de confirmation Material pour une action de cycle de vie.
   * Remplace les `window.confirm()` natifs par le composant unifié, alignant
   * l'UX avec les confirmations de suppression (#267).
   */
  private openLifecycleConfirm(opts: {
    title: string;
    message: string;
    confirmText: string;
    confirmColor: 'primary' | 'warn';
    onConfirm: () => void;
  }): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '500px',
      data: {
        title: opts.title,
        message: opts.message,
        confirmText: opts.confirmText,
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: opts.confirmColor,
      },
    });
    dialogRef.afterClosed().subscribe((confirmed) => {
      if (confirmed) opts.onConfirm();
    });
  }

  confirmValidation(): void {
    const message = '⚠ ' + this.translate.instant('plans.lifecycle.warnings.validateWarning1') + '\n' +
      'ℹ ' + this.translate.instant('plans.lifecycle.warnings.validateWarning2') + '\n' +
      'ℹ ' + this.translate.instant('plans.lifecycle.warnings.validateWarning3');
    this.openLifecycleConfirm({
      title: this.translate.instant('plans.lifecycle.warnings.validateTitle'),
      message,
      confirmText: this.translate.instant('plans.lifecycle.actions.validate'),
      confirmColor: 'primary',
      onConfirm: () => this.validateAfterConfirm(),
    });
  }

  /**
   * #275 / #276 — Aiguillage post-confirmation : si le plan est une
   * modification d'un parent validé ET qu'aucun mi-parcours n'existe encore
   * dans la chaîne, on propose le pop-up "est-ce l'évaluation mi-parcours ?".
   * Sinon, on enchaîne directement sur la validation.
   */
  private validateAfterConfirm(): void {
    const p = this.plan();
    if (!p) return;

    if (!this.shouldPromptMiParcours()) {
      this.changeStatus('valide');
      return;
    }

    const dialogData: MiParcoursPromptDialogData = { planName: p.nom };
    this.dialog
      .open<MiParcoursPromptDialogComponent, MiParcoursPromptDialogData, MiParcoursPromptDialogResult>(
        MiParcoursPromptDialogComponent,
        { data: dialogData, width: '520px', maxWidth: '95vw' }
      )
      .afterClosed()
      .subscribe(result => {
        if (!result || result.isMiParcours === null) return; // annulation
        this.changeStatus('valide', { isMiParcours: result.isMiParcours });
      });
  }

  /**
   * Vrai si on doit proposer le pop-up mi-parcours :
   * - plan_parent est un plan déjà validé (`is_modification` côté serveur),
   * - aucun plan de la chaîne ne porte le drapeau `is_mi_parcours`.
   */
  private shouldPromptMiParcours(): boolean {
    const p = this.plan();
    if (!p?.plan_parent_id) return false;
    // #349 — le plan est déjà désigné comme évaluation mi-parcours dès le
    // brouillon (drapeau posé à la création de l'évaluation) : inutile de
    // redemander à la validation.
    if (p.is_mi_parcours) return false;
    // #250 — Une version étendue est une prolongation, jamais une évaluation
    // mi-parcours : on ne propose pas le pop-up mi-parcours à sa validation.
    if (p.annees_extension && p.annees_extension > 0) return false;
    const chain = p.version_chain ?? [];
    const parent = chain.find(item => item.id_pg === p.plan_parent_id);
    const parentValidated = parent
      ? ['valide', 'modifie', 'archive'].includes(parent.statut)
      : true; // côté serveur, l'absence d'info chaîne ne bloque pas
    if (!parentValidated) return false;
    const hasMiParcours = chain.some(item => item.id_pg !== p.id_pg && item.is_mi_parcours);
    return !hasMiParcours;
  }

  confirmArchive(): void {
    this.openLifecycleConfirm({
      title: this.translate.instant('plans.lifecycle.warnings.archiveTitle'),
      message: '⚠ ' + this.translate.instant('plans.lifecycle.warnings.archiveWarning'),
      confirmText: this.translate.instant('plans.lifecycle.actions.archive'),
      confirmColor: 'warn',
      onConfirm: () => this.changeStatus('archive'),
    });
  }

  confirmToDraft(): void {
    const message = '⚠ ' + this.translate.instant('plans.lifecycle.warnings.toDraftWarning') + '\n\n' +
      this.translate.instant('plans.lifecycle.warnings.toDraftConfirm') + ' ?';
    this.openLifecycleConfirm({
      title: this.translate.instant('plans.lifecycle.warnings.toDraftTitle'),
      message,
      confirmText: this.translate.instant('plans.lifecycle.actions.toDraft'),
      confirmColor: 'warn',
      onConfirm: () => this.changeStatus('draft'),
    });
  }

  confirmReactivate(): void {
    this.openLifecycleConfirm({
      title: this.translate.instant('plans.lifecycle.warnings.reactivateTitle'),
      message: this.translate.instant('plans.lifecycle.warnings.reactivateWarning'),
      confirmText: this.translate.instant('plans.lifecycle.actions.reactivate'),
      confirmColor: 'primary',
      onConfirm: () => this.changeStatus('valide'),
    });
  }

  /**
   * #278 — Ouvre la modale de mise en révision (3 options : créer un brouillon
   * du rang suivant, lier à un plan existant, ou marquer sans lier).
   */
  confirmStartRevision(): void {
    const p = this.plan();
    if (!p) return;

    const dialogRef = this.dialog.open<
      StartRevisionDialogComponent,
      StartRevisionDialogData,
      StartRevisionDialogResult
    >(StartRevisionDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { plan: p },
    });

    dialogRef.afterClosed().subscribe(result => {
      if (!result || result.mode === 'cancel') return;

      // mode 'create' : le brouillon a déjà été créé par la modale, son id est dans nextRangPlanId
      // mode 'link'   : nextRangPlanId est l'id du plan existant choisi
      // mode 'none'   : pas de lien (null)
      this.startRevision(result.nextRangPlanId ?? null);
    });
  }

  /** #278 — Annuler la révision (retire l'indicateur et le lien). */
  confirmEndRevision(): void {
    this.openLifecycleConfirm({
      title: this.translate.instant('plans.lifecycle.warnings.cancelRevisionTitle'),
      message: this.translate.instant('plans.lifecycle.warnings.cancelRevisionWarning'),
      confirmText: this.translate.instant('plans.lifecycle.actions.cancelRevision'),
      confirmColor: 'warn',
      onConfirm: () => this.endRevision(),
    });
  }

  private startRevision(nextRangPlanId?: number | null): void {
    const p = this.plan();
    if (!p) return;
    this.adminService.startPlanRevision(p.id_pg, nextRangPlanId ?? null).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.revisionStarted'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 }
        );
        this.loadPlan();
      },
      error: (err) => {
        const detail = err?.error?.error || this.translate.instant('plans.lifecycle.messages.revisionError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }

  private endRevision(): void {
    const p = this.plan();
    if (!p) return;
    this.adminService.endPlanRevision(p.id_pg).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.revisionEnded'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 }
        );
        this.loadPlan();
      },
      error: (err) => {
        const detail = err?.error?.error || this.translate.instant('plans.lifecycle.messages.revisionError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }

  /** #278 — Indique si le plan est en cours de révision. */
  isPlanInRevision = computed<boolean>(() => {
    const p = this.plan();
    return !!(p && p.en_revision);
  });

  /** #276 — Indique si CE plan porte le drapeau évaluation mi-parcours. */
  isPlanMiParcours = computed<boolean>(() => {
    const p = this.plan();
    return !!(p && p.is_mi_parcours);
  });

  /** #347 — Au moins une information de validation administrative est renseignée. */
  hasCsrpnInfo = computed<boolean>(() => {
    const p = this.plan();
    return !!(p && (p.date_avis_csrpn || p.date_validation_comite || p.date_arrete_pref || p.numero_arrete_pref));
  });

  /** #347 — Récapitulatif des validations administratives (affiché au survol du
   *  badge en haut du plan). Liste CHAQUE étape avec son statut (validé + date /
   *  non commencé), pour donner l'état complet sans ouvrir le menu. */
  csrpnRecapTooltip = computed<string>(() => {
    const fmt = (iso?: string | null) => {
      if (!iso) return null;
      const [y, m, d] = iso.slice(0, 10).split('-');
      return d && m && y ? `${d}/${m}/${y}` : iso;
    };
    const lines = this.adminValidations().map(item => {
      const label = this.translate.instant(item.labelKey);
      if (item.done) {
        const num = item.numero ? ` (n° ${item.numero})` : '';
        const validated = this.translate.instant('plans.adminValidations.validatedOn', { date: fmt(item.date) ?? '' });
        return `${label} : ${validated}${num}`;
      }
      return `${label} : ${this.translate.instant('plans.adminValidations.notStarted')}`;
    });
    return lines.join('\n');
  });

  /** #347 — Compteur « validées / total » affiché sur le badge en haut, pour
   *  visualiser le statut d'un coup d'œil sans survol. */
  adminValidationsSummary = computed<string>(() => {
    const items = this.adminValidations();
    const done = items.filter(i => i.done).length;
    return `${done}/${items.length}`;
  });

  /** #276 — Vrai si la chaîne du plan a déjà une évaluation mi-parcours
   *  (sur n'importe laquelle de ses versions). Bloque la création d'une
   *  nouvelle éval mi-parcours. */
  chainHasMiParcours = computed<boolean>(() => {
    const p = this.plan();
    if (!p) return false;
    const chain = p.version_chain ?? [];
    return chain.some(item => item.is_mi_parcours);
  });

  /** #276 — Vrai si on peut proposer le bouton « Lancer évaluation mi-parcours » :
   *  le plan est validé (`valide`/`modifie`) et aucune éval mi-parcours
   *  n'existe encore dans la chaîne ET aucun brouillon enfant déjà ouvert. */
  canStartMiParcours = computed<boolean>(() => {
    const p = this.plan();
    if (!p) return false;
    const eligible = p.statut === 'valide' || p.statut === 'modifie';
    return eligible && !this.chainHasMiParcours() && !p.has_draft_child;
  });

  /** Vrai si on peut créer une nouvelle version (brouillon) à partir de
   *  ce plan : statut validable + pas de brouillon enfant déjà en cours.
   *  Calculé côté serveur (`can_create_modification`). */
  canCreateNewVersion = computed<boolean>(() => {
    const p = this.plan();
    return !!(p && p.can_create_modification);
  });

  /**
   * #276 — Ouvre la modale de lancement d'une évaluation mi-parcours.
   * 2 options : créer un brouillon EVAL_MI_PARCOURS, ou lier à un brouillon
   * existant. Après confirmation, navigue vers le brouillon.
   */
  openStartMiParcoursDialog(): void {
    const p = this.plan();
    if (!p) return;

    const dialogRef = this.dialog.open<
      StartMiParcoursDialogComponent,
      StartMiParcoursDialogData,
      StartMiParcoursDialogResult
    >(StartMiParcoursDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { plan: p },
    });

    dialogRef.afterClosed().subscribe(result => {
      if (!result || result.mode === 'cancel') return;

      const targetSlug = result.mode === 'create' ? result.newPlanSlug : result.linkedPlanSlug;
      if (!targetSlug) return;

      this.snackBar.open(
        this.translate.instant(
          result.mode === 'create'
            ? 'plans.lifecycle.messages.miParcoursCreated'
            : 'plans.lifecycle.messages.miParcoursLinked'
        ),
        this.translate.instant('common.actions.close'),
        { duration: 3000 }
      );
      this.router.navigate(['/plans', targetSlug]);
    });
  }

  /**
   * Ouvre la modale « Créer une nouvelle version » : duplique le plan validé
   * pour produire un brouillon enfant (même rang, version+1). Workflow
   * standard pour créer une nouvelle modification d'un plan validé.
   */
  openCreateNewVersionDialog(): void {
    const p = this.plan();
    if (!p) return;

    const data: DuplicatePlanDialogData = {
      planId: p.id_pg,
      planName: p.nom,
      planPeriod: this.formatPeriod(p),
      planStatus: this.translate.instant('plans.status.' + p.statut),
      nbSites: (p.sites || []).length,
      planRang: p.rang,
      planVersion: p.version,
    };

    const dialogRef = this.dialog.open(DuplicatePlanDialogComponent, {
      width: '600px',
      maxWidth: '95vw',
      data,
    });

    dialogRef.afterClosed().subscribe((result: DuplicatePlanDialogResult) => {
      if (!result?.confirmed || !result.options) return;
      this.adminService.duplicatePlan(p.id_pg, result.options).subscribe({
        next: (newPlan) => {
          this.snackBar.open(
            this.translate.instant('plans.duplicate.success'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          if (newPlan.slug) {
            this.router.navigate(['/plans', newPlan.slug]);
          }
        },
        error: (err) => {
          // `AdminService.handleError` renvoie un `Error(message)` → lire `err.message`.
          const detail = err?.message || err?.error?.error || this.translate.instant('plans.duplicate.error');
          this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
        },
      });
    });
  }

  /** Formatte la période d'un plan pour les modales (string lisible). */
  private formatPeriod(plan: AdminPlan): string {
    if (plan.annee_debut && plan.annee_fin) {
      return `${plan.annee_debut} - ${plan.annee_fin}`;
    }
    if (plan.annee_debut) return `Depuis ${plan.annee_debut}`;
    if (plan.annee_fin) return `Jusqu'en ${plan.annee_fin}`;
    return '—';
  }

  // ==================== #277 — Workflow CSRPN ====================

  /** Vrai si le site principal du plan est une RNN. Détermine si on passe
   *  par l'étape arrêté préfectoral après la validation comité. */
  isRnn = computed<boolean>(() => this.principalSiteTypeMnemonique() === 'RNN');

  /** #406 — Vrai si le site principal est une réserve naturelle (RNN/RNR/RNC).
   *  La validation administrative n'est proposée que pour ces sites. */
  isReserveNaturelle = computed<boolean>(() =>
    ['RNN', 'RNR', 'RNC'].includes(this.principalSiteTypeMnemonique() ?? ''));

  /** #347 — Validations administratives indépendantes (panneau dédié).
   *  Chaque élément est « validé » dès que sa date est renseignée. L'arrêté
   *  préfectoral n'est présent que pour les RNN/RNR. */
  adminValidations = computed<{
    key: 'avis_csrpn' | 'comite_consultatif' | 'arrete_pref';
    dialogStep: CsrpnStep;
    labelKey: string;
    done: boolean;
    date: string | null;
    numero: string | null;
  }[]>(() => {
    const p = this.plan();
    const items: {
      key: 'avis_csrpn' | 'comite_consultatif' | 'arrete_pref';
      dialogStep: CsrpnStep;
      labelKey: string;
      done: boolean;
      date: string | null;
      numero: string | null;
    }[] = [
      {
        key: 'avis_csrpn', dialogStep: 'csrpn',
        labelKey: 'plans.adminValidations.avisCsrpn',
        done: !!p?.date_avis_csrpn, date: p?.date_avis_csrpn ?? null, numero: null,
      },
      {
        key: 'comite_consultatif', dialogStep: 'comite',
        labelKey: 'plans.adminValidations.comite',
        done: !!p?.date_validation_comite, date: p?.date_validation_comite ?? null, numero: null,
      },
    ];
    if (this.isRnn()) {
      items.push({
        key: 'arrete_pref', dialogStep: 'arrete',
        labelKey: 'plans.adminValidations.arrete',
        done: !!p?.date_arrete_pref, date: p?.date_arrete_pref ?? null,
        numero: p?.numero_arrete_pref ?? null,
      });
    }
    return items;
  });

  /** #347 — Ouvre la modale de saisie pour un élément administratif et enregistre
   *  sa date (et le n° d'arrêté) de façon indépendante du workflow et du statut. */
  openAdminValidationDialog(key: 'avis_csrpn' | 'comite_consultatif' | 'arrete_pref'): void {
    const item = this.adminValidations().find(i => i.key === key);
    if (!item) return;
    this.openCsrpnStepDialog(item.dialogStep).subscribe(result => {
      if (!result) return;
      this.recordAdminValidation(key, result.date, result.numeroArrete ?? null);
    });
  }

  /** #347 — Efface une validation administrative (date → null). */
  clearAdminValidation(key: 'avis_csrpn' | 'comite_consultatif' | 'arrete_pref'): void {
    this.openLifecycleConfirm({
      title: this.translate.instant('plans.adminValidations.clearTitle'),
      message: this.translate.instant('plans.adminValidations.clearMessage'),
      confirmText: this.translate.instant('common.actions.delete'),
      confirmColor: 'warn',
      onConfirm: () => this.recordAdminValidation(key, null, null),
    });
  }

  private recordAdminValidation(
    key: 'avis_csrpn' | 'comite_consultatif' | 'arrete_pref',
    date: string | null,
    numeroArrete?: string | null,
  ): void {
    const p = this.plan();
    if (!p) return;
    this.adminService.recordAdminValidation(p.id_pg, key, date, numeroArrete).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.statusChanged'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadPlan();
      },
      error: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.statusError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      },
    });
  }

  private openCsrpnStepDialog(step: CsrpnStep) {
    const p = this.plan();
    // #347 — pré-remplir la modale avec la date (et le n° d'arrêté) déjà saisis
    // pour cette étape, afin de ne pas perdre l'info après un retour en brouillon.
    const initialDate =
      step === 'csrpn' ? p?.date_avis_csrpn :
      step === 'comite' ? p?.date_validation_comite :
      step === 'arrete' ? p?.date_arrete_pref : null;
    const dialogData: CsrpnStepDialogData = {
      step,
      planName: p?.nom ?? '',
      isRnn: this.isRnn(),
      // #347 — la déclaration mi-parcours se fait à la validation plateforme
      // (confirmValidation), plus à l'étape administrative CSRPN.
      canDeclareMiParcours: false,
      initialDate: initialDate ?? null,
      initialNumeroArrete: step === 'arrete' ? (p?.numero_arrete_pref ?? null) : null,
    };
    return this.dialog
      .open<CsrpnStepDialogComponent, CsrpnStepDialogData, CsrpnStepDialogResult | null>(
        CsrpnStepDialogComponent,
        { data: dialogData, width: '540px', maxWidth: '95vw' },
      )
      .afterClosed();
  }

  /**
   * #250 (refonte) — Ouvre la modale de choix « +1 an » / « +2 ans » pour
   * prolonger la durée du plan. Au choix, l'API crée un brouillon de version
   * étendue (copie du contenu) vers lequel on navigue ensuite.
   */
  openExtendDurationDialog(): void {
    const p = this.plan();
    if (!p || !p.annee_fin) return;

    const dialogData: ExtendDurationDialogData = {
      planName: p.nom,
      anneeFin: p.annee_fin,
      currentExtension: p.annees_extension ?? 0,
    };

    this.dialog
      .open<ExtendDurationDialogComponent, ExtendDurationDialogData, ExtendDurationDialogResult>(
        ExtendDurationDialogComponent,
        { data: dialogData, width: '560px', maxWidth: '95vw' }
      )
      .afterClosed()
      .subscribe(result => {
        if (!result || result.years === null) return;
        this.applyExtension(result.years);
      });
  }

  /**
   * #250 — Retire l'extension d'un plan (annees_extension → 0). Le statut
   * du plan n'est pas modifié : l'extension est un attribut indépendant.
   */
  confirmRevertExtension(): void {
    this.openLifecycleConfirm({
      title: this.translate.instant('plans.lifecycle.warnings.revertExtensionTitle'),
      message: this.translate.instant('plans.lifecycle.warnings.revertExtensionWarning'),
      confirmText: this.translate.instant('plans.lifecycle.actions.revertExtension'),
      confirmColor: 'warn',
      onConfirm: () => this.removeExtension(),
    });
  }

  private removeExtension(): void {
    const p = this.plan();
    if (!p) return;
    this.adminService.removePlanExtension(p.id_pg).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.extensionRemoved'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 }
        );
        this.loadPlan();
      },
      error: (err) => {
        const detail = err?.error?.error || this.translate.instant('plans.lifecycle.messages.extensionError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }

  private applyExtension(years: 1 | 2): void {
    const p = this.plan();
    if (!p) return;
    this.adminService.extendPlanDuration(p.id_pg, years).subscribe({
      next: (newPlan) => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.extensionDraftCreated'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
        // L'API renvoie le brouillon de version étendue : on y navigue pour
        // que le gestionnaire complète les actions/suivis avant validation.
        if (newPlan?.slug) {
          this.router.navigate(['/plans', newPlan.slug]);
        } else {
          this.loadPlan();
        }
      },
      error: (err) => {
        const detail = err?.error?.error || this.translate.instant('plans.lifecycle.messages.extensionError');
        this.snackBar.open(detail, this.translate.instant('common.actions.close'), { duration: 5000 });
      },
    });
  }

  private changeStatus(
    newStatus: PlanStatut,
    options: {
      isMiParcours?: boolean;
    } = {},
  ): void {
    const p = this.plan();
    if (!p) return;

    // Capture la chaîne avant le change-status (#246) : utile uniquement
    // si la transition cible `valide` pour proposer d'archiver le précédent.
    const previousCandidate = newStatus === 'valide'
      ? findPreviousValidatedPlan(p.id_pg, p.version_chain)
      : null;

    this.adminService.changePlanStatus(p.id_pg, newStatus, options).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.statusChanged'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        if (previousCandidate) {
          this.promptArchivePreviousPlan(previousCandidate);
        }
        this.loadPlan();
      },
      error: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.statusError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 }
        );
      },
    });
  }

  /**
   * Affiche la pop-up d'archivage du plan précédent (#246) après validation
   * d'un nouveau plan dans la même chaîne de versions.
   */
  private promptArchivePreviousPlan(previous: PlanVersionChainItem): void {
    const period = (previous.annee_debut && previous.annee_fin)
      ? `${previous.annee_debut} - ${previous.annee_fin}`
      : undefined;

    const dialogData: ArchivePreviousPlanDialogData = {
      previousPlanId: previous.id_pg,
      previousPlanName: previous.nom,
      previousPlanPeriod: period,
    };

    this.dialog
      .open<ArchivePreviousPlanDialogComponent, ArchivePreviousPlanDialogData, ArchivePreviousPlanDialogResult>(
        ArchivePreviousPlanDialogComponent,
        { data: dialogData, width: '520px', maxWidth: '95vw' }
      )
      .afterClosed()
      .subscribe(result => {
        if (!result?.confirmed) return;

        this.adminService.changePlanStatus(previous.id_pg, 'archive').subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('plans.lifecycle.messages.previousArchived'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlan();
          },
          error: () => {
            this.snackBar.open(
              this.translate.instant('plans.lifecycle.messages.previousArchiveError'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
          },
        });
      });
  }

  goBack(): void {
    this.router.navigate(['/plans']);
  }

  toggleAccordion(accordionId: string): void {
    this.syntheseAccordions.update(accordions =>
      accordions.map(acc => ({
        ...acc,
        expanded: acc.id === accordionId ? !acc.expanded : acc.expanded
      }))
    );
  }

  toggleSubAccordion(parentId: string, subId: string): void {
    this.syntheseAccordions.update(accordions =>
      accordions.map(acc => {
        if (acc.id === parentId && acc.subItems) {
          return {
            ...acc,
            subItems: acc.subItems.map(sub => ({
              ...sub,
              expanded: sub.id === subId ? !sub.expanded : sub.expanded
            }))
          };
        }
        return acc;
      })
    );
  }

  // ==================== DOCUMENTS ====================

  openUploadDialog(): void {
    const p = this.plan();
    if (!p) return;

    const data: UploadDocumentDialogData = { planId: p.id_pg };
    const dialogRef = this.dialog.open(UploadDocumentModalComponent, {
      width: '600px',
      maxWidth: '95vw',
      data,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.snackBar.open(
          this.translate.instant('plans.detail.documents.uploadSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadPlan();
      }
    });
  }

  downloadFichier(fichier: PlanFichier): void {
    this.adminService.downloadFichierBlob(fichier.id).subscribe({
      next: (blob) => {
        // Check if the response is a text error (not a real file)
        if (blob.type === 'text/plain' && blob.size < 500) {
          blob.text().then(text => {
            this.snackBar.open(
              text || this.translate.instant('plans.detail.documents.downloadError'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
          });
          return;
        }

        const url = window.URL.createObjectURL(blob);
        const ext = fichier.extension?.toLowerCase().replace('.', '');
        // Open PDFs and images in a new tab, download others
        if (ext === 'pdf' || fichier.is_image) {
          window.open(url, '_blank');
        } else {
          const a = document.createElement('a');
          a.href = url;
          a.download = fichier.nom_fichier;
          a.click();
          window.URL.revokeObjectURL(url);
        }
      },
      error: (err) => {
        // With responseType: 'blob', error body is also a blob — extract text
        if (err.error instanceof Blob) {
          err.error.text().then((text: string) => {
            this.snackBar.open(
              text || this.translate.instant('plans.detail.documents.downloadError'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
          });
        } else {
          this.snackBar.open(
            this.translate.instant('plans.detail.documents.downloadError'),
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
        }
      },
    });
  }

  requestSiteAccess(site: PlanSite): void {
    this.dialog.open(AccessRequestDialogComponent, {
      width: '500px',
      data: {
        type: 'site',
        targetSlug: site.slug,
        targetName: site.nom_site,
        siteMode: 'personal',
      } as AccessRequestDialogData,
    });
  }

  requestSiteOrgLink(site: PlanSite): void {
    this.dialog.open(AccessRequestDialogComponent, {
      width: '500px',
      data: {
        type: 'site',
        targetSlug: site.slug,
        targetName: site.nom_site,
        siteMode: 'organisme',
      } as AccessRequestDialogData,
    });
  }

  /** Ouvre la modale de demande d'accès au plan, option « Référent » présélectionnée. */
  requestBecomeReferent(): void {
    const p = this.plan();
    if (!p) return;
    this.dialog.open(AccessRequestDialogComponent, {
      width: '500px',
      data: {
        type: 'plan',
        targetId: p.id_pg,
        targetName: p.nom,
        hasAccessViaSite: true,
        defaultAsReferent: true,
      } as AccessRequestDialogData,
    });
  }

  // ==================== SITES & USERS MANAGEMENT ====================

  managePlanSites(): void {
    const p = this.plan();
    if (!p) return;

    const data: LinkPlanSiteModalData = {
      plan: {
        id_pg: p.id_pg,
        nom: p.nom,
        sites: p.sites,
      },
    };

    const dialogRef = this.dialog.open(LinkPlanSiteModalComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result?.changed) {
        const message = result.message || this.translate.instant('plans.detail.sitesUpdated');
        this.snackBar.open(
          message,
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadPlan();
      }
    });
  }

  removeSiteFromPlan(site: PlanSite): void {
    const p = this.plan();
    if (!p) return;

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('common.actions.delete'),
        message: this.translate.instant('plans.detail.confirmRemoveSite', { name: site.nom_site }),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn',
      },
    });

    dialogRef.afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      this.adminService.removeSiteFromPlan(p.id_pg, site.id_site).subscribe({
        next: () => {
          this.snackBar.open(
            this.translate.instant('plans.detail.siteRemoved'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.loadPlan();
        },
        error: () => {
          this.snackBar.open(
            this.translate.instant('common.messages.error'),
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
        },
      });
    });
  }

  managePlanUsers(): void {
    const p = this.plan();
    if (!p) return;

    const data: LinkPlanReferentModalData = {
      plan: {
        id_pg: p.id_pg,
        nom: p.nom,
        referents: p.referents,
        membres: p.membres,
      },
    };

    const dialogRef = this.dialog.open(LinkPlanReferentModalComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data,
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result?.changed) {
        this.snackBar.open(
          this.translate.instant('plans.detail.usersUpdated'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.loadPlan();
      }
    });
  }

  // ==================== DOCUMENTS ====================

  deleteFichier(fichier: PlanFichier): void {
    const name = fichier.titre || fichier.nom_fichier;
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('common.actions.delete'),
        message: this.translate.instant('plans.detail.documents.confirmDelete', { name }),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn',
      },
    });

    dialogRef.afterClosed().subscribe((confirmed) => {
      if (!confirmed) return;
      this.adminService.deleteFichier(fichier.id).subscribe({
        next: () => {
          this.snackBar.open(
            this.translate.instant('plans.detail.documents.deleteSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.loadPlan();
        },
        error: () => {
          this.snackBar.open(
            this.translate.instant('plans.detail.documents.deleteError'),
            this.translate.instant('common.actions.close'),
            { duration: 5000 }
          );
        },
      });
    });
  }
}
