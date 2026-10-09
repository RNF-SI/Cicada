import { ChangeDetectionStrategy, Component, DestroyRef, LOCALE_ID, NgZone, OnInit, inject, signal } from '@angular/core';
import { DatePipe, formatDate } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  CLES_ERREUR_RACCORDEMENT,
  CleErreurRaccordement,
  EtatRaccordement,
  FederationRaccordementService,
  PublicationHub,
  VerificationHub,
  cleErreurRaccordement,
  essaisRestants,
  normaliserCode,
} from '../../../../core/services/federation-raccordement.service';
import { AuthService } from '../../../../core/services/auth.service';
import { TagComponent, TagVariant } from '../../../../shared/components/tag/tag.component';
import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';
import { SettingsService } from '../../../../core/services/settings.service';
import { AdhesionDialogComponent, AdhesionDialogData } from './adhesion-dialog/adhesion-dialog.component';
import { ContactRnfDialogComponent } from './contact-rnf-dialog/contact-rnf-dialog.component';

/** Largeur standard des modales du projet (cf. CLAUDE.md). */
const DIALOGUE = { width: '1300px', maxWidth: '95vw', maxHeight: '90vh' } as const;

/** Longueur du code de confirmation une fois normalisé (« ABCD-EFGH »). */
const LONGUEUR_CODE = 8;

/** Erreurs de confirmation après lesquelles le statut a changé côté serveur : on recharge. */
const ERREURS_RECHARGEMENT: readonly CleErreurRaccordement[] = ['trop_d_essais', 'pas_de_code'];

/**
 * Statuts où la décision se prend chez RNF (prise de contact, envoi du code) :
 * l'écran se met à jour seul, sans quoi le champ du code n'apparaît qu'après un
 * rafraîchissement de la page.
 */
const STATUTS_SUIVIS: readonly string[] = ['en_attente', 'code_envoye'];

/** Intervalle d'actualisation pendant une adhésion en cours. */
const INTERVALLE_ACTUALISATION_MS = 15_000;

/** Étape du processus d'adhésion (1 à 5) que l'administrateur a devant lui. */
const ETAPE_PAR_STATUT: Record<string, number> = {
  '': 1,
  en_attente: 2,
  code_envoye: 4,
  acceptee: 5,
};

const VARIANTE_RESULTAT: Record<PublicationHub['resultat'], TagVariant> = {
  reussie: 'success',
  echec: 'error',
  ignoree: 'muted',
  // Retrait voulu par la structure : ni succès ni échec, un état assumé.
  retrait: 'warning',
};

/**
 * #696 / #698 — État du raccordement de l'instance au hub d'exploration.
 *
 * Répond à la question qu'un super admin se pose quand l'exploration nationale
 * « ne marche pas » : est-ce l'identité, les jetons, l'adhésion, le partage ou
 * la dernière publication ? Le diagnostic vient du serveur (premier cas qui
 * s'applique) : le calculer ici dupliquerait une règle qui doit rester unique.
 *
 * Porte aussi l'adhésion (#696 v2) : le jeton ne voyage jamais, seule une
 * demande part vers RNF, avec la personne à contacter. RNF prend contact puis
 * envoie un code de confirmation par e-mail ; le saisir ici accepte l'adhésion
 * et enrôle l'instance sur le hub. « Contacter RNF » reste disponible à tout
 * moment (code non reçu, question…).
 */
