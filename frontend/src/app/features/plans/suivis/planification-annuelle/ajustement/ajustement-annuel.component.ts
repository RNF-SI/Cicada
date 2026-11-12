import {
  ChangeDetectionStrategy, Component, OnInit, computed, inject, signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HeaderComponent } from '../../../../../shared/components/header/header.component';
import { TagComponent } from '../../../../../shared/components/tag/tag.component';
import {
  ConfirmDialogComponent, ConfirmDialogData,
} from '../../../../../shared/components/confirm-dialog/confirm-dialog.component';
import { PlanSidebarComponent } from '../../../shared/plan-sidebar/plan-sidebar.component';
import { AdminService } from '../../../../../core/services/admin.service';
import { PlanificationAnnuelleService } from '../../../../../core/services/planification-annuelle.service';
import {
  ApercuReport, ContenuAnnuel, DetailAnnuel, OrganismeAjuste, RhAjuste,
} from '../../../../../core/models/planification-annuelle.model';
import { PLANIFICATION_STATUT_TAG, TagAppearance } from '../../../../../shared/utils/tag-icons';
import {
  ChampCout, DispositionAjustement, LigneBudget, dispositionAjustement, organismeDeLaLigne,
  salaireCalcule, totauxSaisis,
} from '../ajustement-layout';
import { statutAnnuelKey } from '../plan-planification-annuelle.component';
import {
  ReportAjustementDialogComponent, ReportAjustementData,
} from '../report-dialog/report-ajustement-dialog.component';

const MOIS = Array.from({ length: 12 }, (_, i) => String(i + 1));

/** Copie profonde d'un contenu (le formulaire ne touche jamais la réponse lue). */
function copie<T>(valeur: T): T {
  return JSON.parse(JSON.stringify(valeur));
}

/**
 * #794 — Ajustement d'une action pour une année : statut, mois, temps de
 * travail, budget (selon le mode de ventilation de l'action), financeurs et
 * commentaire, à côté de la programmation du plan de gestion qui reste la
 * référence. Enregistrer marque l'action revue ; le report passe par une
 * modale avec aperçu.
 */
