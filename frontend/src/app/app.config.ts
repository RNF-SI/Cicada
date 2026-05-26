import { ApplicationConfig, provideZoneChangeDetection, ErrorHandler, LOCALE_ID } from '@angular/core';
import { provideRouter, withInMemoryScrolling } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideTranslateService } from '@ngx-translate/core';
import { provideTranslateHttpLoader } from '@ngx-translate/http-loader';
import { MAT_DATE_LOCALE, MAT_DATE_FORMATS, DateAdapter, MAT_NATIVE_DATE_FORMATS, NativeDateAdapter } from '@angular/material/core';
import { MAT_SNACK_BAR_DEFAULT_OPTIONS, MatSnackBarConfig } from '@angular/material/snack-bar';
import { registerLocaleData } from '@angular/common';
import localeFr from '@angular/common/locales/fr';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { loggingInterceptor } from './core/interceptors/logging.interceptor';
import { impersonationInterceptor } from './core/interceptors/impersonation.interceptor';
import { GlobalErrorHandler } from './core/handlers/global-error.handler';

// Enregistrer la locale francaise
registerLocaleData(localeFr);

// Format de date francais DD/MM/YYYY
const FR_DATE_FORMATS = {
  ...MAT_NATIVE_DATE_FORMATS,
  display: {
    ...MAT_NATIVE_DATE_FORMATS.display,
    dateInput: { day: 'numeric', month: 'numeric', year: 'numeric' } as Intl.DateTimeFormatOptions,
  },
};

// Snackbar : durée allongée + bouton fermer ajouté quand absent (revue design Amandine)
const SNACKBAR_DEFAULT_OPTIONS: MatSnackBarConfig = {
  duration: 6000,
  horizontalPosition: 'right',
  verticalPosition: 'bottom',
  panelClass: ['ccd-snackbar'],
};

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(
      routes,
      withInMemoryScrolling({
        scrollPositionRestoration: 'enabled',
        anchorScrolling: 'enabled',
      })
    ),
    provideAnimationsAsync(),
    // Note: loggingInterceptor doit etre avant authInterceptor pour capturer toutes les requetes
    // impersonationInterceptor doit etre apres authInterceptor pour verifier le statut d'impersonnation
    provideHttpClient(withInterceptors([loggingInterceptor, authInterceptor, impersonationInterceptor])),
    provideTranslateService({
      defaultLanguage: 'fr',
      loader: provideTranslateHttpLoader({
        prefix: './assets/i18n/',
        suffix: '.json'
      })
    }),
    // Global error handler pour capturer les erreurs non-catchees
    { provide: ErrorHandler, useClass: GlobalErrorHandler },
    // Locale francaise pour les dates et le datepicker Material
    { provide: LOCALE_ID, useValue: 'fr-FR' },
    { provide: MAT_DATE_LOCALE, useValue: 'fr-FR' },
    { provide: MAT_DATE_FORMATS, useValue: FR_DATE_FORMATS },
    { provide: DateAdapter, useClass: NativeDateAdapter },
    { provide: MAT_SNACK_BAR_DEFAULT_OPTIONS, useValue: SNACKBAR_DEFAULT_OPTIONS },
  ]
};
