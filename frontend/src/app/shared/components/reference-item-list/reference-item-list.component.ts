import { Component, Input, Output, EventEmitter, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { MatChipsModule } from '@angular/material/chips';
import { MatAutocompleteModule, MatAutocompleteSelectedEvent } from '@angular/material/autocomplete';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDialog } from '@angular/material/dialog';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Subject, debounceTime, distinctUntilChanged, takeUntil } from 'rxjs';

import { TaxonomyService, TaxrefAutocomplete, getTaxrefRangLabel } from '../../../core/services/taxonomy.service';
import { HabitatService, HabitatAutocomplete } from '../../../core/services/habitat.service';
import { GeologyService, InpgAutocomplete } from '../../../core/services/geology.service';
import { TaxonRef, HabitatRef, GeologieRef } from '../../../core/models/enjeu.model';
import { ImportListDialogComponent, ImportListDialogData, ImportedItem } from '../modals/import-list-dialog/import-list-dialog.component';

@Component({
  selector: 'app-reference-item-list',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatChipsModule,
    MatAutocompleteModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    TranslateModule,
  ],
  templateUrl: './reference-item-list.component.html',
  styleUrl: './reference-item-list.component.scss'
})
export class ReferenceItemListComponent implements OnInit, OnDestroy {
  @Input() type: 'taxon' | 'habitat' | 'geology' = 'taxon';
  @Input() items: (TaxonRef | HabitatRef | GeologieRef)[] = [];
  @Output() itemsChange = new EventEmitter<(TaxonRef | HabitatRef | GeologieRef)[]>();

  private readonly taxonomyService = inject(TaxonomyService);
  private readonly habitatService = inject(HabitatService);
  private readonly geologyService = inject(GeologyService);
  private readonly dialog = inject(MatDialog);
  private readonly destroy$ = new Subject<void>();

  searchControl = new FormControl('');
  autocompleteResults = signal<(TaxrefAutocomplete | HabitatAutocomplete | InpgAutocomplete)[]>([]);
  isSearching = signal(false);

