import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';

import {
  CLES_ERREUR_RACCORDEMENT,
  CleErreurRaccordement,
  EtatRaccordement,
  FederationRaccordementService,
  PublicationHub,
  VerificationHub,
  cleErreurRaccordement,
} from '../../../../core/services/federation-raccordement.service';
import { TagComponent, TagVariant } from '../../../../shared/components/tag/tag.component';
import { ConfirmDialogComponent } from '../../../../shared/components/confirm-dialog/confirm-dialog.component';

const VARIANTE_RESULTAT: Record<PublicationHub['resultat'], TagVariant> = {
  reussie: 'success',
  echec: 'error',
  ignoree: 'muted',
};

/**
 * #696 / #698 — État du raccordement de l'instance au hub d'exploration.
 *
 * Répond à la question qu'un super admin se pose quand l'exploration nationale
 * « ne marche pas » : est-ce l'identité, les jetons, l'adhésion, le partage ou
 * la dernière publication ? Le diagnostic vient du serveur (premier cas qui
 * s'applique) : le calculer ici dupliquerait une règle qui doit rester unique.
 *
 * Porte aussi la demande d'adhésion : le jeton ne voyage jamais, seule une
 * demande part vers RNF, qui rappelle la structure pour comparer le code de
 * vérification avant d'accepter. Le code doit donc être lisible et copiable.
 */
@Component({
  selector: 'app-federation-raccordement',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    TranslateModule,
    TagComponent,
  ],
  templateUrl: './federation-raccordement.component.html',
  styleUrl: './federation-raccordement.component.scss',
  changeDetection: ChangeDetectionStrategy.Eager,
})
export class FederationRaccordementComponent implements OnInit {
  private readonly service = inject(FederationRaccordementService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly etat = signal<EtatRaccordement | null>(null);
  readonly chargement = signal(false);
  /** Erreur de chargement de l'état (clé i18n), affichée à la place du bloc. */
  readonly erreurChargement = signal<CleErreurRaccordement | null>(null);
  readonly demandeEnCours = signal(false);
  readonly verification = signal<VerificationHub | null>(null);
  readonly verificationEnCours = signal(false);

  ngOnInit(): void {
    this.charger();
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

  /** Confirmation explicite : la demande engage la structure auprès de RNF. */
  demanderAdhesion(): void {
    const etat = this.etat();
    if (!etat?.adhesion.possible || this.demandeEnCours()) {
      return;
    }
    const t = (cle: string, p?: object) => this.translate.instant(`admin.settings.federation.etat.${cle}`, p);
    const dialogRef = this.dialog.open(ConfirmDialogComponent, {
      width: '500px',
      data: {
        title: t('adhesion.confirmTitre'),
        message: t('adhesion.confirmMessage', {
          instance_id: etat.configuration.instance_id,
          libelle: etat.configuration.instance_libelle,
        }),
        warningText: t('adhesion.confirmAvertissement'),
        confirmText: t('adhesion.confirmBouton'),
        cancelText: this.translate.instant('common.actions.cancel'),
      },
    });
    dialogRef.afterClosed().subscribe(confirme => {
      if (confirme) {
        this.envoyerDemande();
      }
    });
  }

  private envoyerDemande(): void {
    this.demandeEnCours.set(true);
    this.service.demanderAdhesion().subscribe({
      next: etat => {
        this.etat.set(etat);
        this.demandeEnCours.set(false);
        this.notifier('adhesion.envoyee');
      },
      error: err => {
        this.demandeEnCours.set(false);
        this.notifier(`erreurs.${cleErreurRaccordement(err)}`);
      },
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

  copierCode(code: string): void {
    const clipboard = typeof navigator !== 'undefined' ? navigator.clipboard : undefined;
    if (!clipboard) {
      this.notifier('adhesion.copieImpossible');
      return;
    }
    clipboard.writeText(code).then(
      () => this.notifier('adhesion.copie'),
      () => this.notifier('adhesion.copieImpossible'),
    );
  }

  /** Clé i18n d'une erreur renvoyée par la vérification (repli si inconnue). */
  cleErreurVerification(erreur: string | null): string {
    const cle = erreur && (CLES_ERREUR_RACCORDEMENT as readonly string[]).includes(erreur) ? erreur : 'erreur_inconnue';
    return `admin.settings.federation.etat.erreurs.${cle}`;
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
