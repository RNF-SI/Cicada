/**
 * Page liste des Suivis et Inventaires (standalone).
 */
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
// MatPaginator removed — using custom pagination matching plans-list style
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  FilterBarComponent,
  FilterDropdownComponent,
  FilterOptionListComponent,
  FilterPanelDirective,
  FilterOption,
} from '../../../shared/components/filters';
import { createFilterSet } from '../../../shared/utils/filter-set';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { SearchBarComponent } from '../../../shared/components/search-bar/search-bar.component';
import { InventaireService } from '../../../core/services/inventaire.service';
import { AdminService } from '../../../core/services/admin.service';
import { SuiviInventaireList } from '../../../core/models/inventaire.model';

@Component({
  selector: 'app-inventaires-list',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatProgressSpinnerModule,
    TranslateModule,
    FilterBarComponent,
    FilterDropdownComponent,
    FilterOptionListComponent,
    FilterPanelDirective,
    HeaderComponent,
    SearchBarComponent,
  ],
  templateUrl: './inventaires-list.component.html',
  styleUrl: './inventaires-list.component.scss'
})
export class InventairesListComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly inventaireService = inject(InventaireService);
  private readonly adminService = inject(AdminService);
  private readonly translate = inject(TranslateService);

  // State
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);
  suivis = signal<SuiviInventaireList[]>([]);
  totalCount = signal(0);

  // Pagination
  readonly pageSize = 10;
  currentPage = signal(1);
  totalPages = computed(() => Math.ceil(this.totalCount() / this.pageSize) || 1);

  readonly paginationPages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: (number | string)[] = [];

    if (total <= 7) {
      for (let i = 1; i <= total; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);
      if (current > 3) pages.push('...');
      for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
        pages.push(i);
      }
      if (current < total - 2) pages.push('...');
      pages.push(total);
    }

    return pages;
  });

  // Filters
  // La recherche reste hors du jeu de filtres : `hasActive()` ne doit pas la compter
  // (le bouton « réinitialiser » ne porte que sur les filtres, cf. #358).
  searchQuery = signal('');
  statutOptions = signal<{ id: number; label: string }[]>([]);
  siteOptions = signal<{ id_site: number; nom_site: string }[]>([]);

  // #358 / #592 — statut, site et date de début, mono-sélection stockée en tableau.
  readonly filters = createFilterSet({
    statut: [] as number[],
    site: [] as number[],
    dateDebutMin: '',
  }, {
    // Le listing est paginé côté serveur : toute remise à zéro relance la requête.
    onReset: () => {
      this.currentPage.set(1);
      this.loadData();
    },
  });

  ngOnInit(): void {
    this.loadStatutOptions();
    this.loadSiteOptions();
    this.loadData();
  }

  loadStatutOptions(): void {
    this.adminService.getNomenclaturesByType('STATUT_SUIVI').subscribe({
      next: (nomenclatures) => {
        this.statutOptions.set(
          nomenclatures.map(n => ({ id: n.id_nomenclature, label: n.label }))
        );
      }
    });
  }

  loadSiteOptions(): void {
    this.adminService.getSites({ page: 1, page_size: 500 }).subscribe({
      next: (response) => {
        this.siteOptions.set(
          response.results
            .map(s => ({ id_site: s.id_site, nom_site: s.nom_site }))
            .sort((a, b) => a.nom_site.localeCompare(b.nom_site))
        );
      }
    });
  }

  loadData(): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.inventaireService.getInventaires({
      search: this.searchQuery() || undefined,
      id_statut: this.filters.statut()[0],
      site: this.filters.site()[0],
      annee_min: this.filters.dateDebutMin() || undefined,
      page: this.currentPage(),
      page_size: this.pageSize,
    }).subscribe({
      next: (response) => {
        this.suivis.set(response.results);
        this.totalCount.set(response.pagination.count);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(
          this.translate.instant('inventaires.errors.loadFailed')
        );
        this.isLoading.set(false);
      }
    });
  }

  onSearch(query: string): void {
    this.searchQuery.set(query);
    this.currentPage.set(1);
    this.loadData();
  }

  /** Tout changement de filtre relance la requête paginée. */
  private applyFilterChange(): void {
    this.currentPage.set(1);
    this.loadData();
  }

  setStatutFilter(values: number[]): void {
    this.filters.statut.set(values);
    this.applyFilterChange();
  }

  // #358 — filtres site + date de début
  setSiteFilter(values: number[]): void {
    this.filters.site.set(values);
    this.applyFilterChange();
  }

  setDateDebutMin(date: string): void {
    this.filters.dateDebutMin.set(date || '');
    this.applyFilterChange();
  }

  /** #592 — options des filtres au format du kit UI. */
  statutFilterOptions = computed<FilterOption<number>[]>(() =>
    this.statutOptions().map((s) => ({ value: s.id, label: s.label })),
  );

  siteFilterOptions = computed<FilterOption<number>[]>(() =>
    this.siteOptions().map((s) => ({ value: s.id_site, label: s.nom_site })),
  );

  goToPage(page: number | string): void {
    if (typeof page === 'number' && page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
      this.loadData();
    }
  }

  previousPage(): void {
    if (this.currentPage() > 1) {
      this.currentPage.update(p => p - 1);
      this.loadData();
    }
  }

  nextPage(): void {
    if (this.currentPage() < this.totalPages()) {
      this.currentPage.update(p => p + 1);
      this.loadData();
    }
  }

  navigateToCreate(): void {
    this.router.navigate(['/inventaires', 'nouveau']);
  }

  navigateToDetail(suivi: SuiviInventaireList): void {
    this.router.navigate(['/inventaires', suivi.id_suivi_inventaire]);
  }

  navigateToEdit(suivi: SuiviInventaireList): void {
    this.router.navigate(['/inventaires', suivi.id_suivi_inventaire, 'modifier']);
  }

  /**
   * Format the period display for a suivi.
   * Examples: "2026-", "2015-2020", "-"
   */
  formatPeriode(suivi: SuiviInventaireList): string {
    const debut = suivi.date_lancement_suivi ? new Date(suivi.date_lancement_suivi).getFullYear() : null;
    const fin = suivi.annee_fin_suivi;
    if (debut && fin) return `${debut}-${fin}`;
    if (debut) return `${debut}-`;
    if (fin) return `-${fin}`;
    return '-';
  }

  /**
   * Get status chip CSS class based on Figma design:
   * - "en cours" → green (#82DB8A)
   * - "terminé" → blue (#81C9D8)
   * - "à venir" → orange salmon (#F5B399)
   */
  getStatutClass(suivi: SuiviInventaireList): string {
    const label = suivi.statut_label?.toLowerCase() || '';
    if (label.includes('en cours')) return 'status-en-cours';
    if (label.includes('termin')) return 'status-termine';
    if (label.includes('venir')) return 'status-a-venir';
    return 'status-chip-default';
  }
}
