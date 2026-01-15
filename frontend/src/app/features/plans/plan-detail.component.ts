import { Component, signal, computed, inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { HeaderComponent } from '../../shared/components/header/header.component';

interface PlanGestion {
  id: number;
  nom: string;
  dateDebut: number;
  dateFin: number;
  organismeRedacteur: string;
  niveauEvaluation: string;
  ct88: boolean;
  rang: number;
  surface: number;
  identifiantCdrOfb: string;
  statut: string;
}

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
    HeaderComponent
  ],
  templateUrl: './plan-detail.component.html',
  styleUrl: './plan-detail.component.scss'
})
export class PlanDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  planId = signal<number | null>(null);

  // Mock data - à remplacer par l'appel API
  plan = signal<PlanGestion | null>(null);

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
    // TODO: Appeler l'API backend pour récupérer le plan
    // Mock data pour l'instant
    this.plan.set({
      id: this.planId() || 1,
      nom: 'Marais du Grosset et Fisselong',
      dateDebut: 2020,
      dateFin: 2025,
      organismeRedacteur: 'Biotope (BE)',
      niveauEvaluation: 'Evaluation intermédiaire',
      ct88: true,
      rang: 3,
      surface: 100000,
      identifiantCdrOfb: 'Lorem ipsum',
      statut: 'Evaluation à mi-parcours'
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
