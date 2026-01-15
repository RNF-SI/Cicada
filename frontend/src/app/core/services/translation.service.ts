import { Injectable, inject } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';

@Injectable({ providedIn: 'root' })
export class TranslationService {
  private translate = inject(TranslateService);

  readonly supportedLanguages = ['fr', 'en'];
  readonly defaultLanguage = 'fr';

  initialize(): void {
    this.translate.setDefaultLang(this.defaultLanguage);
    const savedLang = localStorage.getItem('app-language');
    const browserLang = this.translate.getBrowserLang();
    const langToUse = savedLang || (this.supportedLanguages.includes(browserLang || '') ? browserLang : this.defaultLanguage);
    this.translate.use(langToUse || this.defaultLanguage);
  }

  setLanguage(lang: string): void {
    if (this.supportedLanguages.includes(lang)) {
      this.translate.use(lang);
      localStorage.setItem('app-language', lang);
    }
  }

  getCurrentLanguage(): string {
    return this.translate.currentLang || this.defaultLanguage;
  }

  instant(key: string, params?: object): string {
    return this.translate.instant(key, params);
  }

  get(key: string, params?: object) {
    return this.translate.get(key, params);
  }
}
