import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { HeaderComponent } from '../../shared/components/header/header.component';
import { AdminService } from '../../core/services/admin.service';
import { AdminPlan } from '../../core/models/admin.model';

interface MenuItem {
  label: string;
  icon: string;
  route?: string;
  expanded?: boolean;
  children?: MenuItem[];
}

interface SyntheseAccordion {
  id: string;
  title: string;
  colorClass: 'terra-cotta' | 'orange';
  expanded: boolean;
  hasSubItems?: boolean;
  subItems?: SubAccordion[];
}

interface SubAccordion {
  id: string;
  title: string;
  expanded: boolean;
  items?: string[];
}

@Component({
  selector: 'app-plan-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatProgressSpinnerModule,
    TranslateModule,
    HeaderComponent
  ],
  templateUrl: './plan-detail.component.html',
  styleUrl: './plan-detail.component.scss'
})
export class PlanDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly adminService = inject(AdminService);

  planId = signal<number | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  // Plan data from API
  plan = signal<AdminPlan | null>(null);

  // Menu latéral du plan
  menuItems = signal<MenuItem[]>([
    {
      label: 'Vue d\'ensemble',
      icon: 'fi-rr-eye',
      route: 'overview'
    },
    {
      label: 'Détails et saisie',
      icon: 'fi-rr-pencil',
      expanded: false,
      children: [
        { label: 'Informations générales', icon: '', route: 'details/general' },
        { label: 'Enjeux', icon: '', route: 'details/enjeux' },
        { label: 'Objectifs', icon: '', route: 'details/objectifs' },
        { label: 'Actions', icon: '', route: 'details/actions' }
      ]
    },
    {
      label: 'Suivis',
      icon: 'fi-rr-stats',
      expanded: false,
      children: [
        { label: 'Indicateurs', icon: '', route: 'suivis/indicateurs' },
        { label: 'Bilans', icon: '', route: 'suivis/bilans' }
      ]
    }
  ]);

  activeMenuItem = signal<string>('overview');

  // Accordéons de la section Synthèse
  syntheseAccordions = signal<SyntheseAccordion[]>([
    {
      id: 'enjeux',
      title: 'Enjeux et Facteurs clés de réussite',
      colorClass: 'terra-cotta',
      expanded: false
    },
    {
      id: 'objectifs-lt',
      title: 'Objectifs long terme',
      colorClass: 'terra-cotta',
      expanded: false
    },
    {
      id: 'objectifs-op',
      title: 'Objectifs opérationnels',
      colorClass: 'terra-cotta',
      expanded: false
    },
    {
      id: 'actions',
      title: 'Actions et suivis',
      colorClass: 'orange',
      expanded: true,
      hasSubItems: true,
      subItems: [
        {
          id: 'intervention-patrimoine',
          title: 'Intervention patrimoine naturel',
          expanded: true,
          items: [
            'IP 01 : Restauration des ouvrages de régulation des niveaux d\'eau (y compris grillage contre les ragondins)',
            'IP 02 : Entretien et gestion des ouvrages de régulation des niveaux d\'eau',
            'IP 03 : Pâturage (Marterin)',
            'IP 04 : Broyage sur l\'ensemble des marais',
            'IP 05 : Broyage sur le Grand Étang et l\'Empoissonnement (1 fois /PG)'
          ]
        },
        {
          id: 'surveillance',
          title: 'Surveillance du territoire et police de l\'environnement',
          expanded: false,
          items: []
        },
        {
          id: 'participation',
          title: 'Participation à la recherche',
          expanded: false,
          items: []
        },
        {
          id: 'intervention-naturel',
          title: 'Intervention patrimoine naturel',
          expanded: false,
          items: []
        },
        {
          id: 'infrastructure',
          title: 'Création et maintenance d\'infrastructure d\'accueil',
          expanded: false,
          items: []
        }
      ]
    }
  ]);

  ngOnInit(): void {
    // Récupérer l'ID du plan depuis l'URL
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.planId.set(parseInt(id, 10));
      this.loadPlan();
    }
  }

  loadPlan(): void {
    const id = this.planId();
    if (!id) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    this.adminService.getPlan(id).subscribe({
      next: (plan) => {
        this.plan.set(plan);
        this.isLoading.set(false);
      },
      error: (error) => {
        this.errorMessage.set(error.message || 'Erreur lors du chargement du plan');
        this.isLoading.set(false);
      }
    });
  }

  toggleMenu(item: MenuItem): void {
    if (item.children) {
      item.expanded = !item.expanded;
      this.menuItems.update(items => [...items]);
    } else if (item.route) {
      this.activeMenuItem.set(item.route);
    }
  }

  navigateToChild(child: MenuItem): void {
    if (child.route) {
      this.activeMenuItem.set(child.route);
    }
  }

  goBack(): void {
    this.router.navigate(['/plans']);
  }

  toggleAccordion(accordionId: string): void {
    this.syntheseAccordions.update(accordions =>
      accordions.map(acc => ({
        ...acc,
        expanded: acc.id === accordionId ? !acc.expanded : acc.expanded
      }))
    );
  }

  toggleSubAccordion(parentId: string, subId: string): void {
    this.syntheseAccordions.update(accordions =>
      accordions.map(acc => {
        if (acc.id === parentId && acc.subItems) {
          return {
            ...acc,
            subItems: acc.subItems.map(sub => ({
              ...sub,
              expanded: sub.id === subId ? !sub.expanded : sub.expanded
            }))
          };
        }
        return acc;
      })
    );
  }
}
