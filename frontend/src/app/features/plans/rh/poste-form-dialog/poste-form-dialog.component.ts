/**
 * Formulaire d'ajout / édition d'un « type de poste » d'un plan de gestion
 * (#560, #579, #603, #604, #605).
 *
 * Aucun champ nominatif (RGPD) : un poste est décrit par sa fonction et son
 * organisme, jamais par la personne qui l'occupe.
 *
 * Le parcours dépend du **type de la fonction** choisie :
 *
 * - **salarié / stagiaire** : N personnes → une ligne par personne, chacune
 *   avec SON organisme (référentiel) et SON coût jour (#603). Chaque personne
 *   devient un `Poste` distinct (`nombre = 1`).
 * - **prestataire** : N personnes → une ligne par personne avec un organisme
 *   saisi librement (« presta1 »…). Un `Poste` par personne, sans coût jour.
 * - **bénévole** : regroupés (#605) → un seul `Poste` (`nombre = N`), sans
 *   organisme, coût jour 0.
 * - **partenaire** : regroupés (#605) → un seul `Poste` (`nombre = N`), avec un
 *   organisme saisi librement unique, sans coût jour.
 *
 * En édition (#604), tout est modifiable sur le poste : nombre, organisme et
 * coût jour (selon le type).
 */
import { Component, inject, signal, OnInit, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin } from 'rxjs';

import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';
import { RhService } from '../../../../core/services/rh.service';
import { AdminService } from '../../../../core/services/admin.service';
import {
  Fonction, Poste, PostePayload, TypePoste,
  TYPES_ORGANISME_LIBRE, isGroupedPoste,
} from '../../../../core/models/rh.model';

export interface PosteFormDialogData {
  planId: number;
  /** Poste existant à éditer, ou null pour une création. */
  poste: Poste | null;
}

interface InstanceRow {
  /** Organisme de cette personne (ex. Chargé d'études 1), référentiel. */
  id_organisme: number | null;
  /** Organisme saisi librement (prestataire hors référentiel, #599). */
  organisme_libre: string;
  /** Coût jour (€) propre à cette personne (#603). */
  cout_jour: number | null;
}

interface OrganismeOption {
  id_organisme: number;
  nom_organisme: string;
}

@Component({
  selector: 'app-poste-form-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, TranslateModule,
    MatDialogModule, MatButtonModule, MatProgressSpinnerModule,
    FormFieldComponent,
  ],
  templateUrl: './poste-form-dialog.component.html',
  styleUrl: './poste-form-dialog.component.scss',
})
export class PosteFormDialogComponent implements OnInit {
  private readonly dialogRef = inject(MatDialogRef<PosteFormDialogComponent>);
  private readonly rhService = inject(RhService);
  private readonly adminService = inject(AdminService);
  private readonly translate = inject(TranslateService);
  readonly data = inject<PosteFormDialogData>(MAT_DIALOG_DATA);

  readonly isEdit = !!this.data.poste;
  isSaving = signal(false);
  errorMessage = signal<string | null>(null);

  // Fonction choisie (une seule par type de poste, #579)
  selectedFonctionId = signal<number | null>(null);

  // Coût jour (€) global : utilisé pour un bénévole (0) et en édition d'un
  // poste salarié / stagiaire. En création salarié/stagiaire, le coût jour est
  // saisi PAR personne (#603).
  coutJour = signal<number | null>(null);

  // Ajout d'une fonction à la volée
  showNewFonction = signal(false);
  newFonctionLibelle = signal<string>('');
  newFonctionType = signal<TypePoste>('salarie');
  isCreatingFonction = signal(false);

  /**
   * Types de poste proposés à la création d'une fonction (#596, #605).
   *
   * #622 — « prestataire » n'en fait plus partie : un prestataire n'a pas de
   * coût jour, donc pas de temps de travail à programmer. Son coût se saisit
   * là où il a du sens, en « Coût prestataire » du budget de l'action (saisie
   * et suivi), qui reste inchangé. Le type existe toujours en base pour les
   * postes déjà créés.
   */
  readonly typePosteOptions: TypePoste[] = [
    'salarie', 'stagiaire', 'benevole', 'partenaire',
  ];

  // Création : une ligne (organisme + coût jour) par personne
  nombre = signal<number>(1);
  instances = signal<InstanceRow[]>([
    { id_organisme: null, organisme_libre: '', cout_jour: null },
  ]);

