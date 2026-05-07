export interface MindmapNode {
  name: string;
  entityType: MindmapEntityType;
  id?: number;
  /** Slug exposé pour les types `enjeu` et `fcr` (route `/enjeux/:enjeuSlug`). */
  slug?: string;
  children?: MindmapNode[];
  _children?: MindmapNode[];
}

export type MindmapEntityType =
  | 'plan' | 'enjeu' | 'fcr' | 'facteur' | 'pression'
  | 'olt' | 'etat_enjeu' | 'niveau_exigence'
  | 'oo' | 'resultat_attendu'
  | 'indicateur' | 'metrique' | 'mesure'
  | 'operation' | 'operation_annee' | 'finance'
  | 'suivi' | 'protocole';

export const MINDMAP_COLORS: Record<MindmapEntityType, string> = {
  plan: '#025359',
  enjeu: '#FEC180',
  fcr: '#C0E3CF',
  facteur: '#F5B399',
  pression: '#FF7579',
  olt: '#04854B',
  etat_enjeu: '#82DB8A',
  niveau_exigence: '#81C9D8',
  oo: '#81C9D8',
  resultat_attendu: '#F7D35C',
  indicateur: '#FA9965',
  metrique: '#B74D5D',
  mesure: '#746F6E',
  operation: '#025359',
  operation_annee: '#C6C6C6',
  finance: '#FEC180',
  suivi: '#04854B',
  protocole: '#C0E3CF',
};

export const MINDMAP_LABELS: Record<MindmapEntityType, string> = {
  plan: 'Plan de Gestion',
  enjeu: 'Enjeu',
  fcr: 'FCR',
  facteur: 'Facteur d\'influence',
  pression: 'Pression',
  olt: 'Objectif Long Terme',
  etat_enjeu: 'État Actuel',
  niveau_exigence: 'Niveau d\'Exigence',
  oo: 'Objectif Opérationnel',
  resultat_attendu: 'Résultat Attendu',
  indicateur: 'Indicateur',
  metrique: 'Métrique',
  mesure: 'Mesure',
  operation: 'Opération',
  operation_annee: 'Programmation Annuelle',
  finance: 'Finance',
  suivi: 'Suivi / Inventaire',
  protocole: 'Protocole',
};
