/**
 * #687 — contrôles d'un fichier géographique importé sur la carte.
 */
import {
  fichiersManquantsDuShapefile,
  horsWgs84,
  nomsFichiersZip,
} from './geometry-import.utils';

/** Archive .zip minimale (fichiers vides, sans compression) avec ces noms. */
function zip(noms: string[]): ArrayBuffer {
  const enc = new TextEncoder();
  const locaux: Uint8Array[] = [];
  const centraux: Uint8Array[] = [];
  let offset = 0;
  for (const nom of noms) {
    const n = enc.encode(nom);
    const local = new Uint8Array(30 + n.length);
    const lv = new DataView(local.buffer);
    lv.setUint32(0, 0x04034b50, true);
    lv.setUint16(26, n.length, true);
    local.set(n, 30);
    const central = new Uint8Array(46 + n.length);
    const cv = new DataView(central.buffer);
    cv.setUint32(0, 0x02014b50, true);
    cv.setUint16(28, n.length, true);
    cv.setUint32(42, offset, true);
    central.set(n, 46);
    locaux.push(local);
    centraux.push(central);
    offset += local.length;
  }
  const tailleCentrale = centraux.reduce((t, c) => t + c.length, 0);
  const fin = new Uint8Array(22);
  const fv = new DataView(fin.buffer);
  fv.setUint32(0, 0x06054b50, true);
  fv.setUint16(8, noms.length, true);
  fv.setUint16(10, noms.length, true);
  fv.setUint32(12, tailleCentrale, true);
  fv.setUint32(16, offset, true);
  const total = new Uint8Array(offset + tailleCentrale + 22);
  let pos = 0;
  for (const part of [...locaux, ...centraux, fin]) {
    total.set(part, pos);
    pos += part.length;
  }
  return total.buffer;
}

describe('geometry-import.utils (#687)', () => {
  describe('nomsFichiersZip', () => {
    it('liste les fichiers d\'une archive', () => {
      expect(nomsFichiersZip(zip(['site.shp', 'site.dbf', 'site.prj'])))
        .toEqual(['site.shp', 'site.dbf', 'site.prj']);
    });

    it('renvoie une liste vide pour un fichier qui n\'est pas un zip', () => {
      expect(nomsFichiersZip(new TextEncoder().encode('pas un zip').buffer)).toEqual([]);
    });
  });

  describe('fichiersManquantsDuShapefile', () => {
    it('rien ne manque quand le .shp, le .dbf et le .prj sont là', () => {
      expect(fichiersManquantsDuShapefile(['a/site.SHP', 'a/site.dbf', 'a/site.prj', 'a/site.shx']))
        .toEqual([]);
    });

    it('nomme le .prj absent : sans lui, la projection est inconnue', () => {
      expect(fichiersManquantsDuShapefile(['site.shp', 'site.dbf', 'site.shx'])).toEqual(['.prj']);
    });

    it('nomme le .shp et le .dbf absents', () => {
      expect(fichiersManquantsDuShapefile(['site.prj'])).toEqual(['.shp', '.dbf']);
    });
  });

  describe('horsWgs84', () => {
    const carre = (x: number, y: number, d = 0.01) => ({
      type: 'Polygon',
      coordinates: [[[x, y], [x, y + d], [x + d, y + d], [x + d, y], [x, y]]],
    });

    it('détecte un GeoJSON en mètres (Lambert-93)', () => {
      expect(horsWgs84({ type: 'Feature', properties: {}, geometry: carre(652000, 6862000, 500) }))
        .toBe(true);
    });

    it('accepte l\'outre-mer en WGS 84', () => {
      const fc = {
        type: 'FeatureCollection',
        features: [
          { type: 'Feature', properties: {}, geometry: carre(-61.55, 16.25) },   // Guadeloupe
          { type: 'Feature', properties: {}, geometry: carre(55.5, -21.1) },     // La Réunion
          { type: 'Feature', properties: {}, geometry: carre(-149.5, -17.55) },  // Polynésie
        ],
      };
      expect(horsWgs84(fc)).toBe(false);
    });

    it('détecte une seule géométrie fautive dans une collection', () => {
      expect(horsWgs84({
        type: 'FeatureCollection',
        features: [
          { type: 'Feature', geometry: carre(4.7, 46.9) },
          { type: 'Feature', geometry: { type: 'Point', coordinates: [650000, 1800000] } },
        ],
      })).toBe(true);
    });
  });
});
