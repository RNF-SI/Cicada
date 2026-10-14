import { ComponentFixture, TestBed } from '@angular/core/testing';
import { TranslateLoader, TranslateModule } from '@ngx-translate/core';
import { of } from 'rxjs';

import { TestVersionBannerComponent } from './test-version-banner.component';
// eslint-disable-next-line @typescript-eslint/no-require-imports
const fr = require('../../../../assets/i18n/fr.json');

class FrLoader implements TranslateLoader {
  getTranslation() {
    return of(fr);
  }
}

describe('TestVersionBannerComponent (#709)', () => {
  let fixture: ComponentFixture<TestVersionBannerComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        TestVersionBannerComponent,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FrLoader },
          fallbackLang: 'fr',
        }),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(TestVersionBannerComponent);
  });

  const text = (): string => fixture.nativeElement.textContent;

  it('affiche par défaut le bandeau « version test »', () => {
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('[data-testid="test-version-banner"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="test-version-notice"]')).toBeNull();
    expect(text()).toContain('version de test');
  });

  it('prévient sur connexion / inscription que les nouveaux comptes ne sont pas validés', () => {
    fixture.componentRef.setInput('variant', 'accounts');
    fixture.detectChanges();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('[data-testid="test-version-notice"]')).not.toBeNull();
    expect(el.querySelector('[data-testid="test-version-banner"]')).toBeNull();
    expect(text()).toContain('ne seront pas validés');
    expect(text()).toContain('ouverture');
  });
});
