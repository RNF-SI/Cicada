/**
 * Page « Postes / Ressources humaines » d'un plan de gestion (#560).
 *
 * Route : /plans/:slug/postes
 *
 * Liste les postes du PG — jamais de personnes nommées (RGPD) : un poste est
 * décrit par ses fonctions, son nombre d'exemplaires, son ETP total et son
 * organisme. Ajout / édition / suppression réservés aux gestionnaires du plan
 * (référent, admin organisme, super admin, rédacteur principal). Ces postes
 * alimentent la déclinaison du temps de travail des fiches actions.
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
import { Poste, PosteFonction } from '../../../core/models/rh.model';
import { posteDisplayLabel } from '../../../shared/utils/poste-label';
import {
  PosteFormDialogComponent,
  PosteFormDialogData,
} from './poste-form-dialog/poste-form-dialog.component';

@Component({
  selector: 'app-plan-postes',
  standalone: true,
  imports: [
    CommonModule, TranslateModule,
    MatProgressSpinnerModule, MatButtonModule, MatDialogModule,
    HeaderComponent, PlanSidebarComponent, EntityTileComponent, TagComponent,
  ],
  templateUrl: './plan-postes.component.html',
  styleUrl: './plan-postes.component.scss',
})
export class PlanPostesComponent implements OnInit {
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

  postes = signal<Poste[]>([]);
  canManage = signal<boolean>(false);

  hasPostes = computed(() => this.postes().length > 0);

  /** Nombre de postes distincts (une tuile = un poste). #598 */
  totalPostes = computed(() => this.postes().length);

  /** Nombre total de personnes, tous postes confondus (un poste peut compter plusieurs personnes). */
  totalPersonnes = computed(() =>
    this.postes().reduce((sum, p) => sum + (Number(p.nombre) || 0), 0),
  );

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
          this.loadPostes(plan.id_pg);
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

  private loadPostes(planId: number): void {
    this.isLoading.set(true);
    this.rhService.getPostesByPlan(planId).subscribe({
      next: (list) => {
        this.postes.set(list);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('plans.postes.loadError'));
        this.isLoading.set(false);
      },
    });
  }

  /**
   * Libellé d'un tag de fonction : « Garde » (poste combiné) ou « Garde 60 % ».
   * La quotité arrive en décimal DRF (« 60.00 ») : on retire les zéros inutiles.
   */
  fonctionTagLabel(f: PosteFonction): string {
    const libelle = f.fonction_libelle || '';
    if (f.pourcentage == null || f.pourcentage === '') return libelle;
    const pct = Number(f.pourcentage);
    if (!isFinite(pct)) return libelle;
    return `${libelle} ${parseFloat(pct.toFixed(2))} %`;
  }

  /**
   * Titre d'une tuile : le libellé dérivé des fonctions du poste. Quand
   * plusieurs postes du plan partagent le même libellé (ex. deux animateurs
   * nature créés d'un coup), on suffixe l'indice — « Animateur nature 1 / 2 »
   * (#605). Les postes regroupés (bénévoles / partenaires, uniques) ne sont
   * pas numérotés.
   */
  titleFor(p: Poste): string {
    // #611 — même numérotation que dans les listes de choix du temps de
    // travail (formulaire d'action, saisie de suivi).
    return posteDisplayLabel(
      p, this.postes(), this.translate.instant('plans.postes.untitled'),
    );
  }

  /** Sous-titre : organisme · nombre d'exemplaires. */
  subtitleFor(p: Poste): string {
    const parts: string[] = [];
    const organisme = p.organisme_affichage || p.organisme_nom || p.organisme_libre;
    if (organisme) parts.push(organisme);
    if (p.nombre > 1) {
      parts.push(this.translate.instant('plans.postes.personnesCount', { count: p.nombre }));
    }
    return parts.join(' · ');
  }

  openCreate(): void {
    const planId = this.planId();
    if (planId == null) return;
    this.openDialog({ planId, poste: null });
  }

  openEdit(p: Poste): void {
    const planId = this.planId();
    if (planId == null) return;
    this.openDialog({ planId, poste: p });
  }

  private openDialog(data: PosteFormDialogData): void {
    const ref = this.dialog.open(PosteFormDialogComponent, {
      data,
      width: '640px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      autoFocus: false,
    });
    ref.afterClosed().subscribe((result: Poste | null) => {
      if (result) {
        const id = this.planId();
        if (id != null) this.loadPostes(id);
      }
    });
  }

  deletePoste(p: Poste): void {
    if (p.id_poste == null) return;
    const confirmMsg = this.translate.instant('plans.postes.deleteConfirm', {
      libelle: this.titleFor(p),
    });
    if (!window.confirm(confirmMsg)) return;
    this.rhService.deletePoste(p.id_poste).subscribe({
      next: () => {
        this.postes.update((list) => list.filter((x) => x.id_poste !== p.id_poste));
      },
    });
  }
}
