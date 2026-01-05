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
import { AdminOrganisme, AdminSite } from '../../../../core/models/admin.model';

export interface LinkSiteOrganismeModalData {
  site?: AdminSite; // If provided, select organisme for this site
  organisme?: AdminOrganisme; // If provided, select site for this organisme
}

@Component({
  selector: 'app-link-site-organisme-modal',
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
  templateUrl: './link-site-organisme-modal.component.html',
  styleUrl: './link-site-organisme-modal.component.scss'
})
export class LinkSiteOrganismeModalComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly dialogRef = inject(MatDialogRef<LinkSiteOrganismeModalComponent>);
  readonly data = inject<LinkSiteOrganismeModalData>(MAT_DIALOG_DATA);

  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);

  sites = signal<AdminSite[]>([]);
  organismes = signal<AdminOrganisme[]>([]);

  selectedSiteId: number | null = null;
  selectedOrganismeId: number | null = null;
  isPrincipal = false;

  searchQuery = '';
  filteredSites = signal<AdminSite[]>([]);

  get mode(): 'select-organisme' | 'select-site' {
    return this.data?.site ? 'select-organisme' : 'select-site';
  }

  ngOnInit(): void {
    if (this.mode === 'select-organisme') {
      this.loadOrganismes();
    } else {
      this.loadSites();
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

  private loadSites(): void {
    this.isLoadingData.set(true);
    this.adminService.getSites().subscribe({
      next: (response) => {
        this.sites.set(response.results);
        this.filteredSites.set(response.results);
        this.isLoadingData.set(false);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  filterSites(): void {
    const query = this.searchQuery.toLowerCase();
    const filtered = this.sites().filter(site =>
      site.nom_site.toLowerCase().includes(query) ||
      (site.id_local?.toLowerCase().includes(query) || '')
    );
    this.filteredSites.set(filtered);
  }

  getSiteDisplayName(site: AdminSite): string {
    let name = site.nom_site;
    if (site.type_site_label) {
      name += ` (${site.type_site_label})`;
    }
    if (site.surf_off) {
      name += ` - ${site.surf_off} ha`;
    }
    return name;
  }

  onSubmit(): void {
    const siteId = this.mode === 'select-organisme' ? this.data.site!.id_site : this.selectedSiteId!;
    const organismeId = this.mode === 'select-organisme' ? this.selectedOrganismeId! : this.data.organisme!.id_organisme;

    if (!siteId || !organismeId) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.adminService.assignSiteToOrganisme(organismeId, siteId, this.isPrincipal).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.dialogRef.close({ success: true, siteId, organismeId, principal: this.isPrincipal });
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
