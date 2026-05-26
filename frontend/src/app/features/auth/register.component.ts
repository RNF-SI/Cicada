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
  organismes = signal<OrganismeOption[]>([]);
  filteredOrganismes = signal<OrganismeOption[]>([]);

  constructor() {
    this.registerForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
      identifiant: ['', [Validators.maxLength(100)]],
      password: ['', [Validators.required, Validators.minLength(8)]],
      confirmPassword: ['', [Validators.required]],
      nom: ['', [Validators.required, Validators.maxLength(50)]],
      prenom: ['', [Validators.required, Validators.maxLength(50)]],
      organisme: [null, [Validators.required, this.organismeSelectedValidator]],
      justification: ['', [Validators.maxLength(1000)]]
    }, { validators: this.passwordMatchValidator });
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

  togglePasswordVisibility(): void {
    this.hidePassword.update(value => !value);
  }

  toggleConfirmPasswordVisibility(): void {
    this.hideConfirmPassword.update(value => !value);
  }

  onSubmit(): void {
    if (this.registerForm.invalid) {
      this.registerForm.markAllAsTouched();
      return;
    }

    this.errorMessage.set(null);
    this.isLoading.set(true);

    const formValue = this.registerForm.value;
    const payload = {
      email: formValue.email,
      identifiant: (formValue.identifiant || '').trim(),
      password: formValue.password,
      password_confirm: formValue.confirmPassword,
      nom_role: formValue.nom,
      prenom_role: formValue.prenom,
      requested_organisme_id: formValue.organisme?.id_organisme ?? formValue.organisme?.id ?? null,
      justification: formValue.justification || ''
    };

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
