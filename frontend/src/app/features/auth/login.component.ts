import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="auth-container">
      <h2>Connexion</h2>
      <p>Page de connexion - À implémenter</p>
    </div>
  `,
  styles: [`
    .auth-container {
      padding: 2rem;
      max-width: 500px;
      margin: 0 auto;
    }
  `]
})
export class LoginComponent {}
