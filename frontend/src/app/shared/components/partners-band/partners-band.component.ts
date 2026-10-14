import { Component, ChangeDetectionStrategy } from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';

interface Partenaire {
  nom: string;
  logo: string;
  url: string;
}

interface GroupePartenaires {
  libelle: string;
  partenaires: Partenaire[];
}

const RNF: Partenaire = { nom: 'Réserves Naturelles de France', logo: 'rnf.svg', url: 'https://reserves-naturelles.org' };
const CEN: Partenaire = { nom: "Fédération des Conservatoires d'espaces naturels", logo: 'cen.png', url: 'https://reseau-cen.org' };
const OFB: Partenaire = { nom: 'Office français de la biodiversité', logo: 'ofb.svg', url: 'https://www.ofb.gouv.fr' };
const LPO: Partenaire = { nom: 'LPO — Ligue pour la protection des oiseaux', logo: 'lpo.png', url: 'https://www.lpo.fr' };
const PATRINAT: Partenaire = { nom: 'PatriNat', logo: 'patrinat.png', url: 'https://www.patrinat.fr' };
const REPUBLIQUE: Partenaire = { nom: 'République française', logo: 'republique-francaise.png', url: 'https://www.ecologie.gouv.fr' };

/**
 * PartnersBand - Porteurs, partenaires et financeurs du projet, en trois groupes de logos.
 *
 * Pensé pour un fond `$primary-color` (pied de page de l'accueil) : libellés blancs,
 * logos sur cartes blanches pour garder leurs couleurs d'origine.
 */
@Component({
  selector: 'app-partners-band',
  standalone: true,
  imports: [TranslateModule],
  templateUrl: './partners-band.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './partners-band.component.scss'
})
export class PartnersBandComponent {
  readonly groupes: GroupePartenaires[] = [
    { libelle: 'home.partners.portePar', partenaires: [RNF, CEN] },
    { libelle: 'home.partners.partenariat', partenaires: [OFB, LPO, PATRINAT] },
    { libelle: 'home.partners.soutienFinancier', partenaires: [REPUBLIQUE, OFB] },
  ];
}
