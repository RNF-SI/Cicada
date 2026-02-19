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
  planSlug = input.required<string>();
  activePage = input<'overview' | 'enjeux' | 'bilan' | 'suivi-actions' | 'tableau-de-bord'>('overview');
  selectedEnjeuSlug = input<string | null>(null);

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
    this.router.navigate(['/plans', this.planSlug()]);
  }

  navigateToEnjeux(): void {
    this.router.navigate(['/plans', this.planSlug(), 'enjeux']);
  }

  selectEnjeu(item: Enjeu): void {
    this.router.navigate(['/plans', this.planSlug(), 'enjeux', item.slug]);
  }

  navigateToBilan(): void {
    this.router.navigate(['/plans', this.planSlug(), 'bilan']);
  }

  navigateToSuiviActions(): void {
    this.router.navigate(['/plans', this.planSlug(), 'suivi-actions']);
  }

  navigateToTableauDeBord(): void {
    this.router.navigate(['/plans', this.planSlug(), 'tableau-de-bord']);
  }
}
