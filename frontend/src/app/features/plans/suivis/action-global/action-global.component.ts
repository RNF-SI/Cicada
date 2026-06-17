import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterModule } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule } from '@ngx-translate/core';
import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { TagComponent, TagVariant } from '../../../../shared/components/tag/tag.component';
import { AdminService } from '../../../../core/services/admin.service';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { Operation, OperationAnnee } from '../../../../core/models/enjeu.model';

interface YearRow {
  annee: number;
  niveau: string | null;
  niveauLabel: string | null;
  budgetPrev: number;
  budgetReal: number;
  etpPrev: number;
  etpReal: number;
}

/**
 * #379 — Page globale d'une action : statut de réalisation global (sur la
 * période), totaux budget et RH (prévisionnel vs réalisé) et récapitulatif
 * annuel. Accessible depuis le bouton « Global » des tableaux Réalisation /
 * Budget / RH du suivi des actions.
 */
@Component({
  selector: 'app-action-global',
  standalone: true,
  imports: [
    CommonModule, RouterModule, MatProgressSpinnerModule, MatTooltipModule,
    TranslateModule, HeaderComponent, PlanSidebarComponent, TagComponent
  ],
  templateUrl: './action-global.component.html',
  styleUrl: './action-global.component.scss'
})
export class ActionGlobalComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);
  private readonly enjeuService = inject(EnjeuService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);
  operation = signal<Operation | null>(null);

  /** Récapitulatif annuel (budget/RH prévisionnel vs réalisé + niveau). */
  yearRows = computed<YearRow[]>(() => {
    const op = this.operation();
    if (!op) return [];
    return [...(op.operation_annees || [])]
      .sort((a, b) => a.annee - b.annee)
      .map(oa => ({
        annee: oa.annee,
        niveau: oa.realisation?.niveau_realisation_mnemonique ?? null,
        niveauLabel: oa.realisation?.niveau_realisation_label ?? null,
        budgetPrev: this.budgetPrev(op, oa),
        budgetReal: this.budgetReal(op, oa),
        etpPrev: Number(oa.etp || 0),
        etpReal: Number(oa.realisation?.etp_realise || 0),
      }));
  });

  budgetTotal = computed(() => {
    const rows = this.yearRows();
    return {
      prev: rows.reduce((s, r) => s + r.budgetPrev, 0),
      real: rows.reduce((s, r) => s + r.budgetReal, 0),
    };
  });

  etpTotal = computed(() => {
    const rows = this.yearRows();
    return {
      prev: rows.reduce((s, r) => s + r.etpPrev, 0),
      real: rows.reduce((s, r) => s + r.etpReal, 0),
    };
  });

  ngOnInit(): void {
    const slug = this.route.snapshot.paramMap.get('slug');
    const opId = Number(this.route.snapshot.paramMap.get('operation_id'));
    if (slug) {
      this.planSlug.set(slug);
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => this.planId.set(plan.id_pg),
      });
    }
    if (opId) {
      this.enjeuService.getOperation(opId).subscribe({
        next: (op) => { this.operation.set(op); this.isLoading.set(false); },
        error: () => {
          this.errorMessage.set('Erreur lors du chargement de l\'action');
          this.isLoading.set(false);
        },
      });
    } else {
      this.isLoading.set(false);
    }
  }

  // --- Agrégation budget selon le mode de ventilation ---
  private budgetPrev(op: Operation, oa: OperationAnnee): number {
    const mode = op.ventilation_mode;
    if (mode === 'by_org' || mode === 'by_org_type') {
      return (oa.organismes || []).reduce(
        (s, o) => s + Number(o.budget_fonctionnement || 0) + Number(o.budget_investissement || 0), 0);
    }
    if (mode === 'by_type') {
      return Number(oa.budget_fonctionnement || 0) + Number(oa.budget_investissement || 0);
    }
    return Number(oa.budget || 0);
  }

  private budgetReal(op: Operation, oa: OperationAnnee): number {
    const mode = op.ventilation_mode;
    const r: any = oa.realisation;
    if (mode === 'by_org' || mode === 'by_org_type') {
      return (oa.organismes || []).reduce(
        (s, o: any) => s + Number(o.realisation?.budget_fonctionnement_realise || 0)
          + Number(o.realisation?.budget_investissement_realise || 0), 0);
    }
    if (mode === 'by_type') {
      return Number(r?.budget_fonctionnement_realise || 0) + Number(r?.budget_investissement_realise || 0);
    }
    return Number(r?.budget_realise || 0);
  }

  /** Variante de tag selon le niveau de réalisation. */
  niveauTagVariant(mnemonique: string | null | undefined): TagVariant {
    switch (mnemonique) {
      case 'TERMINE': return 'success';
      case 'EN_COURS': return 'info';
      case 'PARTIEL': return 'warning';
      case 'NON_REALISE': return 'error';
      case 'ABANDONNE': return 'error';
      case 'REPORTE': return 'draft';
      default: return 'muted';
    }
  }

  ecartPct(prev: number, real: number): number | null {
    return prev > 0 ? ((real - prev) / prev) * 100 : null;
  }
}
