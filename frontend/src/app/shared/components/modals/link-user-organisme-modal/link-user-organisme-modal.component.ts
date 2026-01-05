import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatInputModule } from '@angular/material/input';
import { AdminService } from '../../../../core/services/admin.service';
import { AdminOrganisme, AdminUser } from '../../../../core/models/admin.model';

export interface LinkUserOrganismeModalData {
  user?: AdminUser; // If provided, select organisme for this user
  organisme?: AdminOrganisme; // If provided, select user for this organisme
}

@Component({
  selector: 'app-link-user-organisme-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatAutocompleteModule,
    MatInputModule
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

  users = signal<AdminUser[]>([]);
  organismes = signal<AdminOrganisme[]>([]);

  selectedUserId: number | null = null;
  selectedOrganismeId: number | null = null;

  searchUserQuery = '';
  filteredUsers = signal<AdminUser[]>([]);

  get mode(): 'select-organisme' | 'select-user' {
    return this.data?.user ? 'select-organisme' : 'select-user';
  }

  ngOnInit(): void {
    if (this.mode === 'select-organisme') {
      this.selectedOrganismeId = this.data.user?.id_organisme || null;
      this.loadOrganismes();
    } else {
      this.loadUsers();
    }
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

  private loadUsers(): void {
    this.isLoadingData.set(true);
    // Load users without organisme
    this.adminService.getUsers().subscribe({
      next: (response) => {
        this.users.set(response.results);
        this.filteredUsers.set(response.results);
        this.isLoadingData.set(false);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  filterUsers(): void {
    const query = this.searchUserQuery.toLowerCase();
    const filtered = this.users().filter(user =>
      (user.nom_role?.toLowerCase().includes(query) || '') ||
      (user.prenom_role?.toLowerCase().includes(query) || '') ||
      user.email.toLowerCase().includes(query)
    );
    this.filteredUsers.set(filtered);
  }

  getUserDisplayName(user: AdminUser): string {
    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role} (${user.email})`;
    }
    return user.email;
  }

  onSubmit(): void {
    if (this.mode === 'select-organisme' && this.data.user) {
      this.assignOrganismeToUser();
    } else if (this.mode === 'select-user' && this.data.organisme && this.selectedUserId) {
      this.assignOrganismeToUser();
    }
  }

  private assignOrganismeToUser(): void {
    const userId = this.mode === 'select-organisme' ? this.data.user!.id_role : this.selectedUserId!;
    const organismeId = this.mode === 'select-organisme' ? this.selectedOrganismeId : this.data.organisme!.id_organisme;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.adminService.assignOrganismeToUser(userId, organismeId).subscribe({
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

  onCancel(): void {
    this.dialogRef.close();
  }
}
