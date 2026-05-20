import {
  Component, inject, input, output, signal, OnInit, OnDestroy,
  EventEmitter, forwardRef
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, NG_VALUE_ACCESSOR, ControlValueAccessor } from '@angular/forms';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, tap, filter } from 'rxjs/operators';

import { TaxonomyService, TaxrefAutocomplete } from '../../../core/services/taxonomy.service';

@Component({
  selector: 'app-taxon-autocomplete',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatAutocompleteModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatProgressSpinnerModule,
    TranslateModule,
  ],
  templateUrl: './taxon-autocomplete.component.html',
  styleUrl: './taxon-autocomplete.component.scss',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => TaxonAutocompleteComponent),
      multi: true,
    },
  ],
})
export class TaxonAutocompleteComponent implements OnInit, OnDestroy, ControlValueAccessor {
  private readonly taxonomyService = inject(TaxonomyService);

  /** Label du champ */
  label = input<string>('Taxon');

  /** Placeholder */
  placeholder = input<string>('Rechercher un taxon...');

  /** Filtre optionnel par règne */
  regne = input<string | undefined>(undefined);

  /** Filtre optionnel par groupe INPN */
  group2Inpn = input<string | undefined>(undefined);

  /** Nombre max de résultats — borne haute. #238 — la limite effective est
   *  dynamique selon la longueur de la requête (20 pour 2-3 chars, jusqu'à
   *  cette valeur pour 4+ chars) afin de ne pas tronquer les recherches
   *  précises où l'utilisateur attend de voir SON taxon dans la liste. */
  limit = input<number>(50);

  /** Champ obligatoire */
  required = input<boolean>(false);

  /** Événement émis quand un taxon est sélectionné */
  taxonSelected = output<TaxrefAutocomplete | null>();

  searchControl = new FormControl('');
  results = signal<TaxrefAutocomplete[]>([]);
  isLoading = signal(false);
  selectedTaxon = signal<TaxrefAutocomplete | null>(null);

  private subscription = new Subscription();
  private onChange: (value: number | null) => void = () => {};
  private onTouched: () => void = () => {};

  ngOnInit(): void {
    this.subscription.add(
      this.searchControl.valueChanges.pipe(
        debounceTime(300),
        distinctUntilChanged(),
        filter(value => typeof value === 'string'),
        tap(() => this.isLoading.set(true)),
        switchMap(value => {
          const search = (value as string) || '';
          if (search.length < 2) {
            this.isLoading.set(false);
            return [];
          }
          // #238 — limite dynamique : 20 résultats pour 2-3 chars (autocomplete
          // exploratoire), jusqu'à `limit` pour 4+ chars (l'utilisateur cherche
          // un taxon précis et doit pouvoir le voir dans la liste).
          const effectiveLimit = search.length >= 4 ? this.limit() : Math.min(this.limit(), 20);
          return this.taxonomyService.autocomplete(search, {
            limit: effectiveLimit,
            regne: this.regne(),
            group2_inpn: this.group2Inpn(),
          });
        }),
      ).subscribe(results => {
        this.results.set(results as TaxrefAutocomplete[]);
        this.isLoading.set(false);
      })
    );
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  displayFn(taxon: TaxrefAutocomplete | null): string {
    if (!taxon) return '';
    const vern = taxon.nom_vern ? ` (${taxon.nom_vern.split(',')[0]})` : '';
    return `${taxon.lb_nom}${vern}`;
  }

  onOptionSelected(event: any): void {
    const taxon: TaxrefAutocomplete = event.option.value;
    this.selectedTaxon.set(taxon);
    this.taxonSelected.emit(taxon);
    this.onChange(taxon.cd_nom);
    this.onTouched();
  }

  clear(): void {
    this.searchControl.setValue('');
    this.selectedTaxon.set(null);
    this.results.set([]);
    this.taxonSelected.emit(null);
    this.onChange(null);
  }

  // ControlValueAccessor implementation
  writeValue(value: number | null): void {
    if (value) {
      // Si on reçoit un cd_nom, charger le taxon
      this.taxonomyService.autocomplete(value.toString()).subscribe(results => {
        const found = results.find(r => r.cd_nom === value);
        if (found) {
          this.selectedTaxon.set(found);
          this.searchControl.setValue(this.displayFn(found), { emitEvent: false });
        }
      });
    } else {
      this.searchControl.setValue('', { emitEvent: false });
      this.selectedTaxon.set(null);
    }
  }

  registerOnChange(fn: (value: number | null) => void): void {
    this.onChange = fn;
  }

  registerOnTouched(fn: () => void): void {
    this.onTouched = fn;
  }

  setDisabledState(isDisabled: boolean): void {
    if (isDisabled) {
      this.searchControl.disable();
    } else {
      this.searchControl.enable();
    }
  }
}