  // Édition : un poste unique porte un seul organisme
  idOrganisme = signal<number | null>(null);
  // Organisme saisi librement en édition (prestataire / partenaire, #599/#605)
  organismeLibre = signal<string>('');

  // Référentiels
  allFonctions = signal<Fonction[]>([]);
  organismes = signal<OrganismeOption[]>([]);

  showError = signal(false);

  /** Fonction choisie, ou undefined. */
  selectedFonction = computed<Fonction | undefined>(() =>
    this.allFonctions().find((f) => f.id_fonction === this.selectedFonctionId()),
  );

  /** Type de poste de la fonction choisie (#596). */
  selectedType = computed<TypePoste | null>(
    () => this.selectedFonction()?.type_poste ?? null,
  );

  /** Poste « regroupé » : bénévole / partenaire → un seul enregistrement (#605). */
  isGrouped = computed<boolean>(() => isGroupedPoste(this.selectedType()));

  /** Organisme saisi librement : prestataire / partenaire (#599/#605). */
  isOrganismeLibre = computed<boolean>(() => {
    const t = this.selectedType();
    return t != null && TYPES_ORGANISME_LIBRE.includes(t);
  });

  /** Bénévole : pas d'organisme du tout (#605). */
  isBenevole = computed<boolean>(() => this.selectedType() === 'benevole');

  /**
   * Le coût jour concerne salarié / stagiaire / bénévole (pas prestataire ni
   * partenaire, qui sont au forfait). #596/#605.
   */
  wantsCoutJour = computed<boolean>(() => {
    const t = this.selectedType();
    return t != null && !TYPES_ORGANISME_LIBRE.includes(t);
  });

  /** En création salarié/stagiaire, le coût jour est saisi par personne (#603). */
  coutJourPerInstance = computed<boolean>(
    () => !this.isEdit && !this.isGrouped() && this.wantsCoutJour(),
  );

  /** Coût jour global affiché : bénévole en création, ou tout poste en édition. */
  showCoutJourGlobal = computed<boolean>(
    () => this.wantsCoutJour() && (this.isEdit || this.isGrouped()),
  );

  /** Un champ coût jour est affiché quelque part (global ou par personne). */
  showCoutJour = computed<boolean>(
    () => this.coutJourPerInstance() || this.showCoutJourGlobal(),
  );

  /** Libellé de la fonction choisie, pour intituler les lignes « Stagiaire 1 »… */
  selectedFonctionLabel = computed<string>(() => this.selectedFonction()?.libelle ?? '');

  /** Erreur de formulaire, ou null. Une fonction est obligatoire. */
  formError = computed<string | null>(() => {
    if (this.selectedFonctionId() == null) {
      return this.translate.instant('plans.postes.form.errors.noFonctionSelected');
    }
    return null;
  });

  ngOnInit(): void {
    // #631 — socle partagé + fonctions propres à ce plan, jamais celles des autres.
    this.rhService.loadFonctions(this.data.planId).subscribe((list) => {
      this.allFonctions.set(this.withEditedFonction(list));
    });
    this.loadOrganismes();

    const p = this.data.poste;
    if (p) {
      // Édition : on repart sur une fonction unique (la première du poste).
      this.selectedFonctionId.set(p.fonctions?.[0]?.id_fonction ?? null);
      this.idOrganisme.set(p.id_organisme ?? null);
      this.organismeLibre.set(p.organisme_libre ?? '');
      this.nombre.set(p.nombre ?? 1);
      this.coutJour.set(p.cout_jour != null ? Number(p.cout_jour) : null);
    }
  }

  /**
   * #622 — Le référentiel n'expose que les fonctions actives. En édition, la
   * fonction du poste peut avoir été désactivée depuis (c'est le cas de
   * « Prestataire ») : sans elle dans la liste, le menu s'afficherait vide et
   * l'enregistrement perdrait la fonction. On la réinjecte donc.
   */
  private withEditedFonction(list: Fonction[]): Fonction[] {
    const pf = this.data.poste?.fonctions?.[0];
    if (!pf || list.some((f) => f.id_fonction === pf.id_fonction)) return list;
    return [
      ...list,
      {
        id_fonction: pf.id_fonction,
        libelle: pf.fonction_libelle ?? '',
        type_poste: pf.type_poste,
        finance_par_defaut: pf.finance_par_defaut ?? true,
        actif: false,
      },
    ];
  }

