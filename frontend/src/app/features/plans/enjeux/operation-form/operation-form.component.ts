/**
 * Page dédiée formulaire opération (action) - création + édition.
 * Conforme au Figma node-id=154-10720.
 *
 * Refactorisé pour utiliser OperationAnnee[] (table relationnelle)
 * au lieu de JSONField programmation_annuelle/programmation_mensuelle.
 */
import { Component, OnInit, inject, signal, computed, ElementRef, DestroyRef } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { CommonModule, Location } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { FormBuilder, FormControl, FormGroup, Validators, ReactiveFormsModule, FormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatSelectModule } from '@angular/material/select';
import { MatRadioModule } from '@angular/material/radio';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatDatepickerModule } from '@angular/material/datepicker';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatDialogModule, MatDialog } from '@angular/material/dialog';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { forkJoin, of, Observable, Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, filter, switchMap, groupBy, mergeMap, catchError } from 'rxjs/operators';

import { HeaderComponent } from '../../../../shared/components/header/header.component';
import { ReferenceItemListComponent } from '../../../../shared/components/reference-item-list/reference-item-list.component';
import { CheckboxComponent } from '../../../../shared/components/checkbox/checkbox.component';
import { EmpriseEditorComponent } from '../../../../shared/components/emprise-editor/emprise-editor.component';
import { AccordionComponent } from '../../../../shared/components/accordion/accordion.component';
import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';
import { MetriqueFormComponent } from '../../../../shared/components/metrique-form/metrique-form.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { AdminService } from '../../../../core/services/admin.service';
import { CampanuleService } from '../../../../core/services/campanule.service';
import { InventaireService } from '../../../../core/services/inventaire.service';
import { SuiviInventaireDetail } from '../../../../core/models/inventaire.model';
import { Operation, OperationCreatePayload, OperationStatut, OperationAnnee, OperationAnneeOrganisme, FinanceOperation, SuiviInventaire, TaxonRef, HabitatRef, GeologieRef, MetriqueFormData, MetriqueRef, Enjeu } from '../../../../core/models/enjeu.model';
import { CampanuleAutocomplete } from '../../../../core/models/campanule.model';
import { PlanSite, PlanSiteOrganisme } from '../../../../core/models/admin.model';
import { ProtocoleCampanuleDialogComponent } from '../../../../shared/components/modals/protocole-campanule-dialog/protocole-campanule-dialog.component';
import { FrequencyApplyDialogComponent, FrequencyApplyDialogResult } from '../../../../shared/components/modals/frequency-apply-dialog/frequency-apply-dialog.component';

import {
  NomenclatureOption,
  NomenclatureGroup,
  buildNomenclatureGroups,
  getNomenclatureDepth,
  displayNomenclatureFn,
} from '../../../../shared/utils/nomenclature-autocomplete.utils';
import {
  blankMetriqueFormData,
  metriqueRefToFormData,
  buildMetriqueGridFields,
} from '../../../../shared/utils/metrique-form.util';

/** Option de type de métrique brute (nomenclature TYPE_METRIQUE). */
type TypeMetriqueNomenclature = { id_nomenclature: number; mnemonique?: string; label: string };

/**
 * #452 — Types de métrique proposés pour un indicateur de réponse en saisie SIMPLE
 * (case « grille de scoring » décochée) : uniquement « Chiffrée » (CHIFFRE) et
 * « Textuelle » (TEXTE). « Pas de réponse » est l'option vide du select ; le type
 * « Intervalle numérique » (NUMERIQUE) est réservé au mode grille.
 */
export function buildResponseTypeOptions(
  opts: TypeMetriqueNomenclature[],
  translate: (key: string) => string,
): { id: number; label: string }[] {
  const out: { id: number; label: string }[] = [];
  const chiffre = opts.find(o => o.mnemonique === 'CHIFFRE');
  if (chiffre) out.push({ id: chiffre.id_nomenclature, label: translate('enjeux.operations.metriqueTypeChiffree') });
  const texte = opts.find(o => o.mnemonique === 'TEXTE');
  if (texte) out.push({ id: texte.id_nomenclature, label: translate('enjeux.operations.metriqueTypeTextuelle') });
  return out;
}

/**
 * #452 — Types proposés à l'éditeur de grille embarqué (case cochée) : tous les
 * types sauf INDETERMINE (Intervalle numérique, Chiffre, Texte).
 */
export function buildGridTypeMetriqueOptions(
  opts: TypeMetriqueNomenclature[],
): { id_nomenclature: number; mnemonique: string; label: string }[] {
  return opts
    .filter(o => o.mnemonique !== 'INDETERMINE')
    .map(o => ({ id_nomenclature: o.id_nomenclature, mnemonique: o.mnemonique || '', label: o.label }));
}

@Component({
  selector: 'app-operation-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatSelectModule,
    CheckboxComponent,
    MatRadioModule,
    MatProgressSpinnerModule,
    MatDatepickerModule,
    MatSnackBarModule,
    MatAutocompleteModule,
    MatDialogModule,
    MatTooltipModule,
    TranslateModule,
    HeaderComponent,
    ReferenceItemListComponent,
    AccordionComponent,
    FormFieldComponent,
    EmpriseEditorComponent,
    MetriqueFormComponent,
  ],
  templateUrl: './operation-form.component.html',
  styleUrl: './operation-form.component.scss'
})
export class OperationFormComponent implements OnInit {
  private readonly elRef = inject(ElementRef);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly destroyRef = inject(DestroyRef);
  private readonly location = inject(Location);
  private readonly fb = inject(FormBuilder);
  private readonly enjeuService = inject(EnjeuService);
  private readonly adminService = inject(AdminService);
  private readonly campanuleService = inject(CampanuleService);
  private readonly inventaireService = inject(InventaireService);
  private readonly translate = inject(TranslateService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);

  form!: FormGroup;
  isLoading = signal(false);
  isLoadingData = signal(true);
  errorMessage = signal<string | null>(null);

  planId = signal<number | null>(null);
  planSlug = signal<string | null>(null);
  planNom = signal<string>('');
  operationId = signal<number | null>(null);
  isEditMode = signal(false);
  /** Mode lecture seule : la route `operations/:id` (sans /modifier) définit data.readOnly = true */
  isReadOnly = signal(false);
  existingOperation = signal<Operation | null>(null);

  /** Indicateurs de réponse rattachés à l'action : seulement les métriques dont
   * l'indicateur est de type REPONSE (les métriques associées état/pression
   * s'affichent dans la section « Métriques associées », pas ici). */
  responseIndicators = computed(() =>
    (this.existingOperation()?.metriques || []).filter(m => m.indicateur_type === 'REPONSE')
  );

  /** Indicateurs de réponse saisis avant l'enregistrement (création d'action) :
   * conservés en mémoire puis créés côté serveur à la sauvegarde de l'action. */
  pendingResponseIndicators: {
    nom_indicateur: string;
    nom_metrique: string;
    type_metrique_id: number | null;
    valeur_cible: string;
    // #452 — format (id nomenclature) + grille en mémoire (éditée avant l'enregistrement
    // de l'action) ; envoyés au backend à la création.
    format_metrique_id: number | null;
    formData?: MetriqueFormData;
  }[] = [];

  /** #452 — Passe à `true` quand on tente de valider l'action avec un indicateur
   *  de réponse sans intitulé : déclenche l'affichage de l'erreur sous les champs
   *  « Intitulé de l'indicateur de réponse » concernés. */
  showResponseTitleErrors = signal(false);

  /** #452 — Un intitulé d'indicateur de réponse est « manquant » s'il est vide
   *  OU s'il est resté le nom par défaut (« Nouvel indicateur de réponse ») : on
   *  force l'utilisateur à saisir un vrai intitulé avant de valider l'action. */
  private isBlankResponseTitle(nom: string | null | undefined): boolean {
    const v = (nom || '').trim();
    return !v || v === this.translate.instant('enjeux.operations.newIndicatorDefault');
  }

  /** #452 — Vrai si un indicateur de réponse (enregistré ou en attente) n'a pas
   *  d'intitulé valide. L'intitulé est obligatoire pour valider l'action. */
  hasMissingResponseTitle(): boolean {
    return this.responseIndicators().some(m => this.isBlankResponseTitle(m.indicateur_nom))
      || this.pendingResponseIndicators.some(pi => this.isBlankResponseTitle(pi.nom_indicateur));
  }

  /** #452 — Message d'erreur à afficher sous un champ « Intitulé de l'indicateur
   *  de réponse » (null si pas d'erreur ou validation pas encore tentée). */
  responseTitleError(nom: string | null | undefined): string | null {
    return this.showResponseTitleErrors() && this.isBlankResponseTitle(nom)
      ? this.translate.instant('enjeux.operations.indicateurReponseTitleError')
      : null;
  }

  /** Emprise spatiale en cours d'édition (#342). undefined = inchangée. */
  pendingEmprise = signal<any | undefined>(undefined);
  /** Emprise à afficher : modif locale en priorité, sinon valeur serveur. */
  empriseGeom = computed<any>(() => {
    const pending = this.pendingEmprise();
    if (pending !== undefined) return pending;
    return this.existingOperation()?.geom_geojson ?? null;
  });

  /** #410 — « l'emprise de l'action correspond à l'emprise du/des site(s) ».
   *  Quand coché, l'emprise est calculée depuis les sites sélectionnés et le
   *  dessin manuel est désactivé. */
  useSiteEmprise = signal(false);
  isComputingSiteEmprise = signal(false);

  /** #410 — nombre de sites cochés (réactif via selectedSiteIdsVersion). */
  selectedSitesCount = computed<number>(() => {
    this.selectedSiteIdsVersion();
    return Object.values(this.selectedSiteIds).filter(Boolean).length;
  });
  /** Types de métrique disponibles (TYPE_METRIQUE nomenclature). */
  typeMetriqueOptions = signal<{ id_nomenclature: number; mnemonique?: string; label: string }[]>([]);

  /** #347/réponse — Pour les indicateurs de réponse en saisie SIMPLE (sans grille),
   * le type de métrique se limite à « Pas de réponse » (option vide), « Chiffrée »
   * (CHIFFRE) ou « Textuelle » (TEXTE). Le type « Intervalle numérique » (NUMERIQUE)
   * n'est proposé qu'en mode grille (#452 — cf. retour de test) via
   * {@link gridTypeMetriqueOptions}. Logique pure extraite dans
   * {@link buildResponseTypeOptions} pour la testabilité. */
  responseTypeOptions = computed<{ id: number; label: string }[]>(() =>
    buildResponseTypeOptions(this.typeMetriqueOptions(), (k) => this.translate.instant(k)),
  );

  /** #452 — Formats de métrique (SIMPLE / GRILLE) chargés depuis la nomenclature. */
  formatMetriqueOptions = signal<{ id_nomenclature: number; mnemonique?: string; label: string }[]>([]);

  /** Liste de types proposée à l'éditeur de grille embarqué : on exclut INDETERMINE.
   *  Logique pure extraite dans {@link buildGridTypeMetriqueOptions}. */
  gridTypeMetriqueOptions = computed<{ id_nomenclature: number; mnemonique: string; label: string }[]>(() =>
    buildGridTypeMetriqueOptions(this.typeMetriqueOptions()),
  );

  private formatId(mnemonique: 'SIMPLE' | 'GRILLE'): number | null {
    return this.formatMetriqueOptions().find(o => o.mnemonique === mnemonique)?.id_nomenclature ?? null;
  }
  /** Vrai si le format (id nomenclature) correspond à GRILLE. */
  isGrilleFormat(formatId: number | null | undefined): boolean {
    if (formatId == null) return false;
    return this.formatMetriqueOptions().find(o => o.id_nomenclature === formatId)?.mnemonique === 'GRILLE';
  }
  /** Vrai si une métrique de réponse (sauvegardée) est en format GRILLE. */
  isResponseGrille(ref: MetriqueRef): boolean {
    return (ref.format_metrique_mnemonique || '') === 'GRILLE';
  }

  /** #452 — MetriqueFormData (éditeur de grille) par métrique de réponse sauvegardée,
   *  construit à la demande et mémoïsé (clé = id_metrique). */
  private responseFormDataMap = new Map<number, MetriqueFormData>();
  /** Émetteur d'auto-sauvegarde débouncée de la grille (action déjà enregistrée). */
  private gridSave$ = new Subject<{ metriqueId: number; data: MetriqueFormData }>();

  /** Aide « comment remplir un indicateur de réponse » : 3 exemples affichés
   *  au survol (tooltip multi-ligne) pour ne pas alourdir le formulaire. */
  get reponseExamplesTooltip(): string {
    return [
      this.translate.instant('enjeux.operations.reponseExample1'),
      this.translate.instant('enjeux.operations.reponseExample2'),
      this.translate.instant('enjeux.operations.reponseExample3'),
    ].join('\n\n');
  }

  // Query params
  prelinkedMetriqueId = signal<number | null>(null);
  // #1 — Liste de métriques à pré-lier quand l'action est créée au niveau
  // indicateur. Supersede `prelinkedMetriqueId` (qui reste utilisé pour
  // l'auto-scroll et la rétrocompatibilité avec les liens single-metric).
  prelinkedMetriqueIds = signal<number[]>([]);
  // #367 — indicateur de rattachement direct (action créée sans métrique).
  prelinkedIndicateurId = signal<number | null>(null);
  returnEnjeuSlug = signal<string | null>(null);
  // #398 — onglet d'origine (« olt » ou « operations ») pour y revenir après
  // création. Sans ça, une action créée depuis l'onglet OLT renvoyait vers
  // l'onglet Opérations (où une action sans métrique n'apparaît pas).
  returnTab = signal<string | null>(null);

