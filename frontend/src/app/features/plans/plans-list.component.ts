import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatMenuModule } from '@angular/material/menu';
import { MatButtonModule } from '@angular/material/button';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { PlanGaugeComponent, GaugeStatus } from '../../shared/components/plan-gauge/plan-gauge.component';

interface PlanGestion {
  id: number;
  nom: string;
  sousNom?: string;
  isMultisites: boolean;
  periodeDebut: number;
  periodeFin: number;
  statut: 'en_cours_revision' | 'evaluation_mi_parcours' | 'valide' | 'brouillon';
  gaugeStatus: GaugeStatus;
}

@Component({
  selector: 'app-plans-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatMenuModule,
    MatButtonModule,
    HeaderComponent,
    PlanGaugeComponent
  ],
  templateUrl: './plans-list.component.html',
  styleUrl: './plans-list.component.scss'
})
export class PlansListComponent implements OnInit {
  private readonly router = inject(Router);

  // Tab state
  activeTab = signal<'actifs' | 'inactifs'>('actifs');

  // Search
  searchQuery = signal('');

  // Pagination
  currentPage = signal(1);
  totalPages = signal(1);
  itemsPerPage = 10;

  // Afficher la pagination seulement si nécessaire
  showPagination = computed(() => this.totalPages() > 1);

  // Mock data for plans
  plans = signal<PlanGestion[]>([
    {
      id: 1,
      nom: 'Marais du Grosset',
      isMultisites: false,
      periodeDebut: 2026,
      periodeFin: 2036,
      statut: 'en_cours_revision',
      gaugeStatus: 'not-started'
    },
    {
      id: 2,
      nom: 'Aven Espatty',
      isMultisites: true,
      periodeDebut: 2020,
      periodeFin: 2030,
      statut: 'evaluation_mi_parcours',
      gaugeStatus: 'in-progress'
    },
    {
      id: 3,
      nom: 'Bois de la Manche',
      isMultisites: false,
      periodeDebut: 2015,
      periodeFin: 2025,
      statut: 'valide',
      gaugeStatus: 'completed'
    },
    {
      id: 4,
      nom: 'Aven Espatty',
      isMultisites: true,
      periodeDebut: 2012,
      periodeFin: 2022,
      statut: 'valide',
      gaugeStatus: 'exceeded'
    }
  ]);

  // Computed filtered plans
  filteredPlans = computed(() => {
    const query = this.searchQuery().toLowerCase();
    return this.plans().filter(plan =>
      plan.nom.toLowerCase().includes(query)
    );
  });

  // Pagination pages array
  paginationPages = computed(() => {
    const total = this.totalPages();
    const current = this.currentPage();
    const pages: (number | string)[] = [];

    if (total <= 7) {
      for (let i = 1; i <= total; i++) {
        pages.push(i);
      }
    } else {
      pages.push(1);
      if (current > 3) {
        pages.push('...');
      }
      for (let i = Math.max(2, current - 1); i <= Math.min(total - 1, current + 1); i++) {
        if (!pages.includes(i)) {
          pages.push(i);
        }
      }
      if (current < total - 2) {
        pages.push('...');
      }
      if (!pages.includes(total)) {
        pages.push(total);
      }
    }

    return pages;
  });

  setTab(tab: 'actifs' | 'inactifs'): void {
    this.activeTab.set(tab);
  }

  goToPage(page: number | string): void {
    if (typeof page === 'number' && page >= 1 && page <= this.totalPages()) {
      this.currentPage.set(page);
    }
  }

  previousPage(): void {
    if (this.currentPage() > 1) {
      this.currentPage.update(p => p - 1);
    }
  }

  nextPage(): void {
    if (this.currentPage() < this.totalPages()) {
      this.currentPage.update(p => p + 1);
    }
  }

  getStatutLabel(statut: string): string {
    const labels: Record<string, string> = {
      'en_cours_revision': 'en cours de révision',
      'evaluation_mi_parcours': 'évaluation mi-parcours',
      'valide': 'validé',
      'brouillon': 'brouillon'
    };
    return labels[statut] || statut;
  }

  getStatutClass(statut: string): string {
    const classes: Record<string, string> = {
      'en_cours_revision': 'status-warning',
      'evaluation_mi_parcours': 'status-warning',
      'valide': 'status-success',
      'brouillon': 'status-neutral'
    };
    return classes[statut] || '';
  }

  ngOnInit(): void {
    // TODO: Charger les plans depuis l'API
    this.loadPlans();
  }

  loadPlans(): void {
    // TODO: Appeler l'API backend pour récupérer les plans de l'utilisateur
    // Pour l'instant, on utilise les données mock
    console.log('Loading plans...');
  }

  editStatus(plan: PlanGestion): void {
    // TODO: Open modal to edit status
    console.log('Edit status for plan:', plan.id);
  }

  viewPlan(plan: PlanGestion): void {
    // Naviguer vers la page de détail du plan
    this.router.navigate(['/plans', plan.id]);
  }

  followPlan(plan: PlanGestion): void {
    // TODO: Navigate to plan monitoring
    console.log('Follow plan:', plan.id);
  }
}