  /** Sélection d'une fonction → applique coût jour (#596) et défauts presta (#599). */
  onFonctionChange(id: number | null): void {
    this.selectedFonctionId.set(id);
    this.applyCoutJourDefaults();
    this.applyOrganismeLibreDefaults();
  }

  /** Nom d'organisme par défaut d'un prestataire : « presta1 », « presta2 »… (#599). */
  private prestaDefault(index: number): string {
    return `presta${index + 1}`;
  }

  /**
   * Préremplit les organismes libres quand la fonction est prestataire /
   * partenaire (#599/#605). Un partenaire est regroupé : une seule saisie.
   */
  private applyOrganismeLibreDefaults(): void {
    if (!this.isOrganismeLibre()) return;
    if (this.selectedType() === 'prestataire') {
      this.instances.update((rows) =>
        rows.map((r, i) => ({
          ...r,
          organisme_libre: r.organisme_libre || this.prestaDefault(i),
        })),
      );
    }
    if (this.isEdit && !this.organismeLibre().trim()) {
      this.organismeLibre.set(this.prestaDefault(0));
    }
  }

  setInstanceOrganismeLibre(index: number, value: string): void {
    this.instances.update((rows) =>
      rows.map((r, i) => (i === index ? { ...r, organisme_libre: value } : r)),
    );
  }

  setInstanceCoutJour(index: number, value: number | string | null): void {
    const n = this.parseCout(value);
    this.instances.update((rows) =>
      rows.map((r, i) => (i === index ? { ...r, cout_jour: n } : r)),
    );
  }

  private parseCout(value: number | string | null): number | null {
    if (value === null || value === '') return null;
    const n = Number(value);
    return isFinite(n) ? n : null;
  }

  setCoutJour(value: number | string | null): void {
    this.coutJour.set(this.parseCout(value));
  }

  /**
   * Règles de coût jour selon le type de la fonction choisie (#596/#605) :
   * prestataire / partenaire → pas de coût jour ; bénévole → 0 par défaut.
   */
  private applyCoutJourDefaults(): void {
    if (!this.wantsCoutJour()) {
      this.coutJour.set(null);
      return;
    }
    if (this.isBenevole() && this.coutJour() == null) {
      this.coutJour.set(0);
    }
  }

  /** Organismes proposés : ceux des sites du plan (mêmes que la ventilation). */
  private loadOrganismes(): void {
    this.adminService.getPlan(this.data.planId).subscribe({
      next: (plan: any) => {
        const map = new Map<number, OrganismeOption>();
        for (const site of plan.sites || []) {
          for (const org of site.organismes || []) {
            if (!map.has(org.id_organisme)) {
              map.set(org.id_organisme, {
                id_organisme: org.id_organisme,
                nom_organisme: org.nom_organisme,
              });
            }
          }
        }
        this.organismes.set(
          Array.from(map.values()).sort((a, b) =>
            a.nom_organisme.localeCompare(b.nom_organisme),
          ),
        );
      },
    });
  }

  /** Intitulé d'une ligne personne : « Chargé d'études 1 », « Chargé d'études 2 »… */
  instanceLabel(index: number): string {
    const fonction =
      this.selectedFonctionLabel() ||
      this.translate.instant('plans.postes.form.instanceGeneric');
    return this.translate.instant('plans.postes.form.instanceLabel', {
      fonction,
      index: index + 1,
    });
  }

  /** Libellé du champ « nombre » selon le type (bénévoles / partenaires / personnes). */
  nombreLabel(): string {
    const t = this.selectedType();
    if (t === 'benevole') return this.translate.instant('plans.postes.form.nombreBenevoles');
    if (t === 'partenaire') return this.translate.instant('plans.postes.form.nombrePartenaires');
    return this.translate.instant('plans.postes.form.nombrePersonnes');
  }

  /** Ajuste le nombre de lignes personnes en préservant les saisies déjà faites. */
  setNombre(value: number | string): void {
    const n = Math.max(1, Math.floor(Number(value) || 1));
    this.nombre.set(n);
    // Les types regroupés n'ont pas de ligne par personne : un seul enregistrement.
    if (this.isGrouped()) return;
    this.instances.update((rows) => {
      const next = rows.slice(0, n);
      while (next.length < n) {
        next.push({ id_organisme: null, organisme_libre: '', cout_jour: null });
      }
      return next;
    });
    this.applyOrganismeLibreDefaults();
  }

