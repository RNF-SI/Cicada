import { Component, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA, MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatChipsModule } from '@angular/material/chips';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDividerModule } from '@angular/material/divider';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { debounceTime, Subject } from 'rxjs';

import { AdminService } from '../../../../core/services/admin.service';
import { ValidationService } from '../../../../core/services/validation.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AdminSite } from '../../../../core/models/admin.model';
import { SiteFormModalComponent, SiteFormModalData } from '../site-form-modal/site-form-modal.component';

export interface FindOrCreateSiteModalData {
  // Données optionnelles
}

interface SearchableSite extends AdminSite {
  canRequestAccess: boolean;
  hasAccess: boolean;
  hasPendingRequest: boolean;
  // Pour les sites d'autres organismes
  canRequestOrgLink: boolean;
  hasPendingOrgLink: boolean;
  isOtherOrg: boolean;
}

@Component({
  selector: 'app-find-or-create-site-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatDividerModule,
    MatCheckboxModule,
    TranslateModule
  ],
  templateUrl: './find-or-create-site-modal.component.html',
  styleUrl: './find-or-create-site-modal.component.scss'
})
export class FindOrCreateSiteModalComponent {
  private readonly adminService = inject(AdminService);
  private readonly validationService = inject(ValidationService);
  private readonly authService = inject(AuthService);
  private readonly translate = inject(TranslateService);
  private readonly dialogRef = inject(MatDialogRef<FindOrCreateSiteModalComponent>);
  private readonly dialog = inject(MatDialog);
  readonly data = inject<FindOrCreateSiteModalData>(MAT_DIALOG_DATA, { optional: true });

