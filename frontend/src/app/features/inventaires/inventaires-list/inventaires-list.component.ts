/**
 * Page liste des Suivis et Inventaires (standalone).
 */
import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HeaderComponent } from '../../../shared/components/header/header.component';
import { InventaireService } from '../../../core/services/inventaire.service';
import { SuiviInventaireList } from '../../../core/models/inventaire.model';

@Component({
  selector: 'app-inventaires-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatFormFieldModule,
    MatInputModule,
    MatProgressSpinnerModule,
    TranslateModule,
    HeaderComponent
  ],
  templateUrl: './inventaires-list.component.html',
  styleUrl: './inventaires-list.component.scss'
})
export class InventairesListComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly inventaireService = inject(InventaireService);
  private readonly translate = inject(TranslateService);

  // State
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);
  suivis = signal<SuiviInventaireList[]>([]);
  totalCount = signal(0);

  // Filters
  activeTab = signal<'actifs' | 'inactifs'>('actifs');
  searchQuery = signal('');

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);

    const isActif = this.activeTab() === 'actifs';

    this.inventaireService.getInventaires({
      actif: isActif,
      search: this.searchQuery() || undefined,
    }).subscribe({
      next: (response) => {
        this.suivis.set(response.results);
        this.totalCount.set(response.pagination.count);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.errorMessage.set(
          this.translate.instant('inventaires.errors.loadFailed')
        );
        this.isLoading.set(false);
      }
    });
  }

  setTab(tab: 'actifs' | 'inactifs'): void {
    this.activeTab.set(tab);
    this.loadData();
  }

  onSearch(query: string): void {
    this.searchQuery.set(query);
    this.loadData();
  }

  navigateToCreate(): void {
    this.router.navigate(['/inventaires', 'nouveau']);
  }

  navigateToDetail(suivi: SuiviInventaireList): void {
    this.router.navigate(['/inventaires', suivi.id_suivi_inventaire, 'modifier']);
  }

  /**
   * Format the period display for a suivi.
   * Examples: "2026-", "2015-2020", "-"
   */
  formatPeriode(suivi: SuiviInventaireList): string {
    const debut = suivi.annee_lancement_suivi;
    const fin = suivi.annee_fin_suivi;
    if (debut && fin) return `${debut}-${fin}`;
    if (debut) return `${debut}-`;
    if (fin) return `-${fin}`;
    return '-';
  }

  /**
   * Get status chip CSS class.
   */
  getStatutClass(suivi: SuiviInventaireList): string {
    const label = suivi.statut_label?.toLowerCase() || '';
    if (label.includes('en cours')) return 'status-success';
    if (label.includes('termin')) return 'status-warning';
    return 'status-neutre';
  }
}
