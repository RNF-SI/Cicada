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

// Interface for user linked to plan
interface PlanUserInfo {
  id_role: number;
  email: string;
  nom_role?: string;
  prenom_role?: string;
  nom_complet?: string;
  referent: boolean;
}

// Interface for a user assignment in the modal
interface UserAssignment {
  user: PlanUserInfo;
  isNew?: boolean;
  isDeleted?: boolean;
  roleChanged?: boolean; // true if referent status changed
}

export interface LinkPlanReferentModalData {
  plan: {
    id_pg: number;
    nom: string;
    referents?: { id_role: number; email: string; nom_role?: string; prenom_role?: string; nom_complet?: string }[];
    membres?: { id_role: number; email: string; nom_role?: string; prenom_role?: string; nom_complet?: string; referent: boolean }[];
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
  readonly isAdminOrganisme = this.authService.isAdminOrganisme;
  readonly hasGlobalAccess = this.authService.hasGlobalAccess;
  readonly currentUser = this.authService.currentUser;

  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);
  successMessage = signal<string | null>(null);

  // All available users
  allUsers = signal<AdminUser[]>([]);

  // Users currently assigned to plan (with modifications tracking)
  userAssignments = signal<UserAssignment[]>([]);

  // For adding new user
  userControl = new FormControl<AdminUser | string>('');
  filteredUsers = signal<AdminUser[]>([]);
  addAsReferent = false;

  get hasChanges(): boolean {
    return this.userAssignments().some(a => a.isNew || a.isDeleted || a.roleChanged);
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
    this.loadUsersAndAssignments();
    this.userControl.valueChanges.subscribe(value => {
      this.filterAvailableUsers(value);
    });
  }

  private loadUsersAndAssignments(): void {
    this.isLoadingData.set(true);

    const currentOrgId = this.currentUser()?.organisme?.id_organisme;
    const filterByOrg = !this.hasGlobalAccess() && this.isAdminOrganisme() && currentOrgId;

    // Load users - if admin_org, only load users from their organisme
    const params = filterByOrg ? { organisme: currentOrgId, page_size: 500 } : { page_size: 500 };

    this.adminService.getUsers(params).subscribe({
      next: (response) => {
        this.allUsers.set(response.results);
        this.initUserAssignments();
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  private initUserAssignments(): void {
    // Use membres if available (has referent flag), otherwise fallback to referents
    const membres = this.data.plan.membres;
    let existingAssignments: UserAssignment[];

    if (membres && membres.length > 0) {
      existingAssignments = membres.map(m => ({
        user: {
          id_role: m.id_role,
          email: m.email,
          nom_role: m.nom_role,
          prenom_role: m.prenom_role,
          nom_complet: m.nom_complet,
          referent: m.referent,
        },
        isNew: false,
        isDeleted: false,
        roleChanged: false,
      }));
    } else {
      // Fallback: all existing referents are marked as referent=true
      existingAssignments = (this.data.plan.referents || []).map(ref => ({
        user: {
          id_role: ref.id_role,
          email: ref.email,
          nom_role: ref.nom_role,
          prenom_role: ref.prenom_role,
          nom_complet: ref.nom_complet,
          referent: true,
        },
        isNew: false,
        isDeleted: false,
        roleChanged: false,
      }));
    }

    this.userAssignments.set(existingAssignments);
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

  getUserDisplayName(user: PlanUserInfo): string {
    if (user.nom_complet) {
      return user.nom_complet;
    }
    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role}`;
    }
    return user.email;
  }

  // Add a new user to the list
  addUser(user: AdminUser): void {
    const assignments = [...this.userAssignments()];
    assignments.push({
      user: {
        id_role: user.id_role,
        email: user.email,
        nom_role: user.nom_role,
        prenom_role: user.prenom_role,
        referent: this.addAsReferent,
      },
      isNew: true,
      isDeleted: false,
      roleChanged: false,
    });
    this.userAssignments.set(assignments);

    // Reset the form
    this.userControl.setValue('');
    this.filterAvailableUsers('');

    const userName = user.prenom_role && user.nom_role
      ? `${user.prenom_role} ${user.nom_role}`
      : user.email;
    this.successMessage.set(this.translate.instant('modals.linkPlanReferent.messages.userAdded', { name: userName }));
    setTimeout(() => this.successMessage.set(null), 3000);
  }

  // Toggle referent status for an assignment
  toggleReferent(assignment: UserAssignment): void {
    const assignments = [...this.userAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      const newReferent = !assignments[index].user.referent;
      assignments[index] = {
        ...assignments[index],
        user: { ...assignments[index].user, referent: newReferent },
        roleChanged: !assignments[index].isNew ? true : assignments[index].roleChanged,
      };
      this.userAssignments.set(assignments);
    }
  }

  // Remove a user from the list
  removeUser(assignment: UserAssignment): void {
    const assignments = [...this.userAssignments()];
    const index = assignments.findIndex(a => a.user.id_role === assignment.user.id_role);

    if (index >= 0) {
      if (assignment.isNew) {
        assignments.splice(index, 1);
      } else {
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
    const planId = this.data.plan.id_pg;
    const toAdd = this.userAssignments().filter(a => a.isNew && !a.isDeleted);
    const toDelete = this.userAssignments().filter(a => a.isDeleted && !a.isNew);
    const toChangeRole = this.userAssignments().filter(a => a.roleChanged && !a.isNew && !a.isDeleted);

    if (toAdd.length === 0 && toDelete.length === 0 && toChangeRole.length === 0) {
      this.dialogRef.close({ success: true, changed: false });
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.processOperations(planId, toAdd, toDelete, toChangeRole);
  }

  private processOperations(
    planId: number,
    toAdd: UserAssignment[],
    toDelete: UserAssignment[],
    toChangeRole: UserAssignment[]
  ): void {
    let completed = 0;
    let hasError = false;
    const totalOperations = toAdd.length + toDelete.length + toChangeRole.length;

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

    // Add new users (as referent or member)
    toAdd.forEach(assignment => {
      const obs = assignment.user.referent
        ? this.adminService.assignReferentToPlan(planId, assignment.user.id_role)
        : this.adminService.assignMemberToPlan(planId, assignment.user.id_role);

      obs.subscribe({
        next: () => { completed++; checkComplete(); },
        error: (error: Error) => {
          hasError = true;
          this.isLoading.set(false);
          this.errorMessage.set(this.translate.instant('modals.linkPlanReferent.messages.addError', { error: error.message }));
        }
      });
    });

    // Delete users (remove from plan completely)
    toDelete.forEach(assignment => {
      this.adminService.removeMemberFromPlan(planId, assignment.user.id_role).subscribe({
        next: () => { completed++; checkComplete(); },
        error: (error: Error) => {
          hasError = true;
          this.isLoading.set(false);
          this.errorMessage.set(this.translate.instant('modals.linkPlanReferent.messages.removeError', { error: error.message }));
        }
      });
    });

    // Role changes (referent ↔ member)
    toChangeRole.forEach(assignment => {
      if (assignment.user.referent) {
        // Was member → now referent
        this.adminService.assignReferentToPlan(planId, assignment.user.id_role).subscribe({
          next: () => { completed++; checkComplete(); },
          error: (error: Error) => {
            hasError = true;
            this.isLoading.set(false);
            this.errorMessage.set(error.message);
          }
        });
      } else {
        // Was referent → now member
        this.adminService.removeReferentFromPlan(planId, assignment.user.id_role).subscribe({
          next: () => { completed++; checkComplete(); },
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
