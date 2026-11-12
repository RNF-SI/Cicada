import { popupTexte } from './leaflet-map.component';

describe('popupTexte — nom de site affiché sur la carte', () => {
  it('garde un nom piégé en texte : aucun élément ni gestionnaire n’est créé', () => {
    const piege = '<img src=x onerror="alert(1)">';
    const noeud = popupTexte(piege);

    expect(noeud.tagName).toBe('STRONG');
    expect(noeud.textContent).toBe(piege);
    expect(noeud.querySelector('img')).toBeNull();
    expect(noeud.innerHTML).toContain('&lt;img');
  });
});
