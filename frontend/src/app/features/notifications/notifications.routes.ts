import { Routes } from '@angular/router';
import { authGuard } from '../../core/guards/auth.guard';
import { NotificationsComponent } from './notifications.component';

export const NOTIFICATIONS_ROUTES: Routes = [
  {
    path: '',
    component: NotificationsComponent,
    canActivate: [authGuard]
  }
];
