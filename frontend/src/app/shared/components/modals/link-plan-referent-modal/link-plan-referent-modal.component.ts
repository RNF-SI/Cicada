import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormControl } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { AdminService } from '../../../../core/services/admin.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AdminUser } from '../../../../core/models/admin.model';

// Interface for referent linked to plan
interface PlanReferentInfo {
  id_role: number;
  email: string;
  nom_role?: string;
  prenom_role?: string;
  nom_complet?: string;
}

// Interface for a referent assignment in the modal
interface ReferentAssignment {
  user: PlanReferentInfo;
  isNew?: boolean;
  isDeleted?: boolean;
}

export interface LinkPlanReferentModalData {
  plan: {
    id_pg: number;
    nom: string;
    referents?: PlanReferentInfo[];
  };
}

@Component({
  selector: 'app-link-plan-referent-modal',
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
    MatIconModule,
    TranslateModule
  ],
  templateUrl: './link-plan-referent-modal.component.html',
  styleUrl: './link-plan-referent-modal.component.scss'
})
export class LinkPlanReferentModalComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly dialogRef = inject(MatDialogRef<LinkPlanReferentModalComponent>);
  private readonly translate = inject(TranslateService);
  readonly data = inject<LinkPlanReferentModalData>(MAT_DIALOG_DATA);

  readonly isSuperAdmin = this.authService.isSuperAdmin;
  readonly currentUser = this.authService.currentUser;

  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // All available users
  allUsers = signal<AdminUser[]>([]);

  // Referents currently assigned to plan (with modifications tracking)
  referentAssignments = signal<ReferentAssignment[]>([]);

  // For adding new referent
  userControl = new FormControl<AdminUser | string>('');
  filteredUsers = signal<AdminUser[]>([]);

  get hasChanges(): boolean {
    return this.referentAssignments().some(a => a.isNew || a.isDeleted);
  }

  get visibleAssignments(): ReferentAssignment[] {
    return this.referentAssignments().filter(a => !a.isDeleted);
  }

  get availableUsersForAdd(): AdminUser[] {
    const assignedIds = new Set(this.referentAssignments()
      .filter(a => !a.isDeleted)
      .map(a => a.user.id_role));
    return this.allUsers().filter(u => !assignedIds.has(u.id_role));
  }

  ngOnInit(): void {
    this.loadUsersAndAssignments();
    this.userControl.valueChanges.subscribe(value => {
      this.filterAvailableUsers(value);
    });
  }

  private loadUsersAndAssignments(): void {
    this.isLoadingData.set(true);

    const currentOrgId = this.currentUser()?.organisme?.id;
    const filterByOrg = !this.isSuperAdmin() && currentOrgId;

    // Load users - if admin_org, only load users from their organisme
    const params = filterByOrg ? { organisme: currentOrgId, page_size: 500 } : { page_size: 500 };

    this.adminService.getUsers(params).subscribe({
      next: (response) => {
        this.allUsers.set(response.results);
        this.initReferentAssignments();
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  private initReferentAssignments(): void {
    // Initialize assignments from plan's existing referents
    const existingAssignments: ReferentAssignment[] = (this.data.plan.referents || []).map(ref => ({
      user: {
        id_role: ref.id_role,
        email: ref.email,
        nom_role: ref.nom_role,
        prenom_role: ref.prenom_role,
        nom_complet: ref.nom_complet
      },
      isNew: false,
      isDeleted: false
    }));

    this.referentAssignments.set(existingAssignments);
    this.filterAvailableUsers('');
    this.isLoadingData.set(false);
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

  getUserDisplayName(user: PlanReferentInfo): string {
    if (user.nom_complet) {
      return user.nom_complet;
    }
    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role}`;
    }
    return user.email;
  }

  // Add a new referent to the list
  addReferent(user: AdminUser): void {
    const assignments = [...this.referentAssignments()];
    assignments.push({
      user: {
        id_role: user.id_role,
        email: user.email,
        nom_role: user.nom_role,
        prenom_role: user.prenom_role
      },
      isNew: true,
      isDeleted: false
    });
    this.referentAssignments.set(assignments);

    // Reset the form
    this.userControl.setValue('');
    this.filterAvailableUsers('');

    const userName = user.prenom_role && user.nom_role
      ? `${user.prenom_role} ${user.nom_role}`
      : user.email;
    this.successMessage.set(this.translate.instant('modals.linkPlanReferent.messages.referentAdded', { name: userName }));
    setTimeout(() => this.successMessage.set(null), 3000);
  }

  // Remove a referent from the list
  removeReferent(assignment: ReferentAssignment): void {
    const assignments = [...this.referentAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      if (assignment.isNew) {
        // Just remove it from the list
        assignments.splice(index, 1);
      } else {
        // Mark for deletion
        assignments[index] = { ...assignments[index], isDeleted: true };
      }
      this.referentAssignments.set(assignments);
      this.filterAvailableUsers(this.userControl.value);
    }
  }

  // Restore a referent marked for deletion
  restoreReferent(assignment: ReferentAssignment): void {
    const assignments = [...this.referentAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      assignments[index] = { ...assignments[index], isDeleted: false };
      this.referentAssignments.set(assignments);
      this.filterAvailableUsers(this.userControl.value);
    }
  }

  // Save all changes
  onSave(): void {
    const planId = this.data.plan.id_pg;
    const toAdd = this.referentAssignments().filter(a => a.isNew && !a.isDeleted);
    const toDelete = this.referentAssignments().filter(a => a.isDeleted && !a.isNew);

    if (toAdd.length === 0 && toDelete.length === 0) {
      this.dialogRef.close({ success: true, changed: false });
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    // Process operations - add all new referents in a single call
    this.processOperations(planId, toAdd, toDelete);
  }

  private processOperations(
    planId: number,
    toAdd: ReferentAssignment[],
    toDelete: ReferentAssignment[]
  ): void {
    let completed = 0;
    let hasError = false;
    const totalOperations = toAdd.length + toDelete.length;

    if (totalOperations === 0) {
      this.isLoading.set(false);
      this.dialogRef.close({ success: true, changed: true });
      return;
    }

    const checkComplete = () => {
      if (completed === totalOperations && !hasError) {
        this.isLoading.set(false);
        this.dialogRef.close({ success: true, changed: true });
      }
    };

    // Add new referents
    toAdd.forEach(assignment => {
      this.adminService.assignReferentToPlan(planId, assignment.user.id_role).subscribe({
        next: () => {
          completed++;
          checkComplete();
        },
        error: (error: Error) => {
          hasError = true;
          this.isLoading.set(false);
          this.errorMessage.set(this.translate.instant('modals.linkPlanReferent.messages.addError', { error: error.message }));
        }
      });
    });

    // Delete referents
    toDelete.forEach(assignment => {
      this.adminService.removeReferentFromPlan(planId, assignment.user.id_role).subscribe({
        next: () => {
          completed++;
          checkComplete();
        },
        error: (error: Error) => {
          hasError = true;
          this.isLoading.set(false);
          this.errorMessage.set(this.translate.instant('modals.linkPlanReferent.messages.removeError', { error: error.message }));
        }
      });
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
