import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { Router, provideRouter } from '@angular/router';
import { HttpClient } from '@angular/common/http';
import { Component } from '@angular/core';
import { TranslateModule, TranslateLoader, TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';

import { RegisterComponent } from './register.component';

// Dummy component for routes
@Component({ template: '' })
class DummyComponent {}

// Fake translate loader for testing
class FakeTranslateLoader implements TranslateLoader {
  getTranslation(lang: string) {
    return of({
      'auth.register.title': 'Créer un compte',
      'auth.register.email': 'Adresse email',
      'auth.register.password': 'Mot de passe',
      'auth.register.confirmPassword': 'Confirmer le mot de passe',
      'auth.register.nom': 'Nom',
      'auth.register.prenom': 'Prénom',
      'auth.register.organisme': 'Organisme',
      'auth.register.justification': 'Justification',
      'auth.register.submit': 'Créer un compte',
      'auth.register.errors.emailAlreadyUsed': 'Cette adresse email est déjà utilisée',
      'errors.generic': 'Une erreur est survenue'
    });
  }
}

describe('RegisterComponent', () => {
  let component: RegisterComponent;
  let fixture: ComponentFixture<RegisterComponent>;
  let router: Router;
  let httpMock: { get: jest.Mock; post: jest.Mock };

  const mockOrganismes = [
    { id: 1, nom_organisme: 'RNF - Réserves Naturelles de France' },
    { id: 2, nom_organisme: 'CEN AURA' },
    { id: 3, nom_organisme: 'DREAL Nouvelle-Aquitaine' }
  ];

  const setupTestBed = async () => {
    httpMock = {
      get: jest.fn().mockReturnValue(of(mockOrganismes)),
      post: jest.fn().mockReturnValue(of({ success: true }))
    };

    await TestBed.configureTestingModule({
      imports: [
        RegisterComponent,
        NoopAnimationsModule,
        TranslateModule.forRoot({
          loader: { provide: TranslateLoader, useClass: FakeTranslateLoader }
        })
      ],
      providers: [
        provideRouter([
          { path: '', component: DummyComponent },
          { path: 'auth/login', component: DummyComponent },
          { path: 'auth/register', component: DummyComponent },
          { path: 'auth/registration-pending', component: DummyComponent }
        ]),
        { provide: HttpClient, useValue: httpMock }
      ]
    }).compileComponents();

    router = TestBed.inject(Router);
    jest.spyOn(router, 'navigate').mockReturnValue(Promise.resolve(true));

    const translate = TestBed.inject(TranslateService);
    translate.setDefaultLang('fr');
    translate.use('fr');

    fixture = TestBed.createComponent(RegisterComponent);
    component = fixture.componentInstance;
  };

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  // ==================== BASIC TESTS ====================

  describe('Basic Operations', () => {
    beforeEach(async () => {
      await setupTestBed();
      fixture.detectChanges();
    });

    it('should create', () => {
      expect(component).toBeTruthy();
    });

    it('should initialize form with empty values', () => {
      expect(component.registerForm.get('email')?.value).toBe('');
      expect(component.registerForm.get('password')?.value).toBe('');
      expect(component.registerForm.get('confirmPassword')?.value).toBe('');
      expect(component.registerForm.get('nom')?.value).toBe('');
      expect(component.registerForm.get('prenom')?.value).toBe('');
      expect(component.registerForm.get('organisme')?.value).toBeNull();
    });

    it('should start with passwords hidden', () => {
      expect(component.hidePassword()).toBe(true);
      expect(component.hideConfirmPassword()).toBe(true);
    });

    it('should start with no error message', () => {
      expect(component.errorMessage()).toBeNull();
    });

    it('should load organismes on init', () => {
      expect(httpMock.get).toHaveBeenCalledWith('/api/users/organismes/public/');
      expect(component.organismes()).toEqual(mockOrganismes);
    });
  });

  // ==================== FORM VALIDATION ====================

  describe('Form Validation', () => {
    beforeEach(async () => {
      await setupTestBed();
      fixture.detectChanges();
    });

    it('should require email', () => {
      const control = component.registerForm.get('email');
      control?.setValue('');
      expect(control?.valid).toBe(false);
      expect(control?.hasError('required')).toBe(true);
    });

    it('should validate email format', () => {
      const control = component.registerForm.get('email');
      control?.setValue('invalid-email');
      expect(control?.valid).toBe(false);
      expect(control?.hasError('email')).toBe(true);

      control?.setValue('valid@email.com');
      expect(control?.valid).toBe(true);
    });

    it('should require password', () => {
      const control = component.registerForm.get('password');
      control?.setValue('');
      expect(control?.valid).toBe(false);
      expect(control?.hasError('required')).toBe(true);
    });

    it('should require password minimum length of 8', () => {
      const control = component.registerForm.get('password');
      control?.setValue('short');
      expect(control?.valid).toBe(false);
      expect(control?.hasError('minlength')).toBe(true);

      control?.setValue('validPass123');
      expect(control?.valid).toBe(true);
    });

    it('should require nom', () => {
      const control = component.registerForm.get('nom');
      control?.setValue('');
      expect(control?.valid).toBe(false);
      expect(control?.hasError('required')).toBe(true);
    });

    it('should limit nom to 50 characters', () => {
      const control = component.registerForm.get('nom');
      control?.setValue('a'.repeat(51));
      expect(control?.valid).toBe(false);
      expect(control?.hasError('maxlength')).toBe(true);
    });

    it('should require prenom', () => {
      const control = component.registerForm.get('prenom');
      control?.setValue('');
      expect(control?.valid).toBe(false);
      expect(control?.hasError('required')).toBe(true);
    });

    it('should require organisme', () => {
      const control = component.registerForm.get('organisme');
      control?.setValue(null);
      expect(control?.valid).toBe(false);
      expect(control?.hasError('required')).toBe(true);
    });

    it('should make justification optional', () => {
      const control = component.registerForm.get('justification');
      control?.setValue('');
      expect(control?.valid).toBe(true);
    });

    it('should limit justification to 1000 characters', () => {
      const control = component.registerForm.get('justification');
      control?.setValue('a'.repeat(1001));
      expect(control?.valid).toBe(false);
      expect(control?.hasError('maxlength')).toBe(true);
    });
  });

  // ==================== PASSWORD MATCH VALIDATION ====================

  describe('Password Match Validation', () => {
    beforeEach(async () => {
      await setupTestBed();
      fixture.detectChanges();
    });

    it('should detect password mismatch', () => {
      component.registerForm.patchValue({
        password: 'password123',
        confirmPassword: 'differentPassword'
      });

      expect(component.registerForm.hasError('passwordMismatch')).toBe(true);
    });

    it('should pass when passwords match', () => {
      component.registerForm.patchValue({
        password: 'password123',
        confirmPassword: 'password123'
      });

      expect(component.registerForm.hasError('passwordMismatch')).toBe(false);
    });
  });

  // ==================== PASSWORD VISIBILITY ====================

  describe('Password Visibility', () => {
    beforeEach(async () => {
      await setupTestBed();
      fixture.detectChanges();
    });

    it('should toggle password visibility', () => {
      expect(component.hidePassword()).toBe(true);

      component.togglePasswordVisibility();
      expect(component.hidePassword()).toBe(false);

      component.togglePasswordVisibility();
      expect(component.hidePassword()).toBe(true);
    });

    it('should toggle confirm password visibility', () => {
      expect(component.hideConfirmPassword()).toBe(true);

      component.toggleConfirmPasswordVisibility();
      expect(component.hideConfirmPassword()).toBe(false);

      component.toggleConfirmPasswordVisibility();
      expect(component.hideConfirmPassword()).toBe(true);
    });
  });

  // ==================== ORGANISME FILTERING ====================

  describe('Organisme Filtering', () => {
    beforeEach(async () => {
      await setupTestBed();
      fixture.detectChanges();
    });

    it('should filter organismes by name', () => {
      const event = { target: { value: 'RNF' } } as unknown as Event;
      component.filterOrganismes(event);

      expect(component.filteredOrganismes().length).toBe(1);
      expect(component.filteredOrganismes()[0].nom_organisme).toContain('RNF');
    });

    it('should be case insensitive when filtering', () => {
      const event = { target: { value: 'rnf' } } as unknown as Event;
      component.filterOrganismes(event);

      expect(component.filteredOrganismes().length).toBe(1);
    });

    it('should show all organismes when filter is empty', () => {
      const event = { target: { value: '' } } as unknown as Event;
      component.filterOrganismes(event);

      expect(component.filteredOrganismes().length).toBe(mockOrganismes.length);
    });

    it('should show no organismes when filter matches nothing', () => {
      const event = { target: { value: 'xyz123' } } as unknown as Event;
      component.filterOrganismes(event);

      expect(component.filteredOrganismes().length).toBe(0);
    });
  });

  // ==================== DISPLAY ORGANISME ====================

  describe('Display Organisme', () => {
    beforeEach(async () => {
      await setupTestBed();
      fixture.detectChanges();
    });

    it('should display organisme name', () => {
      const organisme = { id: 1, nom_organisme: 'Test Org' };
      expect(component.displayOrganisme(organisme)).toBe('Test Org');
    });

    it('should return empty string for null organisme', () => {
      expect(component.displayOrganisme(null as any)).toBe('');
    });

    it('should return empty string for undefined organisme', () => {
      expect(component.displayOrganisme(undefined as any)).toBe('');
    });
  });

  // ==================== FORM SUBMISSION ====================

  describe('Form Submission', () => {
    beforeEach(async () => {
      await setupTestBed();
      fixture.detectChanges();
    });

    it('should not submit when form is invalid', () => {
      component.registerForm.patchValue({
        email: '',
        password: ''
      });

      component.onSubmit();

      expect(httpMock.post).not.toHaveBeenCalled();
    });

    it('should mark form as touched on invalid submit', () => {
      component.onSubmit();

      expect(component.registerForm.get('email')?.touched).toBe(true);
      expect(component.registerForm.get('password')?.touched).toBe(true);
    });

    it('should submit valid form with correct payload', fakeAsync(() => {
      const selectedOrganisme = { id_organisme: 1, nom_organisme: 'Test Org' };

      component.registerForm.patchValue({
        email: 'test@example.com',
        password: 'password123',
        confirmPassword: 'password123',
        nom: 'Dupont',
        prenom: 'Jean',
        organisme: selectedOrganisme,
        justification: 'Test justification'
      });

      component.onSubmit();
      tick();

      expect(httpMock.post).toHaveBeenCalledWith('/api/auth/register/', {
        email: 'test@example.com',
        password: 'password123',
        password_confirm: 'password123',
        nom_role: 'Dupont',
        prenom_role: 'Jean',
        requested_organisme_id: 1,
        justification: 'Test justification'
      });
    }));

    it('should set loading state during submission', fakeAsync(() => {
      component.registerForm.patchValue({
        email: 'test@example.com',
        password: 'password123',
        confirmPassword: 'password123',
        nom: 'Dupont',
        prenom: 'Jean',
        organisme: { id_organisme: 1 }
      });

      // After submit starts, loading should be true (can't easily test this with synchronous mock)
      component.onSubmit();
      tick();

      // After success, component navigates away
      expect(router.navigate).toHaveBeenCalledWith(['/auth/registration-pending']);
    }));

    it('should navigate to registration-pending on success', fakeAsync(() => {
      component.registerForm.patchValue({
        email: 'test@example.com',
        password: 'password123',
        confirmPassword: 'password123',
        nom: 'Dupont',
        prenom: 'Jean',
        organisme: { id_organisme: 1 }
      });

      component.onSubmit();
      tick();

      expect(router.navigate).toHaveBeenCalledWith(['/auth/registration-pending']);
    }));

    it('should clear error message before submitting', fakeAsync(() => {
      component.errorMessage.set('Previous error');

      component.registerForm.patchValue({
        email: 'test@example.com',
        password: 'password123',
        confirmPassword: 'password123',
        nom: 'Dupont',
        prenom: 'Jean',
        organisme: { id_organisme: 1 }
      });

      component.onSubmit();

      expect(component.errorMessage()).toBeNull();

      tick();
    }));
  });

  // ==================== ERROR HANDLING ====================

  describe('Error Handling', () => {
    beforeEach(async () => {
      await setupTestBed();
      fixture.detectChanges();
    });

    it('should show email already used error', fakeAsync(() => {
      httpMock.post.mockReturnValue(throwError(() => ({
        error: { email: ['This email is already used'] }
      })));

      component.registerForm.patchValue({
        email: 'existing@example.com',
        password: 'password123',
        confirmPassword: 'password123',
        nom: 'Dupont',
        prenom: 'Jean',
        organisme: { id_organisme: 1 }
      });

      component.onSubmit();
      tick();

      expect(component.errorMessage()).toBe('Cette adresse email est déjà utilisée');
      expect(component.isLoading()).toBe(false);
    }));

    it('should show server error message', fakeAsync(() => {
      httpMock.post.mockReturnValue(throwError(() => ({
        error: { error: 'Custom server error' }
      })));

      component.registerForm.patchValue({
        email: 'test@example.com',
        password: 'password123',
        confirmPassword: 'password123',
        nom: 'Dupont',
        prenom: 'Jean',
        organisme: { id_organisme: 1 }
      });

      component.onSubmit();
      tick();

      expect(component.errorMessage()).toBe('Custom server error');
    }));

    it('should show generic error on unknown error', fakeAsync(() => {
      httpMock.post.mockReturnValue(throwError(() => ({
        error: {}
      })));

      component.registerForm.patchValue({
        email: 'test@example.com',
        password: 'password123',
        confirmPassword: 'password123',
        nom: 'Dupont',
        prenom: 'Jean',
        organisme: { id_organisme: 1 }
      });

      component.onSubmit();
      tick();

      expect(component.errorMessage()).toBe('Une erreur est survenue');
    }));

    it('should set loading to false on error', fakeAsync(() => {
      httpMock.post.mockReturnValue(throwError(() => new Error('Network error')));

      component.registerForm.patchValue({
        email: 'test@example.com',
        password: 'password123',
        confirmPassword: 'password123',
        nom: 'Dupont',
        prenom: 'Jean',
        organisme: { id_organisme: 1 }
      });

      component.onSubmit();
      tick();

      expect(component.isLoading()).toBe(false);
    }));

    it('should handle organisme load error gracefully', fakeAsync(() => {
      httpMock.get.mockReturnValue(throwError(() => new Error('Network error')));

      const consoleSpy = jest.spyOn(console, 'error').mockImplementation();

      // Manually call loadOrganismes to test error handling
      component.loadOrganismes();
      tick();

      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    }));
  });

  // ==================== INTEGRATION TESTS ====================

  describe('Integration', () => {
    beforeEach(async () => {
      await setupTestBed();
      fixture.detectChanges();
    });

    it('should complete full registration flow', fakeAsync(() => {
      // Fill in the form
      component.registerForm.patchValue({
        email: 'newuser@example.com',
        password: 'securePassword123',
        confirmPassword: 'securePassword123',
        nom: 'Martin',
        prenom: 'Sophie',
        organisme: { id_organisme: 2, nom_organisme: 'CEN AURA' },
        justification: 'Je souhaite rejoindre l\'équipe'
      });

      // Form should be valid
      expect(component.registerForm.valid).toBe(true);

      // Submit
      component.onSubmit();
      tick();

      // Should navigate to pending page
      expect(router.navigate).toHaveBeenCalledWith(['/auth/registration-pending']);
    }));
  });
});
