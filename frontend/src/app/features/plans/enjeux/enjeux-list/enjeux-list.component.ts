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
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatButtonModule } from '@angular/material/button';
import { MatMenuModule } from '@angular/material/menu';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
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
  EtatActuel, ObjectifLongTerme, NiveauExigence, Indicateur, Metrique
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

  // Métriques state
  addingMetriqueForIndicateur = signal<number | null>(null);
  editingMetriqueId = signal<number | null>(null);
  newMetriqueNom = '';
  newMetriqueType: number | null = null;
  newMetriqueUnite = '';
  editMetriqueNom = '';
  editMetriqueType: number | null = null;
  editMetriqueUnite = '';

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
  }

  cancelAddIndicateur(): void {
    this.addingIndicateurForNe.set(null);
  }

  saveIndicateur(ne: any): void {
    if (!this.newIndicateurNom.trim()) return;
    const payload: any = {
      id_ne: ne.id_ne,
      nom_indicateur: this.newIndicateurNom.trim(),
      est_standardise: this.newIndicateurStandardise,
    };
    if (this.newIndicateurType) payload.type_indicateur = this.newIndicateurType;
    if (this.newIndicateurDescription.trim()) payload.description = this.newIndicateurDescription.trim();

    this.enjeuService.createIndicateur(payload).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.indicateurs.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.addingIndicateurForNe.set(null);
        this.enjeuService.refreshCurrentPlanEnjeux();
      },
      error: () => {
        this.snackBar.open('Erreur lors de la création', this.translate.instant('common.actions.close'), { duration: 3000 });
      }
    });
  }

  startEditIndicateur(ind: any): void {
    this.editingIndicateurId.set(ind.id_indicateur);
    this.editIndicateurNom = ind.nom_indicateur;
    this.editIndicateurType = ind.type_indicateur || null;
    this.editIndicateurStandardise = ind.est_standardise;
    this.editIndicateurDescription = ind.description || '';
  }

  cancelEditIndicateur(): void {
    this.editingIndicateurId.set(null);
  }

  saveEditIndicateur(ind: any): void {
    if (!this.editIndicateurNom.trim()) return;
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
        this.snackBar.open(
          this.translate.instant('enjeux.indicateurs.updateSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.editingIndicateurId.set(null);
        this.enjeuService.refreshCurrentPlanEnjeux();
      },
      error: () => {
        this.snackBar.open('Erreur lors de la mise à jour', this.translate.instant('common.actions.close'), { duration: 3000 });
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

  startAddMetrique(indicateurId: number): void {
    this.addingMetriqueForIndicateur.set(indicateurId);
    this.newMetriqueNom = '';
    this.newMetriqueType = null;
    this.newMetriqueUnite = '';
  }

  cancelAddMetrique(): void {
    this.addingMetriqueForIndicateur.set(null);
  }

  saveMetrique(ind: any): void {
    if (!this.newMetriqueNom.trim()) return;
    const payload: any = {
      id_indicateur: ind.id_indicateur,
      nom_metrique: this.newMetriqueNom.trim(),
    };
    if (this.newMetriqueType) payload.type_metrique = this.newMetriqueType;
    if (this.newMetriqueUnite.trim()) payload.unite = this.newMetriqueUnite.trim();

    this.enjeuService.createMetrique(payload).pipe(
      takeUntilDestroyed(this.destroyRef)
    ).subscribe({
      next: () => {
        this.snackBar.open(
          this.translate.instant('enjeux.metriques.createSuccess'),
          this.translate.instant('common.actions.close'),
          { duration: 3000 }
        );
        this.addingMetriqueForIndicateur.set(null);
        this.enjeuService.refreshCurrentPlanEnjeux();
      },
      error: () => {
        this.snackBar.open('Erreur lors de la création', this.translate.instant('common.actions.close'), { duration: 3000 });
      }
    });
  }

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
}
