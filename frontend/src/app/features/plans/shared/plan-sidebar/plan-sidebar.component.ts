import { Component, OnInit, input, inject, signal, computed, effect, untracked } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AuthService } from '../../../../core/services/auth.service';
import { AdminService } from '../../../../core/services/admin.service';
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
  private readonly authService = inject(AuthService);
  private readonly adminService = inject(AdminService);

  planId = input.required<number>();
  planSlug = input.required<string>();
  activePage = input<'overview' | 'enjeux' | 'bilan' | 'suivi-actions' | 'tableau-de-bord' | 'mindmap' | 'settings' | 'postes' | 'exports'>('overview');
  selectedEnjeuSlug = input<string | null>(null);
  /** #348 — Affiche l'entrée « Paramètres » (gestion avancée des versions),
   *  réservée au référent du plan, admin organisme et super admin.
   *  #578 — Override optionnel : `null` (défaut) → la sidebar calcule le droit
   *  elle-même (voir `effectiveCanManage`) pour que la section « Paramétrage »
   *  reste visible sur TOUTES les pages du PG, pas seulement overview/paramètres/postes.
   *  Une valeur explicite (fournie par la page) court-circuite ce calcul et le fetch. */
  canManage = input<boolean | null>(null);

  /** #578 — Référents du plan, chargés à la demande pour évaluer le droit de gestion
   *  quand aucun override n'est fourni et que le rôle seul ne suffit pas. */
  private readonly planReferentIds = signal<number[]>([]);

  /** Accès gestion via le rôle seul (aucune donnée du plan requise). */
  private readonly roleCanManage = computed(() =>
    this.authService.isSuperAdmin() ||
    this.authService.isRedacteurPrincipal() ||
    this.authService.isAdminOrganisme()
  );

  /** #578 — Droit effectif d'afficher la section « Paramétrage »
   *  (Paramètres, Postes). Réservé au référent du plan, admin_og, super_admin
   *  et rédacteur principal — aligné sur `canManageLifecycle` de plan-detail. */
  effectiveCanManage = computed(() => {
    const override = this.canManage();
    if (override !== null) return override;
    if (this.roleCanManage()) return true;
    const userId = this.authService.currentUser()?.id;
    return userId != null && this.planReferentIds().includes(userId);
  });

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
  parametrageMenuExpanded = signal(true);
  detailsMenuExpanded = signal(true);
  suivisMenuExpanded = signal(true);

  isSuivisActive = computed(() => {
    const page = this.activePage();
    return page === 'bilan' || page === 'suivi-actions' || page === 'tableau-de-bord';
  });

  /** #610 — La section « Suivis » (Bilan, Suivi des actions, Tableau de bord)
   *  est réservée aux référents du plan et gestionnaires (admin_og, super_admin,
   *  rédacteur principal) — même audience que « Paramétrage ». Un utilisateur
   *  simplement lié au plan (non référent) ne doit pas voir les suivis. */
  canViewSuivis = computed(() => this.effectiveCanManage());

  /** Les exports extraient l'intégralité du contenu du plan : ils sont réservés
   *  aux référents du plan et gestionnaires (admin_og, super_admin, rédacteur
   *  principal), au même titre que « Paramétrage » et « Suivis ». Un utilisateur
   *  simplement lié au plan le consulte en lecture seule mais n'exporte pas. */
  canViewExports = computed(() => this.effectiveCanManage());

  isMindmapActive = computed(() => this.activePage() === 'mindmap');

  /** #583 — La section « Paramétrage » couvre les pages Paramètres et Postes/RH. */
  isParametrageActive = computed(() => {
    const page = this.activePage();
    return page === 'settings' || page === 'postes';
  });

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

    // #578 — Récupère les référents du plan pour déterminer le droit de gestion
    // quand aucun override n'est fourni et que le rôle seul ne suffit pas (cas
    // d'un simple utilisateur référent du plan). Évite tout fetch inutile sinon.
    effect(() => {
      const planId = this.planId();
      if (this.canManage() !== null) return; // la page fournit déjà le droit
      if (this.roleCanManage()) return;       // rôle suffisant, référents inutiles
      if (!planId) return;
      untracked(() => {
        this.adminService.getPlan(planId).subscribe({
          next: p => this.planReferentIds.set((p.referents || []).map(r => r.id_role)),
          error: () => this.planReferentIds.set([]),
        });
      });
    });
  }

  ngOnInit(): void {
    // Le chargement initial est géré par l'effect dans le constructeur
  }

  toggleParametrageMenu(): void {
    this.parametrageMenuExpanded.update(v => !v);
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

  navigateToSettings(): void {
    this.router.navigate(['/plans', this.planSlug(), 'parametres']);
  }

  navigateToPostes(): void {
    this.router.navigate(['/plans', this.planSlug(), 'postes']);
  }

  /** #617 — Zone « Exports », réservée aux référents/gestionnaires du plan. */
  navigateToExports(): void {
    this.router.navigate(['/plans', this.planSlug(), 'exports']);
  }
}