  // État
  readonly searchTerm = signal('');
  readonly isSearching = signal(false);
  readonly isSubmitting = signal(false);
  readonly allSites = signal<SearchableSite[]>([]);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);

  // État pour le formulaire de demande de lien
  readonly expandedOrgLinkSite = signal<number | null>(null);
  readonly orgLinkJustification = signal('');

  // Map pour stocker le choix "référent" par site
  readonly referentRequests = new Map<number, boolean>();

  // Subject pour le debounce de la recherche
  private searchSubject = new Subject<string>();

  // Sites filtrés par la recherche
  readonly filteredSites = computed(() => {
    const term = this.searchTerm().toLowerCase().trim();
    if (term.length < 2) return [];

    return this.allSites()
      .filter(s => s.nom_site.toLowerCase().includes(term))
      .slice(0, 20); // Augmenté à 20 résultats
  });

  // Sites de mon organisme (filtrés)
  readonly mySites = computed(() => {
    return this.filteredSites().filter(s => !s.isOtherOrg);
  });

  // Sites d'autres organismes (filtrés)
  readonly otherOrgSites = computed(() => {
    return this.filteredSites().filter(s => s.isOtherOrg);
  });

  // Indique si on peut créer un nouveau site (toujours possible si l'utilisateur a un organisme)
  readonly canCreateNew = computed(() => {
    return this.hasOrganisme();
  });

  // L'utilisateur a un organisme
  readonly hasOrganisme = computed(() => {
    return !!this.authService.currentUser()?.organisme?.id_organisme;
  });

  constructor() {
    this.loadAllSites();

    // Configurer le debounce pour la recherche
    this.searchSubject.pipe(debounceTime(300)).subscribe(term => {
      this.searchTerm.set(term);
    });
  }

  /**
   * Charge tous les sites accessibles (y compris ceux d'autres organismes)
   */
  private loadAllSites(): void {
    this.isSearching.set(true);
    const currentUser = this.authService.currentUser();
    const userOrgId = currentUser?.organisme?.id_organisme;

    // Utiliser search_all pour avoir accès à tous les sites
    this.adminService.searchAllSites({ page_size: 500 }).subscribe({
      next: (response) => {
        // Enrichir les sites avec les informations d'accès
        const enrichedSites: SearchableSite[] = response.results.map(site => {
          const isUserLinked = (site as any).users?.some(
            (u: any) => u.id_role === currentUser?.id
          );
          const isOrgSite = site.organismes?.some(o => o.id_organisme === userOrgId);
          const isOtherOrg = !isOrgSite && userOrgId !== undefined;

          return {
            ...site,
            hasAccess: isUserLinked || false,
            hasPendingRequest: false, // Sera mis à jour avec les demandes
            canRequestAccess: !isUserLinked && isOrgSite,
            // Site d'un autre organisme - peut demander le lien
            isOtherOrg,
            canRequestOrgLink: isOtherOrg && !!userOrgId,
            hasPendingOrgLink: false
          } as SearchableSite;
        });

        // Charger les demandes en cours pour mettre à jour hasPendingRequest
        this.validationService.getMyRequests().subscribe({
          next: (requests) => {
            const pendingAccessRequests = requests.filter(
              r => r.request_type === 'site_access' && r.status === 'pending'
            );
            const pendingOrgLinkRequests = requests.filter(
              r => r.request_type === 'site_org_link' && r.status === 'pending'
            );

            enrichedSites.forEach(site => {
              // Demandes d'accès - matcher par ID du site
              const hasPendingAccess = pendingAccessRequests.some(
                r => r.target_site_id === site.id_site
              );
              site.hasPendingRequest = hasPendingAccess;
              if (hasPendingAccess) {
                site.canRequestAccess = false;
              }

              // Demandes de lien site-organisme - matcher par ID du site
              const hasPendingOrgLink = pendingOrgLinkRequests.some(
                r => r.target_site_id === site.id_site
              );
              site.hasPendingOrgLink = hasPendingOrgLink;
              if (hasPendingOrgLink) {
                site.canRequestOrgLink = false;
              }
            });

            this.allSites.set(enrichedSites);
            this.isSearching.set(false);
          },
          error: () => {
            this.allSites.set(enrichedSites);
            this.isSearching.set(false);
          }
        });
      },
      error: () => {
        this.isSearching.set(false);
        this.errorMessage.set(this.translate.instant('common.messages.error'));
      }
    });
  }

  /**
   * Gère le changement de recherche
   */
  onSearchChange(event: Event): void {
    const value = (event.target as HTMLInputElement).value;
    this.searchSubject.next(value);
    this.errorMessage.set(null);
    this.successMessage.set(null);
    // Fermer le formulaire de lien si ouvert
    this.cancelOrgLinkRequest();
  }

  /**
   * Gère le changement de la checkbox référent
   */
  onReferentChange(site: SearchableSite, checked: boolean): void {
    this.referentRequests.set(site.id_site, checked);
  }

  /**
   * Vérifie si la demande comme référent est cochée pour un site
   */
  isReferentRequest(site: SearchableSite): boolean {
    return this.referentRequests.get(site.id_site) || false;
  }

  /**
   * Demande l'accès à un site existant
   */
  requestAccess(site: SearchableSite): void {
    if (!site.canRequestAccess) return;

    this.isSubmitting.set(true);
    this.errorMessage.set(null);

    const asReferent = this.referentRequests.get(site.id_site) || false;

    this.validationService.requestSiteAccess(site.slug, {
      justification: this.translate.instant('sites.findOrCreate.autoMessage'),
      request_as_referent: asReferent
    }).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        const messageKey = asReferent
          ? 'sites.findOrCreate.accessRequestedAsReferent'
          : 'sites.findOrCreate.accessRequested';
        this.successMessage.set(
          this.translate.instant(messageKey, { name: site.nom_site })
        );
        // Recharger les données pour actualiser l'affichage
        this.loadAllSites();
      },
      error: (err: { message?: string }) => {
        this.isSubmitting.set(false);
        this.errorMessage.set(err.message || this.translate.instant('common.messages.error'));
      }
    });
  }

  /**
   * Ouvre le formulaire de demande de lien site-organisme
   */
  startOrgLinkRequest(site: SearchableSite): void {
    this.expandedOrgLinkSite.set(site.id_site);
    this.orgLinkJustification.set('');
    this.errorMessage.set(null);
    this.successMessage.set(null);
  }

  /**
   * Annule la demande de lien site-organisme
   */
  cancelOrgLinkRequest(): void {
    this.expandedOrgLinkSite.set(null);
    this.orgLinkJustification.set('');
  }

  /**
   * Gère le changement de texte de justification
   */
  onOrgLinkJustificationChange(event: Event): void {
    const value = (event.target as HTMLTextAreaElement).value;
    this.orgLinkJustification.set(value);
  }

  /**
   * Soumet la demande de lien site-organisme
   */
  submitOrgLinkRequest(site: SearchableSite): void {
    if (!site.canRequestOrgLink) return;
    const justification = this.orgLinkJustification().trim();
    if (!justification) return;

    this.isSubmitting.set(true);
    this.errorMessage.set(null);

    this.validationService.requestSiteOrgLink(site.slug, {
      justification
    }).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        this.successMessage.set(
          this.translate.instant('sites.findOrCreate.orgLinkRequested', { name: site.nom_site })
        );
        // Fermer le formulaire et recharger les données
        this.cancelOrgLinkRequest();
        this.loadAllSites();
      },
      error: (err: { message?: string }) => {
        this.isSubmitting.set(false);
        this.errorMessage.set(err.message || this.translate.instant('common.messages.error'));
      }
    });
  }

  /**
   * Ouvre le modal de création de site
   */
  createNewSite(): void {
    const currentUser = this.authService.currentUser();
    if (!currentUser?.organisme?.id_organisme) {
      this.errorMessage.set(this.translate.instant('sites.createSite.noOrganisme'));
      return;
    }

    // Ouvrir le dialogue de création de site
    const createDialogRef = this.dialog.open(SiteFormModalComponent, {
      width: '1300px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: {
        organismeId: currentUser.organisme.id_organisme,
        principal: false
      } as SiteFormModalData
    });

    createDialogRef.afterClosed().subscribe(result => {
      // Fermer ce dialogue avec true si un site a été créé
      // pour que le parent recharge les données
      this.dialogRef.close(result ? true : false);
    });
  }

  /**
   * Ferme le dialogue
   */
  close(): void {
    this.dialogRef.close(this.successMessage() ? true : false);
  }
}
