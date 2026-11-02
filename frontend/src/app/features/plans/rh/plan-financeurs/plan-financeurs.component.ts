/**
 * #790 — Financeurs d'un plan, sous les postes de la page « Postes / RH /
 * Financeurs ». Un financeur = un nom + une catégorie : celle de la liste
 * commune (CATEGORIE_FINANCE) ou, à défaut, une catégorie libre **propre à ce
 * plan** (jamais ajoutée à la liste des autres plans). Même nom + même
 * catégorie = un seul financeur (refus 400 du serveur). Les montants se
 * saisissent dans la fiche action (prévu global) et au suivi (annuel).
 */
import { ChangeDetectionStrategy, Component, OnChanges, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AdminService } from '../../../../core/services/admin.service';
import { RhService } from '../../../../core/services/rh.service';
import { Financeur } from '../../../../core/models/rh.model';
import { EntityTileComponent } from '../../../../shared/components/entity-tile/entity-tile.component';
import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';

/** Valeur du sélecteur de catégorie pour « autre catégorie (propre au plan) ». */
export const AUTRE_CATEGORIE = -1;

@Component({
  selector: 'app-plan-financeurs',
  standalone: true,
  imports: [FormsModule, MatButtonModule, TranslateModule, EntityTileComponent, FormFieldComponent],
  templateUrl: './plan-financeurs.component.html',
  styleUrl: './plan-financeurs.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class PlanFinanceursComponent implements OnChanges {
  private readonly rhService = inject(RhService);
  private readonly adminService = inject(AdminService);
  private readonly translate = inject(TranslateService);

  planId = input.required<number>();
  canManage = input<boolean>(false);

  readonly AUTRE = AUTRE_CATEGORIE;
  financeurs = signal<Financeur[]>([]);
  categories = signal<{ id_nomenclature: number; label: string }[]>([]);
  erreur = signal<string | null>(null);

  /** Financeur en cours d'édition (null = ajout). */
  enEdition: Financeur | null = null;
  nom = '';
  categorie: number | null = null;
  categorieLibre = '';

  ngOnChanges(): void {
    this.charger();
    this.adminService.getNomenclaturesByType('CATEGORIE_FINANCE').subscribe({
      next: (cats) => this.categories.set(cats),
      error: () => this.categories.set([]),
    });
  }

  private charger(): void {
    this.rhService.getFinanceursByPlan(this.planId()).subscribe({
      next: (list) => this.financeurs.set(list),
      error: () => this.financeurs.set([]),
    });
  }

  peutEnregistrer(): boolean {
    return !!this.nom.trim() && (this.categorie !== AUTRE_CATEGORIE || !!this.categorieLibre.trim());
  }

  modifier(f: Financeur): void {
    this.enEdition = f;
    this.nom = f.nom;
    this.categorie = f.id_categorie ?? (f.categorie_libre ? AUTRE_CATEGORIE : null);
    this.categorieLibre = f.categorie_libre || '';
    this.erreur.set(null);
  }

  annuler(): void {
    this.enEdition = null;
    this.nom = '';
    this.categorie = null;
    this.categorieLibre = '';
    this.erreur.set(null);
  }

  enregistrer(): void {
    if (!this.peutEnregistrer()) return;
    const autre = this.categorie === AUTRE_CATEGORIE;
    const payload = {
      id_pg: this.planId(),
      nom: this.nom.trim(),
      id_categorie: autre ? null : this.categorie,
      categorie_libre: autre ? this.categorieLibre.trim() : '',
    };
    const appel = this.enEdition
      ? this.rhService.updateFinanceur(this.enEdition.id_financeur, payload)
      : this.rhService.createFinanceur(payload);
    appel.subscribe({
      next: () => { this.annuler(); this.charger(); },
      error: (err) => this.erreur.set(
        err?.error?.nom?.[0] || this.translate.instant('plans.financeurs.saveError')),
    });
  }

  supprimer(f: Financeur): void {
    const msg = this.translate.instant(
      f.nb_actions ? 'plans.financeurs.deleteConfirmUsed' : 'plans.financeurs.deleteConfirm',
      { nom: f.nom, count: f.nb_actions });
    if (!window.confirm(msg)) return;
    this.rhService.deleteFinanceur(f.id_financeur).subscribe({
      next: () => this.financeurs.update((l) => l.filter((x) => x.id_financeur !== f.id_financeur)),
    });
  }
}
