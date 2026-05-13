import { Component, signal, computed, inject, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subscription } from 'rxjs';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { SectionTitleComponent } from '../../shared/components/section-title/section-title.component';
import { PlanSidebarComponent } from './shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../core/services/admin.service';
import { AuthService } from '../../core/services/auth.service';
import { EnjeuService } from '../../core/services/enjeu.service';
import { ValidationService } from '../../core/services/validation.service';
import { ValidationRequestListItem } from '../../core/models/notification.model';
import { AdminPlan, PlanFichier, PlanMembre, PlanSite, PlanStatut, PlanVersionChainItem } from '../../core/models/admin.model';
import { PlanVersionTimelineComponent } from '../../shared/components/plan-version-timeline/plan-version-timeline.component';
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
    TranslateModule,
    HeaderComponent,
    SectionTitleComponent,
    PlanSidebarComponent,
    PlanVersionTimelineComponent,
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

  // Enjeux/FCR data for synthèse and sidebar
  enjeuxData = signal<Enjeu[]>([]);
  fcrData = signal<Enjeu[]>([]);
  enjeuxLoading = signal(false);

  // Aggregated OLT/OO across all enjeux
  allOlts = computed(() => {
    return this.enjeuxData().flatMap(enjeu =>
      (enjeu.objectifs_long_terme || []).map(olt => ({
        ...olt,
        enjeu_libelle: enjeu.libelle,
        enjeu_id: enjeu.id_enjeu
      }))
    );
  });

  allOos = computed(() => {
    const seen = new Set<number>();
    return this.enjeuxData().flatMap(enjeu =>
      (enjeu.facteurs_influence || []).flatMap(fi =>
        (fi.pressions || []).flatMap(p =>
          (p.objectifs_operationnels || [])
            .filter(oo => {
              if (seen.has(oo.id_oo)) return false;
              seen.add(oo.id_oo);
              return true;
            })
            .map(oo => ({
              ...oo,
              enjeu_libelle: enjeu.libelle,
              enjeu_id: enjeu.id_enjeu
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

  // Permissions cycle de vie: référent du plan, admin_og ou super_admin (PAS redacteur_principal)
  canManageLifecycle = computed(() => {
    if (this.authService.isRedacteurPrincipal()) return false;
    if (this.authService.isSuperAdmin() || this.authService.isAdminOrganisme()) {
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
   * Plan éditable (#248). Renvoie true pour `draft` et `etendu` (#250 — un plan
   * prolongé doit rester modifiable pour les actions sur les années ajoutées).
   * Conserve le nom historique `isPlanDraft` pour limiter le diff.
   */
  isPlanDraft = computed(() => {
    const s = this.plan()?.statut;
    return s === 'draft' || s === 'etendu';
  });

  // Accordéons de la section Synthèse
  syntheseAccordions = signal<SyntheseAccordion[]>([
    {
      id: 'enjeux',
      title: 'Enjeux et Facteurs clés de réussite',
      colorClass: 'terra-cotta',
      expanded: false
    },
    {
      id: 'objectifs-lt',
      title: 'Objectifs long terme',
      colorClass: 'terra-cotta',
      expanded: false
    },
    {
      id: 'objectifs-op',
      title: 'Objectifs opérationnels',
      colorClass: 'terra-cotta',
      expanded: false
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
      onConfirm: () => this.changeStatus('valide'),
    });
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
   * #250 — Ouvre la modale de choix « +1 an » / « +2 ans » pour prolonger
   * la durée du plan. Appel API au choix de l'utilisateur.
   */
  openExtendDurationDialog(): void {
    const p = this.plan();
    if (!p || !p.annee_fin) return;

    const dialogData: ExtendDurationDialogData = {
      planName: p.nom,
      anneeFin: p.annee_fin,
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
   * #250 — Étendu → Validé : annule l'extension en repassant en statut validé.
   * Le champ `annees_extension` est conservé jusqu'à la prochaine extension.
   */
  confirmRevertExtension(): void {
    this.openLifecycleConfirm({
      title: this.translate.instant('plans.lifecycle.warnings.revertExtensionTitle'),
      message: this.translate.instant('plans.lifecycle.warnings.revertExtensionWarning'),
      confirmText: this.translate.instant('plans.lifecycle.actions.revertExtension'),
      confirmColor: 'warn',
      onConfirm: () => this.changeStatus('valide'),
    });
  }

  private applyExtension(years: 1 | 2): void {
    const p = this.plan();
    if (!p) return;
    this.adminService.extendPlanDuration(p.id_pg, years).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('plans.lifecycle.messages.extensionApplied', { years }),
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

  private changeStatus(newStatus: PlanStatut): void {
    const p = this.plan();
    if (!p) return;

    // Capture la chaîne avant le change-status (#246) : utile uniquement
    // si la transition cible `valide` pour proposer d'archiver le précédent.
    const previousCandidate = newStatus === 'valide'
      ? findPreviousValidatedPlan(p.id_pg, p.version_chain)
      : null;

    this.adminService.changePlanStatus(p.id_pg, newStatus).subscribe({
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
