import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { TranslateModule } from '@ngx-translate/core';
import { of } from 'rxjs';

import { AuthService } from '../../../core/services/auth.service';
import { ExplorationService } from '../../../core/services/exploration.service';
import { SettingsService } from '../../../core/services/settings.service';
import { PorteeBanniereComponent } from './portee-banniere.component';

describe('PorteeBanniereComponent (#636)', () => {
  let fixture: ComponentFixture<PorteeBanniereComponent>;

  async function setup(options: {
    partage: boolean;
    superAdmin: boolean;
    structures?: number;
  }) {
    const instances = Array.from({ length: options.structures ?? 1 }, (_, i) => ({
      instance_id: `i${i}`,
      instance_libelle: `Structure ${i}`,
    }));

    await TestBed.resetTestingModule()
      .configureTestingModule({
        imports: [PorteeBanniereComponent, TranslateModule.forRoot()],
        providers: [
          provideRouter([]),
          {
            provide: SettingsService,
            useValue: { partageFederationActif: () => options.partage },
          },
          { provide: AuthService, useValue: { isSuperAdmin: () => options.superAdmin } },
          { provide: ExplorationService, useValue: { instances: () => of(instances) } },
        ],
      })
      .compileComponents();

    fixture = TestBed.createComponent(PorteeBanniereComponent);
    fixture.detectChanges();
  }

  const trouver = (testId: string): HTMLElement | null =>
    fixture.nativeElement.querySelector(`[data-testid="${testId}"]`);

  describe('partage inactif', () => {
    it('affiche le message permanent et le lien d\'activation pour un super admin', async () => {
      await setup({ partage: false, superAdmin: true });

      const bloc = trouver('exploration-perimetre-local');
      expect(bloc).not.toBeNull();
      expect(bloc!.classList).toContain('info-block');
      expect(bloc!.textContent).toContain('exploration.perimetreNational.locale.incitation');
      expect(bloc!.textContent).toContain('exploration.perimetreNational.locale.rassurance');
      // Non refermable : aucun bouton de fermeture.
      expect(bloc!.querySelector('button')).toBeNull();

      const lien = trouver('exploration-perimetre-activer') as HTMLAnchorElement;
      expect(lien).not.toBeNull();
      expect(lien.getAttribute('href')).toBe('/administration/parametres?onglet=exploration');
      expect(trouver('exploration-perimetre-contact')).toBeNull();
      expect(trouver('exploration-perimetre-national')).toBeNull();
    });

    it('invite à contacter l\'administrateur, sans lien, pour un autre rôle', async () => {
      await setup({ partage: false, superAdmin: false });

      expect(trouver('exploration-perimetre-local')).not.toBeNull();
      expect(trouver('exploration-perimetre-activer')).toBeNull();
      expect(trouver('exploration-perimetre-contact')!.textContent).toContain(
        'exploration.perimetreNational.locale.contactAdmin',
      );
    });
  });

  describe('partage actif', () => {
    it('affiche une ligne discrète chiffrée, sans message d\'incitation', async () => {
      await setup({ partage: true, superAdmin: true, structures: 4 });

      expect(trouver('exploration-perimetre-local')).toBeNull();
      expect(trouver('exploration-perimetre-activer')).toBeNull();
      expect(trouver('exploration-perimetre-national')!.textContent).toContain(
        'exploration.perimetreNational.nationaleDetail',
      );
    });

    it('reste générique tant qu\'une seule structure est connue', async () => {
      await setup({ partage: true, superAdmin: false, structures: 1 });

      const ligne = trouver('exploration-perimetre-national')!;
      expect(ligne.textContent).toContain('exploration.perimetreNational.nationale');
      expect(ligne.textContent).not.toContain('nationaleDetail');
    });
  });
});