  setInstanceOrganisme(index: number, value: number | null): void {
    this.instances.update((rows) =>
      rows.map((r, i) => (i === index ? { ...r, id_organisme: value } : r)),
    );
  }

  toggleNewFonction(): void {
    this.showNewFonction.update((v) => !v);
  }

  /**
   * Crée une fonction à la volée (avec son type de poste) et la sélectionne.
   * Elle reste propre à ce plan de gestion (#631).
   */
  createFonction(): void {
    const libelle = this.newFonctionLibelle().trim();
    if (!libelle || this.isCreatingFonction()) return;
    const type = this.newFonctionType();
    this.isCreatingFonction.set(true);
    // Bénévole / partenaire ne sont pas financés par défaut (#596/#605).
    const finance = type !== 'benevole' && type !== 'partenaire';
    this.rhService.createFonction(libelle, finance, type, this.data.planId).subscribe({
      next: (f) => {
        if (!this.allFonctions().some((x) => x.id_fonction === f.id_fonction)) {
          this.allFonctions.update((list) =>
            [...list, f].sort((a, b) => a.libelle.localeCompare(b.libelle)),
          );
        }
        this.selectedFonctionId.set(f.id_fonction);
        this.applyCoutJourDefaults();
        this.applyOrganismeLibreDefaults();
        this.newFonctionLibelle.set('');
        this.newFonctionType.set('salarie');
        this.showNewFonction.set(false);
        this.isCreatingFonction.set(false);
      },
      error: () => this.isCreatingFonction.set(false),
    });
  }

  save(): void {
    if (this.formError()) {
      this.showError.set(true);
      return;
    }
    this.showError.set(false);
    this.isSaving.set(true);
    this.errorMessage.set(null);

    const fonctions = [{ id_fonction: this.selectedFonctionId()!, pourcentage: null }];
    const libre = this.isOrganismeLibre();
    const benevole = this.isBenevole();

    if (this.isEdit) {
      const payload: Partial<PostePayload> = {
        id_pg: this.data.planId,
        // Prestataire / partenaire → organisme libre ; bénévole → aucun ; sinon référentiel.
        id_organisme: libre || benevole ? null : (this.idOrganisme() ?? null),
        organisme_libre: libre ? this.organismeLibre().trim() : '',
        // #604 — le nombre est désormais modifiable en édition.
        nombre: this.nombre() || 1,
        cout_jour: this.wantsCoutJour() ? this.coutJour() : null,
        fonctions,
      };
      this.rhService.updatePoste(this.data.poste!.id_poste!, payload).subscribe({
        next: (poste) => this.dialogRef.close(poste),
        error: () => {
          this.errorMessage.set('error');
          this.isSaving.set(false);
        },
      });
      return;
    }

    // Création regroupée (bénévole / partenaire) : un seul poste, nombre = N (#605).
    if (this.isGrouped()) {
      this.rhService
        .createPoste({
          id_pg: this.data.planId,
          id_organisme: null,
          organisme_libre: libre ? this.organismeLibre().trim() : '',
          nombre: this.nombre() || 1,
          cout_jour: benevole ? (this.coutJour() ?? 0) : null,
          fonctions,
        })
        .subscribe({
          next: (poste) => this.dialogRef.close([poste]),
          error: () => {
            this.errorMessage.set('error');
            this.isSaving.set(false);
          },
        });
      return;
    }

    // Création par personne : un poste (nombre = 1) par ligne, avec son
    // organisme et son coût jour (#603).
    const requests = this.instances().map((inst) =>
      this.rhService.createPoste({
        id_pg: this.data.planId,
        id_organisme: libre ? null : (inst.id_organisme ?? null),
        organisme_libre: libre ? inst.organisme_libre.trim() : '',
        nombre: 1,
        cout_jour: this.wantsCoutJour() ? inst.cout_jour : null,
        fonctions,
      }),
    );
    forkJoin(requests).subscribe({
      next: (postes) => this.dialogRef.close(postes),
      error: () => {
        this.errorMessage.set('error');
        this.isSaving.set(false);
      },
    });
  }

  cancel(): void {
    this.dialogRef.close(null);
  }
}
