import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { Observable } from 'rxjs';

import {
  CHAMPS_CONNEXION,
  ChampConnexion,
  ConnexionGeoNatureService,
  EtatConnexionGeoNature,
  ResultatTest,
  SaisieConnexion,
  commandeCompteLecture,
  erreurConnexion,
} from '../../../../core/services/connexion-geonature.service';
import { FormFieldComponent } from '../../../../shared/components/form-field/form-field.component';
import { TagComponent } from '../../../../shared/components/tag/tag.component';
import {
  ConfirmDialogComponent,
  ConfirmDialogData,
} from '../../../../shared/components/confirm-dialog/confirm-dialog.component';

/** Largeur standard des modales du projet (cf. CLAUDE.md). */
const DIALOGUE = { width: '1300px', maxWidth: '95vw', maxHeight: '90vh' } as const;

/** Hôtes qui désignent le serveur CICADA lui-même (base installée à côté). */
const HOTES_LOCAUX = ['localhost', '127.0.0.1', '::1', 'host.docker.internal'];

/**
 * #769 — Brancher l'instance sur son GeoNature / UsersHub sans terminal sur le
 * serveur CICADA : réglages, commande du compte de lecture à copier, test,
 * activation. Les garde-fous (test réussi, pas d'enfermement, confirmation)
 * sont appliqués par le backend ; l'écran les explique.
 */
