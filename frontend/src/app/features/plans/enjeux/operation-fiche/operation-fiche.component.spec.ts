/**
 * Tests unitaires — OperationFicheComponent (#516).
 *
 * Régression couverte : dans la fiche d'action, les métriques « en blocs » des
 * indicateurs État/Pression n'apparaissaient pas (seul leur nom était listé en
 * texte), alors que les indicateurs de réponse affichaient bien leur grille.
 * On vérifie ici que la fiche rend une grille (`app-metrique-grid-display`) pour
 * TOUS les indicateurs liés — réponse ET état/pression — et donc leurs blocs.
 */
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { of } from 'rxjs';

import { OperationFicheComponent } from './operation-fiche.component';
import { EnjeuService } from '../../../../core/services/enjeu.service';
import { Operation } from '../../../../core/models/enjeu.model';

/** Métrique NUMERIQUE en grille avec 1 bloc complémentaire (ET/OU). */
function multiBlockMetrique(over: Record<string, unknown>): any {
  return {
    id_metrique: 1,
    nom_metrique: 'Métrique',
    type_metrique_mnemonique: 'NUMERIQUE',
    format_metrique_mnemonique: 'GRILLE',
    bloc_intitule: 'Bloc principal',
    unite: 'u',
    score_1_inf: 0, score_1_sup: 10,
    score_2_inf: 10, score_2_sup: 20,
    score_blocks: [
      {
        id_score_block: 9, position: 1, intitule: 'Bloc secondaire', unite: 'v',
        logical_op: 'OR', group_open: 0, group_close: 0, sens_variation: 'CROISSANT',
        score_1_inf: 0, score_1_sup: 5, score_2_inf: 5, score_2_sup: 10,
      },
    ],
    ...over,
  };
}

function operationWith(metriques: any[]): Operation {
  return {
    id_operation: 42,
    libelle: 'Action test',
    metriques,
    operation_annees: [],
    finances: [],
  } as unknown as Operation;
}

function setup(
  op: Operation,
  opts: { from?: string; fromEnjeu?: string; router?: { navigate: jest.Mock } } = {},
): ComponentFixture<OperationFicheComponent> {
  const enjeuService = { getOperation: jest.fn().mockReturnValue(of(op)) };
  const queryParamMap = new Map<string, string>();
  if (opts.from) queryParamMap.set('from', opts.from);
  if (opts.fromEnjeu) queryParamMap.set('fromEnjeu', opts.fromEnjeu);
  const route = {
    snapshot: {
      paramMap: new Map<string, string>([['operationId', '42'], ['slug', 'plan-x']]),
      queryParamMap,
    },
    parent: null,
  };
  // Map#get already matches ParamMap.get signature for our usage.
  TestBed.configureTestingModule({
    imports: [OperationFicheComponent, NoopAnimationsModule, TranslateModule.forRoot()],
    providers: [
      { provide: EnjeuService, useValue: enjeuService },
      { provide: ActivatedRoute, useValue: route },
      { provide: Router, useValue: opts.router ?? { navigate: jest.fn() } },
    ],
  });
  const fixture = TestBed.createComponent(OperationFicheComponent);
  fixture.detectChanges();
  return fixture;
}

