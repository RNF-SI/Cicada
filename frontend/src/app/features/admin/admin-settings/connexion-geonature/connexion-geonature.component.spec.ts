import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { HttpErrorResponse } from '@angular/common/http';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { ConnexionGeoNatureComponent } from './connexion-geonature.component';
import {
  ConnexionGeoNatureService,
  EtatConnexionGeoNature,
  ResultatTest,
  commandeCompteLecture,
} from '../../../../core/services/connexion-geonature.service';

class FakeLoader implements TranslateLoader {
  getTranslation() {
    return of({});
  }
}

function etatFactice(surcharge: Partial<EtatConnexionGeoNature> = {}): EtatConnexionGeoNature {
  return {
    mode: 'local',
    configuree: true,
    base_sur_ce_serveur: false,
    valeurs: {
      libelle: 'RNF', organismes_exclus: '', code_application: 'CICADA', db_host: '10.0.30.12',
      db_port: 5432, db_name: 'geonature_global', db_user: 'cicada_usershub', db_sslmode: 'require',
    },
    mot_de_passe_defini: true,
    origines: {
      libelle: 'base', organismes_exclus: null, code_application: 'base', db_host: 'base', db_port: null,
      db_name: 'base', db_user: 'base', db_sslmode: 'base', db_password: 'base', mode: 'environnement',
    },
    modifie_le: null,
    modifie_par: null,
    ...surcharge,
  };
}

function testFactice(surcharge: Partial<ResultatTest> = {}): ResultatTest {
  return {
    ok: true, erreur: null, message: '', chiffree: true, application: true,
    bilan: { total: 3, autorises: 2, refuses: 1, super_admins_autorises: 1,
      comptes: [{ id: 1, email: 'refuse@test.fr', super_admin: false, motif: 'sans_droit' }] },
    vous: { autorise: true, motif: null },
    ...surcharge,
  };
}

describe('ConnexionGeoNatureComponent (#769)', () => {
  let fixture: ComponentFixture<ConnexionGeoNatureComponent>;
  let component: ConnexionGeoNatureComponent;
  let service: jest.Mocked<ConnexionGeoNatureService>;
  let dialog: { open: jest.Mock };

  const el = (testid: string): HTMLElement | null =>
    fixture.nativeElement.querySelector(`[data-testid="${testid}"]`);

  async function monter(etat = etatFactice()) {
    service = {
      etat: jest.fn().mockReturnValue(of(etat)),
      configurer: jest.fn().mockReturnValue(of(etat)),
      tester: jest.fn().mockReturnValue(of(testFactice())),
      activer: jest.fn().mockReturnValue(of(testFactice())),
      desactiver: jest.fn().mockReturnValue(of(etatFactice({ mode: 'local' }))),
    } as unknown as jest.Mocked<ConnexionGeoNatureService>;
    dialog = { open: jest.fn().mockReturnValue({ afterClosed: () => of(true) }) };
    await TestBed.configureTestingModule({
      imports: [ConnexionGeoNatureComponent, NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FakeLoader } })],
      providers: [
        { provide: ConnexionGeoNatureService, useValue: service },
        { provide: MatSnackBar, useValue: { open: jest.fn() } },
      ],
    }).overrideProvider(MatDialog, { useValue: dialog }).compileComponents();
    fixture = TestBed.createComponent(ConnexionGeoNatureComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  it('verrouille un champ fourni par le .env', async () => {
    const etat = etatFactice();
    etat.origines.db_host = 'environnement';
    await monter(etat);
    expect((el('champ-db_host') as HTMLInputElement).disabled).toBe(true);
    expect((el('champ-db_name') as HTMLInputElement).disabled).toBe(false);
  });

  it("n'envoie que les champs modifiés, et le mot de passe seulement s'il est saisi", async () => {
    await monter();
    component.saisie.db_name = 'autre_base';
    expect(component.modifications()).toEqual({ db_name: 'autre_base' });
    component.motDePasse = 'secret';
    component.enregistrer();
    expect(service.configurer).toHaveBeenCalledWith({ db_name: 'autre_base', db_password: 'secret' });
  });

  it('demande confirmation quand des comptes seront refusés, puis active', async () => {
    await monter();
    service.activer.mockReturnValueOnce(throwError(() => new HttpErrorResponse({
      status: 409, error: { code: 'confirmation_requise', detail: '…', test: testFactice() },
    })));
    component.activer();
    expect(dialog.open).toHaveBeenCalled();
    expect(service.activer).toHaveBeenLastCalledWith(true);
  });

  it("affiche le refus d'enfermement sans rien activer", async () => {
    await monter();
    service.activer.mockReturnValueOnce(throwError(() => new HttpErrorResponse({
      status: 409, error: { code: 'enfermement', detail: 'Vous seriez enfermé dehors',
        test: testFactice({ vous: { autorise: false, motif: 'sans_droit' } }) },
    })));
    component.activer();
    fixture.detectChanges();
    expect(dialog.open).not.toHaveBeenCalled();
    expect(el('connexion-erreur')?.textContent).toContain('Vous seriez enfermé dehors');
    expect(el('test-vous')).not.toBeNull();
  });

  it('propose de revenir aux comptes CICADA quand GeoNature est actif', async () => {
    await monter(etatFactice({ mode: 'geonature' }));
    expect(el('bouton-activer')).toBeNull();
    (el('bouton-desactiver') as HTMLButtonElement).click();
    expect(service.desactiver).toHaveBeenCalledWith(true);
  });

  it('affiche le bilan du test', async () => {
    await monter();
    component.tester();
    fixture.detectChanges();
    expect(el('connexion-test')).not.toBeNull();
    expect(el('test-bilan')).not.toBeNull();
  });
});

describe('commandeCompteLecture', () => {
  it('base sur ce serveur : --docker-local', () => {
    expect(commandeCompteLecture('geonature2db', 'CICADA', true, ''))
      .toBe('sudo cicada-usershub-lecture --db geonature2db --docker-local --code CICADA');
  });

  it('base distante : téléchargement du script et --client', () => {
    const commande = commandeCompteLecture('geonature_global', 'CICADA', false, '10.0.20.13');
    expect(commande).toContain('curl -fsSL https://raw.githubusercontent.com/');
    expect(commande).toContain('--db geonature_global --client 10.0.20.13/32 --code CICADA');
  });
});
