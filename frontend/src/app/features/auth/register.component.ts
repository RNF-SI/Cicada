import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AbstractControl, FormBuilder, FormGroup, ValidationErrors, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { HttpClient } from '@angular/common/http';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { FormFieldComponent } from '../../shared/components/form-field/form-field.component';

interface OrganismeOption {
  id: number;
  nom_organisme: string;
}

@Component({
  selector: 'app-register',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatAutocompleteModule,
    TranslateModule,
    FormFieldComponent,
  ],
  templateUrl: './register.component.html',
  styleUrl: './register.component.scss'
})
export class RegisterComponent implements OnInit {
  private readonly fb = inject(FormBuilder);
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  private readonly translate = inject(TranslateService);

  registerForm: FormGroup;
  hidePassword = signal(true);
  hideConfirmPassword = signal(true);
  errorMessage = signal<string | null>(null);
  isLoading = signal(false);
  submitAttempted = signal(false);
  organismes = signal<OrganismeOption[]>([]);
  filteredOrganismes = signal<OrganismeOption[]>([]);
  /** Mode « créer un nouvel organisme » (l'organisme du demandeur n'existe pas). */
  creatingOrganisme = signal(false);

  constructor() {
    this.registerForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      identifiant: ['', [Validators.required, Validators.maxLength(100)]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      confirmPassword: ['', [Validators.required]],
      nom: ['', [Validators.required, Validators.maxLength(50)]],
      prenom: ['', [Validators.required, Validators.maxLength(50)]],
      organisme: [null, [Validators.required, this.organismeSelectedValidator]],
      // Sous-formulaire « nouvel organisme » (calqué sur le formulaire admin).
      // Les validators required sont activés dynamiquement en mode création.
      newOrganisme: this.fb.group({
        nom_organisme: ['', [Validators.maxLength(255)]],
        parent_id: [null],
        adresse_organisme: ['', [Validators.maxLength(255)]],
        cp_organisme: ['', [Validators.maxLength(10), Validators.pattern(/^\d{5}$/)]],
        ville_organisme: ['', [Validators.maxLength(100)]],
        tel_organisme: ['', [Validators.maxLength(20)]],
        email_organisme: ['', [Validators.email, Validators.maxLength(255)]],
        url_organisme: ['', [Validators.maxLength(255)]],
      }),
      justification: ['', [Validators.maxLength(1000)]]
    }, { validators: this.passwordMatchValidator });
  }

  /**
   * Bascule entre « choisir un organisme existant » et « créer un nouvel organisme ».
   * Active/désactive les validators en conséquence.
   */
  toggleCreateOrganisme(create: boolean): void {
    const organisme = this.registerForm.get('organisme')!;
    const newOrg = this.registerForm.get('newOrganisme') as FormGroup;
    const nom = newOrg.get('nom_organisme')!;

    if (create) {
      organisme.clearValidators();
      organisme.setValue(null);
      organisme.disable();
      nom.setValidators([Validators.required, Validators.maxLength(255)]);
    } else {
      organisme.enable();
      organisme.setValidators([Validators.required, this.organismeSelectedValidator]);
      nom.setValidators([Validators.maxLength(255)]);
      newOrg.reset({ parent_id: null });
    }
    organisme.updateValueAndValidity();
    nom.updateValueAndValidity();
    this.creatingOrganisme.set(create);
  }

  /** Message d'erreur d'un champ du sous-formulaire « nouvel organisme ». */
  newOrgError(name: string): string | null {
    const control = this.registerForm.get(['newOrganisme', name]);
    if (!control || (!control.touched && !this.submitAttempted()) || !control.errors) {
      return null;
    }
    const t = (key: string, params?: object) => this.translate.instant(key, params);
    const errors = control.errors;
    if (name === 'nom_organisme') {
      if (errors['required']) return t('common.validation.required');
      if (errors['maxlength']) return t('common.validation.maxLength', { max: 255 });
    }
    if (name === 'cp_organisme' && errors['pattern']) {
      return t('modals.organismeForm.validation.postalCodeInvalid');
    }
    if (name === 'email_organisme' && errors['email']) {
      return t('common.validation.email');
    }
    return null;
  }

  ngOnInit(): void {
    this.loadOrganismes();
  }

  /**
   * Charge la liste des organismes.
   */
  loadOrganismes(): void {
    this.http.get<OrganismeOption[]>('/api/users/organismes/public/')
      .subscribe({
        next: (organismes) => {
          this.organismes.set(organismes);
          this.filteredOrganismes.set(organismes);
        },
        error: (error) => {
          console.error('Erreur chargement organismes:', error);
        }
      });
  }

  /**
   * Filtre les organismes selon la saisie.
   */
  filterOrganismes(event: Event): void {
    const input = event.target as HTMLInputElement;
    const value = input.value.toLowerCase();

    if (!value) {
      this.filteredOrganismes.set(this.organismes());
      return;
    }

    const filtered = this.organismes().filter(org =>
      org.nom_organisme.toLowerCase().includes(value)
    );
    this.filteredOrganismes.set(filtered);
  }

  /**
   * Affiche le nom de l'organisme selectionne.
   */
  displayOrganisme(organisme: OrganismeOption): string {
    return organisme?.nom_organisme || '';
  }

  /**
   * Validator : l'organisme doit être un objet sélectionné dans la liste,
   * pas une string tapée librement (sinon id_organisme = undefined → null envoyé).
   */
  organismeSelectedValidator(control: AbstractControl): ValidationErrors | null {
    const value = control.value;
    if (value === null || value === undefined || value === '') {
      return null;  // Validators.required gère ce cas
    }
    const id = value?.id_organisme ?? value?.id;
    return typeof id === 'number' ? null : { organismeNotSelected: true };
  }

  /**
   * Validator pour verifier que les mots de passe correspondent.
   */
  passwordMatchValidator(form: FormGroup): { [key: string]: boolean } | null {
    const password = form.get('password');
    const confirmPassword = form.get('confirmPassword');

    if (password && confirmPassword && password.value !== confirmPassword.value) {
      return { passwordMismatch: true };
    }
    return null;
  }

  /**
   * Retourne le message d'erreur traduit d'un champ, ou null si le champ est valide.
   * Le message n'apparaît qu'une fois le champ "touché" ou après une tentative d'envoi,
   * pour ne pas afficher des erreurs sur un formulaire vierge.
   */
  fieldError(name: string): string | null {
    const control = this.registerForm.get(name);
    if (!control || (!control.touched && !this.submitAttempted())) {
      return null;
    }
    const t = (key: string, params?: object) => this.translate.instant(key, params);

    // Cas particulier : la concordance est une erreur de niveau formulaire.
    if (name === 'confirmPassword') {
      if (control.hasError('required')) return t('auth.register.errors.confirmPasswordRequired');
      if (this.registerForm.hasError('passwordMismatch')) return t('auth.register.errors.passwordMismatch');
      return null;
    }

    const errors = control.errors;
    if (!errors) return null;

    switch (name) {
      case 'prenom':
        if (errors['required']) return t('auth.register.errors.firstNameRequired');
        if (errors['maxlength']) return t('auth.register.errors.maxLength', { max: 50 });
        break;
      case 'nom':
        if (errors['required']) return t('auth.register.errors.lastNameRequired');
        if (errors['maxlength']) return t('auth.register.errors.maxLength', { max: 50 });
        break;
      case 'email':
        if (errors['required']) return t('auth.register.errors.emailRequired');
        if (errors['email']) return t('auth.register.errors.emailInvalid');
        break;
      case 'identifiant':
        if (errors['required']) return t('auth.register.errors.identifiantRequired');
        if (errors['maxlength']) return t('auth.register.errors.maxLength', { max: 100 });
        break;
      case 'password':
        if (errors['required']) return t('auth.register.errors.passwordRequired');
        if (errors['minlength']) return t('auth.register.errors.passwordMinLength');
        break;
      case 'organisme':
        if (errors['required']) return t('auth.register.errors.organismeRequired');
        if (errors['organismeNotSelected']) return t('auth.register.errors.organismeNotSelected');
        break;
      case 'justification':
        if (errors['maxlength']) return t('auth.register.errors.maxLength', { max: 1000 });
        break;
    }
    return null;
  }

  togglePasswordVisibility(): void {
    this.hidePassword.update(value => !value);
  }

  toggleConfirmPasswordVisibility(): void {
    this.hideConfirmPassword.update(value => !value);
  }

  onSubmit(): void {
    this.submitAttempted.set(true);

    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      this.errorMessage.set(this.translate.instant('auth.register.errors.formInvalid'));
      return;
    }

    this.errorMessage.set(null);
    this.isLoading.set(true);

    const formValue = this.registerForm.getRawValue();
    const payload: Record<string, unknown> = {
      email: formValue.email,
      identifiant: (formValue.identifiant || '').trim(),
      password: formValue.password,
      password_confirm: formValue.confirmPassword,
      nom_role: formValue.nom,
      prenom_role: formValue.prenom,
      justification: formValue.justification || ''
    };

    if (this.creatingOrganisme()) {
      // Demande de création d'un nouvel organisme (envoyée au super admin)
      const no = formValue.newOrganisme;
      payload['new_organisme'] = {
        nom_organisme: no.nom_organisme,
        parent_id: no.parent_id ?? null,
        adresse_organisme: no.adresse_organisme || '',
        cp_organisme: no.cp_organisme || '',
        ville_organisme: no.ville_organisme || '',
        tel_organisme: no.tel_organisme || '',
        email_organisme: no.email_organisme || '',
        url_organisme: no.url_organisme || ''
      };
    } else {
      payload['requested_organisme_id'] =
        formValue.organisme?.id_organisme ?? formValue.organisme?.id ?? null;
    }

    this.http.post('/api/auth/register/', payload)
      .subscribe({
        next: () => {
          this.router.navigate(['/auth/registration-pending']);
        },
        error: (error) => {
          if (error.error?.identifiant) {
            this.errorMessage.set(this.translate.instant('auth.register.errors.identifiantAlreadyUsed'));
          } else if (error.error?.email) {
            this.errorMessage.set(this.translate.instant('auth.register.errors.emailAlreadyUsed'));
          } else if (error.error?.error) {
            this.errorMessage.set(error.error.error);
          } else {
            this.errorMessage.set(this.translate.instant('errors.generic'));
          }
          this.isLoading.set(false);
        }
      });
  }
}