@Component({
  selector: 'app-federation-raccordement',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    MatTooltipModule,
    TranslateModule,
    TagComponent,
    FormFieldComponent,
  ],
  templateUrl: './federation-raccordement.component.html',
  styleUrl: './federation-raccordement.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class FederationRaccordementComponent implements OnInit {
  private readonly service = inject(FederationRaccordementService);
  private readonly settingsService = inject(SettingsService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);
  private readonly authService = inject(AuthService);
  private readonly locale = inject(LOCALE_ID);
  private readonly destroyRef = inject(DestroyRef);
  private readonly zone = inject(NgZone);

  readonly etat = signal<EtatRaccordement | null>(null);
  readonly chargement = signal(false);
  /** Erreur de chargement de l'état (clé i18n), affichée à la place du bloc. */
  readonly erreurChargement = signal<CleErreurRaccordement | null>(null);
  readonly demandeEnCours = signal(false);
  readonly verification = signal<VerificationHub | null>(null);
  readonly verificationEnCours = signal(false);

  /** Code de confirmation tel que saisi (forcé en majuscules). */
  codeSaisi = '';
  readonly confirmationEnCours = signal(false);
  /** Message d'erreur de la confirmation, déjà traduit (porte les essais restants). */
  readonly erreurCode = signal<string | null>(null);

  ngOnInit(): void {
    this.charger();

    // RNF agit de son côté (prise de contact, envoi du code) : tant qu'une
    // adhésion est en cours, l'état est relu régulièrement et au retour sur
    // l'onglet du navigateur — l'administrateur qui revient de sa messagerie
    // avec le code trouve le champ de saisie sans avoir à recharger la page.
    // Hors de la zone Angular : un minuteur permanent dans la zone la rendrait
    // instable pour toujours (tests qui attendent la stabilité, hydratation).
    // Chaque tick y revient pour que l'affichage suive.
    const minuteur = this.zone.runOutsideAngular(() =>
      setInterval(() => this.zone.run(() => this.actualiserSiEnCours()), INTERVALLE_ACTUALISATION_MS),
    );
    const auRetour = () => {
      if (document.visibilityState === 'visible') {
        this.actualiserSiEnCours();
      }
    };
    document.addEventListener('visibilitychange', auRetour);
    this.destroyRef.onDestroy(() => {
      clearInterval(minuteur);
      document.removeEventListener('visibilitychange', auRetour);
    });
  }

  /**
   * Relit l'état sans indicateur de chargement ni perte de la saisie en cours,
   * seulement si une adhésion attend une action de RNF.
   */
  actualiserSiEnCours(): void {
    const statut = this.etat()?.adhesion.statut ?? '';
    if (
      !STATUTS_SUIVIS.includes(statut)
      || this.chargement()
      || this.confirmationEnCours()
      || document.visibilityState === 'hidden'
    ) {
      return;
    }
    this.service.etat().subscribe({
      next: etat => this.etat.set(etat),
      // Silencieux : un échec ponctuel ne doit pas remplacer l'écran par une
      // erreur, la prochaine actualisation réessaiera.
      error: () => undefined,
    });
  }

  /**
   * Texte de l'info-bulle : les étapes de l'adhésion, et celle où l'on en est.
   * Une adhésion refusée ou des jetons fournis par la configuration sortent du
   * parcours : seules les étapes sont alors rappelées.
   */
  aideProcessus(): string {
    const etat = this.etat();
    const base = this.translate.instant('admin.settings.federation.etat.adhesion.aideProcessus');
    if (!etat || etat.configuration.source_jetons === 'environnement') {
      return base;
    }
    const etape = ETAPE_PAR_STATUT[etat.adhesion.statut ?? ''];
    if (!etape) {
      return base;
    }
    const position = this.translate.instant('admin.settings.federation.etat.adhesion.aideEtape', { etape });
    return `${base}\n\n${position}`;
  }

  charger(): void {
    this.chargement.set(true);
    this.erreurChargement.set(null);
    this.service.etat().subscribe({
      next: etat => {
        this.etat.set(etat);
        this.chargement.set(false);
      },
      error: err => {
        this.chargement.set(false);
        this.erreurChargement.set(cleErreurRaccordement(err));
      },
    });
  }

  /**
   * Ouvre le formulaire de demande : nom et adresse pré-remplis avec
   * l'utilisateur connecté, que RNF contactera puis à qui il enverra le code.
   */
  demanderAdhesion(): void {
    const etat = this.etat();
    if (!etat?.adhesion.possible || this.demandeEnCours()) {
      return;
    }
    const utilisateur = this.authService.currentUser();
    const data: AdhesionDialogData = {
      instance_id: etat.configuration.instance_id,
      libelle: etat.configuration.instance_libelle,
      contact_nom: this.authService.getUserDisplayName(),
      contact_email: utilisateur?.email ?? '',
    };
    this.demandeEnCours.set(true);
    this.dialog
      .open<AdhesionDialogComponent, AdhesionDialogData, EtatRaccordement>(AdhesionDialogComponent, { ...DIALOGUE, data })
      .afterClosed()
      .subscribe(nouvelEtat => {
        this.demandeEnCours.set(false);
        if (nouvelEtat) {
          this.etat.set(nouvelEtat);
          this.notifier('adhesion.envoyee');
          // Demander l'adhésion vaut consentement au partage : le serveur a
          // coché la case. On relit les paramètres pour que la page la montre
          // cochée sans rechargement — sinon elle contredirait la demande.
          this.settingsService.loadSettings().subscribe({ error: () => undefined });
        }
      });
  }

  saisirCode(valeur: string): void {
    this.codeSaisi = (valeur ?? '').toUpperCase();
    this.erreurCode.set(null);
  }

  /** Code complet (8 caractères hors tirets et espaces) : active le bouton. */
  codeComplet(): boolean {
    return normaliserCode(this.codeSaisi).length === LONGUEUR_CODE;
  }

  confirmerCode(): void {
    if (!this.codeComplet() || this.confirmationEnCours()) {
      return;
    }
    this.confirmationEnCours.set(true);
    this.erreurCode.set(null);
    this.service.confirmerCode(normaliserCode(this.codeSaisi)).subscribe({
      next: etat => {
        this.confirmationEnCours.set(false);
        this.codeSaisi = '';
        this.etat.set(etat);
        this.notifier('confirmation.reussie');
      },
      error: err => {
        this.confirmationEnCours.set(false);
        const cle = cleErreurRaccordement(err);
        const essais = essaisRestants(err);
        const cleMessage = cle === 'code_invalide' && essais !== null ? 'code_invalide_essais' : cle;
        if (ERREURS_RECHARGEMENT.includes(cle)) {
          // Code invalidé ou plus attendu : le statut a changé côté serveur, le
          // champ de saisie va disparaître — le message passe par la snackbar.
          this.codeSaisi = '';
          this.notifier(`erreurs.${cleMessage}`);
          this.charger();
          return;
        }
        this.erreurCode.set(
          this.translate.instant(`admin.settings.federation.etat.erreurs.${cleMessage}`, { essais }),
        );
      },
    });
  }

  contacterRnf(): void {
    this.dialog
      .open<ContactRnfDialogComponent, void, boolean>(ContactRnfDialogComponent, { ...DIALOGUE })
      .afterClosed()
      .subscribe(envoye => {
        if (envoye) {
          this.notifier('contact.envoye');
        }
      });
  }

  verifier(): void {
    if (this.verificationEnCours()) {
      return;
    }
    this.verificationEnCours.set(true);
    this.verification.set(null);
    this.service.verifier().subscribe({
      next: resultat => {
        this.verification.set(resultat);
        this.verificationEnCours.set(false);
      },
      error: err => {
        this.verificationEnCours.set(false);
        this.notifier(`erreurs.${cleErreurRaccordement(err)}`);
      },
    });
  }

  /** Clé i18n d'une erreur renvoyée par la vérification (repli si inconnue). */
  cleErreurVerification(erreur: string | null): string {
    const cle = erreur && (CLES_ERREUR_RACCORDEMENT as readonly string[]).includes(erreur) ? erreur : 'erreur_inconnue';
    return `admin.settings.federation.etat.erreurs.${cle}`;
  }

  /**
   * Paramètres du diagnostic prêts à interpoler : les dates (`expire_le`)
   * arrivent en ISO, illisibles telles quelles dans une phrase.
   */
  parametresDiagnostic(parametres: Record<string, string | number>): Record<string, string | number> {
    const resultat = { ...parametres };
    const expire = resultat['expire_le'];
    if (typeof expire === 'string' && expire) {
      try {
        resultat['expire_le'] = formatDate(expire, 'dd/MM/yyyy HH:mm', this.locale);
      } catch {
        // Date illisible : on garde la valeur brute plutôt que de masquer le message.
      }
    }
    return resultat;
  }

  varianteResultat(resultat: PublicationHub['resultat']): TagVariant {
    return VARIANTE_RESULTAT[resultat] ?? 'neutral';
  }

  /** Tag oui/non (succès / gris) : une valeur `null` signifie « inconnu ». */
  varianteBool(valeur: boolean | null): TagVariant {
    return valeur === true ? 'success' : valeur === false ? 'error' : 'muted';
  }

  cleBool(valeur: boolean | null): string {
    const suffixe = valeur === true ? 'oui' : valeur === false ? 'non' : 'inconnu';
    return `admin.settings.federation.etat.commun.${suffixe}`;
  }

  private notifier(cle: string): void {
    this.snackBar.open(
      this.translate.instant(`admin.settings.federation.etat.${cle}`),
      this.translate.instant('common.actions.close'),
      { duration: 5000 },
    );
  }
}
