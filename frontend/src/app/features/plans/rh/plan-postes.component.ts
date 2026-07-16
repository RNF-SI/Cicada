/**
 * Page « Personnes / Ressources humaines » d'un plan de gestion (#560).
 *
 * Route : /plans/:slug/personnes
 *
 * Liste les personnes rattachées au PG, avec leurs fonctions et un lien
 * facultatif vers un compte CICADA. Ajout / édition / suppression réservés
 * aux gestionnaires du plan (référent, admin organisme, super admin,
 * rédacteur principal). Ces personnes alimentent la saisie du temps de
 * travail des fiches actions.
 */
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HeaderComponent } from '../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../shared/plan-sidebar/plan-sidebar.component';
import { EntityTileComponent } from '../../../shared/components/entity-tile/entity-tile.component';
import { TagComponent } from '../../../shared/components/tag/tag.component';
import { AdminService } from '../../../core/services/admin.service';
import { AuthService } from '../../../core/services/auth.service';
import { RhService } from '../../../core/services/rh.service';
import { PersonnePlan, PersonneFonction } from '../../../core/models/rh.model';
import {
  PersonneFormDialogComponent,
  PersonneFormDialogData,
} from './personne-form-dialog/personne-form-dialog.component';

@Component({
  selector: 'app-plan-personnes',
  standalone: true,
  imports: [
    CommonModule, TranslateModule,
    MatProgressSpinnerModule, MatButtonModule, MatDialogModule,
    HeaderComponent, PlanSidebarComponent, EntityTileComponent, TagComponent,
  ],
  templateUrl: './plan-personnes.component.html',
  styleUrl: './plan-personnes.component.scss',
})
export class PlanPersonnesComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly adminService = inject(AdminService);
  private readonly authService = inject(AuthService);
  private readonly rhService = inject(RhService);
  private readonly dialog = inject(MatDialog);
  private readonly translate = inject(TranslateService);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  personnes = signal<PersonnePlan[]>([]);
  canManage = signal<boolean>(false);

  hasPersonnes = computed(() => this.personnes().length > 0);

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      const slug = params.get('slug');
      this.planSlug.set(slug);
      if (!slug) return;
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planNom.set(plan.nom);
          this.canManage.set(this.computeCanManage(plan.referents));
          this.loadPersonnes(plan.id_pg);
        },
        error: () => {
          this.errorMessage.set(
            this.translate.instant('plans.suivis.saisie.errors.planNotFound'),
          );
          this.isLoading.set(false);
        },
      });
    });
  }

  private computeCanManage(referents?: { id_role: number }[]): boolean {
    if (
      this.authService.isSuperAdmin() ||
      this.authService.isRedacteurPrincipal() ||
      this.authService.isAdminOrganisme()
    ) {
      return true;
    }
    const currentUser = this.authService.currentUser();
    if (!currentUser) return false;
    return referents?.some((r) => r.id_role === currentUser.id) || false;
  }

  private loadPersonnes(planId: number): void {
    this.isLoading.set(true);
    this.rhService.getPersonnesByPlan(planId).subscribe({
      next: (list) => {
        this.personnes.set(list);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('plans.personnes.loadError'));
        this.isLoading.set(false);
      },
    });
  }

  /**
   * Libellé d'un tag de fonction : « Garde · 60 % ».
   * La quotité arrive en décimal DRF (« 60.00 ») : on retire les zéros inutiles.
   */
  fonctionTagLabel(f: PersonneFonction): string {
    const libelle = f.fonction_libelle || '';
    if (f.pourcentage == null || f.pourcentage === '') return libelle;
    const pct = Number(f.pourcentage);
    if (!isFinite(pct)) return libelle;
    return `${libelle} · ${parseFloat(pct.toFixed(2))} %`;
  }

  /** Sous-titre d'une tuile : compte lié + dates. */
  subtitleFor(p: PersonnePlan): string {
    const parts: string[] = [];
    if (p.role_nom) parts.push(p.role_nom);
    else if (p.role_email) parts.push(p.role_email);
    if (p.date_arrivee || p.date_depart) {
      const from = p.date_arrivee || '…';
      const to = p.date_depart || '…';
      parts.push(`${from} → ${to}`);
    }
    return parts.join(' · ');
  }

  openCreate(): void {
    const planId = this.planId();
    if (planId == null) return;
    this.openDialog({ planId, personne: null });
  }

  openEdit(p: PersonnePlan): void {
    const planId = this.planId();
    if (planId == null) return;
    this.openDialog({ planId, personne: p });
  }

  private openDialog(data: PersonneFormDialogData): void {
    const ref = this.dialog.open(PersonneFormDialogComponent, {
      data,
      width: '640px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      autoFocus: false,
    });
    ref.afterClosed().subscribe((result: PersonnePlan | null) => {
      if (result) {
        const id = this.planId();
        if (id != null) this.loadPersonnes(id);
      }
    });
  }

  deletePersonne(p: PersonnePlan): void {
    if (p.id_personne_plan == null) return;
    const confirmMsg = this.translate.instant('plans.personnes.deleteConfirm', {
      nom: p.nom,
    });
    if (!window.confirm(confirmMsg)) return;
    this.rhService.deletePersonne(p.id_personne_plan).subscribe({
      next: () => {
        this.personnes.update((list) =>
          list.filter((x) => x.id_personne_plan !== p.id_personne_plan),
        );
      },
    });
  }
}
