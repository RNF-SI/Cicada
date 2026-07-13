/**
 * Fiche détail d'un Suivi/Inventaire (lecture seule).
 */
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HeaderComponent } from '../../../shared/components/header/header.component';
import { ProtocoleCampanuleDialogComponent } from '../../../shared/components/modals/protocole-campanule-dialog/protocole-campanule-dialog.component';
import { InventaireService } from '../../../core/services/inventaire.service';
import { SuiviInventaireDetail } from '../../../core/models/inventaire.model';
import { taxonRefsToText } from '../../../shared/utils/taxon-ref.utils';

@Component({
  selector: 'app-inventaire-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatDialogModule,
    TranslateModule,
    HeaderComponent,
  ],
  templateUrl: './inventaire-detail.component.html',
  styleUrl: './inventaire-detail.component.scss'
})
export class InventaireDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly inventaireService = inject(InventaireService);
  private readonly translate = inject(TranslateService);
  private readonly dialog = inject(MatDialog);

  suivi = signal<SuiviInventaireDetail | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  // Derived values
  titre = computed(() => this.suivi()?.intitule || '');

  /** Taxons référés en texte lisible (le champ peut être du JSON, cf. #563). */
  taxonRefText = computed(() => taxonRefsToText(this.suivi()?.taxon_taxref));

  periode = computed(() => {
    const s = this.suivi();
    if (!s) return '';
    const debut = s.date_lancement_suivi ? new Date(s.date_lancement_suivi).getFullYear() : null;
    const fin = s.annee_fin_suivi;
    if (debut && fin) return `${debut} – ${fin}`;
    if (debut) return `${debut} –`;
    if (fin) return `– ${fin}`;
    return '';
  });

  frequenceLabel = computed(() => {
    const s = this.suivi();
    if (!s?.frequence_nombre || !s?.frequence_unite) return '';
    const uniteKey = `inventaires.form.unite${this.capitalize(s.frequence_unite)}`;
    const unite = this.translate.instant(uniteKey);
    return `${s.frequence_nombre} ${this.translate.instant('inventaires.form.frequenceFoisPar')} ${unite}`;
  });

  isCampanule = computed(() => this.suivi()?.protocole?.protocole_dans_campanule === true);
  isNotCampanule = computed(() => this.suivi()?.protocole?.protocole_dans_campanule === false);
  isNonRespect = computed(() => this.suivi()?.protocole?.respect_protocole === false);

  hasProtocole = computed(() => {
    const p = this.suivi()?.protocole;
    return p && (p.protocole_dans_campanule === true || p.protocole_dans_campanule === false);
  });

  ngOnInit(): void {
    const idStr = this.route.snapshot.paramMap.get('suiviId');
    if (idStr) {
      const id = parseInt(idStr, 10);
      if (!isNaN(id)) {
        this.loadSuivi(id);
        return;
      }
    }
    this.errorMessage.set(this.translate.instant('inventaires.errors.loadFailed'));
    this.isLoading.set(false);
  }

  private loadSuivi(id: number): void {
    this.inventaireService.getInventaire(id).subscribe({
      next: (data) => {
        this.suivi.set(data);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('inventaires.errors.loadFailed'));
        this.isLoading.set(false);
      }
    });
  }

  navigateToEdit(): void {
    const s = this.suivi();
    if (s) {
      this.router.navigate(['/inventaires', s.id_suivi_inventaire, 'modifier']);
    }
  }

  consulterProtocole(): void {
    const cdProtocole = this.suivi()?.protocole?.cd_protocole_campanule;
    if (!cdProtocole) return;
    this.dialog.open(ProtocoleCampanuleDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { cdProtocole },
    });
  }

  formatBoolean(val: boolean | null | undefined): string {
    if (val === true) return this.translate.instant('common.yes');
    if (val === false) return this.translate.instant('common.no');
    return '—';
  }

  getStatutClass(): string {
    const label = this.suivi()?.statut_label?.toLowerCase() || '';
    if (label.includes('en cours')) return 'status-en-cours';
    if (label.includes('termin')) return 'status-termine';
    if (label.includes('venir')) return 'status-a-venir';
    return 'status-chip-default';
  }

  private capitalize(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }
}