  ngOnInit(): void {
    this.searchControl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      takeUntil(this.destroy$)
    ).subscribe(value => {
      if (typeof value === 'string' && value.length >= 2) {
        this.search(value);
      } else {
        this.autocompleteResults.set([]);
      }
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  private search(term: string): void {
    this.isSearching.set(true);
    const handler = {
      next: (results: (TaxrefAutocomplete | HabitatAutocomplete | InpgAutocomplete)[]) => {
        this.autocompleteResults.set(results);
        this.isSearching.set(false);
      },
      error: () => this.isSearching.set(false)
    };
    // #238 — limite dynamique : 20 résultats pour 2-3 chars (exploration),
    // 50 pour 4+ chars (l'utilisateur connaît son taxon/habitat et doit le
    // trouver dans la liste).
    const effectiveLimit = term.length >= 4 ? 50 : 20;
    if (this.type === 'taxon') {
      this.taxonomyService.autocomplete(term, { limit: effectiveLimit }).subscribe(handler);
    } else if (this.type === 'habitat') {
      this.habitatService.autocomplete(term, { limit: effectiveLimit }).subscribe(handler);
    } else {
      this.geologyService.autocomplete(term, { limit: effectiveLimit }).subscribe(handler);
    }
  }

  onAutocompleteSelected(event: MatAutocompleteSelectedEvent): void {
    const selected = event.option.value;
    if (!selected) return;

    if (this.type === 'taxon') {
      const taxon = selected as TaxrefAutocomplete;
      const exists = (this.items as TaxonRef[]).some(t => t.cd_nom === taxon.cd_nom);
      if (!exists) {
        const newItem: TaxonRef = {
          cd_nom: taxon.cd_nom,
          nom_complet: taxon.nom_valide || taxon.lb_nom,
          nom_vern: taxon.nom_vern || undefined,
          regne: taxon.regne,
          id_rang: taxon.id_rang || undefined,
        };
        this.items = [...this.items, newItem];
        this.itemsChange.emit(this.items);
      }
    } else if (this.type === 'habitat') {
      const habitat = selected as HabitatAutocomplete;
      const exists = (this.items as HabitatRef[]).some(h => String(h.cd_hab) === String(habitat.cd_hab));
      if (!exists) {
        const newItem: HabitatRef = {
          cd_hab: String(habitat.cd_hab),
          lb_hab_fr: habitat.lb_hab_fr || habitat.search_name || undefined,
        };
        this.items = [...this.items, newItem];
        this.itemsChange.emit(this.items);
      }
    } else {
      const inpg = selected as InpgAutocomplete;
      const exists = (this.items as GeologieRef[]).some(g => String(g.id_inpg) === String(inpg.id_inpg));
      if (!exists) {
        const newItem: GeologieRef = {
          id_inpg: String(inpg.id_inpg),
          nom: inpg.lb_site || inpg.id_metier || undefined,
        };
        this.items = [...this.items, newItem];
        this.itemsChange.emit(this.items);
      }
    }

    this.searchControl.setValue('');
    this.autocompleteResults.set([]);
  }

  removeItem(index: number): void {
    this.items = this.items.filter((_, i) => i !== index);
    this.itemsChange.emit(this.items);
  }

  openImportDialog(): void {
    const existingCodes = this.type === 'taxon'
      ? (this.items as TaxonRef[]).map(t => t.cd_nom)
      : this.type === 'habitat'
        ? (this.items as HabitatRef[]).map(h => h.cd_hab)
        : (this.items as GeologieRef[]).map(g => g.id_inpg);

    const dialogRef = this.dialog.open(ImportListDialogComponent, {
      width: '1300px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { type: this.type, existingCodes } as ImportListDialogData,
    });

    dialogRef.afterClosed().subscribe(result => {
      if (result?.items?.length) {
        this.addImportedItems(result.items);
      }
    });
  }

  private addImportedItems(importedItems: ImportedItem[]): void {
    if (this.type === 'taxon') {
      const currentItems = this.items as TaxonRef[];
      const existingCodes = new Set(currentItems.map(t => t.cd_nom));
      const newItems: TaxonRef[] = importedItems
        .filter(item => !existingCodes.has(Number(item.code)))
        .map(item => ({
          cd_nom: Number(item.code),
          nom_complet: item.label,
          nom_vern: item.secondaryLabel || undefined,
        }));
      this.items = [...currentItems, ...newItems];
    } else if (this.type === 'habitat') {
      const currentItems = this.items as HabitatRef[];
      const existingCodes = new Set(currentItems.map(h => String(h.cd_hab)));
      const newItems: HabitatRef[] = importedItems
        .filter(item => !existingCodes.has(String(item.code)))
        .map(item => ({
          cd_hab: String(item.code),
          lb_hab_fr: item.label,
        }));
      this.items = [...currentItems, ...newItems];
    } else {
      const currentItems = this.items as GeologieRef[];
      const existingCodes = new Set(currentItems.map(g => String(g.id_inpg)));
      const newItems: GeologieRef[] = importedItems
        .filter(item => !existingCodes.has(String(item.code)))
        .map(item => ({
          id_inpg: String(item.code),
          nom: item.label,
        }));
      this.items = [...currentItems, ...newItems];
    }
    this.itemsChange.emit(this.items);
  }

  getItemLabel(item: TaxonRef | HabitatRef | GeologieRef): string {
    if (this.type === 'taxon') {
      return (item as TaxonRef).nom_complet || `cd_nom: ${(item as TaxonRef).cd_nom}`;
    }
    if (this.type === 'habitat') {
      return (item as HabitatRef).lb_hab_fr || `cd_hab: ${(item as HabitatRef).cd_hab}`;
    }
    return (item as GeologieRef).nom || `id_inpg: ${(item as GeologieRef).id_inpg}`;
  }

  getItemSecondary(item: TaxonRef | HabitatRef | GeologieRef): string {
    if (this.type === 'taxon') {
      const t = item as TaxonRef;
      const rang = getTaxrefRangLabel(t.id_rang);
      const parts = [rang, t.nom_vern].filter(Boolean);
      return parts.join(' · ');
    }
    if (this.type === 'habitat') {
      return `cd_hab: ${(item as HabitatRef).cd_hab}`;
    }
    return `id_inpg: ${(item as GeologieRef).id_inpg}`;
  }

  displayFn(result: TaxrefAutocomplete | HabitatAutocomplete | InpgAutocomplete | string): string {
    if (!result || typeof result === 'string') return result || '';
    if ('cd_nom' in result) {
      return (result as TaxrefAutocomplete).nom_valide || (result as TaxrefAutocomplete).lb_nom;
    }
    if ('cd_hab' in result) {
      return (result as HabitatAutocomplete).lb_hab_fr || (result as HabitatAutocomplete).search_name || '';
    }
    return (result as InpgAutocomplete).lb_site || (result as InpgAutocomplete).id_metier || '';
  }

  getResultLabel(result: TaxrefAutocomplete | HabitatAutocomplete | InpgAutocomplete): string {
    if ('cd_nom' in result) {
      return (result as TaxrefAutocomplete).nom_valide || (result as TaxrefAutocomplete).lb_nom;
    }
    if ('cd_hab' in result) {
      const h = result as HabitatAutocomplete;
      // lb_hab_fr_complet inclut l'auteur (ex: "Klika 1933") et désambiguïse les variantes
      return h.lb_hab_fr_complet || h.lb_hab_fr || h.search_name || '';
    }
    return (result as InpgAutocomplete).lb_site || (result as InpgAutocomplete).id_metier || '';
  }

  getResultSecondary(result: TaxrefAutocomplete | HabitatAutocomplete | InpgAutocomplete): string {
    if ('cd_nom' in result) {
      const t = result as TaxrefAutocomplete;
      const rang = getTaxrefRangLabel(t.id_rang);
      const parts = [rang, t.nom_vern].filter(Boolean);
      const prefix = parts.length ? `${parts.join(' · ')} — ` : '';
      return `${prefix}cd_nom: ${t.cd_nom}`;
    }
    if ('cd_hab' in result) {
      const h = result as HabitatAutocomplete;
      const typo = h.lb_typo ? h.lb_typo.replace(/_/g, ' ') : '';
      const parts = [typo, h.lb_code].filter(Boolean);
      const prefix = parts.length ? `${parts.join(' · ')} — ` : '';
      return `${prefix}cd_hab: ${h.cd_hab}`;
    }
    const g = result as InpgAutocomplete;
    return g.id_metier ? `${g.id_metier} (id_inpg: ${g.id_inpg})` : `id_inpg: ${g.id_inpg}`;
  }
}