@Component({
  selector: 'app-connexion-geonature',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.Eager,
  imports: [DatePipe, FormsModule, MatButtonModule, MatProgressSpinnerModule, TranslateModule,
    FormFieldComponent, TagComponent],
  templateUrl: './connexion-geonature.component.html',
  styleUrls: ['./connexion-geonature.component.scss'],
})
export class ConnexionGeoNatureComponent implements OnInit {
  private readonly service = inject(ConnexionGeoNatureService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  private readonly translate = inject(TranslateService);

  readonly etat = signal<EtatConnexionGeoNature | null>(null);
  readonly chargement = signal(true);
  readonly enCours = signal(false);
  readonly erreur = signal<string | null>(null);
  readonly test = signal<ResultatTest | null>(null);

  /** Saisie en cours, initialisée sur les valeurs effectives. */
  saisie: Record<ChampConnexion, string> = this.saisieVide();
  motDePasse = '';
  /** Adresse de ce serveur vue par la base (pour --client) : non conservée. */
  adresseCicada = '';

  ngOnInit(): void {
    this.charger();
  }

  charger(): void {
    this.chargement.set(true);
    this.service.etat().subscribe({
      next: etat => {
        this.appliquer(etat);
        this.chargement.set(false);
      },
      error: () => {
        this.erreur.set(this.translate.instant('admin.settings.connexion.erreurChargement'));
        this.chargement.set(false);
      },
    });
  }

  private saisieVide(): Record<ChampConnexion, string> {
    return Object.fromEntries(CHAMPS_CONNEXION.map(c => [c, ''])) as Record<ChampConnexion, string>;
  }

  private appliquer(etat: EtatConnexionGeoNature): void {
    this.etat.set(etat);
    this.saisie = Object.fromEntries(
      CHAMPS_CONNEXION.map(c => [c, String(etat.valeurs[c] ?? '')]),
    ) as Record<ChampConnexion, string>;
    this.motDePasse = '';
  }

  /** Valeur fournie par le `.env` du serveur : elle prime, le champ est verrouillé. */
  verrouille(champ: ChampConnexion | 'db_password'): boolean {
    return this.etat()?.origines[champ] === 'environnement';
  }

  actif(): boolean {
    return this.etat()?.mode === 'geonature';
  }

  surCeServeur(): boolean {
    return HOTES_LOCAUX.includes(this.saisie.db_host.trim());
  }

  commande(): string {
    return commandeCompteLecture(this.saisie.db_name, this.saisie.code_application, this.surCeServeur(),
      this.adresseCicada);
  }

  copierCommande(): void {
    navigator.clipboard?.writeText(this.commande()).then(
      () => this.snackBar.open(this.translate.instant('admin.settings.connexion.commandeCopiee'),
        this.translate.instant('common.actions.close'), { duration: 2500 }),
      () => undefined,
    );
  }

  modifications(): SaisieConnexion {
    const etat = this.etat();
    const saisie: SaisieConnexion = {};
    if (!etat) {
      return saisie;
    }
    for (const champ of CHAMPS_CONNEXION) {
      if (this.verrouille(champ)) {
        continue;
      }
      const valeur = this.saisie[champ].trim();
      if (valeur !== String(etat.valeurs[champ] ?? '')) {
        saisie[champ] = valeur;
      }
    }
    if (!this.verrouille('db_password') && this.motDePasse) {
      saisie.db_password = this.motDePasse;
    }
    return saisie;
  }

  modifie(): boolean {
    return Object.keys(this.modifications()).length > 0;
  }

  enregistrer(): void {
    const saisie = this.modifications();
    if (!Object.keys(saisie).length) {
      return;
    }
    this.lancer(this.service.configurer(saisie), etat => {
      this.appliquer(etat);
      this.test.set(null);
      this.annoncer('admin.settings.connexion.enregistre');
    });
  }

  tester(): void {
    this.lancer(this.service.tester(), resultat => this.test.set(resultat));
  }

  activer(confirmer = false): void {
    this.lancer(this.service.activer(confirmer), resultat => {
      this.test.set(resultat);
      this.annoncer('admin.settings.connexion.active');
      this.charger();
    }, err => {
      const refus = erreurConnexion(err);
      if (refus?.test) {
        this.test.set(refus.test);
      }
      if (refus?.code === 'confirmation_requise' && refus.test?.bilan) {
        this.confirmer(
          'admin.settings.connexion.confirmerActivation',
          { refuses: refus.test.bilan.refuses, autorises: refus.test.bilan.autorises },
          () => this.activer(true),
        );
        return true;
      }
      return false;
    });
  }

  desactiver(): void {
    this.confirmer('admin.settings.connexion.confirmerDesactivation', {}, () =>
      this.lancer(this.service.desactiver(true), etat => {
        this.appliquer(etat);
        this.annoncer('admin.settings.connexion.desactive');
      }),
    );
  }

  /** Libellé traduit du motif de refus d'un compte. */
  motif(motif: string | null): string {
    return motif ? this.translate.instant(`admin.settings.connexion.motifs.${motif}`) : '';
  }

  comptesRefuses(): { email: string; motif: string | null }[] {
    return (this.test()?.bilan?.comptes ?? []).filter(c => c.motif);
  }

  private confirmer(cle: string, params: object, suite: () => void): void {
    const data: ConfirmDialogData = {
      title: this.translate.instant(`${cle}.titre`),
      message: this.translate.instant(`${cle}.message`, params),
      confirmText: this.translate.instant(`${cle}.bouton`),
      cancelText: this.translate.instant('common.actions.cancel'),
    };
    this.dialog.open(ConfirmDialogComponent, { ...DIALOGUE, data }).afterClosed().subscribe(ok => {
      if (ok) {
        suite();
      }
    });
  }

  private annoncer(cle: string): void {
    this.snackBar.open(this.translate.instant(cle), this.translate.instant('common.actions.close'),
      { duration: 3000 });
  }

  /**
   * Appel avec indicateur et message d'erreur. `refus` peut prendre la main sur
   * une erreur (true = traitée, rien à afficher).
   */
  private lancer<T>(
    appel: Observable<T>,
    succes: (valeur: T) => void,
    refus?: (err: HttpErrorResponse) => boolean,
  ): void {
    this.enCours.set(true);
    this.erreur.set(null);
    appel.subscribe({
      next: valeur => {
        this.enCours.set(false);
        succes(valeur);
      },
      error: (err: HttpErrorResponse) => {
        this.enCours.set(false);
        if (refus?.(err)) {
          return;
        }
        this.erreur.set(erreurConnexion(err)?.detail
          ?? this.translate.instant('admin.settings.connexion.erreurInconnue'));
      },
    });
  }
}