  // Nomenclatures
  typeActionOptions = signal<NomenclatureOption[]>([]);
  prioriteOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);

  // Type d'action autocomplete
  typeActionSearchCtrl = new FormControl('');
  typeActionGroups = computed<NomenclatureGroup[]>(() => {
    return this.buildActionGroups(this.typeActionOptions(), this.typeActionSearchText());
  });
  typeActionSearchText = signal('');
  selectedTypeAction = signal<NomenclatureOption | null>(null);

  /** Vrai si le type d'action sélectionné est un code CS (Connaissance et Suivi) */
  isCSAction = computed(() => {
    const selected = this.selectedTypeAction();
    if (!selected) return false;
    const code = selected.cd_nomenclature || selected.mnemonique || '';
    return code.startsWith('CS');
  });

  // #228 — Catégorie d'action réserve (CT88, 9 entrées avec code 2 lettres).
  categorieActionReserveOptions = signal<NomenclatureOption[]>([]);
  categorieActionReserveCtrl = new FormControl<number | null>(null);

  /**
   * Préfixe 2 lettres calculé côté UI pour aperçu en temps réel — priorité
   * à la catégorie d'action réserve, sinon lettres de tête du type d'action.
   * Le code complet (avec rang) est calculé côté backend.
   */
  previewCode = computed<string | null>(() => {
    const catId = this.categorieActionReserveCtrl.value;
    if (catId != null) {
      const cat = this.categorieActionReserveOptions().find(c => c.id_nomenclature === catId);
      if (cat?.cd_nomenclature) {
        return cat.cd_nomenclature.substring(0, 2).toUpperCase();
      }
    }
    const ta = this.selectedTypeAction();
    if (ta) {
      const code = ta.cd_nomenclature || ta.mnemonique || '';
      let letters = '';
      for (const ch of code) {
        if (/[A-Za-z]/.test(ch)) letters += ch; else break;
      }
      if (letters) return letters.substring(0, 2).toUpperCase();
    }
    return null;
  });

  /**
   * Libellé de la catégorie d'action réserve sélectionnée, pour l'affichage du
   * `mat-select-trigger` (valeur fermée). Sans cela, le sélecteur affiche le
   * texte brut de l'option où le code et l'intitulé sont collés (« CSConnaissance
   * et suivi… »), Angular supprimant l'espace entre les deux <span>.
   */
  selectedCategorieActionReserveLabel(): string | null {
    const id = this.categorieActionReserveCtrl.value;
    if (id == null) return null;
    const cat = this.categorieActionReserveOptions().find(c => c.id_nomenclature === id);
    if (!cat) return null;
    return cat.cd_nomenclature ? `${cat.cd_nomenclature} — ${cat.label}` : cat.label;
  }

  /** Capture les modifications de l'éditeur d'emprise spatiale (#342). */
  onEmpriseChange(geom: any): void {
    this.pendingEmprise.set(geom);
  }

  /** Inventaires existants chargés (filtrés par type d'action) */
  availableInventaires = signal<{ id_suivi_inventaire: number; intitule: string; type_action_code?: string }[]>([]);
  categorieFinanceOptions = signal<{ id_nomenclature: number; mnemonique: string; label: string }[]>([]);

  // Objectif/Cible nomenclatures
  objectifSuiviOptions = signal<NomenclatureOption[]>([]);
  cibleSuiviOptions = signal<NomenclatureOption[]>([]);
  bancarisationOptions = signal<NomenclatureOption[]>([]);
  outilSaisieOptions = signal<NomenclatureOption[]>([]);

  // Grouped objectifs for mat-optgroup display
  objectifGroups = computed<NomenclatureGroup[]>(() => {
    return this.buildGroups(this.objectifSuiviOptions());
  });

  // Reference item lists (taxons / habitats for operation suivi)
  taxonItems: TaxonRef[] = [];
  habitatItems: HabitatRef[] = [];

  // Plan sites (for "L'action est liée au/aux")
  planSites = signal<PlanSite[]>([]);

  // Indicateurs et métriques du plan (pour les selects M2M)
  planIndicateurs = signal<{ id_indicateur: number; nom_indicateur: string }[]>([]);
  planMetriques = signal<{ id_metrique: number; nom_metrique: string; indicateur_nom: string; indicateur_id: number }[]>([]);

  // #476 — résolution de l'enjeu associé à l'action pour suggérer ses
  // habitats/espèces en accès rapide dans le formulaire de suivi.
  private indicateurEnjeuMap = signal<Map<number, Enjeu>>(new Map());
  private metriqueIndicateurMap = signal<Map<number, number>>(new Map());
  /** Reflet réactif du contrôle `metrique_ids` (pour les computeds de suggestions). */
  selectedMetriqueIdsSig = signal<number[]>([]);

  /** Enjeu(x) rattaché(s) à l'action via ses indicateurs/métriques liés. */
  private linkedEnjeux = computed<Enjeu[]>(() => {
    const indMap = this.indicateurEnjeuMap();
    const metMap = this.metriqueIndicateurMap();
    const indIds = new Set<number>();
    for (const mid of this.selectedMetriqueIdsSig()) {
      const indId = metMap.get(mid);
      if (indId) indIds.add(indId);
    }
    for (const m of this.existingOperation()?.metriques || []) {
      if (m.indicateur_id) indIds.add(m.indicateur_id);
    }
    const pre = this.prelinkedIndicateurId();
    if (pre) indIds.add(pre);
    const enjeuById = new Map<number, Enjeu>();
    for (const indId of indIds) {
      const e = indMap.get(indId);
      if (e) enjeuById.set(e.id_enjeu, e);
    }
    return [...enjeuById.values()];
  });

  /** #476 — habitats de l'enjeu associé, proposés en suggestion (dédupliqués). */
  enjeuHabitatSuggestions = computed<HabitatRef[]>(() => {
    const out: HabitatRef[] = [];
    const seen = new Set<string>();
    for (const e of this.linkedEnjeux()) {
      for (const h of e.habitats || []) {
        const k = String(h.cd_hab);
        if (h.cd_hab && !seen.has(k)) { seen.add(k); out.push(h); }
      }
    }
    return out;
  });

  /** #476 — espèces (taxons) de l'enjeu associé, proposées en suggestion. */
  enjeuTaxonSuggestions = computed<TaxonRef[]>(() => {
    const out: TaxonRef[] = [];
    const seen = new Set<number>();
    for (const e of this.linkedEnjeux()) {
      for (const t of e.taxons || []) {
        if (t.cd_nom && !seen.has(t.cd_nom)) { seen.add(t.cd_nom); out.push(t); }
      }
    }
    return out;
  });

  /** #227 — Sélecteur « Métriques associées » : terme de recherche + portée. */
  metriqueSearch = signal('');
  /** Portée du filtre : 'indicateur' = métriques de l'indicateur de l'action ; 'plan' = tout le plan. */
  metriqueScope = signal<'indicateur' | 'plan'>('indicateur');

  /** Indicateur de l'action courante : rattachement direct, sinon indicateur de la 1re métrique pré-liée. */
  currentIndicateurId = computed<number | null>(() => {
    const direct = this.prelinkedIndicateurId();
    if (direct) return direct;
    const firstMet = this.prelinkedMetriqueIds()[0] ?? this.prelinkedMetriqueId();
    if (firstMet) {
      const m = this.planMetriques().find(x => x.id_metrique === firstMet);
      return m?.indicateur_id ?? null;
    }
    return null;
  });

  /** Réinitialise la recherche à la fermeture du panneau de sélection. */
  onMetriquePanelToggle(opened: boolean): void {
    if (!opened) this.metriqueSearch.set('');
  }

  /**
   * #227 — Liste plate des métriques pour le sélecteur, filtrée par la portée
   * (cet indicateur / tout le plan) et par le terme de recherche. Chaque option
   * affiche, sur une seule ligne, le nom de la métrique + son indicateur.
   */
  metriquesFiltrees = computed(() => {
    const term = this.metriqueSearch().trim().toLowerCase();
    const scope = this.metriqueScope();
    const curInd = this.currentIndicateurId();
    return this.planMetriques().filter(m => {
      if (scope === 'indicateur' && curInd != null && m.indicateur_id !== curInd) return false;
      if (term && !(`${m.nom_metrique} ${m.indicateur_nom}`.toLowerCase().includes(term))) return false;
      return true;
    });
  });

  // Programmation annuelle via OperationAnnee[]
  years: number[] = [];
  months = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
  monthLabels = ['Janvier', 'Février', 'Mars', 'Avril', 'Mai', 'Juin', 'Juillet', 'Août', 'Septembre', 'Octobre', 'Novembre', 'Décembre'];
  operationAnnees: OperationAnnee[] = [];

  // Template mensuel unique (même mois chaque année)
  programmationMensuelleDefaut: Record<string, boolean> = {};

  // Finances
  finances: FinanceOperation[] = [];

  // Per-organisme budget data: key = `${yearIndex}-${organismeId}`
  orgBudgets: Record<string, { fonct: number | null; invest: number | null; etp: number | null }> = {};

  /** Mode de ventilation budgétaire : none, by_org, by_type, by_org_type */
  ventilationMode = signal<'none' | 'by_org' | 'by_type' | 'by_org_type'>('none');

  /** Raccourci pour rétrocompatibilité avec le code existant */
  directTotalMode = computed(() => this.ventilationMode() === 'none');

  /** Direct-entered totals per year when in mode 'none': key = yearIndex */
  directTotals: Record<number, { budget: number | null; etp: number | null }> = {};

  /** Budget par type (mode 'by_type') : key = yearIndex */
  typeBudgets: Record<number, { fonct: number | null; invest: number | null; etp: number | null }> = {};

  /** Budget par organisme (mode 'by_org', totaux) : key = `${yearIndex}-${organismeId}` */
  orgByOrgData: Record<string, { budget: number | null; etp: number | null }> = {};

  // Available organismes derived from selected sites
  availableOrganismes = computed(() => {
    this.selectedSiteIdsVersion(); // dependency trigger
    const sites = this.planSites();
    const selectedIds = this.selectedSiteIds;
    const orgMap = new Map<number, { id_organisme: number; nom_organisme: string }>();
    for (const site of sites) {
      if (!selectedIds[site.id_site]) continue;
      for (const org of site.organismes || []) {
        if (!orgMap.has(org.id_organisme)) {
          orgMap.set(org.id_organisme, { id_organisme: org.id_organisme, nom_organisme: org.nom_organisme });
        }
      }
    }
    return Array.from(orgMap.values()).sort((a, b) => a.nom_organisme.localeCompare(b.nom_organisme));
  });

  // Sites M2M checkboxes — use signal so computed can react
  selectedSiteIds: Record<number, boolean> = {};
  selectedSiteIdsVersion = signal(0); // bump to trigger recompute

  // Suivi existant toggle
  estSuiviExistant = signal(false);
  /** Mirror of the libelle form control value, for the read-only display in CS mode */
  libelleDisplay = signal('');


  // CAMPanule autocomplete
  campanuleSearchCtrl = new FormControl('');
  campanuleResults = signal<CampanuleAutocomplete[]>([]);
  selectedCampanule = signal<CampanuleAutocomplete | null>(null);

  // Collapsible sections state
  sectionsOpen: Record<string, boolean> = {
    details_suivi: true,
    protocole: true,
    bancarisation: true,
    programmation: true,
    details: true,
    emprise: true,
    indicateurs_reponse: true
  };

  // Frequency units (loaded from nomenclature FREQUENCE_EMBOITEMENT)
  frequenceUnites: { value: string; label: string }[] = [];

  ngOnInit(): void {
    window.scrollTo({ top: 0, behavior: 'instant' });
    this.loadFrequenceNomenclature();
    this.initForm();
    this.initMetriqueIdsSync();
    this.initSuiviLibelleSync();
    this.initTypeActionAutocomplete();
    this.initCampanuleAutocomplete();
    this.initResponseGridAutosave();
    this.loadRouteParams();
  }

  /** #452 — Auto-sauvegarde débouncée de la grille d'un indicateur de réponse
   *  déjà enregistré : 1 flux par métrique (groupBy) pour éviter d'écraser une
   *  grille par une autre, débounce 600 ms, dernier état gagne (switchMap). */
  private initResponseGridAutosave(): void {
    this.gridSave$.pipe(
      groupBy(e => e.metriqueId),
      mergeMap(group => group.pipe(
        debounceTime(600),
        switchMap(({ metriqueId, data }) =>
          this.enjeuService.updateMetrique(metriqueId, this.buildResponseGridPayload(data)),
        ),
      )),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      error: () => this.snackBar.open(
        this.translate.instant('enjeux.operations.indicateursAddError'),
        this.translate.instant('common.actions.close'),
        { duration: 4000 },
      ),
    });
  }

  /** #452 — Construit le payload PATCH d'une grille d'indicateur de réponse
   *  (partagé entre l'auto-save débouncé et le flush au moment de « Valider »). */
  private buildResponseGridPayload(data: MetriqueFormData): Record<string, unknown> {
    const mnemo = this.getMetriqueTypeMnemonique(data.type_metrique);
    return {
      nom_metrique: (data.nom_metrique || '').trim(),
      type_metrique: data.type_metrique ?? undefined,
      format_metrique: this.formatId('GRILLE'),
      etat_reference: (data.etat_reference || '').trim(),
      // #452 — unité et pondération éditées dans la grille (étaient perdues).
      unite: (data.unite || '').trim() || null,
      ponderation: data.ponderation ?? null,
      ...buildMetriqueGridFields(data, mnemo),
    };
  }

  /** #452 — Dernier état de grille saisi par métrique (pour flush au submit :
   *  l'auto-save est débouncé et serait perdu si l'utilisateur valide aussitôt). */
  private latestGridData = new Map<number, MetriqueFormData>();

  /**
   * #452 — Flush des grilles d'indicateurs de réponse en attente : enregistre
   * immédiatement (sans debounce) le dernier état saisi, pour qu'un clic
   * « Valider » juste après une saisie ne perde pas le type / les valeurs / les
   * libellés (symptôme « la grille ne réapparaît pas au rechargement »).
   *
   * `strict = false` (brouillon) : tolérant — une grille incomplète ne bloque pas.
   * `strict = true` (« Valider ») : l'observable **échoue** si une grille est
   * incomplète ou sans intitulé (le backend renvoie 400) → la validation est
   * bloquée et l'erreur affichée, au lieu d'un échec silencieux.
   */
  private flushResponseGrids(strict = false): Observable<unknown> {
    if (this.latestGridData.size === 0) return of(null);
    const calls = [...this.latestGridData.entries()].map(([metriqueId, data]) => {
      const call = this.enjeuService.updateMetrique(metriqueId, this.buildResponseGridPayload(data));
      // En mode strict on laisse l'erreur remonter (forkJoin échouera) ; sinon on
      // l'absorbe pour ne pas bloquer un simple enregistrement brouillon.
      return strict ? call : call.pipe(catchError(() => of(null)));
    });
    return forkJoin(calls);
  }

  private loadFrequenceNomenclature(): void {
    this.adminService.getNomenclaturesByType('FREQUENCE_EMBOITEMENT').subscribe({
      next: (nomenclatures) => {
        this.frequenceUnites = nomenclatures
          .sort((a, b) => (a.hierarchy || '').localeCompare(b.hierarchy || ''))
          .map(n => ({
            value: (n.mnemonique || '').toLowerCase(),
            label: n.label
          }));
      },
      error: () => {
        // Fallback si la nomenclature n'est pas chargée
        this.frequenceUnites = [
          { value: 'jour', label: 'Jour' },
          { value: 'semaine', label: 'Semaine' },
          { value: 'mois', label: 'Mois' },
          { value: 'an', label: 'Ans' }
        ];
      }
    });
  }

  private initForm(): void {
    this.form = this.fb.group({
      // Main card
      libelle: ['', [Validators.maxLength(500)]],
      id_type_action: [null],
      id_suivi: [null],
      intitule_suivi: [''],
      metrique_ids: [[] as number[]],
      id_priorite: [null],
      // Suivi/inventaire fields (nested in suivi_inventaire on save)
      objectif_principal: [''],
      objectif_secondaire: [''],
      cibles_principales: [null],
      cible_secondaire: [''],
      date_lancement_suivi: [null],
      protocole_dans_campanule: [null],
      protocole_campanule_nom: [''],
      cd_protocole_campanule: [null],
      nb_etp_cycle: [null],
      nom_protocole: [''],
      respect_protocole: [null],
      justification_non_respect: [''],
      differences_protocole: [''],
      description_protocole: [''],
      objectif_protocole: [''],
      periode_echantillonnage: [''],
      outil_bancarisation: [null],
      outil_saisie: [null],
      transmission_donnee: [null],
      // Programmation
      frequence_nombre: [null],
      frequence_unite: [null],
      operateurs: [''],
      partenaires: [''],
      // #343 — financeur textuel supprimé au profit des financeurs structurés (libellé + catégorie)
      // Détails
      description: [''],
      // Hidden but kept for backwards compat
      code_operation: [''],
      id_referentiel_operations: [''],
      annee_min: [null],
      annee_max: [null],
    });
  }

  /** #476 — reflète le contrôle `metrique_ids` dans un signal pour alimenter les
   *  computeds de suggestions (habitats/espèces de l'enjeu associé). */
  private initMetriqueIdsSync(): void {
    const ctrl = this.form.get('metrique_ids');
    if (!ctrl) return;
    this.selectedMetriqueIdsSig.set((ctrl.value as number[]) || []);
    ctrl.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value: number[] | null) => this.selectedMetriqueIdsSig.set(value || []));
  }

  private loadRouteParams(): void {
    // #415 — s'abonner aux paramètres (au lieu de lire le snapshot une seule
    // fois) : si Angular réutilise ce composant pour une autre action (ex.
    // « Modifier l'action » depuis le suivi), on recharge bien les données au
    // lieu de conserver un formulaire vide/obsolète.
    this.route.paramMap
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.applyRouteParams());
  }

  private applyRouteParams(): void {
    // Walk up the route tree to find the 'slug' param (plan slug)
    const slug = this.findRouteParam('slug');
    if (slug) {
      this.planSlug.set(slug);
    }

    // La route `operations/:operationId` (sans /modifier) définit data.readOnly = true
    if (this.route.snapshot.data['readOnly'] === true) {
      this.isReadOnly.set(true);
    }

    const opIdStr = this.route.snapshot.paramMap.get('operationId');
    const newOpId = opIdStr ? parseInt(opIdStr, 10) : null;
    // #415 — changement d'action sur un composant réutilisé : on repart d'un
    // état propre avant de recharger (sinon les anciennes données persistent).
    if (newOpId !== this.operationId()) {
      this.resetOperationState();
    }
    if (newOpId != null) {
      this.operationId.set(newOpId);
      // En mode lecture seule la page reste "vue" — pas d'édition — mais on
      // doit quand même charger les données de l'action existante
      if (!this.isReadOnly()) {
        this.isEditMode.set(true);
      }
    }

    const metriqueIdStr = this.route.snapshot.queryParamMap.get('metriqueId');
    if (metriqueIdStr) {
      this.prelinkedMetriqueId.set(parseInt(metriqueIdStr, 10));
    }

    // #1 — Liste de métriques (CSV) quand l'action est créée au niveau indicateur.
    const metriqueIdsStr = this.route.snapshot.queryParamMap.get('metriqueIds');
    if (metriqueIdsStr) {
      const ids = metriqueIdsStr
        .split(',')
        .map(s => parseInt(s.trim(), 10))
        .filter(n => !isNaN(n));
      this.prelinkedMetriqueIds.set(ids);
      // Le premier id sert aussi de `prelinkedMetriqueId` pour les comportements
      // existants (auto-scroll, etc.).
      if (ids.length > 0 && !this.prelinkedMetriqueId()) {
        this.prelinkedMetriqueId.set(ids[0]);
      }
    }

    // #367 — rattachement direct à un indicateur (action créée sans métrique).
    const indicateurIdStr = this.route.snapshot.queryParamMap.get('indicateurId');
    if (indicateurIdStr) {
      const id = parseInt(indicateurIdStr, 10);
      if (!isNaN(id)) this.prelinkedIndicateurId.set(id);
    }

    const returnEnjeu = this.route.snapshot.queryParamMap.get('returnEnjeu');
    if (returnEnjeu) {
      this.returnEnjeuSlug.set(returnEnjeu);
    }

    const returnTab = this.route.snapshot.queryParamMap.get('returnTab');
    if (returnTab) {
      this.returnTab.set(returnTab);
    }

    this.loadData();
  }

  /**
   * #415 — Réinitialise l'état spécifique à une action (utilisé quand le
   * composant est réutilisé pour une autre action). Les souscriptions du
   * formulaire restent intactes (on ne recrée pas le FormGroup) ; loadData()
   * repeuplera ensuite les valeurs.
   */
  private resetOperationState(): void {
    this.existingOperation.set(null);
    this.isEditMode.set(false);
    this.operationAnnees = [];
    this.years = [];
    this.orgBudgets = {};
    this.typeBudgets = {};
    this.directTotals = {};
    this.orgByOrgData = {};
    this.selectedSiteIds = {};
    this.selectedSiteIdsVersion.update(v => v + 1);
    this.pendingEmprise.set(undefined);
    this.useSiteEmprise.set(false);
    this.ventilationMode.set('none');
  }

  /**
   * Walk up the activated route tree to find a param by name.
   */
  private findRouteParam(name: string): string | null {
    let current = this.route.snapshot;
    while (current) {
      const value = current.paramMap.get(name);
      if (value) return value;
      current = current.parent!;
    }
    return null;
  }

  /**
   * #452/#248 — Verrou lecture seule si le plan n'est pas en brouillon : le
   * serveur refuse toute modification (CanModifyOnlyDraftPlan → 403). Sans ce
   * verrou, la case « Utiliser une grille de scoring » restait cliquable sur un
   * plan validé ; la mise à jour optimiste la cochait puis, au retour 403 du
   * PATCH, la décochait aussitôt (symptôme « cochée puis décochée »).
   * N'abaisse jamais un verrou déjà posé par la route (lecture seule de la fiche).
   */
  private applyPlanReadOnly(statut: string | null | undefined): void {
    if (statut && statut !== 'draft') {
      this.isReadOnly.set(true);
    }
  }

  /**
   * #452 — Une mutation refusée car le plan n'est plus en brouillon renvoie 403
   * (CanModifyOnlyDraftPlan). Cas typique : le plan a été validé pendant que le
   * formulaire d'action restait ouvert. On verrouille alors le formulaire en
   * lecture seule (les boutons d'édition — corbeille, case grille… — disparaissent)
   * et on l'explique clairement, au lieu de laisser l'utilisateur cliquer sur des
   * actions qui échouent « en silence ». Renvoie `true` si l'erreur a été traitée.
   */
  private handlePlanLocked(err: unknown): boolean {
    if ((err as { status?: number })?.status === 403) {
      this.isReadOnly.set(true);
      this.snackBar.open(
        this.translate.instant('enjeux.operations.planLockedError'),
        this.translate.instant('common.actions.close'),
        { duration: 6000 },
      );
      return true;
    }
    return false;
  }

  private loadData(): void {
    this.isLoadingData.set(true);

    const slug = this.planSlug();
    if (slug) {
      this.adminService.getPlanBySlug(slug).subscribe({
        next: (plan) => {
          this.planId.set(plan.id_pg);
          this.planNom.set(plan.nom);
          this.applyPlanReadOnly(plan.statut);
          this.computeYears(plan.annee_debut, plan.annee_fin);
          // Extract plan sites
          if (plan.sites) {
            this.planSites.set(plan.sites);
            const isSingleSite = plan.sites.length === 1;
            for (const site of plan.sites) {
              this.selectedSiteIds[site.id_site] = isSingleSite;
            }
          }
          // Load operation data AFTER sites are initialized to avoid race condition
          this.loadOperationIfEdit();
          // Load enjeux after plan is loaded. Force-refresh : une métrique créée
          // juste avant (dans l'indicateur) doit apparaître dans le sélecteur
          // « Métriques associées » sans dépendre du cache.
          this.enjeuService.getPlanEnjeux(plan.id_pg, true).subscribe({
            next: (response) => {
              const indicateurs: { id_indicateur: number; nom_indicateur: string }[] = [];
              const metriques: { id_metrique: number; nom_metrique: string; indicateur_nom: string; indicateur_id: number }[] = [];

              const allEnjeux = [...(response.enjeux || []), ...(response.fcr || [])];
              const seenIndicateurs = new Set<number>();
              const seenMetriques = new Set<number>();
              // #476 — maps indicateur→enjeu et métrique→indicateur pour résoudre
              // l'enjeu associé à l'action et en proposer les habitats/espèces.
              const indEnjeuMap = new Map<number, Enjeu>();
              const metIndMap = new Map<number, number>();

              const collectIndicateursMetriques = (ind: any, enjeu: Enjeu) => {
                if (!ind || seenIndicateurs.has(ind.id_indicateur)) return;
                // #398 — les indicateurs de réponse (et leurs métriques) ne font pas
                // partie des « métriques associées » sélectionnables : ils sont propres
                // à une action et gérés dans la section « Indicateur(s) de réponse ».
                if (ind.type_indicateur_mnemonique === 'REPONSE') return;
                seenIndicateurs.add(ind.id_indicateur);
                indEnjeuMap.set(ind.id_indicateur, enjeu);
                indicateurs.push({ id_indicateur: ind.id_indicateur, nom_indicateur: ind.nom_indicateur });
                for (const met of ind.metriques || []) {
                  metIndMap.set(met.id_metrique, ind.id_indicateur);
                  if (seenMetriques.has(met.id_metrique)) continue;
                  seenMetriques.add(met.id_metrique);
                  metriques.push({
                    id_metrique: met.id_metrique,
                    nom_metrique: met.nom_metrique,
                    indicateur_nom: ind.nom_indicateur,
                    indicateur_id: ind.id_indicateur
                  });
                }
              };

              for (const enjeu of allEnjeux) {
                // Chemin OLT : Enjeu → OLT → NE → Indicateur → Métrique
                for (const olt of enjeu.objectifs_long_terme || []) {
                  for (const ne of olt.niveaux_exigence || []) {
                    for (const ind of ne.indicateurs || []) {
                      collectIndicateursMetriques(ind, enjeu);
                    }
                  }
                }
                // Chemin OO : Enjeu → FI → Pression → OO → RA → Indicateur → Métrique
                for (const fi of enjeu.facteurs_influence || []) {
                  for (const pression of fi.pressions || []) {
                    for (const oo of pression.objectifs_operationnels || []) {
                      for (const ra of oo.resultats_attendus || []) {
                        for (const ind of ra.indicateurs || []) {
                          collectIndicateursMetriques(ind, enjeu);
                        }
                      }
                    }
                  }
                }
                // #337 — Chemin OO direct (OO rattaché directement à l'enjeu/FCR,
                // sans pression) : Enjeu → OO → RA → Indicateur → Métrique. Sans ce
                // parcours, les métriques des indicateurs d'un FCR n'apparaissaient
                // pas dans le sélecteur « Métriques associées ».
                for (const oo of enjeu.objectifs_operationnels || []) {
                  for (const ra of oo.resultats_attendus || []) {
                    for (const ind of ra.indicateurs || []) {
                      collectIndicateursMetriques(ind, enjeu);
                    }
                  }
                }
              }

              this.planIndicateurs.set(indicateurs);
              this.planMetriques.set(metriques);
              this.indicateurEnjeuMap.set(indEnjeuMap);
              this.metriqueIndicateurMap.set(metIndMap);
            },
            error: () => {}
          });
        },
        error: () => {
          this.computeYears(null, null);
          this.loadOperationIfEdit();
        }
      });
    } else {
      // No plan slug found: generate default years so tables render
      this.computeYears(null, null);
      this.loadOperationIfEdit();
    }

    this.adminService.getNomenclaturesByType('TYPE_ACTION').subscribe({
      next: (options) => {
        this.typeActionOptions.set(options);
        // Si on est en mode édition et que l'opération est déjà chargée, restaurer l'autocomplete
        const op = this.existingOperation();
        if (op?.id_type_action) {
          this.restoreTypeActionAutocomplete(op.id_type_action, options);
        }
      },
      error: () => this.typeActionOptions.set([])
    });

    this.adminService.getNomenclaturesByType('PRIORITE_OPERATION').subscribe({
      next: (options) => this.prioriteOptions.set(options),
      error: () => this.prioriteOptions.set([])
    });

    // #228 — Charger les 9 catégories d'action réserve (CT88).
    this.adminService.getNomenclaturesByType('CATEGORIE_ACTION_RESERVE').subscribe({
      next: (options) => this.categorieActionReserveOptions.set(options),
      error: () => this.categorieActionReserveOptions.set([])
    });

    // Types de métriques pour la section Indicateurs de réponse.
    this.adminService.getNomenclaturesByType('TYPE_METRIQUE').subscribe({
      next: (options) => this.typeMetriqueOptions.set(options),
      error: () => this.typeMetriqueOptions.set([]),
    });

    // #452 — formats de métrique (SIMPLE / GRILLE) pour les indicateurs de réponse.
    this.adminService.getNomenclaturesByType('FORMAT_METRIQUE').subscribe({
      next: (options) => this.formatMetriqueOptions.set(options),
      error: () => this.formatMetriqueOptions.set([]),
    });



    this.adminService.getNomenclaturesByType('CATEGORIE_FINANCE').subscribe({
      next: (options) => this.categorieFinanceOptions.set(options),
      error: () => this.categorieFinanceOptions.set([])
    });

    this.adminService.getNomenclaturesByType('OBJECTIF_SUIVI').subscribe({
      next: (options) => this.objectifSuiviOptions.set(options),
      error: () => this.objectifSuiviOptions.set([])
    });

    this.adminService.getNomenclaturesByType('CIBLE_SUIVI').subscribe({
      next: (options) => this.cibleSuiviOptions.set(options),
      error: () => this.cibleSuiviOptions.set([])
    });

    this.adminService.getNomenclaturesByType('BANCARISATION_STOCKAGE').subscribe({
      next: (options) => this.bancarisationOptions.set(options),
      error: () => this.bancarisationOptions.set([])
    });

    this.adminService.getNomenclaturesByType('OUTIL_SAISIE').subscribe({
      next: (options) => this.outilSaisieOptions.set(options),
      error: () => this.outilSaisieOptions.set([])
    });
  }

  private computeYears(anneeDebut: number | null | undefined, anneeFin: number | null | undefined): void {
    const start = anneeDebut || new Date().getFullYear();
    const end = anneeFin || start + 5;
    this.years = [];
    this.operationAnnees = [];
    for (let y = start; y <= end; y++) {
      this.years.push(y);
      this.operationAnnees.push({
        annee: y,
        periodicite: false,
        budget: null,
        etp: null,
        periodicite_mensuelle: this.emptyMensuelle()
      });
    }
    // Init default monthly template
    this.programmationMensuelleDefaut = this.emptyMensuelle();
  }

  private emptyMensuelle(): Record<string, boolean> {
    const m: Record<string, boolean> = {};
    for (const month of this.months) {
      m[month.toString()] = false;
    }
    return m;
  }

  private loadOperationIfEdit(): void {
    const opId = this.operationId();
    if (!opId) {
      // #1 — Pré-sélectionne toutes les métriques passées en query
      // (`metriqueIds` au niveau indicateur, fallback `metriqueId` single).
      const prelinkedIds = this.prelinkedMetriqueIds();
      const prelinkedId = this.prelinkedMetriqueId();
      const ids = prelinkedIds.length > 0
        ? prelinkedIds
        : (prelinkedId ? [prelinkedId] : []);
      if (ids.length > 0) {
        this.form.patchValue({ metrique_ids: ids });
      }
      this.isLoadingData.set(false);
      return;
    }

    this.enjeuService.getOperation(opId).subscribe({
      next: (operation) => {
        this.existingOperation.set(operation);
        this.populateForm(operation);
        // Verrouille tout le formulaire en mode lecture seule une fois les valeurs chargées
        if (this.isReadOnly()) {
          this.form.disable();
          this.typeActionSearchCtrl.disable();
          this.campanuleSearchCtrl.disable();
        }
        this.isLoadingData.set(false);
      },
      error: () => {
        this.errorMessage.set(this.translate.instant('enjeux.messages.loadError'));
        this.isLoadingData.set(false);
      }
    });
  }

  private populateForm(op: Operation): void {
    // Set est_suivi_existant state
    if (op.est_suivi_existant) {
      this.estSuiviExistant.set(true);
    }

    this.form.patchValue({
      libelle: op.libelle,
      id_type_action: op.id_type_action || null,
      id_suivi: op.id_suivi || null,
      id_priorite: op.id_priorite || null,
      code_operation: op.code_operation || '',
      id_referentiel_operations: op.id_referentiel_operations || '',
      description: op.description || '',
      annee_min: op.annee_min || null,
      annee_max: op.annee_max || null,
      // Fréquence & acteurs
      frequence_nombre: op.frequence_nombre || null,
      frequence_unite: op.frequence_unite || null,
      operateurs: op.operateurs || '',
      partenaires: op.partenaires || '',
      metrique_ids: op.metrique_ids || []
    });

    // #367 — conserver le rattachement direct à un indicateur (action sans métrique).
    if ((op as any).id_indicateur) {
      this.prelinkedIndicateurId.set((op as any).id_indicateur);
    }

    // Restore type action autocomplete
    if (op.id_type_action) {
      this.restoreTypeActionAutocomplete(op.id_type_action);
    }

    // #228 — Restaurer la catégorie d'action réserve
    if (op.id_categorie_action_reserve != null) {
      this.categorieActionReserveCtrl.setValue(op.id_categorie_action_reserve);
    } else {
      this.categorieActionReserveCtrl.setValue(null);
    }

    // Populate suivi fields from nested suivi_inventaire
    const suivi = op.suivi_inventaire;
    if (suivi) {
      // Parse taxon references from stored string
      if (suivi.taxon_taxref) {
        this.taxonItems = suivi.taxon_taxref.split(',').map((s: string) => s.trim()).filter((s: string) => s).map((name: string) => ({
          cd_nom: 0,
          nom_complet: name,
        }));
      }
      // Habitats : on privilégie la liste structurée (avec cd_hab, nécessaire
      // aux correspondances), sinon on retombe sur le texte `habitat_ref`.
      if (Array.isArray(suivi.habitats) && suivi.habitats.length > 0) {
        this.habitatItems = suivi.habitats.map((h: any) => ({ cd_hab: h.cd_hab ?? '', lb_hab_fr: h.lb_hab_fr ?? '', lb_code: h.lb_code, lb_typo: h.lb_typo, lb_hab_fr_complet: h.lb_hab_fr_complet }));
      } else if (suivi.habitat_ref) {
        this.habitatItems = suivi.habitat_ref.split(',').map((s: string) => s.trim()).filter((s: string) => s).map((name: string) => ({
          cd_hab: '',
          lb_hab_fr: name,
        }));
      }

      this.form.patchValue({
        intitule_suivi: suivi.intitule || '',
        objectif_principal: suivi.objectif_principal || '',
        objectif_secondaire: suivi.objectif_secondaire || '',
        cibles_principales: suivi.cibles_principales || null,
        cible_secondaire: suivi.cible_secondaire || '',
        date_lancement_suivi: suivi.date_lancement_suivi ? new Date(suivi.date_lancement_suivi) : null,
        outil_bancarisation: suivi.outil_bancarisation || null,
        outil_saisie: suivi.outil_saisie || null,
        transmission_donnee: suivi.transmission_donnee ?? null,
      });

      // Populate protocole fields from nested protocole
      const proto = suivi.protocole;
      if (proto) {
        this.form.patchValue({
          protocole_dans_campanule: proto.protocole_dans_campanule ?? null,
          protocole_campanule_nom: proto.protocole_campanule_nom || '',
          cd_protocole_campanule: proto.cd_protocole_campanule || null,
          nb_etp_cycle: proto.nb_etp_cycle || null,
          nom_protocole: proto.nom_protocole || '',
          respect_protocole: proto.respect_protocole ?? null,
          justification_non_respect: proto.justification_non_respect || '',
          differences_protocole: proto.differences_protocole || '',
          description_protocole: proto.description_protocole || '',
          objectif_protocole: proto.objectif_protocole || '',
          periode_echantillonnage: proto.periode_echantillonnage || '',
        });

        // Restore CAMPanule autocomplete state
        if (proto.cd_protocole_campanule && proto.protocole_campanule_nom) {
          this.campanuleSearchCtrl.setValue(proto.protocole_campanule_nom, { emitEvent: false });
          this.selectedCampanule.set({
            cd_protocole: proto.cd_protocole_campanule,
            search_name: proto.protocole_campanule_nom,
            lb_protocole_court: proto.protocole_campanule_nom,
          });
        }
      }
    }

    // Disable fields if est_suivi_existant
    if (op.est_suivi_existant) {
      this.setSuiviFieldsEnabled(false);
    }

    // For CS actions, libelle is synced with inventaire title
    if (op.id_type_action) {
      const opts = this.typeActionOptions();
      const match = opts.find(o => o.id_nomenclature === op.id_type_action);
      const code = match?.cd_nomenclature || match?.mnemonique || '';
      if (code.startsWith('CS')) {
        this.form.get('libelle')?.disable();
        this.libelleDisplay.set(op.libelle || '');
        // Charger la liste des inventaires existants (sinon, en mode "suivi existant",
        // le mat-select n'a aucune option et l'intitulé sélectionné n'apparaît pas).
        this.loadInventairesByTypeAction(code);
        // En mode "nouveau suivi", l'intitulé de l'inventaire = libellé de l'action.
        // Si suivi.intitule est vide/manquant, on retombe sur op.libelle pour que le
        // champ ne soit pas vide à l'ouverture de l'édition.
        const currentIntitule = this.form.get('intitule_suivi')?.value;
        if (!currentIntitule && op.libelle) {
          this.form.patchValue({ intitule_suivi: op.libelle });
        }
      }
    }

    // Synchronise les validators conditionnels (notamment intitule_suivi requis
    // pour CS + nouveau suivi) — sinon en édition l'utilisateur peut vider le
    // champ et sauvegarder sans erreur.
    this.syncConditionalValidators();

    // Restore site selections
    if (op.site_ids) {
      for (const siteId of op.site_ids) {
        this.selectedSiteIds[siteId] = true;
      }
      this.selectedSiteIdsVersion.update(v => v + 1);
    }

    // Restore operation_annees from relational data
    if (op.operation_annees && op.operation_annees.length > 0) {
      // Merge server data with existing year slots
      for (const serverAnnee of op.operation_annees) {
        const idx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
        if (idx >= 0) {
          this.operationAnnees[idx] = { ...serverAnnee };
          // Parse decimal strings from DRF (DecimalField serializes as string)
          if (this.operationAnnees[idx].budget != null) {
            this.operationAnnees[idx].budget = parseFloat(String(this.operationAnnees[idx].budget));
          }
          if (this.operationAnnees[idx].etp != null) {
            this.operationAnnees[idx].etp = parseFloat(String(this.operationAnnees[idx].etp));
          }
        } else {
          // Year from server not in plan range: add it
          const parsed = { ...serverAnnee };
          if (parsed.budget != null) parsed.budget = parseFloat(String(parsed.budget));
          if (parsed.etp != null) parsed.etp = parseFloat(String(parsed.etp));
          this.operationAnnees.push(parsed);
          this.years.push(serverAnnee.annee);
        }
      }
      // Re-sort
      this.years.sort((a, b) => a - b);
      this.operationAnnees.sort((a, b) => a.annee - b.annee);

      // Restore per-organisme data
      for (const serverAnnee of op.operation_annees) {
        const yearIdx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
        if (yearIdx >= 0 && serverAnnee.organismes) {
          for (const org of serverAnnee.organismes) {
            this.orgBudgets[this.orgKey(yearIdx, org.id_organisme)] = {
              fonct: org.budget_fonctionnement != null ? parseFloat(String(org.budget_fonctionnement)) : null,
              invest: org.budget_investissement != null ? parseFloat(String(org.budget_investissement)) : null,
              etp: org.etp != null ? parseFloat(String(org.etp)) : null,
            };
          }
        }
      }
    }

    // Restore ventilation mode from backend (or infer for legacy data)
    const savedMode = op.ventilation_mode || 'none';
    this.ventilationMode.set(savedMode);

    if (op.operation_annees && op.operation_annees.length > 0) {
      if (savedMode === 'by_org') {
        for (const serverAnnee of op.operation_annees) {
          const yearIdx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
          if (yearIdx >= 0 && serverAnnee.organismes) {
            for (const org of serverAnnee.organismes) {
              this.orgByOrgData[`${yearIdx}-${org.id_organisme}`] = {
                budget: org.budget_fonctionnement != null ? parseFloat(String(org.budget_fonctionnement)) : null,
                etp: org.etp != null ? parseFloat(String(org.etp)) : null,
              };
            }
          }
        }
      } else if (savedMode === 'by_type') {
        for (const serverAnnee of op.operation_annees) {
          const yearIdx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
          if (yearIdx >= 0) {
            this.typeBudgets[yearIdx] = {
              fonct: serverAnnee.budget_fonctionnement != null ? parseFloat(String(serverAnnee.budget_fonctionnement)) : null,
              invest: serverAnnee.budget_investissement != null ? parseFloat(String(serverAnnee.budget_investissement)) : null,
              etp: serverAnnee.etp != null ? parseFloat(String(serverAnnee.etp)) : null,
            };
          }
        }
      } else if (savedMode === 'none') {
        for (const serverAnnee of op.operation_annees) {
          const yearIdx = this.operationAnnees.findIndex(a => a.annee === serverAnnee.annee);
          if (yearIdx >= 0) {
            this.directTotals[yearIdx] = {
              budget: serverAnnee.budget != null ? parseFloat(String(serverAnnee.budget)) : null,
              etp: serverAnnee.etp != null ? parseFloat(String(serverAnnee.etp)) : null,
            };
          }
        }
      }
      // Mode by_org_type: orgBudgets already populated above (lines 634-638)
    }

    // Restore default monthly template
    if (op.programmation_mensuelle_defaut && Object.keys(op.programmation_mensuelle_defaut).length > 0) {
      this.programmationMensuelleDefaut = { ...op.programmation_mensuelle_defaut };
    }

    // Restore finances
    if (op.finances && op.finances.length > 0) {
      this.finances = op.finances.map(f => ({ ...f }));
    }
  }

  save(): void {
    // #452 — un indicateur de réponse doit avoir un intitulé pour valider l'action.
    const titleMissing = this.hasMissingResponseTitle();
    if (this.form.invalid || titleMissing) {
      this.form.markAllAsTouched();
      if (titleMissing) {
        this.showResponseTitleErrors.set(true);
        this.snackBar.open(
          this.translate.instant('enjeux.operations.indicateurReponseTitleRequired'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 },
        );
      } else {
        this.showValidationErrorMessage();
      }
      this.scrollToError();
      return;
    }
    this.submitToApi(this.buildPayload(), { stayOnForm: false, statut: 'valide' });
  }

  /**
   * Enregistrement sans validation des champs requis.
   * L'utilisateur reste sur le formulaire :
   *  - en édition : aucune navigation, snackbar de confirmation
   *  - en création : redirection silencieuse vers l'URL d'édition de l'opération créée,
   *    pour que les enregistrements suivants soient des PATCH plutôt que des POST.
   *
   * #251 — Force le statut à 'draft' : tant que l'utilisateur n'a pas explicitement
   * cliqué sur « Valider », l'action est considérée comme brouillon (chip dans les listes).
   */
  saveDraft(): void {
    this.submitToApi(this.buildPayload(), { stayOnForm: true, statut: 'draft' });
  }

  // ===========================================================================
  // Section Indicateurs de réponse — CRUD inline
  // ===========================================================================

  /**
   * Met à jour le signal `existingOperation` en patchant la métrique passée.
   * Utilisé pour appliquer immédiatement les changements locaux après un PATCH
   * API réussi, sans avoir à refetch l'opération complète.
   */
  private patchLocalMetrique(metriqueId: number, patch: Partial<{
    nom_metrique: string; indicateur_nom: string; etat_reference: string;
    type_metrique_id: number | null; type_metrique_label: string | null;
    // #452 — format (id + mnémonique) pour le toggle simple/grille.
    format_metrique_id: number | null; format_metrique_mnemonique: string | null;
  }>): void {
    const op = this.existingOperation();
    if (!op?.metriques) return;
    const updated = op.metriques.map(m =>
      m.id_metrique === metriqueId ? { ...m, ...patch } : m,
    );
    this.existingOperation.set({ ...op, metriques: updated });
  }

  /** Bouton "+ Ajouter un indicateur de réponse" : crée Indicateur + Métrique côté backend. */
  addResponseIndicator(): void {
    const opId = this.operationId();
    if (!opId) {
      // En création : l'action n'existe pas encore côté serveur. On collecte
      // l'indicateur de réponse en mémoire ; il sera créé à l'enregistrement.
      // #398 — la métrique reste vide tant que l'utilisateur ne l'a pas nommée :
      // un indicateur de réponse sans métrique nommée ne doit pas afficher de chip.
      this.pendingResponseIndicators.push({
        nom_indicateur: this.translate.instant('enjeux.operations.newIndicatorDefault'),
        nom_metrique: '',
        type_metrique_id: null,
        valeur_cible: '',
        format_metrique_id: this.formatId('SIMPLE'),
      });
      return;
    }
    const defaultNom = this.translate.instant('enjeux.operations.newIndicatorDefault');
    this.enjeuService.createOperationResponseIndicator(opId, {
      nom_indicateur: defaultNom,
    }).subscribe({
      next: (created) => {
        const op = this.existingOperation();
        if (!op) return;
        const newRef = {
          id_metrique: created.id_metrique,
          nom_metrique: created.nom_metrique,
          indicateur_id: created.id_indicateur,
          indicateur_nom: created.nom_indicateur,
          // create-indicator crée toujours un indicateur de type REPONSE.
          indicateur_type: 'REPONSE',
          etat_reference: created.etat_reference,
          type_metrique_id: created.type_metrique,
          type_metrique_label: null,
        };
        this.existingOperation.set({
          ...op,
          metriques: [...(op.metriques || []), newRef],
        });
        // NB : pas de synchro avec `metrique_ids` — les métriques d'indicateurs de
        // réponse n'appartiennent pas à cette liste (gérées à part côté backend).
      },
      error: (err) => {
        const msg = err?.error?.detail
          || this.translate.instant('enjeux.operations.indicateursAddError');
        this.snackBar.open(msg, this.translate.instant('common.actions.close'), { duration: 4000 });
      },
    });
  }

  /** Bouton corbeille : supprime l'indicateur de réponse (et sa métrique). Un
   *  indicateur de réponse est propre à l'action ; une fois retiré il ne doit
   *  plus exister. La suppression de l'indicateur cascade sur sa métrique et sur
   *  le lien op ↔ métrique. Comme les métriques de réponse ne transitent pas par
   *  `metrique_ids` (gérées à part côté backend), aucun risque de re-création au save. */
  removeResponseIndicator(metriqueId: number): void {
    const opId = this.operationId();
    if (!opId) return;
    const met = this.existingOperation()?.metriques?.find(m => m.id_metrique === metriqueId);
    const indicateurId = met?.indicateur_id ?? null;

    const onRemoved = () => {
      // #452 — purger l'état de grille en attente (sinon un flush au submit
      // tenterait de PATCHer une métrique supprimée → 404).
      this.latestGridData.delete(metriqueId);
      const op = this.existingOperation();
      if (op?.metriques) {
        this.existingOperation.set({
          ...op,
          metriques: op.metriques.filter(m => m.id_metrique !== metriqueId),
        });
      }
    };
    const onError = (err: unknown) => {
      if (this.handlePlanLocked(err)) return;
      this.snackBar.open(
        this.translate.instant('enjeux.operations.indicateursRemoveError'),
        this.translate.instant('common.actions.close'),
        { duration: 4000 },
      );
    };

    // Cas nominal : on supprime l'indicateur de réponse (cascade métrique + lien).
    if (indicateurId) {
      this.enjeuService.deleteIndicateur(indicateurId).subscribe({ next: onRemoved, error: onError });
      return;
    }
    // Filet : indicateur inconnu → on se contente de retirer le lien.
    this.enjeuService.unlinkOperationMetrique(opId, metriqueId).subscribe({ next: onRemoved, error: onError });
  }

  /** Retire un indicateur de réponse en attente (création, non encore enregistré). */
  removePendingResponseIndicator(index: number): void {
    this.pendingResponseIndicators.splice(index, 1);
  }

  /** Sauvegarde le titre de l'indicateur (on blur de l'input). */
  saveIndicatorName(indicateurId: number, metriqueId: number, value: string): void {
    if (!indicateurId) return;
    const trimmed = (value || '').trim();
    this.enjeuService.updateIndicateur(indicateurId, { nom_indicateur: trimmed }).subscribe({
      next: () => this.patchLocalMetrique(metriqueId, { indicateur_nom: trimmed }),
    });
  }

  /** Sauvegarde le nom de la métrique. */
  saveMetricName(metriqueId: number, value: string): void {
    const trimmed = (value || '').trim();
    this.enjeuService.updateMetrique(metriqueId, { nom_metrique: trimmed }).subscribe({
      next: () => this.patchLocalMetrique(metriqueId, { nom_metrique: trimmed }),
    });
  }

  /** Sauvegarde le type de métrique (dropdown). */
  saveMetricType(metriqueId: number, typeId: number | null): void {
    const payload = { type_metrique: typeId ?? undefined } as any;
    this.enjeuService.updateMetrique(metriqueId, payload).subscribe({
      next: () => {
        const label = this.typeMetriqueOptions().find(o => o.id_nomenclature === typeId)?.label || null;
        this.patchLocalMetrique(metriqueId, { type_metrique_id: typeId, type_metrique_label: label });
      },
    });
  }

  /** Sauvegarde la valeur cible (mappée sur Metrique.etat_reference). */
  saveMetricTarget(metriqueId: number, value: string): void {
    const trimmed = (value || '').trim();
    this.enjeuService.updateMetrique(metriqueId, { etat_reference: trimmed }).subscribe({
      next: () => this.patchLocalMetrique(metriqueId, { etat_reference: trimmed }),
    });
  }

  // ===========================================================================
  // #452 — Format grille des indicateurs de réponse
  // ===========================================================================

  /** Mnémonique du type de métrique (NUMERIQUE par défaut), depuis la nomenclature. */
  getMetriqueTypeMnemonique(typeMetriqueId: number | null | undefined): string {
    if (!typeMetriqueId) return 'NUMERIQUE';
    return this.typeMetriqueOptions().find(o => o.id_nomenclature === typeMetriqueId)?.mnemonique || 'NUMERIQUE';
  }

  /** MetriqueFormData (éditeur de grille) d'une métrique de réponse sauvegardée,
   *  construite à la demande et mémoïsée pour conserver l'état d'édition. */
  responseGridData(ref: MetriqueRef): MetriqueFormData {
    let data = this.responseFormDataMap.get(ref.id_metrique);
    if (!data) {
      data = metriqueRefToFormData(ref);
      this.responseFormDataMap.set(ref.id_metrique, data);
    }
    return data;
  }

  /** Bascule le format (SIMPLE / GRILLE) d'une métrique de réponse sauvegardée.
   *  Mise à jour **optimiste** : l'éditeur de grille (et son champ « Type de grille
   *  de métrique ») s'affiche immédiatement, sans attendre l'aller-retour serveur
   *  qui bloquait le rendu (#452 — retour de test). En cas d'échec réseau, on
   *  restaure l'état précédent. */
  setResponseFormat(ref: MetriqueRef, grille: boolean): void {
    const formatId = this.formatId(grille ? 'GRILLE' : 'SIMPLE');
    const previous = {
      format_metrique_id: ref.format_metrique_id ?? null,
      format_metrique_mnemonique: ref.format_metrique_mnemonique ?? null,
    };
    this.patchLocalMetrique(ref.id_metrique, {
      format_metrique_id: formatId,
      format_metrique_mnemonique: grille ? 'GRILLE' : 'SIMPLE',
    });
    this.enjeuService.updateMetrique(ref.id_metrique, { format_metrique: formatId }).subscribe({
      // #452 — en cas d'échec (ex. plan devenu non modifiable → 403), on restaure
      // l'état précédent ET on l'explique : sans message, l'utilisateur voyait la
      // case « se cocher puis se décocher » sans comprendre pourquoi.
      error: (err: unknown) => {
        this.patchLocalMetrique(ref.id_metrique, previous);
        if (this.handlePlanLocked(err)) return;
        this.snackBar.open(
          this.translate.instant('enjeux.operations.formatGrilleSaveError'),
          this.translate.instant('common.actions.close'),
          { duration: 5000 },
        );
      },
    });
  }

  /** L'éditeur de grille a émis une modification → auto-sauvegarde débouncée.
   *  On mémorise aussi le dernier état pour pouvoir le flusher au submit (#452). */
  onResponseGridChange(metriqueId: number, data: MetriqueFormData): void {
    this.latestGridData.set(metriqueId, data);
    this.gridSave$.next({ metriqueId, data });
  }

  /** Bascule le format d'un indicateur de réponse en attente (création). */
  setPendingResponseFormat(pi: OperationFormComponent['pendingResponseIndicators'][number], grille: boolean): void {
    pi.format_metrique_id = this.formatId(grille ? 'GRILLE' : 'SIMPLE');
    if (grille && !pi.formData) {
      const fd = blankMetriqueFormData();
      fd.nom_metrique = pi.nom_metrique;
      fd.type_metrique = pi.type_metrique_id;
      fd.etat_reference = pi.valeur_cible;
      pi.formData = fd;
    }
  }
  isPendingGrille(pi: OperationFormComponent['pendingResponseIndicators'][number]): boolean {
    return this.isGrilleFormat(pi.format_metrique_id);
  }

  private buildPayload(): OperationCreatePayload {
    const fv = this.form.value;

    // getRawValue() includes disabled fields (for readonly suivi mode)
    const rawFv = this.form.getRawValue();

    // Use rawFv for libelle since it may be disabled (auto-filled from inventaire)
    let libelle = rawFv.libelle?.trim() || '';
    if (!libelle) {
      const selected = this.selectedTypeAction();
      if (selected) {
        const code = selected.cd_nomenclature || selected.mnemonique || '';
        libelle = `${code} - ${selected.label}`;
      }
    }
    if (!libelle) {
      libelle = this.translate.instant('enjeux.operations.draftPlaceholderLibelle');
    }

    const payload: OperationCreatePayload = {
      libelle,
    };

    if (fv.id_type_action) payload.id_type_action = fv.id_type_action;
    if (fv.id_priorite) payload.id_priorite = fv.id_priorite;
    // #228 — Catégorie d'action réserve (optionnel).
    const catReserve = this.categorieActionReserveCtrl.value;
    if (catReserve != null) {
      payload.id_categorie_action_reserve = catReserve;
    } else {
      payload.id_categorie_action_reserve = null;
    }
    if (fv.code_operation?.trim()) payload.code_operation = fv.code_operation.trim();
    if (fv.id_referentiel_operations?.trim()) payload.id_referentiel_operations = fv.id_referentiel_operations.trim();
    if (fv.description?.trim()) payload.description = fv.description.trim();
    if (fv.annee_min != null) payload.annee_min = fv.annee_min;
    if (fv.annee_max != null) payload.annee_max = fv.annee_max;

    // est_suivi_existant
    payload.est_suivi_existant = this.estSuiviExistant();

    // If existing suivi selected, pass id_suivi
    if (this.estSuiviExistant() && fv.id_suivi) {
      payload.id_suivi = fv.id_suivi;
    }

    // Build nested suivi_inventaire from form fields (only if CS action and not "existing suivi" mode)
    if (this.isCSAction() && !this.estSuiviExistant()) {
      const suiviData: Record<string, unknown> = {};
      // Intitulé de l'inventaire (requis pour les nouveaux)
      if (fv.intitule_suivi?.trim()) suiviData['intitule'] = fv.intitule_suivi.trim();
      // Propager le type d'action CS sélectionné
      if (fv.id_type_action) suiviData['id_type_action'] = fv.id_type_action;
      if (rawFv.objectif_principal?.trim()) suiviData['objectif_principal'] = rawFv.objectif_principal.trim();
      if (rawFv.objectif_secondaire?.trim()) suiviData['objectif_secondaire'] = rawFv.objectif_secondaire.trim();
      if (rawFv.cibles_principales) suiviData['cibles_principales'] = rawFv.cibles_principales;
      if (rawFv.cible_secondaire) suiviData['cible_secondaire'] = rawFv.cible_secondaire;
      // Serialize taxon/habitat reference lists to strings
      if (this.taxonItems.length > 0) {
        suiviData['taxon_taxref'] = this.taxonItems.map(t => t.nom_complet || String(t.cd_nom)).join(', ');
      }
      if (this.habitatItems.length > 0) {
        // `habitat_ref` (noms) conservé pour l'affichage hérité ; `habitats`
        // (structuré, avec cd_hab) permet d'afficher les correspondances.
        suiviData['habitat_ref'] = this.habitatItems.map(h => h.lb_hab_fr || h.cd_hab).join(', ');
        // #368 — on conserve aussi les habitats « libres » (sans cd_hab, ex. Outre-mer) :
        // cd_hab=null + libellé saisi. On ne garde que les entrées ayant un code OU un libellé.
        suiviData['habitats'] = this.habitatItems
          .filter(h => h.cd_hab || (h.lb_hab_fr || '').trim())
          .map(h => ({
            cd_hab: h.cd_hab || null,
            lb_hab_fr: h.lb_hab_fr,
            lb_code: h.lb_code,
            lb_typo: h.lb_typo,
            lb_hab_fr_complet: h.lb_hab_fr_complet,
          }));
      } else {
        suiviData['habitats'] = [];
      }
      const dateLancement = this.formatDate(rawFv.date_lancement_suivi);
      if (dateLancement) suiviData['date_lancement_suivi'] = dateLancement;
      if (rawFv.outil_bancarisation) suiviData['outil_bancarisation'] = rawFv.outil_bancarisation;
      if (rawFv.outil_saisie) suiviData['outil_saisie'] = rawFv.outil_saisie;
      if (rawFv.transmission_donnee != null) suiviData['transmission_donnee'] = rawFv.transmission_donnee;

      // Build nested protocole
      const protocoleData: Record<string, unknown> = {};
      if (rawFv.protocole_dans_campanule != null) protocoleData['protocole_dans_campanule'] = rawFv.protocole_dans_campanule;
      if (rawFv.protocole_campanule_nom) protocoleData['protocole_campanule_nom'] = rawFv.protocole_campanule_nom;
      if (rawFv.cd_protocole_campanule != null) protocoleData['cd_protocole_campanule'] = rawFv.cd_protocole_campanule;
      if (rawFv.nb_etp_cycle != null) protocoleData['nb_etp_cycle'] = rawFv.nb_etp_cycle;
      if (rawFv.nom_protocole?.trim()) protocoleData['nom_protocole'] = rawFv.nom_protocole.trim();
      if (rawFv.respect_protocole != null) protocoleData['respect_protocole'] = rawFv.respect_protocole;
      if (rawFv.justification_non_respect?.trim()) protocoleData['justification_non_respect'] = rawFv.justification_non_respect.trim();
      if (rawFv.differences_protocole?.trim()) protocoleData['differences_protocole'] = rawFv.differences_protocole.trim();
      if (rawFv.description_protocole?.trim()) protocoleData['description_protocole'] = rawFv.description_protocole.trim();
      if (rawFv.objectif_protocole?.trim()) protocoleData['objectif_protocole'] = rawFv.objectif_protocole.trim();
      if (rawFv.periode_echantillonnage?.trim()) protocoleData['periode_echantillonnage'] = rawFv.periode_echantillonnage.trim();

      if (Object.keys(protocoleData).length > 0) {
        suiviData['protocole'] = protocoleData;
      }

      if (Object.keys(suiviData).length > 0) {
        payload.suivi_inventaire = suiviData;
      }
    }

    // Fréquence
    if (fv.frequence_nombre != null) payload.frequence_nombre = fv.frequence_nombre;
    if (fv.frequence_unite) payload.frequence_unite = fv.frequence_unite;
    if (fv.operateurs?.trim()) payload.operateurs = fv.operateurs.trim();
    if (fv.partenaires?.trim()) payload.partenaires = fv.partenaires.trim();
    // #343 — financeur textuel supprimé : on n'envoie plus le champ libre (financeurs structurés via `finances`).
    if (fv.metrique_ids?.length) payload.metrique_ids = fv.metrique_ids;
    // #367/#398 — toujours rattacher l'action à son indicateur parent
    // (rattachement direct OU indicateur de la métrique pré-liée). Sans ça,
    // une action sans métrique restait orpheline et n'apparaissait nulle part.
    const indId = this.currentIndicateurId();
    if (indId) payload.id_indicateur = indId;

    // Sites
    const siteIds = Object.entries(this.selectedSiteIds)
      .filter(([_, selected]) => selected)
      .map(([id, _]) => parseInt(id, 10));
    if (siteIds.length) payload.site_ids = siteIds;

    // Template mensuel (mêmes mois chaque année)
    payload.programmation_mensuelle_defaut = { ...this.programmationMensuelleDefaut };

    // Mode de ventilation du budget
    const mode = this.ventilationMode();
    payload.ventilation_mode = mode;

    // Operation annees: apply the monthly template to all years + per-organisme data
    const orgs = this.availableOrganismes();
    type OrgEntry = { id_organisme: number; budget_fonctionnement: number | null; budget_investissement: number | null; etp: number | null };
    const anneesToSave = this.operationAnnees.map((a, idx) => {
      const base = {
        annee: a.annee,
        periodicite: a.periodicite,
        periodicite_mensuelle: { ...this.programmationMensuelleDefaut },
      };

      if (mode === 'none') {
        // Mode 1: Pas de ventilation — totaux directs
        const directData = this.getDirectTotal(idx);
        return { ...base, budget: directData.budget, etp: directData.etp, budget_fonctionnement: null, budget_investissement: null, organismes: [] as OrgEntry[] };
      }

      if (mode === 'by_type') {
        // Mode 3: Par type de budget (global, sans organismes)
        const typeData = this.getTypeBudget(idx);
        const totalBudget = (typeData.fonct || 0) + (typeData.invest || 0);
        return { ...base, budget: totalBudget || null, etp: typeData.etp, budget_fonctionnement: typeData.fonct, budget_investissement: typeData.invest, organismes: [] as OrgEntry[] };
      }

      if (mode === 'by_org') {
        // Mode 2: Par organisme (totaux, sans fonct/invest)
        const orgEntries: OrgEntry[] = [];
        for (const org of orgs) {
          const data = this.getOrgByOrgData(idx, org.id_organisme);
          if (data.budget != null || data.etp != null) {
            orgEntries.push({
              id_organisme: org.id_organisme,
              budget_fonctionnement: data.budget,
              budget_investissement: null,
              etp: data.etp,
            });
          }
        }
        const totalBudget = orgEntries.reduce((sum, o) => sum + (o.budget_fonctionnement || 0), 0);
        const totalEtp = orgEntries.reduce((sum, o) => sum + (o.etp || 0), 0);
        return { ...base, budget: orgEntries.length > 0 ? totalBudget : null, etp: orgEntries.length > 0 ? totalEtp : null, budget_fonctionnement: null, budget_investissement: null, organismes: orgEntries };
      }

      // Mode 4: by_org_type — Par organisme + type (mode actuel ventilation)
      const orgEntries: OrgEntry[] = [];
      for (const org of orgs) {
        const data = this.getOrgBudget(idx, org.id_organisme);
        if (data.fonct != null || data.invest != null || data.etp != null) {
          orgEntries.push({
            id_organisme: org.id_organisme,
            budget_fonctionnement: data.fonct,
            budget_investissement: data.invest,
            etp: data.etp,
          });
        }
      }
      const totalBudget = orgEntries.reduce((sum, o) => sum + (o.budget_fonctionnement || 0) + (o.budget_investissement || 0), 0);
      const totalEtp = orgEntries.reduce((sum, o) => sum + (o.etp || 0), 0);
      return { ...base, budget: orgEntries.length > 0 ? totalBudget : a.budget, etp: orgEntries.length > 0 ? totalEtp : a.etp, budget_fonctionnement: null, budget_investissement: null, organismes: orgEntries };
    });

    const hasAnneeData = anneesToSave.some(
      a => a.periodicite || a.budget != null || a.etp != null ||
        a.organismes.length > 0 ||
        Object.values(a.periodicite_mensuelle).some(v => v)
    );
    if (hasAnneeData) {
      payload.operation_annees = anneesToSave;
    }

    // Finances (relational)
    if (this.finances.length > 0) {
      payload.finances = this.finances
        .filter(f => f.libelle?.trim())
        .map(f => ({
          libelle: f.libelle.trim(),
          id_categorie: f.id_categorie || undefined
        }));
    }

    // Emprise spatiale (#342) : incluse uniquement si modifiée localement
    // (undefined = on ne touche pas au serveur ; null = effacement explicite).
    const pendingEmprise = this.pendingEmprise();
    if (pendingEmprise !== undefined) {
      payload.geom_geojson = pendingEmprise;
    }

    return payload;
  }

  /**
   * Soumet le payload à l'API (create ou update).
   * `stayOnForm = true` (saveDraft) : reste sur le formulaire ; en création, redirige
   * silencieusement vers l'URL d'édition pour que les saves suivants soient des PATCH.
   * `stayOnForm = false` (save validé) : navigue vers la liste après succès.
   */
  private submitToApi(
    payload: OperationCreatePayload,
    opts: { stayOnForm: boolean; statut: OperationStatut },
  ): void {
    this.isLoading.set(true);
    this.errorMessage.set(null);
    // #452 — flush des grilles d'indicateurs de réponse en attente (auto-save
    // débouncé non encore parti) AVANT de soumettre/naviguer : sinon les
    // dernières saisies de grille (type, valeurs, libellés) sont perdues quand
    // l'utilisateur clique « Valider » juste après les avoir remplies.
    // En validation stricte (« Valider »), une grille incomplète / sans intitulé
    // de métrique fait échouer le flush (400) → on BLOQUE et on affiche l'erreur,
    // au lieu de valider l'action alors que la grille n'a pas pu s'enregistrer.
    const strict = !opts.stayOnForm;
    this.flushResponseGrids(strict).subscribe({
      next: () => this.doSubmitToApi(payload, opts),
      error: () => {
        if (strict) {
          this.isLoading.set(false);
          this.snackBar.open(
            this.translate.instant('enjeux.operations.responseGridIncomplete'),
            this.translate.instant('common.actions.close'),
            { duration: 7000 },
          );
          this.scrollToError();
          return;
        }
        // brouillon : on ne bloque pas la sauvegarde pour une grille incomplète.
        this.doSubmitToApi(payload, opts);
      },
    });
  }

  private doSubmitToApi(
    payload: OperationCreatePayload,
    opts: { stayOnForm: boolean; statut: OperationStatut },
  ): void {
    payload.statut = opts.statut;

    const successKey = opts.stayOnForm
      ? 'enjeux.operations.saveSuccess'
      : (this.isEditMode() ? 'enjeux.operations.updateSuccess' : 'enjeux.operations.createSuccess');

    if (this.isEditMode()) {
      const opId = this.operationId()!;
      this.enjeuService.updateOperation(opId, payload).subscribe({
        next: () => {
          this.isLoading.set(false);
          this.snackBar.open(
            this.translate.instant(successKey),
            this.translate.instant('common.actions.close'),
            { duration: 3000 }
          );
          this.enjeuService.refreshCurrentPlanEnjeux();
          if (!opts.stayOnForm) {
            // #482 — Revenir sur l'enjeu/onglet d'origine (et déployer l'action
            // modifiée) plutôt que d'utiliser location.back(), qui pouvait
            // ramener l'utilisateur « sur l'OO » de façon inattendue.
            this.navigateAfterCreate(opId);
          }
        },
        error: (error) => {
          this.isLoading.set(false);
          this.errorMessage.set(
            error.message || this.translate.instant('enjeux.messages.updateError')
          );
          this.scrollToError();
        }
      });
    } else {
      this.enjeuService.createOperation(payload).subscribe({
        next: (created) => {
          const newOpId = created?.id_operation ?? null;
          // Créer les indicateurs de réponse saisis avant l'enregistrement.
          const pending = this.pendingResponseIndicators;
          const createPending$: Observable<unknown> = (newOpId && pending.length > 0)
            ? forkJoin(pending.map(pi => {
                const grille = this.isGrilleFormat(pi.format_metrique_id);
                // En grille, la métrique (nom/type/cible) est portée par la
                // grille en mémoire (pi.formData) ; sinon par les champs simples.
                const fd = pi.formData;
                const body: Record<string, unknown> = {
                  nom_indicateur: (pi.nom_indicateur || '').trim() || this.translate.instant('enjeux.operations.newIndicatorDefault'),
                  format_metrique: pi.format_metrique_id ?? undefined,
                };
                if (grille && fd) {
                  const mnemo = this.getMetriqueTypeMnemonique(fd.type_metrique);
                  body['nom_metrique'] = (fd.nom_metrique || '').trim() || undefined;
                  body['type_metrique_id'] = fd.type_metrique ?? undefined;
                  body['valeur_cible'] = (fd.etat_reference || '').trim() || undefined;
                  Object.assign(body, buildMetriqueGridFields(fd, mnemo));
                } else {
                  body['nom_metrique'] = (pi.nom_metrique || '').trim() || undefined;
                  body['type_metrique_id'] = pi.type_metrique_id ?? undefined;
                  body['valeur_cible'] = (pi.valeur_cible || '').trim() || undefined;
                }
                return this.enjeuService.createOperationResponseIndicator(newOpId, body as any);
              }))
            : of(null);

          createPending$.subscribe({
            next: () => {
              this.pendingResponseIndicators = [];
              this.isLoading.set(false);
              this.snackBar.open(
                this.translate.instant(successKey),
                this.translate.instant('common.actions.close'),
                { duration: 3000 }
              );
              this.enjeuService.refreshCurrentPlanEnjeux();
              if (opts.stayOnForm && newOpId) {
                this.navigateToEdit(newOpId);
              } else {
                this.navigateAfterCreate(newOpId);
              }
            },
            error: () => {
              // L'action est créée ; seul l'ajout d'un indicateur a échoué.
              this.isLoading.set(false);
              this.snackBar.open(
                this.translate.instant('enjeux.operations.indicateursAddError'),
                this.translate.instant('common.actions.close'),
                { duration: 4000 }
              );
              this.enjeuService.refreshCurrentPlanEnjeux();
              if (newOpId) this.navigateToEdit(newOpId);
            },
          });
        },
        error: (error) => {
          this.isLoading.set(false);
          this.errorMessage.set(
            error.message || this.translate.instant('enjeux.messages.createError')
          );
          this.scrollToError();
        }
      });
    }
  }

  /**
   * Après un saveDraft en mode création : redirige vers l'URL d'édition de l'opération
   * créée, en remplaçant l'historique pour que l'utilisateur ne revienne pas sur le
   * formulaire de création vide via "back".
   */
  private navigateToEdit(opId: number): void {
    const slug = this.planSlug();
    if (!slug) {
      return;
    }
    this.router.navigate(
      ['/plans', slug, 'enjeux', 'operations', opId, 'modifier'],
      { replaceUrl: true, queryParamsHandling: 'preserve' }
    );
  }

  /**
   * Met à jour les validators conditionnels en fonction de l'état du formulaire.
   * Couvre tous les champs marqués d'un `*` dans le template :
   *  - intitule_suivi : requis si action CS et nouveau suivi
   *  - protocole_dans_campanule, respect_protocole : requis si action CS et nouveau suivi
   *  - cd_protocole_campanule : requis si ci-dessus + mode CAMPanule (Oui)
   *  - nom_protocole : requis si ci-dessus + mode hors CAMPanule (Non)
   *
   * Doit être appelé après populateForm, au changement de type d'action, au
   * toggle "suivi existant", et au changement de "protocole dans CAMPanule".
   */
  private syncConditionalValidators(): void {
    const requireForCS = this.isCSAction() && !this.estSuiviExistant();
    const protocoleCampanule = this.form.get('protocole_dans_campanule')?.value;

    this.applyRequiredValidator('intitule_suivi', requireForCS);
    // #461 — objectif principal + cible principale obligatoires pour une
    // action de type suivi (CS, nouveau suivi).
    this.applyRequiredValidator('objectif_principal', requireForCS);
    this.applyRequiredValidator('cibles_principales', requireForCS);
    this.applyRequiredValidator('protocole_dans_campanule', requireForCS);
    // #414 — « Respect strict du protocole » n'est demandé que pour les
    // protocoles CAMPanule ; masqué (et non requis) pour les protocoles locaux.
    this.applyRequiredValidator(
      'respect_protocole',
      requireForCS && protocoleCampanule === true,
    );
    this.applyRequiredValidator(
      'cd_protocole_campanule',
      requireForCS && protocoleCampanule === true,
    );
    // #413 — le nom d'un protocole non-CAMPanule (nom local) est facultatif.
    this.applyRequiredValidator('nom_protocole', false);
  }

  /** Helper : ajoute ou retire Validators.required sur un contrôle, sans émettre. */
  private applyRequiredValidator(controlName: string, required: boolean): void {
    const ctrl = this.form.get(controlName);
    if (!ctrl) return;
    if (required) {
      ctrl.setValidators([Validators.required]);
    } else {
      ctrl.clearValidators();
    }
    ctrl.updateValueAndValidity({ emitEvent: false });
  }

  /**
   * Tableau (formControlName, clé i18n du label) pour traduire les contrôles
   * invalides en libellés humains dans le message d'erreur.
   */
  private readonly fieldLabelKeys: Record<string, string> = {
    libelle: 'enjeux.operations.libelleLabel',
    intitule_suivi: 'enjeux.operations.intituleSuiviLabel',
    id_type_action: 'enjeux.operations.typeActionLabel',
    objectif_principal: 'enjeux.operations.objectifPrincipal',
    cibles_principales: 'enjeux.operations.ciblesPrincipales',
    protocole_dans_campanule: 'enjeux.operations.protocoleCampanule',
    cd_protocole_campanule: 'enjeux.operations.protocoleNom',
    nom_protocole: 'enjeux.operations.nomProtocole',
    respect_protocole: 'enjeux.operations.respectProtocole',
  };

  /**
   * Construit un message d'erreur listant les champs invalides (libellés
   * traduits) et l'affiche dans la bannière en haut du formulaire.
   */
  private showValidationErrorMessage(): void {
    const invalidLabels = this.collectInvalidFieldLabels();
    if (invalidLabels.length > 0) {
      this.errorMessage.set(
        this.translate.instant('enjeux.messages.validationFailedWithFields', {
          fields: invalidLabels.join(', '),
        }),
      );
    } else {
      this.errorMessage.set(this.translate.instant('enjeux.messages.validationFailed'));
    }
  }

  /** Liste les libellés (traduits) des contrôles invalides du formulaire. */
  private collectInvalidFieldLabels(): string[] {
    const labels: string[] = [];
    for (const [name, control] of Object.entries(this.form.controls)) {
      if (control.invalid && this.fieldLabelKeys[name]) {
        labels.push(this.translate.instant(this.fieldLabelKeys[name]));
      }
    }
    return labels;
  }

  /**
   * Scrolle le premier contrôle invalide du formulaire au centre du viewport
   * et y donne le focus. Couvre mat-form-field, mat-radio-group, mat-select
   * (et fallback sur n'importe quel élément `.ng-invalid` non-form).
   */
  private scrollToError(): void {
    setTimeout(() => {
      // 1) Premier contrôle invalide en ordre du DOM (radio group, select, form-field) :
      //    c'est l'endroit où l'utilisateur doit corriger, donc priorité 1.
      const candidates = this.elRef.nativeElement.querySelectorAll(
        'mat-form-field.ng-invalid, mat-radio-group.ng-invalid, mat-select.ng-invalid, .ng-invalid:not(form):not(mat-form-field):not(mat-radio-group):not(mat-select)',
      ) as NodeListOf<HTMLElement>;

      for (const el of Array.from(candidates)) {
        // Ignore le formulaire racine et les éléments cachés (display:none).
        if (el.tagName === 'FORM') continue;
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) continue;

        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Focus si possible (input, textarea ou bouton interne).
        const focusable = el.querySelector('input, textarea, [tabindex]:not([tabindex="-1"])') as HTMLElement | null;
        focusable?.focus({ preventScroll: true });
        return;
      }

      // 2) Aucun contrôle invalide → on retombe sur la bannière (cas erreur backend).
      const banner = this.elRef.nativeElement.querySelector('.error-banner');
      banner?.scrollIntoView({ behavior: 'smooth', block: 'center' });
    });
  }

  /**
   * Retour à la page précédente via l'historique du navigateur.
   * Préserve l'URL exacte (filtres, onglet, query params) et la position de scroll.
   */
  goBack(): void {
    this.location.back();
  }

  /**
   * Navigation après création d'une nouvelle action : on cible l'enjeu d'origine
   * en demandant à la liste de déployer et scroller jusqu'à la nouvelle action.
   */
  private navigateAfterCreate(newOpId: number | null): void {
    const slug = this.planSlug();
    if (!slug) {
      this.router.navigate(['/plans']);
      return;
    }

    const returnEnjeu = this.returnEnjeuSlug();
    const metriqueId = this.prelinkedMetriqueId();
    if (returnEnjeu) {
      // #398 — revenir sur l'onglet d'origine (OLT ou Opérations) plutôt que
      // de forcer « operations » : une action sans métrique n'apparaît pas
      // dans l'onglet Opérations et l'utilisateur se retrouvait « sur les OO ».
      const queryParams: Record<string, number | string> = { tab: this.returnTab() || 'operations' };
      if (newOpId) {
        queryParams['expandOperation'] = newOpId;
      } else if (metriqueId) {
        queryParams['expandMetrique'] = metriqueId;
      }
      this.router.navigate(
        ['/plans', slug, 'enjeux', returnEnjeu],
        { queryParams }
      );
    } else {
      this.router.navigate(['/plans', slug, 'enjeux']);
    }
  }

  toggleSection(section: string): void {
    this.sectionsOpen[section] = !this.sectionsOpen[section];
  }

  setEstSuiviExistant(value: boolean): void {
    this.estSuiviExistant.set(value);
    if (value) {
      // "Existing suivi" mode: disable suivi fields
      this.setSuiviFieldsEnabled(false);
      // Sync libelle from selected inventaire
      this.updateLibelle(this.getSelectedSuiviIntitule());
    } else {
      // "New suivi" mode: enable suivi fields, reset values
      this.resetSuiviFields();
      this.setSuiviFieldsEnabled(true);
      this.form.get('id_suivi')?.setValue(null);
      // Sync libelle from intitule_suivi text
      this.updateLibelle(this.form.get('intitule_suivi')?.value || '');
    }
    this.syncConditionalValidators();
  }

  /**
   * For CS actions, libelle = intitulé de l'inventaire (existing or new).
   * Subscribe to id_suivi changes and intitule_suivi keystrokes.
   */
  private initSuiviLibelleSync(): void {
    // Existing suivi selected → sync libelle + fetch full details
    this.form.get('id_suivi')?.valueChanges.subscribe((idSuivi) => {
      if (this.isCSAction() && this.estSuiviExistant()) {
        this.updateLibelle(this.getSelectedSuiviIntitule());
        if (idSuivi) {
          this.fetchAndPopulateSuiviDetails(idSuivi);
        }
      }
    });

    // New suivi typed → sync libelle as user types
    this.form.get('intitule_suivi')?.valueChanges.subscribe((val) => {
      if (this.isCSAction() && !this.estSuiviExistant()) {
        this.updateLibelle(val || '');
      }
    });

    // Switch CAMPanule (Oui/Non) change le champ requis (cd_protocole_campanule
    // vs nom_protocole) → re-synchroniser les validators.
    this.form.get('protocole_dans_campanule')?.valueChanges.subscribe(() => {
      this.syncConditionalValidators();
    });
  }

  /** Get the intitule of the currently selected existing inventaire. */
  private getSelectedSuiviIntitule(): string {
    const idSuivi = this.form.get('id_suivi')?.value;
    if (!idSuivi) return '';
    const inv = this.availableInventaires().find(i => i.id_suivi_inventaire === idSuivi);
    return inv?.intitule || '';
  }

  /** Update the libelle form control and its display signal. */
  private updateLibelle(value: string): void {
    this.form.get('libelle')?.setValue(value, { emitEvent: false });
    this.libelleDisplay.set(value);
  }

  /** Fetch full inventaire details and populate the suivi/protocole form fields. */
  private fetchAndPopulateSuiviDetails(idSuivi: number): void {
    this.inventaireService.getInventaire(idSuivi).subscribe({
      next: (detail: SuiviInventaireDetail) => {
        // Populate taxon/habitat reference lists
        if (detail.taxon_taxref) {
          this.taxonItems = detail.taxon_taxref.split(',').map(s => s.trim()).filter(s => s).map(name => ({
            cd_nom: 0,
            nom_complet: name,
          }));
        } else {
          this.taxonItems = [];
        }
        if (Array.isArray(detail.habitats) && detail.habitats.length > 0) {
          this.habitatItems = detail.habitats.map((h: any) => ({ cd_hab: h.cd_hab ?? '', lb_hab_fr: h.lb_hab_fr ?? '', lb_code: h.lb_code, lb_typo: h.lb_typo, lb_hab_fr_complet: h.lb_hab_fr_complet }));
        } else if (detail.habitat_ref) {
          this.habitatItems = detail.habitat_ref.split(',').map(s => s.trim()).filter(s => s).map(name => ({
            cd_hab: '',
            lb_hab_fr: name,
          }));
        } else {
          this.habitatItems = [];
        }

        // Populate suivi fields
        this.form.patchValue({
          objectif_principal: detail.objectif_principal || '',
          objectif_secondaire: detail.objectif_secondaire || '',
          cibles_principales: detail.cibles_principales || null,
          cible_secondaire: detail.cible_secondaire || '',
          date_lancement_suivi: detail.date_lancement_suivi ? new Date(detail.date_lancement_suivi) : null,
          outil_bancarisation: detail.outil_bancarisation || null,
          outil_saisie: detail.outil_saisie || null,
          transmission_donnee: detail.transmission_donnee ?? null,
        });

        // Populate protocole fields
        const proto = detail.protocole;
        if (proto) {
          this.form.patchValue({
            protocole_dans_campanule: proto.protocole_dans_campanule ?? null,
            protocole_campanule_nom: proto.protocole_campanule_nom || '',
            cd_protocole_campanule: proto.cd_protocole_campanule || null,
            nb_etp_cycle: proto.nb_etp_cycle || null,
            nom_protocole: proto.nom_protocole || '',
            respect_protocole: proto.respect_protocole ?? null,
            justification_non_respect: proto.justification_non_respect || '',
            differences_protocole: proto.differences_protocole || '',
            description_protocole: proto.description_protocole || '',
            objectif_protocole: proto.objectif_protocole || '',
            periode_echantillonnage: proto.periode_echantillonnage || '',
          });

          // Restore CAMPanule autocomplete state
          if (proto.cd_protocole_campanule && proto.protocole_campanule_nom) {
            this.campanuleSearchCtrl.setValue(proto.protocole_campanule_nom, { emitEvent: false });
            this.selectedCampanule.set({
              cd_protocole: proto.cd_protocole_campanule,
              search_name: proto.protocole_campanule_nom,
              lb_protocole_court: proto.protocole_campanule_nom,
            });
          }
        }
      },
    });
  }

  // ════════════════════════════════════════════════
  // Type d'action autocomplete (codes Eden 62)
  // ════════════════════════════════════════════════

  private initTypeActionAutocomplete(): void {
    this.typeActionSearchCtrl.valueChanges.subscribe((val) => {
      if (typeof val === 'string') {
        this.typeActionSearchText.set(val);
      }
    });
  }

  displayTypeActionFn = displayNomenclatureFn;

  onTypeActionSelected(option: NomenclatureOption): void {
    this.selectedTypeAction.set(option);
    this.form.get('id_type_action')?.setValue(option.id_nomenclature);

    // Si c'est un code CS, charger les inventaires correspondants et griser le libellé
    const code = option.cd_nomenclature || option.mnemonique || '';
    if (code.startsWith('CS')) {
      this.loadInventairesByTypeAction(code);
      this.form.get('libelle')?.disable();
    } else {
      this.availableInventaires.set([]);
      this.estSuiviExistant.set(false);
      this.form.get('libelle')?.enable();
    }
    this.syncConditionalValidators();
  }

  clearTypeAction(): void {
    this.typeActionSearchCtrl.setValue('');
    this.selectedTypeAction.set(null);
    this.form.get('id_type_action')?.setValue(null);
    this.availableInventaires.set([]);
    this.estSuiviExistant.set(false);
    this.form.get('libelle')?.enable();
    this.syncConditionalValidators();
  }

  /** Charge les inventaires existants filtrés par préfixe du type d'action CS */
  private loadInventairesByTypeAction(codePrefix: string): void {
    this.inventaireService.getInventaires({ type_action_prefix: codePrefix, page_size: 200 }).subscribe({
      next: (res) => {
        const items = (res.results || []).map((inv: any) => ({
          id_suivi_inventaire: inv.id_suivi_inventaire,
          intitule: inv.intitule,
          type_action_code: inv.type_action_code,
        }));
        this.availableInventaires.set(items);
      },
      error: () => this.availableInventaires.set([]),
    });
  }

  private restoreTypeActionAutocomplete(typeActionId: number, options?: NomenclatureOption[]): void {
    const opts = options || this.typeActionOptions();
    const match = opts.find(o => o.id_nomenclature === typeActionId);
    if (match) {
      this.selectedTypeAction.set(match);
      this.typeActionSearchCtrl.setValue(this.displayTypeActionFn(match), { emitEvent: false });
    }
  }

  private buildActionGroups(options: NomenclatureOption[], searchText: string): NomenclatureGroup[] {
    return buildNomenclatureGroups(options, searchText);
  }

  getActionDepth = getNomenclatureDepth;

  // ════════════════════════════════════════════════
  // CAMPanule autocomplete
  // ════════════════════════════════════════════════

  private initCampanuleAutocomplete(): void {
    this.campanuleSearchCtrl.valueChanges.pipe(
      debounceTime(300),
      distinctUntilChanged(),
      filter((val): val is string => typeof val === 'string' && val.length >= 1),
      switchMap((search) => this.campanuleService.autocomplete(search))
    ).subscribe({
      next: (results) => this.campanuleResults.set(results),
      error: () => this.campanuleResults.set([]),
    });
  }

  displayCampanuleFn(option: CampanuleAutocomplete | string): string {
    if (!option) return '';
    if (typeof option === 'string') return option;
    return option.lb_protocole_court || '';
  }

  onCampanuleSelected(event: any): void {
    const selected: CampanuleAutocomplete = event.option.value;
    this.selectedCampanule.set(selected);
    // Ne pas appeler setValue ici : Angular Material gère l'affichage via displayWith

    this.form.patchValue({
      protocole_campanule_nom: selected.lb_protocole_court,
      cd_protocole_campanule: selected.cd_protocole,
    });

    // Fetch full protocol details to populate description/objectif/période
    this.campanuleService.getProtocole(selected.cd_protocole).subscribe({
      next: (detail) => {
        this.form.patchValue({
          description_protocole: detail.description || '',
          objectif_protocole: detail.descr_objectif_prot || '',
        });
        if (detail.echantillonnages && detail.echantillonnages.length > 0) {
          const periodes = detail.echantillonnages
            .filter(e => e.periode_an)
            .map(e => e.periode_an)
            .join('; ');
          if (periodes) {
            this.form.patchValue({ periode_echantillonnage: periodes });
          }
        }
      },
    });
  }

  onCampanuleReset(): void {
    this.selectedCampanule.set(null);
    this.campanuleSearchCtrl.setValue('');
    this.form.patchValue({
      protocole_campanule_nom: '',
      cd_protocole_campanule: null,
      description_protocole: '',
      objectif_protocole: '',
      periode_echantillonnage: '',
    });
  }

  /**
   * #520 — Au changement MANUEL du choix « le protocole est-il dans CAMPanule ? »,
   * vider la sélection CAMPanule et les champs auto-remplis depuis le protocole
   * (description, objectif, période). Sans cela, en repassant sur « Non » les
   * valeurs issues de CAMPanule restaient affichées dans les champs éditables
   * (et inversement, des données saisies restaient sous un protocole CAMPanule).
   * Branché sur l'événement (change) du radio : ne se déclenche donc PAS lors du
   * patchValue de chargement en édition (préserve les données enregistrées).
   */
  onProtocoleCampanuleChange(): void {
    this.onCampanuleReset();
  }

  consulterProtocole(): void {
    const cdProtocole = this.form.get('cd_protocole_campanule')?.value;
    if (!cdProtocole) return;

    this.dialog.open(ProtocoleCampanuleDialogComponent, {
      width: '900px',
      maxWidth: '95vw',
      maxHeight: '90vh',
      data: { cdProtocole },
    });
  }

  get isCampanule(): boolean {
    return this.form.get('protocole_dans_campanule')?.value === true;
  }

  get isNotCampanule(): boolean {
    return this.form.get('protocole_dans_campanule')?.value === false;
  }

  get isNonRespect(): boolean {
    return this.form.get('respect_protocole')?.value === false;
  }

  get hasCampanuleSelected(): boolean {
    return !!this.form.get('cd_protocole_campanule')?.value;
  }

  /** Build grouped nomenclature structure from flat options using definition field */
  private buildGroups(options: NomenclatureOption[]): NomenclatureGroup[] {
    const groups: NomenclatureGroup[] = [];
    const groupMap = new Map<string, NomenclatureOption[]>();

    for (const opt of options) {
      const groupKey = opt.definition || '';
      if (!groupMap.has(groupKey)) {
        groupMap.set(groupKey, []);
      }
      groupMap.get(groupKey)!.push(opt);
    }

    for (const [groupLabel, opts] of groupMap) {
      groups.push({ groupLabel, options: opts });
    }
    return groups;
  }

  /** Check if selected cible requires taxref display */
  get showTaxref(): boolean {
    const cible = this.form.get('cibles_principales')?.value;
    return cible === 'ESPECES';
  }

  /** Check if selected cible requires habitat display */
  get showHabitat(): boolean {
    const cible = this.form.get('cibles_principales')?.value;
    return cible === 'HABITATS_VEGETATIONS';
  }

  /** Check if objectif principal is set (to show objectif secondaire) */
  get hasObjectifPrincipal(): boolean {
    return !!this.form.get('objectif_principal')?.value;
  }

  /** Check if cible principale is set (to show cible secondaire) */
  get hasCiblePrincipale(): boolean {
    return !!this.form.get('cibles_principales')?.value;
  }

  onTaxonsChange(items: (TaxonRef | HabitatRef | GeologieRef)[]): void {
    this.taxonItems = items as TaxonRef[];
  }

  onHabitatsChange(items: (TaxonRef | HabitatRef | GeologieRef)[]): void {
    this.habitatItems = items as HabitatRef[];
  }

  private formatDate(date: Date | string | null): string | undefined {
    if (!date) return undefined;
    if (typeof date === 'string') return date;
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }

  private resetSuiviFields(): void {
    const fields = [
      'objectif_principal', 'objectif_secondaire',
      'cibles_principales', 'cible_secondaire',
      'date_lancement_suivi', 'protocole_dans_campanule', 'protocole_campanule_nom',
      'cd_protocole_campanule', 'nb_etp_cycle', 'nom_protocole',
      'respect_protocole', 'justification_non_respect', 'differences_protocole',
      'description_protocole', 'objectif_protocole', 'periode_echantillonnage',
      'outil_bancarisation', 'outil_saisie', 'transmission_donnee',
      'intitule_suivi'
    ];
    for (const field of fields) {
      this.form.get(field)?.reset();
    }
  }

  private setSuiviFieldsEnabled(enabled: boolean): void {
    const fields = [
      'objectif_principal', 'objectif_secondaire',
      'cibles_principales', 'cible_secondaire',
      'date_lancement_suivi', 'protocole_dans_campanule', 'protocole_campanule_nom',
      'cd_protocole_campanule', 'nb_etp_cycle', 'nom_protocole',
      'respect_protocole', 'justification_non_respect', 'differences_protocole',
      'description_protocole', 'objectif_protocole', 'periode_echantillonnage',
      'outil_bancarisation', 'outil_saisie', 'transmission_donnee'
    ];
    for (const field of fields) {
      const control = this.form.get(field);
      if (control) {
        if (enabled) {
          control.enable();
        } else {
          control.disable();
        }
      }
    }
  }

  toggleSite(siteId: number): void {
    this.selectedSiteIds[siteId] = !this.selectedSiteIds[siteId];
    this.selectedSiteIdsVersion.update(v => v + 1);
    // #410 — si l'emprise suit les sites, la recalculer quand la sélection change.
    if (this.useSiteEmprise()) {
      this.computeSiteEmprise();
    }
  }

  /** #410 — bascule « emprise de l'action = emprise du/des site(s) ». */
  toggleUseSiteEmprise(checked: boolean): void {
    this.useSiteEmprise.set(checked);
    if (checked) {
      this.computeSiteEmprise();
    }
    // Décoché : on conserve l'emprise calculée comme point de départ éditable.
  }

  /**
   * #410 — Calcule l'emprise de l'action à partir des géométries des sites
   * sélectionnés (union des MultiPolygons) et l'applique comme emprise courante.
   */
  private computeSiteEmprise(): void {
    const slugs = this.planSites()
      .filter(s => this.selectedSiteIds[s.id_site] && s.slug)
      .map(s => s.slug as string);
    if (slugs.length === 0) {
      this.pendingEmprise.set(null);
      return;
    }
    this.isComputingSiteEmprise.set(true);
    forkJoin(slugs.map(slug => this.adminService.getSiteGeoJSON(slug))).subscribe({
      next: (features) => {
        const geoms = features.map(f => (f as any)?.geometry).filter(Boolean);
        this.pendingEmprise.set(this.combineSiteGeometries(geoms));
        this.isComputingSiteEmprise.set(false);
      },
      error: () => {
        this.isComputingSiteEmprise.set(false);
        this.useSiteEmprise.set(false);
        this.snackBar.open(
          this.translate.instant('enjeux.operations.empriseSitesError'),
          this.translate.instant('common.actions.close'),
          { duration: 4000 },
        );
      },
    });
  }

  /**
   * #410 — Fusionne plusieurs géométries de sites (Polygon / MultiPolygon) en
   * un seul MultiPolygon GeoJSON (concaténation des polygones).
   */
  private combineSiteGeometries(geoms: any[]): any {
    const polygons: any[] = [];
    for (const g of geoms) {
      if (!g) continue;
      if (g.type === 'Polygon') polygons.push(g.coordinates);
      else if (g.type === 'MultiPolygon') polygons.push(...g.coordinates);
    }
    if (polygons.length === 0) return null;
    return { type: 'MultiPolygon', coordinates: polygons };
  }

  // ════════════════════════════════════════════════
  // Per-organisme budget/travail
  // ════════════════════════════════════════════════

  private orgKey(yearIdx: number, orgId: number): string {
    return `${yearIdx}-${orgId}`;
  }

  getOrgBudget(yearIdx: number, orgId: number): { fonct: number | null; invest: number | null; etp: number | null } {
    const key = this.orgKey(yearIdx, orgId);
    if (!this.orgBudgets[key]) {
      this.orgBudgets[key] = { fonct: null, invest: null, etp: null };
    }
    return this.orgBudgets[key];
  }

  updateOrgBudgetFonct(yearIdx: number, orgId: number, value: string): void {
    this.getOrgBudget(yearIdx, orgId).fonct = this.parseDecimal(value);
    this.autoCheckPeriodicite(yearIdx);
  }

  updateOrgBudgetInvest(yearIdx: number, orgId: number, value: string): void {
    this.getOrgBudget(yearIdx, orgId).invest = this.parseDecimal(value);
    this.autoCheckPeriodicite(yearIdx);
  }

  updateOrgEtp(yearIdx: number, orgId: number, value: string): void {
    this.getOrgBudget(yearIdx, orgId).etp = this.parseDecimal(value);
    this.autoCheckPeriodicite(yearIdx);
  }

  getOrgTotal(yearIdx: number, orgId: number): number {
    const data = this.getOrgBudget(yearIdx, orgId);
    return (data.fonct || 0) + (data.invest || 0);
  }

  getYearTotalBudget(yearIdx: number): number {
    let total = 0;
    for (const org of this.availableOrganismes()) {
      total += this.getOrgTotal(yearIdx, org.id_organisme);
    }
    return total;
  }

  getYearTotalEtp(yearIdx: number): number {
    let total = 0;
    for (const org of this.availableOrganismes()) {
      total += this.getOrgBudget(yearIdx, org.id_organisme).etp || 0;
    }
    return total;
  }

  // ════════════════════════════════════════════════
  // Programmation annuelle (OperationAnnee[])
  // ════════════════════════════════════════════════

  togglePeriodicite(index: number): void {
    const annee = this.operationAnnees[index];
    annee.periodicite = !annee.periodicite;
    if (!annee.periodicite) {
      // #425 — décocher la programmation d'une année doit remettre à zéro le
      // budget et la RH de cette colonne, quel que soit le mode de ventilation.
      this.clearYearBudget(index);
    }
  }

  /**
   * #425 — Réinitialise toutes les saisies budget/RH d'une année (tous modes de
   * ventilation confondus). Appelé quand on décoche la programmation de l'année.
   */
  private clearYearBudget(index: number): void {
    const annee = this.operationAnnees[index];
    if (annee) {
      annee.budget = null;
      annee.etp = null;
    }
    this.directTotals[index] = { budget: null, etp: null };
    this.typeBudgets[index] = { fonct: null, invest: null, etp: null };
    for (const org of this.availableOrganismes()) {
      const key = this.orgKey(index, org.id_organisme);
      this.orgBudgets[key] = { fonct: null, invest: null, etp: null };
      this.orgByOrgData[key] = { budget: null, etp: null };
    }
  }

  /**
   * #374 — Une année dont la périodicité n'est pas cochée n'est pas programmée :
   * on grise et on verrouille la saisie de budget / ETP de cette colonne.
   */
  isYearLocked(index: number): boolean {
    return !this.operationAnnees[index]?.periodicite;
  }

  updateBudget(index: number, value: string): void {
    this.operationAnnees[index].budget = this.parseDecimal(value);
  }

  /**
   * #374 — Ouvre la modale « Appliquer aux années » : l'utilisateur choisit
   * l'année et le mois de départ, prévisualise les occurrences calculées selon
   * la fréquence, les ajuste si besoin, puis valide. La périodicité annuelle et
   * la périodicité mensuelle récurrente sont alors **remplacées** par la sélection.
   * (Remplace l'ancien auto-calcul `i % step` ancré à la 1re année du plan, qui
   * décalait les ronds — on ne devine plus l'ancrage.)
   */
  applyFrequencyToAnnees(): void {
    if (this.operationAnnees.length === 0) return;

    // Départ proposé par défaut : 1re année saisie (budget/ETP) ou déjà cochée, sinon la 1re.
    let defaultStartYearIndex = this.operationAnnees.findIndex((_, i) => this.anneeIndexHasData(i));
    if (defaultStartYearIndex < 0) {
      defaultStartYearIndex = this.operationAnnees.findIndex(a => a.periodicite);
    }
    if (defaultStartYearIndex < 0) defaultStartYearIndex = 0;

    // Mois de départ par défaut : 1er mois récurrent déjà coché, sinon janvier.
    let defaultStartMonth = 1;
    for (const m of this.months) {
      if (this.programmationMensuelleDefaut[m.toString()]) { defaultStartMonth = m; break; }
    }

    const ref = this.dialog.open(FrequencyApplyDialogComponent, {
      width: '640px',
      maxWidth: '95vw',
      data: {
        years: this.operationAnnees.map(a => a.annee),
        monthLabels: this.monthLabels,
        frequenceNombre: this.form.get('frequence_nombre')?.value ?? null,
        frequenceUnite: this.form.get('frequence_unite')?.value ?? null,
        defaultStartYearIndex,
        defaultStartMonth,
      },
    });

    ref.afterClosed().subscribe((result: FrequencyApplyDialogResult | null) => {
      if (!result) return;
      // Remplace la périodicité annuelle.
      this.operationAnnees.forEach((annee, i) => {
        annee.periodicite = !!result.yearFlags[i];
      });
      // Remplace la périodicité mensuelle récurrente (mêmes mois chaque année).
      this.programmationMensuelleDefaut = { ...result.monthFlags };
    });
  }

  /**
   * #374 — Une année est considérée « saisie » si un budget ou un nombre de jours
   * (ETP) y a été renseigné, quel que soit le mode de ventilation (direct, par
   * organisme, par type, par organisme+type).
   */
  private anneeIndexHasData(i: number): boolean {
    const dt = this.directTotals[i];
    if (dt && (dt.budget != null || dt.etp != null)) return true;
    const tb = this.typeBudgets[i];
    if (tb && (tb.fonct != null || tb.invest != null || tb.etp != null)) return true;
    const oa = this.operationAnnees[i];
    if (oa && (oa.budget != null || oa.etp != null || oa.budget_fonctionnement != null || oa.budget_investissement != null)) return true;
    for (const org of this.availableOrganismes()) {
      const key = this.orgKey(i, org.id_organisme);
      const ob = this.orgBudgets[key];
      if (ob && (ob.fonct != null || ob.invest != null || ob.etp != null)) return true;
      const obo = this.orgByOrgData[key];
      if (obo && (obo.budget != null || obo.etp != null)) return true;
    }
    return false;
  }

  updateEtp(index: number, value: string): void {
    this.operationAnnees[index].etp = this.parseDecimal(value);
  }

  duplicateFirstColumn(): void {
    if (this.operationAnnees.length < 2) return;
    const first = this.operationAnnees[0];
    for (let i = 1; i < this.operationAnnees.length; i++) {
      this.operationAnnees[i] = {
        ...this.operationAnnees[i],
        periodicite: first.periodicite,
        budget: first.budget,
        etp: first.etp,
        periodicite_mensuelle: { ...first.periodicite_mensuelle }
      };
      // Duplicate per-organisme data
      for (const org of this.availableOrganismes()) {
        const srcData = this.getOrgBudget(0, org.id_organisme);
        this.orgBudgets[this.orgKey(i, org.id_organisme)] = { ...srcData };
      }
      // Duplicate direct totals / type budgets / org totals
      const mode = this.ventilationMode();
      if (mode === 'none') {
        this.directTotals[i] = { ...this.getDirectTotal(0) };
      } else if (mode === 'by_type') {
        this.typeBudgets[i] = { ...this.getTypeBudget(0) };
      } else if (mode === 'by_org') {
        for (const org of this.availableOrganismes()) {
          this.orgByOrgData[`${i}-${org.id_organisme}`] = { ...this.getOrgByOrgData(0, org.id_organisme) };
        }
      }
    }
  }

  // ════════════════════════════════════════════════
  // Mode totaux directs
  // ════════════════════════════════════════════════

  /** Parse une valeur décimale en acceptant la virgule comme séparateur. */
  private parseDecimal(value: string): number | null {
    if (!value) return null;
    // Supprimer les espaces (séparateurs de milliers) avant de parser
    const normalized = String(value).replace(/\s/g, '').replace(',', '.');
    const parsed = parseFloat(normalized);
    return isNaN(parsed) ? null : parsed;
  }

  formatBudget(value: number | null): string {
    if (value == null) return '';
    return value.toLocaleString('fr-FR');
  }

  onModeToggle(mode: string): void {
    this.ventilationMode.set(mode as 'none' | 'by_org' | 'by_type' | 'by_org_type');
  }

  getDirectTotal(yearIdx: number): { budget: number | null; etp: number | null } {
    if (!this.directTotals[yearIdx]) {
      this.directTotals[yearIdx] = { budget: null, etp: null };
    }
    return this.directTotals[yearIdx];
  }

  updateDirectBudget(yearIdx: number, value: string): void {
    this.getDirectTotal(yearIdx).budget = this.parseDecimal(value);
    this.autoCheckPeriodicite(yearIdx);
  }

  updateDirectEtp(yearIdx: number, value: string): void {
    this.getDirectTotal(yearIdx).etp = this.parseDecimal(value);
    this.autoCheckPeriodicite(yearIdx);
  }

  // ════════════════════════════════════════════════
  // Mode 'by_type' helpers (ventilation par type budget global)
  // ════════════════════════════════════════════════

  getTypeBudget(yearIdx: number): { fonct: number | null; invest: number | null; etp: number | null } {
    if (!this.typeBudgets[yearIdx]) {
      this.typeBudgets[yearIdx] = { fonct: null, invest: null, etp: null };
    }
    return this.typeBudgets[yearIdx];
  }

  updateTypeFonct(yearIdx: number, value: string): void {
    this.getTypeBudget(yearIdx).fonct = this.parseDecimal(value);
    this.autoCheckPeriodicite(yearIdx);
  }

  updateTypeInvest(yearIdx: number, value: string): void {
    this.getTypeBudget(yearIdx).invest = this.parseDecimal(value);
    this.autoCheckPeriodicite(yearIdx);
  }

  updateTypeEtp(yearIdx: number, value: string): void {
    this.getTypeBudget(yearIdx).etp = this.parseDecimal(value);
    this.autoCheckPeriodicite(yearIdx);
  }

  // ════════════════════════════════════════════════
  // Mode 'by_org' helpers (ventilation par organisme, totaux)
  // ════════════════════════════════════════════════

  getOrgByOrgData(yearIdx: number, orgId: number): { budget: number | null; etp: number | null } {
    const key = `${yearIdx}-${orgId}`;
    if (!this.orgByOrgData[key]) {
      this.orgByOrgData[key] = { budget: null, etp: null };
    }
    return this.orgByOrgData[key];
  }

  /**
   * #245 — Autococher la périodicité dès qu'un budget ou un ETP est saisi
   * pour une année donnée. Sophie : « si la ligne porte du budget ou des
   * RH, c'est qu'elle est active — ne pas obliger l'utilisateur à cocher
   * la case en plus ». Ne décoche jamais : seule l'action explicite sur
   * la case (cf. `toggleAnneePeriodicite`) peut la repasser à false.
   */
  private autoCheckPeriodicite(yearIdx: number): void {
    const annee = this.operationAnnees[yearIdx];
    if (!annee) return;
    if (annee.periodicite) return; // déjà cochée — pas besoin
    if (this.yearHasAnyAmount(yearIdx)) {
      annee.periodicite = true;
    }
  }

  /** Vrai si l'année a au moins une valeur budget/ETP renseignée
   *  (toutes ventilations confondues : direct, by_type, by_org). */
  private yearHasAnyAmount(yearIdx: number): boolean {
    const direct = this.directTotals[yearIdx];
    if (direct && ((direct.budget ?? 0) > 0 || (direct.etp ?? 0) > 0)) return true;
    const type = this.typeBudgets[yearIdx];
    if (type && ((type.fonct ?? 0) > 0 || (type.invest ?? 0) > 0 || (type.etp ?? 0) > 0)) return true;
    for (const key of Object.keys(this.orgBudgets)) {
      if (!key.startsWith(`${yearIdx}-`)) continue;
      const b = this.orgBudgets[key];
      if ((b.fonct ?? 0) > 0 || (b.invest ?? 0) > 0 || (b.etp ?? 0) > 0) return true;
    }
    for (const key of Object.keys(this.orgByOrgData)) {
      if (!key.startsWith(`${yearIdx}-`)) continue;
      const d = this.orgByOrgData[key];
      if ((d.budget ?? 0) > 0 || (d.etp ?? 0) > 0) return true;
    }
    return false;
  }

  updateOrgByOrgBudget(yearIdx: number, orgId: number, value: string): void {
    this.getOrgByOrgData(yearIdx, orgId).budget = this.parseDecimal(value);
    this.autoCheckPeriodicite(yearIdx);
  }

  updateOrgByOrgEtp(yearIdx: number, orgId: number, value: string): void {
    this.getOrgByOrgData(yearIdx, orgId).etp = this.parseDecimal(value);
    this.autoCheckPeriodicite(yearIdx);
  }

  getByOrgYearTotalBudget(yearIdx: number): number {
    let total = 0;
    for (const org of this.availableOrganismes()) {
      total += this.getOrgByOrgData(yearIdx, org.id_organisme).budget || 0;
    }
    return total;
  }

  getByOrgYearTotalEtp(yearIdx: number): number {
    let total = 0;
    for (const org of this.availableOrganismes()) {
      total += this.getOrgByOrgData(yearIdx, org.id_organisme).etp || 0;
    }
    return total;
  }

  // ════════════════════════════════════════════════
  // Programmation mensuelle (template unique pour toutes les années)
  // ════════════════════════════════════════════════

  toggleMensuelleDefaut(month: string): void {
    this.programmationMensuelleDefaut[month] = !this.programmationMensuelleDefaut[month];
  }

  // ════════════════════════════════════════════════
  // Finances
  // ════════════════════════════════════════════════

  addFinance(): void {
    this.finances.push({ libelle: '', id_categorie: null });
  }

  removeFinance(index: number): void {
    this.finances.splice(index, 1);
  }

  // ════════════════════════════════════════════════
  // Fréquence
  // ════════════════════════════════════════════════

  incrementFrequence(): void {
    const current = this.form.get('frequence_nombre')?.value || 0;
    this.form.patchValue({ frequence_nombre: current + 1 });
  }

  decrementFrequence(): void {
    const current = this.form.get('frequence_nombre')?.value || 0;
    if (current > 1) {
      this.form.patchValue({ frequence_nombre: current - 1 });
    }
  }
}
