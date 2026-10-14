import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { FederationRaccordementComponent } from './federation-raccordement.component';
import { AdhesionDialogComponent } from './adhesion-dialog/adhesion-dialog.component';
import { ContactRnfDialogComponent } from './contact-rnf-dialog/contact-rnf-dialog.component';
import { AuthService } from '../../../../core/services/auth.service';
import { SettingsService } from '../../../../core/services/settings.service';
import {
  EtatRaccordement,
  FederationRaccordementService,
  cleErreurRaccordement,
  essaisRestants,
  normaliserCode,
} from '../../../../core/services/federation-raccordement.service';

const TRADUCTIONS = {
  admin: {
    settings: {
      federation: {
        etat: {
          diagnostic: {
            ok: 'Tout va bien',
            adhesion_en_attente: 'En attente de RNF',
            adhesion_refusee: 'Refusée : {{motif}}',
            identite_manquante: 'Identité manquante',
            adhesion_code_envoye: 'Code à saisir avant le {{expire_le}}',
          },
          adhesion: {
            demander: 'Demander',
            redemander: 'Refaire',
            envoyee: 'Envoyée',
            enAttenteTexte: 'RNF va contacter {{email}}',
            aideProcessus: 'Étapes de l’adhésion',
            aideEtape: 'Étape {{etape}}',
            codeEnvoyeTexte: 'Demande faite avec {{email}}',
            codeExpireLe: 'Valable jusqu’au {{date}}',
            statut: { acceptee: 'Acceptée' },
          },
          confirmation: { reussie: 'Code accepté' },
          contact: { bouton: 'Contacter RNF', envoye: 'Message envoyé' },
          erreurs: {
            suivi_indisponible: 'Suivi indisponible',
            erreur_inconnue: 'Erreur inconnue',
            code_invalide: 'Code incorrect',
            code_invalide_essais: 'Code incorrect, {{essais}} essai(s)',
            code_expire: 'Code expiré',
            trop_d_essais: 'Trop d’essais',
          },
        },
      },
    },
  },
};

class FakeLoader implements TranslateLoader {
  getTranslation() {
    return of(TRADUCTIONS);
  }
}

function etatFactice(surcharge: {
  diagnostic?: Partial<EtatRaccordement['diagnostic']>;
  adhesion?: Partial<EtatRaccordement['adhesion']>;
  publications?: EtatRaccordement['publications'];
} = {}): EtatRaccordement {
  return {
    configuration: {
      instance_id: 'cen-aura',
      instance_libelle: 'CEN Auvergne-Rhône-Alpes',
      identite_valide: true,
      hub_url: 'https://hub.example.org',
      source_jetons: null,
      jeton_depot_defini: false,
      jeton_lecture_defini: false,
      exploration_source: 'local',
      relais_actif: false,
      publication_auto: true,
      partage: true,
      suivi_disponible: true,
    },
    adhesion: {
      statut: '',
      demandee_le: null,
      motif: '',
      possible: true,
      erreur_suivi: null,
      code_expire_le: null,
      contact_email: '',
      ...surcharge.adhesion,
    },
    publications: surcharge.publications ?? [],
    diagnostic: { niveau: 'info', cle: 'non_raccorde', parametres: {}, ...surcharge.diagnostic },
  };
}

