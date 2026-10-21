import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal } from '@angular/core';
import { TranslateModule } from '@ngx-translate/core';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { CguGateComponent } from './cgu-gate.component';
import { AuthService } from '../../../core/services/auth.service';
import { SettingsService } from '../../../core/services/settings.service';

describe('CguGateComponent (#746)', () => {
  let fixture: ComponentFixture<CguGateComponent>;
  let component: CguGateComponent;
  const user = signal<{ cgu_a_accepter?: boolean } | null>({ cgu_a_accepter: true });
  const impersonating = signal(false);
  const config = signal<{ cgu_texte: string; cgu_version: string } | null>({
    cgu_texte: '# CGU\n\nTexte', cgu_version: '2026-10-21T10:00:00Z',
  });
  const auth = {
    currentUser: user,
    isImpersonating: impersonating,
    accepterCgu: jest.fn().mockReturnValue(of({ cgu_a_accepter: false })),
    logout: jest.fn().mockReturnValue(of(undefined)),
  };
  const settings = { config, loadSettings: jest.fn().mockReturnValue(of({})) };

  beforeEach(() => {
    user.set({ cgu_a_accepter: true });
    impersonating.set(false);
    auth.accepterCgu.mockClear();
    TestBed.configureTestingModule({
      imports: [CguGateComponent, TranslateModule.forRoot(), NoopAnimationsModule],
      providers: [
        { provide: AuthService, useValue: auth },
        { provide: SettingsService, useValue: settings },
        { provide: Router, useValue: { navigate: jest.fn() } },
      ],
    });
    fixture = TestBed.createComponent(CguGateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  const dialogue = (): HTMLElement | null => fixture.nativeElement.querySelector('[data-testid="cgu-gate"]');

  it('s\'affiche tant que l\'utilisateur n\'a pas accepté la version en vigueur', () => {
    expect(dialogue()).not.toBeNull();
    expect(dialogue()!.textContent).toContain('Texte');
  });

  it('ne s\'affiche pas une fois les CGU acceptées, ni sans utilisateur', () => {
    user.set({ cgu_a_accepter: false });
    fixture.detectChanges();
    expect(dialogue()).toBeNull();
    user.set(null);
    fixture.detectChanges();
    expect(dialogue()).toBeNull();
  });

  it('ne s\'affiche pas pendant une impersonation', () => {
    impersonating.set(true);
    fixture.detectChanges();
    expect(dialogue()).toBeNull();
  });

  it('n\'accepte qu\'après la case cochée, avec la version lue', () => {
    component.accepter();
    expect(auth.accepterCgu).not.toHaveBeenCalled();
    component.coche.set(true);
    component.accepter();
    expect(auth.accepterCgu).toHaveBeenCalledWith('2026-10-21T10:00:00Z');
  });

  it('CGU modifiées pendant la lecture : recharge le texte et décoche', () => {
    auth.accepterCgu.mockReturnValueOnce(throwError(() => ({ status: 409 })));
    component.coche.set(true);
    component.accepter();
    expect(settings.loadSettings).toHaveBeenCalled();
    expect(component.coche()).toBe(false);
    expect(component.erreur()).toBeTruthy();
  });
});
