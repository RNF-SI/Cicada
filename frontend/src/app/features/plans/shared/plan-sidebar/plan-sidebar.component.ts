import { Component, OnInit, input, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { Enjeu } from '../../../../core/models/enjeu.model';

@Component({
  selector: 'app-plan-sidebar',
  standalone: true,
  imports: [CommonModule, TranslateModule],
  templateUrl: './plan-sidebar.component.html',
  styleUrl: './plan-sidebar.component.scss'
})
export class PlanSidebarComponent implements OnInit {
  private readonly router = inject(Router);
  private readonly enjeuService = inject(EnjeuService);

  planId = input.required<number>();
  activePage = input<'overview' | 'enjeux' | 'bilan' | 'suivi-actions' | 'tableau-de-bord'>('overview');
  selectedEnjeuId = input<number | null>(null);

  enjeux = signal<Enjeu[]>([]);
  fcr = signal<Enjeu[]>([]);
  detailsMenuExpanded = signal(true);
  suivisMenuExpanded = signal(true);

  isSuivisActive = computed(() => {
    const page = this.activePage();
    return page === 'bilan' || page === 'suivi-actions' || page === 'tableau-de-bord';
  });

  ngOnInit(): void {
    this.enjeuService.getPlanEnjeux(this.planId()).subscribe(response => {
      this.enjeux.set(response.enjeux);
      this.fcr.set(response.fcr);
    });
  }

  toggleDetailsMenu(): void {
    this.detailsMenuExpanded.update(v => !v);
  }

  toggleSuivisMenu(): void {
    this.suivisMenuExpanded.update(v => !v);
  }

  navigateToOverview(): void {
    this.router.navigate(['/plans', this.planId()]);
  }

  navigateToEnjeux(): void {
    this.router.navigate(['/plans', this.planId(), 'enjeux']);
  }

  selectEnjeu(item: Enjeu): void {
    this.router.navigate(['/plans', this.planId(), 'enjeux', item.id_enjeu]);
  }

  navigateToBilan(): void {
    this.router.navigate(['/plans', this.planId(), 'bilan']);
  }

  navigateToSuiviActions(): void {
    this.router.navigate(['/plans', this.planId(), 'suivi-actions']);
  }

  navigateToTableauDeBord(): void {
    this.router.navigate(['/plans', this.planId(), 'tableau-de-bord']);
  }
}