describe('FederationRaccordementComponent', () => {
  let fixture: ComponentFixture<FederationRaccordementComponent>;
  let component: FederationRaccordementComponent;
  let service: {
    etat: jest.Mock;
    verifier: jest.Mock;
    demanderAdhesion: jest.Mock;
    confirmerCode: jest.Mock;
    contacterRnf: jest.Mock;
  };
  let dialog: { open: jest.Mock };
  let snackBar: { open: jest.Mock };
  let settingsService: { loadSettings: jest.Mock };

  async function creer(etat: EtatRaccordement | HttpErrorResponse): Promise<void> {
    service.etat.mockReturnValue(etat instanceof HttpErrorResponse ? throwError(() => etat) : of(etat));
    fixture = TestBed.createComponent(FederationRaccordementComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  const el = (): HTMLElement => fixture.nativeElement;

  beforeEach(async () => {
    service = {
      etat: jest.fn(),
      verifier: jest.fn(),
      demanderAdhesion: jest.fn(),
      confirmerCode: jest.fn(),
      contacterRnf: jest.fn(),
    };
    dialog = { open: jest.fn() };
    snackBar = { open: jest.fn() };
    settingsService = { loadSettings: jest.fn(() => of({})) };

    await TestBed.configureTestingModule({
      imports: [
        FederationRaccordementComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FakeLoader } }),
      ],
    })
      .overrideComponent(FederationRaccordementComponent, {
        add: {
          providers: [
            { provide: MatDialog, useValue: dialog },
            { provide: MatSnackBar, useValue: snackBar },
          ],
        },
      })
      .overrideProvider(FederationRaccordementService, { useValue: service })
      .overrideProvider(SettingsService, { useValue: settingsService })
      .overrideProvider(AuthService, {
        useValue: {
          currentUser: () => ({ email: 'marie@cen-aura.org' }),
          getUserDisplayName: () => 'Marie Dupont',
        },
      })
      .compileComponents();

    TestBed.inject(TranslateService).use('fr');
  });

  it('charge l’état à l’initialisation', async () => {
    await creer(etatFactice());
    expect(service.etat).toHaveBeenCalledTimes(1);
    expect(component.etat()?.configuration.instance_id).toBe('cen-aura');
  });

  it.each([
    ['ok', 'info-block-success'],
    ['attention', 'info-block-warning'],
    ['erreur', 'info-block-error'],
  ] as const)('diagnostic de niveau %s → classe %s', async (niveau, classe) => {
    await creer(etatFactice({ diagnostic: { niveau, cle: 'ok' } }));
    const bloc = el().querySelector('[data-testid="raccordement-diagnostic"]')!;
    expect(bloc.classList).toContain('info-block');
    expect(bloc.classList).toContain(classe);
  });

  it('diagnostic de niveau info → bloc neutre', async () => {
    await creer(etatFactice());
    const bloc = el().querySelector('[data-testid="raccordement-diagnostic"]')!;
    expect(bloc.className).not.toMatch(/info-block-(success|warning|error)/);
  });

  it('interpole les paramètres du diagnostic', async () => {
    await creer(etatFactice({ diagnostic: { niveau: 'erreur', cle: 'adhesion_refusee', parametres: { motif: 'doublon' } } }));
    expect(el().querySelector('[data-testid="raccordement-diagnostic"]')!.textContent).toContain('Refusée : doublon');
  });

  it('affiche la demande en attente, sans bouton d’adhésion', async () => {
    await creer(etatFactice({
      adhesion: { statut: 'en_attente', possible: false },
      diagnostic: { niveau: 'info', cle: 'adhesion_en_attente', parametres: {} },
    }));
    expect(el().querySelector('[data-testid="raccordement-diagnostic"]')!.textContent).toContain('En attente de RNF');
    expect(el().querySelector('[data-testid="adhesion-en-attente"]')!.textContent).toContain('RNF va contacter');
    expect(el().querySelector('[data-testid="bouton-adhesion"]')).toBeNull();
  });

  it('montre le bouton d’adhésion seulement si possible', async () => {
    await creer(etatFactice({ adhesion: { possible: false } }));
    expect(el().querySelector('[data-testid="bouton-adhesion"]')).toBeNull();

    component.etat.set(etatFactice({ adhesion: { possible: true } }));
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="bouton-adhesion"]')!.textContent).toContain('Demander');
  });

  it('propose « Refaire une demande » après un refus', async () => {
    await creer(etatFactice({ adhesion: { statut: 'refusee', motif: 'doublon', possible: true } }));
    expect(el().querySelector('[data-testid="bouton-adhesion"]')!.textContent).toContain('Refaire');
  });

  it('ouvre le formulaire d’adhésion pré-rempli avec l’utilisateur connecté', async () => {
    await creer(etatFactice());
    dialog.open.mockReturnValue({ afterClosed: () => of(undefined) });

    component.demanderAdhesion();

    expect(dialog.open).toHaveBeenCalledWith(AdhesionDialogComponent, expect.objectContaining({
      width: '1300px',
      maxWidth: '95vw',
      data: {
        instance_id: 'cen-aura',
        libelle: 'CEN Auvergne-Rhône-Alpes',
        contact_nom: 'Marie Dupont',
        contact_email: 'marie@cen-aura.org',
      },
    }));
    // Formulaire annulé : rien ne change.
    expect(component.etat()?.adhesion.statut).toBe('');
    expect(snackBar.open).not.toHaveBeenCalled();
    expect(component.demandeEnCours()).toBe(false);
    expect(settingsService.loadSettings).not.toHaveBeenCalled();
  });

  it('remplace l’état par celui renvoyé une fois la demande envoyée', async () => {
    await creer(etatFactice());
    const attente = etatFactice({ adhesion: { statut: 'en_attente', possible: false, contact_email: 'marie@cen-aura.org' } });
    dialog.open.mockReturnValue({ afterClosed: () => of(attente) });

    component.demanderAdhesion();
    fixture.detectChanges();

    expect(component.etat()?.adhesion.statut).toBe('en_attente');
    expect(snackBar.open).toHaveBeenCalledWith('Envoyée', expect.anything(), expect.anything());
    expect(el().querySelector('[data-testid="adhesion-en-attente"]')!.textContent).toContain('RNF va contacter marie@cen-aura.org');
  });

  it('relit les paramètres après la demande : la case de partage apparaît cochée', async () => {
    await creer(etatFactice());
    dialog.open.mockReturnValue({ afterClosed: () => of(etatFactice({ adhesion: { statut: 'en_attente', possible: false } })) });

    component.demanderAdhesion();

    expect(settingsService.loadSettings).toHaveBeenCalledTimes(1);
  });

  it('n’ouvre pas le formulaire si l’adhésion n’est pas possible', async () => {
    await creer(etatFactice({ adhesion: { possible: false } }));
    component.demanderAdhesion();
    expect(dialog.open).not.toHaveBeenCalled();
  });

  describe('actualisation pendant une adhésion en cours', () => {
    const enAttente = () => etatFactice({
      adhesion: { statut: 'en_attente', possible: false, contact_email: 'marie@cen-aura.org' },
      diagnostic: { niveau: 'info', cle: 'adhesion_en_attente', parametres: {} },
    });
    const codeEnvoye = () => etatFactice({
      adhesion: { statut: 'code_envoye', possible: false, contact_email: 'marie@cen-aura.org' },
      diagnostic: { niveau: 'info', cle: 'adhesion_code_envoye', parametres: {} },
    });

    it('fait apparaître le champ du code dès que RNF l’a envoyé, sans recharger la page', async () => {
      await creer(enAttente());
      expect(el().querySelector('[data-testid="adhesion-code"]')).toBeNull();

      service.etat.mockReturnValue(of(codeEnvoye()));
      component.actualiserSiEnCours();
      fixture.detectChanges();

      expect(service.etat).toHaveBeenCalledTimes(2);
      expect(el().querySelector('[data-testid="adhesion-code"]')).not.toBeNull();
    });

    it('ne relit pas l’état hors d’une adhésion en cours', async () => {
      await creer(etatFactice());
      component.actualiserSiEnCours();
      expect(service.etat).toHaveBeenCalledTimes(1);
    });

    it('garde l’écran affiché si une actualisation échoue', async () => {
      await creer(enAttente());
      service.etat.mockReturnValue(throwError(() => new HttpErrorResponse({ status: 502 })));
      component.actualiserSiEnCours();
      fixture.detectChanges();
      expect(component.erreurChargement()).toBeNull();
      expect(component.etat()?.adhesion.statut).toBe('en_attente');
    });
  });

  describe('info-bulle des étapes', () => {
    it.each([
      ['', 'Étape 1'],
      ['en_attente', 'Étape 2'],
      ['code_envoye', 'Étape 4'],
      ['acceptee', 'Étape 5'],
    ])('statut « %s » → %s', async (statut, attendu) => {
      await creer(etatFactice({ adhesion: { statut: statut as EtatRaccordement['adhesion']['statut'] } }));
      expect(component.aideProcessus()).toBe(`Étapes de l’adhésion\n\n${attendu}`);
      expect(el().querySelector('[data-testid="aide-processus"]')?.getAttribute('aria-label'))
        .toContain(attendu);
    });

    it('ne donne pas d’étape pour une adhésion refusée', async () => {
      await creer(etatFactice({ adhesion: { statut: 'refusee' } }));
      expect(component.aideProcessus()).toBe('Étapes de l’adhésion');
    });
  });

  describe('code de confirmation (statut code_envoye)', () => {
    const codeEnvoye = () => etatFactice({
      adhesion: {
        statut: 'code_envoye',
        possible: false,
        contact_email: 'marie@cen-aura.org',
        code_expire_le: '2026-10-14T12:00:00Z',
      },
      diagnostic: { niveau: 'info', cle: 'adhesion_code_envoye', parametres: { expire_le: '2026-10-14T12:00:00Z' } },
    });

    const bouton = () => el().querySelector('[data-testid="bouton-valider-code"]') as HTMLButtonElement;

    it('affiche le champ de saisie, l’adresse de la demande et l’échéance', async () => {
      await creer(codeEnvoye());
      expect(el().querySelector('[data-testid="adhesion-code"]')).not.toBeNull();
      expect(el().querySelector('[data-testid="adhesion-code-envoye"]')!.textContent).toContain('marie@cen-aura.org');
      expect(el().querySelector('[data-testid="adhesion-code-expiration"]')!.textContent).toContain('Valable jusqu’au');
      // La date ISO du diagnostic est mise en forme avant interpolation.
      const diagnostic = el().querySelector('[data-testid="raccordement-diagnostic"]')!.textContent!;
      expect(diagnostic).toContain('Code à saisir avant le');
      expect(diagnostic).not.toContain('2026-10-14T');
      expect(el().querySelector('[data-testid="bouton-adhesion"]')).toBeNull();
    });

    it('force les majuscules et n’active le bouton qu’avec un code complet', async () => {
      await creer(codeEnvoye());
      expect(bouton().disabled).toBe(true);

      component.saisirCode('abcd-ef');
      fixture.detectChanges();
      expect(component.codeSaisi).toBe('ABCD-EF');
      expect(bouton().disabled).toBe(true);

      component.saisirCode('abcd efgh');
      fixture.detectChanges();
      expect(bouton().disabled).toBe(false);
    });

    it('valide le code et affiche l’adhésion acceptée', async () => {
      await creer(codeEnvoye());
      service.confirmerCode.mockReturnValue(of(etatFactice({
        adhesion: { statut: 'acceptee', possible: false },
        diagnostic: { niveau: 'info', cle: 'aucune_publication', parametres: {} },
      })));

      component.saisirCode('abcd-efgh');
      component.confirmerCode();
      fixture.detectChanges();

      expect(service.confirmerCode).toHaveBeenCalledWith('ABCDEFGH');
      expect(component.etat()?.adhesion.statut).toBe('acceptee');
      expect(component.codeSaisi).toBe('');
      expect(el().querySelector('[data-testid="adhesion-acceptee"]')).not.toBeNull();
      expect(el().querySelector('[data-testid="adhesion-code"]')).toBeNull();
      expect(snackBar.open).toHaveBeenCalledWith('Code accepté', expect.anything(), expect.anything());
    });

    it('affiche l’erreur de code incorrect avec les essais restants', async () => {
      await creer(codeEnvoye());
      service.confirmerCode.mockReturnValue(throwError(() =>
        new HttpErrorResponse({ status: 400, error: { erreur: 'code_invalide', essais_restants: 3 } })));

      component.saisirCode('ABCD-EFGH');
      component.confirmerCode();
      fixture.detectChanges();

      expect(component.erreurCode()).toBe('Code incorrect, 3 essai(s)');
      expect(el().querySelector('.raccordement-code')!.textContent).toContain('Code incorrect, 3 essai(s)');
      expect(component.confirmationEnCours()).toBe(false);
      // Le code reste saisi pour être corrigé.
      expect(component.codeSaisi).toBe('ABCD-EFGH');
      expect(service.etat).toHaveBeenCalledTimes(1);
    });

    it('traduit un code expiré', async () => {
      await creer(codeEnvoye());
      service.confirmerCode.mockReturnValue(throwError(() =>
        new HttpErrorResponse({ status: 400, error: { erreur: 'code_expire' } })));

      component.saisirCode('ABCD-EFGH');
      component.confirmerCode();
      expect(component.erreurCode()).toBe('Code expiré');
    });

    it('recharge l’état quand le code est invalidé (trop d’essais)', async () => {
      await creer(codeEnvoye());
      service.confirmerCode.mockReturnValue(throwError(() =>
        new HttpErrorResponse({ status: 400, error: { erreur: 'trop_d_essais' } })));
      service.etat.mockReturnValue(of(etatFactice({ adhesion: { statut: 'en_attente', possible: false } })));

      component.saisirCode('ABCD-EFGH');
      component.confirmerCode();
      fixture.detectChanges();

      expect(snackBar.open).toHaveBeenCalledWith('Trop d’essais', expect.anything(), expect.anything());
      expect(service.etat).toHaveBeenCalledTimes(2);
      expect(component.etat()?.adhesion.statut).toBe('en_attente');
      expect(component.codeSaisi).toBe('');
    });
  });

  describe('contact RNF', () => {
    it.each(['', 'en_attente', 'code_envoye', 'acceptee', 'refusee'] as const)(
      'le bouton est visible quel que soit le statut (%s)', async statut => {
        await creer(etatFactice({ adhesion: { statut, possible: false } }));
        expect(el().querySelector('[data-testid="bouton-contact"]')!.textContent).toContain('Contacter RNF');
      });

    it('ouvre le dialogue et confirme l’envoi par une snackbar', async () => {
      await creer(etatFactice());
      dialog.open.mockReturnValue({ afterClosed: () => of(true) });

      (el().querySelector('[data-testid="bouton-contact"]') as HTMLButtonElement).click();

      expect(dialog.open).toHaveBeenCalledWith(ContactRnfDialogComponent, expect.objectContaining({ width: '1300px' }));
      expect(snackBar.open).toHaveBeenCalledWith('Message envoyé', expect.anything(), expect.anything());
    });

    it('ne notifie rien si le dialogue est annulé', async () => {
      await creer(etatFactice());
      dialog.open.mockReturnValue({ afterClosed: () => of(false) });
      component.contacterRnf();
      expect(snackBar.open).not.toHaveBeenCalled();
    });
  });

  it('vérifie le raccordement et affiche le résultat', async () => {
    await creer(etatFactice());
    service.verifier.mockReturnValue(of({
      hub_joignable: true, instance_reconnue: true, active: true,
      derniere_publication: '2026-10-07T02:30:00Z', plans: 12, contenus: 340, erreur: null,
    }));

    (el().querySelector('[data-testid="bouton-verifier"]') as HTMLButtonElement).click();
    fixture.detectChanges();

    expect(service.verifier).toHaveBeenCalledTimes(1);
    expect(el().querySelector('[data-testid="resultat-verification"]')).not.toBeNull();
    expect(component.verificationEnCours()).toBe(false);
  });

  it('affiche l’état vide des publications', async () => {
    await creer(etatFactice());
    expect(el().querySelector('[data-testid="publications-vide"]')).not.toBeNull();
  });

  it('liste les publications', async () => {
    await creer(etatFactice({
      publications: [
        { date: '2026-10-07T02:30:00Z', origine: 'nuit', resultat: 'reussie', plans: 12, documents: 340, depublies: 0, message: '' },
        { date: '2026-10-06T02:30:00Z', origine: 'manuelle', resultat: 'echec', plans: 0, documents: 0, depublies: 0, message: 'hub injoignable' },
      ],
    }));
    expect(el().querySelectorAll('.publications-table tbody tr').length).toBe(2);
  });

  it('signale une erreur de chargement', async () => {
    await creer(new HttpErrorResponse({ status: 500 }));
    expect(el().querySelector('[data-testid="raccordement-erreur"]')).not.toBeNull();
  });
});