@Component({
  selector: 'app-ajustement-annuel',
  standalone: true,
  imports: [
    CommonModule, FormsModule, RouterModule, MatButtonModule, MatProgressSpinnerModule,
    MatTooltipModule, TranslateModule, HeaderComponent, PlanSidebarComponent, TagComponent,
  ],
  templateUrl: './ajustement-annuel.component.html',
  styleUrl: './ajustement-annuel.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class AjustementAnnuelComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly adminService = inject(AdminService);
  private readonly service = inject(PlanificationAnnuelleService);
  private readonly translate = inject(TranslateService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  readonly mois = MOIS;

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal('');
  planStatut = signal<string | null>(null);
  operationId = signal<number | null>(null);
  annee = signal<number | null>(null);

  isLoading = signal(true);
  enregistrement = signal(false);
  errorMessage = signal<string | null>(null);

  detail = signal<DetailAnnuel | null>(null);
  /** Contenu en cours de saisie (copie de l'effectif). */
  contenu: ContenuAnnuel = { statut: 'planifiee' };
  private reference = '';

  /** Actions du plan dans l'ordre du tableau, pour passer à la suivante. */
  ordre = signal<number[]>([]);

  disposition = computed<DispositionAjustement | null>(() => {
    const d = this.detail();
    return d ? dispositionAjustement(d.reglages) : null;
  });

  planNonValide = computed(() => {
    const s = this.planStatut();
    return !!s && !['valide', 'modifie', 'mi_parcours', 'archive'].includes(s);
  });
  lectureSeule = computed(() => !this.detail()?.peut_saisir);

  precedente = computed(() => this.voisine(-1));
  suivante = computed(() => this.voisine(1));

  ngOnInit(): void {
    const params = this.route.snapshot.paramMap;
    const slug = params.get('slug');
    this.planSlug.set(slug);
    this.route.paramMap.subscribe(p => {
      this.operationId.set(Number(p.get('operation_id')));
      this.annee.set(Number(p.get('annee')));
      if (this.planId()) this.charger();
    });
    if (!slug) return;
    this.adminService.getPlanBySlug(slug).subscribe({
      next: (plan) => {
        this.planId.set(plan.id_pg);
        this.planNom.set(plan.nom);
        this.planStatut.set(plan.statut ?? null);
        this.charger();
        this.chargerOrdre();
      },
      error: () => this.echec(),
    });
  }

  charger(): void {
    const op = this.operationId(), annee = this.annee();
    if (!op || !annee) return;
    this.isLoading.set(true);
    this.errorMessage.set(null);
    this.service.detail(op, annee).subscribe({
      next: (detail) => this.afficher(detail),
      error: (err) => this.echec(err?.status),
    });
  }

  private chargerOrdre(): void {
    const planId = this.planId(), annee = this.annee();
    if (!planId || !annee) return;
    this.service.tableau(planId, annee).subscribe({
      next: (t) => this.ordre.set(t.actions.map(a => a.id_operation)),
      error: () => this.ordre.set([]),
    });
  }

  private afficher(detail: DetailAnnuel): void {
    this.detail.set(detail);
    const contenu = copie(detail.effectif);
    contenu.organismes ??= [];
    contenu.rh_lignes ??= [];
    contenu.financeurs ??= [];
    contenu.periodicite_mensuelle ??= {};
    this.contenu = contenu;
    this.completerTemps();
    this.reference = JSON.stringify(this.contenu);
    this.isLoading.set(false);
  }

  private echec(status?: number): void {
    this.isLoading.set(false);
    this.errorMessage.set(this.translate.instant(status === 403
      ? 'plans.suivis.planificationAnnuelle.accesRefuse'
      : 'plans.suivis.planificationAnnuelle.erreurChargement'));
  }

  private voisine(sens: number): number | null {
    const ordre = this.ordre(), op = this.operationId();
    const i = op ? ordre.indexOf(op) : -1;
    return i < 0 ? null : ordre[i + sens] ?? null;
  }

  // --- État de la saisie -------------------------------------------------------

  modifie(): boolean {
    return JSON.stringify(this.contenu) !== this.reference;
  }

  planifiee(): boolean {
    return this.contenu.statut === 'planifiee';
  }

  reportee(): boolean {
    return this.contenu.statut === 'reportee';
  }

  /** Années vers lesquelles l'action peut être reportée. */
  anneesReport(): number[] {
    const d = this.detail(), annee = this.annee();
    return d && annee ? d.annees.filter(a => a > annee) : [];
  }

  choisirStatut(statut: 'planifiee' | 'non_prevue'): void {
    if (this.lectureSeule()) return;
    this.contenu.statut = statut;
    if (statut === 'planifiee' && !this.contenu.organismes?.length && !this.contenu.rh_lignes?.length) {
      // Repartir de la programmation du plan de gestion plutôt que de zéro.
      const pg = copie(this.detail()!.pg);
      Object.assign(this.contenu, pg, { statut, commentaire: this.contenu.commentaire });
    }
    this.completerTemps();
  }

  /**
   * Lignes de temps attendues par la disposition, ajoutées vides : une par
   * organisme (temps par organisme), ou la ligne du temps total. Les lignes
   * restées vides ne partent pas au serveur.
   */
  private completerTemps(): void {
    const mode = this.disposition()?.rhMode;
    const lignes = [...(this.contenu.rh_lignes ?? [])];
    if (mode === 'organismes') {
      for (const org of this.contenu.organismes ?? []) {
        if (!lignes.some(l => l.id_poste == null && l.id_organisme === org.id_organisme)) {
          lignes.push({ id_organisme: org.id_organisme, jours: null, finance: true,
            categorie_depense: 'fonctionnement' });
        }
      }
    } else if (mode === 'global' && !lignes.some(l => l.id_poste == null && l.id_organisme == null)) {
      lignes.push({ jours: null, finance: true, categorie_depense: 'fonctionnement' });
    }
    this.contenu.rh_lignes = lignes;
  }

  basculerMois(m: string): void {
    if (this.lectureSeule() || !this.planifiee()) return;
    const mois = { ...(this.contenu.periodicite_mensuelle ?? {}) };
    if (mois[m]) delete mois[m]; else mois[m] = true;
    this.contenu.periodicite_mensuelle = mois;
  }

  moisActif(m: string): boolean {
    return !!this.contenu.periodicite_mensuelle?.[m];
  }

  moisPg(m: string): boolean {
    return !!this.detail()?.pg.periodicite_mensuelle?.[m];
  }

  moisCourt(m: string): string {
    return this.translate.instant('plans.suivis.planification.monthsShort').split(',')[Number(m) - 1];
  }

  // --- Organismes et budget ----------------------------------------------------

  nomOrganisme(id: number | null | undefined): string {
    return this.detail()?.choix.organismes.find(o => o.id_organisme === id)?.nom ?? '—';
  }

  organismesDisponibles(): { id_organisme: number; nom: string }[] {
    const pris = new Set((this.contenu.organismes ?? []).map(o => o.id_organisme));
    return (this.detail()?.choix.organismes ?? []).filter(o => !pris.has(o.id_organisme));
  }

  ajouterOrganisme(id: number | string | null): void {
    if (id == null || id === '') return;
    this.contenu.organismes = [...(this.contenu.organismes ?? []), { id_organisme: Number(id) }];
    this.completerTemps();
  }

  retirerOrganisme(org: OrganismeAjuste): void {
    this.contenu.organismes = (this.contenu.organismes ?? []).filter(o => o !== org);
    this.contenu.rh_lignes = (this.contenu.rh_lignes ?? []).filter(
      l => l.id_poste != null || l.id_organisme !== org.id_organisme);
  }

  /** Valeur du plan de gestion pour un champ (année ou organisme). */
  valeurPg(champ: ChampCout, organisme?: number): number | null {
    const pg = this.detail()?.pg;
    if (!pg) return null;
    const source = organisme === undefined
      ? (pg as unknown as Record<string, string | null>)
      : (pg.organismes?.find(o => o.id_organisme === organisme) as unknown as Record<string, string | null>);
    const v = source?.[champ];
    return v == null || v === '' ? null : Number(v);
  }

  /** Coût salarial calculé (jours × coût jour), affiché à la place du champ. */
  salaire(ligne: LigneBudget, organisme?: number): number {
    const d = this.detail();
    return d ? salaireCalcule(this.contenu, d.choix, ligne.invest, organisme) : 0;
  }

  salairePg(ligne: LigneBudget, organisme?: number): number {
    const d = this.detail();
    return d ? salaireCalcule(d.pg, d.choix, ligne.invest, organisme) : 0;
  }

  lignesFonct(): LigneBudget[] {
    return this.disposition()?.lignes.filter(l => !l.invest) ?? [];
  }

  lignesInvest(): LigneBudget[] {
    return this.disposition()?.lignes.filter(l => l.invest) ?? [];
  }

  // --- Temps de travail --------------------------------------------------------

  libellePoste(id: number | null | undefined): string {
    return this.detail()?.choix.postes.find(p => p.id_poste === id)?.libelle ?? '—';
  }

  postesDisponibles(): { id_poste: number; libelle: string }[] {
    const pris = new Set((this.contenu.rh_lignes ?? []).map(l => l.id_poste));
    return (this.detail()?.choix.postes ?? []).filter(p => !pris.has(p.id_poste));
  }

  ajouterPoste(id: number | string | null): void {
    if (id == null || id === '') return;
    const poste = this.detail()?.choix.postes.find(p => p.id_poste === Number(id));
    if (!poste) return;
    this.contenu.rh_lignes = [...(this.contenu.rh_lignes ?? []), {
      id_poste: poste.id_poste, jours: null, finance: poste.finance_par_defaut,
      categorie_depense: poste.finance_par_defaut ? 'fonctionnement' : 'benevolat_partenariat',
    }];
  }

  /** Lignes de temps par organisme : une par organisme de l'action. */
  lignesParOrganisme(): RhAjuste[] {
    return (this.contenu.rh_lignes ?? []).filter(l => l.id_poste == null && l.id_organisme != null);
  }

  /** Temps total (sans poste ni organisme) : une seule ligne. */
  lignesGlobales(): RhAjuste[] {
    return (this.contenu.rh_lignes ?? []).filter(l => l.id_poste == null && l.id_organisme == null);
  }

  lignesPostes(): RhAjuste[] {
    return (this.contenu.rh_lignes ?? []).filter(l => l.id_poste != null);
  }

  retirerLigne(ligne: RhAjuste): void {
    this.contenu.rh_lignes = (this.contenu.rh_lignes ?? []).filter(l => l !== ligne);
  }

  joursPg(ligne: RhAjuste): number | null {
    const pg = this.detail()?.pg.rh_lignes ?? [];
    const meme = pg.filter(l => (l.id_poste ?? null) === (ligne.id_poste ?? null)
      && (ligne.id_poste != null || (l.id_organisme ?? null) === (ligne.id_organisme ?? null)));
    if (!meme.length) return null;
    return meme.reduce((t, l) => t + Number(l.jours ?? 0), 0);
  }

  organismeDuPoste(ligne: RhAjuste): string {
    const d = this.detail();
    return d ? this.nomOrganisme(organismeDeLaLigne(ligne, d.choix)) : '';
  }

  // --- Financeurs --------------------------------------------------------------

  nomFinanceur(id: number): string {
    return this.detail()?.choix.financeurs.find(f => f.id_financeur === id)?.nom ?? '—';
  }

  montantPgFinanceur(id: number): string | null {
    return this.detail()?.financeurs_pg.find(f => f.id_financeur === id)?.montant ?? null;
  }

  financeursDisponibles(): { id_financeur: number; nom: string }[] {
    const pris = new Set((this.contenu.financeurs ?? []).map(f => f.id_financeur));
    return (this.detail()?.choix.financeurs ?? []).filter(f => !pris.has(f.id_financeur));
  }

  ajouterFinanceur(id: number | string | null): void {
    if (id == null || id === '') return;
    this.contenu.financeurs = [...(this.contenu.financeurs ?? []), { id_financeur: Number(id), montant: null }];
  }

  retirerFinanceur(id: number): void {
    this.contenu.financeurs = (this.contenu.financeurs ?? []).filter(f => f.id_financeur !== id);
  }

  // --- Totaux ------------------------------------------------------------------

  totaux(): { budget: number; jours: number } {
    const d = this.detail();
    return d ? totauxSaisis(this.contenu, d.choix, d.reglages) : { budget: 0, jours: 0 };
  }

  num(valeur: string | number | null | undefined): number {
    return Number(valeur ?? 0);
  }

  tag(): TagAppearance {
    const r = this.detail()?.effectif_resume;
    return r ? PLANIFICATION_STATUT_TAG[statutAnnuelKey(r)] : PLANIFICATION_STATUT_TAG['non_prevue'];
  }

  statutLabel(): string {
    const r = this.detail()?.effectif_resume;
    if (!r) return '';
    return this.translate.instant(
      `plans.suivis.planificationAnnuelle.statut.${statutAnnuelKey(r)}`, { annee: r.annee_report });
  }

  // --- Actions -----------------------------------------------------------------

  /** Enregistre l'ajustement (l'action est revue) ; `ensuite` : action suivante. */
  enregistrer(ensuite = false): void {
    const op = this.operationId(), annee = this.annee();
    if (!op || !annee || this.lectureSeule()) return;
    this.enregistrement.set(true);
    this.service.enregistrer(op, annee, this.contenuAEnvoyer()).subscribe({
      next: (detail) => {
        this.enregistrement.set(false);
        this.snackBar.open(this.translate.instant('plans.suivis.planificationAnnuelle.ajustement.enregistre'),
          this.translate.instant('common.actions.close'), { duration: 3000 });
        const suivante = this.suivante();
        if (ensuite && suivante) {
          this.allerA(suivante);
        } else {
          this.afficher(detail);
        }
      },
      error: (err) => {
        this.enregistrement.set(false);
        this.snackBar.open(this.messageErreur(err),
          this.translate.instant('common.actions.close'), { duration: 6000 });
      },
    });
  }

  /** Lignes vides retirées : seules les saisies partent au serveur. */
  private contenuAEnvoyer(): ContenuAnnuel {
    const c = copie(this.contenu);
    c.rh_lignes = (c.rh_lignes ?? []).filter(l => l.jours != null && String(l.jours) !== '');
    c.financeurs = (c.financeurs ?? []).filter(f => f.id_financeur != null);
    for (const ligne of c.rh_lignes) {
      ligne.finance = ligne.categorie_depense !== 'benevolat_partenariat';
    }
    return c;
  }

  private messageErreur(err: { error?: Record<string, unknown> } | null): string {
    const e = err?.error;
    if (e && typeof e['detail'] === 'string') return e['detail'];
    if (e) {
      const premier = Object.values(e)[0];
      if (Array.isArray(premier) && typeof premier[0] === 'string') return premier[0];
      if (typeof premier === 'string') return premier;
    }
    return this.translate.instant('plans.suivis.planificationAnnuelle.ajustement.erreurEnregistrement');
  }

  revenirAuPlan(): void {
    const op = this.operationId(), annee = this.annee();
    if (!op || !annee) return;
    const data: ConfirmDialogData = {
      title: this.translate.instant('plans.suivis.planificationAnnuelle.ajustement.revenirTitre'),
      message: this.translate.instant('plans.suivis.planificationAnnuelle.ajustement.revenirMessage'),
      confirmText: this.translate.instant('plans.suivis.planificationAnnuelle.ajustement.revenir'),
    };
    this.dialog.open(ConfirmDialogComponent, { data, width: '560px', maxWidth: '95vw' })
      .afterClosed().subscribe(ok => {
        if (!ok) return;
        this.service.revenirAuPlan(op, annee).subscribe({
          next: () => this.charger(),
          error: (err) => this.snackBar.open(this.messageErreur(err),
            this.translate.instant('common.actions.close'), { duration: 6000 }),
        });
      });
  }

  reporter(): void {
    const d = this.detail(), annee = this.annee();
    if (!d || !annee) return;
    const data: ReportAjustementData = {
      operationId: d.id_operation, annee, annees: this.anneesReport(),
      libelle: `${d.code} ${d.libelle}`.trim(),
    };
    this.dialog.open(ReportAjustementDialogComponent, {
      data, width: '1300px', maxWidth: '95vw', maxHeight: '90vh',
    }).afterClosed().subscribe((resultat?: ApercuReport) => {
      if (!resultat) return;
      this.snackBar.open(this.translate.instant('plans.suivis.planificationAnnuelle.report.fait',
        { annee: resultat.annee_report }), this.translate.instant('common.actions.close'), { duration: 4000 });
      this.charger();
    });
  }

  allerA(operationId: number): void {
    this.router.navigate(['/plans', this.planSlug(), 'planification-annuelle', operationId, this.annee()]);
  }

  retourTableau(): void {
    this.router.navigate(['/plans', this.planSlug(), 'planification-annuelle'],
      { queryParams: { annee: this.annee() } });
  }
}
