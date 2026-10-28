import { ChangeDetectionStrategy, Component, computed, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { HttpErrorResponse } from '@angular/common/http';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatButtonModule } from '@angular/material/button';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatRadioModule } from '@angular/material/radio';
import { MatSelectModule } from '@angular/material/select';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import { AdminService } from '../../../../core/services/admin.service';
import { InventaireService } from '../../../../core/services/inventaire.service';
import {
  OptionType, ReferentielActionsService, SuiviActualisation, TypeDejaModifie,
} from '../../../../core/services/referentiel-actions.service';
import { ProtocoleActionComponent } from '../../../../features/plans/enjeux/operation-form/protocole-action/protocole-action.component';
import {
  buildNomenclatureGroups, displayNomenclatureFn, getNomenclatureDepth, NomenclatureOption,
} from '../../../utils/nomenclature-autocomplete.utils';

export interface ActualiserTypeDialogData {
  operationId: number;
  libelle: string;
  codeAffichage?: string | null;
  ancienCode: string;
  ancienLibelle: string;
  /** #776 — équivalents proposés par la table (le premier = la proposition). */
  options: OptionType[];
  note: string;
  /** Type affiché à l'ouverture : sert à détecter un choix concurrent. */
  typeActuelId: number | null;
  /** Code du type actuel (ancien type conservé, ou type posé automatiquement). */
  typeActuelCode?: string | null;
  /** L'action a déjà un suivi : elle peut devenir CS sans autre question. */
  aUnSuivi: boolean;
  /** `correction` : changer un type posé automatiquement (#776). */
  mode?: 'choix' | 'correction';
}

export interface ActualiserTypeDialogResult {
  /** Fiche de l'action renvoyée par le serveur après enregistrement. */
  operation?: unknown;
  /** Un autre référent a choisi le type entre-temps. */
  conflit?: TypeDejaModifie;
}

interface SuiviExistant {
  id_suivi_inventaire: number;
  intitule: string;
}

const estCs = (code: string | null | undefined) => (code || '').startsWith('CS');

/**
 * #751 / #776 — choisir (ou corriger) le type d'une action après un passage du
 * référentiel des types d'action. Fonctionne dans un plan validé ou archivé
 * (seul le type change). Les équivalents de la table se choisissent en un clic,
 * la recherche libre reste ouverte ; une action qui devient CS sans suivi reçoit
 * un suivi existant ou nouveau (questions obligatoires d'un suivi).
 */
