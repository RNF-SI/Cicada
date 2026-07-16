import { Component, inject, input, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';

import { TaxonomyService, TaxrefDetail } from '../../../core/services/taxonomy.service';
import { TagComponent } from '../tag/tag.component';

@Component({
  selector: 'app-taxon-detail',
  standalone: true,
  imports: [
    CommonModule,
    MatCardModule,
    MatProgressSpinnerModule,
    TranslateModule,
    TagComponent,
  ],
  templateUrl: './taxon-detail.component.html',
  styleUrl: './taxon-detail.component.scss',
})
export class TaxonDetailComponent {
  private readonly taxonomyService = inject(TaxonomyService);

  /** Code nom du taxon à afficher */
  cdNom = input.required<number>();

  taxon = signal<TaxrefDetail | null>(null);
  isLoading = signal(false);
  error = signal<string | null>(null);

  constructor() {
    effect(() => {
      const cd = this.cdNom();
      if (cd) {
        this.loadTaxon(cd);
      }
    });
  }

  private loadTaxon(cdNom: number): void {
    this.isLoading.set(true);
    this.error.set(null);

    this.taxonomyService.getDetail(cdNom).subscribe({
      next: (taxon) => {
        this.taxon.set(taxon);
        this.isLoading.set(false);
      },
      error: (err) => {
        this.error.set('Impossible de charger les informations du taxon.');
        this.isLoading.set(false);
      },
    });
  }

  /** Construit la hiérarchie taxonomique du taxon */
  get hierarchy(): { label: string; value: string }[] {
    const t = this.taxon();
    if (!t) return [];
    return [
      { label: 'Règne', value: t.regne },
      { label: 'Phylum', value: t.phylum },
      { label: 'Classe', value: t.classe },
      { label: 'Ordre', value: t.ordre },
      { label: 'Famille', value: t.famille },
    ].filter(item => !!item.value);
  }
}