describe('cleErreurRaccordement', () => {
  it('reconnaît une clé connue dans le corps de la réponse', () => {
    expect(cleErreurRaccordement(new HttpErrorResponse({ status: 409, error: { erreur: 'deja_acceptee' } }))).toBe('deja_acceptee');
    expect(cleErreurRaccordement(new HttpErrorResponse({ status: 400, error: { code: 'suivi_indisponible' } }))).toBe('suivi_indisponible');
  });

  it('reconnaît les erreurs de la confirmation par code', () => {
    for (const cle of ['contact_invalide', 'code_invalide', 'code_expire', 'trop_d_essais', 'pas_de_code', 'hub_injoignable']) {
      expect(cleErreurRaccordement(new HttpErrorResponse({ status: 400, error: { erreur: cle } }))).toBe(cle);
    }
  });

  it('retombe sur erreur_inconnue sinon', () => {
    expect(cleErreurRaccordement(new HttpErrorResponse({ status: 500, error: { detail: 'boum' } }))).toBe('erreur_inconnue');
    expect(cleErreurRaccordement(null)).toBe('erreur_inconnue');
  });
});

describe('essaisRestants', () => {
  it('lit le nombre d’essais restants, ou null', () => {
    expect(essaisRestants(new HttpErrorResponse({ status: 400, error: { erreur: 'code_invalide', essais_restants: 2 } }))).toBe(2);
    expect(essaisRestants(new HttpErrorResponse({ status: 400, error: { erreur: 'code_expire' } }))).toBeNull();
    expect(essaisRestants(null)).toBeNull();
  });
});

describe('normaliserCode', () => {
  it('met en majuscules et retire espaces et tirets', () => {
    expect(normaliserCode(' abcd-efgh ')).toBe('ABCDEFGH');
    expect(normaliserCode('AB CD - EF GH')).toBe('ABCDEFGH');
  });
});
