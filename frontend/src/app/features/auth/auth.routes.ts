import { Routes } from '@angular/router';
import { LoginComponent } from './login.component';
import { RegisterComponent } from './register.component';
import { RegistrationPendingComponent } from './registration-pending.component';
import { ForgotPasswordComponent } from './forgot-password.component';
import { ResetPasswordComponent } from './reset-password.component';
import { connexionLocaleGuard } from '../../core/guards/auth.guard';

export const AUTH_ROUTES: Routes = [
  {
    path: 'login',
    component: LoginComponent
  },
  {
    path: 'register',
    component: RegisterComponent,
    canActivate: [connexionLocaleGuard]
  },
  {
    path: 'forgot-password',
    component: ForgotPasswordComponent,
    canActivate: [connexionLocaleGuard]
  },
  {
    path: 'reset-password',
    component: ResetPasswordComponent,
    canActivate: [connexionLocaleGuard]
  },
  {
    path: 'registration-pending',
    component: RegistrationPendingComponent
  }
];
