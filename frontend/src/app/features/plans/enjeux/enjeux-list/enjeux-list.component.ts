/**
 * Composant pour afficher la liste des Enjeux et FCR d'un plan.
 * - Sans enjeu sélectionné : liste plate de cartes accordéon
 * - Avec enjeu sélectionné (route :enjeuId) : vue détail avec 3 onglets
 */
import { Component, OnInit, DestroyRef, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { forkJoin, Observable } from 'rxjs';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { PlanSidebarComponent } from '../../shared/plan-sidebar/plan-sidebar.component';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import {
  Enjeu, FacteurInfluence, Pression, PlanEnjeuxResponse,
  EtatActuel, ObjectifLongTerme, NiveauExigence, Indicateur, Metrique,
  MetriqueFormData, MetriqueCreatePayload, Operation, OperationAnnee,
  ObjectifOperationnel, ResultatAttendu
} from '../../../../core/models/enjeu.model';
import { EnjeuAccordionComponent } from '../enjeu-accordion/enjeu-accordion.component';
import { SectionTitleComponent } from '../../../../shared/components/section-title/section-title.component';

type TabType = 'detail' | 'olt' | 'operations';

@Component({
  selector: 'app-enjeux-list',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    MatProgressSpinnerModule,
    MatButtonModule,
    MatMenuModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatRadioModule,
    MatDialogModule,
    MatSnackBarModule,
    TranslateModule,
    HeaderComponent,
    PlanSidebarComponent,
    EnjeuAccordionComponent,
    SectionTitleComponent
  ],
  templateUrl: './enjeux-list.component.html',
  styleUrl: './enjeux-list.component.scss'
})
export class EnjeuxListComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly enjeuService = inject(EnjeuService);
  private readonly adminService = inject(AdminService);
  private readonly translate = inject(TranslateService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly destroyRef = inject(DestroyRef);

  planId = signal<number | null>(null);
  planNom = signal<string>('');
  planAnneeDebut = signal<number | null>(null);
  planAnneeFin = signal<number | null>(null);
  isLoading = signal(true);
  errorMessage = signal<string | null>(null);

  planEnjeuxData = signal<PlanEnjeuxResponse | null>(null);

  // Onglet actif (vue détail uniquement)
  activeTab = signal<TabType>('detail');

  // Enjeu sélectionné (via route :enjeuId)
  selectedEnjeuId = signal<number | null>(null);

  // Expand/collapse state pour la vue détail
  enjeuDetailExpanded = signal(true);
  expandedFcrIds = signal<Set<number>>(new Set());

  // Facteurs d'influence / Pressions state
  expandedFacteurIds = signal<Set<number>>(new Set());
  expandedPressionIds = signal<Set<number>>(new Set());
  addingFacteurInfluence = signal(false);
  addingPressionForFacteur = signal<number | null>(null);
  newFacteurLibelle = '';
  newFacteurDescription = '';
  newPressionLibelle = '';
  newPressionDescription = '';

  // OLT / Niveaux d'exigence state
  expandedOltIds = signal<Set<number>>(new Set());
  expandedEtatIds = signal<Set<number>>(new Set());
  addingEtatForOlt = signal<number | null>(null);
  addingOlt = signal(false);
  addingNeForOlt = signal<number | null>(null);
  editingEtatId = signal<number | null>(null);
  editingOltId = signal<number | null>(null);
  editingNeId = signal<number | null>(null);
  newEtatLibelle = '';
  newEtatDescription = '';
  editEtatLibelle = '';
  editEtatDescription = '';
  newOltLibelle = '';
  newOltDescription = '';
  newNeLibelle = '';
  newNeDescription = '';
  editOltLibelle = '';
  editOltDescription = '';
  editNeLibelle = '';
  editNeDescription = '';

  // Opérations expand/collapse
  expandedOperationIds = signal<Set<number>>(new Set());

  // Indicateurs state
  expandedIndicateurIds = signal<Set<number>>(new Set());
  addingIndicateurForNe = signal<number | null>(null);
  editingIndicateurId = signal<number | null>(null);
  newIndicateurNom = '';
  newIndicateurType: number | null = null;
  newIndicateurStandardise = false;
  newIndicateurDescription = '';
  editIndicateurNom = '';
  editIndicateurType: number | null = null;
  editIndicateurStandardise = false;
  editIndicateurDescription = '';

  // Unified indicateur form state (indicateur + inline metriques)
  indicateurFormMetriques: MetriqueFormData[] = [];
  // Edit indicateur: metriques inline editing
  editIndicateurMetriques: MetriqueFormData[] = [];
  typeMetriqueOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);
  isSavingIndicateur = signal(false);

  // OO (Objectifs Opérationnels) state
  expandedOoIds = signal<Set<number>>(new Set());
  addingOo = signal(false);
  editingOoId = signal<number | null>(null);
  newOoLibelle = '';
  newOoDescription = '';
  newOoFacteurId: number | null = null;
  editOoLibelle = '';
  editOoDescription = '';
  editOoFacteurId: number | null = null;

  // Résultat Attendu state
  addingRaForOo = signal<number | null>(null);
  editingRaId = signal<number | null>(null);
  newRaLibelle = '';
  newRaDescription = '';
  editRaLibelle = '';
  editRaDescription = '';

  // Indicateurs pression (for OO tab)
  addingIndicateurForRa = signal<number | null>(null);
  editingOoIndicateurId = signal<number | null>(null);
  newOoIndicateurNom = '';
  newOoIndicateurType: number | null = null;
  newOoIndicateurStandardise = false;
  newOoIndicateurDescription = '';
  editOoIndicateurNom = '';
  editOoIndicateurType: number | null = null;
  editOoIndicateurStandardise = false;
  editOoIndicateurDescription = '';
  ooIndicateurFormMetriques: MetriqueFormData[] = [];
  editOoIndicateurMetriques: MetriqueFormData[] = [];
  isSavingOoIndicateur = signal(false);
  expandedOoIndicateurIds = signal<Set<number>>(new Set());
  expandedOoOperationIds = signal<Set<number>>(new Set());

  // Enjeux et FCR séparés
  enjeux = computed(() => {
    const data = this.planEnjeuxData();
    return data?.enjeux || [];
  });

  fcr = computed(() => {
    const data = this.planEnjeuxData();
    return data?.fcr || [];
  });

  // Compteur total
  totalCount = computed(() => {
    const data = this.planEnjeuxData();
    return data ? data.total_enjeux + data.total_fcr : 0;
  });

  hasData = computed(() => this.totalCount() > 0);

  // Enjeu sélectionné
  selectedEnjeu = computed(() => {
    const id = this.selectedEnjeuId();
    if (!id) return null;

    const enjeu = this.enjeux().find(e => e.id_enjeu === id);
    if (enjeu) return enjeu;

    const fcrItem = this.fcr().find(f => f.id_enjeu === id);
    return fcrItem || null;
  });

  // Computed helpers pour la vue détail de l'enjeu sélectionné
  isSelectedFcr = computed(() => {
    return this.selectedEnjeu()?.categorie_mnemonique === 'FCR';
  });

  selectedCategoryLabel = computed(() => {
    const enjeu = this.selectedEnjeu();
    if (!enjeu) return '';
    if (enjeu.categorie_ecologique === true) {
      return this.translate.instant('enjeux.enjeuForm.ecologique');
    } else if (enjeu.categorie_ecologique === false) {
      return this.translate.instant('enjeux.enjeuForm.socioEconomique');
    }
    return '';
  });

  selectedTypeLabels = computed(() => {
    const enjeu = this.selectedEnjeu();
    if (!enjeu) return [];
    const labels: string[] = [];
    if (enjeu.habitat) labels.push(this.translate.instant('enjeux.accordion.habitats'));
    if (enjeu.espece) labels.push(this.translate.instant('enjeux.accordion.especes'));
    if (enjeu.processus) labels.push(this.translate.instant('enjeux.accordion.processus'));
    return labels;
  });

  selectedHasTaxons = computed(() => {
    const enjeu = this.selectedEnjeu();
    return (enjeu?.taxons?.length || 0) > 0 || (enjeu?.nb_taxons || 0) > 0;
  });

  selectedFcrCategoryLabel = computed(() => {
    return this.selectedEnjeu()?.categorie_fcr_label || '';
  });

  // Index d'affichage de l'enjeu sélectionné (1-based)
  selectedDisplayIndex = computed(() => {
    const id = this.selectedEnjeuId();
    if (!id) return 0;
    const idx = this.enjeux().findIndex(e => e.id_enjeu === id);
    if (idx >= 0) return idx + 1;
    const fcrIdx = this.fcr().findIndex(f => f.id_enjeu === id);
    if (fcrIdx >= 0) return fcrIdx + 1;
    return 0;
  });

  ngOnInit(): void {
    // Récupérer l'ID du plan depuis les paramètres parent
    const parentParams = this.route.parent?.snapshot.paramMap;
    const id = parentParams?.get('id') || this.route.snapshot.paramMap.get('planId');

    if (id) {
      this.planId.set(parseInt(id, 10));
      this.loadPlanData();
    } else {
      this.errorMessage.set('ID du plan non trouvé');
      this.isLoading.set(false);
    }

    // Écouter les changements de l'enjeuId dans la route
    this.route.params.pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(params => {
      const enjeuId = params['enjeuId'];
      if (enjeuId) {
        this.selectedEnjeuId.set(parseInt(enjeuId, 10));
        this.enjeuDetailExpanded.set(true);
        this.activeTab.set('detail');
      } else {
        this.selectedEnjeuId.set(null);
      }
    });
  }

  loadPlanData(): void {
    const id = this.planId();
    if (!id) return;

    this.isLoading.set(true);
    this.errorMessage.set(null);

    // Charger les infos du plan
    this.adminService.getPlan(id).subscribe({
      next: (plan) => {
        this.planNom.set(plan.nom);
        this.planAnneeDebut.set(plan.annee_debut || null);
        this.planAnneeFin.set(plan.annee_fin || null);
      },
      error: () => {
        // Non bloquant, on continue
      }
    });

    // Charger les enjeux et FCR
    this.enjeuService.getPlanEnjeux(id).subscribe({
      next: (response) => {
        this.planEnjeuxData.set(response);
        this.isLoading.set(false);
      },
      error: () => {
        this.errorMessage.set(
          this.translate.instant('enjeux.messages.loadError')
        );
        this.isLoading.set(false);
      }
    });
  }

  // Navigation
  navigateToNewEnjeu(): void {
    const planId = this.planId();
    if (planId) {
      this.router.navigate(['/plans', planId, 'enjeux', 'nouveau']);
    }
  }

  navigateToNewFcr(): void {
    const planId = this.planId();
    if (planId) {
      this.router.navigate(['/plans', planId, 'enjeux', 'fcr', 'nouveau']);
    }
  }

  navigateToEdit(item: Enjeu): void {
    const planId = this.planId();
    if (!planId) return;

    if (item.categorie_mnemonique === 'FCR') {
      this.router.navigate(['/plans', planId, 'enjeux', 'fcr', item.id_enjeu, 'modifier']);
    } else {
      this.router.navigate(['/plans', planId, 'enjeux', item.id_enjeu, 'modifier']);
    }
  }

  // Onglets (vue détail)
  setActiveTab(tab: TabType): void {
    this.activeTab.set(tab);
  }

  // Toggle detail card expand/collapse
  toggleEnjeuDetail(): void {
    this.enjeuDetailExpanded.update(v => !v);
  }

  // Toggle FCR card expand/collapse
  toggleFcr(id: number): void {
    this.expandedFcrIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isFcrExpanded(id: number): boolean {
    return this.expandedFcrIds().has(id);
  }

  // Computed pour les facteurs d'influence de l'enjeu sélectionné
  selectedFacteurs = computed(() => {
    return this.selectedEnjeu()?.facteurs_influence || [];
  });

  // Computed pour les OLTs de l'enjeu sélectionné
  selectedOlts = computed(() => {
    return this.selectedEnjeu()?.objectifs_long_terme || [];
  });

  totalOltCount = computed(() => {
    return this.selectedOlts().length;
  });

  // Computed pour les OOs de l'enjeu sélectionné
  selectedOos = computed(() => {
    return this.selectedEnjeu()?.objectifs_operationnels || [];
  });

  totalOoCount = computed(() => {
    return this.selectedOos().length;
  });

  // Event handlers pour les accordéons
  onEnjeuDelete(enjeu: Enjeu): void {
    this.enjeuService.deleteEnjeu(enjeu.id_enjeu).subscribe({
      next: () => {
        // Si l'enjeu supprimé était sélectionné, retourner à la liste
        if (this.selectedEnjeuId() === enjeu.id_enjeu) {
          const planId = this.planId();
          if (planId) {
            this.router.navigate(['/plans', planId, 'enjeux']);
          }
        }
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(
          this.translate.instant('enjeux.messages.deleteError')
        );
      }
    });
  }

  // Navigation vers le détail depuis l'accordéon
  navigateToEnjeuDetail(enjeu: Enjeu): void {
    const planId = this.planId();
    if (planId) {
      this.router.navigate(['/plans', planId, 'enjeux', enjeu.id_enjeu]);
    }
  }

  // ============================================
  // Facteurs d'Influence
  // ============================================

  toggleFacteur(id: number): void {
    this.expandedFacteurIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isFacteurExpanded(id: number): boolean {
    return this.expandedFacteurIds().has(id);
  }

  startAddFacteur(): void {
    this.addingFacteurInfluence.set(true);
    this.newFacteurLibelle = '';
    this.newFacteurDescription = '';
  }

  cancelAddFacteur(): void {
    this.addingFacteurInfluence.set(false);
    this.newFacteurLibelle = '';
    this.newFacteurDescription = '';
  }

  saveFacteurInfluence(): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu || !this.newFacteurLibelle.trim()) return;

    this.enjeuService.createFacteurInfluence({
      id_enjeu: enjeu.id_enjeu,
      libelle: this.newFacteurLibelle.trim(),
      description: this.newFacteurDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.facteurInfluence.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddFacteur();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  deleteFacteur(facteur: FacteurInfluence): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.facteurInfluence.deleteTitle'),
        message: this.translate.instant('enjeux.facteurInfluence.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteFacteurInfluence(facteur.id_facteur_influence).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.facteurInfluence.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData();
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Pressions
  // ============================================

  togglePression(id: number): void {
    this.expandedPressionIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isPressionExpanded(id: number): boolean {
    return this.expandedPressionIds().has(id);
  }

  startAddPression(facteurId: number): void {
    this.addingPressionForFacteur.set(facteurId);
    this.newPressionLibelle = '';
    this.newPressionDescription = '';
  }

  cancelAddPression(): void {
    this.addingPressionForFacteur.set(null);
    this.newPressionLibelle = '';
    this.newPressionDescription = '';
  }

  savePression(facteur: FacteurInfluence): void {
    if (!this.newPressionLibelle.trim()) return;

    this.enjeuService.createPression({
      id_facteur_influence: facteur.id_facteur_influence,
      libelle: this.newPressionLibelle.trim(),
      description: this.newPressionDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.pression.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddPression();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  deletePression(pression: Pression): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.pression.deleteTitle'),
        message: this.translate.instant('enjeux.pression.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deletePression(pression.id_pression).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.pression.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData();
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // États Actuels
  // ============================================

  startAddEtat(oltId: number): void {
    this.addingEtatForOlt.set(oltId);
    this.newEtatLibelle = '';
    this.newEtatDescription = '';
  }

  cancelAddEtat(): void {
    this.addingEtatForOlt.set(null);
    this.newEtatLibelle = '';
    this.newEtatDescription = '';
  }

  saveEtatActuel(olt: ObjectifLongTerme): void {
    if (!this.newEtatLibelle.trim()) return;

    this.enjeuService.createEtatActuel({
      id_olt: olt.id_olt,
      libelle: this.newEtatLibelle.trim(),
      description: this.newEtatDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.etatActuel.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddEtat();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  deleteEtatActuel(etat: EtatActuel): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.etatActuel.deleteTitle'),
        message: this.translate.instant('enjeux.etatActuel.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteEtatActuel(etat.id_etat_actuel).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.etatActuel.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData();
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  startEditEtat(etat: EtatActuel): void {
    this.editingEtatId.set(etat.id_etat_actuel);
    this.editEtatLibelle = etat.libelle;
    this.editEtatDescription = etat.description || '';
  }

  cancelEditEtat(): void {
    this.editingEtatId.set(null);
    this.editEtatLibelle = '';
    this.editEtatDescription = '';
  }

  saveEditEtat(etat: EtatActuel): void {
    if (!this.editEtatLibelle.trim()) return;

    this.enjeuService.updateEtatActuel(etat.id_etat_actuel, {
      libelle: this.editEtatLibelle.trim(),
      description: this.editEtatDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.etatActuel.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditEtat();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  // ============================================
  // Objectifs à Long Terme (OLT)
  // ============================================

  toggleOlt(id: number): void {
    this.expandedOltIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isOltExpanded(id: number): boolean {
    return this.expandedOltIds().has(id);
  }

  toggleEtat(id: number): void {
    this.expandedEtatIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isEtatExpanded(id: number): boolean {
    return this.expandedEtatIds().has(id);
  }

  startAddOlt(): void {
    this.addingOlt.set(true);
    this.newOltLibelle = '';
    this.newOltDescription = '';
  }

  cancelAddOlt(): void {
    this.addingOlt.set(false);
    this.newOltLibelle = '';
    this.newOltDescription = '';
  }

  saveOlt(): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu || !this.newOltLibelle.trim()) return;

    this.enjeuService.createObjectifLongTerme({
      id_enjeu: enjeu.id_enjeu,
      libelle: this.newOltLibelle.trim(),
      description: this.newOltDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.olt.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddOlt();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  startEditOlt(olt: ObjectifLongTerme): void {
    this.editingOltId.set(olt.id_olt);
    this.editOltLibelle = olt.libelle;
    this.editOltDescription = olt.description || '';
  }

  cancelEditOlt(): void {
    this.editingOltId.set(null);
    this.editOltLibelle = '';
    this.editOltDescription = '';
  }

  saveEditOlt(olt: ObjectifLongTerme): void {
    if (!this.editOltLibelle.trim()) return;

    this.enjeuService.updateObjectifLongTerme(olt.id_olt, {
      libelle: this.editOltLibelle.trim(),
      description: this.editOltDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.olt.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditOlt();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  deleteOlt(olt: ObjectifLongTerme): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.olt.deleteTitle'),
        message: this.translate.instant('enjeux.olt.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteObjectifLongTerme(olt.id_olt).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.olt.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData();
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Niveaux d'Exigence
  // ============================================

  startAddNe(oltId: number): void {
    this.addingNeForOlt.set(oltId);
    this.newNeLibelle = '';
    this.newNeDescription = '';
  }

  cancelAddNe(): void {
    this.addingNeForOlt.set(null);
    this.newNeLibelle = '';
    this.newNeDescription = '';
  }

  saveNe(olt: ObjectifLongTerme): void {
    if (!this.newNeLibelle.trim()) return;

    this.enjeuService.createNiveauExigence({
      id_olt: olt.id_olt,
      libelle: this.newNeLibelle.trim(),
      description: this.newNeDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.niveauExigence.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddNe();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  startEditNe(ne: NiveauExigence): void {
    this.editingNeId.set(ne.id_ne);
    this.editNeLibelle = ne.libelle;
    this.editNeDescription = ne.description || '';
  }

  cancelEditNe(): void {
    this.editingNeId.set(null);
    this.editNeLibelle = '';
    this.editNeDescription = '';
  }

  saveEditNe(ne: NiveauExigence): void {
    if (!this.editNeLibelle.trim()) return;

    this.enjeuService.updateNiveauExigence(ne.id_ne, {
      libelle: this.editNeLibelle.trim(),
      description: this.editNeDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.niveauExigence.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditNe();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  deleteNe(ne: NiveauExigence): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.niveauExigence.deleteTitle'),
        message: this.translate.instant('enjeux.niveauExigence.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteNiveauExigence(ne.id_ne).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.niveauExigence.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData();
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Indicateurs CRUD
  // ============================================

  toggleIndicateur(id: number): void {
    const expanded = new Set(this.expandedIndicateurIds());
    if (expanded.has(id)) {
      expanded.delete(id);
    } else {
      expanded.add(id);
    }
    this.expandedIndicateurIds.set(expanded);
  }

  isIndicateurExpanded(id: number): boolean {
    return this.expandedIndicateurIds().has(id);
  }

  startAddIndicateur(neId: number): void {
    this.addingIndicateurForNe.set(neId);
    this.newIndicateurNom = '';
    this.newIndicateurType = null;
    this.newIndicateurStandardise = false;
    this.newIndicateurDescription = '';
    this.indicateurFormMetriques = [];
    this.loadTypeMetriqueOptions();
  }

  cancelAddIndicateur(): void {
    this.addingIndicateurForNe.set(null);
    this.indicateurFormMetriques = [];
  }

  loadTypeMetriqueOptions(): void {
    if (this.typeMetriqueOptions().length > 0) return;
    this.adminService.getNomenclaturesByType('TYPE_METRIQUE').subscribe({
      next: (options) => this.typeMetriqueOptions.set(options),
      error: () => this.typeMetriqueOptions.set([])
    });
  }

  createEmptyMetrique(): MetriqueFormData {
    return {
      nom_metrique: '',
      type_metrique: null,
      unite: '',
      ponderation: null,
      etat_reference: '',
      scores: {
        1: { inf: null, sup: null },
        2: { inf: null, sup: null },
        3: { inf: null, sup: null },
        4: { inf: null, sup: null },
        5: { inf: null, sup: null }
      }
    };
  }

  addMetriqueToForm(): void {
    this.indicateurFormMetriques = [...this.indicateurFormMetriques, this.createEmptyMetrique()];
  }

  removeMetriqueFromForm(index: number): void {
    this.indicateurFormMetriques = this.indicateurFormMetriques.filter((_, i) => i !== index);
  }

  buildMetriquePayload(indicateurId: number, met: MetriqueFormData): MetriqueCreatePayload {
    const payload: MetriqueCreatePayload = {
      id_indicateur: indicateurId,
      nom_metrique: met.nom_metrique.trim(),
    };
    if (met.type_metrique) payload.type_metrique = met.type_metrique;
    if (met.unite.trim()) payload.unite = met.unite.trim();
    if (met.ponderation != null) payload.ponderation = met.ponderation;
    if (met.etat_reference.trim()) payload.etat_reference = met.etat_reference.trim();
    for (let level = 1; level <= 5; level++) {
      const s = met.scores[level];
      if (s?.inf != null) (payload as any)[`score_${level}_inf`] = s.inf;
      if (s?.sup != null) (payload as any)[`score_${level}_sup`] = s.sup;
    }
    return payload;
  }

  saveIndicateur(ne: any): void {
    if (!this.newIndicateurNom.trim()) return;
    this.isSavingIndicateur.set(true);

    const payload: any = {
      id_ne: ne.id_ne,
      nom_indicateur: this.newIndicateurNom.trim(),
      est_standardise: this.newIndicateurStandardise,
    };
    if (this.newIndicateurType) payload.type_indicateur = this.newIndicateurType;
    if (this.newIndicateurDescription.trim()) payload.description = this.newIndicateurDescription.trim();

    // Filter metriques that have a name
    const validMetriques = this.indicateurFormMetriques.filter(m => m.nom_metrique.trim());

    this.enjeuService.createIndicateur(payload).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: (createdIndicateur: any) => {
        const indicateurId = createdIndicateur.id_indicateur;

        if (validMetriques.length === 0) {
          // No metriques to create
          this.snackBar.open(
            this.translate.instant('enjeux.indicateurs.createSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.addingIndicateurForNe.set(null);
          this.indicateurFormMetriques = [];
          this.isSavingIndicateur.set(false);
          this.enjeuService.refreshCurrentPlanEnjeux();
          return;
        }

        // Create all metriques in parallel
        const metriqueRequests = validMetriques.map(met =>
          this.enjeuService.createMetrique(this.buildMetriquePayload(indicateurId, met))
        );

        forkJoin(metriqueRequests).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.indicateurs.createSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.addingIndicateurForNe.set(null);
            this.indicateurFormMetriques = [];
            this.isSavingIndicateur.set(false);
            this.enjeuService.refreshCurrentPlanEnjeux();
          },
          error: () => {
            // Partial success: indicateur created but some metriques failed
            this.snackBar.open(
              this.translate.instant('enjeux.metriques.partialError'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
            this.addingIndicateurForNe.set(null);
            this.indicateurFormMetriques = [];
            this.isSavingIndicateur.set(false);
            this.enjeuService.refreshCurrentPlanEnjeux();
          }
        });
      },
      error: () => {
        this.isSavingIndicateur.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.createError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  startEditIndicateur(ind: any): void {
    this.editingIndicateurId.set(ind.id_indicateur);
    this.editIndicateurNom = ind.nom_indicateur;
    this.editIndicateurType = ind.type_indicateur || null;
    this.editIndicateurStandardise = ind.est_standardise;
    this.editIndicateurDescription = ind.description || '';
    this.loadTypeMetriqueOptions();

    // Load existing metriques into edit form
    this.editIndicateurMetriques = (ind.metriques || []).map((met: Metrique) => ({
      id_metrique: met.id_metrique,
      nom_metrique: met.nom_metrique,
      type_metrique: met.type_metrique || null,
      unite: met.unite || '',
      ponderation: met.ponderation ?? null,
      etat_reference: met.etat_reference || '',
      scores: {
        1: { inf: met.score_1_inf ?? null, sup: met.score_1_sup ?? null },
        2: { inf: met.score_2_inf ?? null, sup: met.score_2_sup ?? null },
        3: { inf: met.score_3_inf ?? null, sup: met.score_3_sup ?? null },
        4: { inf: met.score_4_inf ?? null, sup: met.score_4_sup ?? null },
        5: { inf: met.score_5_inf ?? null, sup: met.score_5_sup ?? null }
      }
    } as MetriqueFormData));
  }

  cancelEditIndicateur(): void {
    this.editingIndicateurId.set(null);
    this.editIndicateurMetriques = [];
  }

  addMetriqueToEdit(): void {
    this.editIndicateurMetriques = [...this.editIndicateurMetriques, this.createEmptyMetrique()];
  }

  removeMetriqueFromEdit(index: number): void {
    const met = this.editIndicateurMetriques[index];
    if (met.id_metrique) {
      // Mark existing metrique for deletion
      this.editIndicateurMetriques = this.editIndicateurMetriques.map((m, i) =>
        i === index ? { ...m, _deleted: true } : m
      );
    } else {
      // Remove new metrique entirely
      this.editIndicateurMetriques = this.editIndicateurMetriques.filter((_, i) => i !== index);
    }
  }

  saveEditIndicateur(ind: any): void {
    if (!this.editIndicateurNom.trim()) return;
    this.isSavingIndicateur.set(true);

    const payload: any = {
      nom_indicateur: this.editIndicateurNom.trim(),
      est_standardise: this.editIndicateurStandardise,
    };
    if (this.editIndicateurType) payload.type_indicateur = this.editIndicateurType;
    if (this.editIndicateurDescription.trim()) payload.description = this.editIndicateurDescription.trim();

    this.enjeuService.updateIndicateur(ind.id_indicateur, payload).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        // Process metriques: create new, update existing, delete removed
        const metriqueOps: Observable<any>[] = [];

        for (const met of this.editIndicateurMetriques) {
          if (met._deleted && met.id_metrique) {
            // Delete existing metrique
            metriqueOps.push(this.enjeuService.deleteMetrique(met.id_metrique));
          } else if (!met._deleted && met.nom_metrique.trim()) {
            if (met.id_metrique) {
              // Update existing metrique
              metriqueOps.push(this.enjeuService.updateMetrique(met.id_metrique, this.buildMetriquePayload(ind.id_indicateur, met)));
            } else {
              // Create new metrique
              metriqueOps.push(this.enjeuService.createMetrique(this.buildMetriquePayload(ind.id_indicateur, met)));
            }
          }
        }

        if (metriqueOps.length === 0) {
          this.snackBar.open(
            this.translate.instant('enjeux.indicateurs.updateSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.editingIndicateurId.set(null);
          this.editIndicateurMetriques = [];
          this.isSavingIndicateur.set(false);
          this.enjeuService.refreshCurrentPlanEnjeux();
          return;
        }

        forkJoin(metriqueOps).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.indicateurs.updateSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.editingIndicateurId.set(null);
            this.editIndicateurMetriques = [];
            this.isSavingIndicateur.set(false);
            this.enjeuService.refreshCurrentPlanEnjeux();
          },
          error: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.metriques.partialError'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
            this.editingIndicateurId.set(null);
            this.editIndicateurMetriques = [];
            this.isSavingIndicateur.set(false);
            this.enjeuService.refreshCurrentPlanEnjeux();
          }
        });
      },
      error: () => {
        this.isSavingIndicateur.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.updateError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  deleteIndicateur(ind: any): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      data: {
        title: this.translate.instant('common.actions.delete'),
        message: this.translate.instant('enjeux.indicateurs.deleteConfirm'),
        confirmLabel: this.translate.instant('common.actions.delete')
      }
    });

    dialogRef.afterClosed().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(result => {
      if (result) {
        this.enjeuService.deleteIndicateur(ind.id_indicateur).pipe(
          takeUntilDestroyed(this.destroyRef)
        ).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.indicateurs.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.enjeuService.refreshCurrentPlanEnjeux();
          }
        });
      }
    });
  }

  // ============================================
  // Métriques CRUD
  // ============================================

  readonly scoreLevels = [1, 2, 3, 4, 5];

  deleteMetrique(met: any): void {
    this.enjeuService.deleteMetrique(met.id_metrique).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.metriques.deleteSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.enjeuService.refreshCurrentPlanEnjeux();
      }
    });
  }

  getScoreLevelLabel(level: number): string {
    const labels: Record<number, string> = {
      1: this.translate.instant('enjeux.metriques.scores.tresMauvais'),
      2: this.translate.instant('enjeux.metriques.scores.mauvais'),
      3: this.translate.instant('enjeux.metriques.scores.moyen'),
      4: this.translate.instant('enjeux.metriques.scores.bon'),
      5: this.translate.instant('enjeux.metriques.scores.tresBon'),
    };
    return labels[level] || '';
  }

  getScoreInf(met: any, level: number): string {
    const val = met[`score_${level}_inf`];
    return val != null ? val.toString() : '-';
  }

  getScoreSup(met: any, level: number): string {
    const val = met[`score_${level}_sup`];
    return val != null ? val.toString() : '-';
  }

  getScoreRange(met: any, level: number): string {
    const inf = met[`score_${level}_inf`];
    const sup = met[`score_${level}_sup`];
    if (inf != null && sup != null) {
      return `${inf} - ${sup}`;
    }
    if (inf != null) return `≥ ${inf}`;
    if (sup != null) return `≤ ${sup}`;
    return '- - -';
  }

  // ============================================
  // Operations (Actions) - Expand/collapse + helpers
  // ============================================

  toggleOperation(id: number): void {
    this.expandedOperationIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isOperationExpanded(id: number): boolean {
    return this.expandedOperationIds().has(id);
  }

  /**
   * Get the plan's full year range for the programmation table.
   * All operations use the same columns (plan years).
   */
  getPlanYears(): number[] {
    const debut = this.planAnneeDebut();
    const fin = this.planAnneeFin();
    if (!debut || !fin) return [];
    const years: number[] = [];
    for (let y = debut; y <= fin; y++) {
      years.push(y);
    }
    return years;
  }

  /**
   * Get sorted year range for the programmation table (operation-specific fallback).
   */
  getOperationYears(op: Operation): number[] {
    if (op.operation_annees && op.operation_annees.length > 0) {
      return op.operation_annees
        .map(a => a.annee)
        .sort((a, b) => a - b);
    }
    // Fallback to annee_min/annee_max
    if (op.annee_min && op.annee_max) {
      const years: number[] = [];
      for (let y = op.annee_min; y <= op.annee_max; y++) {
        years.push(y);
      }
      return years;
    }
    return [];
  }

  /**
   * Get OperationAnnee for a given year, or null.
   */
  getOperationAnnee(op: Operation, year: number): OperationAnnee | null {
    if (!op.operation_annees) return null;
    return op.operation_annees.find(a => a.annee === year) || null;
  }

  /**
   * Check if an operation year is planned (periodicite or monthly planning).
   */
  isYearPlanned(op: Operation, year: number): boolean {
    const annee = this.getOperationAnnee(op, year);
    if (!annee) return false;
    if (annee.periodicite) return true;
    if (annee.periodicite_mensuelle) {
      return Object.values(annee.periodicite_mensuelle).some(v => v === true);
    }
    return false;
  }

  /**
   * Check if any year of the operation has monthly planning details.
   */
  hasAnyMonthlyPlanning(op: Operation): boolean {
    if (!op.operation_annees) return false;
    return op.operation_annees.some(a =>
      a.periodicite_mensuelle && Object.values(a.periodicite_mensuelle).some(v => v === true)
    );
  }

  private readonly monthNames = [
    'Jan', 'Fév', 'Mar', 'Avr', 'Mai', 'Juin',
    'Juil', 'Août', 'Sep', 'Oct', 'Nov', 'Déc'
  ];

  /**
   * Get list of planned month names for a given year.
   */
  getPlannedMonths(op: Operation, year: number): string[] {
    const annee = this.getOperationAnnee(op, year);
    if (!annee || !annee.periodicite_mensuelle) return [];
    const months: string[] = [];
    for (let m = 1; m <= 12; m++) {
      if (annee.periodicite_mensuelle[m.toString()] === true) {
        months.push(this.monthNames[m - 1]);
      }
    }
    return months;
  }

  /**
   * Get the planned months for the entire operation (same for all years).
   * Takes the monthly planning from the first year that has it.
   */
  getPlannedMonthsForOperation(op: Operation): string[] {
    if (!op.operation_annees) return [];
    const anneeWithMonths = op.operation_annees.find(a =>
      a.periodicite_mensuelle && Object.values(a.periodicite_mensuelle).some(v => v === true)
    );
    if (!anneeWithMonths || !anneeWithMonths.periodicite_mensuelle) return [];
    const months: string[] = [];
    for (let m = 1; m <= 12; m++) {
      if (anneeWithMonths.periodicite_mensuelle[m.toString()] === true) {
        months.push(this.monthNames[m - 1]);
      }
    }
    return months;
  }

  /**
   * Format budget value for display.
   */
  formatBudget(value: number | null | undefined): string {
    if (value == null) return '-';
    return value.toLocaleString('fr-FR') + '€';
  }

  /**
   * Format ETP/travail value for display.
   */
  formatTravail(value: number | null | undefined): string {
    if (value == null) return '-';
    return value.toString();
  }

  /**
   * Format frequency display.
   */
  getFrequenceDisplay(op: Operation): string {
    if (!op.frequence_nombre || !op.frequence_unite) return '';
    const unite = this.translate.instant('enjeux.operations.unite' + this.capitalizeFirst(op.frequence_unite));
    return `${op.frequence_nombre} ${this.translate.instant('enjeux.operations.foisPar')} ${unite}`;
  }

  private capitalizeFirst(s: string): string {
    if (!s) return s;
    return s.charAt(0).toUpperCase() + s.slice(1).toLowerCase();
  }

  // ============================================
  // Operations (Actions) - Navigation vers page dédiée
  // ============================================

  navigateToOperationForm(indicateurId?: number): void {
    const planId = this.planId();
    if (!planId) return;
    const extras: any = {};
    if (indicateurId) {
      extras.queryParams = { indicateurId };
    }
    this.router.navigate(['/plans', planId, 'enjeux', 'operations', 'nouveau'], extras);
  }

  navigateToEditOperation(operationId: number): void {
    const planId = this.planId();
    if (!planId) return;
    this.router.navigate(['/plans', planId, 'enjeux', 'operations', operationId, 'modifier']);
  }

  deleteOperation(operation: Operation): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.operations.deleteTitle'),
        message: this.translate.instant('enjeux.operations.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteOperation(operation.id_operation).pipe(
          takeUntilDestroyed(this.destroyRef)
        ).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.operations.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.enjeuService.refreshCurrentPlanEnjeux();
          },
          error: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.messages.deleteError'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
          }
        });
      }
    });
  }

  getPrioriteClass(op: Operation): string {
    if (!op.priorite_label) return '';
    if (op.priorite_label.includes('1')) return '1';
    if (op.priorite_label.includes('2')) return '2';
    if (op.priorite_label.includes('3')) return '3';
    return '';
  }

  // ============================================
  // Objectifs Opérationnels (OO)
  // ============================================

  toggleOo(id: number): void {
    this.expandedOoIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) {
        newIds.delete(id);
      } else {
        newIds.add(id);
      }
      return newIds;
    });
  }

  isOoExpanded(id: number): boolean {
    return this.expandedOoIds().has(id);
  }

  startAddOo(): void {
    this.addingOo.set(true);
    this.newOoLibelle = '';
    this.newOoDescription = '';
    this.newOoFacteurId = null;
  }

  cancelAddOo(): void {
    this.addingOo.set(false);
    this.newOoLibelle = '';
    this.newOoDescription = '';
    this.newOoFacteurId = null;
  }

  saveOo(): void {
    const enjeu = this.selectedEnjeu();
    if (!enjeu || !this.newOoLibelle.trim()) return;

    this.enjeuService.createObjectifOperationnel({
      id_enjeu: enjeu.id_enjeu,
      libelle: this.newOoLibelle.trim(),
      description: this.newOoDescription.trim() || undefined,
      id_facteur_influence: this.newOoFacteurId || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.oo.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddOo();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  startEditOo(oo: ObjectifOperationnel): void {
    this.editingOoId.set(oo.id_oo);
    this.editOoLibelle = oo.libelle;
    this.editOoDescription = oo.description || '';
    this.editOoFacteurId = oo.id_facteur_influence || null;
  }

  cancelEditOo(): void {
    this.editingOoId.set(null);
    this.editOoLibelle = '';
    this.editOoDescription = '';
    this.editOoFacteurId = null;
  }

  saveEditOo(oo: ObjectifOperationnel): void {
    if (!this.editOoLibelle.trim()) return;

    this.enjeuService.updateObjectifOperationnel(oo.id_oo, {
      libelle: this.editOoLibelle.trim(),
      description: this.editOoDescription.trim() || undefined,
      id_facteur_influence: this.editOoFacteurId || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.oo.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditOo();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  deleteOo(oo: ObjectifOperationnel): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.oo.deleteTitle'),
        message: this.translate.instant('enjeux.oo.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteObjectifOperationnel(oo.id_oo).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.oo.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData();
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Résultats Attendus
  // ============================================

  startAddRa(ooId: number): void {
    this.addingRaForOo.set(ooId);
    this.newRaLibelle = '';
    this.newRaDescription = '';
  }

  cancelAddRa(): void {
    this.addingRaForOo.set(null);
    this.newRaLibelle = '';
    this.newRaDescription = '';
  }

  saveRa(oo: ObjectifOperationnel): void {
    if (!this.newRaLibelle.trim()) return;

    this.enjeuService.createResultatAttendu({
      id_oo: oo.id_oo,
      libelle: this.newRaLibelle.trim(),
      description: this.newRaDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.resultatAttendu.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelAddRa();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  startEditRa(ra: ResultatAttendu): void {
    this.editingRaId.set(ra.id_ra);
    this.editRaLibelle = ra.libelle;
    this.editRaDescription = ra.description || '';
  }

  cancelEditRa(): void {
    this.editingRaId.set(null);
    this.editRaLibelle = '';
    this.editRaDescription = '';
  }

  saveEditRa(ra: ResultatAttendu): void {
    if (!this.editRaLibelle.trim()) return;

    this.enjeuService.updateResultatAttendu(ra.id_ra, {
      libelle: this.editRaLibelle.trim(),
      description: this.editRaDescription.trim() || undefined
    }).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.resultatAttendu.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.cancelEditRa();
        this.loadPlanData();
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.updateError'));
      }
    });
  }

  deleteRa(ra: ResultatAttendu): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.resultatAttendu.deleteTitle'),
        message: this.translate.instant('enjeux.resultatAttendu.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteResultatAttendu(ra.id_ra).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.resultatAttendu.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData();
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }

  // ============================================
  // Indicateurs de pression (OO tab)
  // ============================================

  toggleOoIndicateur(id: number): void {
    this.expandedOoIndicateurIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) { newIds.delete(id); } else { newIds.add(id); }
      return newIds;
    });
  }

  isOoIndicateurExpanded(id: number): boolean {
    return this.expandedOoIndicateurIds().has(id);
  }

  toggleOoOperation(id: number): void {
    this.expandedOoOperationIds.update(ids => {
      const newIds = new Set(ids);
      if (newIds.has(id)) { newIds.delete(id); } else { newIds.add(id); }
      return newIds;
    });
  }

  isOoOperationExpanded(id: number): boolean {
    return this.expandedOoOperationIds().has(id);
  }

  startAddIndicateurForRa(raId: number): void {
    this.addingIndicateurForRa.set(raId);
    this.newOoIndicateurNom = '';
    this.newOoIndicateurType = null;
    this.newOoIndicateurStandardise = false;
    this.newOoIndicateurDescription = '';
    this.ooIndicateurFormMetriques = [];
  }

  cancelAddIndicateurForRa(): void {
    this.addingIndicateurForRa.set(null);
    this.newOoIndicateurNom = '';
    this.newOoIndicateurType = null;
    this.newOoIndicateurStandardise = false;
    this.newOoIndicateurDescription = '';
    this.ooIndicateurFormMetriques = [];
  }

  addOoMetriqueRow(): void {
    this.ooIndicateurFormMetriques.push({
      nom_metrique: '',
      type_metrique: null,
      unite: '',
      ponderation: null,
      etat_reference: '',
      scores: { 1: { inf: null, sup: null }, 2: { inf: null, sup: null }, 3: { inf: null, sup: null }, 4: { inf: null, sup: null }, 5: { inf: null, sup: null } }
    });
  }

  removeOoMetriqueRow(index: number): void {
    this.ooIndicateurFormMetriques.splice(index, 1);
  }

  saveIndicateurForRa(ra: ResultatAttendu): void {
    if (!this.newOoIndicateurNom.trim()) return;

    this.isSavingOoIndicateur.set(true);
    this.enjeuService.createIndicateur({
      id_resultat_attendu: ra.id_ra,
      nom_indicateur: this.newOoIndicateurNom.trim(),
      description: this.newOoIndicateurDescription.trim() || undefined,
      type_indicateur: this.newOoIndicateurType || undefined,
      est_standardise: this.newOoIndicateurStandardise
    }).subscribe({
      next: (indicateur) => {
        // Create metriques if any
        const metriquesToCreate = this.ooIndicateurFormMetriques.filter(m => m.nom_metrique.trim());
        if (metriquesToCreate.length > 0) {
          const metriqueRequests: Observable<any>[] = metriquesToCreate.map(m => {
            const payload: MetriqueCreatePayload = {
              id_indicateur: indicateur.id_indicateur,
              nom_metrique: m.nom_metrique.trim(),
              type_metrique: m.type_metrique || undefined,
              unite: m.unite || undefined,
              ponderation: m.ponderation || undefined,
              etat_reference: m.etat_reference || undefined,
            };
            // Add score thresholds
            for (let level = 1; level <= 5; level++) {
              const score = m.scores[level];
              if (score) {
                (payload as any)[`score_${level}_inf`] = score.inf;
                (payload as any)[`score_${level}_sup`] = score.sup;
              }
            }
            return this.enjeuService.createMetrique(payload);
          });

          forkJoin(metriqueRequests).subscribe({
            next: () => {
              this.isSavingOoIndicateur.set(false);
              this.snackBar.open(
                this.translate.instant('enjeux.indicateur.createSuccess'),
                this.translate.instant('common.actions.close'),
                { duration: 3000 }
              );
              this.cancelAddIndicateurForRa();
              this.loadPlanData();
            },
            error: () => {
              this.isSavingOoIndicateur.set(false);
              this.loadPlanData();
            }
          });
        } else {
          this.isSavingOoIndicateur.set(false);
          this.snackBar.open(
            this.translate.instant('enjeux.indicateur.createSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.cancelAddIndicateurForRa();
          this.loadPlanData();
        }
      },
      error: () => {
        this.isSavingOoIndicateur.set(false);
        this.errorMessage.set(this.translate.instant('enjeux.messages.createError'));
      }
    });
  }

  startEditOoIndicateur(indicateur: Indicateur): void {
    this.editingOoIndicateurId.set(indicateur.id_indicateur);
    this.editOoIndicateurNom = indicateur.nom_indicateur;
    this.editOoIndicateurType = indicateur.type_indicateur || null;
    this.editOoIndicateurStandardise = indicateur.est_standardise;
    this.editOoIndicateurDescription = indicateur.description || '';
    this.editOoIndicateurMetriques = (indicateur.metriques || []).map(m => ({
      id_metrique: m.id_metrique,
      nom_metrique: m.nom_metrique,
      type_metrique: m.type_metrique || null,
      unite: m.unite || '',
      ponderation: m.ponderation || null,
      etat_reference: m.etat_reference || '',
      scores: {
        1: { inf: m.score_1_inf ?? null, sup: m.score_1_sup ?? null },
        2: { inf: m.score_2_inf ?? null, sup: m.score_2_sup ?? null },
        3: { inf: m.score_3_inf ?? null, sup: m.score_3_sup ?? null },
        4: { inf: m.score_4_inf ?? null, sup: m.score_4_sup ?? null },
        5: { inf: m.score_5_inf ?? null, sup: m.score_5_sup ?? null },
      }
    }));
  }

  cancelEditOoIndicateur(): void {
    this.editingOoIndicateurId.set(null);
    this.editOoIndicateurNom = '';
    this.editOoIndicateurType = null;
    this.editOoIndicateurStandardise = false;
    this.editOoIndicateurDescription = '';
    this.editOoIndicateurMetriques = [];
  }

  addOoMetriqueToEdit(): void {
    this.editOoIndicateurMetriques = [...this.editOoIndicateurMetriques, this.createEmptyMetrique()];
  }

  removeOoMetriqueFromEdit(index: number): void {
    const met = this.editOoIndicateurMetriques[index];
    if (met.id_metrique) {
      this.editOoIndicateurMetriques = this.editOoIndicateurMetriques.map((m, i) =>
        i === index ? { ...m, _deleted: true } : m
      );
    } else {
      this.editOoIndicateurMetriques = this.editOoIndicateurMetriques.filter((_, i) => i !== index);
    }
  }

  saveEditOoIndicateur(ind: Indicateur): void {
    if (!this.editOoIndicateurNom.trim()) return;
    this.isSavingOoIndicateur.set(true);

    const payload: any = {
      nom_indicateur: this.editOoIndicateurNom.trim(),
      est_standardise: this.editOoIndicateurStandardise,
    };
    if (this.editOoIndicateurType) payload.type_indicateur = this.editOoIndicateurType;
    if (this.editOoIndicateurDescription.trim()) payload.description = this.editOoIndicateurDescription.trim();

    this.enjeuService.updateIndicateur(ind.id_indicateur, payload).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        const metriqueOps: Observable<any>[] = [];

        for (const met of this.editOoIndicateurMetriques) {
          if (met._deleted && met.id_metrique) {
            metriqueOps.push(this.enjeuService.deleteMetrique(met.id_metrique));
          } else if (!met._deleted && met.nom_metrique.trim()) {
            if (met.id_metrique) {
              metriqueOps.push(this.enjeuService.updateMetrique(met.id_metrique, this.buildMetriquePayload(ind.id_indicateur, met)));
            } else {
              metriqueOps.push(this.enjeuService.createMetrique(this.buildMetriquePayload(ind.id_indicateur, met)));
            }
          }
        }

        if (metriqueOps.length === 0) {
          this.snackBar.open(
            this.translate.instant('enjeux.indicateurs.updateSuccess'),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.editingOoIndicateurId.set(null);
          this.editOoIndicateurMetriques = [];
          this.isSavingOoIndicateur.set(false);
          this.enjeuService.refreshCurrentPlanEnjeux();
          return;
        }

        forkJoin(metriqueOps).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.indicateurs.updateSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.editingOoIndicateurId.set(null);
            this.editOoIndicateurMetriques = [];
            this.isSavingOoIndicateur.set(false);
            this.enjeuService.refreshCurrentPlanEnjeux();
          },
          error: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.metriques.partialError'),
              this.translate.instant('common.actions.close'),
              { duration: 5000 }
            );
            this.editingOoIndicateurId.set(null);
            this.editOoIndicateurMetriques = [];
            this.isSavingOoIndicateur.set(false);
            this.enjeuService.refreshCurrentPlanEnjeux();
          }
        });
      },
      error: () => {
        this.isSavingOoIndicateur.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.messages.updateError'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
      }
    });
  }

  deleteOoIndicateur(indicateur: Indicateur): void {
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.translate.instant('enjeux.indicateur.deleteTitle'),
        message: this.translate.instant('enjeux.indicateur.deleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.enjeuService.deleteIndicateur(indicateur.id_indicateur).subscribe({
          next: () => {
            this.snackBar.open(
              this.translate.instant('enjeux.indicateur.deleteSuccess'),
              this.translate.instant('common.actions.close'),
              { duration: 3000 }
            );
            this.loadPlanData();
          },
          error: () => {
            this.errorMessage.set(this.translate.instant('enjeux.messages.deleteError'));
          }
        });
      }
    });
  }
}
