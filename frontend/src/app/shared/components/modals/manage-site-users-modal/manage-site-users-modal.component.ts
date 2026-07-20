/**
 * Modal unifie pour gerer les utilisateurs d'un site.
 * Permet d'ajouter des utilisateurs des organismes lies au site.
 */
import { Component, inject, signal, OnInit, computed } from '@angular/core';
import {
  FilterDropdownComponent,
  FilterOptionListComponent,
  FilterPanelDirective,
  FilterOption,
} from '../../filters';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatChipsModule } from '@angular/material/chips';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin, of } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AdminSite, AdminUser, SiteOrganisme } from '../../../../core/models/admin.model';

// Interface pour les utilisateurs assignes au site
interface SiteUserAssignment {
  user: AdminUser;
  referent: boolean;
  isNew?: boolean;
  isModified?: boolean;
  isDeleted?: boolean;
}

// Donnees passees au modal
export interface ManageSiteUsersModalData {
  site: AdminSite;
  existingUsers?: {
    id_role: number;
    nom_complet?: string;
    email: string;
    referent: boolean;
    organisme?: string;
  }[];
}

@Component({
  selector: 'app-manage-site-users-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatInputModule,
    MatSelectModule,
    MatCheckboxModule,
    MatIconModule,
    MatChipsModule,
    MatTabsModule,
    FilterDropdownComponent,
    FilterOptionListComponent,
    FilterPanelDirective,
    MatTooltipModule,
    TranslateModule
  ],
  templateUrl: './manage-site-users-modal.component.html',
  styleUrl: './manage-site-users-modal.component.scss'
})
export class ManageSiteUsersModalComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly dialogRef = inject(MatDialogRef<ManageSiteUsersModalComponent>);
  private readonly translate = inject(TranslateService);
  readonly data = inject<ManageSiteUsersModalData>(MAT_DIALOG_DATA);

  readonly isLoading = signal(false);
  readonly isLoadingData = signal(true);
  readonly errorMessage = signal<string | null>(null);
  readonly successMessage = signal<string | null>(null);

  // Organismes lies au site
  readonly linkedOrganismes = signal<SiteOrganisme[]>([]);

  // Tous les utilisateurs disponibles (des organismes lies)
  readonly allAvailableUsers = signal<AdminUser[]>([]);

  // Utilisateurs assignes au site
  readonly userAssignments = signal<SiteUserAssignment[]>([]);

  // Filtre par organisme
  readonly selectedOrganismeFilter = signal<number | null>(null);

  // Recherche utilisateur
  readonly userSearchControl = new FormControl('');
  readonly filteredUsers = signal<AdminUser[]>([]);

  // Nouveau utilisateur a ajouter
  readonly newUserReferent = signal(false);

  // Utilisateurs visibles (non supprimes)
  readonly visibleAssignments = computed(() => {
    return this.userAssignments().filter(a => !a.isDeleted);
  });

  // Liste triée : nouveaux utilisateurs en haut (revue design Amandine)
  readonly sortedAssignments = computed(() => {
    return [...this.userAssignments()].sort((a, b) => {
      if (a.isNew && !b.isNew) return -1;
      if (!a.isNew && b.isNew) return 1;
      if (a.isModified && !b.isModified) return -1;
      if (!a.isModified && b.isModified) return 1;
      // Sinon par nom
      const an = ((a.user.nom_role || '') + ' ' + (a.user.prenom_role || '')).toLowerCase();
      const bn = ((b.user.nom_role || '') + ' ' + (b.user.prenom_role || '')).toLowerCase();
      return an.localeCompare(bn);
    });
  });

  // Utilisateurs disponibles pour ajout (pas deja assignes)
  readonly availableUsersForAdd = computed(() => {
    const assignedIds = new Set(
      this.userAssignments()
        .filter(a => !a.isDeleted)
        .map(a => a.user.id_role)
    );
    let users = this.allAvailableUsers().filter(u => !assignedIds.has(u.id_role));

    // Filtrer par organisme si selectionne
    const orgFilter = this.selectedOrganismeFilter();
    if (orgFilter !== null) {
      users = users.filter(u => u.organisme?.id_organisme === orgFilter);
    }

    return users;
  });

  // Y a-t-il des changements?
  readonly hasChanges = computed(() => {
    return this.userAssignments().some(a => a.isNew || a.isModified || a.isDeleted);
  });

  ngOnInit(): void {
    this.loadData();

    // Filtrer les utilisateurs lors de la saisie
    this.userSearchControl.valueChanges.subscribe(value => {
      this.filterUsers(value);
    });
  }

  private loadData(): void {
    this.isLoadingData.set(true);

    // Recuperer les organismes lies au site
    const organismes = this.data.site.organismes || [];
    this.linkedOrganismes.set(organismes);

    if (organismes.length === 0) {
      this.allAvailableUsers.set([]);
      this.initUserAssignments([]);
      this.isLoadingData.set(false);
      return;
    }

    // Charger les utilisateurs de tous les organismes lies
    const orgIds = organismes.map(o => o.id_organisme);

    // On charge tous les utilisateurs puis on filtre
    this.adminService.getUsers({ page_size: 500 }).pipe(
      catchError(() => of({ results: [] }))
    ).subscribe({
      next: (response) => {
        // Filtrer pour ne garder que les utilisateurs des organismes lies
        const filteredUsers = response.results.filter(user =>
          user.organisme && orgIds.includes(user.organisme.id_organisme)
        );
        this.allAvailableUsers.set(filteredUsers);
        this.initUserAssignments(response.results);
        this.filterUsers('');
        this.isLoadingData.set(false);
      },
      error: () => {
        this.isLoadingData.set(false);
        this.errorMessage.set(this.translate.instant('common.messages.error'));
      }
    });
  }

  private initUserAssignments(allUsers: AdminUser[]): void {
    const existingUsers = this.data.existingUsers || [];

    const assignments: SiteUserAssignment[] = existingUsers.map(eu => {
      // Chercher l'utilisateur complet
      const fullUser = allUsers.find(u => u.id_role === eu.id_role);
      return {
        user: fullUser || {
          id_role: eu.id_role,
          email: eu.email,
          nom_role: eu.nom_complet?.split(' ').slice(1).join(' '),
          prenom_role: eu.nom_complet?.split(' ')[0],
          role_level: 'utilisateur' as const,
          active: true
        } as AdminUser,
        referent: eu.referent,
        isNew: false,
        isModified: false,
        isDeleted: false
      };
    });

    this.userAssignments.set(assignments);
  }

  private filterUsers(value: string | null): void {
    const available = this.availableUsersForAdd();
    if (!value) {
      this.filteredUsers.set(available);
      return;
    }
    const query = value.toLowerCase();
    const filtered = available.filter(user =>
      (user.nom_role?.toLowerCase().includes(query) || false) ||
      (user.prenom_role?.toLowerCase().includes(query) || false) ||
      user.email.toLowerCase().includes(query)
    );
    this.filteredUsers.set(filtered);
  }

  displayUser(user: AdminUser | null): string {
    if (!user) return '';
    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role} (${user.email})`;
    }
    return user.email;
  }

  getUserDisplayName(user: AdminUser): string {
    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role}`;
    }
    return user.email;
  }

  getUserOrganisme(user: AdminUser): string {
    return user.organisme?.nom_organisme || '-';
  }

  onOrganismeFilterChange(orgId: number | null): void {
    this.selectedOrganismeFilter.set(orgId);
    this.filterUsers(this.userSearchControl.value);
  }

  /** #592 — options du filtre organisme, au format du kit UI. */
  readonly organismeFilterOptions = computed<FilterOption<number>[]>(() =>
    this.linkedOrganismes().map((o) => ({ value: o.id_organisme, label: o.nom_organisme })),
  );

  /** Adaptation entre le `number | null` du composant et le tableau du kit UI. */
  readonly organismeFilterSelection = computed<number[]>(() => {
    const id = this.selectedOrganismeFilter();
    return id === null ? [] : [id];
  });

  /** Libellé de l'organisme filtré, affiché sur le déclencheur fermé. */
  readonly organismeFilterSummary = computed<string>(() => {
    const id = this.selectedOrganismeFilter();
    return this.organismeFilterOptions().find((o) => o.value === id)?.label ?? '';
  });

  onOrganismeFilterSelection(values: number[]): void {
    this.onOrganismeFilterChange(values[0] ?? null);
  }

  addUser(user: AdminUser): void {
    const assignments = [...this.userAssignments()];
    assignments.push({
      user,
      referent: this.newUserReferent(),
      isNew: true,
      isModified: false,
      isDeleted: false
    });
    this.userAssignments.set(assignments);

    // Reset
    this.userSearchControl.setValue('');
    this.newUserReferent.set(false);
    this.filterUsers('');

    const userName = this.getUserDisplayName(user);
    this.successMessage.set(
      this.translate.instant('modals.manageSiteUsers.messages.userAdded', { name: userName })
    );
    setTimeout(() => this.successMessage.set(null), 3000);
  }

  removeUser(assignment: SiteUserAssignment): void {
    const assignments = [...this.userAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      if (assignment.isNew) {
        assignments.splice(index, 1);
      } else {
        assignments[index] = { ...assignments[index], isDeleted: true };
      }
      this.userAssignments.set(assignments);
      this.filterUsers(this.userSearchControl.value);
    }
  }

  restoreUser(assignment: SiteUserAssignment): void {
    const assignments = [...this.userAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      assignments[index] = { ...assignments[index], isDeleted: false };
      this.userAssignments.set(assignments);
      this.filterUsers(this.userSearchControl.value);
    }
  }

  toggleReferent(assignment: SiteUserAssignment): void {
    const assignments = [...this.userAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      assignments[index] = {
        ...assignments[index],
        referent: !assignments[index].referent,
        isModified: !assignments[index].isNew
      };
      this.userAssignments.set(assignments);
    }
  }

  onSave(): void {
    const siteSlug = this.data.site.slug;
    const toAdd = this.userAssignments().filter(a => a.isNew && !a.isDeleted);
    const toUpdate = this.userAssignments().filter(a => a.isModified && !a.isNew && !a.isDeleted);
    const toDelete = this.userAssignments().filter(a => a.isDeleted && !a.isNew);

    if (toAdd.length === 0 && toUpdate.length === 0 && toDelete.length === 0) {
      this.dialogRef.close({ success: true, changed: false });
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const allOperations = [
      ...toAdd.map(a => ({ type: 'add' as const, assignment: a })),
      ...toUpdate.map(a => ({ type: 'update' as const, assignment: a })),
      ...toDelete.map(a => ({ type: 'delete' as const, assignment: a }))
    ];

    let completed = 0;
    let hasError = false;

    allOperations.forEach(op => {
      if (op.type === 'delete') {
        this.adminService.removeUserFromSite(siteSlug, op.assignment.user.id_role).subscribe({
          next: () => {
            completed++;
            if (completed === allOperations.length && !hasError) {
              this.isLoading.set(false);
              this.dialogRef.close({ success: true, changed: true });
            }
          },
          error: (error: Error) => {
            hasError = true;
            this.isLoading.set(false);
            this.errorMessage.set(error.message);
          }
        });
      } else {
        this.adminService.assignUserToSite(
          siteSlug,
          op.assignment.user.id_role,
          op.assignment.referent
        ).subscribe({
          next: () => {
            completed++;
            if (completed === allOperations.length && !hasError) {
              this.isLoading.set(false);
              this.dialogRef.close({ success: true, changed: true });
            }
          },
          error: (error: Error) => {
            hasError = true;
            this.isLoading.set(false);
            this.errorMessage.set(error.message);
          }
        });
      }
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
