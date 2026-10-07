import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateLoader, TranslateModule, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { FederationRaccordementComponent } from './federation-raccordement.component';
import {
  EtatRaccordement,
  FederationRaccordementService,
  cleErreurRaccordement,
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
          },
          adhesion: { demander: 'Demander', redemander: 'Refaire', envoyee: 'Envoyée', enAttenteTexte: 'Apparaîtra une fois acceptée' },
          erreurs: { suivi_indisponible: 'Suivi indisponible', erreur_inconnue: 'Erreur inconnue' },
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
      ...surcharge.adhesion,
    },
    publications: surcharge.publications ?? [],
    diagnostic: { niveau: 'info', cle: 'non_raccorde', parametres: {}, ...surcharge.diagnostic },
  };
}

describe('FederationRaccordementComponent', () => {
  let fixture: ComponentFixture<FederationRaccordementComponent>;
  let component: FederationRaccordementComponent;
  let service: { etat: jest.Mock; verifier: jest.Mock; demanderAdhesion: jest.Mock };
  let dialog: { open: jest.Mock };
  let snackBar: { open: jest.Mock };

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
    service = { etat: jest.fn(), verifier: jest.fn(), demanderAdhesion: jest.fn() };
    dialog = { open: jest.fn() };
    snackBar = { open: jest.fn() };

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
    expect(el().querySelector('[data-testid="adhesion-en-attente"]')!.textContent).toContain('Apparaîtra une fois acceptée');
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

  it('demande confirmation avant d’envoyer la demande d’adhésion', async () => {
    await creer(etatFactice());
    const attente = etatFactice({ adhesion: { statut: 'en_attente', possible: false } });
    service.demanderAdhesion.mockReturnValue(of(attente));

    dialog.open.mockReturnValue({ afterClosed: () => of(false) });
    component.demanderAdhesion();
    expect(service.demanderAdhesion).not.toHaveBeenCalled();

    dialog.open.mockReturnValue({ afterClosed: () => of(true) });
    component.demanderAdhesion();
    expect(service.demanderAdhesion).toHaveBeenCalledTimes(1);
    expect(component.etat()?.adhesion.statut).toBe('en_attente');
  });

  it('affiche une snackbar traduite si la demande échoue', async () => {
    await creer(etatFactice());
    dialog.open.mockReturnValue({ afterClosed: () => of(true) });
    service.demanderAdhesion.mockReturnValue(throwError(() =>
      new HttpErrorResponse({ status: 400, error: { erreur: 'suivi_indisponible' } })));

    component.demanderAdhesion();
    expect(snackBar.open).toHaveBeenCalledWith('Suivi indisponible', expect.anything(), expect.anything());
    expect(component.demandeEnCours()).toBe(false);
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

  it('retombe sur erreur_inconnue sinon', () => {
    expect(cleErreurRaccordement(new HttpErrorResponse({ status: 500, error: { detail: 'boum' } }))).toBe('erreur_inconnue');
    expect(cleErreurRaccordement(null)).toBe('erreur_inconnue');
  });
});
