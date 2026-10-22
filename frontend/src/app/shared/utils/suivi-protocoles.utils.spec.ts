import { Protocole } from '../../core/models/enjeu.model';
import { ProtocoleSaisiParAction, protocolesDepuisAction } from './suivi-protocoles.utils';

function saisi(overrides: Partial<ProtocoleSaisiParAction> = {}): ProtocoleSaisiParAction {
  return {
    id_protocole: null,
    protocole_dans_campanule: false,
    protocole_campanule_nom: '',
    cd_protocole_campanule: null,
    nb_etp_cycle: null,
    nom_protocole: '',
    respect_protocole: null,
    justification_non_respect: '',
    differences_protocole: '',
    description_protocole: '',
    objectif_protocole: '',
    periode_echantillonnage: '',
    ...overrides,
  };
}

describe('protocolesDepuisAction (#715, #732)', () => {
  const transect: Protocole = {
    id_protocole: 11,
    protocole_dans_campanule: false,
    nom_protocole: 'Transect local',
    periode_suivi: 'AVRIL,MAI',
    documentation_disponible: true,
    url_documentation: 'https://example.org/transect',
    date_ajout: '2026-10-01',
  };
  const ecoute: Protocole = { id_protocole: 12, protocole_dans_campanule: false, nom_protocole: "Points d'écoute" };

  it('nouveau suivi sans saisie : ne touche pas aux protocoles', () => {
    expect(protocolesDepuisAction([], [saisi({ protocole_dans_campanule: null })])).toBeUndefined();
  });

  it('nouveau suivi : envoie chaque protocole saisi, sans identifiant', () => {
    const res = protocolesDepuisAction([], [
      saisi({ nom_protocole: 'A' }),
      saisi({ protocole_dans_campanule: true, cd_protocole_campanule: 7, protocole_campanule_nom: 'IPA' }),
    ])!;
    expect(res.map((p) => p['nom_protocole'] || p['protocole_campanule_nom'])).toEqual(['A', 'IPA']);
    expect(res.every((p) => !('id_protocole' in p))).toBe(true);
  });

  it('ignore un bloc ajouté mais laissé vide', () => {
    const res = protocolesDepuisAction([], [saisi({ nom_protocole: 'A' }), saisi({ protocole_dans_campanule: null })])!;
    expect(res).toHaveLength(1);
  });

  it('chaque protocole existant garde les champs que la fiche action ne saisit pas', () => {
    const res = protocolesDepuisAction([transect, ecoute], [
      saisi({ id_protocole: 11, nom_protocole: 'Transect modifié' }),
      saisi({ id_protocole: 12, nom_protocole: "Points d'écoute" }),
    ])!;
    expect(res[0]).toMatchObject({
      nom_protocole: 'Transect modifié',
      periode_suivi: 'AVRIL,MAI',
      documentation_disponible: true,
      url_documentation: 'https://example.org/transect',
    });
    expect(res[0]).not.toHaveProperty('id_protocole');
    expect(res[0]).not.toHaveProperty('date_ajout');
    expect(res[1]['nom_protocole']).toBe("Points d'écoute");
  });

  it('retirer le premier protocole ne transfère pas ses champs au suivant', () => {
    const res = protocolesDepuisAction([transect, ecoute], [saisi({ id_protocole: 12, nom_protocole: "Points d'écoute" })])!;
    expect(res).toHaveLength(1);
    expect(res[0]['nom_protocole']).toBe("Points d'écoute");
    expect(res[0]).not.toHaveProperty('periode_suivi');
  });

  it('ajoute un protocole à un suivi existant', () => {
    const res = protocolesDepuisAction([transect], [
      saisi({ id_protocole: 11, nom_protocole: 'Transect local' }),
      saisi({ nom_protocole: 'Nouveau' }),
    ])!;
    expect(res.map((p) => p['nom_protocole'])).toEqual(['Transect local', 'Nouveau']);
    expect(res[0]['url_documentation']).toBe('https://example.org/transect');
  });

  it('tout retirer vide la liste du suivi existant', () => {
    expect(protocolesDepuisAction([transect], [])).toEqual([]);
  });
});
