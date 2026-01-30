import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router, ActivatedRoute, provideRouter } from '@angular/router';
import { Component, signal, WritableSignal } from '@angular/core';
import { TranslateModule, TranslateLoader } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { LoginComponent } from './login.component';
import { AuthService } from '../../core/services/auth.service';

// Dummy component for routes
@Component({ template: '' })
class DummyComponent {}

// Fake translate loader for testing
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'auth.login.title': 'Connexion',
      'auth.login.username': 'Email',
      'auth.login.password': 'Mot de passe',
      'auth.login.submit': 'Se connecter',
      'auth.login.register': 'Créer un compte'
    });
  }
}

describe('LoginComponent', () => {
  let component: LoginComponent;
  let fixture: ComponentFixture<LoginComponent>;
  let router: Router;

  let loginMock: jest.Mock;
  let isLoadingSignal: WritableSignal<boolean>;

  const setupTestBed = async (returnUrl: string | null = null) => {
    loginMock = jest.fn().mockReturnValue(of({ access: 'token', refresh: 'refresh' }));
    isLoadingSignal = signal(false);

    const authServiceMock = {
      login: loginMock,
      isLoading: isLoadingSignal.asReadonly()
    };

    const activatedRouteMock = {
      snapshot: {
        queryParams: returnUrl ? { returnUrl } : {}
      }
    };

    await TestBed.configureTestingModule({
      imports: [
        LoginComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader }
        })
      ],
      providers: [
        provideRouter([
          { path: '', component: DummyComponent },
          { path: 'accueil', component: DummyComponent },
          { path: 'auth/login', component: DummyComponent },
          { path: 'auth/register', component: DummyComponent },
          { path: 'admin/users', component: DummyComponent },
          { path: 'sites/:id', component: DummyComponent }
        ]),
        { provide: AuthService, useValue: authServiceMock },
        { provide: ActivatedRoute, useValue: activatedRouteMock }
      ]
    }).compileComponents();

    router = TestBed.inject(Router);
    // Spy on navigateByUrl to verify navigation without actually navigating
    jest.spyOn(router, 'navigateByUrl').mockReturnValue(Promise.resolve(true));

    fixture = TestBed.createComponent(LoginComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should initialize form with empty values', () => {
      expect(component.loginForm.get('username')?.value).toBe('');
      expect(component.loginForm.get('password')?.value).toBe('');
    });

    it('should start with password hidden', () => {
      expect(component.hidePassword()).toBe(true);
    });

    it('should start with no error message', () => {
      expect(component.errorMessage()).toBeNull();
    });
  });

  // ==================== FORM VALIDATION ====================

  describe('Form Validation', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should require username', () => {
      const control = component.loginForm.get('username');
      control?.setValue('');
      expect(control?.valid).toBe(false);

      control?.setValue('user@test.fr');
      expect(control?.valid).toBe(true);
    });

    it('should require password', () => {
      const control = component.loginForm.get('password');
      control?.setValue('');
      expect(control?.valid).toBe(false);

      control?.setValue('password123');
      expect(control?.valid).toBe(true);
    });

    it('should be invalid when form is empty', () => {
      expect(component.loginForm.valid).toBe(false);
    });

    it('should be valid when both fields are filled', () => {
      component.loginForm.patchValue({
        username: 'user@test.fr',
        password: 'password123'
      });

      expect(component.loginForm.valid).toBe(true);
    });

    it('should mark form as touched on invalid submit', () => {
      component.loginForm.patchValue({
        username: '',
        password: ''
      });

      component.onSubmit();

      expect(component.loginForm.get('username')?.touched).toBe(true);
      expect(component.loginForm.get('password')?.touched).toBe(true);
    });
  });

  // ==================== PASSWORD VISIBILITY ====================

  describe('Password Visibility', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should toggle password visibility', () => {
      expect(component.hidePassword()).toBe(true);

      component.togglePasswordVisibility();
      expect(component.hidePassword()).toBe(false);

      component.togglePasswordVisibility();
      expect(component.hidePassword()).toBe(true);
    });
  });

  // ==================== LOGIN SUBMISSION ====================

  describe('Login Submission', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should not submit when form is invalid', () => {
      component.loginForm.patchValue({
        username: '',
        password: ''
      });

      component.onSubmit();

      expect(loginMock).not.toHaveBeenCalled();
    });

    it('should call authService.login with credentials', fakeAsync(() => {
      component.loginForm.patchValue({
        username: 'user@test.fr',
        password: 'password123'
      });

      component.onSubmit();
      tick();

      expect(loginMock).toHaveBeenCalledWith({
        username: 'user@test.fr',
        password: 'password123'
      });
    }));

    it('should clear error message before submitting', fakeAsync(() => {
      component.errorMessage.set('Previous error');

      component.loginForm.patchValue({
        username: 'user@test.fr',
        password: 'password123'
      });

      component.onSubmit();

      expect(component.errorMessage()).toBeNull();

      tick();
    }));
  });

  // ==================== NAVIGATION AFTER LOGIN ====================

  describe('Navigation after login', () => {
    it('should navigate to /accueil after successful login (no return URL)', async () => {
      await setupTestBed(); // No return URL

      component.loginForm.patchValue({
        username: 'user@test.fr',
        password: 'password123'
      });

      component.onSubmit();
      await fixture.whenStable();

      expect(router.navigateByUrl).toHaveBeenCalledWith('/accueil');
    });

    it('should navigate to return URL after successful login', async () => {
      await setupTestBed('/admin/users'); // With return URL

      component.loginForm.patchValue({
        username: 'user@test.fr',
        password: 'password123'
      });

      component.onSubmit();
      await fixture.whenStable();

      expect(router.navigateByUrl).toHaveBeenCalledWith('/admin/users');
    });

    it('should navigate to custom return URL after successful login', async () => {
      await setupTestBed('/sites/123'); // Custom return URL

      component.loginForm.patchValue({
        username: 'user@test.fr',
        password: 'password123'
      });

      component.onSubmit();
      await fixture.whenStable();

      expect(router.navigateByUrl).toHaveBeenCalledWith('/sites/123');
    });
  });

  // ==================== ERROR HANDLING ====================

  describe('Error Handling', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should display error message on login failure', fakeAsync(() => {
      loginMock.mockReturnValue(throwError(() => new Error('Invalid credentials')));

      component.loginForm.patchValue({
        username: 'user@test.fr',
        password: 'wrongpassword'
      });

      component.onSubmit();
      tick();

      expect(component.errorMessage()).toBe('Invalid credentials');
    }));

    it('should not navigate on login failure', fakeAsync(() => {
      loginMock.mockReturnValue(throwError(() => new Error('Invalid credentials')));

      component.loginForm.patchValue({
        username: 'user@test.fr',
        password: 'wrongpassword'
      });

      component.onSubmit();
      tick();

      expect(router.navigateByUrl).not.toHaveBeenCalled();
    }));

    it('should handle network errors', fakeAsync(() => {
      loginMock.mockReturnValue(throwError(() => new Error('Network error')));

      component.loginForm.patchValue({
        username: 'user@test.fr',
        password: 'password123'
      });

      component.onSubmit();
      tick();

      expect(component.errorMessage()).toBe('Network error');
    }));
  });

  // ==================== LOADING STATE ====================

  describe('Loading State', () => {
    beforeEach(async () => {
      await setupTestBed();
    });

    it('should expose isLoading from authService', () => {
      expect(component.isLoading()).toBe(false);

      isLoadingSignal.set(true);
      expect(component.isLoading()).toBe(true);

      isLoadingSignal.set(false);
      expect(component.isLoading()).toBe(false);
    });
  });
});
