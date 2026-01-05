import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { AdminService } from '../../../../core/services/admin.service';
import { AdminOrganisme, OrganismeCreatePayload } from '../../../../core/models/admin.model';

export interface OrganismeFormModalData {
  organisme?: AdminOrganisme; // If provided, edit mode
  parentOrganismes?: AdminOrganisme[]; // For parent selection
}

@Component({
  selector: 'app-organisme-form-modal',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './organisme-form-modal.component.html',
  styleUrl: './organisme-form-modal.component.scss'
})
export class OrganismeFormModalComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly adminService = inject(AdminService);
  private readonly dialogRef = inject(MatDialogRef<OrganismeFormModalComponent>);
  readonly data = inject<OrganismeFormModalData>(MAT_DIALOG_DATA);

  form!: FormGroup;
  isLoading = signal(false);
  errorMessage = signal<string | null>(null);
  parentOrganismes = signal<AdminOrganisme[]>([]);

  get isEditMode(): boolean {
    return !!this.data?.organisme;
  }

  ngOnInit(): void {
    this.initForm();
    this.loadParentOrganismes();
  }

  private initForm(): void {
    const org = this.data?.organisme;

    this.form = this.fb.group({
      nom_organisme: [org?.nom_organisme || '', [Validators.required, Validators.maxLength(255)]],
      adresse_organisme: [org?.adresse_organisme || '', Validators.maxLength(255)],
      cp_organisme: [org?.cp_organisme || '', [Validators.maxLength(10), Validators.pattern(/^\d{5}$/)]],
      ville_organisme: [org?.ville_organisme || '', Validators.maxLength(100)],
      tel_organisme: [org?.tel_organisme || '', Validators.maxLength(20)],
      email_organisme: [org?.email_organisme || '', [Validators.email, Validators.maxLength(255)]],
      url_organisme: [org?.url_organisme || '', Validators.maxLength(255)],
      parent_id: [org?.id_parent || null]
    });
  }

  private loadParentOrganismes(): void {
    // Load available parent organismes if provided
    if (this.data?.parentOrganismes) {
      // Filter out the current organisme if editing
      const filtered = this.isEditMode
        ? this.data.parentOrganismes.filter(o => o.id_organisme !== this.data.organisme!.id_organisme)
        : this.data.parentOrganismes;
      this.parentOrganismes.set(filtered);
    } else {
      // Load from API
      this.adminService.getOrganismes().subscribe({
        next: (response) => {
          const filtered = this.isEditMode
            ? response.results.filter(o => o.id_organisme !== this.data.organisme!.id_organisme)
            : response.results;
          this.parentOrganismes.set(filtered);
        }
      });
    }
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    this.errorMessage.set(null);

    const payload: OrganismeCreatePayload = {
      nom_organisme: this.form.value.nom_organisme,
      adresse_organisme: this.form.value.adresse_organisme || undefined,
      cp_organisme: this.form.value.cp_organisme || undefined,
      ville_organisme: this.form.value.ville_organisme || undefined,
      tel_organisme: this.form.value.tel_organisme || undefined,
      email_organisme: this.form.value.email_organisme || undefined,
      url_organisme: this.form.value.url_organisme || undefined,
      parent_id: this.form.value.parent_id || null
    };

    const request$ = this.isEditMode
      ? this.adminService.updateOrganisme(this.data.organisme!.id_organisme, payload)
      : this.adminService.createOrganisme(payload);

    request$.subscribe({
      next: (organisme) => {
        this.isLoading.set(false);
        this.dialogRef.close(organisme);
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
