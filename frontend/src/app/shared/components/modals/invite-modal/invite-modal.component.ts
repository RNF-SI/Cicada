/**
 * Modal pour inviter un organisme ou un utilisateur a rejoindre un site.
 */
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
import { debounceTime, distinctUntilChanged, switchMap, of, catchError } from 'rxjs';

import { AdminService } from '../../../../core/services/admin.service';
import { ValidationService } from '../../../../core/services/validation.service';
import { AdminOrganisme, AdminSite, AdminUser } from '../../../../core/models/admin.model';

export type InviteMode = 'organisme' | 'user';

export interface InviteModalData {
  site: AdminSite;
  mode: InviteMode;
  linkedOrganismes?: AdminOrganisme[]; // Pour le mode 'user', les organismes lies au site
}

@Component({
  selector: 'app-invite-modal',
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
  templateUrl: './invite-modal.component.html',
  styleUrl: './invite-modal.component.scss'
})
export class InviteModalComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly validationService = inject(ValidationService);
  private readonly dialogRef = inject(MatDialogRef<InviteModalComponent>);
  private readonly translate = inject(TranslateService);
  readonly data = inject<InviteModalData>(MAT_DIALOG_DATA);

  readonly isLoading = signal(false);
  readonly isSearching = signal(false);
  readonly errorMessage = signal<string | null>(null);

  // Recherche autocomplete
  readonly searchControl = new FormControl('');
  readonly justificationControl = new FormControl('');

  // Resultats de recherche
  readonly searchResults = signal<(AdminOrganisme | AdminUser)[]>([]);

  // Selection
  readonly selectedItem = signal<AdminOrganisme | AdminUser | null>(null);

  ngOnInit(): void {
    // Setup autocomplete search
    this.searchControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      switchMap(query => {
        if (!query || typeof query !== 'string' || query.length < 2) {
          this.searchResults.set([]);
          return of([]);
        }
        this.isSearching.set(true);
        return this.search(query);
      })
    ).subscribe({
      next: (results) => {
        this.searchResults.set(results);
        this.isSearching.set(false);
      },
      error: () => {
        this.searchResults.set([]);
        this.isSearching.set(false);
      }
    });
  }

  private search(query: string) {
    if (this.data.mode === 'organisme') {
      return this.adminService.getOrganismes({ search: query, for_invite: true }).pipe(
        switchMap(response => of((response.results || []).slice(0, 10))),
        catchError(() => of([]))
      );
    } else {
      // Mode 'user' - chercher les utilisateurs des organismes lies
      // On recupere tous les utilisateurs puis on filtre cote client
      return this.adminService.getUsers({ search: query }).pipe(
        switchMap(response => {
          // Filtrer pour ne garder que les utilisateurs dont l'organisme est lie au site
          const linkedOrgIds = new Set(
            (this.data.linkedOrganismes || []).map(o => o.id_organisme)
          );
          const filtered = (response.results || []).filter(user =>
            user.id_organisme && linkedOrgIds.has(user.id_organisme)
          ).slice(0, 10);
          return of(filtered);
        }),
        catchError(() => of([]))
      );
    }
  }

  displayFn(item: AdminOrganisme | AdminUser | null): string {
    if (!item) return '';
    if (this.data.mode === 'organisme') {
      return (item as AdminOrganisme).nom_organisme || '';
    } else {
      const user = item as AdminUser;
      const fullName = `${user.prenom_role || ''} ${user.nom_role || ''}`.trim();
      return fullName || user.email;
    }
  }

  onItemSelected(item: AdminOrganisme | AdminUser): void {
    this.selectedItem.set(item);
  }

  getTitle(): string {
    if (this.data.mode === 'organisme') {
      return this.translate.instant('modals.invite.titleOrganisme');
    }
    return this.translate.instant('modals.invite.titleUser');
  }

  getPlaceholder(): string {
    if (this.data.mode === 'organisme') {
      return this.translate.instant('modals.invite.searchOrganisme');
    }
    return this.translate.instant('modals.invite.searchUser');
  }

  onCancel(): void {
    this.dialogRef.close(null);
  }

  onSubmit(): void {
    const item = this.selectedItem();
    if (!item) {
      this.errorMessage.set(this.translate.instant('modals.invite.selectRequired'));
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const justification = this.justificationControl.value || '';

    if (this.data.mode === 'organisme') {
      const organisme = item as AdminOrganisme;
      this.validationService.inviteOrganismeToSite(this.data.site.slug, {
        organisme_id: organisme.id_organisme,
        justification
      }).subscribe({
        next: (response) => {
          this.isLoading.set(false);
          this.dialogRef.close({ success: true, message: response.message });
        },
        error: (error) => {
          this.isLoading.set(false);
          this.errorMessage.set(error.error?.error || this.translate.instant('common.messages.error'));
        }
      });
    } else {
      const user = item as AdminUser;
      this.validationService.inviteUserToSite(this.data.site.slug, {
        user_id: user.id_role,
        justification
      }).subscribe({
        next: (response) => {
          this.isLoading.set(false);
          this.dialogRef.close({ success: true, message: response.message });
        },
        error: (error) => {
          this.isLoading.set(false);
          this.errorMessage.set(error.error?.error || this.translate.instant('common.messages.error'));
        }
      });
    }
  }
}
