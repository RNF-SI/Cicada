import { Component, OnInit, input, inject, signal, computed, effect, untracked } from '@angular/core';
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
  activePage = input<'overview' | 'enjeux' | 'bilan' | 'suivi-actions' | 'tableau-de-bord' | 'mindmap'>('overview');
  selectedEnjeuSlug = input<string | null>(null);

  // Signal partagé service : la sidebar reflète automatiquement les
  // mutations faites côté enjeux-list (DnD, CRUD…). Voir
  // `EnjeuService.currentPlanEnjeux` qui est mis à jour par
  // `getPlanEnjeux()` et par `updatePlanEnjeuxCache()`.
  // Tri par `(ordre, id_enjeu)` pour refléter le DnD enjeux/FCR.
  enjeux = computed(() => {
    const data = this.enjeuService.currentPlanEnjeux();
    if (!data || data.plan_id !== this.planId()) return [];
    return [...(data.enjeux || [])].sort((a, b) => {
      const oa = (a as any).ordre ?? 0;
      const ob = (b as any).ordre ?? 0;
      if (oa !== ob) return oa - ob;
      return a.id_enjeu - b.id_enjeu;
    });
  });
  fcr = computed(() => {
    const data = this.enjeuService.currentPlanEnjeux();
    if (!data || data.plan_id !== this.planId()) return [];
    return [...(data.fcr || [])].sort((a, b) => {
      const oa = (a as any).ordre ?? 0;
      const ob = (b as any).ordre ?? 0;
      if (oa !== ob) return oa - ob;
      return a.id_enjeu - b.id_enjeu;
    });
  });
  detailsMenuExpanded = signal(true);
  suivisMenuExpanded = signal(true);

  isSuivisActive = computed(() => {
    const page = this.activePage();
    return page === 'bilan' || page === 'suivi-actions' || page === 'tableau-de-bord';
  });

  isMindmapActive = computed(() => this.activePage() === 'mindmap');

  constructor() {
    // Charge les enjeux si le cache service ne les a pas (ou pour un autre
    // plan). Sinon on s'appuie sur le signal partagé `currentPlanEnjeux`
    // qui est mis à jour par tous les chargements et mutations (DnD).
    //
    // `untracked` : `getPlanEnjeux` lit + set le signal de cache, sans
    // ce wrap on déclencherait une boucle (#224).
    effect(() => {
      const planId = this.planId();
      this.activePage(); // track pour rafraîchir quand on revient sur la page
      if (!planId) return;
      untracked(() => {
        const cached = this.enjeuService.currentPlanEnjeux();
        if (cached && cached.plan_id === planId) return; // sidebar bénéficie déjà du cache
        this.enjeuService.getPlanEnjeux(planId, true).subscribe();
      });
    });
  }

  ngOnInit(): void {
    // Le chargement initial est géré par l'effect dans le constructeur
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

  navigateToMindmap(): void {
    this.router.navigate(['/plans', this.planSlug(), 'tableau-d-arborescence']);
  }
}
