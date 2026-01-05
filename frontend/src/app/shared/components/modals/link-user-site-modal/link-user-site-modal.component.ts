import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatInputModule } from '@angular/material/input';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { AdminService } from '../../../../core/services/admin.service';
import { AdminSite, AdminUser } from '../../../../core/models/admin.model';

export interface LinkUserSiteModalData {
  user?: AdminUser; // If provided, select site for this user
  site?: AdminSite; // If provided, select user for this site
}

@Component({
  selector: 'app-link-user-site-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatSelectModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatInputModule,
    MatCheckboxModule
  ],
  templateUrl: './link-user-site-modal.component.html',
  styleUrl: './link-user-site-modal.component.scss'
})
export class LinkUserSiteModalComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly dialogRef = inject(MatDialogRef<LinkUserSiteModalComponent>);
  readonly data = inject<LinkUserSiteModalData>(MAT_DIALOG_DATA);

  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);

  sites = signal<AdminSite[]>([]);
  users = signal<AdminUser[]>([]);

  selectedSiteId: number | null = null;
  selectedUserId: number | null = null;
  isReferent = true;

  searchQuery = '';
  filteredItems = signal<any[]>([]);

  get mode(): 'select-site' | 'select-user' {
    return this.data?.user ? 'select-site' : 'select-user';
  }

  ngOnInit(): void {
    if (this.mode === 'select-site') {
      this.loadSites();
    } else {
      this.loadUsers();
    }
  }

  private loadSites(): void {
    this.isLoadingData.set(true);
    this.adminService.getSites().subscribe({
      next: (response) => {
        this.sites.set(response.results);
        this.filteredItems.set(response.results);
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
    this.adminService.getUsers().subscribe({
      next: (response) => {
        this.users.set(response.results);
        this.filteredItems.set(response.results);
        this.isLoadingData.set(false);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  filterItems(): void {
    const query = this.searchQuery.toLowerCase();

    if (this.mode === 'select-site') {
      const filtered = this.sites().filter(site =>
        site.nom_site.toLowerCase().includes(query) ||
        (site.id_local?.toLowerCase().includes(query) || '')
      );
      this.filteredItems.set(filtered);
    } else {
      const filtered = this.users().filter(user =>
        (user.nom_role?.toLowerCase().includes(query) || '') ||
        (user.prenom_role?.toLowerCase().includes(query) || '') ||
        user.email.toLowerCase().includes(query)
      );
      this.filteredItems.set(filtered);
    }
  }

  getSiteDisplayName(site: AdminSite): string {
    let name = site.nom_site;
    if (site.type_site_label) {
      name += ` (${site.type_site_label})`;
    }
    return name;
  }

  getUserDisplayName(user: AdminUser): string {
    if (user.prenom_role && user.nom_role) {
      return `${user.prenom_role} ${user.nom_role} (${user.email})`;
    }
    return user.email;
  }

  onSubmit(): void {
    const userId = this.mode === 'select-site' ? this.data.user!.id_role : this.selectedUserId!;
    const siteId = this.mode === 'select-site' ? this.selectedSiteId! : this.data.site!.id_site;

    if (!userId || !siteId) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.adminService.assignUserToSite(siteId, userId, this.isReferent).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.dialogRef.close({ success: true, userId, siteId, referent: this.isReferent });
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
