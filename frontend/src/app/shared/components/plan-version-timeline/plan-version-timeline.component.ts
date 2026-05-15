import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { MatChipsModule } from '@angular/material/chips';
import { TranslateModule } from '@ngx-translate/core';
import { PlanVersionChainItem } from '../../../core/models/admin.model';
import { getPlanStatusKey } from '../../utils/plan-status.utils';

@Component({
  selector: 'app-plan-version-timeline',
  standalone: true,
  imports: [CommonModule, RouterModule, MatChipsModule, TranslateModule],
  templateUrl: './plan-version-timeline.component.html',
  styleUrl: './plan-version-timeline.component.scss',
})
export class PlanVersionTimelineComponent {
  @Input() chain: PlanVersionChainItem[] = [];
  @Input() currentStatus = 'draft';
  /** Mnémonique du type de site principal (RNN, RNR, PNR, ENS...) — #281 */
  @Input() principalSiteTypeMnemonique: string | null = null;

  /** Clé i18n du statut, contextualisée pour `etendu` selon le type d'aire (#281). */
  getStatusLabelKey(item: PlanVersionChainItem): string {
    return getPlanStatusKey(item.statut, this.principalSiteTypeMnemonique);
  }

  getNodeIcon(item: PlanVersionChainItem): string {
    switch (item.type_document_mnemonique) {
      case 'EVAL_MI_PARCOURS':
        return 'fi-rr-time-forward';
      case 'PLAN_REVISE':
        return 'fi-rr-refresh';
      default:
        return 'fi-rr-document';
    }
  }

  getStatusClass(item: PlanVersionChainItem): string {
    const classes: Record<string, string> = {
      draft: 'status-warning',
      // #277 — Statuts intermédiaires CSRPN : couleur "en cours" (warning)
      // pour signaler qu'une étape réglementaire est en attente.
      avis_csrpn: 'status-warning',
      comite_consultatif: 'status-warning',
      arrete_pref: 'status-warning',
      valide: 'status-success',
      modifie: 'status-success',
      mi_parcours: 'status-success',
      etendu: 'status-info',
      en_revision: 'status-info',
      archive: 'status-neutre',
    };
    return classes[item.statut] || '';
  }

  /**
   * Indique si un nœud représente le brouillon d'un rang ultérieur au plan
   * en cours de consultation (#280). Sert à appliquer un style distinct
   * (cadre pointillé) cf. note Cycle de vie d'un plan de gestion.
   */
  isNextRangDraft(item: PlanVersionChainItem): boolean {
    if (item.statut !== 'draft' || item.rang === undefined) return false;
    const current = this.chain.find(c => c.is_current);
    if (!current || current.rang === undefined) return false;
    return item.rang > current.rang;
  }
}
