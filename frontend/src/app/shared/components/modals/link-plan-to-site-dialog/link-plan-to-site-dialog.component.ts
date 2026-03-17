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
import { ValidationService } from '../../../../core/services/validation.service';
import { AdminPlan } from '../../../../core/models/admin.model';

export interface LinkPlanToSiteDialogData {
  siteId: number;
  siteName: string;
  existingPlanIds: number[];
}

@Component({
  selector: 'app-link-plan-to-site-dialog',
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
  templateUrl: './link-plan-to-site-dialog.component.html',
  styleUrl: './link-plan-to-site-dialog.component.scss'
})
export class LinkPlanToSiteDialogComponent implements OnInit {
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly validationService = inject(ValidationService);
  private readonly dialogRef = inject(MatDialogRef<LinkPlanToSiteDialogComponent>);
  private readonly translate = inject(TranslateService);
  readonly data = inject<LinkPlanToSiteDialogData>(MAT_DIALOG_DATA);

  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);

  allPlans = signal<AdminPlan[]>([]);
  filteredPlans = signal<AdminPlan[]>([]);
  planControl = new FormControl<AdminPlan | string>('');

  get availablePlans(): AdminPlan[] {
    const existingIds = new Set(this.data.existingPlanIds || []);
    return this.allPlans().filter(p => !existingIds.has(p.id_pg));
  }

  ngOnInit(): void {
    this.loadPlans();
    this.planControl.valueChanges.subscribe(value => {
      this.filterPlans(value);
    });
  }

  private loadPlans(): void {
    this.isLoadingData.set(true);
    this.adminService.getPlans({ page_size: 500, scope: 'mine' }).subscribe({
      next: (response) => {
        this.allPlans.set(response.results);
        this.filterPlans('');
        this.isLoadingData.set(false);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
        this.isLoadingData.set(false);
      }
    });
  }

  private filterPlans(value: AdminPlan | string | null): void {
    const available = this.availablePlans;
    if (!value) {
      this.filteredPlans.set(available);
      return;
    }
    const query = typeof value === 'string' ? value.toLowerCase() : value.nom.toLowerCase();
    this.filteredPlans.set(
      available.filter(p => p.nom.toLowerCase().includes(query))
    );
  }

  displayPlan(plan: AdminPlan | null): string {
    if (!plan) return '';
    let label = plan.nom;
    if (plan.annee_debut && plan.annee_fin) {
      label += ` (${plan.annee_debut}-${plan.annee_fin})`;
    }
    return label;
  }

  selectPlan(plan: AdminPlan): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.validationService.requestPlanSiteLink(plan.id_pg, this.data.siteId).subscribe({
      next: (result: any) => {
        this.isLoading.set(false);
        this.dialogRef.close({
          success: true,
          plan,
          direct: result.direct,
          message: result.message
        });
      },
      error: (error: any) => {
        this.isLoading.set(false);
        const msg = error.error?.error || error.message || this.translate.instant('common.messages.error');
        this.errorMessage.set(msg);
      }
    });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
