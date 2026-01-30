import { ApplicationConfig, provideZoneChangeDetection, ErrorHandler } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideTranslateService } from '@ngx-translate/core';
import { provideTranslateHttpLoader } from '@ngx-translate/http-loader';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { loggingInterceptor } from './core/interceptors/logging.interceptor';
import { impersonationInterceptor } from './core/interceptors/impersonation.interceptor';
import { GlobalErrorHandler } from './core/handlers/global-error.handler';

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
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
  ]
};
