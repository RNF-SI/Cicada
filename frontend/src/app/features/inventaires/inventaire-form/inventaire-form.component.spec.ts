/**
 * Tests unitaires pour InventaireFormComponent — protocoles multiples (#252).
 *
 * On teste la logique métier (FormArray, validators conditionnels par bloc,
 * sérialisation du payload) sans monter le composant complet : comme pour
 * OperationFormComponent, les dépendances de template sont trop nombreuses.
 */
import { TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { FormBuilder } from '@angular/forms';
import { of } from 'rxjs';

import { InventaireFormComponent } from './inventaire-form.component';

/** Instancie le composant "à la main", avec le strict nécessaire au FormArray. */
function createComponentInstance(): InventaireFormComponent {
  const comp = Object.create(InventaireFormComponent.prototype) as InventaireFormComponent;

  (comp as any).fb = TestBed.inject(FormBuilder);
  (comp as any).translate = {
    instant: (key: string, params?: Record<string, unknown>) =>
      params ? `${key}:${JSON.stringify(params)}` : key,
  };
  // L'autocomplete CAMPanule est branché à chaque addProtocole().
  (comp as any).campanuleService = { autocomplete: () => of([]), getProtocole: () => of({}) };

  // `Object.create` n'exécute pas les initialiseurs de champs : on reproduit
  // les signaux et constantes utilisés par la logique testée.
  comp.campanuleSearchCtrls = [];
  (comp as any).campanuleSubs = [];
  (comp as any).campanuleResults = signal<any[]>([]);
  (comp as any).selectedCampanules = signal<any[]>([]);
  (comp as any).protocolesSoftLimit = 3;

  (comp as any).initForm();
  return comp;
}

describe('InventaireFormComponent — protocoles multiples (#252)', () => {
  let comp: InventaireFormComponent;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    comp = createComponentInstance();
  });

  it('démarre avec un seul protocole (cas majoritaire)', () => {
    expect(comp.protocolesArray.length).toBe(1);
    expect(comp.campanuleSearchCtrls.length).toBe(1);
  });

  it('ajoute un protocole avec son propre état d\'autocomplete CAMPanule', () => {
    comp.addProtocole();

    expect(comp.protocolesArray.length).toBe(2);
    expect(comp.campanuleSearchCtrls.length).toBe(2);
    expect(comp.campanuleResults().length).toBe(2);
    expect(comp.selectedCampanules().length).toBe(2);
    // Les contrôles de recherche sont bien distincts.
    expect(comp.campanuleSearchCtrls[0]).not.toBe(comp.campanuleSearchCtrls[1]);
  });

  it('retire un protocole et son état associé', () => {
    comp.addProtocole();
    comp.protocolesArray.at(0).patchValue({ nom_protocole: 'Premier' });
    comp.protocolesArray.at(1).patchValue({ nom_protocole: 'Second' });

    comp.removeProtocole(0);

    expect(comp.protocolesArray.length).toBe(1);
    expect(comp.campanuleSearchCtrls.length).toBe(1);
    expect(comp.protocolesArray.at(0).get('nom_protocole')?.value).toBe('Second');
  });

  it('ne supprime jamais le dernier protocole', () => {
    comp.removeProtocole(0);
    expect(comp.protocolesArray.length).toBe(1);
  });

  it('applique les validators conditionnels bloc par bloc', () => {
    comp.addProtocole();
    // Bloc 0 : CAMPanule → cd_protocole_campanule requis, nb_etp_cycle non.
    comp.protocolesArray.at(0).patchValue({ protocole_dans_campanule: true });
    // Bloc 1 : hors CAMPanule → nb_etp_cycle requis, cd_protocole_campanule non.
    comp.protocolesArray.at(1).patchValue({ protocole_dans_campanule: false });
    (comp as any).syncConditionalValidators();

    const bloc0 = comp.protocolesArray.at(0);
    const bloc1 = comp.protocolesArray.at(1);

    expect(bloc0.get('cd_protocole_campanule')?.hasError('required')).toBe(true);
    expect(bloc0.get('nb_etp_cycle')?.hasError('required')).toBe(false);

    expect(bloc1.get('nb_etp_cycle')?.hasError('required')).toBe(true);
    expect(bloc1.get('cd_protocole_campanule')?.hasError('required')).toBe(false);
  });

  it('rend la fréquence requise dès qu\'un protocole est renseigné', () => {
    expect(comp.form.get('frequence_nombre')?.hasError('required')).toBe(false);

    comp.protocolesArray.at(0).patchValue({ protocole_dans_campanule: false });
    (comp as any).syncConditionalValidators();

    expect(comp.form.get('frequence_nombre')?.hasError('required')).toBe(true);
    expect(comp.form.get('frequence_unite')?.hasError('required')).toBe(true);
  });

  it('sérialise chaque protocole, en joignant periode_suivi', () => {
    comp.addProtocole();
    comp.protocolesArray.at(0).patchValue({
      protocole_dans_campanule: true,
      protocole_campanule_nom: 'STOC-EPS',
      cd_protocole_campanule: 42,
      respect_protocole: true,
    });
    comp.protocolesArray.at(1).patchValue({
      protocole_dans_campanule: false,
      nom_protocole: 'IPA',
      nb_etp_cycle: 1.5,
      periode_suivi: ['AVRIL', 'MAI'],
    });

    const payloads = comp.protocolesArray.value.map((pv: any) =>
      (comp as any).buildProtocolePayload(pv),
    );

    expect(payloads).toHaveLength(2);
    expect(payloads[0]).toMatchObject({
      protocole_dans_campanule: true,
      protocole_campanule_nom: 'STOC-EPS',
      cd_protocole_campanule: 42,
      respect_protocole: true,
    });
    expect(payloads[1]).toMatchObject({
      protocole_dans_campanule: false,
      nom_protocole: 'IPA',
      nb_etp_cycle: 1.5,
      periode_suivi: 'AVRIL,MAI',
    });
  });

  it('n\'envoie pas url_documentation quand la documentation est absente', () => {
    comp.protocolesArray.at(0).patchValue({
      protocole_dans_campanule: false,
      documentation_disponible: false,
      url_documentation: 'https://exemple.fr/doc.pdf',
    });

    const payload = (comp as any).buildProtocolePayload(comp.protocolesArray.at(0).value);

    expect(payload['documentation_disponible']).toBe(false);
    expect(payload['url_documentation']).toBeUndefined();
  });

  it('affiche le nom du protocole en titre, sinon un libellé indexé', () => {
    comp.addProtocole();
    comp.protocolesArray.at(0).patchValue({ nom_protocole: 'Points d\'écoute' });

    expect(comp.protocoleTitle(0)).toBe('Points d\'écoute');
    expect(comp.protocoleTitle(1)).toContain('inventaires.form.protocoleIndex');
  });

  it('signale le dépassement du seuil de lisibilité au-delà de 3 protocoles', () => {
    expect(comp.showProtocolesSoftLimitHint).toBe(false);
    comp.addProtocole();
    comp.addProtocole();
    expect(comp.showProtocolesSoftLimitHint).toBe(false);
    comp.addProtocole();
    expect(comp.showProtocolesSoftLimitHint).toBe(true);
  });
});
