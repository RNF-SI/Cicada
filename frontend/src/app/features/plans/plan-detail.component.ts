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
}
