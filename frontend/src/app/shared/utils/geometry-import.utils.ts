/**
 * #687 — contrôles d'un fichier géographique importé sur la carte
 * (`leaflet-map-edit` : géométrie d'un site, emprise d'une action).
 *
 * Le serveur ne reprojette jamais : il enregistre les coordonnées comme des
 * degrés WGS 84. Un shapefile sans `.prj` ou un GeoJSON en Lambert-93 / UTM
 * finissait donc « hors du globe », sans département et sans message. On
 * refuse ces fichiers dès la carte, avec un message qui dit quoi corriger.
 */

/**
 * Noms des fichiers d'une archive .zip, lus dans son répertoire central.
 * Renvoie une liste vide si le fichier n'est pas une archive lisible.
 */
export function nomsFichiersZip(buffer: ArrayBuffer): string[] {
  const view = new DataView(buffer);
  const decoder = new TextDecoder();
  // Fin du répertoire central : signature 0x06054b50, cherchée depuis la fin
  // (elle peut être suivie d'un commentaire de 64 Ko au plus).
  const debut = Math.max(0, buffer.byteLength - 22 - 0xffff);
  let fin = -1;
  for (let i = buffer.byteLength - 22; i >= debut; i--) {
    if (view.getUint32(i, true) === 0x06054b50) {
      fin = i;
      break;
    }
  }
  if (fin < 0) return [];

  const nombre = view.getUint16(fin + 10, true);
  let pos = view.getUint32(fin + 16, true);
  const noms: string[] = [];
  for (let k = 0; k < nombre; k++) {
    if (pos + 46 > buffer.byteLength || view.getUint32(pos, true) !== 0x02014b50) break;
    const longueurNom = view.getUint16(pos + 28, true);
    const longueurExtra = view.getUint16(pos + 30, true);
    const longueurCommentaire = view.getUint16(pos + 32, true);
    noms.push(decoder.decode(new Uint8Array(buffer, pos + 46, longueurNom)));
    pos += 46 + longueurNom + longueurExtra + longueurCommentaire;
  }
  return noms;
}

/**
 * Fichiers indispensables absents d'un shapefile zippé : la géométrie (.shp),
 * les attributs (.dbf) et la projection (.prj). Sans `.prj`, la projection est
 * inconnue et rien ne permet de reprojeter en WGS 84.
 */
export function fichiersManquantsDuShapefile(noms: string[]): string[] {
  const extensions = new Set(
    noms.map(n => (n.split('.').pop() || '').toLowerCase()),
  );
  return ['shp', 'dbf', 'prj']
    .filter(ext => !extensions.has(ext))
    .map(ext => `.${ext}`);
}

/** Vrai si une coordonnée du GeoJSON sort de ±180 (longitude) / ±90 (latitude). */
export function horsWgs84(geojson: unknown): boolean {
  const visiter = (valeur: any): boolean => {
    if (!Array.isArray(valeur)) return false;
    if (typeof valeur[0] === 'number') {
      const [x, y] = valeur;
      return Math.abs(x) > 180 || Math.abs(y) > 90;
    }
    return valeur.some(visiter);
  };
  const geometries: any[] = [];
  const collecter = (objet: any): void => {
    if (!objet || typeof objet !== 'object') return;
    if (objet.type === 'FeatureCollection') objet.features?.forEach(collecter);
    else if (objet.type === 'Feature') collecter(objet.geometry);
    else if (objet.type === 'GeometryCollection') objet.geometries?.forEach(collecter);
    else if (objet.coordinates) geometries.push(objet);
  };
  collecter(geojson);
  return geometries.some(g => visiter(g.coordinates));
}
