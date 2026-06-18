import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { AuthService } from '../../core/services/auth.service';
import { FormFieldComponent } from '../../shared/components/form-field/form-field.component';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatProgressSpinnerModule,
    TranslateModule,
    FormFieldComponent,
  ],
  templateUrl: './reset-password.component.html',
  styleUrl: './login.component.scss',
})
export class ResetPasswordComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);

  form: FormGroup;
  hidePassword = signal(true);
  hideConfirm = signal(true);
  isLoading = signal(false);
  errorMessage = signal<string | null>(null);
  /** Passe à true après réinitialisation réussie : on masque le formulaire. */
  done = signal(false);

  private readonly uid: string;
  private readonly token: string;
  /** Lien incomplet (uid/token manquants) : on affiche un message dédié. */
  readonly invalidLink: boolean;

  constructor() {
    this.uid = this.route.snapshot.queryParams['uid'] ?? '';
    this.token = this.route.snapshot.queryParams['token'] ?? '';
    this.invalidLink = !this.uid || !this.token;

    this.form = this.fb.group(
      {
        password: ['', [Validators.required, Validators.minLength(8)]],
        confirmPassword: ['', [Validators.required]],
      },
      { validators: this.passwordMatchValidator },
    );
  }

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

  toggleConfirmVisibility(): void {
    this.hideConfirm.update(value => !value);
  }

  onSubmit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    this.errorMessage.set(null);
    this.isLoading.set(true);

    this.authService.confirmPasswordReset(this.uid, this.token, this.form.value.password).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.done.set(true);
        // Redirection automatique vers la connexion après un court délai.
        setTimeout(() => this.router.navigate(['/auth/login']), 2500);
      },
      error: (error: Error) => {
        this.isLoading.set(false);
        this.errorMessage.set(error.message);
      },
    });
  }
}
