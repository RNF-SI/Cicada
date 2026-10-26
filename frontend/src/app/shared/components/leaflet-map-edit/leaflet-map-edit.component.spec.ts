/**
 * #687 — import d'un fichier géographique sur la carte.
 *
 * On teste `onGeometryFileSelected` sans monter la carte Leaflet (jsdom n'a
 * pas de rendu) : composant instancié « à la main », snackbar et traduction
 * remplacés, `processImportedGeometry` espionné.
 */
import { signal } from '@angular/core';
import { LeafletMapEditComponent } from './leaflet-map-edit.component';

function fakeFile(name: string, content: string | ArrayBuffer) {
  const buffer = typeof content === 'string' ? new TextEncoder().encode(content).buffer : content;
  return {
    name,
    text: async () => (typeof content === 'string' ? content : ''),
    arrayBuffer: async () => buffer,
  };
}

function setup() {
  const comp = Object.create(LeafletMapEditComponent.prototype) as LeafletMapEditComponent;
  const snack = { open: jest.fn() };
  (comp as any).snackBar = snack;
  (comp as any).translate = {
    instant: (key: string, params?: Record<string, unknown>) =>
      params ? `${key}:${JSON.stringify(params)}` : key,
  };
  (comp as any).isImporting = signal(false);
  const process = jest.fn();
  (comp as any).processImportedGeometry = process;
  return { comp, snack, process };
}

async function importer(comp: LeafletMapEditComponent, file: unknown) {
  await comp.onGeometryFileSelected({ target: { files: [file], value: 'x' } } as any);
}

/** Archive .zip minimale (fichiers vides) avec ces noms. */
function zip(noms: string[]): ArrayBuffer {
  const enc = new TextEncoder();
  const centraux = noms.map((nom) => {
    const n = enc.encode(nom);
    const c = new Uint8Array(46 + n.length);
    const v = new DataView(c.buffer);
    v.setUint32(0, 0x02014b50, true);
    v.setUint16(28, n.length, true);
    c.set(n, 46);
    return c;
  });
  const taille = centraux.reduce((t, c) => t + c.length, 0);
  const fin = new Uint8Array(22);
  const fv = new DataView(fin.buffer);
  fv.setUint32(0, 0x06054b50, true);
  fv.setUint16(10, noms.length, true);
  fv.setUint32(12, taille, true);
  fv.setUint32(16, 0, true);
  const total = new Uint8Array(taille + 22);
  let pos = 0;
  for (const part of [...centraux, fin]) { total.set(part, pos); pos += part.length; }
  return total.buffer;
}

const carre = (x: number, y: number, d = 0.01) => JSON.stringify({
  type: 'Feature', properties: {},
  geometry: { type: 'Polygon', coordinates: [[[x, y], [x, y + d], [x + d, y + d], [x + d, y], [x, y]]] },
});

describe('LeafletMapEditComponent — import de fichier (#687)', () => {
  it('refuse un .shp seul : sans .prj, la projection est inconnue', async () => {
    const { comp, snack, process } = setup();
    await importer(comp, fakeFile('site.shp', new ArrayBuffer(8)));
    expect(snack.open).toHaveBeenCalledWith(
      'sites.form.geometry.import.invalidFormat', expect.anything(), expect.anything());
    expect(process).not.toHaveBeenCalled();
  });

  it('refuse un .zip sans .prj en nommant le fichier manquant', async () => {
    const { comp, snack, process } = setup();
    await importer(comp, fakeFile('site.zip', zip(['site.shp', 'site.shx', 'site.dbf'])));
    expect(snack.open).toHaveBeenCalledWith(
      'sites.form.geometry.import.missingFiles:{"fichiers":".prj"}',
      expect.anything(), expect.anything());
    expect(process).not.toHaveBeenCalled();
  });

  it('refuse un GeoJSON en mètres avec un message dédié', async () => {
    const { comp, snack, process } = setup();
    await importer(comp, fakeFile('site.geojson', carre(652000, 6862000, 500)));
    expect(snack.open).toHaveBeenCalledWith(
      'sites.form.geometry.import.notWgs84', expect.anything(), expect.anything());
    expect(process).not.toHaveBeenCalled();
  });

  it('importe un GeoJSON d\'outre-mer en WGS 84', async () => {
    const { comp, process } = setup();
    await importer(comp, fakeFile('reunion.geojson', carre(55.5, -21.1)));
    expect(process).toHaveBeenCalled();
  });
});

// #768 — les outils de dessin restaient en anglais (« Draw a polygon », « Finish ») :
// leaflet-draw pose ses textes sur `window.L`, pas sur le module importé.
describe('LeafletMapEditComponent — textes des outils de dessin (#768)', () => {
  const avant = (window as any).L;
  afterEach(() => { (window as any).L = avant; });

  it('traduit les outils de leaflet-draw posés sur window.L', () => {
    const drawLocal = {
      draw: { toolbar: { buttons: { polygon: 'Draw a polygon' }, finish: { text: 'Finish' } }, handlers: {} },
      edit: { toolbar: { buttons: { edit: 'Edit layers', editDisabled: 'No layers to edit', remove: 'Delete layers', removeDisabled: 'No layers to delete' } }, handlers: {} },
    };
    (window as any).L = { drawLocal };
    const comp = Object.create(LeafletMapEditComponent.prototype) as any;
    comp.configureDrawLocale();
    expect(drawLocal.draw.toolbar.buttons.polygon).toBe('Tracer un contour');
    expect(drawLocal.draw.toolbar.finish.text).toBe('Terminer');
    expect(drawLocal.edit.toolbar.buttons.edit).toBe('Modifier le contour');
    expect(drawLocal.edit.toolbar.buttons.editDisabled).toBe('Aucun contour à modifier : tracez-en un d\'abord');
    expect(drawLocal.edit.toolbar.buttons.remove).toBe('Supprimer le contour');
  });
});
