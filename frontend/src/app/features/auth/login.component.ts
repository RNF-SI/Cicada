import { Component, computed, inject, signal, ChangeDetectionStrategy } from '@angular/core';

import { FormBuilder, FormGroup, Validators, ReactiveFormsModule } from '@angular/forms';
import { Router, ActivatedRoute, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { AuthService } from '../../core/services/auth.service';
import { LoginMode, LoginModeCode } from '../../core/models/user.model';
import { FormFieldComponent } from '../../shared/components/form-field/form-field.component';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    RouterLink,
    MatButtonModule,
    MatProgressSpinnerModule,
    TranslateModule,
    FormFieldComponent
],
  templateUrl: './login.component.html',
  changeDetection: ChangeDetectionStrategy.Eager,
  styleUrl: './login.component.scss'
})
export class LoginComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  loginForm: FormGroup;
  hidePassword = signal(true);
  errorMessage = signal<string | null>(null);
  isLoading = this.authService.isLoading;

  /** #689 — modes proposés par l'instance ; le choix n'apparaît que s'il y en a plusieurs. */
  modes = signal<LoginMode[]>([{ code: 'local' }]);
  mode = signal<LoginModeCode>('local');
  modeGeoNature = computed(() => this.modes().find(m => m.code === 'geonature') ?? null);

  constructor() {
    this.loginForm = this.fb.group({
      username: ['', [Validators.required]],
      password: ['', [Validators.required]]
    });

    this.authService.getLoginModes().subscribe(modes => {
      this.modes.set(modes);
      if (!this.modeGeoNature()) {
        return;
      }
      // Dernier mode utilisé sur ce navigateur, sinon le compte externe
      // (sur une instance raccordée, c'est le cas le plus courant).
      let dernier: string | null = null;
      try {
        dernier = localStorage.getItem(LoginComponent.CLE_MODE);
      } catch {
        dernier = null;
      }
      this.mode.set(dernier === 'local' ? 'local' : 'geonature');
    });
  }

  private static readonly CLE_MODE = 'login_mode';

  changerMode(mode: LoginModeCode): void {
    this.mode.set(mode);
    this.errorMessage.set(null);
  }

  togglePasswordVisibility(): void {
    this.hidePassword.update(value => !value);
  }

  onSubmit(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.errorMessage.set(null);

    const { username, password } = this.loginForm.value;

    const mode = this.mode();
    this.authService.login({ username, password }, mode).subscribe({
      next: () => {
        try {
          localStorage.setItem(LoginComponent.CLE_MODE, mode);
        } catch {
          // Stockage indisponible (navigation privée) : on retombera sur le défaut.
        }
        // Redirect to return URL or home
        const returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/accueil';
        this.router.navigateByUrl(returnUrl);
      },
      error: (error: Error) => {
        this.errorMessage.set(error.message);
      }
    });
  }
}
