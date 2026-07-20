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
import { Protocole } from '../../../core/models/enjeu.model';
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

  /**
   * Protocoles du suivi (#252). Repli sur `protocole` singulier pour les
   * réponses d'API antérieures.
   */
  protocoles = computed<Protocole[]>(() => {
    const s = this.suivi();
    if (s?.protocoles?.length) return s.protocoles;
    return s?.protocole ? [s.protocole] : [];
  });

  /** N'affiche que les protocoles dont le mode (CAMPanule ou non) est renseigné. */
  protocolesAffichables = computed<Protocole[]>(() =>
    this.protocoles().filter(
      (p) => p.protocole_dans_campanule === true || p.protocole_dans_campanule === false,
    ),
  );

  hasProtocole = computed(() => this.protocolesAffichables().length > 0);

  isCampanule(p: Protocole): boolean {
    return p.protocole_dans_campanule === true;
  }

  isNotCampanule(p: Protocole): boolean {
    return p.protocole_dans_campanule === false;
  }

  isNonRespect(p: Protocole): boolean {
    return p.respect_protocole === false;
  }

  /** Libellé compact d'un protocole, pour l'en-tête de son bloc. */
  protocoleNom(p: Protocole, index: number): string {
    return (
      p.protocole_campanule_nom?.trim() ||
      p.nom_protocole?.trim() ||
      this.translate.instant('inventaires.form.protocoleIndex', { index: index + 1 })
    );
  }

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

  consulterProtocole(p: Protocole): void {
    const cdProtocole = p.cd_protocole_campanule;
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
