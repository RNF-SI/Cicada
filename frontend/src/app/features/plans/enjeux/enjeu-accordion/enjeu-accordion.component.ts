/**
 * Composant accordéon pour afficher un Enjeu ou FCR.
 * Affiche le résumé fermé et les détails à l'ouverture.
 */
import { Component, Input, Output, EventEmitter, signal, ElementRef, inject, OnInit, AfterViewInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { Enjeu } from '../../../../core/models/enjeu.model';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';

@Component({
  selector: 'app-enjeu-accordion',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatTooltipModule,
    MatDialogModule,
    TranslateModule
  ],
  templateUrl: './enjeu-accordion.component.html',
  styleUrl: './enjeu-accordion.component.scss'
})
export class EnjeuAccordionComponent implements OnInit, AfterViewInit {
  @Input() enjeu!: Enjeu;
  @Input() id: string = '';
  @Input() isFcr: boolean = false;
  @Input() displayIndex: number = 0;
  @Input() initiallyExpanded: boolean = false;
  @Input() canEdit: boolean = true;

  @Output() edit = new EventEmitter<Enjeu>();
  @Output() delete = new EventEmitter<Enjeu>();
  @Output() navigateToDetail = new EventEmitter<Enjeu>();

  expanded = signal(false);
  showTaxonList = signal(false);
  showHabitatList = signal(false);
  showGeologyList = signal(false);

  private readonly el = inject(ElementRef);
  private readonly dialog = inject(MatDialog);
  private readonly translate = inject(TranslateService);

  ngOnInit(): void {
    if (this.initiallyExpanded) {
      this.expanded.set(true);
    }
  }

  ngAfterViewInit(): void {
    if (this.initiallyExpanded) {
      setTimeout(() => {
        this.el.nativeElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 100);
    }
  }

  toggle(): void {
    this.expanded.update(v => !v);
  }

  onEdit(event: Event): void {
    event.stopPropagation();
    this.edit.emit(this.enjeu);
  }

  onDelete(event: Event): void {
    event.stopPropagation();

    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '450px',
      data: {
        title: this.isFcr
          ? this.translate.instant('enjeux.messages.fcrDeleteConfirmTitle')
          : this.translate.instant('enjeux.messages.enjeuDeleteConfirmTitle'),
        message: this.isFcr
          ? this.translate.instant('enjeux.messages.fcrDeleteConfirm')
          : this.translate.instant('enjeux.messages.enjeuDeleteConfirm'),
        confirmText: this.translate.instant('common.actions.delete'),
        cancelText: this.translate.instant('common.actions.cancel'),
        confirmColor: 'warn'
      }
    });

    dialogRef.afterClosed().subscribe(confirmed => {
      if (confirmed) {
        this.delete.emit(this.enjeu);
      }
    });
  }

  // Helpers pour l'affichage
  get priorityClass(): string {
    return `priority-${this.enjeu.rang || 1}`;
  }

  get categoryLabel(): string {
    if (this.enjeu.categorie_ecologique === true) {
      return this.translate.instant('enjeux.enjeuForm.ecologique');
    } else if (this.enjeu.categorie_ecologique === false) {
      return this.translate.instant('enjeux.enjeuForm.socioEconomique');
    }
    return '';
  }

  get typeLabels(): string[] {
    const labels: string[] = [];
    // Écologique
    if (this.enjeu.habitat) {
      labels.push(this.translate.instant('enjeux.enjeuForm.habitat'));
    }
    if (this.enjeu.espece) {
      labels.push(this.translate.instant('enjeux.enjeuForm.espece'));
    }
    if (this.enjeu.patrimoine_geologique) {
      labels.push(this.translate.instant('enjeux.enjeuForm.patrimoineGeologique'));
    }
    if (this.enjeu.fonctionnalite_ecosysteme) {
      labels.push(this.translate.instant('enjeux.enjeuForm.fonctionnaliteEcosysteme'));
    }
    if (this.enjeu.autre_ecologique) {
      labels.push(this.translate.instant('enjeux.enjeuForm.autreEcologique'));
    }
    // Socio-économique
    if (this.enjeu.valeur_paysagere) {
      labels.push(this.translate.instant('enjeux.enjeuForm.valeurPaysagere'));
    }
    if (this.enjeu.patrimoine_culturel) {
      labels.push(this.translate.instant('enjeux.enjeuForm.patrimoineCulturel'));
    }
    if (this.enjeu.developpement_durable) {
      labels.push(this.translate.instant('enjeux.enjeuForm.developpementDurable'));
    }
    if (this.enjeu.usages) {
      labels.push(this.translate.instant('enjeux.enjeuForm.usages'));
    }
    if (this.enjeu.valeur_ajoutee) {
      labels.push(this.translate.instant('enjeux.enjeuForm.valeurAjoutee'));
    }
    if (this.enjeu.autre_socioeco) {
      labels.push(this.translate.instant('enjeux.enjeuForm.autreSocioEco'));
    }
    return labels;
  }

  get fcrCategoryLabel(): string {
    return this.enjeu.categorie_fcr_label || '';
  }

  get hasTaxons(): boolean {
    return (this.enjeu.taxons?.length || 0) > 0 || (this.enjeu.nb_taxons || 0) > 0;
  }

  get hasHabitats(): boolean {
    return (this.enjeu.habitats?.length || 0) > 0 || (this.enjeu.nb_habitats || 0) > 0;
  }

  get hasGeologies(): boolean {
    return (this.enjeu.geologies?.length || 0) > 0 || (this.enjeu.nb_geologies || 0) > 0;
  }

  get taxonCount(): number {
    return this.enjeu.taxons?.length || this.enjeu.nb_taxons || 0;
  }

  get habitatCount(): number {
    return this.enjeu.habitats?.length || this.enjeu.nb_habitats || 0;
  }

  get geologyCount(): number {
    return this.enjeu.geologies?.length || this.enjeu.nb_geologies || 0;
  }

  get facteurCount(): number {
    return this.enjeu.facteurs_influence?.length || this.enjeu.nb_facteurs_influence || 0;
  }

  toggleTaxonList(event: Event): void {
    event.stopPropagation();
    this.showTaxonList.update(v => !v);
  }

  toggleHabitatList(event: Event): void {
    event.stopPropagation();
    this.showHabitatList.update(v => !v);
  }

  toggleGeologyList(event: Event): void {
    event.stopPropagation();
    this.showGeologyList.update(v => !v);
  }

  onNavigateToDetail(event: Event): void {
    event.stopPropagation();
    this.navigateToDetail.emit(this.enjeu);
  }
}