@Component({
  selector: 'app-actualiser-type-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule, MatDialogModule, MatButtonModule, MatAutocompleteModule,
    MatFormFieldModule, MatInputModule, MatRadioModule, MatSelectModule, TranslateModule,
    ProtocoleActionComponent,
  ],
  templateUrl: './actualiser-type-dialog.component.html',
  styleUrl: './actualiser-type-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class ActualiserTypeDialogComponent implements OnInit {
  private readonly dialogRef = inject(MatDialogRef<ActualiserTypeDialogComponent, ActualiserTypeDialogResult>);
  private readonly adminService = inject(AdminService);
  private readonly inventaireService = inject(InventaireService);
  private readonly service = inject(ReferentielActionsService);
  private readonly translate = inject(TranslateService);
  private readonly fb = inject(FormBuilder);
  readonly data: ActualiserTypeDialogData = inject(MAT_DIALOG_DATA);

  readonly options = signal<NomenclatureOption[]>([]);
  readonly recherche = signal('');
  readonly choisi = signal<NomenclatureOption | null>(null);
  readonly enregistrement = signal(false);
  readonly erreur = signal<string | null>(null);
  readonly conflit = signal<TypeDejaModifie | null>(null);
  readonly searchCtrl = new FormControl<string | NomenclatureOption>('');

  readonly groupes = computed(() => buildNomenclatureGroups(this.options(), this.recherche()));
  /** En correction, le type déjà posé n'est pas reproposé : seuls les autres équivalents. */
  readonly propositions = computed(() => (this.data.options ?? []).filter(
    o => this.data.mode !== 'correction' || o.id !== this.data.typeActuelId));

  // ── Suivi d'une action qui devient CS ─────────────────────────────────
  readonly devientCs = computed(() => {
    const t = this.choisi();
    return !!t && estCs(t.cd_nomenclature || t.mnemonique)
      && !estCs(this.data.typeActuelCode) && !this.data.aUnSuivi;
  });
  readonly modeSuivi = signal<'existant' | 'nouveau'>('nouveau');
  readonly suivisExistants = signal<SuiviExistant[]>([]);
  readonly objectifs = signal<NomenclatureOption[]>([]);
  readonly cibles = signal<NomenclatureOption[]>([]);
  readonly suiviExistantCtrl = new FormControl<number | null>(null);
  readonly suiviForm = this.fb.group({
    intitule: [this.data.libelle || '', Validators.required],
    objectif_principal: ['', Validators.required],
    cibles_principales: ['', Validators.required],
  });
  readonly protocoleForm = this.fb.group({
    id_protocole: [null as number | null],
    protocole_dans_campanule: [null as boolean | null, Validators.required],
    protocole_campanule_nom: [''],
    cd_protocole_campanule: [null as number | null],
    nb_etp_cycle: [null as number | null],
    nom_protocole: [''],
    respect_protocole: [null as boolean | null],
    justification_non_respect: [''],
    differences_protocole: [''],
    description_protocole: [''],
    objectif_protocole: [''],
    periode_echantillonnage: [''],
  });

  readonly display = displayNomenclatureFn;
  readonly depth = getNomenclatureDepth;

  ngOnInit(): void {
    this.adminService.getNomenclaturesByType('TYPE_ACTION').subscribe({
      next: opts => this.options.set(opts as NomenclatureOption[]),
      error: () => this.options.set([]),
    });
    this.adminService.getNomenclaturesByType('OBJECTIF_SUIVI').subscribe({
      next: opts => this.objectifs.set(opts as NomenclatureOption[]),
      error: () => this.objectifs.set([]),
    });
    this.adminService.getNomenclaturesByType('CIBLE_SUIVI').subscribe({
      next: opts => this.cibles.set(opts as NomenclatureOption[]),
      error: () => this.cibles.set([]),
    });
    this.searchCtrl.valueChanges.subscribe(v => {
      if (typeof v === 'string') {
        this.recherche.set(v);
        if (this.choisi() && v !== this.display(this.choisi())) this.choisi.set(null);
      }
    });
  }

  choisir(option: NomenclatureOption): void {
    this.choisi.set(option);
    this.searchCtrl.setValue(option, { emitEvent: false });
    if (this.devientCs()) this.chargerSuivis(option.cd_nomenclature || option.mnemonique);
  }

  /** Un équivalent de la table, pris en un clic. */
  choisirProposition(p: OptionType): void {
    const option = this.options().find(o => o.id_nomenclature === p.id)
      ?? { id_nomenclature: p.id, mnemonique: p.code, cd_nomenclature: p.code, label: p.libelle };
    this.choisir(option);
  }

  estChoisie(p: OptionType): boolean {
    return this.choisi()?.id_nomenclature === p.id;
  }

  effacer(): void {
    this.choisi.set(null);
    this.searchCtrl.setValue('');
  }

  private chargerSuivis(code: string): void {
    this.inventaireService.getInventaires({ type_action_prefix: code, page_size: 200 }).subscribe({
      next: res => this.suivisExistants.set((res.results || []).map(s => ({
        id_suivi_inventaire: s.id_suivi_inventaire, intitule: s.intitule,
      }))),
      error: () => this.suivisExistants.set([]),
    });
  }

  /** Le suivi à envoyer, ou `null` s'il manque une réponse obligatoire. */
  private suiviAEnvoyer(): SuiviActualisation | null | undefined {
    if (!this.devientCs()) return undefined;
    if (this.modeSuivi() === 'existant') {
      const id = this.suiviExistantCtrl.value;
      return id ? { id_suivi: id } : null;
    }
    this.suiviForm.markAllAsTouched();
    this.protocoleForm.markAllAsTouched();
    const p = this.protocoleForm.getRawValue();
    const protocoleOk = p.protocole_dans_campanule !== null
      && (!p.protocole_dans_campanule || !!p.cd_protocole_campanule);
    if (this.suiviForm.invalid || !protocoleOk) return null;
    const { id_protocole, ...protocole } = p;
    return { ...this.suiviForm.getRawValue() as SuiviActualisation, protocoles: [protocole] };
  }

  readonly suiviIncomplet = signal(false);

  annuler(): void {
    this.dialogRef.close();
  }

  valider(): void {
    const type = this.choisi();
    if (!type || this.enregistrement()) return;
    const suivi = this.suiviAEnvoyer();
    this.suiviIncomplet.set(suivi === null);
    if (suivi === null) return;
    this.enregistrement.set(true);
    this.erreur.set(null);
    this.service.actualiserType(this.data.operationId, type.id_nomenclature, this.data.typeActuelId,
      suivi ?? undefined).subscribe({
      next: operation => this.dialogRef.close({ operation }),
      error: (e: HttpErrorResponse) => {
        this.enregistrement.set(false);
        if (e.status === 409 && e.error?.code === 'type_deja_modifie') {
          this.conflit.set(e.error as TypeDejaModifie);
          return;
        }
        this.erreur.set(e.error?.detail || e.error?.id_type_action?.[0]
          || this.translate.instant('referentielActions.dialog.erreur'));
      },
    });
  }

  fermerSurConflit(): void {
    this.dialogRef.close({ conflit: this.conflit() ?? undefined });
  }
}
