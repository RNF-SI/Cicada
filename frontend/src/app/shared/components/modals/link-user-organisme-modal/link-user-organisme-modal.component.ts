import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { AdminService } from '../../../../core/services/admin.service';
import { AdminOrganisme, AdminUser } from '../../../../core/models/admin.model';

// Interface for a user assignment in the modal
interface UserAssignment {
  user: AdminUser;
  isNew?: boolean;  // true if just added, not yet saved
  isDeleted?: boolean;  // true if marked for removal from organisme
}

export interface LinkUserOrganismeModalData {
  user?: AdminUser; // If provided, select organisme for this user
  organisme?: AdminOrganisme; // If provided, manage users for this organisme
}

@Component({
  selector: 'app-link-user-organisme-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatAutocompleteModule,
    MatSelectModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatInputModule,
    MatIconModule
  ],
  templateUrl: './link-user-organisme-modal.component.html',
  styleUrl: './link-user-organisme-modal.component.scss'
})
export class LinkUserOrganismeModalComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly dialogRef = inject(MatDialogRef<LinkUserOrganismeModalComponent>);
  readonly data = inject<LinkUserOrganismeModalData>(MAT_DIALOG_DATA);

  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // All available users
  allUsers = signal<AdminUser[]>([]);

  // Users currently assigned to organisme (with modifications tracking)
  userAssignments = signal<UserAssignment[]>([]);

  // For select-organisme mode (when user is provided)
  organismes = signal<AdminOrganisme[]>([]);
  selectedOrganismeUuid: string | null = null;

  // For adding new user (select-user mode)
  userControl = new FormControl<AdminUser | string>('');
  filteredUsers = signal<AdminUser[]>([]);

  get mode(): 'select-organisme' | 'select-user' {
    return this.data?.user ? 'select-organisme' : 'select-user';
  }

  get hasChanges(): boolean {
    return this.userAssignments().some(a => a.isNew || a.isDeleted);
  }

  get visibleAssignments(): UserAssignment[] {
    return this.userAssignments().filter(a => !a.isDeleted);
  }

  get availableUsersForAdd(): AdminUser[] {
    const assignedIds = new Set(this.userAssignments()
      .filter(a => !a.isDeleted)
      .map(a => a.user.id_role));
    return this.allUsers().filter(u => !assignedIds.has(u.id_role));
  }

  ngOnInit(): void {
    if (this.mode === 'select-user') {
      this.loadUsersAndAssignments();
      this.userControl.valueChanges.subscribe(value => {
        this.filterAvailableUsers(value);
      });
    } else {
      this.selectedOrganismeUuid = this.data.user?.organisme?.uuid_organisme || null;
      this.loadOrganismes();
    }
  }

  private loadUsersAndAssignments(): void {
    this.isLoadingData.set(true);

    // Load all users
    this.adminService.getUsers().subscribe({
      next: (response) => {
        this.allUsers.set(response.results);

        // Load existing assignments from organisme
        if (this.data.organisme?.id_organisme) {
          this.adminService.getOrganismeUsers(this.data.organisme.id_organisme).subscribe({
            next: (users) => {
              const existingAssignments: UserAssignment[] = users.map(user => ({
                user,
                isNew: false,
                isDeleted: false
              }));

              this.userAssignments.set(existingAssignments);
              this.filterAvailableUsers('');
              this.isLoadingData.set(false);
            },
            error: (error: Error) => {
              // If no users yet, that's OK
              this.userAssignments.set([]);
              this.filterAvailableUsers('');
              this.isLoadingData.set(false);
            }
          });
        } else {
          this.filterAvailableUsers('');
          this.isLoadingData.set(false);
        }
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  private loadOrganismes(): void {
    this.isLoadingData.set(true);
    this.adminService.getOrganismes().subscribe({
      next: (response) => {
        this.organismes.set(response.results);
        this.isLoadingData.set(false);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  private filterAvailableUsers(value: AdminUser | string | null): void {
    const available = this.availableUsersForAdd;
    if (!value) {
      this.filteredUsers.set(available);
      return;
    }
    const query = typeof value === 'string' ? value.toLowerCase() : value.email.toLowerCase();
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

  getUserInitials(user: AdminUser): string {
    const first = user.prenom_role?.charAt(0) || '';
    const last = user.nom_role?.charAt(0) || '';
    return first + last || user.email.charAt(0).toUpperCase();
  }

  getUserDisplayName(user: AdminUser): string {
    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role}`;
    }
    return user.email;
  }

  // Add a new user to the list
  addUser(user: AdminUser): void {
    const assignments = [...this.userAssignments()];
    assignments.push({
      user,
      isNew: true,
      isDeleted: false
    });
    this.userAssignments.set(assignments);

    // Reset the form
    this.userControl.setValue('');
    this.filterAvailableUsers('');

    this.successMessage.set(`Utilisateur "${this.getUserDisplayName(user)}" ajoute a la liste`);
    setTimeout(() => this.successMessage.set(null), 3000);
  }

  // Remove a user from the list
  removeUser(assignment: UserAssignment): void {
    const assignments = [...this.userAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      if (assignment.isNew) {
        // Just remove it from the list
        assignments.splice(index, 1);
      } else {
        // Mark for deletion (will set organisme to null)
        assignments[index] = { ...assignments[index], isDeleted: true };
      }
      this.userAssignments.set(assignments);
      this.filterAvailableUsers(this.userControl.value);
    }
  }

  // Restore a user marked for deletion
  restoreUser(assignment: UserAssignment): void {
    const assignments = [...this.userAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      assignments[index] = { ...assignments[index], isDeleted: false };
      this.userAssignments.set(assignments);
      this.filterAvailableUsers(this.userControl.value);
    }
  }

  // Save all changes
  onSave(): void {
    if (this.mode === 'select-organisme') {
      this.saveSelectOrganisme();
    } else {
      this.saveSelectUser();
    }
  }

  private saveSelectOrganisme(): void {
    if (!this.data.user) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.adminService.assignOrganismeToUser(
      this.data.user.id_role,
      this.selectedOrganismeUuid
    ).subscribe({
      next: (user) => {
        this.isLoading.set(false);
        this.dialogRef.close({ success: true, user });
      },
      error: (error: Error) => {
        this.isLoading.set(false);
        this.errorMessage.set(error.message);
      }
    });
  }

  private saveSelectUser(): void {
    if (!this.data.organisme) return;

    const organismeUuid = this.data.organisme.uuid_organisme;
    const toAdd = this.userAssignments().filter(a => a.isNew && !a.isDeleted);
    const toDelete = this.userAssignments().filter(a => a.isDeleted && !a.isNew);

    if (toAdd.length === 0 && toDelete.length === 0) {
      this.dialogRef.close({ success: true, changed: false });
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    // Process all operations
    this.processOperations(organismeUuid, toAdd, toDelete);
  }

  private processOperations(
    organismeUuid: string | undefined,
    toAdd: UserAssignment[],
    toDelete: UserAssignment[]
  ): void {
    const allOperations = [
      ...toAdd.map(a => ({ type: 'add' as const, assignment: a })),
      ...toDelete.map(a => ({ type: 'delete' as const, assignment: a }))
    ];

    if (allOperations.length === 0) {
      this.isLoading.set(false);
      this.dialogRef.close({ success: true, changed: true });
      return;
    }

    let completed = 0;
    let hasError = false;

    allOperations.forEach(op => {
      if (op.type === 'delete') {
        // Remove user from organisme (set to null)
        this.adminService.assignOrganismeToUser(op.assignment.user.id_role, null).subscribe({
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
            this.errorMessage.set(`Erreur lors de la suppression: ${error.message}`);
          }
        });
      } else {
        // Add user to organisme
        this.adminService.assignOrganismeToUser(op.assignment.user.id_role, organismeUuid || null).subscribe({
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
            this.errorMessage.set(`Erreur: ${error.message}`);
          }
        });
      }
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
