import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../core/services/admin.service';

@Component({
  selector: 'app-plan-bilan',
  standalone: true,
  imports: [CommonModule, RouterModule, TranslateModule, HeaderComponent, PlanSidebarComponent],
  template: `
    <app-header></app-header>
    <div class="suivis-layout">
      @if (planId(); as id) {
        <app-plan-sidebar [planId]="id" activePage="bilan"></app-plan-sidebar>
      }
      <main class="plan-main">
        <section class="hero-section">
          <div class="hero-background"><div class="hero-pattern"></div></div>
          <div class="hero-content">
            <nav class="breadcrumb" aria-label="Fil d'Ariane">
              <a routerLink="/accueil" class="breadcrumb-home" title="Retour à l'accueil">
                <i class="fi fi-rr-home"></i>
              </a>
              <div class="breadcrumb-lines"></div>
              <div class="breadcrumb-text">
                <a routerLink="/plans" class="breadcrumb-link">{{ 'plans.detail.sidebar.title' | translate }}</a>
                <i class="fi fi-rr-angle-small-right breadcrumb-chevron"></i>
                <a [routerLink]="['/plans', planId()]" class="breadcrumb-link">{{ planNom() }}</a>
                <i class="fi fi-rr-angle-small-right breadcrumb-chevron"></i>
                <span class="breadcrumb-current">{{ 'plans.suivis.bilan.title' | translate }}</span>
              </div>
            </nav>
            <div class="plan-header">
              <div class="plan-subtitle">
                <i class="fi fi-rr-stats"></i>
                <span>{{ 'plans.detail.sidebar.suivis' | translate | uppercase }}</span>
              </div>
              <h1 class="plan-title">{{ 'plans.suivis.bilan.title' | translate }}</h1>
            </div>
          </div>
        </section>
        <section class="content-section">
          <div class="coming-soon">
            <i class="fi fi-rr-time-forward"></i>
            <p>{{ 'plans.suivis.bilan.comingSoon' | translate }}</p>
          </div>
        </section>
      </main>
    </div>
  `,
  styleUrl: './plan-suivis.component.scss'
})
export class PlanBilanComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);

  planId = signal<number | null>(null);
  planNom = signal<string>('');

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      const planId = parseInt(id, 10);
      this.planId.set(planId);
      this.adminService.getPlan(planId).subscribe({
        next: (plan) => this.planNom.set(plan.nom)
      });
    }
  }
}
