import {
  Component, inject, input, output, signal, OnInit, OnDestroy,
  forwardRef
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, NG_VALUE_ACCESSOR, ControlValueAccessor } from '@angular/forms';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, switchMap, tap, filter } from 'rxjs/operators';

import { HabitatService, HabitatAutocomplete } from '../../../core/services/habitat.service';

@Component({
  selector: 'app-habitat-autocomplete',
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
  templateUrl: './habitat-autocomplete.component.html',
  styleUrl: './habitat-autocomplete.component.scss',
  providers: [
    {
      provide: NG_VALUE_ACCESSOR,
      useExisting: forwardRef(() => HabitatAutocompleteComponent),
      multi: true,
    },
  ],
})
export class HabitatAutocompleteComponent implements OnInit, OnDestroy, ControlValueAccessor {
  private readonly habitatService = inject(HabitatService);

  /** Label du champ */
  label = input<string>('Habitat');

  /** Placeholder */
  placeholder = input<string>('Rechercher un habitat...');

  /** Filtre optionnel par code de typologie */
  cdTypo = input<number | undefined>(undefined);

  /** Nombre max de résultats */
  // #238 — borne haute (la limite effective est dynamique : 20 pour 2-3
  // chars, jusqu'à `limit` pour 4+ chars).
  limit = input<number>(50);

  /** Champ obligatoire */
  required = input<boolean>(false);

  /** Événement émis quand un habitat est sélectionné */
  habitatSelected = output<HabitatAutocomplete | null>();

  searchControl = new FormControl('');
  results = signal<HabitatAutocomplete[]>([]);
  isLoading = signal(false);
  selectedHabitat = signal<HabitatAutocomplete | null>(null);

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
          // #238 — limite dynamique selon longueur de recherche.
          const effectiveLimit = search.length >= 4 ? this.limit() : Math.min(this.limit(), 20);
          return this.habitatService.autocomplete(search, {
            cdTypo: this.cdTypo(),
            limit: effectiveLimit,
          });
        }),
      ).subscribe(results => {
        this.results.set(results as HabitatAutocomplete[]);
        this.isLoading.set(false);
      })
    );
  }

  ngOnDestroy(): void {
    this.subscription.unsubscribe();
  }

  displayFn(habitat: HabitatAutocomplete | null): string {
    if (!habitat) return '';
    const code = habitat.lb_code ? `[${habitat.lb_code}] ` : '';
    return `${code}${habitat.lb_hab_fr || ''}`;
  }

  onOptionSelected(event: any): void {
    const habitat: HabitatAutocomplete = event.option.value;
    this.selectedHabitat.set(habitat);
    this.habitatSelected.emit(habitat);
    this.onChange(habitat.cd_hab);
    this.onTouched();
  }

  clear(): void {
    this.searchControl.setValue('');
    this.selectedHabitat.set(null);
    this.results.set([]);
    this.habitatSelected.emit(null);
    this.onChange(null);
  }

  // ControlValueAccessor implementation
  writeValue(value: number | null): void {
    if (!value) {
      this.searchControl.setValue('', { emitEvent: false });
      this.selectedHabitat.set(null);
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
