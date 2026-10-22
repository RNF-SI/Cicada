/**
 * Bloc protocole de la fiche action (#732) : recherche CAMPanule (#584) et
 * bascule « protocole standardisé ? » (#520), propres à chaque protocole.
 */
import { signal } from '@angular/core';
import { FormControl, FormGroup } from '@angular/forms';
import { of, throwError } from 'rxjs';
import { ProtocoleActionComponent } from './protocole-action.component';

function groupe(valeurs: Record<string, unknown> = {}): FormGroup {
  return new FormGroup({
    protocole_dans_campanule: new FormControl(valeurs['protocole_dans_campanule'] ?? false),
    protocole_campanule_nom: new FormControl(valeurs['protocole_campanule_nom'] ?? ''),
    cd_protocole_campanule: new FormControl(valeurs['cd_protocole_campanule'] ?? null),
    description_protocole: new FormControl(valeurs['description_protocole'] ?? ''),
    objectif_protocole: new FormControl(valeurs['objectif_protocole'] ?? ''),
    periode_echantillonnage: new FormControl(valeurs['periode_echantillonnage'] ?? ''),
    respect_protocole: new FormControl(null),
  });
}

function makeComp(g: FormGroup = groupe()): ProtocoleActionComponent {
  const comp = Object.create(ProtocoleActionComponent.prototype) as ProtocoleActionComponent;
  comp.group = g;
  (comp as any).campanuleSearchCtrl = new FormControl('');
  (comp as any).campanuleResults = signal<unknown[]>([]);
  (comp as any).selectedCampanule = signal<unknown>(null);
  (comp as any).manualProtocoleSnapshot = null;
  (comp as any).campanuleSnapshot = null;
  return comp;
}

describe('ProtocoleActionComponent — #584 onCampanuleFocus', () => {
  function avecService(searchValue: string, results: unknown[]) {
    const comp = makeComp();
    const autocomplete = jest.fn().mockReturnValue(of([
      { cd_protocole: 1, lb_protocole_court: 'Aile de papillon' },
      { cd_protocole: 2, lb_protocole_court: 'Comptage oiseaux' },
    ]));
    comp.campanuleSearchCtrl.setValue(searchValue);
    comp.campanuleResults.set(results as any);
    (comp as any).campanuleService = { autocomplete };
    return { comp, autocomplete };
  }

  it('charge la liste par défaut quand le champ est vide et qu\'aucun résultat n\'est affiché', () => {
    const { comp, autocomplete } = avecService('', []);
    comp.onCampanuleFocus();
    expect(autocomplete).toHaveBeenCalledWith('', 100);
    expect(comp.campanuleResults().length).toBe(2);
  });

  it('ne recharge rien si un terme est déjà saisi', () => {
    const { comp, autocomplete } = avecService('oiseaux', []);
    comp.onCampanuleFocus();
    expect(autocomplete).not.toHaveBeenCalled();
  });

  it('ne recharge rien si des résultats sont déjà affichés', () => {
    const { comp, autocomplete } = avecService('', [{ cd_protocole: 9 }]);
    comp.onCampanuleFocus();
    expect(autocomplete).not.toHaveBeenCalled();
  });

  it('vide la liste en cas d\'erreur API', () => {
    const { comp } = avecService('', []);
    (comp as any).campanuleService = { autocomplete: () => throwError(() => new Error('boom')) };
    comp.onCampanuleFocus();
    expect(comp.campanuleResults()).toEqual([]);
  });
});

describe('ProtocoleActionComponent — #520 onProtocoleCampanuleChange', () => {
  function avecSelection(): ProtocoleActionComponent {
    const comp = makeComp(groupe({
      protocole_dans_campanule: false,
      protocole_campanule_nom: 'Proto X',
      cd_protocole_campanule: 42,
      description_protocole: 'Description issue de CAMPanule',
      objectif_protocole: 'Objectif CAMPanule',
      periode_echantillonnage: 'Mai; Juin',
    }));
    comp.selectedCampanule.set({ cd_protocole: 42, lb_protocole_court: 'Proto X' } as any);
    comp.campanuleSearchCtrl.setValue('Proto X');
    return comp;
  }

  it('vide les champs auto-remplis et la sélection CAMPanule au changement de choix', () => {
    const c = avecSelection();
    c.onProtocoleCampanuleChange();
    const g = c.group;
    expect(g.get('description_protocole')?.value).toBe('');
    expect(g.get('objectif_protocole')?.value).toBe('');
    expect(g.get('periode_echantillonnage')?.value).toBe('');
    expect(g.get('protocole_campanule_nom')?.value).toBe('');
    expect(g.get('cd_protocole_campanule')?.value).toBeNull();
    expect(c.selectedCampanule()).toBeNull();
    expect(c.campanuleSearchCtrl.value).toBe('');
  });

  it('préserve la saisie manuelle après un aller-retour Non → Oui → Non', () => {
    const c = makeComp();
    const g = c.group;
    (c as any).campanuleService = { autocomplete: () => of([]) };
    g.patchValue({
      description_protocole: 'Ma description perso',
      objectif_protocole: 'Mon objectif perso',
      periode_echantillonnage: 'Avril; Mai',
    });

    g.get('protocole_dans_campanule')?.setValue(true);
    c.onProtocoleCampanuleChange();
    expect(g.get('description_protocole')?.value).toBe('');

    g.get('protocole_dans_campanule')?.setValue(false);
    c.onProtocoleCampanuleChange();
    expect(g.get('description_protocole')?.value).toBe('Ma description perso');
    expect(g.get('objectif_protocole')?.value).toBe('Mon objectif perso');
    expect(g.get('periode_echantillonnage')?.value).toBe('Avril; Mai');
  });

  it('restaure la sélection CAMPanule après un aller-retour Oui → Non → Oui', () => {
    const c = avecSelection();
    const g = c.group;
    g.get('protocole_dans_campanule')?.setValue(true);

    g.get('protocole_dans_campanule')?.setValue(false);
    c.onProtocoleCampanuleChange();
    expect(g.get('cd_protocole_campanule')?.value).toBeNull();
    expect(c.selectedCampanule()).toBeNull();

    g.get('protocole_dans_campanule')?.setValue(true);
    c.onProtocoleCampanuleChange();
    expect(g.get('cd_protocole_campanule')?.value).toBe(42);
    expect(g.get('protocole_campanule_nom')?.value).toBe('Proto X');
    expect(g.get('description_protocole')?.value).toBe('Description issue de CAMPanule');
    expect(c.selectedCampanule()).toEqual({ cd_protocole: 42, lb_protocole_court: 'Proto X' });
  });
});
