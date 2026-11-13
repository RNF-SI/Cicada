import { ComponentFixture, TestBed, fakeAsync, tick, discardPeriodicTasks } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { of } from 'rxjs';

import { AdminUpdateComponent } from './admin-update.component';
import { SystemUpdateService, SystemVersionInfo } from '../../../core/services/system-update.service';

const fr = require('../../../../assets/i18n/fr.json');

class FrLoader implements TranslateLoader {
  getTranslation() {
    return of(fr);
  }
}

const ECHEC_RETOUR_FAIT = {
  success: false,
  version: '0.1.70',
  timestamp: '2026-11-06T10:05:00+01:00',
  error: "L'application ne démarre pas : ProgrammingError — retour à la version 0.1.69 effectué",
  statut: 'echec_retour_fait' as const,
  depart: '0.1.69',
  cible: '0.1.70',
  retour_arriere: true,
  commande: null,
};

function info(partiel: Partial<SystemVersionInfo>): SystemVersionInfo {
  return {
    current_version: '0.1.69',
    update_available: true,
    latest_version: '0.1.70',
    last_check: null,
    last_update: null,
    last_backup: null,
    ...partiel,
  };
}

/**
 * #796 — la page dit ce qu'est devenue la dernière mise à jour (annulée,
 * retour arrière fait, application arrêtée) et quand date la dernière sauvegarde.
 */
describe('AdminUpdateComponent', () => {
  let fixture: ComponentFixture<AdminUpdateComponent>;
  let service: {
    getVersion: jest.Mock; pollVersion: jest.Mock; triggerUpdate: jest.Mock;
    checkForUpdate: jest.Mock; markUpdateInProgress: jest.Mock; markUpdateFinished: jest.Mock;
  };

  function creer(version: SystemVersionInfo): HTMLElement {
    service.getVersion.mockReturnValue(of(version));
    fixture = TestBed.createComponent(AdminUpdateComponent);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(async () => {
    service = {
      getVersion: jest.fn(), pollVersion: jest.fn(), triggerUpdate: jest.fn(),
      checkForUpdate: jest.fn(), markUpdateInProgress: jest.fn(), markUpdateFinished: jest.fn(),
    };
    await TestBed.configureTestingModule({
      imports: [
        AdminUpdateComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({ loader: { provide: TranslateLoader, useClass: FrLoader }, fallbackLang: 'fr' }),
      ],
      providers: [{ provide: SystemUpdateService, useValue: service }],
    }).compileComponents();
  });

  it("rappelle à l'ouverture un échec avec retour arrière", () => {
    const page = creer(info({ last_update: ECHEC_RETOUR_FAIT }));

    const bloc = page.querySelector('[data-testid="update-last-failure"]');
    expect(bloc?.textContent).toContain(
      "La mise à jour vers la version 0.1.70 a échoué : la version 0.1.69 a été rétablie automatiquement"
    );
    expect(bloc?.textContent).toContain('ProgrammingError');
    // La mise à jour reste proposée : relancer une fois la cause corrigée
    expect(page.textContent).toContain('Mettre à jour');
  });

  it("donne la commande de reprise quand l'application est restée arrêtée", () => {
    const page = creer(info({
      last_update: { ...ECHEC_RETOUR_FAIT, statut: 'echec_sans_retour', retour_arriere: false,
                     commande: 'sudo cicada-update rollback' },
    }));

    const bloc = page.querySelector('[data-testid="update-last-failure"]');
    expect(bloc?.textContent).toContain("l'application est arrêtée");
    expect(bloc?.querySelector('code')?.textContent).toBe('sudo cicada-update rollback');
  });

  it("renvoie au guide d'administration après un échec", () => {
    const page = creer(info({ last_update: ECHEC_RETOUR_FAIT }));

    const lien = page.querySelector<HTMLAnchorElement>(
      '[data-testid="update-last-failure"] [data-testid="update-help-link"]'
    );
    expect(lien?.getAttribute('href')).toBe('/aide/administration/installation/#maj-mal-passee');
    expect(lien?.textContent).toContain('Une mise à jour s\'est mal passée');
  });

  it("n'affiche plus l'échec une fois la version en service", () => {
    const page = creer(info({ current_version: '0.1.70', update_available: false, last_update: ECHEC_RETOUR_FAIT }));
    expect(page.querySelector('[data-testid="update-last-failure"]')).toBeNull();
  });

  it("n'affiche rien pour un résultat d'un paquet antérieur (sans statut)", () => {
    const page = creer(info({ last_update: { success: false, timestamp: 'x', error: 'code 100' } }));
    expect(page.querySelector('[data-testid="update-last-failure"]')).toBeNull();
  });

  it("n'affiche pas d'échec après un retour demandé par l'administrateur (#800)", () => {
    const page = creer(info({
      current_version: '0.1.69',
      last_update: { ...ECHEC_RETOUR_FAIT, success: true, statut: 'retour_demande', cible: '0.1.70',
                     error: 'Retour demandé à la version 0.1.69' },
    }));
    expect(page.querySelector('[data-testid="update-last-failure"]')).toBeNull();
    expect(page.textContent).toContain('Mettre à jour');
  });

  it("signale un service resté en échec après une mise à jour réussie", () => {
    const page = creer(info({
      current_version: '0.1.70', update_available: false,
      last_update: { success: true, timestamp: 'x', statut: 'reussie', cible: '0.1.70',
                     avertissement: 'Service(s) celery-worker déjà en échec avant la mise à jour' },
    }));
    const bloc = page.querySelector('[data-testid="update-last-warning"]');
    expect(bloc?.textContent).toContain('celery-worker');
    expect(page.querySelector('[data-testid="update-last-failure"]')).toBeNull();
  });

  it('affiche la dernière sauvegarde', () => {
    const page = creer(info({
      last_backup: { nombre: 3, dossier: '/var/backups/cicada', derniere: {
        nom: 'x', date: '2026-11-06T00:52:00+01:00', raison: 'quotidienne', version: '0.1.69', taille: 46 * 1024 ** 2 } },
    }));
    const ligne = page.querySelector('[data-testid="update-last-backup"]')?.textContent ?? '';
    expect(ligne).toContain('46 Mo');
    expect(ligne).toContain('3 conservée(s)');
  });

  it("sans sauvegarde connue, le dit", () => {
    const page = creer(info({}));
    expect(page.querySelector('[data-testid="update-last-backup"]')?.textContent).toContain("aucune pour l'instant");
  });

  it("après le clic, titre l'échec selon son issue", fakeAsync(() => {
    jest.spyOn(window, 'confirm').mockReturnValue(true);
    const page = creer(info({}));
    service.triggerUpdate.mockReturnValue(of({ success: true }));
    service.pollVersion.mockReturnValue(of(info({
      last_update: { ...ECHEC_RETOUR_FAIT, statut: 'annulee', error: "Téléchargement impossible — rien n'a changé" },
    })));

    fixture.componentInstance.triggerUpdate();
    tick(5000);
    fixture.detectChanges();

    expect(fixture.componentInstance.phase()).toBe('failed');
    expect(page.textContent).toContain("La mise à jour vers la version 0.1.70 a été annulée : rien n'a changé.");
    expect(page.textContent).toContain('sudo cicada-update status');
    discardPeriodicTasks();
  }));
});