describe('OperationFicheComponent — grilles/blocs des indicateurs (#516)', () => {
  it('sépare les indicateurs de réponse des indicateurs état/pression', () => {
    const fixture = setup(operationWith([
      multiBlockMetrique({ id_metrique: 1, indicateur_id: 100, indicateur_nom: 'Rép', indicateur_type: 'REPONSE' }),
      multiBlockMetrique({ id_metrique: 2, indicateur_id: 200, indicateur_nom: 'Pres', indicateur_type: 'PRESSION' }),
    ]));
    const c = fixture.componentInstance;
    expect(c.indicateursReponse().map(i => i.id)).toEqual([100]);
    expect(c.indicateursEtatPression().map(i => i.id)).toEqual([200]);
  });

  it('rend une grille de métriques pour l\'indicateur de réponse ET pour l\'état/pression', () => {
    const fixture = setup(operationWith([
      multiBlockMetrique({ id_metrique: 1, indicateur_id: 100, indicateur_nom: 'Rép', indicateur_type: 'REPONSE' }),
      multiBlockMetrique({ id_metrique: 2, indicateur_id: 200, indicateur_nom: 'Pres', indicateur_type: 'PRESSION' }),
    ]));
    const grids = fixture.nativeElement.querySelectorAll('app-metrique-grid-display');
    // Régression #516 : avant le correctif, l'état/pression n'avait pas de grille
    // (une seule grille au lieu de deux).
    expect(grids.length).toBe(2);
  });

  it('affiche les blocs (ET/OU) d\'une métrique état/pression dans sa grille', () => {
    const fixture = setup(operationWith([
      multiBlockMetrique({ id_metrique: 2, indicateur_id: 200, indicateur_nom: 'Pres', indicateur_type: 'PRESSION' }),
    ]));
    const text: string = fixture.nativeElement.textContent;
    // Les cellules multi-blocs listent chaque bloc (intitulé) — trace visible d'un « bloc ».
    expect(text).toContain('Bloc principal');
    expect(text).toContain('Bloc secondaire');
  });
});

describe('OperationFicheComponent — personnalisation des sections de l\'export (#532)', () => {
  it('affiche toutes les sections par défaut (toutes cochées)', () => {
    const fixture = setup(operationWith([]));
    const c = fixture.componentInstance;
    expect(c.toggleableSections.every(s => c.sectionVisible(s.key))).toBe(true);
    // La section « Réalisation » (toujours présente) est rendue.
    expect(fixture.nativeElement.textContent).toContain('plans.suivis.actions.fiche.realisationGlobale');
  });

  it('retire du DOM une section décochée', () => {
    const fixture = setup(operationWith([]));
    const c = fixture.componentInstance;
    c.setSectionVisible('realisation', false);
    fixture.detectChanges();
    expect(c.sectionVisible('realisation')).toBe(false);
    expect(fixture.nativeElement.textContent).not.toContain('plans.suivis.actions.fiche.realisationGlobale');
  });

  it('n\'affiche le panneau de choix des sections qu\'après ouverture', () => {
    const fixture = setup(operationWith([]));
    const c = fixture.componentInstance;
    expect(fixture.nativeElement.querySelector('.fiche-section-picker')).toBeNull();
    c.toggleSectionPicker();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.fiche-section-picker')).not.toBeNull();
  });
});

describe('OperationFicheComponent — bouton retour vers la page d\'origine (#529, #531)', () => {
  it('retourne à la position de l\'action dans l\'architecture quand from=enjeux + fromEnjeu', () => {
    const router = { navigate: jest.fn() };
    const fixture = setup(operationWith([]), { from: 'enjeux', fromEnjeu: 'mon-enjeu', router });
    fixture.componentInstance.goBack();
    // #531 — op mock : id_operation = 42 → query param `expandOperation` que la
    // liste décode pour ouvrir le bon onglet, déplier l'OLT/OO et scroller.
    expect(router.navigate).toHaveBeenCalledWith(
      ['/plans', 'plan-x', 'enjeux', 'mon-enjeu'],
      { queryParams: { expandOperation: 42 } },
    );
  });

  it('retourne à la liste des enjeux quand from=enjeux sans fromEnjeu', () => {
    const router = { navigate: jest.fn() };
    const fixture = setup(operationWith([]), { from: 'enjeux', router });
    fixture.componentInstance.goBack();
    expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-x', 'enjeux']);
  });

  it('retourne au suivi des actions quand from=suivi', () => {
    const router = { navigate: jest.fn() };
    const fixture = setup(operationWith([]), { from: 'suivi', router });
    fixture.componentInstance.goBack();
    expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-x', 'suivi-actions']);
  });

  it('retourne au suivi des actions par défaut (aucun from)', () => {
    const router = { navigate: jest.fn() };
    const fixture = setup(operationWith([]), { router });
    fixture.componentInstance.goBack();
    expect(router.navigate).toHaveBeenCalledWith(['/plans', 'plan-x', 'suivi-actions']);
  });
});
