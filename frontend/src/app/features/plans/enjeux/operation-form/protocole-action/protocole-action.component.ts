import { ChangeDetectionStrategy, Component, DestroyRef, EventEmitter, Input, OnChanges, OnInit, Output, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule } from '@angular/common';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { TranslateModule } from '@ngx-translate/core';
import { debounceTime, distinctUntilChanged, filter, switchMap } from 'rxjs/operators';

import { CampanuleService } from '../../../../../core/services/campanule.service';
import { CampanuleAutocomplete, campanuleProtocoleLabel } from '../../../../../core/models/campanule.model';
import { FormFieldComponent } from '../../../../../shared/components/form-field/form-field.component';
import { ProtocoleCampanuleDialogComponent } from '../../../../../shared/components/modals/protocole-campanule-dialog/protocole-campanule-dialog.component';

/**
 * Un protocole d'une action de suivi (CS), dans la fiche action (#732).
 *
 * La fiche action saisit N protocoles (#252) : chaque bloc édite son propre
 * `FormGroup` (créé par le formulaire parent) et porte son propre état de
 * recherche CAMPanule, pour que deux protocoles ne se partagent ni la liste
 * proposée ni la sélection.
 */
@Component({
  selector: 'app-protocole-action',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatRadioModule,
    MatAutocompleteModule,
    MatDialogModule,
    TranslateModule,
    FormFieldComponent,
  ],
  templateUrl: './protocole-action.component.html',
  styleUrls: ['./protocole-action.component.scss'],
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ProtocoleActionComponent implements OnInit, OnChanges {
  private readonly campanuleService = inject(CampanuleService);
  private readonly dialog = inject(MatDialog);
  private readonly destroyRef = inject(DestroyRef);

  /** Groupe du protocole, dans le FormArray `protocoles` du formulaire parent. */
  @Input({ required: true }) group!: FormGroup;
  /** Titre du bloc (nom du protocole, sinon « Protocole n »). */
  @Input() titre = '';
  /** Affiche le bouton de retrait (pas sur le dernier bloc restant). */
  @Input() retirable = false;
  /** Lecture seule (plan verrouillé) : ni recherche ni retrait. */
  @Input() lectureSeule = false;

  @Output() retirer = new EventEmitter<void>();

  /** #584 — nombre de protocoles proposés quand aucun terme n'est saisi. */
  private static readonly CAMPANULE_DEFAULT_LIMIT = 100;

  campanuleSearchCtrl = new FormControl('');
  campanuleResults = signal<CampanuleAutocomplete[]>([]);
  selectedCampanule = signal<CampanuleAutocomplete | null>(null);

  ngOnInit(): void {
    // Sélection CAMPanule déjà enregistrée : on la réaffiche dans la recherche.
    const cd = this.group.get('cd_protocole_campanule')?.value;
    const nom = this.group.get('protocole_campanule_nom')?.value;
    if (cd && nom) {
      this.campanuleSearchCtrl.setValue(nom, { emitEvent: false });
      this.selectedCampanule.set({ cd_protocole: cd, search_name: nom, lb_protocole_court: nom });
    }

    this.campanuleSearchCtrl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      // Une chaîne vide est acceptée : elle recharge la liste alphabétique (#584).
      filter((val): val is string => typeof val === 'string'),
      switchMap((search) => this.campanuleService.autocomplete(
        search,
        search ? 20 : ProtocoleActionComponent.CAMPANULE_DEFAULT_LIMIT,
      )),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (results) => this.campanuleResults.set(results),
      error: () => this.campanuleResults.set([]),
    });
  }

  ngOnChanges(): void {
    // Le parent désactive le groupe (plan verrouillé, suivi existant) ; la
    // recherche CAMPanule, hors du groupe, suit le même état.
    if (this.lectureSeule || this.group?.disabled) {
      this.campanuleSearchCtrl.disable({ emitEvent: false });
    } else {
      this.campanuleSearchCtrl.enable({ emitEvent: false });
    }
  }

  get isCampanule(): boolean {
    return this.group.get('protocole_dans_campanule')?.value === true;
  }

  get isNotCampanule(): boolean {
    return this.group.get('protocole_dans_campanule')?.value === false;
  }

  get isNonRespect(): boolean {
    return this.group.get('respect_protocole')?.value === false;
  }

  get hasCampanuleSelected(): boolean {
    return !!this.group.get('cd_protocole_campanule')?.value;
  }

  /**
   * #584 — Au clic dans le champ, on affiche d'emblée les protocoles par ordre
   * alphabétique plutôt qu'une liste vide en attente de saisie.
   */
  onCampanuleFocus(): void {
    const search = this.campanuleSearchCtrl.value;
    if (typeof search === 'string' && search.length > 0) return;
    if (this.campanuleResults().length > 0) return;

    this.campanuleService
      .autocomplete('', ProtocoleActionComponent.CAMPANULE_DEFAULT_LIMIT)
      .subscribe({
        next: (results) => this.campanuleResults.set(results),
        error: () => this.campanuleResults.set([]),
      });
  }

  /** Libellé d'affichage d'un protocole (nom court, sinon nom complet). #564 */
  campanuleLabel(option: CampanuleAutocomplete): string {
    return campanuleProtocoleLabel(option);
  }

  displayCampanuleFn(option: CampanuleAutocomplete | string): string {
    if (!option) return '';
    if (typeof option === 'string') return option;
    return campanuleProtocoleLabel(option);
  }

  onCampanuleSelected(event: { option: { value: CampanuleAutocomplete } }): void {
    const selected = event.option.value;
    this.selectedCampanule.set(selected);
    // Ne pas appeler setValue ici : Angular Material gère l'affichage via displayWith

    this.group.patchValue({
      protocole_campanule_nom: campanuleProtocoleLabel(selected),
      cd_protocole_campanule: selected.cd_protocole,
    });

    // Description / objectif / période repris de la fiche CAMPanule.
    this.campanuleService.getProtocole(selected.cd_protocole).subscribe({
      next: (detail) => {
        this.group.patchValue({
          description_protocole: detail.description || '',
          objectif_protocole: detail.descr_objectif_prot || '',
        });
        const periodes = (detail.echantillonnages || [])
          .filter((e) => e.periode_an)
          .map((e) => e.periode_an)
          .join('; ');
        if (periodes) this.group.patchValue({ periode_echantillonnage: periodes });
      },
    });
  }

  onCampanuleReset(): void {
    this.selectedCampanule.set(null);
    this.campanuleSearchCtrl.setValue('');
    this.group.patchValue({
      protocole_campanule_nom: '',
      cd_protocole_campanule: null,
      description_protocole: '',
      objectif_protocole: '',
      periode_echantillonnage: '',
    });
  }

  /**
   * #520 — Mémoire des valeurs saisies MANUELLEMENT (mode « Non ») pour ne pas
   * les perdre lors d'un aller-retour du choix CAMPanule.
   */
  private manualProtocoleSnapshot: {
    description_protocole: string;
    objectif_protocole: string;
    periode_echantillonnage: string;
  } | null = null;

  /**
   * #520 — Mémoire de la sélection CAMPanule (mode « Oui ») pour la restaurer
   * si l'on rebascule sur « Oui » sans avoir à re-rechercher le protocole.
   */
  private campanuleSnapshot: {
    selected: CampanuleAutocomplete | null;
    protocole_campanule_nom: string;
    cd_protocole_campanule: number | null;
    description_protocole: string;
    objectif_protocole: string;
    periode_echantillonnage: string;
  } | null = null;

  /**
   * #520 — Au changement MANUEL du choix « le protocole est-il dans CAMPanule ? ».
   *
   * Les champs description / objectif / période sont partagés entre les deux
   * modes : on garde deux « canaux » en mémoire, pour qu'un aller-retour du
   * choix ne perde ni la saisie manuelle ni la sélection CAMPanule. Branché sur
   * (change) du radio : ne se déclenche pas au chargement en édition.
   */
  onProtocoleCampanuleChange(): void {
    const g = this.group;
    if (this.isCampanule) {
      // Non → Oui : archiver la saisie manuelle, restaurer la sélection CAMPanule
      this.manualProtocoleSnapshot = {
        description_protocole: g.get('description_protocole')?.value || '',
        objectif_protocole: g.get('objectif_protocole')?.value || '',
        periode_echantillonnage: g.get('periode_echantillonnage')?.value || '',
      };
      if (this.campanuleSnapshot) {
        const snap = this.campanuleSnapshot;
        this.selectedCampanule.set(snap.selected);
        this.campanuleSearchCtrl.setValue(snap.protocole_campanule_nom, { emitEvent: false });
        g.patchValue({
          protocole_campanule_nom: snap.protocole_campanule_nom,
          cd_protocole_campanule: snap.cd_protocole_campanule,
          description_protocole: snap.description_protocole,
          objectif_protocole: snap.objectif_protocole,
          periode_echantillonnage: snap.periode_echantillonnage,
        });
      } else {
        this.onCampanuleReset();
      }
    } else {
      // Oui → Non : archiver la sélection CAMPanule, restaurer la saisie manuelle
      this.campanuleSnapshot = {
        selected: this.selectedCampanule(),
        protocole_campanule_nom: g.get('protocole_campanule_nom')?.value || '',
        cd_protocole_campanule: g.get('cd_protocole_campanule')?.value ?? null,
        description_protocole: g.get('description_protocole')?.value || '',
        objectif_protocole: g.get('objectif_protocole')?.value || '',
        periode_echantillonnage: g.get('periode_echantillonnage')?.value || '',
      };
      this.selectedCampanule.set(null);
      this.campanuleSearchCtrl.setValue('', { emitEvent: false });
      const manual = this.manualProtocoleSnapshot;
      g.patchValue({
        protocole_campanule_nom: '',
        cd_protocole_campanule: null,
        description_protocole: manual?.description_protocole ?? '',
        objectif_protocole: manual?.objectif_protocole ?? '',
        periode_echantillonnage: manual?.periode_echantillonnage ?? '',
      });
    }
  }

  consulterProtocole(): void {
    const cdProtocole = this.group.get('cd_protocole_campanule')?.value;
    if (!cdProtocole) return;
    this.dialog.open(ProtocoleCampanuleDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { cdProtocole },
    });
  }
}
